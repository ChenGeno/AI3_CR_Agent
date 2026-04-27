from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Hunk:
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    changed_new_lines: list[int] = field(default_factory=list)
    added_line_map: list[tuple[int, str]] = field(default_factory=list)
    removed_line_map: list[tuple[int, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FilePatch:
    old_path: str
    new_path: str
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def target_path(self) -> str:
        return self.new_path if self.new_path != "/dev/null" else self.old_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_path": self.old_path,
            "new_path": self.new_path,
            "target_path": self.target_path,
            "hunks": [hunk.to_dict() for hunk in self.hunks],
        }


@dataclass
class ChangeUnit:
    change_id: str
    file_path: str
    hunk_index: int
    hunk: Hunk

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "file_path": self.file_path,
            "hunk_index": self.hunk_index,
            "hunk": self.hunk.to_dict(),
        }


@dataclass
class RelatedDefinition:
    name: str
    symbol_type: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextBundle:
    change_id: str
    file_path: str
    language: str
    symbol_name: str | None
    symbol_type: str | None
    symbol_source: str
    file_excerpt: str
    related_definitions: list[RelatedDefinition]
    pr_summary: str
    repo_summary: str
    review_rules: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "file_path": self.file_path,
            "language": self.language,
            "symbol_name": self.symbol_name,
            "symbol_type": self.symbol_type,
            "symbol_source": self.symbol_source,
            "file_excerpt": self.file_excerpt,
            "related_definitions": [item.to_dict() for item in self.related_definitions],
            "pr_summary": self.pr_summary,
            "repo_summary": self.repo_summary,
            "review_rules": self.review_rules,
        }


@dataclass
class Finding:
    change_id: str
    file_path: str
    severity: str
    category: str
    confidence: float
    title: str
    issue: str
    evidence: str
    suggestion: str
    line: int | None = None
    finding_id: str = ""
    source_phase: str = "batch"
    batch_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewBatch:
    batch_id: str
    change_ids: list[str]
    file_paths: list[str]
    symbol_names: list[str]
    estimated_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchReviewRun:
    batch_id: str
    summary: str
    findings: list[Finding]
    estimated_tokens: int
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    status: str = "completed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "summary": self.summary,
            "findings": [item.to_dict() for item in self.findings],
            "estimated_tokens": self.estimated_tokens,
            "request_payload": self.request_payload,
            "response_payload": self.response_payload,
            "status": self.status,
        }


@dataclass
class ReviewRun:
    provider: str
    model: str
    generated_at: str
    summary: str
    findings: list[Finding]
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "findings": [item.to_dict() for item in self.findings],
            "request_payload": self.request_payload,
            "response_payload": self.response_payload,
        }


@dataclass
class ReviewSkill:
    skill_id: str
    name: str
    description: str
    content: str
    source_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "source_path": self.source_path,
        }
