from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse
from urllib import error, request

from ai3_cr_agent.config import RuntimeConfig
from ai3_cr_agent.domain.models import ChangeUnit, ContextBundle, Finding, ReviewRun, ReviewSkill


class OpenAIReviewClient:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def review(
        self,
        *,
        agent_input: dict[str, object],
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
        skills: list[ReviewSkill],
    ) -> ReviewRun:
        request_payload, response_payload = self._invoke(agent_input, skills=skills)
        response_text = self._extract_response_text(response_payload)
        parsed = self._parse_response_json(response_text)
        findings = self._normalize_findings(parsed.get("findings", []), change_units)
        summary = str(parsed.get("summary", "")).strip() or _default_summary(findings)
        return ReviewRun(
            provider="openai",
            model=str(response_payload.get("model") or self.config.openai_model),
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            findings=findings,
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def review_stream(
        self,
        *,
        agent_input: dict[str, object],
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
        skills: list[ReviewSkill],
        on_event: Callable[[dict[str, Any]], None],
    ) -> ReviewRun:
        on_event({"type": "status", "message": f"Connecting to model {self.config.openai_model}..."})
        request_payload, response_payload, response_text = self._invoke_streaming(
            agent_input=agent_input,
            skills=skills,
            on_event=on_event,
        )
        on_event({"type": "status", "message": "Parsing model output..."})
        parsed = self._parse_response_json(response_text)
        findings = self._normalize_findings(parsed.get("findings", []), change_units)
        summary = str(parsed.get("summary", "")).strip() or _default_summary(findings)
        review_run = ReviewRun(
            provider="openai",
            model=str(response_payload.get("model") or self.config.openai_model),
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            findings=findings,
            request_payload=request_payload,
            response_payload=response_payload,
        )
        on_event(
            {
                "type": "complete",
                "summary": summary,
                "review_run": review_run.to_dict(),
            }
        )
        return review_run

    def _invoke(
        self,
        agent_input: dict[str, object],
        *,
        skills: list[ReviewSkill],
    ) -> tuple[dict[str, object], dict[str, Any]]:
        if self._prefer_chat_completions():
            payload = self._build_chat_completions_payload(agent_input, skills=skills)
            if skills:
                return payload, self._post_chat_completions_with_skills(payload, skills=skills)
            return payload, self._post_chat_completions(payload)

        payload = self._build_responses_payload(agent_input)
        try:
            return payload, self._post_responses(payload)
        except RuntimeError as exc:
            message = str(exc)
            if "404" not in message and "url.not_found" not in message:
                raise
            fallback_payload = self._build_chat_completions_payload(agent_input)
            response_payload = self._post_chat_completions(fallback_payload)
            return fallback_payload, response_payload

    def _invoke_streaming(
        self,
        *,
        agent_input: dict[str, object],
        skills: list[ReviewSkill],
        on_event: Callable[[dict[str, Any]], None],
    ) -> tuple[dict[str, object], dict[str, Any], str]:
        if self._prefer_chat_completions():
            payload = self._build_chat_completions_payload(agent_input, skills=skills, stream=True)
            if skills:
                response_payload, response_text = self._post_chat_completions_with_skills_stream(
                    payload,
                    skills=skills,
                    on_event=on_event,
                )
                return payload, response_payload, response_text
            response_payload, response_text = self._post_chat_completions_stream(payload, on_event=on_event)
            return payload, response_payload, response_text

        payload = self._build_responses_payload(agent_input, stream=True)
        try:
            response_payload, response_text = self._post_responses_stream(payload, on_event=on_event)
            return payload, response_payload, response_text
        except RuntimeError as exc:
            message = str(exc)
            if "404" not in message and "url.not_found" not in message:
                raise
            on_event({"type": "status", "message": "Falling back to chat completions compatibility mode..."})
            fallback_payload = self._build_chat_completions_payload(agent_input, skills=skills, stream=True)
            if skills:
                response_payload, response_text = self._post_chat_completions_with_skills_stream(
                    fallback_payload,
                    skills=skills,
                    on_event=on_event,
                )
            else:
                response_payload, response_text = self._post_chat_completions_stream(
                    fallback_payload,
                    on_event=on_event,
                )
            return fallback_payload, response_payload, response_text

    def _build_responses_payload(
        self,
        agent_input: dict[str, object],
        *,
        stream: bool = False,
    ) -> dict[str, object]:
        payload = {
            "model": self.config.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are a senior code review agent. Review only changed code and "
                                "return strict JSON. Surface only actionable findings with concrete evidence."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": _build_review_prompt(agent_input),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "code_review_result",
                    "strict": True,
                    "schema": _review_response_schema(),
                }
            },
        }
        if stream:
            payload["stream"] = True
        return payload

    def _build_chat_completions_payload(
        self,
        agent_input: dict[str, object],
        *,
        skills: list[ReviewSkill] | None = None,
        stream: bool = False,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.config.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior code review agent. Review only changed code and "
                        "return strict JSON. Surface only actionable findings with concrete evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": _build_review_prompt(agent_input),
                },
            ],
        }
        if skills:
            payload["tools"] = _build_skill_tools(skills)
            payload["tool_choice"] = "auto"
        if stream:
            payload["stream"] = True
        if self.config.openai_model.startswith("kimi-k2.5"):
            payload["thinking"] = {"type": "disabled"}
        return payload

    def _post_responses(self, payload: dict[str, object]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.config.openai_base_url}/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._execute_request(req)

    def _post_chat_completions(self, payload: dict[str, object]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.config.openai_base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._execute_request(req)

    def _post_chat_completions_with_skills(
        self,
        payload: dict[str, object],
        *,
        skills: list[ReviewSkill],
    ) -> dict[str, Any]:
        base_messages = list(payload.get("messages", []))
        messages = [dict(item) for item in base_messages]
        tool_index = {skill.skill_id: skill for skill in skills}
        current_payload = dict(payload)
        current_payload["messages"] = messages
        current_payload.pop("stream", None)

        for _ in range(8):
            response = self._post_chat_completions(current_payload)
            message = _first_choice_message(response)
            tool_calls = _extract_tool_calls(message)
            if not tool_calls:
                return response

            messages.append(message)
            for tool_call in tool_calls:
                tool_result = _execute_skill_tool_call(tool_call, tool_index)
                messages.append(tool_result)
            current_payload = dict(payload)
            current_payload["messages"] = messages
            current_payload.pop("stream", None)

        raise RuntimeError("Skill tool loop exceeded maximum iterations.")

    def _post_responses_stream(
        self,
        payload: dict[str, object],
        *,
        on_event: Callable[[dict[str, Any]], None],
    ) -> tuple[dict[str, Any], str]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.config.openai_base_url}/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        final_payload: dict[str, Any] = {}
        text_parts: list[str] = []
        try:
            with request.urlopen(req, timeout=self.config.openai_timeout_seconds) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    if not isinstance(event, dict):
                        continue
                    final_payload = event
                    delta = _extract_responses_delta(event)
                    if delta:
                        text_parts.append(delta)
                        on_event({"type": "token", "text": delta})
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API request failed: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc

        response_text = _strip_markdown_fence("".join(text_parts))
        if not response_text:
            payload = self._post_responses({key: value for key, value in payload.items() if key != "stream"})
            return payload, self._extract_response_text(payload)
        return final_payload, response_text

    def _post_chat_completions_stream(
        self,
        payload: dict[str, object],
        *,
        on_event: Callable[[dict[str, Any]], None],
    ) -> tuple[dict[str, Any], str]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.config.openai_base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        final_payload: dict[str, Any] = {"model": self.config.openai_model}
        text_parts: list[str] = []
        try:
            with request.urlopen(req, timeout=self.config.openai_timeout_seconds) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    if not isinstance(event, dict):
                        continue
                    final_payload = event
                    delta = _extract_chat_delta(event)
                    if delta:
                        text_parts.append(delta)
                        on_event({"type": "token", "text": delta})
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API request failed: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc

        response_text = _strip_markdown_fence("".join(text_parts))
        if not response_text:
            payload = self._post_chat_completions({key: value for key, value in payload.items() if key != "stream"})
            return payload, self._extract_response_text(payload)
        return final_payload, response_text

    def _post_chat_completions_with_skills_stream(
        self,
        payload: dict[str, object],
        *,
        skills: list[ReviewSkill],
        on_event: Callable[[dict[str, Any]], None],
    ) -> tuple[dict[str, Any], str]:
        base_messages = list(payload.get("messages", []))
        messages = [dict(item) for item in base_messages]
        tool_index = {skill.skill_id: skill for skill in skills}
        current_payload = dict(payload)
        current_payload["messages"] = messages
        current_payload.pop("stream", None)

        for _ in range(8):
            response = self._post_chat_completions(current_payload)
            message = _first_choice_message(response)
            tool_calls = _extract_tool_calls(message)
            if not tool_calls:
                text = self._extract_response_text(response)
                if text:
                    on_event({"type": "token", "text": text})
                return response, text

            messages.append(message)
            for tool_call in tool_calls:
                skill_id = _extract_skill_id(tool_call)
                if skill_id:
                    on_event({"type": "status", "message": f"Model invoked skill: {skill_id}"})
                tool_result = _execute_skill_tool_call(tool_call, tool_index)
                messages.append(tool_result)
            current_payload = dict(payload)
            current_payload["messages"] = messages
            current_payload.pop("stream", None)

        raise RuntimeError("Skill tool loop exceeded maximum iterations.")

    def _execute_request(self, req: request.Request) -> dict[str, Any]:
        try:
            with request.urlopen(req, timeout=self.config.openai_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API request failed: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc

    def _extract_response_text(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return _strip_markdown_fence(content)

        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        output = payload.get("output", [])
        if not isinstance(output, list):
            raise RuntimeError("OpenAI API response missing output content.")

        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") not in {"output_text", "text"}:
                    continue
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
        if not parts:
            raise RuntimeError("OpenAI API response did not contain review JSON text.")
        return _strip_markdown_fence("\n".join(parts))

    def _parse_response_json(self, text: str) -> dict[str, Any]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse OpenAI JSON review response: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("OpenAI JSON review response must be an object.")
        return payload

    def _normalize_findings(
        self,
        payload_findings: object,
        change_units: list[ChangeUnit],
    ) -> list[Finding]:
        if not isinstance(payload_findings, list):
            raise RuntimeError("OpenAI JSON review response field 'findings' must be a list.")

        change_by_id = {item.change_id: item for item in change_units}
        change_ids_by_file: dict[str, list[str]] = {}
        for item in change_units:
            change_ids_by_file.setdefault(item.file_path, []).append(item.change_id)

        deduped: dict[tuple[str, str, str, int | None], Finding] = {}
        for index, raw_item in enumerate(payload_findings, start=1):
            if not isinstance(raw_item, dict):
                continue

            raw_change_id = str(raw_item.get("change_id", "")).strip()
            file_path = str(raw_item.get("file_path", "")).strip()
            if raw_change_id not in change_by_id:
                candidates = change_ids_by_file.get(file_path, [])
                if len(candidates) == 1:
                    raw_change_id = candidates[0]
                else:
                    continue

            change_unit = change_by_id[raw_change_id]
            severity = _normalize_severity(raw_item.get("severity"))
            category = _normalize_category(raw_item.get("category"))
            title = str(raw_item.get("title", "")).strip()
            issue = str(raw_item.get("issue", "")).strip()
            evidence = str(raw_item.get("evidence", "")).strip()
            suggestion = str(raw_item.get("suggestion", "")).strip()
            if not all([title, issue, evidence, suggestion]):
                continue

            line = _normalize_line(raw_item.get("line"))
            confidence = _normalize_confidence(raw_item.get("confidence"))
            finding = Finding(
                finding_id=f"finding-{index}",
                change_id=raw_change_id,
                file_path=change_unit.file_path,
                severity=severity,
                category=category,
                confidence=confidence,
                title=title,
                issue=issue,
                evidence=evidence,
                suggestion=suggestion,
                line=line,
            )
            key = (finding.file_path, finding.category, finding.title, finding.line)
            existing = deduped.get(key)
            if existing is None or finding.confidence > existing.confidence:
                deduped[key] = finding

        return sorted(
            deduped.values(),
            key=lambda item: (_severity_rank(item.severity), -item.confidence, item.file_path),
        )

    def _prefer_chat_completions(self) -> bool:
        host = urlparse(self.config.openai_base_url).netloc.lower()
        if not host:
            return False
        return "api.openai.com" not in host


def _build_review_prompt(agent_input: dict[str, object]) -> str:
    return "\n".join(
        [
            "Review the supplied changed code only.",
            "Apply the active skills from agent_input.active_skills as additional review criteria.",
            "Return zero findings when no actionable issues are present.",
            "Use only these categories: correctness, security, maintainability.",
            "Use only these severities: high, medium, low.",
            "Use the exact change_id values from the input when you reference a finding.",
            "",
            "Review input JSON:",
            json.dumps(agent_input, ensure_ascii=False, indent=2),
        ]
    )


def _review_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "findings"],
        "properties": {
            "summary": {"type": "string"},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "change_id",
                        "file_path",
                        "severity",
                        "category",
                        "title",
                        "issue",
                        "evidence",
                        "suggestion",
                        "line",
                        "confidence",
                    ],
                    "properties": {
                        "change_id": {"type": "string"},
                        "file_path": {"type": "string"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "category": {
                            "type": "string",
                            "enum": ["correctness", "security", "maintainability"],
                        },
                        "title": {"type": "string"},
                        "issue": {"type": "string"},
                        "evidence": {"type": "string"},
                        "suggestion": {"type": "string"},
                        "line": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
        },
    }


def _normalize_severity(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"high", "medium", "low"} else "medium"


def _normalize_category(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"correctness", "security", "maintainability"} else "maintainability"


def _normalize_line(value: object) -> int | None:
    if value in {"", None}:
        return None
    try:
        line = int(value)
    except (TypeError, ValueError):
        return None
    return line if line > 0 else None


def _normalize_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(confidence, 1.0))


def _default_summary(findings: list[Finding]) -> str:
    if not findings:
        return "No actionable findings in the changed code."
    return f"Generated {len(findings)} actionable review findings."


def _severity_rank(severity: str) -> int:
    ranks = {"high": 0, "medium": 1, "low": 2}
    return ranks.get(severity, 99)


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_chat_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta", {})
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _extract_responses_delta(payload: dict[str, Any]) -> str:
    event_type = payload.get("type")
    if event_type == "response.output_text.delta":
        delta = payload.get("delta")
        return delta if isinstance(delta, str) else ""
    if event_type == "response.output_text.done":
        text = payload.get("text")
        return text if isinstance(text, str) else ""
    return ""


def _build_skill_tools(skills: list[ReviewSkill]) -> list[dict[str, Any]]:
    if not skills:
        return []
    enum_values = [skill.skill_id for skill in skills]
    descriptions = [f"- {skill.skill_id}: {skill.description}" for skill in skills]
    return [
        {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": (
                    "按需读取已激活的 Skill 内容，用于辅助当前代码审查。只有在你确实需要该 Skill 的具体规则或能力说明时才调用。"
                    + "\n可用 Skills：\n"
                    + "\n".join(descriptions)
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "enum": enum_values,
                            "description": "需要读取的 Skill 标识。",
                        }
                    },
                    "required": ["skill_id"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def _first_choice_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Chat completions response missing choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise RuntimeError("Chat completions first choice is invalid.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("Chat completions response missing message.")
    return message


def _extract_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls = message.get("tool_calls", [])
    return [item for item in tool_calls if isinstance(item, dict)]


def _execute_skill_tool_call(
    tool_call: dict[str, Any],
    tool_index: dict[str, ReviewSkill],
) -> dict[str, Any]:
    skill_id = _extract_skill_id(tool_call)
    if not skill_id:
        raise RuntimeError("Skill tool call missing skill_id.")
    skill = tool_index.get(skill_id)
    if skill is None:
        raise RuntimeError(f"Skill not found: {skill_id}")
    return {
        "role": "tool",
        "tool_call_id": str(tool_call.get("id", "")),
        "content": json.dumps(
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "content": skill.content,
            },
            ensure_ascii=False,
        ),
    }


def _extract_skill_id(tool_call: dict[str, Any]) -> str:
    function = tool_call.get("function", {})
    if not isinstance(function, dict):
        return ""
    arguments = function.get("arguments", "{}")
    if not isinstance(arguments, str):
        return ""
    try:
        payload = json.loads(arguments)
    except json.JSONDecodeError:
        return ""
    skill_id = payload.get("skill_id")
    return str(skill_id).strip() if skill_id is not None else ""
