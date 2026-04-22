from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ShadowExecutionResult:
    predicted_status: str
    actual_status: str
    status_match: bool
    predicted_result_keys: list[str]
    actual_result_keys: list[str]
    missing_predicted_keys: list[str]
    unexpected_result_keys: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            'predicted_status': self.predicted_status,
            'actual_status': self.actual_status,
            'status_match': self.status_match,
            'predicted_result_keys': self.predicted_result_keys,
            'actual_result_keys': self.actual_result_keys,
            'missing_predicted_keys': self.missing_predicted_keys,
            'unexpected_result_keys': self.unexpected_result_keys,
            'confidence': self.confidence,
        }


class ShadowExecutionService:
    def compare(self, predicted: dict[str, Any], actual: dict[str, Any]) -> ShadowExecutionResult:
        predicted_status = str(predicted.get('status', 'unknown'))
        actual_status = str(actual.get('status', 'unknown'))
        predicted_keys = sorted(predicted.keys())
        actual_keys = sorted(actual.keys())
        predicted_set = set(predicted_keys)
        actual_set = set(actual_keys)
        missing = sorted(predicted_set - actual_set)
        unexpected = sorted(actual_set - predicted_set)
        status_match = predicted_status == actual_status
        key_overlap = len(predicted_set & actual_set)
        denom = max(len(predicted_set | actual_set), 1)
        overlap_score = key_overlap / denom
        confidence = round((0.7 if status_match else 0.0) + (0.3 * overlap_score), 3)
        return ShadowExecutionResult(
            predicted_status=predicted_status,
            actual_status=actual_status,
            status_match=status_match,
            predicted_result_keys=predicted_keys,
            actual_result_keys=actual_keys,
            missing_predicted_keys=missing,
            unexpected_result_keys=unexpected,
            confidence=confidence,
        )
