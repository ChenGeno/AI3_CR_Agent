from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai3_cr_agent.analysis.batch_planner import BatchPlanner
from ai3_cr_agent.analysis.context_resolver import ContextResolver
from ai3_cr_agent.parsers.diff_parser import build_change_units, parse_unified_diff


class BatchPlannerTests(unittest.TestCase):
    def test_small_case_collapses_into_single_batch(self) -> None:
        case_dir = ROOT / "examples" / "cases" / "python_null_guard"
        diff_text = (case_dir / "diff.patch").read_text(encoding="utf-8")
        change_units = build_change_units(parse_unified_diff(diff_text))
        contexts = ContextResolver().resolve(
            change_units=change_units,
            source_root=case_dir / "source_snapshot",
            pr_summary="pr",
            repo_summary="repo",
            review_rules=["rule"],
        )

        plan = BatchPlanner().plan(change_units=change_units, contexts=contexts)

        self.assertEqual(len(plan.batches), 1)
        self.assertEqual(plan.batches[0].change_ids, [item.change_id for item in change_units])


if __name__ == "__main__":
    unittest.main()
