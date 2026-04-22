from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldModel:
    facts: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    def update_fact(self, key: str, value: Any) -> None:
        self.facts[key] = value
        self.history.append({"key": key, "value": value})

    def snapshot(self) -> dict[str, Any]:
        return {"facts": dict(self.facts), "history": list(self.history)}
