from __future__ import annotations

import re

from ai3_cr_agent.domain.models import ChangeUnit, FilePatch, Hunk

HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<header>.*)$"
)


def _normalize_path(path_line: str) -> str:
    path = path_line.split(maxsplit=1)[1].strip()
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _finalize_hunk(hunk: Hunk | None) -> Hunk | None:
    return hunk


def parse_unified_diff(diff_text: str) -> list[FilePatch]:
    file_patches: list[FilePatch] = []
    current_file: FilePatch | None = None
    current_hunk: Hunk | None = None
    old_line_no = 0
    new_line_no = 0

    for raw_line in diff_text.splitlines():
        line = raw_line.rstrip("\n")

        if line.startswith("diff --git "):
            if current_file and current_hunk:
                current_file.hunks.append(_finalize_hunk(current_hunk))
                current_hunk = None
            if current_file:
                file_patches.append(current_file)
            current_file = FilePatch(old_path="", new_path="")
            continue

        if current_file is None:
            continue

        if line.startswith("--- "):
            current_file.old_path = _normalize_path(line)
            continue

        if line.startswith("+++ "):
            current_file.new_path = _normalize_path(line)
            continue

        hunk_match = HUNK_RE.match(line)
        if hunk_match:
            if current_hunk:
                current_file.hunks.append(_finalize_hunk(current_hunk))
            old_start = int(hunk_match.group("old_start"))
            new_start = int(hunk_match.group("new_start"))
            current_hunk = Hunk(
                header=hunk_match.group("header").strip(),
                old_start=old_start,
                old_count=int(hunk_match.group("old_count") or "1"),
                new_start=new_start,
                new_count=int(hunk_match.group("new_count") or "1"),
            )
            old_line_no = old_start
            new_line_no = new_start
            continue

        if current_hunk is None:
            continue

        current_hunk.lines.append(line)
        if line.startswith("+") and not line.startswith("+++"):
            current_hunk.added_lines.append(line[1:])
            current_hunk.changed_new_lines.append(new_line_no)
            current_hunk.added_line_map.append((new_line_no, line[1:]))
            new_line_no += 1
            continue
        if line.startswith("-") and not line.startswith("---"):
            current_hunk.removed_lines.append(line[1:])
            current_hunk.removed_line_map.append((old_line_no, line[1:]))
            old_line_no += 1
            continue
        if line.startswith("\\ No newline at end of file"):
            continue

        old_line_no += 1
        new_line_no += 1

    if current_file and current_hunk:
        current_file.hunks.append(_finalize_hunk(current_hunk))
    if current_file:
        file_patches.append(current_file)
    return file_patches


def build_change_units(file_patches: list[FilePatch]) -> list[ChangeUnit]:
    change_units: list[ChangeUnit] = []
    for file_patch in file_patches:
        for index, hunk in enumerate(file_patch.hunks, start=1):
            change_units.append(
                ChangeUnit(
                    change_id=f"{file_patch.target_path}::hunk-{index}",
                    file_path=file_patch.target_path,
                    hunk_index=index,
                    hunk=hunk,
                )
            )
    return change_units

