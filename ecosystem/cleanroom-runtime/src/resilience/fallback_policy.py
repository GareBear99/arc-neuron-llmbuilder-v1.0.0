from __future__ import annotations

"""Fallback policy defines legal downgrade chains for each failure class."""

from .failure_classifier import FailureClass


class FallbackPolicy:
    def options_for(self, failure: FailureClass, task_kind: str) -> list[str]:
        if task_kind == 'model_prompt':
            if failure in {FailureClass.MODEL_TIMEOUT, FailureClass.MODEL_UNAVAILABLE, FailureClass.UNKNOWN}:
                return ['deterministic_router', 'echo_stub', 'retry_smaller_model_request']
            if failure == FailureClass.MODEL_INTERRUPTED:
                return ['partial_receipt']
        if task_kind == 'code_patch':
            if failure in {FailureClass.PATCH_ANCHOR_MISSING, FailureClass.PATCH_VERIFY_FAILED, FailureClass.UNKNOWN}:
                return ['suffix_symbol_match', 'line_range_retry', 'scaffold_manual_fix']
        return ['partial_receipt']
