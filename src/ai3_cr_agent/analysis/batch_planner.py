from __future__ import annotations

from dataclasses import dataclass

from ai3_cr_agent.domain.models import ChangeUnit, ContextBundle, ReviewBatch


@dataclass
class BatchPlan:
    batches: list[ReviewBatch]
    contexts_by_batch_id: dict[str, list[ContextBundle]]
    changes_by_batch_id: dict[str, list[ChangeUnit]]


class BatchPlanner:
    def __init__(
        self,
        *,
        max_batch_tokens: int = 2400,
        max_changes_per_batch: int = 6,
    ) -> None:
        self.max_batch_tokens = max_batch_tokens
        self.max_changes_per_batch = max_changes_per_batch

    def plan(
        self,
        *,
        change_units: list[ChangeUnit],
        contexts: list[ContextBundle],
    ) -> BatchPlan:
        context_by_id = {context.change_id: context for context in contexts}
        grouped: dict[tuple[str, str], list[ChangeUnit]] = {}
        for change_unit in change_units:
            context = context_by_id[change_unit.change_id]
            key = (change_unit.file_path, context.symbol_name or f"hunk-{change_unit.hunk_index}")
            grouped.setdefault(key, []).append(change_unit)

        ordered_groups = sorted(grouped.values(), key=lambda items: items[0].change_id)
        batches: list[ReviewBatch] = []
        contexts_by_batch_id: dict[str, list[ContextBundle]] = {}
        changes_by_batch_id: dict[str, list[ChangeUnit]] = {}

        batch_index = 1
        current_changes: list[ChangeUnit] = []
        current_contexts: list[ContextBundle] = []
        current_tokens = 0

        for group in ordered_groups:
            group_contexts = [context_by_id[change_unit.change_id] for change_unit in group]
            group_tokens = sum(
                _estimate_change_tokens(change_unit, context)
                for change_unit, context in zip(group, group_contexts)
            )
            if current_changes and (
                len(current_changes) + len(group) > self.max_changes_per_batch
                or current_tokens + group_tokens > self.max_batch_tokens
            ):
                batch_id = f"batch-{batch_index}"
                batch = _build_batch(
                    batch_id=batch_id,
                    change_units=current_changes,
                    contexts=current_contexts,
                    estimated_tokens=current_tokens,
                )
                batches.append(batch)
                changes_by_batch_id[batch_id] = list(current_changes)
                contexts_by_batch_id[batch_id] = list(current_contexts)
                batch_index += 1
                current_changes = []
                current_contexts = []
                current_tokens = 0

            for change_unit, context in zip(group, group_contexts):
                estimate = _estimate_change_tokens(change_unit, context)
                would_overflow = (
                    current_changes
                    and (
                        len(current_changes) >= self.max_changes_per_batch
                        or current_tokens + estimate > self.max_batch_tokens
                    )
                )
                if would_overflow:
                    batch_id = f"batch-{batch_index}"
                    batch = _build_batch(
                        batch_id=batch_id,
                        change_units=current_changes,
                        contexts=current_contexts,
                        estimated_tokens=current_tokens,
                    )
                    batches.append(batch)
                    changes_by_batch_id[batch_id] = list(current_changes)
                    contexts_by_batch_id[batch_id] = list(current_contexts)
                    batch_index += 1
                    current_changes = []
                    current_contexts = []
                    current_tokens = 0

                current_changes.append(change_unit)
                current_contexts.append(context)
                current_tokens += estimate

        if current_changes:
            batch_id = f"batch-{batch_index}"
            batch = _build_batch(
                batch_id=batch_id,
                change_units=current_changes,
                contexts=current_contexts,
                estimated_tokens=current_tokens,
            )
            batches.append(batch)
            changes_by_batch_id[batch_id] = list(current_changes)
            contexts_by_batch_id[batch_id] = list(current_contexts)

        return BatchPlan(
            batches=batches,
            contexts_by_batch_id=contexts_by_batch_id,
            changes_by_batch_id=changes_by_batch_id,
        )


def _build_batch(
    *,
    batch_id: str,
    change_units: list[ChangeUnit],
    contexts: list[ContextBundle],
    estimated_tokens: int,
) -> ReviewBatch:
    symbol_names = sorted({context.symbol_name for context in contexts if context.symbol_name})
    file_paths = sorted({change.file_path for change in change_units})
    return ReviewBatch(
        batch_id=batch_id,
        change_ids=[change.change_id for change in change_units],
        file_paths=file_paths,
        symbol_names=symbol_names,
        estimated_tokens=estimated_tokens,
    )


def _estimate_change_tokens(change_unit: ChangeUnit, context: ContextBundle) -> int:
    parts = [
        "\n".join(change_unit.hunk.lines),
        context.file_excerpt,
        context.symbol_source,
        "\n".join(item.source for item in context.related_definitions),
        context.pr_summary,
        context.repo_summary,
        "\n".join(context.review_rules),
    ]
    total_chars = sum(len(part) for part in parts if part)
    return max(80, total_chars // 4)
