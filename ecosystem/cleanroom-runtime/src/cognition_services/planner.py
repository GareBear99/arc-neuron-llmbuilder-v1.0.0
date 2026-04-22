from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from arc_kernel.schemas import Proposal
from model_services.interfaces import PlannerModel


@dataclass(slots=True)
class PlanStep:
    title: str
    detail: str
    branch_score: float


class PlannerService:
    def __init__(self, model: PlannerModel | None = None) -> None:
        self.model = model

    def build_plan(self, proposal: Proposal, branch_candidates: list[dict[str, Any]]) -> dict[str, Any]:
        summary = f"Plan for {proposal.action} with {len(branch_candidates)} candidate branches."
        steps = [
            {"title": "Inspect proposal", "detail": proposal.rationale, "branch_score": max((c.get('score', 0.0) for c in branch_candidates), default=0.0)},
            {"title": "Select branch", "detail": "Prefer highest-scoring safe branch first.", "branch_score": max((c.get('score', 0.0) for c in branch_candidates), default=0.0)},
            {"title": "Validate execution", "detail": "Run validators and capture receipt.", "branch_score": 1.0},
        ]
        if self.model is not None:
            summary = self.model.generate(summary, context={"proposal": proposal.to_dict(), "branches": branch_candidates})
        return {"summary": summary, "steps": steps}
