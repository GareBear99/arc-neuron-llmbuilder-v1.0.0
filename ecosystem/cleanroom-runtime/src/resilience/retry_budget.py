from __future__ import annotations

"""Retry budgets prevent infinite fallback loops during degraded execution."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class RetryBudget:
    max_attempts: int = 3
    attempts_by_key: dict[str, int] = field(default_factory=dict)

    def allow(self, key: str) -> bool:
        attempts = self.attempts_by_key.get(key, 0)
        if attempts >= self.max_attempts:
            return False
        self.attempts_by_key[key] = attempts + 1
        return True

    def remaining(self, key: str) -> int:
        return max(0, self.max_attempts - self.attempts_by_key.get(key, 0))
