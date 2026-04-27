from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai3_cr_agent.analysis.change_summary import build_change_summary
from ai3_cr_agent.analysis.openai_review_client import OpenAIReviewClient
from ai3_cr_agent.analysis.context_resolver import ContextResolver
from ai3_cr_agent.analysis.review_agent import ReviewAgent, render_review_comments
from ai3_cr_agent.analysis.static_checks import run_static_checks
from ai3_cr_agent.config import load_runtime_config
from ai3_cr_agent.domain.models import ReviewRun, ReviewSkill
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


class PipelineRunner:
    def __init__(
        self,
        *,
        context_resolver: ContextResolver | None = None,
        review_agent: ReviewAgent | None = None,
    ) -> None:
        self.context_resolver = context_resolver or ContextResolver()
        self.review_agent = review_agent

    def run(self, case_dir: Path, output_dir: Path | None = None) -> Path:
        review_agent = self.review_agent or ReviewAgent(
            client=OpenAIReviewClient(load_runtime_config())
        )
        prepared = self.prepare(case_dir, output_dir=output_dir, review_agent=review_agent)
        review_run = review_agent.review(
            change_units=prepared.change_units,
            contexts=prepared.contexts,
            change_summary_markdown=prepared.change_summary,
            static_findings=prepared.static_findings,
            skills=prepared.skills,
            agent_input=prepared.agent_input,
        )
        self.finalize(prepared, review_run)
        return prepared.output_dir

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
        )

    def finalize(self, prepared: PreparedReview, review_run: ReviewRun) -> Path:
        review_findings = review_run.findings
        review_comments = render_review_comments(review_findings)

        _write_json(prepared.output_dir / "parsed_changes.json", [item.to_dict() for item in prepared.change_units])
        _write_json(prepared.output_dir / "resolved_contexts.json", [item.to_dict() for item in prepared.contexts])
        (prepared.output_dir / "change_summary.md").write_text(prepared.change_summary, encoding="utf-8")
        _write_json(prepared.output_dir / "agent_input.json", prepared.agent_input)
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
