from __future__ import annotations

from pathlib import Path
from typing import Optional

from .branching import BranchPlanner
from .event_log import EventLog
from .policy import PolicyEngine
from .state import StateProjector
from .schemas import Event, EventKind, Proposal, PolicyDecision, Receipt, BranchCandidate, Decision


class KernelEngine:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.log = EventLog(db_path=db_path)
        self.policy = PolicyEngine()
        self.projector = StateProjector()
        self.branches = BranchPlanner()

    def record_input(self, actor: str, payload: dict) -> Event:
        return self.log.append(Event(kind=EventKind.INPUT, actor=actor, payload=payload))

    def record_proposal(self, actor: str, proposal: Proposal, parent_event_id: str | None = None) -> Event:
        return self.log.append(
            Event(kind=EventKind.PROPOSAL, actor=actor, payload=proposal.to_dict(), parent_event_id=parent_event_id)
        )

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        event = self.log.find_latest(EventKind.PROPOSAL, "proposal_id", proposal_id)
        if not event:
            return None
        return Proposal.from_dict(event.payload)

    def plan_branches(self, actor: str, proposal: Proposal, parent_event_id: str | None = None) -> list[BranchCandidate]:
        candidates = self.branches.plan(proposal)
        self.log.append(
            Event(
                kind=EventKind.BRANCH_PLAN,
                actor=actor,
                payload={"proposal_id": proposal.proposal_id, "candidates": [c.to_dict() for c in candidates]},
                parent_event_id=parent_event_id,
            )
        )
        return candidates

    def get_branch_plan(self, proposal_id: str) -> list[BranchCandidate]:
        event = self.log.find_latest(EventKind.BRANCH_PLAN, "proposal_id", proposal_id)
        if not event:
            return []
        return [BranchCandidate(**candidate) for candidate in event.payload.get("candidates", [])]

    def evaluate_proposal(self, actor: str, proposal: Proposal, parent_event_id: str | None = None) -> PolicyDecision:
        state = self.projector.project(self.log.all())
        decision = self.policy.evaluate(proposal, state=state)
        self.log.append(
            Event(kind=EventKind.POLICY_DECISION, actor=actor, payload=decision.to_dict(), parent_event_id=parent_event_id)
        )
        return decision

    def force_decision(
        self,
        actor: str,
        proposal_id: str,
        decision: Decision,
        reason: str,
        parent_event_id: str | None = None,
    ) -> PolicyDecision:
        override = PolicyDecision(proposal_id=proposal_id, decision=decision, reason=reason, decided_by=actor)
        self.log.append(
            Event(kind=EventKind.POLICY_DECISION, actor=actor, payload=override.to_dict(), parent_event_id=parent_event_id)
        )
        return override

    def latest_decision(self, proposal_id: str) -> Optional[PolicyDecision]:
        event = self.log.find_latest(EventKind.POLICY_DECISION, "proposal_id", proposal_id)
        if not event:
            return None
        return PolicyDecision.from_dict(event.payload)


    def record_evaluation(self, actor: str, payload: dict, parent_event_id: str | None = None) -> Event:
        return self.log.append(
            Event(kind=EventKind.EVALUATION, actor=actor, payload=payload, parent_event_id=parent_event_id)
        )

    def record_execution(self, actor: str, payload: dict, parent_event_id: str | None = None) -> Event:
        return self.log.append(
            Event(kind=EventKind.EXECUTION, actor=actor, payload=payload, parent_event_id=parent_event_id)
        )

    def record_memory_update(self, actor: str, payload: dict, parent_event_id: str | None = None) -> Event:
        return self.log.append(
            Event(kind=EventKind.MEMORY_UPDATE, actor=actor, payload=payload, parent_event_id=parent_event_id)
        )

    def record_receipt(self, actor: str, receipt: Receipt, parent_event_id: str | None = None) -> Event:
        return self.log.append(
            Event(kind=EventKind.RECEIPT, actor=actor, payload=receipt.to_dict(), parent_event_id=parent_event_id)
        )

    def latest_receipt(self, proposal_id: str) -> Optional[Receipt]:
        event = self.log.find_latest(EventKind.RECEIPT, "proposal_id", proposal_id)
        if not event:
            return None
        return Receipt.from_dict(event.payload)

    def state(self):
        return self.projector.project(self.log.all())

    def state_at(self, event_id: str):
        return self.projector.project(self.log.slice_until(event_id))


    @property
    def db_path(self) -> Path | None:
        return self.log.db_path

    def export_events_jsonl(self, output_path: str | Path) -> Path:
        return self.log.export_jsonl(output_path)

    def import_events_jsonl(self, input_path: str | Path) -> int:
        return self.log.import_jsonl(input_path)

    def backup_sqlite(self, output_path: str | Path) -> Path:
        return self.log.backup_sqlite(output_path)

    def compact(self) -> dict:
        before = self.log.stats()
        self.log.vacuum()
        after = self.log.stats()
        return {'before': before, 'after': after}

    def stats(self) -> dict:
        return self.log.stats()

    def close(self) -> None:
        self.log.close()
