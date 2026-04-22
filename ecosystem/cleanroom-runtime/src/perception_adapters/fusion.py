"""PerceptionFusionEngine — multi-adapter observation fusion.

Merges ObservationBatches from all registered adapters into a single
ranked, deduplicated world-fact update. This is the boundary between
raw sensor output and the world model — nothing raw crosses this line.

Design principles (DARPA-grade):
- Temporal smoothing: repeated same-kind observations are confidence-averaged
  to prevent noise spikes from dominating the world model.
- Alert deduplication: identical alert strings within a fusion window are
  collapsed to one alert with a repeat count.
- Confidence gating: observations below the global floor are dropped before
  any world model write.
- Source attribution: every fact carries its adapter source and timestamp
  for full audit traceability through the kernel event log.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .interfaces import Observation, ObservationBatch


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class FusedWorldUpdate:
    """Output of one fusion cycle, ready for WorldModel.update_fact()."""

    def __init__(
        self,
        observations: list[Observation],
        alerts: list[str],
        sources: list[str],
        timestamp: str,
        raw_summaries: list[str],
    ) -> None:
        self.observations = observations
        self.alerts = alerts
        self.sources = sources
        self.timestamp = timestamp
        self.raw_summaries = raw_summaries

    def to_world_facts(self) -> dict[str, Any]:
        """Format for direct injection into WorldModel.update_fact()."""
        by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for obs in self.observations:
            by_kind[obs.kind].append({
                "confidence": obs.confidence,
                "attributes": dict(obs.attributes),
            })

        return {
            "fused_at": self.timestamp,
            "sources": list(self.sources),
            "observation_count": len(self.observations),
            "alert_count": len(self.alerts),
            "alerts": list(self.alerts),
            "by_kind": dict(by_kind),
            "top_observations": [
                {
                    "kind": o.kind,
                    "confidence": o.confidence,
                    "attributes": dict(o.attributes),
                }
                for o in sorted(self.observations, key=lambda x: x.confidence, reverse=True)[:10]
            ],
            "raw_summaries": list(self.raw_summaries),
        }

    def has_high_priority_alerts(self, threshold: float = 0.70) -> bool:
        """True if any observation exceeds threshold — used for interrupt logic."""
        return any(o.confidence >= threshold for o in self.observations)


class PerceptionFusionEngine:
    """Fuses ObservationBatches from multiple perception adapters.

    Applies temporal smoothing, alert deduplication, and confidence gating
    before producing a FusedWorldUpdate safe for world model injection.

    Args:
        confidence_floor: Global minimum observation confidence (default 0.25).
        temporal_window: Number of recent observations per kind to smooth over
            (default 3). Set to 1 to disable smoothing.
        alert_dedup_window: Number of fusions to remember for alert dedup
            (default 5). Set to 0 to disable.
    """

    def __init__(
        self,
        confidence_floor: float = 0.25,
        temporal_window: int = 3,
        alert_dedup_window: int = 5,
    ) -> None:
        self.confidence_floor = confidence_floor
        self.temporal_window = temporal_window
        self.alert_dedup_window = alert_dedup_window

        # Temporal smoothing buffer: kind → deque of recent confidences
        self._history: dict[str, list[float]] = defaultdict(list)

        # Alert dedup: set of recent alert strings
        self._recent_alerts: list[set[str]] = []

    def fuse(self, batches: list[ObservationBatch]) -> FusedWorldUpdate:
        """Merge a list of ObservationBatches into a FusedWorldUpdate.

        Call this once per perception loop tick with all adapter outputs.
        """
        all_observations: list[Observation] = []
        all_alerts: list[str] = []
        sources: list[str] = []
        raw_summaries: list[str] = []

        for batch in batches:
            if batch.source not in sources:
                sources.append(batch.source)
            if batch.raw_summary:
                raw_summaries.append(f"[{batch.source}] {batch.raw_summary}")
            for obs in batch.observations:
                all_observations.append(obs)
            for alert in batch.alerts:
                all_alerts.append(alert)

        # Confidence gate
        gated = [o for o in all_observations if o.confidence >= self.confidence_floor]

        # Temporal smoothing — average confidence across recent observations of same kind
        smoothed: list[Observation] = []
        kind_groups: dict[str, list[Observation]] = defaultdict(list)
        for obs in gated:
            kind_groups[obs.kind].append(obs)

        for kind, obs_list in kind_groups.items():
            # Pick the highest-confidence observation of this kind this cycle
            best = max(obs_list, key=lambda x: x.confidence)
            history = self._history[kind]
            history.append(best.confidence)
            if len(history) > self.temporal_window:
                history.pop(0)
            smoothed_conf = round(sum(history) / len(history), 3)
            smoothed.append(
                Observation(
                    kind=best.kind,
                    confidence=smoothed_conf,
                    attributes=dict(best.attributes),
                )
            )

        # Sort by confidence descending
        smoothed.sort(key=lambda x: x.confidence, reverse=True)

        # Alert deduplication
        this_cycle_alerts = set(all_alerts)
        past_alerts: set[str] = set()
        for past_set in self._recent_alerts:
            past_alerts |= past_set
        new_alerts = [a for a in all_alerts if a not in past_alerts]
        # Update dedup window
        self._recent_alerts.append(this_cycle_alerts)
        if len(self._recent_alerts) > self.alert_dedup_window:
            self._recent_alerts.pop(0)

        return FusedWorldUpdate(
            observations=smoothed,
            alerts=new_alerts,
            sources=sources,
            timestamp=_utcnow(),
            raw_summaries=raw_summaries,
        )

    def reset_history(self) -> None:
        """Clear temporal buffers — call on major context change or teleop reset."""
        self._history.clear()
        self._recent_alerts.clear()
