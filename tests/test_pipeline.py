from __future__ import annotations

import shutil
import sys
from pathlib import Path
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai3_cr_agent.analysis.review_agent import ReviewAgent
from ai3_cr_agent.domain.models import Finding, ReviewRun
from ai3_cr_agent.pipeline import PipelineRunner


class FakeOpenAIReviewClient:
    def review(self, *, agent_input: dict[str, object], change_units, contexts, skills) -> ReviewRun:
        seed_findings = agent_input.get("seed_findings", [])
        findings = [
            Finding(
                finding_id=f"finding-{index}",
                change_id=item["change_id"],
                file_path=item["file_path"],
                severity=item["severity"],
                category=item["category"],
                confidence=item["confidence"],
                title=item["title"],
                issue=item["issue"],
                evidence=item["evidence"],
                suggestion=item["suggestion"],
                line=item["line"],
            )
            for index, item in enumerate(seed_findings, start=1)
        ]
        return ReviewRun(
            provider="openai",
            model="fake-review-model",
            generated_at="2026-04-15T00:00:00+00:00",
            summary="Fake LLM review summary.",
            findings=findings,
            request_payload={"agent_input": agent_input},
            response_payload={"id": "resp_fake", "model": "fake-review-model"},
        )


class PipelineRunnerTests(unittest.TestCase):
    def test_pipeline_generates_expected_artifacts(self) -> None:
        case_src = ROOT / "examples" / "cases" / "python_null_guard"
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_case = Path(tmp_dir) / "python_null_guard"
            shutil.copytree(case_src, temp_case)
            output_dir = PipelineRunner(
                review_agent=ReviewAgent(client=FakeOpenAIReviewClient())
            ).run(temp_case)

            self.assertTrue((output_dir / "parsed_changes.json").exists())
            self.assertTrue((output_dir / "resolved_contexts.json").exists())
            self.assertTrue((output_dir / "change_summary.md").exists())
            self.assertTrue((output_dir / "agent_input.json").exists())
            self.assertTrue((output_dir / "review_run.json").exists())
            self.assertTrue((output_dir / "review_findings.json").exists())
            self.assertTrue((output_dir / "review_comments.md").exists())
            self.assertTrue((output_dir / "pr_review.html").exists())
            self.assertTrue((output_dir / "issue_create.html").exists())
            self.assertTrue((output_dir / "issues.html").exists())
            self.assertTrue((output_dir / "issue_detail.html").exists())

            review_run = (output_dir / "review_run.json").read_text(encoding="utf-8")
            pr_review = (output_dir / "pr_review.html").read_text(encoding="utf-8")
            self.assertIn("Fake LLM review summary.", review_run)
            self.assertIn("Fake LLM review summary.", pr_review)
            self.assertIn("issue_detail.html", (output_dir / "issues.html").read_text(encoding="utf-8"))
            agent_input = json.loads((output_dir / "agent_input.json").read_text(encoding="utf-8"))
            self.assertEqual(len(agent_input["active_skills"]), 2)
            self.assertEqual(agent_input["active_skills"][0]["skill_id"], "custom_coding_conventions")


if __name__ == "__main__":
    unittest.main()
