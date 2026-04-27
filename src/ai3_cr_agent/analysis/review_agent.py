from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Protocol

from ai3_cr_agent.analysis.change_summary import build_change_summary_payload
from ai3_cr_agent.domain.models import ChangeUnit, ContextBundle, Finding, ReviewRun, ReviewSkill


class ReviewClient(Protocol):
    def review(
        self,
        *,
        agent_input: dict[str, object],
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
        skills: list[ReviewSkill],
    ) -> ReviewRun: ...

    def review_stream(
        self,
        *,
        agent_input: dict[str, object],
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
        skills: list[ReviewSkill],
        on_event: Callable[[dict[str, Any]], None],
    ) -> ReviewRun: ...


class ReviewAgent:
    def __init__(self, client: ReviewClient) -> None:
        self.client = client

    def build_agent_input(
        self,
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
        change_summary_markdown: str,
        static_findings: list[Finding],
        skills: list[ReviewSkill] | None = None,
    ) -> dict[str, object]:
        skills = skills or []
        return {
            "system_goal": (
                "Review only the changed code. Focus on correctness, security, and "
                "maintainability. Use the provided minimal context before asking for "
                "larger context."
            ),
            "active_skills": [skill.to_public_dict() for skill in skills],
            "review_contract": {
                "allowed_categories": ["correctness", "security", "maintainability"],
                "allowed_severities": ["high", "medium", "low"],
                "required_output_fields": [
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
                "do_not_comment_on": [
                    "formatting-only nits",
                    "speculative architecture rewrites",
                    "issues without code evidence",
                ],
            },
            "change_summary_markdown": change_summary_markdown,
            "change_summary": build_change_summary_payload(change_units, contexts),
            "contexts": [context.to_dict() for context in contexts],
            "seed_findings": [finding.to_dict() for finding in static_findings],
        }

    def review(
        self,
        *,
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
        change_summary_markdown: str,
        static_findings: list[Finding],
        skills: list[ReviewSkill] | None = None,
        agent_input: dict[str, object] | None = None,
    ) -> ReviewRun:
        agent_input = agent_input or self.build_agent_input(
            change_units=change_units,
            contexts=contexts,
            change_summary_markdown=change_summary_markdown,
            static_findings=static_findings,
            skills=skills,
        )
        return self.client.review(
            agent_input=agent_input,
            change_units=change_units,
            contexts=contexts,
            skills=skills or [],
        )

    def review_stream(
        self,
        *,
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
        change_summary_markdown: str,
        static_findings: list[Finding],
        skills: list[ReviewSkill] | None = None,
        on_event: Callable[[dict[str, Any]], None],
        agent_input: dict[str, object] | None = None,
    ) -> ReviewRun:
        agent_input = agent_input or self.build_agent_input(
            change_units=change_units,
            contexts=contexts,
            change_summary_markdown=change_summary_markdown,
            static_findings=static_findings,
            skills=skills,
        )
        return self.client.review_stream(
            agent_input=agent_input,
            change_units=change_units,
            contexts=contexts,
            skills=skills or [],
            on_event=on_event,
        )


def render_review_comments(findings: list[Finding]) -> str:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.file_path].append(finding)

    lines = ["# Review Comments", ""]
    if not findings:
        lines.extend(["No findings.", ""])
        return "\n".join(lines)

    for file_path in sorted(grouped):
        lines.append(f"## {file_path}")
        for finding in grouped[file_path]:
            location = f"Line {finding.line}" if finding.line else "Line n/a"
            lines.append(
                f"- [{finding.severity.upper()}] {finding.title} ({location}, {finding.category})"
            )
            lines.append(f"  Issue: {finding.issue}")
            lines.append(f"  Evidence: {finding.evidence}")
            lines.append(f"  Suggestion: {finding.suggestion}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
