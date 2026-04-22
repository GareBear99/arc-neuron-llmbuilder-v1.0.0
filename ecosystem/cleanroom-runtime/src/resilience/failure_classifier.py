from __future__ import annotations

"""Failure classification turns raw exceptions/results into stable recovery categories."""

from dataclasses import dataclass
from enum import Enum


class FailureClass(str, Enum):
    MODEL_UNAVAILABLE = 'model_unavailable'
    MODEL_INTERRUPTED = 'model_interrupted'
    MODEL_TIMEOUT = 'model_timeout'
    PATCH_ANCHOR_MISSING = 'patch_anchor_missing'
    PATCH_VERIFY_FAILED = 'patch_verify_failed'
    VALIDATION_FAILED = 'validation_failed'
    UNKNOWN = 'unknown'


@dataclass(slots=True)
class FailureInfo:
    classification: FailureClass
    reason: str
    retryable: bool = True

    def to_dict(self) -> dict[str, object]:
        return {'classification': self.classification.value, 'reason': self.reason, 'retryable': self.retryable}


class FailureClassifier:
    """Maps exceptions and failed results into recovery-oriented categories."""

    def classify_exception(self, exc: Exception) -> FailureInfo:
        message = str(exc)
        lowered = message.lower()
        if isinstance(exc, KeyboardInterrupt):
            return FailureInfo(FailureClass.MODEL_INTERRUPTED, 'Operator interrupted local generation.', retryable=False)
        if 'symbol not found' in lowered or 'hash mismatch' in lowered:
            return FailureInfo(FailureClass.PATCH_ANCHOR_MISSING, message, retryable=True)
        if 'timeout' in lowered:
            return FailureInfo(FailureClass.MODEL_TIMEOUT, message, retryable=True)
        if 'connection' in lowered or 'refused' in lowered or 'unavailable' in lowered:
            return FailureInfo(FailureClass.MODEL_UNAVAILABLE, message, retryable=True)
        return FailureInfo(FailureClass.UNKNOWN, message, retryable=True)

    def classify_patch_result(self, result: dict[str, object]) -> FailureInfo | None:
        if bool(result.get('success')):
            return None
        verification = result.get('verification', {}) or {}
        checks = verification.get('checks', []) or []
        if any(not bool(c.get('passed')) for c in checks):
            return FailureInfo(FailureClass.PATCH_VERIFY_FAILED, result.get('message', 'Patch verification failed.'), retryable=True)
        return FailureInfo(FailureClass.UNKNOWN, result.get('message', 'Patch failed.'), retryable=True)
