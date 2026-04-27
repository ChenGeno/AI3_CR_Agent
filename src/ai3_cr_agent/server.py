from __future__ import annotations

import json
import mimetypes
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from ai3_cr_agent.analysis.change_summary import build_change_summary
from ai3_cr_agent.analysis.openai_review_client import OpenAIReviewClient
from ai3_cr_agent.analysis.review_agent import ReviewAgent
from ai3_cr_agent.config import RuntimeConfig, load_runtime_config
from ai3_cr_agent.domain.models import BatchReviewRun, ReviewRun, ReviewSkill
from ai3_cr_agent.pipeline import PipelineRunner, PreparedReview
from ai3_cr_agent.skills import list_registered_skills
from ai3_cr_agent.ui.admin_generation_page import render_admin_generation_page
from ai3_cr_agent.ui.admin_input_page import render_admin_input_page


@dataclass
class DashboardState:
    prepared: PreparedReview
    review_agent: ReviewAgent
    config: RuntimeConfig
    registered_skills: list[ReviewSkill]
    review_run: ReviewRun | None = None
    batch_runs: list[BatchReviewRun] = field(default_factory=list)
    global_review_run: ReviewRun | None = None
    generation_error: str | None = None
    pushed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


def serve_dashboard(
    case_dir: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    output_dir: Path | None = None,
) -> ThreadingHTTPServer:
    config = load_runtime_config()
    review_agent = ReviewAgent(client=OpenAIReviewClient(config))
    runner = PipelineRunner(review_agent=review_agent)
    prepared = runner.prepare(case_dir, output_dir=output_dir, review_agent=review_agent)
    state = DashboardState(
        prepared=prepared,
        review_agent=review_agent,
        config=config,
        registered_skills=list_registered_skills(),
    )

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/admin/input"}:
                self._send_html(
                    render_admin_input_page(
                        case_dir=state.prepared.case_dir,
                        model=state.config.openai_model,
                        registered_skills=state.registered_skills,
                        active_skills=state.prepared.skills,
                        agent_input=state.prepared.agent_input,
                        review_batches=state.prepared.review_batches,
                    )
                )
                return
            if parsed.path == "/admin/generate":
                self._send_html(
                    render_admin_generation_page(
                        model=state.config.openai_model,
                        batches_payload=json.dumps(
                            [batch.to_dict() for batch in state.prepared.review_batches],
                            ensure_ascii=False,
                        ),
                    )
                )
                return
            if parsed.path == "/api/generate-stream":
                self._handle_generate_stream()
                return
            if parsed.path == "/api/skills":
                self._send_json(
                    {
                        "registered_skills": [skill.to_dict() for skill in state.registered_skills],
                        "active_skill_ids": [skill.skill_id for skill in state.prepared.skills],
                    }
                )
                return
            if parsed.path.startswith("/artifacts/"):
                self._serve_artifact(parsed.path.removeprefix("/artifacts/"))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/push-review":
                self._handle_push_review()
                return
            if parsed.path == "/api/skills/toggle":
                self._handle_toggle_skill()
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:
            return

        def _handle_generate_stream(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            if state.review_run is not None:
                self._send_sse(
                    "complete",
                    {
                        "summary": state.review_run.summary,
                        "review_run": state.review_run.to_dict(),
                    },
                )
                return

            if not state.lock.acquire(blocking=False):
                self._send_sse("error", {"message": "A generation task is already running."})
                return

            try:
                self._emit_prepared_pipeline_snapshot()
                self._send_sse("status", {"message": "正在启动 Code Review 生成流程..."})
                review_run, batch_runs, global_review_run = PipelineRunner(
                    review_agent=state.review_agent
                ).execute(
                    state.prepared,
                    review_agent=state.review_agent,
                    on_event=lambda event: self._handle_pipeline_event(event),
                )
                state.review_run = review_run
                state.batch_runs = batch_runs
                state.global_review_run = global_review_run
                state.generation_error = None
                self._send_sse(
                    "complete",
                    {
                        "summary": state.review_run.summary,
                        "review_run": state.review_run.to_dict(),
                    },
                )
                self._send_sse(
                    "pipeline_step",
                    {
                        "stage_id": "final-merge",
                        "title": "合并审查结论",
                        "status": "completed",
                        "summary": "将局部批次审查结果与全局复审结果合并去重。",
                        "input": {
                            "batch_count": len(state.batch_runs),
                            "global_findings": len(state.global_review_run.findings) if state.global_review_run else 0,
                        },
                        "output": {
                            "final_finding_count": len(state.review_run.findings),
                            "summary": state.review_run.summary,
                        },
                    },
                )
            except Exception as exc:  # noqa: BLE001
                state.generation_error = str(exc)
                self._send_sse("error", {"message": str(exc)})
            finally:
                state.lock.release()

        def _handle_push_review(self) -> None:
            if state.review_run is None:
                self._send_json(
                    {"error": "No generated review is available yet."},
                    status=HTTPStatus.CONFLICT,
                )
                return

            if not state.pushed:
                PipelineRunner(review_agent=state.review_agent).finalize(
                    state.prepared,
                    state.review_run,
                    batch_runs=state.batch_runs,
                    global_review_run=state.global_review_run,
                )
                state.pushed = True

            self._send_json({"redirect_url": "/artifacts/pr_review.html"})

        def _handle_toggle_skill(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            payload = json.loads(raw_body)
            skill_id = str(payload.get("skill_id", "")).strip()
            if not skill_id:
                self._send_json({"error": "skill_id is required."}, status=HTTPStatus.BAD_REQUEST)
                return

            with state.lock:
                registry = {skill.skill_id: skill for skill in state.registered_skills}
                skill = registry.get(skill_id)
                if skill is None:
                    self._send_json({"error": f"Unknown skill: {skill_id}"}, status=HTTPStatus.NOT_FOUND)
                    return

                active_by_id = {item.skill_id: item for item in state.prepared.skills}
                if skill_id in active_by_id:
                    state.prepared.skills = [item for item in state.prepared.skills if item.skill_id != skill_id]
                else:
                    state.prepared.skills = [*state.prepared.skills, skill]

                state.prepared.agent_input = state.review_agent.build_agent_input(
                    change_units=state.prepared.change_units,
                    contexts=state.prepared.contexts,
                    change_summary_markdown=state.prepared.change_summary,
                    static_findings=state.prepared.static_findings,
                    skills=state.prepared.skills,
                )
                for review_batch in state.prepared.review_batches:
                    batch_change_ids = set(review_batch.change_ids)
                    batch_change_units = [
                        item for item in state.prepared.change_units if item.change_id in batch_change_ids
                    ]
                    batch_contexts = [
                        item for item in state.prepared.contexts if item.change_id in batch_change_ids
                    ]
                    batch_findings = [
                        item for item in state.prepared.static_findings if item.change_id in batch_change_ids
                    ]
                    state.prepared.batch_static_findings[review_batch.batch_id] = batch_findings
                    state.prepared.batch_agent_inputs[review_batch.batch_id] = state.review_agent.build_agent_input(
                        change_units=batch_change_units,
                        contexts=batch_contexts,
                        change_summary_markdown=build_change_summary(batch_change_units, batch_contexts),
                        static_findings=batch_findings,
                        skills=state.prepared.skills,
                    )
                state.review_run = None
                state.batch_runs = []
                state.global_review_run = None
                state.generation_error = None
                state.pushed = False

            self._send_json(
                {
                    "active_skill_ids": [item.skill_id for item in state.prepared.skills],
                    "agent_input": state.prepared.agent_input,
                }
            )

        def _serve_artifact(self, relative_path: str) -> None:
            safe_path = Path(unquote(relative_path)).name
            target = state.prepared.output_dir / safe_path
            if not target.exists() or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            content_type, _ = mimetypes.guess_type(str(target))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type or "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(target.read_bytes())

        def _send_html(self, payload: str) -> None:
            data = payload.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, payload: dict[str, object], *, status: int = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_sse(self, event_name: str, payload: dict[str, object]) -> None:
            data = json.dumps(payload, ensure_ascii=False)
            message = f"event: {event_name}\ndata: {data}\n\n".encode("utf-8")
            self.wfile.write(message)
            self.wfile.flush()

        def _handle_pipeline_event(self, event: dict[str, object]) -> None:
            event_type = str(event.get("type", "status"))
            payload = _payload_without_type(event)
            if event_type == "batch_start":
                batch_id = payload.get("batch_id", "")
                change_ids = payload.get("change_ids", [])
                review_batch = next(
                    (item for item in state.prepared.review_batches if item.batch_id == batch_id),
                    None,
                )
                self._send_sse(
                    "status",
                    {
                        "message": (
                            f"正在审查 {batch_id} "
                            f"（{len(change_ids) if isinstance(change_ids, list) else 0} 个变更）..."
                        )
                    },
                )
                self._send_sse(
                    "pipeline_step",
                    {
                        "stage_id": f"batch-review::{batch_id}",
                        "title": f"批次模型审查 {batch_id}",
                        "status": "running",
                        "summary": "正在执行当前语义批次的模型审查。",
                        "input": {
                            "change_ids": change_ids,
                            "estimated_tokens": payload.get("estimated_tokens"),
                            "skills": [skill.skill_id for skill in state.prepared.skills],
                            "files": review_batch.file_paths if review_batch else [],
                        },
                        "output": None,
                    },
                )
            elif event_type == "batch_complete":
                batch_id = payload.get("batch_id", "")
                self._send_sse(
                    "pipeline_step",
                    {
                        "stage_id": f"batch-review::{batch_id}",
                        "title": f"批次模型审查 {batch_id}",
                        "status": "completed",
                        "summary": payload.get("summary", ""),
                        "input": None,
                        "output": {
                            "finding_count": payload.get("finding_count", 0),
                            "finding_titles": payload.get("finding_titles", []),
                        },
                    },
                )
            elif event_type == "global_start":
                self._send_sse("status", {"message": "正在执行全局跨批次复审..."})
                self._send_sse(
                    "pipeline_step",
                    {
                        "stage_id": "global-review",
                        "title": "全局跨批次复审",
                        "status": "running",
                        "summary": "正在检查接口联动、状态流与跨文件一致性。",
                        "input": {
                            "batch_count": len(state.prepared.review_batches),
                            "batch_ids": [item.batch_id for item in state.prepared.review_batches],
                            "seed_finding_count": sum(
                                len(items) for items in state.prepared.batch_static_findings.values()
                            ),
                        },
                        "output": None,
                    },
                )
            elif event_type == "global_complete":
                self._send_sse(
                    "pipeline_step",
                    {
                        "stage_id": "global-review",
                        "title": "全局跨批次复审",
                        "status": "completed",
                        "summary": payload.get("summary", ""),
                        "input": None,
                        "output": {
                            "finding_count": payload.get("finding_count", 0),
                            "finding_titles": payload.get("finding_titles", []),
                        },
                    },
                )
            self._send_sse(event_type, payload)

        def _emit_prepared_pipeline_snapshot(self) -> None:
            context_symbols = sorted(
                {
                    context.symbol_name
                    for context in state.prepared.contexts
                    if context.symbol_name
                }
            )
            self._send_sse(
                "pipeline_step",
                {
                    "stage_id": "parse-diff",
                    "title": "解析 Diff",
                    "status": "completed",
                    "summary": "将统一 diff 解析成文件级补丁和 hunk 级变更单元。",
                    "input": {
                        "source": "diff.patch",
                    },
                    "output": {
                        "change_unit_count": len(state.prepared.change_units),
                        "change_ids": [item.change_id for item in state.prepared.change_units],
                    },
                },
            )
            self._send_sse(
                "pipeline_step",
                {
                    "stage_id": "resolve-context",
                    "title": "解析上下文",
                    "status": "completed",
                    "summary": "为每个变更补充代码片段、所属符号和一跳依赖定义。",
                    "input": {
                        "source_root": str(state.prepared.case_dir / "source_snapshot"),
                        "review_rules_count": len(state.prepared.contexts[0].review_rules) if state.prepared.contexts else 0,
                    },
                    "output": {
                        "context_count": len(state.prepared.contexts),
                        "symbols": context_symbols,
                    },
                },
            )
            self._send_sse(
                "pipeline_step",
                {
                    "stage_id": "static-checks",
                    "title": "执行静态检查",
                    "status": "completed",
                    "summary": "在调用模型前先生成种子问题与规则信号。",
                    "input": {
                        "change_ids": [item.change_id for item in state.prepared.change_units],
                    },
                    "output": {
                        "seed_finding_count": len(state.prepared.static_findings),
                        "seed_titles": [item.title for item in state.prepared.static_findings[:5]],
                    },
                },
            )
            self._send_sse(
                "pipeline_step",
                {
                    "stage_id": "plan-batches",
                    "title": "规划语义批次",
                    "status": "completed",
                    "summary": "基于文件与符号邻近性，把相关 hunk 聚合成审查批次。",
                    "input": {
                        "change_unit_count": len(state.prepared.change_units),
                        "active_skills": [skill.skill_id for skill in state.prepared.skills],
                    },
                    "output": {
                        "batch_count": len(state.prepared.review_batches),
                        "batches": [batch.to_dict() for batch in state.prepared.review_batches],
                    },
                },
            )
            self._send_sse(
                "pipeline_step",
                {
                    "stage_id": "build-agent-input",
                    "title": "构建审查输入",
                    "status": "completed",
                    "summary": "为全局复审和每个批次分别构建模型输入。",
                    "input": {
                        "active_skills": [skill.skill_id for skill in state.prepared.skills],
                    },
                    "output": {
                        "global_input_keys": sorted(state.prepared.agent_input.keys()),
                        "batch_input_count": len(state.prepared.batch_agent_inputs),
                    },
                },
            )

    return ThreadingHTTPServer((host, port), Handler)


def _payload_without_type(event: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in event.items() if key != "type"}
