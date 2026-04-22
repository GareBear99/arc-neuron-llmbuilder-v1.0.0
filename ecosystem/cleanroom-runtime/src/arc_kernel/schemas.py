from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventKind(str, Enum):
    INPUT = "input"
    PROPOSAL = "proposal"
    POLICY_DECISION = "policy_decision"
    EXECUTION = "execution"
    RECEIPT = "receipt"
    EVALUATION = "evaluation"
    MEMORY_UPDATE = "memory_update"
    BRANCH_PLAN = "branch_plan"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


@dataclass(slots=True)
class Event:
    kind: EventKind
    actor: str
    payload: Dict[str, Any]
    parent_event_id: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        payload = dict(data)
        payload["kind"] = EventKind(payload["kind"])
        return cls(**payload)


@dataclass(slots=True)
class Capability:
    name: str
    description: str
    risk: RiskLevel
    side_effects: List[str] = field(default_factory=list)
    validators: List[str] = field(default_factory=list)
    dry_run_supported: bool = True
    requires_confirmation: bool = False


@dataclass(slots=True)
class Proposal:
    action: str
    capability: Capability
    params: Dict[str, Any]
    proposed_by: str
    rationale: str
    proposal_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["capability"]["risk"] = self.capability.risk.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proposal":
        capability_dict = dict(data["capability"])
        capability_dict["risk"] = RiskLevel(capability_dict["risk"])
        return cls(
            action=data["action"],
            capability=Capability(**capability_dict),
            params=dict(data["params"]),
            proposed_by=data["proposed_by"],
            rationale=data["rationale"],
            proposal_id=data["proposal_id"],
            created_at=data["created_at"],
        )


@dataclass(slots=True)
class PolicyDecision:
    proposal_id: str
    decision: Decision
    reason: str
    decided_by: str = "arc-policy"
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyDecision":
        return cls(
            proposal_id=data["proposal_id"],
            decision=Decision(data["decision"]),
            reason=data["reason"],
            decided_by=data.get("decided_by", "arc-policy"),
            created_at=data["created_at"],
        )


@dataclass(slots=True)
class Receipt:
    proposal_id: str
    success: bool
    outputs: Dict[str, Any]
    validator_results: List[Dict[str, Any]]
    receipt_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Receipt":
        return cls(
            proposal_id=data["proposal_id"],
            success=bool(data["success"]),
            outputs=dict(data["outputs"]),
            validator_results=list(data["validator_results"]),
            receipt_id=data["receipt_id"],
            created_at=data["created_at"],
        )


@dataclass(slots=True)
class BranchCandidate:
    branch_id: str
    title: str
    proposal: Dict[str, Any]
    score: float
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
