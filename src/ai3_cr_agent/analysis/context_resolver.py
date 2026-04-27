from __future__ import annotations

import ast
from pathlib import Path

from ai3_cr_agent.domain.models import ChangeUnit, ContextBundle, RelatedDefinition


def detect_language(file_path: str) -> str:
    if file_path.endswith(".py"):
        return "python"
    return "text"


class ContextResolver:
    def resolve(
        self,
        change_units: list[ChangeUnit],
        source_root: Path,
        pr_summary: str,
        repo_summary: str,
        review_rules: list[str],
    ) -> list[ContextBundle]:
        bundles: list[ContextBundle] = []
        for change_unit in change_units:
            language = detect_language(change_unit.file_path)
            target_file = source_root / change_unit.file_path
            if language == "python" and target_file.exists():
                bundles.append(
                    self._resolve_python_context(
                        change_unit=change_unit,
                        target_file=target_file,
                        pr_summary=pr_summary,
                        repo_summary=repo_summary,
                        review_rules=review_rules,
                    )
                )
                continue
            bundles.append(
                self._resolve_plain_context(
                    change_unit=change_unit,
                    target_file=target_file,
                    pr_summary=pr_summary,
                    repo_summary=repo_summary,
                    review_rules=review_rules,
                )
            )
        return bundles

    def _resolve_plain_context(
        self,
        change_unit: ChangeUnit,
        target_file: Path,
        pr_summary: str,
        repo_summary: str,
        review_rules: list[str],
    ) -> ContextBundle:
        source = target_file.read_text(encoding="utf-8") if target_file.exists() else ""
        excerpt = _build_excerpt(source.splitlines(), change_unit.hunk.changed_new_lines)
        return ContextBundle(
            change_id=change_unit.change_id,
            file_path=change_unit.file_path,
            language=detect_language(change_unit.file_path),
            symbol_name=None,
            symbol_type=None,
            symbol_source="",
            file_excerpt=excerpt,
            related_definitions=[],
            pr_summary=pr_summary,
            repo_summary=repo_summary,
            review_rules=review_rules,
        )

    def _resolve_python_context(
        self,
        change_unit: ChangeUnit,
        target_file: Path,
        pr_summary: str,
        repo_summary: str,
        review_rules: list[str],
    ) -> ContextBundle:
        source = target_file.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and hasattr(node, "end_lineno")
        ]

        changed_lines = change_unit.hunk.changed_new_lines or [change_unit.hunk.new_start]
        symbol_node = _find_smallest_enclosing_node(nodes, changed_lines)
        symbol_source = ""
        symbol_name: str | None = None
        symbol_type: str | None = None
        related_definitions: list[RelatedDefinition] = []

        if symbol_node is not None:
            symbol_name = symbol_node.name
            symbol_type = "class" if isinstance(symbol_node, ast.ClassDef) else "function"
            symbol_source = _slice_source(lines, symbol_node.lineno, symbol_node.end_lineno)
            related_definitions = _collect_related_definitions(tree, lines, symbol_node)

        excerpt = _build_excerpt(lines, changed_lines)
        return ContextBundle(
            change_id=change_unit.change_id,
            file_path=change_unit.file_path,
            language="python",
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            symbol_source=symbol_source,
            file_excerpt=excerpt,
            related_definitions=related_definitions,
            pr_summary=pr_summary,
            repo_summary=repo_summary,
            review_rules=review_rules,
        )


def _find_smallest_enclosing_node(nodes: list[ast.AST], changed_lines: list[int]) -> ast.AST | None:
    candidates = []
    for node in nodes:
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if start is None or end is None:
            continue
        if all(start <= line <= end for line in changed_lines):
            candidates.append(node)
    if not candidates:
        return None
    return min(candidates, key=lambda item: getattr(item, "end_lineno") - getattr(item, "lineno"))


def _slice_source(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1 : end])


def _build_excerpt(lines: list[str], changed_lines: list[int], radius: int = 3) -> str:
    if not lines:
        return ""
    start = max(1, min(changed_lines) - radius)
    end = min(len(lines), max(changed_lines) + radius)
    numbered = []
    for line_no in range(start, end + 1):
        numbered.append(f"{line_no:>4}: {lines[line_no - 1]}")
    return "\n".join(numbered)


def _collect_related_definitions(
    tree: ast.Module,
    lines: list[str],
    symbol_node: ast.AST,
) -> list[RelatedDefinition]:
    definition_index: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and hasattr(node, "end_lineno"):
            definition_index[node.name] = node

    related: list[RelatedDefinition] = []
    seen: set[str] = set()
    for call in ast.walk(symbol_node):
        callee_name = _resolve_callee_name(call)
        if callee_name is None or callee_name in seen:
            continue
        target = definition_index.get(callee_name)
        if target is None or target is symbol_node:
            continue
        related.append(
            RelatedDefinition(
                name=callee_name,
                symbol_type="function",
                source=_slice_source(lines, target.lineno, target.end_lineno),
            )
        )
        seen.add(callee_name)
        if len(related) >= 3:
            break
    return related


def _resolve_callee_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None

