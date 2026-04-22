"""AGILoop — unified closed-loop orchestrator.

This is the main event loop that wires every subsystem together into the
complete sense-reflect-reason-act-verify-learn cycle described in the
DARPA assessment. It replaces the informal "call these things in order"
pattern with a single, auditable, fault-tolerant orchestrator.

One tick of the AGI loop:

  1. SENSE        PerceptionLoop provides world model updates
  2. RETRIEVE     EpisodicRetrieval surfaces relevant history before action
  3. SYNTHESIZE   GoalSynthesizer generates novel goals from world deltas
  4. REFLECT      ReflectionService checks cross-cycle consistency (every N)
  5. REASON       PersistentLoop selects and plans the current goal
  6. ACT          LuciferRuntime executes the plan via proposal/receipt cycle
  7. CRITIQUE     CriticService scores the execution output
  8. DRIFT CHECK  DriftDetector feeds on critique score + goal outcome
  9. LEARN        CurriculumMemory records outcome; CurriculumTrainer evaluates
 10. REMEMBER     WorldModel updated with all signals
 11. HEARTBEAT    ContinuityShell heartbeat; kernel event emitted

The loop is the demo. Running it for 100 ticks with a failure injected
at tick 30 and watching the system repair, log the fix, recover, continue,
and show the full receipt trail is the "jaw-dropping proof" the assessment
called for.

Emergency override:
    loop.freeze()   — freeze self-modification (DriftDetector also does this)
    loop.thaw()     — unfreeze (requires DriftDetector to be clear)
    loop.inject(text) — operator injection mid-loop (forwarded to StreamSession)
    loop.status()   — full system status snapshot

All events are kernel-logged. The loop itself is replayable.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from cognition_services.drift_detector import DriftDetector, DriftThresholds
from cognition_services.immutable_baseline import ImmutableBaseline
from cognition_services.reflection_service import ReflectionService
from cognition_services.episodic_retrieval import EpisodicRetrieval
from cognition_services.goal_synthesizer import GoalSynthesizer
from cognition_services.critic import CriticService
from cognition_services.curriculum_trainer import CurriculumTrainer
from cognition_services.persistent_loop import PersistentLoop


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LoopTickReport:
    """Complete record of one AGI loop tick."""
    tick: int
    goal: str | None
    action_status: str
    critique_score: float | None
    drift_detected: bool
    reflection_triggered: bool
    goals_synthesized: int
    episodic_recommendation: str
    self_modification_frozen: bool
    elapsed_s: float
    timestamp: str = field(default_factory=_utcnow)
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "agi_loop_tick",
            **{k: v for k, v in self.__dict__.items()},
        }


class AGILoop:
    """The unified AGI sense-reflect-reason-act-verify-learn loop.

    Args:
        runtime:          LuciferRuntime — the execution substrate.
        world_model:      WorldModel — shared state across all subsystems.
        tick_interval_s:  Target seconds between ticks (default 2.0).
        max_ticks:        Stop after this many ticks (0 = run forever).
        on_tick:          Optional callback(LoopTickReport) after each tick.
        on_drift_alert:   Optional callback(DriftReport) on drift detection.
        drift_thresholds: Custom DriftThresholds (uses defaults if None).
    """

    def __init__(
        self,
        runtime: Any,
        world_model: Any,
        *,
        tick_interval_s: float = 2.0,
        max_ticks: int = 0,
        on_tick: Callable[[LoopTickReport], None] | None = None,
        on_drift_alert: Callable[[Any], None] | None = None,
        drift_thresholds: DriftThresholds | None = None,
    ) -> None:
        self.runtime = runtime
        self.world_model = world_model
        self.tick_interval_s = tick_interval_s
        self.max_ticks = max_ticks
        self.on_tick = on_tick

        # Core loop components
        self.drift_detector = DriftDetector(
            drift_thresholds,
            on_drift_alert=on_drift_alert or self._default_drift_alert,
            on_drift_cleared=self._on_drift_cleared,
        )
        self.drift_detector.wire(runtime)

        self.immutable_baseline = ImmutableBaseline(
            workspace_root=getattr(runtime, "workspace_root", "."),
            runtime=runtime,
            drift_detector=self.drift_detector,
        )

        self.reflection_service = ReflectionService(
            cognition_core=getattr(runtime, "cognition_core", None),
            runtime=runtime,
            reflect_every_n=5,
        )

        self.episodic_retrieval = EpisodicRetrieval(runtime=runtime)

        self.goal_synthesizer = GoalSynthesizer(
            goal_engine=runtime.goals,
            runtime=runtime,
        )

        self.critic_service = CriticService()

        self.curriculum_trainer = CurriculumTrainer(
            workspace_root=getattr(runtime, "workspace_root", "."),
            runtime=runtime,
            failure_threshold=5,
            export_only=False,
        )

        self.persistent_loop = PersistentLoop(
            goal_engine=runtime.goals,
            world_model=world_model,
        )

        # Attach to runtime for external access
        runtime.drift_detector = self.drift_detector
        runtime.immutable_baseline = self.immutable_baseline
        runtime.reflection_service = self.reflection_service
        runtime.episodic_retrieval = self.episodic_retrieval
        runtime.goal_synthesizer = self.goal_synthesizer
        runtime.agi_loop = self

        # State
        self._tick = 0
        self._running = False
        self._frozen = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._tick_reports: list[LoopTickReport] = []
        self._active_session_id: str | None = None

    # ── Control API ───────────────────────────────────────────────────────────

    def start(self, daemon: bool = True) -> None:
        """Start the AGI loop in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="AGILoop", daemon=daemon,
        )
        self._thread.start()
        self._emit_kernel("agi_loop_started", {"tick_interval_s": self.tick_interval_s})

    def stop(self, timeout: float = 10.0) -> None:
        """Signal the loop to stop and wait."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._emit_kernel("agi_loop_stopped", {"total_ticks": self._tick})

    def tick_once(self) -> LoopTickReport:
        """Run one synchronous tick. Useful for testing and demos."""
        return self._tick_loop()

    def freeze(self, reason: str = "operator freeze") -> None:
        """Freeze self-modification. Does not stop the loop."""
        self._frozen = True
        self._emit_kernel("agi_loop_frozen", {"reason": reason})

    def thaw(self) -> bool:
        """Unfreeze if DriftDetector is clear. Returns True if thawed."""
        if self.drift_detector.drift_detected:
            return False
        self._frozen = False
        self._emit_kernel("agi_loop_thawed", {})
        return True

    def inject(self, text: str, session_id: str | None = None) -> dict[str, Any]:
        """Inject operator text into the active streaming session mid-loop."""
        sid = session_id or self._active_session_id
        if sid and hasattr(self.runtime, "cognition_inject"):
            ok = self.runtime.cognition_inject(sid, text)
            return {"status": "ok" if ok else "not_found", "session_id": sid}
        return {"status": "no_active_session"}

    @property
    def is_frozen(self) -> bool:
        return self._frozen or self.drift_detector.is_frozen

    def status(self) -> dict[str, Any]:
        return {
            "tick": self._tick,
            "running": bool(self._thread and self._thread.is_alive()),
            "frozen": self._frozen,
            "drift": self.drift_detector.status(),
            "baseline": self.immutable_baseline.status(),
            "reflection": self.reflection_service.status(),
            "episodic": self.episodic_retrieval.status(),
            "goal_synthesizer": self.goal_synthesizer.status(),
            "recent_ticks": [r.to_dict() for r in self._tick_reports[-10:]],
        }

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        self._running = True
        while not self._stop_event.is_set():
            if self.max_ticks and self._tick >= self.max_ticks:
                break
            tick_start = time.monotonic()
            try:
                report = self._tick_loop()
                if self.on_tick:
                    try:
                        self.on_tick(report)
                    except Exception:
                        pass
            except Exception as exc:
                self._emit_kernel("agi_loop_tick_error", {"tick": self._tick, "error": str(exc)})

            elapsed = time.monotonic() - tick_start
            sleep_time = max(0.0, self.tick_interval_s - elapsed)
            self._stop_event.wait(timeout=sleep_time)
        self._running = False

    def _tick_loop(self) -> LoopTickReport:
        """One complete AGI loop tick — all 11 stages."""
        self._tick += 1
        tick_start = time.monotonic()
        alerts: list[str] = []
        critique_score: float | None = None
        reflection_triggered = False
        goals_synthesized = 0
        episodic_rec = "no_history"
        action_status = "idle"
        goal_title: str | None = None

        # ── 1. SENSE — world model is updated by PerceptionLoop (external thread)

        # ── 2. RETRIEVE — surface episodic history before acting
        current_goal = self.runtime.goals.current_goal()
        if current_goal:
            goal_title = current_goal.title
            ep_result = self.episodic_retrieval.action_lookup(goal_title)
            episodic_rec = ep_result.recommendation
            if ep_result.recommendation == "avoid":
                alerts.append(f"episodic: prior failures on similar task ({ep_result.top_similarity:.2f} similarity)")
            elif ep_result.recommendation == "caution":
                alerts.append(f"episodic: mixed history on similar task")

        # ── 3. SYNTHESIZE — generate novel goals from world model
        new_goals = self.goal_synthesizer.tick(self.world_model)
        goals_synthesized = len(new_goals)

        # ── 4. REFLECT — check cross-cycle consistency (every N ticks)
        reflection = self.reflection_service.tick()
        if reflection is not None:
            reflection_triggered = True
            if not reflection.passed:
                alerts.extend(reflection.alerts)
            if reflection.directive_drift_detected:
                alerts.append(f"directive drift detected (alignment={reflection.directive_alignment:.2f})")

        # ── 5–6. REASON + ACT — execute via PersistentLoop
        if not self.is_frozen:
            loop_result = self.persistent_loop.tick(self.runtime, confirm=False)
            action_status = loop_result.action.get("status", "idle")
            goal_title = loop_result.goal

            # ── 7. CRITIQUE — score the output
            if goal_title and action_status not in ("idle", "denied"):
                output_text = str(loop_result.action)
                cr = self.critic_service.critique(
                    proposal_id=f"agi_tick_{self._tick}",
                    task_description=goal_title,
                    output_text=output_text,
                    active_goal=goal_title,
                    execution_result=loop_result.action,
                )
                critique_score = cr.composite_score
                if cr.recommendation == "reject":
                    alerts.append(f"critic: output rejected (score={critique_score:.2f})")

                # ── 8. DRIFT CHECK — feed signals
                self.drift_detector.feed_critic_score(critique_score)
                self.drift_detector.feed_goal_completed(
                    action_status in ("approve", "confirmed")
                )
        else:
            alerts.append("self-modification frozen — executing in safe mode only")

        # ── 8. DRIFT TICK (always runs)
        drift_report = self.drift_detector.tick(self.world_model)
        if drift_report.drift_detected and drift_report.action == "drift_alert":
            alerts.extend([f"DRIFT: {s}" for s in drift_report.breached_signals])

        # ── 9. LEARN — curriculum + training evaluation
        try:
            curriculum = getattr(self.runtime, "curriculum", None)
            if curriculum and self._tick % 10 == 0:
                curriculum_stats = curriculum.stats()
                # Merge stats into format CurriculumTrainer expects
                profiles = []
                for t in curriculum_stats.get("top_themes", []):
                    profiles.append({
                        "theme": t.get("name"), "outcome": t.get("last_outcome"),
                        "failure_cluster": None,
                    })
                for c in curriculum_stats.get("top_failure_clusters", []):
                    profiles.append({
                        "theme": "curriculum",
                        "failure_cluster": c.get("name"),
                        "outcome": "failure",
                    })
                self.curriculum_trainer.evaluate({"profiles": profiles})
        except Exception:
            pass

        # ── 10. REMEMBER — world model tick summary
        try:
            self.world_model.update_fact("agi_loop_tick", self._tick)
            self.world_model.update_fact("agi_loop_last_action", action_status)
            self.world_model.update_fact("agi_loop_critique_score", critique_score)
            self.world_model.update_fact("agi_loop_frozen", self.is_frozen)
            self.world_model.update_fact("agi_loop_alerts", alerts)
        except Exception:
            pass

        # ── 11. HEARTBEAT
        elapsed = round(time.monotonic() - tick_start, 3)
        try:
            self.runtime.continuity_heartbeat(
                mode="drift_detected" if drift_report.drift_detected else "primary",
                notes=f"agi_loop tick {self._tick}",
            )
        except Exception:
            pass

        report = LoopTickReport(
            tick=self._tick,
            goal=goal_title,
            action_status=action_status,
            critique_score=critique_score,
            drift_detected=drift_report.drift_detected,
            reflection_triggered=reflection_triggered,
            goals_synthesized=goals_synthesized,
            episodic_recommendation=episodic_rec,
            self_modification_frozen=self.is_frozen,
            elapsed_s=elapsed,
            alerts=alerts,
        )
        self._tick_reports.append(report)
        self._emit_kernel("agi_loop_tick", report.to_dict())
        return report

    # ── Event callbacks ───────────────────────────────────────────────────────

    def _default_drift_alert(self, drift_report: Any) -> None:
        self._frozen = True  # freeze loop on drift

    def _on_drift_cleared(self, drift_report: Any) -> None:
        self._frozen = False

    # ── Kernel event emission ─────────────────────────────────────────────────

    def _emit_kernel(self, kind: str, payload: dict) -> None:
        kernel = getattr(self.runtime, "kernel", None)
        if kernel:
            try:
                kernel.record_evaluation("agi_loop", {"kind": kind, **payload})
            except Exception:
                pass
