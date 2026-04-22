from __future__ import annotations

from .schemas import BranchCandidate, Proposal, RiskLevel


class BranchPlanner:
    def plan(self, proposal: Proposal) -> list[BranchCandidate]:
        base = proposal.action.replace('_', ' ').title()
        dry_score = 0.95 if proposal.capability.risk in {RiskLevel.MEDIUM, RiskLevel.HIGH} else 0.75
        exec_score = 0.8 if proposal.capability.risk == RiskLevel.LOW else 0.6
        branches = [
            BranchCandidate(
                branch_id=f"{proposal.proposal_id}:dryrun",
                title=f"{base} (Dry Run)",
                proposal={**proposal.to_dict(), "params": {**proposal.params, "dry_run": True}},
                score=dry_score,
                reasoning="Prefer observable, non-destructive path first.",
            ),
            BranchCandidate(
                branch_id=f"{proposal.proposal_id}:execute",
                title=f"{base} (Execute)",
                proposal=proposal.to_dict(),
                score=exec_score,
                reasoning="Proceed directly when policy permits and operator confirms.",
            ),
        ]
        return sorted(branches, key=lambda b: b.score, reverse=True)
