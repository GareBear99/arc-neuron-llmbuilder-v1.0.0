from __future__ import annotations

from .budgets import BudgetManager
from .schemas import Decision, PolicyDecision, Proposal, RiskLevel


class PolicyEngine:
    def __init__(self, budgets: BudgetManager | None = None) -> None:
        self.budgets = budgets or BudgetManager()

    def evaluate(self, proposal: Proposal, state=None) -> PolicyDecision:
        risk = proposal.capability.risk
        if proposal.action == "unknown":
            return PolicyDecision(proposal.proposal_id, Decision.DENY, "Unknown intent cannot be executed.")
        if risk == RiskLevel.CRITICAL:
            return PolicyDecision(proposal.proposal_id, Decision.DENY, "Critical-risk actions are denied by default.")
        if state is not None:
            allowed, reason = self.budgets.assess(proposal, state)
            if not allowed:
                return PolicyDecision(proposal.proposal_id, Decision.DENY, reason or "Budget policy denied action.")
        if proposal.capability.requires_confirmation or risk == RiskLevel.HIGH:
            return PolicyDecision(proposal.proposal_id, Decision.REQUIRE_CONFIRMATION, "High-risk action requires human confirmation.")
        return PolicyDecision(proposal.proposal_id, Decision.APPROVE, "Action approved under current policy.")
