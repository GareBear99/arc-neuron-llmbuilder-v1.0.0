"""FallbackConsciousnessLayer — the system's awareness of its own degraded state.

This is the piece that makes fallback "conscious" rather than silent.

When the CognitionCore switches tiers, this layer:

1. KNOWS  — tracks the current tier, duration in fallback, frequency of drops
2. SAYS   — builds a system prompt prefix that tells the model exactly what
             tier it's on, what capabilities it has, and why it degraded
3. SHOWS  — writes the degraded state into WorldModel so GoalEngine can see it
4. LEARNS — feeds every fallback event into FixNet and the self_improve planner
             with root-cause analysis, so the system can improve its reliability
5. RECOVERS — when a tier recovers, records the recovery as a positive outcome
               and adjusts the improvement backlog

The prefix injected into prompts looks like this when degraded:

    [COGNITION STATE: tier=local | depth=2 | degraded for 47s]
    Primary model unavailable (connection refused). Running on local echo stub.
    Capabilities in this mode: echo, deterministic_router.
    I will flag any response that requires capabilities I currently lack.
    Recovery probe running — will restore primary tier automatically.

The model (whatever it is) sees this prefix and can reason from it.
The operator sees tier-switch events in the stream.
The kernel event log has the full audit trail.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .cognition_core import CognitionCore, TierChangeEvent, TIER_PRIMARY, TIER_ORDER


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FallbackEpisode:
    """One continuous period spent below the primary tier."""
    from_tier: str
    to_tier: str
    reason: str
    started_at: str
    ended_at: str | None = None
    recovered_to_tier: str | None = None
    duration_s: float | None = None
    improvement_goal_generated: bool = False

    def close(self, recovered_to: str) -> None:
        now = datetime.now(timezone.utc)
        self.ended_at = now.isoformat()
        self.recovered_to_tier = recovered_to
        start = datetime.fromisoformat(self.started_at)
        self.duration_s = round((now - start).total_seconds(), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_tier": self.from_tier,
            "to_tier": self.to_tier,
            "reason": self.reason,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "recovered_to_tier": self.recovered_to_tier,
            "duration_s": self.duration_s,
            "improvement_goal_generated": self.improvement_goal_generated,
        }


class FallbackConsciousnessLayer:
    """Wraps CognitionCore to add self-awareness about degraded state.

    Usage::

        core = CognitionCore()
        core.add_tier(TIER_PRIMARY, my_backend)
        consciousness = FallbackConsciousnessLayer(core)
        consciousness.wire(runtime=runtime, world_model=world_model)
        core.on_tier_change = consciousness.on_tier_change

        # Now every prompt goes through the consciousness layer:
        prompt = consciousness.build_prefix()
        for event in core.stream(user_prompt, consciousness_prefix=prompt):
            ...

    Args:
        core: The CognitionCore to monitor.
        max_episode_history: How many FallbackEpisodes to keep (default 50).
        improvement_cooldown_s: Minimum seconds between improvement goal
            generation events (prevents spam during rapid flapping, default 30).
    """

    def __init__(
        self,
        core: CognitionCore,
        *,
        max_episode_history: int = 50,
        improvement_cooldown_s: float = 30.0,
    ) -> None:
        self.core = core
        self.max_episode_history = max_episode_history
        self.improvement_cooldown_s = improvement_cooldown_s

        self._episodes: list[FallbackEpisode] = []
        self._current_episode: FallbackEpisode | None = None
        self._degraded_since: float | None = None
        self._last_improvement_at: float = 0.0
        self._tier_change_count = 0
        self._total_fallback_duration_s: float = 0.0

        # Wired in after construction
        self._runtime: Any = None
        self._world_model: Any = None

    def wire(self, *, runtime: Any, world_model: Any) -> None:
        """Connect to the runtime and world model for events and world state."""
        self._runtime = runtime
        self._world_model = world_model

    # ── Tier-change handler (set as core.on_tier_change) ─────────────────────

    def on_tier_change(self, evt: TierChangeEvent) -> None:
        """Called synchronously by CognitionCore on every tier switch."""
        self._tier_change_count += 1
        now_mono = time.monotonic()

        if evt.direction == "degraded":
            self._degraded_since = now_mono
            episode = FallbackEpisode(
                from_tier=evt.from_tier,
                to_tier=evt.to_tier,
                reason=evt.reason,
                started_at=evt.timestamp,
            )
            self._current_episode = episode
            self._episodes.append(episode)
            if len(self._episodes) > self.max_episode_history:
                self._episodes.pop(0)

            self._write_world_model_degraded(evt)
            self._emit_kernel_event("cognition_degraded", evt.to_dict())
            self._maybe_generate_improvement_goal(evt)

        elif evt.direction == "recovered":
            if self._current_episode:
                self._current_episode.close(recovered_to=evt.to_tier)
                if self._current_episode.duration_s:
                    self._total_fallback_duration_s += self._current_episode.duration_s
                self._current_episode = None
            self._degraded_since = None

            self._write_world_model_recovered(evt)
            self._emit_kernel_event("cognition_recovered", evt.to_dict())
            self._record_recovery_trust(evt)

    # ── Prefix builder ────────────────────────────────────────────────────────

    def build_prefix(self) -> str | None:
        """Build the consciousness prefix to inject into the next prompt.

        Returns None when at primary tier (no prefix needed).
        Returns a descriptive prefix when degraded.
        """
        if not self.core.is_degraded:
            return None

        tier = self.core.active_tier
        depth = self.core.degradation_depth
        caps = self.core.active_capabilities()
        caps_str = ", ".join(caps) if caps else "none"

        degraded_for = ""
        if self._degraded_since is not None:
            secs = round(time.monotonic() - self._degraded_since)
            degraded_for = f" | degraded for {secs}s"

        reason = ""
        if self._current_episode:
            reason = f"\nReason for degradation: {self._current_episode.reason}"

        return (
            f"[COGNITION STATE: tier={tier} | depth={depth}/3{degraded_for}]\n"
            f"Primary model unavailable.{reason}\n"
            f"Running on tier '{tier}'. Capabilities in this mode: {caps_str}.\n"
            f"Flag any response that requires capabilities currently unavailable.\n"
            f"Recovery probe is active — primary tier will be restored automatically."
        )

    # ── Status ────────────────────────────────────────────────────────────────

    def is_degraded(self) -> bool:
        return self.core.is_degraded

    def fallback_stats(self) -> dict[str, Any]:
        recent = [e.to_dict() for e in self._episodes[-10:]]
        current = self._current_episode.to_dict() if self._current_episode else None
        degraded_for_s = None
        if self._degraded_since is not None:
            degraded_for_s = round(time.monotonic() - self._degraded_since, 1)
        return {
            "is_degraded": self.is_degraded(),
            "active_tier": self.core.active_tier,
            "degradation_depth": self.core.degradation_depth,
            "degraded_for_s": degraded_for_s,
            "tier_change_count": self._tier_change_count,
            "episode_count": len(self._episodes),
            "total_fallback_duration_s": round(self._total_fallback_duration_s, 2),
            "current_episode": current,
            "recent_episodes": recent,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _write_world_model_degraded(self, evt: TierChangeEvent) -> None:
        if not self._world_model:
            return
        self._world_model.update_fact("cognition_tier", evt.to_tier)
        self._world_model.update_fact("cognition_is_degraded", True)
        self._world_model.update_fact("cognition_degradation_reason", evt.reason)
        self._world_model.update_fact("cognition_degraded_since", evt.timestamp)
        self._world_model.update_fact("cognition_active_capabilities", self.core.active_capabilities())

    def _write_world_model_recovered(self, evt: TierChangeEvent) -> None:
        if not self._world_model:
            return
        self._world_model.update_fact("cognition_tier", evt.to_tier)
        self._world_model.update_fact("cognition_is_degraded", False)
        self._world_model.update_fact("cognition_degradation_reason", None)
        self._world_model.update_fact("cognition_degraded_since", None)
        self._world_model.update_fact("cognition_recovered_at", evt.timestamp)
        self._world_model.update_fact("cognition_active_capabilities", self.core.active_capabilities())

    def _emit_kernel_event(self, kind: str, payload: dict[str, Any]) -> None:
        if not self._runtime:
            return
        kernel = getattr(self._runtime, "kernel", None)
        if not kernel:
            return
        try:
            kernel.record_evaluation("cognition_consciousness", {"kind": kind, **payload})
        except Exception:
            pass

    def _maybe_generate_improvement_goal(self, evt: TierChangeEvent) -> None:
        """Feed fallback event into self-improve and fixnet — the learning loop."""
        now = time.monotonic()
        if now - self._last_improvement_at < self.improvement_cooldown_s:
            return
        self._last_improvement_at = now

        if not self._runtime:
            return

        # 1. Record to FixNet — pattern-match against known failure signatures
        try:
            fix_result = self._runtime.fixnet_register(
                title=f"Cognition fallback: {evt.from_tier} → {evt.to_tier}",
                error_type="cognition_tier_degradation",
                error_signature=f"tier:{evt.from_tier}|reason:{evt.reason[:80]}",
                solution=(
                    f"Investigate why tier '{evt.from_tier}' became unavailable. "
                    f"Common causes: model process crashed, port conflict, model path wrong, "
                    f"OOM. Check continuity logs and restart primary backend."
                ),
                summary=f"System fell back from {evt.from_tier} to {evt.to_tier}: {evt.reason}",
                keywords=["fallback", "cognition", evt.from_tier, evt.to_tier],
                context={"tier_change": evt.to_dict(), "stats": self.fallback_stats()},
                evidence={"tier_change_count": self._tier_change_count},
                auto_embed=True,
            )
        except Exception:
            fix_result = {}

        # 2. Record curriculum — the system learns that this failure class occurred
        try:
            self._runtime.record_curriculum(
                theme="cognition_reliability",
                skill=f"tier_{evt.from_tier}_availability",
                failure_cluster="tier_degradation",
                outcome="failure",
                notes=f"fell back to {evt.to_tier}: {evt.reason[:120]}",
            )
        except Exception:
            pass

        # 3. Record trust outcome for the failed tier's backend
        try:
            self._runtime.record_tool_outcome(
                f"cognition_tier_{evt.from_tier}",
                succeeded=False,
                notes=evt.reason,
                evidence={"tier_change": evt.to_dict()},
            )
        except Exception:
            pass

        # 4. Inject a high-priority self-improvement goal into GoalEngine
        try:
            self._runtime.goals.add_goal(
                f"restore primary cognition tier — currently degraded to {evt.to_tier}",
                priority=95,
                completion_criteria=[f"tier '{evt.from_tier}' returns to healthy status"],
                constraints=["do not disrupt active streaming sessions"],
                abort_conditions=["operator cancels recovery goal"],
                compile=False,
            )
        except Exception:
            pass

        if self._current_episode:
            self._current_episode.improvement_goal_generated = True

    def _record_recovery_trust(self, evt: TierChangeEvent) -> None:
        if not self._runtime:
            return
        try:
            self._runtime.record_tool_outcome(
                f"cognition_tier_{evt.to_tier}",
                succeeded=True,
                notes=f"tier recovered from {evt.from_tier}",
                evidence={"tier_change": evt.to_dict()},
            )
            self._runtime.record_curriculum(
                theme="cognition_reliability",
                skill=f"tier_{evt.to_tier}_availability",
                outcome="success",
                notes=f"recovered to {evt.to_tier} from {evt.from_tier}",
            )
        except Exception:
            pass
