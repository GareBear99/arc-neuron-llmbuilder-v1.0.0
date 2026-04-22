from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

from .schemas import Proposal, RiskLevel


@dataclass(slots=True)
class BudgetPolicy:
    max_file_bytes_write: int = 100_000
    max_shell_commands_per_session: int = 10
    max_high_risk_approvals_per_session: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BudgetManager:
    def __init__(self, policy: BudgetPolicy | None = None) -> None:
        self.policy = policy or BudgetPolicy()

    def assess(self, proposal: Proposal, state) -> tuple[bool, str | None]:
        if proposal.action == "write_file":
            size = len((proposal.params.get("content") or "").encode("utf-8"))
            if size > self.policy.max_file_bytes_write:
                return False, f"Write exceeds max allowed bytes ({self.policy.max_file_bytes_write})."
        if proposal.action == "shell_command":
            shell_count = sum(1 for execution in getattr(state, "executions", []) if execution.get("action") == "shell_command")
            if shell_count >= self.policy.max_shell_commands_per_session:
                return False, f"Shell command budget exceeded ({self.policy.max_shell_commands_per_session})."
        if proposal.capability.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            proposal_risks = {
                proposal_item.get("proposal_id"): ((proposal_item.get("capability") or {}).get("risk"))
                for proposal_item in getattr(state, "proposals", [])
            }
            approvals = 0
            for decision in getattr(state, "policy_decisions", []):
                if decision.get("decision") != "approve":
                    continue
                decided_proposal_id = decision.get("proposal_id")
                if proposal_risks.get(decided_proposal_id) in {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}:
                    approvals += 1
            if approvals >= self.policy.max_high_risk_approvals_per_session:
                return False, f"High-risk approval budget exceeded ({self.policy.max_high_risk_approvals_per_session})."
        return True, None
