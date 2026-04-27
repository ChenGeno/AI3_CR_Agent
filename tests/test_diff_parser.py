from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai3_cr_agent.parsers.diff_parser import build_change_units, parse_unified_diff


class DiffParserTests(unittest.TestCase):
    def test_parse_example_patch(self) -> None:
        diff_text = (
            ROOT / "examples" / "cases" / "python_null_guard" / "diff.patch"
        ).read_text(encoding="utf-8")
        file_patches = parse_unified_diff(diff_text)
        change_units = build_change_units(file_patches)

        self.assertEqual(len(file_patches), 1)
        self.assertEqual(file_patches[0].target_path, "service/user_service.py")
        self.assertEqual(len(change_units), 2)
        self.assertIn("shell=True", change_units[0].hunk.added_lines[0])
        self.assertIn("except Exception", change_units[1].hunk.added_lines[-1])


if __name__ == "__main__":
    unittest.main()

