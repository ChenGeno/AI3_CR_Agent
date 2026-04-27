from __future__ import annotations

import json
import mimetypes
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from ai3_cr_agent.analysis.openai_review_client import OpenAIReviewClient
from ai3_cr_agent.analysis.review_agent import ReviewAgent
from ai3_cr_agent.config import RuntimeConfig, load_runtime_config
from ai3_cr_agent.domain.models import ReviewSkill
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
    review_run: object | None = None
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
                    )
                )
                return
            if parsed.path == "/admin/generate":
                self._send_html(render_admin_generation_page(model=state.config.openai_model))
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
                self._send_sse("status", {"message": "Starting Code Review generation..."})
                review_run = state.review_agent.review_stream(
                    change_units=state.prepared.change_units,
                    contexts=state.prepared.contexts,
                    change_summary_markdown=state.prepared.change_summary,
                    static_findings=state.prepared.static_findings,
                    skills=state.prepared.skills,
                    agent_input=state.prepared.agent_input,
                    on_event=lambda event: self._send_sse(event["type"], _payload_without_type(event)),
                )
                state.review_run = review_run
                state.generation_error = None
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
                PipelineRunner(review_agent=state.review_agent).finalize(state.prepared, state.review_run)
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
                state.review_run = None
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

    return ThreadingHTTPServer((host, port), Handler)


def _payload_without_type(event: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in event.items() if key != "type"}
