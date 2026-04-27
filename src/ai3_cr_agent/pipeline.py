from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ai3_cr_agent.analysis.batch_planner import BatchPlanner
from ai3_cr_agent.analysis.change_summary import build_change_summary
from ai3_cr_agent.analysis.openai_review_client import OpenAIReviewClient
from ai3_cr_agent.analysis.context_resolver import ContextResolver
from ai3_cr_agent.analysis.review_agent import ReviewAgent, render_review_comments
from ai3_cr_agent.analysis.static_checks import run_static_checks
from ai3_cr_agent.config import load_runtime_config
from ai3_cr_agent.domain.models import BatchReviewRun, ReviewBatch, ReviewRun, ReviewSkill
from ai3_cr_agent.parsers.diff_parser import build_change_units, parse_unified_diff
from ai3_cr_agent.skills import load_selected_skills
from ai3_cr_agent.ui.issue_creation_page import render_issue_creation_page
from ai3_cr_agent.ui.issues_page import render_issues_page
from ai3_cr_agent.ui.pr_review_page import render_pr_review_page
from ai3_cr_agent.ui.issue_detail_page import render_issue_detail_page


@dataclass
class PreparedReview:
    case_dir: Path
    output_dir: Path
    change_units: list
    contexts: list
    change_summary: str
    static_findings: list
    skills: list[ReviewSkill]
    agent_input: dict[str, object]
    review_batches: list[ReviewBatch]
    batch_agent_inputs: dict[str, dict[str, object]]
    batch_static_findings: dict[str, list]
    global_agent_input: dict[str, object]


class PipelineRunner:
    def __init__(
        self,
        *,
        context_resolver: ContextResolver | None = None,
        review_agent: ReviewAgent | None = None,
        batch_planner: BatchPlanner | None = None,
    ) -> None:
        self.context_resolver = context_resolver or ContextResolver()
        self.review_agent = review_agent
        self.batch_planner = batch_planner or BatchPlanner()

    def run(self, case_dir: Path, output_dir: Path | None = None) -> Path:
        review_agent = self.review_agent or ReviewAgent(
            client=OpenAIReviewClient(load_runtime_config())
        )
        prepared = self.prepare(case_dir, output_dir=output_dir, review_agent=review_agent)
        review_run, batch_runs, global_review_run = self.execute(prepared, review_agent=review_agent)
        self.finalize(prepared, review_run, batch_runs=batch_runs, global_review_run=global_review_run)
        return prepared.output_dir

    def execute(
        self,
        prepared: PreparedReview,
        *,
        review_agent: ReviewAgent | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[ReviewRun, list[BatchReviewRun], ReviewRun]:
        review_agent = review_agent or self.review_agent or ReviewAgent(
            client=OpenAIReviewClient(load_runtime_config())
        )
        batch_runs = self._run_batches(prepared, review_agent=review_agent, on_event=on_event)
        prepared.global_agent_input = review_agent.build_global_agent_input(
            change_units=prepared.change_units,
            contexts=prepared.contexts,
            batch_runs=batch_runs,
            skills=prepared.skills,
        )
        if on_event is not None:
            on_event({"type": "global_start"})
        global_review_run = review_agent.review(
            change_units=prepared.change_units,
            contexts=prepared.contexts,
            change_summary_markdown=prepared.change_summary,
            static_findings=[],
            skills=prepared.skills,
            agent_input=prepared.global_agent_input,
        )
        for finding in global_review_run.findings:
            finding.source_phase = "global"
            finding.batch_id = None
        if on_event is not None:
            on_event(
                {
                    "type": "global_complete",
                    "summary": global_review_run.summary,
                    "finding_count": len(global_review_run.findings),
                    "finding_titles": [item.title for item in global_review_run.findings[:5]],
                }
            )

        review_run = _merge_review_runs(batch_runs, global_review_run)
        return review_run, batch_runs, global_review_run

    def prepare(
        self,
        case_dir: Path,
        *,
        output_dir: Path | None = None,
        review_agent: ReviewAgent | None = None,
    ) -> PreparedReview:
        case_dir = case_dir.resolve()
        output_dir = (output_dir or case_dir / "build").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        diff_text = _read_required(case_dir / "diff.patch")
        pr_summary = _read_required(case_dir / "pr_summary.md")
        repo_summary = _read_required(case_dir / "repo_summary.md")
        review_rules = _load_rules(case_dir / "review_rules.json")
        source_root = case_dir / "source_snapshot"

        file_patches = parse_unified_diff(diff_text)
        change_units = build_change_units(file_patches)
        contexts = self.context_resolver.resolve(
            change_units=change_units,
            source_root=source_root,
            pr_summary=pr_summary,
            repo_summary=repo_summary,
            review_rules=review_rules,
        )
        change_summary = build_change_summary(change_units, contexts)
        static_findings = run_static_checks(change_units, contexts)
        skills = load_selected_skills(case_dir)
        review_agent = review_agent or self.review_agent or ReviewAgent(
            client=OpenAIReviewClient(load_runtime_config())
        )
        review_batches_plan = self.batch_planner.plan(change_units=change_units, contexts=contexts)
        batch_agent_inputs: dict[str, dict[str, object]] = {}
        batch_static_findings: dict[str, list] = {}
        for review_batch in review_batches_plan.batches:
            batch_change_units = review_batches_plan.changes_by_batch_id[review_batch.batch_id]
            batch_contexts = review_batches_plan.contexts_by_batch_id[review_batch.batch_id]
            batch_findings = [
                finding
                for finding in static_findings
                if finding.change_id in set(review_batch.change_ids)
            ]
            batch_static_findings[review_batch.batch_id] = batch_findings
            batch_agent_inputs[review_batch.batch_id] = review_agent.build_agent_input(
                change_units=batch_change_units,
                contexts=batch_contexts,
                change_summary_markdown=build_change_summary(batch_change_units, batch_contexts),
                static_findings=batch_findings,
                skills=skills,
            )

        agent_input = review_agent.build_agent_input(
            change_units=change_units,
            contexts=contexts,
            change_summary_markdown=change_summary,
            static_findings=static_findings,
            skills=skills,
        )
        return PreparedReview(
            case_dir=case_dir,
            output_dir=output_dir,
            change_units=change_units,
            contexts=contexts,
            change_summary=change_summary,
            static_findings=static_findings,
            skills=skills,
            agent_input=agent_input,
            review_batches=review_batches_plan.batches,
            batch_agent_inputs=batch_agent_inputs,
            batch_static_findings=batch_static_findings,
            global_agent_input={},
        )

    def finalize(
        self,
        prepared: PreparedReview,
        review_run: ReviewRun,
        batch_runs: list[BatchReviewRun] | None = None,
        global_review_run: ReviewRun | None = None,
    ) -> Path:
        batch_runs = batch_runs or []
        global_review_run = global_review_run or _empty_global_review_run()
        review_findings = review_run.findings
        review_comments = render_review_comments(review_findings)

        _write_json(prepared.output_dir / "parsed_changes.json", [item.to_dict() for item in prepared.change_units])
        _write_json(prepared.output_dir / "resolved_contexts.json", [item.to_dict() for item in prepared.contexts])
        (prepared.output_dir / "change_summary.md").write_text(prepared.change_summary, encoding="utf-8")
        _write_json(prepared.output_dir / "agent_input.json", prepared.agent_input)
        _write_json(prepared.output_dir / "batched_review_plan.json", [item.to_dict() for item in prepared.review_batches])
        _write_json(prepared.output_dir / "batch_runs.json", [item.to_dict() for item in batch_runs])
        _write_json(prepared.output_dir / "global_review_run.json", global_review_run.to_dict())
        _write_json(prepared.output_dir / "review_run.json", review_run.to_dict())
        _write_json(prepared.output_dir / "review_findings.json", [item.to_dict() for item in review_findings])
        (prepared.output_dir / "review_comments.md").write_text(review_comments, encoding="utf-8")
        (prepared.output_dir / "pr_review.html").write_text(
            render_pr_review_page(
                findings=review_findings,
                contexts=prepared.contexts,
                review_summary=review_run.summary,
            ),
            encoding="utf-8",
        )
        (prepared.output_dir / "issue_create.html").write_text(
            render_issue_creation_page(findings=review_findings, contexts=prepared.contexts),
            encoding="utf-8",
        )
        (prepared.output_dir / "issues.html").write_text(
            render_issues_page(),
            encoding="utf-8",
        )
        (prepared.output_dir / "issue_detail.html").write_text(
            render_issue_detail_page(),
            encoding="utf-8",
        )
        return prepared.output_dir

    def _run_batches(
        self,
        prepared: PreparedReview,
        *,
        review_agent: ReviewAgent,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> list[BatchReviewRun]:
        context_by_id = {context.change_id: context for context in prepared.contexts}
        change_by_id = {change_unit.change_id: change_unit for change_unit in prepared.change_units}
        batch_runs: list[BatchReviewRun] = []

        for review_batch in prepared.review_batches:
            if on_event is not None:
                on_event(
                    {
                        "type": "batch_start",
                        "batch_id": review_batch.batch_id,
                        "estimated_tokens": review_batch.estimated_tokens,
                        "change_ids": review_batch.change_ids,
                    }
                )
            batch_change_units = [change_by_id[change_id] for change_id in review_batch.change_ids]
            batch_contexts = [context_by_id[change_id] for change_id in review_batch.change_ids]
            batch_review_run = review_agent.review(
                change_units=batch_change_units,
                contexts=batch_contexts,
                change_summary_markdown=build_change_summary(batch_change_units, batch_contexts),
                static_findings=prepared.batch_static_findings[review_batch.batch_id],
                skills=prepared.skills,
                agent_input=prepared.batch_agent_inputs[review_batch.batch_id],
            )
            for finding in batch_review_run.findings:
                finding.source_phase = "batch"
                finding.batch_id = review_batch.batch_id
            batch_runs.append(
                BatchReviewRun(
                    batch_id=review_batch.batch_id,
                    summary=batch_review_run.summary,
                    findings=batch_review_run.findings,
                    estimated_tokens=review_batch.estimated_tokens,
                    request_payload=batch_review_run.request_payload,
                    response_payload=batch_review_run.response_payload,
                )
            )
            if on_event is not None:
                on_event(
                    {
                        "type": "batch_complete",
                        "batch_id": review_batch.batch_id,
                        "summary": batch_review_run.summary,
                        "finding_count": len(batch_review_run.findings),
                        "finding_titles": [item.title for item in batch_review_run.findings[:5]],
                    }
                )
        return batch_runs


def _read_required(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_rules(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("rules", []))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _merge_review_runs(batch_runs: list[BatchReviewRun], global_review_run: ReviewRun) -> ReviewRun:
    deduped: dict[tuple[str, str, str, int | None], object] = {}
    combined_findings = [finding for batch_run in batch_runs for finding in batch_run.findings]
    combined_findings.extend(global_review_run.findings)
    for finding in combined_findings:
        key = (finding.file_path, finding.category, finding.title, finding.line)
        existing = deduped.get(key)
        if existing is None or finding.confidence >= existing.confidence:
            deduped[key] = finding

    batch_summaries = [f"{batch_run.batch_id}: {batch_run.summary}" for batch_run in batch_runs]
    if global_review_run.summary:
        batch_summaries.append(f"global: {global_review_run.summary}")
    return ReviewRun(
        provider="openai",
        model=global_review_run.model,
        generated_at=global_review_run.generated_at,
        summary="\n".join(batch_summaries).strip(),
        findings=list(deduped.values()),
        request_payload={
            "mode": "layered_batches",
            "batch_count": len(batch_runs),
            "batches": [batch_run.to_dict() for batch_run in batch_runs],
            "global_review_request": global_review_run.request_payload,
        },
        response_payload={
            "global_review_response": global_review_run.response_payload,
        },
    )


def _empty_global_review_run() -> ReviewRun:
    return ReviewRun(
        provider="openai",
        model="",
        generated_at="",
        summary="",
        findings=[],
        request_payload={},
        response_payload={},
    )
