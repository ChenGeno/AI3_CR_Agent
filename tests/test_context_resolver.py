from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai3_cr_agent.analysis.context_resolver import ContextResolver
from ai3_cr_agent.parsers.diff_parser import build_change_units, parse_unified_diff


class ContextResolverTests(unittest.TestCase):
    def test_resolves_enclosing_symbol_and_one_hop_dependencies(self) -> None:
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

        self.assertEqual(contexts[0].symbol_name, "fetch_profile_name")
        self.assertEqual(contexts[1].symbol_name, "update_user_status")
        self.assertEqual(
            [item.name for item in contexts[1].related_definitions],
            ["normalize_status", "fetch_profile_name"],
        )


if __name__ == "__main__":
    unittest.main()
