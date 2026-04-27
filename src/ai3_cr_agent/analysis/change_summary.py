from __future__ import annotations

from ai3_cr_agent.domain.models import ChangeUnit, ContextBundle


def build_change_summary(change_units: list[ChangeUnit], contexts: list[ContextBundle]) -> str:
    context_by_id = {context.change_id: context for context in contexts}
    lines = ["# Change Summary", ""]
    for change_unit in change_units:
        context = context_by_id[change_unit.change_id]
        hunk = change_unit.hunk
        signals = _derive_signals(hunk.added_lines)
        lines.append(f"## {change_unit.change_id}")
        lines.append(f"- File: `{change_unit.file_path}`")
        lines.append(f"- Added lines: `{len(hunk.added_lines)}`")
        lines.append(f"- Removed lines: `{len(hunk.removed_lines)}`")
        if context.symbol_name:
            lines.append(f"- Enclosing symbol: `{context.symbol_name}` ({context.symbol_type})")
        if context.related_definitions:
            related_names = ", ".join(f"`{item.name}`" for item in context.related_definitions)
            lines.append(f"- One-hop related definitions: {related_names}")
        if signals:
            lines.append(f"- Review signals: {', '.join(signals)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_change_summary_payload(
    change_units: list[ChangeUnit],
    contexts: list[ContextBundle],
) -> list[dict[str, object]]:
    context_by_id = {context.change_id: context for context in contexts}
    payload: list[dict[str, object]] = []
    for change_unit in change_units:
        context = context_by_id[change_unit.change_id]
        payload.append(
            {
                "change_id": change_unit.change_id,
                "file_path": change_unit.file_path,
                "added_lines": len(change_unit.hunk.added_lines),
                "removed_lines": len(change_unit.hunk.removed_lines),
                "symbol_name": context.symbol_name,
                "symbol_type": context.symbol_type,
                "signals": _derive_signals(change_unit.hunk.added_lines),
            }
        )
    return payload


def _derive_signals(added_lines: list[str]) -> list[str]:
    signals: list[str] = []
    joined = "\n".join(added_lines)
    if "shell=True" in joined:
        signals.append("shell execution introduced")
    if "except Exception" in joined:
        signals.append("broad exception handling")
    if any(line.count(".") >= 2 for line in added_lines):
        signals.append("deep attribute access")
    if "return {" in joined:
        signals.append("response payload changed")
    return signals

