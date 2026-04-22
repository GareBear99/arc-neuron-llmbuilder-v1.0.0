from __future__ import annotations

from typing import Any


class EvaluatorService:
    def evaluate(self, proposal_id: str, validators: list[dict[str, Any]], result: dict[str, Any]) -> dict[str, Any]:
        passed = sum(1 for item in validators if item.get("passed"))
        total = len(validators)
        score = round((passed / total), 3) if total else 0.0
        return {
            "proposal_id": proposal_id,
            "validator_pass_rate": score,
            "all_validators_passed": passed == total,
            "result_keys": sorted(result.keys()),
        }
