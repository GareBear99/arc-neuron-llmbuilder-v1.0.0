from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .interfaces import ActionAdapter, OptionalAdapterConfig, PerceptionAdapter


@dataclass
class AdapterRegistry:
    """Tracks optional adapters without imposing any hard dependency chain."""

    perception: dict[str, PerceptionAdapter] = field(default_factory=dict)
    action: dict[str, ActionAdapter] = field(default_factory=dict)
    configs: dict[str, OptionalAdapterConfig] = field(default_factory=dict)

    def register_perception(
        self,
        name: str,
        adapter: PerceptionAdapter,
        config: OptionalAdapterConfig | None = None,
    ) -> None:
        self.perception[name] = adapter
        self.configs[name] = config or OptionalAdapterConfig(enabled=True, mode="perception")

    def register_action(
        self,
        name: str,
        adapter: ActionAdapter,
        config: OptionalAdapterConfig | None = None,
    ) -> None:
        self.action[name] = adapter
        self.configs[name] = config or OptionalAdapterConfig(enabled=True, mode="action")

    def describe(self) -> dict[str, Any]:
        return {
            "perception": {name: adapter.describe() for name, adapter in self.perception.items()},
            "action": {name: adapter.describe() for name, adapter in self.action.items()},
            "configs": {
                name: {
                    "enabled": cfg.enabled,
                    "mode": cfg.mode,
                    "options": dict(cfg.options),
                }
                for name, cfg in self.configs.items()
            },
        }
