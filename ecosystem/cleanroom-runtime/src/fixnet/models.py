from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

RelationshipType = Literal[
    "inspired_by",
    "solved_similar",
    "alternative_approach",
    "improved_version",
    "prerequisite",
    "supersedes",
    "fallback_for",
]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class FixEdge:
    parent_fix_id: str
    child_fix_id: str
    relationship: RelationshipType
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FixRecord:
    fix_id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    error_type: str = ""
    error_signature: str = ""
    solution: str = ""
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    linked_event_ids: list[str] = field(default_factory=list)
    linked_run_ids: list[str] = field(default_factory=list)
    linked_proposal_ids: list[str] = field(default_factory=list)
    remote_ref: Optional[dict[str, Any]] = None
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConsensusRecord:
    fix_id: str
    trust_level: str = "unknown"
    success_rate: float = 0.0
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    reputation_score: float = 0.5
    quarantined: bool = False
    updated_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NoveltyDecision:
    fix_id: str
    novelty_score: float
    decision: str  # novel|duplicate|variant|update
    duplicate_of: Optional[str] = None
    variant_of: Optional[str] = None
    reason: str = ""
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EmbeddedArchiveRef:
    fix_id: str
    archive_branch_id: str
    archive_pack_id: str
    early_merge_at: str
    last_sync_at: str
    retirement_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
