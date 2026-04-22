from __future__ import annotations

"""Fallback selection chooses the next allowed degraded mode for the active task."""

from .failure_classifier import FailureInfo
from .fallback_policy import FallbackPolicy
from .retry_budget import RetryBudget


class FallbackSelector:
    def __init__(self, policy: FallbackPolicy | None = None, retry_budget: RetryBudget | None = None) -> None:
        self.policy = policy or FallbackPolicy()
        self.retry_budget = retry_budget or RetryBudget()

    def choose(self, failure: FailureInfo, task_kind: str) -> str | None:
        for option in self.policy.options_for(failure.classification, task_kind):
            key = f'{task_kind}:{option}'
            if self.retry_budget.allow(key):
                return option
        return None
