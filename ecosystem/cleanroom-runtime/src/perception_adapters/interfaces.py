from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SensorPacket:
    """Normalized sensor input passed into optional perception services.

    The runtime keeps these packets generic on purpose so camera, audio,
    simulator, or desktop-capture inputs can be attached without changing the
    deterministic shell contract.
    """

    source: str
    modality: str
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    """A structured fact emitted by an optional adapter."""

    kind: str
    confidence: float
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservationBatch:
    """Structured perception output safe to feed into world-state logic."""

    source: str
    timestamp: str
    observations: tuple[Observation, ...] = ()
    alerts: tuple[str, ...] = ()
    raw_summary: str = ""

    def to_world_facts(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "timestamp": self.timestamp,
            "observation_count": len(self.observations),
            "alerts": list(self.alerts),
            "observations": [
                {
                    "kind": item.kind,
                    "confidence": item.confidence,
                    "attributes": dict(item.attributes),
                }
                for item in self.observations
            ],
            "raw_summary": self.raw_summary,
        }


@dataclass(frozen=True)
class OptionalAdapterConfig:
    """Declares optional capabilities without making them mandatory.

    This lets the runtime advertise a clean contract: perception and robotics
    are extension points, not required installation surfaces.
    """

    enabled: bool = False
    mode: str = "disabled"
    options: dict[str, Any] = field(default_factory=dict)


class PerceptionAdapter(Protocol):
    """Turn raw sensor packets into structured observations."""

    def describe(self) -> dict[str, Any]: ...

    def process(self, packet: SensorPacket) -> ObservationBatch: ...


class ActionAdapter(Protocol):
    """Execute a bounded action against an optional embodiment layer."""

    def describe(self) -> dict[str, Any]: ...

    def perform(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...
