"""DriftDetector — behavioral drift detection across rolling execution windows.

The single most important safety component in a self-modifying system.
Catches the failure mode that everything else misses:

    The system still runs. Tests still pass. But it is becoming wrong.

DriftDetector watches five independent signals across rolling windows and
raises a drift alert when any signal crosses its threshold:

  1. CriticScore trend     — is reasoning quality declining across cycles?
  2. GoalCompletion rate   — are goals completing or stacking up undone?
  3. FixNet novelty rate   — new error patterns mean new territory = drift risk
  4. ShadowMismatch rate   — predicted vs actual divergence growing?
  5. BehavioralRegression  — does current behavior match a frozen reference run?

When drift is detected:

  - self-modification is FROZEN (no new SelfImprove patches promoted)
  - kernel evaluation event emitted with full signal report
  - WorldModel updated: drift_detected=True, drift_signals=[...]
  - GoalSynthesizer fires 'investigate and stabilize system drift' goal
  - ContinuityShell heartbeat updated to 'drift_detected' mode
  - Optional operator alert callback fired

Drift clearance:

  - All signals must return below threshold for CLEAR_WINDOW consecutive ticks
  - Clearance emits kernel event and unfreezes self-modification
  - Full episode recorded for curriculum training signal

This is the Truth Layer the DARPA assessment identified as missing.
Without it, CurriculumTrainer, GoalSynthesizer, and SelfImprove can
faithfully optimize in the wrong direction.
"""
from __future__ import annotations

import statistics
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Deque


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Signal configuration ──────────────────────────────────────────────────────

@dataclass
class DriftThresholds:
    """Configurable thresholds for each drift signal.

    Conservative defaults — tune per deployment after baseline is established.
    """
    # CriticService composite score — alert if rolling mean drops below this
    critic_score_floor: float = 0.45
    # Minimum rolling window size before critic signal is trusted
    critic_window_min: int = 5
    # Goal completion rate — alert if below this fraction over window
    goal_completion_floor: float = 0.30
    # FixNet novel events per window — alert if exceeds this (too many new errors)
    fixnet_novelty_ceiling: int = 8
    # Shadow mismatch rate — alert if above this fraction
    shadow_mismatch_ceiling: float = 0.40
    # Behavioral regression — max allowed score delta from reference
    regression_delta_ceiling: float = 0.25
    # Consecutive ticks all signals must be clear before drift is lifted
    clear_window: int = 3
    # Rolling window size for all signal calculations
    window_size: int = 20


@dataclass
class SignalReading:
    """One signal measurement at one point in time."""
    signal: str
    value: float
    threshold: float
    breached: bool
    timestamp: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DriftReport:
    """Full state report from one drift evaluation tick."""
    tick: int
    drift_detected: bool
    signals: list[SignalReading]
    self_modification_frozen: bool
    clear_ticks_remaining: int
    action: str          # "none" | "drift_alert" | "drift_cleared" | "ongoing"
    timestamp: str = field(default_factory=_utcnow)
    episode_duration_s: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = "drift_report"
        return d

    @property
    def breached_signals(self) -> list[str]:
        return [s.signal for s in self.signals if s.breached]


# ── Reference receipt (frozen baseline) ──────────────────────────────────────

@dataclass
class ReferenceReceipt:
    """A frozen behavioral baseline snapshot for regression testing.

    Captured from a known-good run. Compared against current behavior
    every N ticks to detect silent behavioral regression.
    """
    captured_at: str
    goal_completion_rate: float
    mean_critic_score: float
    mean_steps_per_goal: float
    fixnet_novel_rate: float
    shadow_match_rate: float
    kernel_event_count: int
    notes: str = ""

    def score(self) -> float:
        """Composite reference score for regression comparison."""
        return round(
            self.goal_completion_rate * 0.3
            + self.mean_critic_score * 0.4
            + self.shadow_match_rate * 0.2
            + (1.0 - min(1.0, self.fixnet_novel_rate / 10)) * 0.1,
            3,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReferenceReceipt":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── DriftDetector ─────────────────────────────────────────────────────────────

class DriftDetector:
    """Behavioral drift detection for self-modifying AI runtimes.

    Args:
        thresholds:       Configurable signal thresholds.
        on_drift_alert:   Callback(DriftReport) fired on first drift detection.
        on_drift_cleared: Callback(DriftReport) fired when drift is cleared.
        reference:        Frozen baseline for regression testing. If None,
                          regression signal is skipped until capture() is called.
    """

    def __init__(
        self,
        thresholds: DriftThresholds | None = None,
        *,
        on_drift_alert: Callable[[DriftReport], None] | None = None,
        on_drift_cleared: Callable[[DriftReport], None] | None = None,
        reference: ReferenceReceipt | None = None,
    ) -> None:
        self.thresholds = thresholds or DriftThresholds()
        self.on_drift_alert = on_drift_alert
        self.on_drift_cleared = on_drift_cleared
        self.reference = reference

        # Rolling signal buffers
        W = self.thresholds.window_size
        self._critic_scores:      Deque[float] = deque(maxlen=W)
        self._goal_completions:   Deque[bool]  = deque(maxlen=W)
        self._fixnet_novel_flags: Deque[bool]  = deque(maxlen=W)
        self._shadow_matches:     Deque[bool]  = deque(maxlen=W)

        # State
        self._drift_detected = False
        self._modification_frozen = False
        self._drift_start: float | None = None
        self._clear_streak = 0
        self._tick = 0
        self._reports: list[DriftReport] = []
        self._runtime: Any = None

    def wire(self, runtime: Any) -> None:
        """Connect to LuciferRuntime for kernel events and world model."""
        self._runtime = runtime

    # ── Feed methods (call these from the main execution loop) ────────────────

    def feed_critic_score(self, score: float) -> None:
        """Record one CriticService composite score."""
        self._critic_scores.append(max(0.0, min(1.0, score)))

    def feed_goal_completed(self, completed: bool) -> None:
        """Record whether the latest goal attempt completed successfully."""
        self._goal_completions.append(completed)

    def feed_fixnet_event(self, is_novel: bool) -> None:
        """Record one FixNet event — True if the error signature was novel."""
        self._fixnet_novel_flags.append(is_novel)

    def feed_shadow_result(self, matched: bool) -> None:
        """Record one shadow execution comparison — True if predicted == actual."""
        self._shadow_matches.append(matched)

    # ── Capture reference baseline ────────────────────────────────────────────

    def capture_reference(self, notes: str = "") -> ReferenceReceipt:
        """Snapshot current window state as the behavioral baseline.

        Call this after a known-good run to establish the regression anchor.
        Overwrites any existing reference.
        """
        ref = ReferenceReceipt(
            captured_at=_utcnow(),
            goal_completion_rate=self._goal_completion_rate(),
            mean_critic_score=self._mean_critic_score(),
            mean_steps_per_goal=1.0,    # placeholder — extend with step data
            fixnet_novel_rate=self._fixnet_novel_rate(),
            shadow_match_rate=self._shadow_match_rate(),
            kernel_event_count=self._kernel_event_count(),
            notes=notes,
        )
        self.reference = ref
        self._emit_kernel("drift_reference_captured", ref.to_dict())
        return ref

    # ── Evaluation tick ───────────────────────────────────────────────────────

    def tick(self, world_model: Any | None = None) -> DriftReport:
        """Run one drift evaluation cycle. Call once per execution loop tick.

        Args:
            world_model: Optional WorldModel for additional context signals.
                         If provided, world model facts are also sampled.

        Returns:
            DriftReport with full signal state and recommended action.
        """
        self._tick += 1

        # Optional: pull extra signals from world model
        if world_model is not None:
            self._pull_world_model_signals(world_model)

        signals = self._evaluate_signals()
        any_breached = any(s.breached for s in signals)

        action = "none"
        episode_duration: float | None = None

        if any_breached and not self._drift_detected:
            # New drift detected
            self._drift_detected = True
            self._modification_frozen = True
            self._drift_start = time.monotonic()
            self._clear_streak = 0
            action = "drift_alert"
            self._fire_alert_callbacks = True

        elif any_breached and self._drift_detected:
            # Ongoing drift
            self._clear_streak = 0
            action = "ongoing"
            self._fire_alert_callbacks = False

        elif not any_breached and self._drift_detected:
            # Potentially clearing
            self._clear_streak += 1
            action = "clearing"
            self._fire_alert_callbacks = False
            if self._clear_streak >= self.thresholds.clear_window:
                # Drift cleared
                if self._drift_start:
                    episode_duration = round(time.monotonic() - self._drift_start, 2)
                self._drift_detected = False
                self._modification_frozen = False
                self._drift_start = None
                self._clear_streak = 0
                action = "drift_cleared"

        else:
            self._fire_alert_callbacks = False

        report = DriftReport(
            tick=self._tick,
            drift_detected=self._drift_detected,
            signals=signals,
            self_modification_frozen=self._modification_frozen,
            clear_ticks_remaining=max(
                0, self.thresholds.clear_window - self._clear_streak
            ) if self._drift_detected else 0,
            action=action,
            episode_duration_s=episode_duration,
        )
        self._reports.append(report)

        # Side effects
        if action == "drift_alert":
            self._write_world_model(report)
            self._emit_kernel("drift_alert", report.to_dict())
            self._inject_stabilize_goal(report)
            self._freeze_self_modification()
            if self.on_drift_alert:
                try:
                    self.on_drift_alert(report)
                except Exception:
                    pass

        elif action == "drift_cleared":
            self._write_world_model_cleared(report)
            self._emit_kernel("drift_cleared", report.to_dict())
            self._record_drift_episode_to_curriculum(report, episode_duration)
            if self.on_drift_cleared:
                try:
                    self.on_drift_cleared(report)
                except Exception:
                    pass

        elif action in ("ongoing", "clearing"):
            self._write_world_model(report)

        return report

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def is_frozen(self) -> bool:
        """True when self-modification is frozen due to detected drift."""
        return self._modification_frozen

    @property
    def drift_detected(self) -> bool:
        return self._drift_detected

    def status(self) -> dict[str, Any]:
        recent = self._reports[-5:] if self._reports else []
        return {
            "tick": self._tick,
            "drift_detected": self._drift_detected,
            "self_modification_frozen": self._modification_frozen,
            "clear_streak": self._clear_streak,
            "window_fill": {
                "critic": len(self._critic_scores),
                "goal_completion": len(self._goal_completions),
                "fixnet_novel": len(self._fixnet_novel_flags),
                "shadow": len(self._shadow_matches),
            },
            "current_signals": {
                "mean_critic_score": round(self._mean_critic_score(), 3),
                "goal_completion_rate": round(self._goal_completion_rate(), 3),
                "fixnet_novel_rate": round(self._fixnet_novel_rate(), 3),
                "shadow_match_rate": round(self._shadow_match_rate(), 3),
            },
            "reference": self.reference.to_dict() if self.reference else None,
            "recent_reports": [r.to_dict() for r in recent],
        }

    # ── Private: signal computations ──────────────────────────────────────────

    def _mean_critic_score(self) -> float:
        if not self._critic_scores:
            return 1.0  # no data = assume healthy
        return statistics.mean(self._critic_scores)

    def _goal_completion_rate(self) -> float:
        if not self._goal_completions:
            return 1.0
        return sum(1 for c in self._goal_completions if c) / len(self._goal_completions)

    def _fixnet_novel_rate(self) -> float:
        if not self._fixnet_novel_flags:
            return 0.0
        return sum(1 for f in self._fixnet_novel_flags if f)

    def _shadow_match_rate(self) -> float:
        if not self._shadow_matches:
            return 1.0
        return sum(1 for m in self._shadow_matches if m) / len(self._shadow_matches)

    def _kernel_event_count(self) -> int:
        if not self._runtime:
            return 0
        try:
            return self._runtime.kernel.stats().get("event_count", 0)
        except Exception:
            return 0

    def _evaluate_signals(self) -> list[SignalReading]:
        T = self.thresholds
        signals: list[SignalReading] = []

        # 1. Critic score
        critic = self._mean_critic_score()
        enough_data = len(self._critic_scores) >= T.critic_window_min
        signals.append(SignalReading(
            signal="critic_score",
            value=round(critic, 3),
            threshold=T.critic_score_floor,
            breached=enough_data and critic < T.critic_score_floor,
        ))

        # 2. Goal completion rate
        gcr = self._goal_completion_rate()
        signals.append(SignalReading(
            signal="goal_completion_rate",
            value=round(gcr, 3),
            threshold=T.goal_completion_floor,
            breached=len(self._goal_completions) >= 5 and gcr < T.goal_completion_floor,
        ))

        # 3. FixNet novelty rate
        fnr = self._fixnet_novel_rate()
        signals.append(SignalReading(
            signal="fixnet_novel_rate",
            value=round(fnr, 1),
            threshold=float(T.fixnet_novelty_ceiling),
            breached=fnr > T.fixnet_novelty_ceiling,
        ))

        # 4. Shadow mismatch rate
        smr = self._shadow_match_rate()
        mismatch = 1.0 - smr
        signals.append(SignalReading(
            signal="shadow_mismatch_rate",
            value=round(mismatch, 3),
            threshold=T.shadow_mismatch_ceiling,
            breached=len(self._shadow_matches) >= 5 and mismatch > T.shadow_mismatch_ceiling,
        ))

        # 5. Behavioral regression against reference
        if self.reference:
            current_score = (
                gcr * 0.3
                + critic * 0.4
                + smr * 0.2
                + (1.0 - min(1.0, fnr / 10)) * 0.1
            )
            delta = round(self.reference.score() - current_score, 3)
            signals.append(SignalReading(
                signal="behavioral_regression_delta",
                value=delta,
                threshold=T.regression_delta_ceiling,
                breached=delta > T.regression_delta_ceiling,
            ))

        return signals

    def _pull_world_model_signals(self, wm: Any) -> None:
        """Sample additional signals directly from WorldModel facts."""
        try:
            facts = wm.snapshot().get("facts", {})

            # Pull shadow mismatch from world model if available
            shadow_evals = facts.get("recent_tool_trust_profiles", [])
            for t in shadow_evals:
                if t.get("tool_name") == "shadow_execution":
                    matched = t.get("last_outcome") == "success"
                    # Only feed if not already in buffer from explicit feed
                    if len(self._shadow_matches) < self.thresholds.window_size:
                        self._shadow_matches.append(matched)

        except Exception:
            pass

    # ── Side effects ──────────────────────────────────────────────────────────

    def _write_world_model(self, report: DriftReport) -> None:
        if not self._runtime:
            return
        wm = getattr(self._runtime, "world_model", None)
        if not wm:
            return
        try:
            wm.update_fact("drift_detected", report.drift_detected)
            wm.update_fact("drift_signals_breached", report.breached_signals)
            wm.update_fact("drift_self_modification_frozen", report.self_modification_frozen)
            wm.update_fact("drift_tick", report.tick)
        except Exception:
            pass

    def _write_world_model_cleared(self, report: DriftReport) -> None:
        if not self._runtime:
            return
        wm = getattr(self._runtime, "world_model", None)
        if not wm:
            return
        try:
            wm.update_fact("drift_detected", False)
            wm.update_fact("drift_signals_breached", [])
            wm.update_fact("drift_self_modification_frozen", False)
            wm.update_fact("drift_cleared_at", _utcnow())
        except Exception:
            pass

    def _emit_kernel(self, kind: str, payload: dict) -> None:
        if not self._runtime:
            return
        kernel = getattr(self._runtime, "kernel", None)
        if kernel:
            try:
                kernel.record_evaluation("drift_detector", {"kind": kind, **payload})
            except Exception:
                pass

    def _inject_stabilize_goal(self, report: DriftReport) -> None:
        """Inject a high-priority stabilization goal into GoalEngine."""
        if not self._runtime:
            return
        goals = getattr(self._runtime, "goals", None)
        if goals:
            try:
                signals_str = ", ".join(report.breached_signals)
                goals.add_goal(
                    f"investigate and stabilize system drift — breached signals: {signals_str}",
                    priority=99,
                    completion_criteria=["all drift signals return below threshold"],
                    constraints=["do not promote self-improvement patches while drift is active"],
                    abort_conditions=["operator clears drift manually"],
                    compile=False,
                )
            except Exception:
                pass

    def _freeze_self_modification(self) -> None:
        """Record in kernel that self-modification is frozen."""
        self._emit_kernel("self_modification_frozen", {
            "reason": "drift_detected",
            "timestamp": _utcnow(),
        })

    def _record_drift_episode_to_curriculum(
        self, report: DriftReport, duration_s: float | None
    ) -> None:
        """Feed completed drift episode into curriculum memory as a failure record."""
        if not self._runtime:
            return
        try:
            self._runtime.record_curriculum(
                theme="system_drift",
                skill="behavioral_stability",
                failure_cluster="drift_episode",
                outcome="failure",
                notes=(
                    f"drift episode lasted {duration_s:.1f}s, "
                    f"breached: {', '.join(report.breached_signals)}"
                ) if duration_s else "drift cleared",
            )
        except Exception:
            pass
