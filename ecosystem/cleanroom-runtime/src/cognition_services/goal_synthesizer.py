"""GoalSynthesizer — emergent goal generation from observed world state.

The existing GoalEngine requires text input from an operator or directive.
It cannot autonomously decide "I should pursue X" based on what it observes.

GoalSynthesizer closes this gap. It:
  1. Reads world_model.snapshot() deltas (what changed since last tick)
  2. Matches changes against a library of synthesis rules
  3. Generates novel Goal objects and injects them into GoalEngine
  4. Records every synthesized goal as a kernel evaluation event for audit

Synthesis rule library covers:
  - Perception triggers    (alarm audio, near obstacle, screen error)
  - Cognition triggers     (tier degradation, fallback episode)
  - Trust triggers         (tool trust falls to 'degraded')
  - Curriculum triggers    (failure cluster accumulates above threshold)
  - FixNet triggers        (novelty spike — genuinely new error pattern)
  - Self-improve triggers  (validation failure, promotion block)
  - Memory triggers        (archive nearing capacity, retention stale)

Each rule specifies:
  - condition(snapshot, prev_snapshot) → bool
  - goal_title(snapshot) → str
  - priority: int
  - cooldown_s: float (prevent goal spam on sustained conditions)
  - requires_evidence: list[str] (world model keys that must be present)
  - auto_complete_condition(snapshot) → bool (when to mark goal done)

This closes the "goals still come from outside" gap identified in the
AGI assessment. The system can now notice unexpected conditions in the
world model and autonomously pursue corrective goals.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Synthesis rule ────────────────────────────────────────────────────────────

@dataclass
class SynthesisRule:
    """One rule that can trigger a synthesized goal.

    Args:
        rule_id:        Stable identifier for dedup and audit.
        condition:      fn(snapshot, prev) → bool. Fires when True.
        goal_title:     fn(snapshot) → str. The goal text to inject.
        priority:       GoalEngine priority (0–100, higher = more urgent).
        cooldown_s:     Min seconds between re-triggering this rule.
        evidence_keys:  World model keys that must exist for condition check.
        auto_complete:  fn(snapshot) → bool. Mark goal done when True.
        category:       Label for kernel audit ("perception" / "cognition" / etc.)
    """
    rule_id: str
    condition: Callable[[dict, dict], bool]
    goal_title: Callable[[dict], str]
    priority: int = 60
    cooldown_s: float = 60.0
    evidence_keys: list[str] = field(default_factory=list)
    auto_complete: Callable[[dict], bool] | None = None
    category: str = "general"

    _last_fired: float = field(default=0.0, init=False, repr=False)

    def is_ready(self) -> bool:
        return (time.monotonic() - self._last_fired) >= self.cooldown_s

    def mark_fired(self) -> None:
        self._last_fired = time.monotonic()


# ── Synthesized goal record ───────────────────────────────────────────────────

@dataclass
class SynthesizedGoal:
    rule_id: str
    goal_id: str
    goal_title: str
    priority: int
    category: str
    evidence: dict[str, Any]
    timestamp: str = field(default_factory=_utcnow)
    auto_completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "synthesized_goal",
            "rule_id": self.rule_id,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "priority": self.priority,
            "category": self.category,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "auto_completed": self.auto_completed,
        }


# ── Built-in synthesis rules ──────────────────────────────────────────────────

def _get_facts(snap: dict) -> dict:
    return snap.get("facts", {})


def _build_default_rules() -> list[SynthesisRule]:
    return [

        # ── Perception rules ──────────────────────────────────────────────────

        SynthesisRule(
            rule_id="perception_alarm_audio",
            condition=lambda s, p: any(
                "alarm" in str(a).lower() or "siren" in str(a).lower()
                for a in _get_facts(s).get("perception_alerts", [])
            ),
            goal_title=lambda s: "investigate alarm audio event detected by perception system",
            priority=90,
            cooldown_s=30.0,
            evidence_keys=["perception_alerts"],
            auto_complete=lambda s: not any(
                "alarm" in str(a).lower()
                for a in _get_facts(s).get("perception_alerts", [])
            ),
            category="perception",
        ),

        SynthesisRule(
            rule_id="perception_near_obstacle",
            condition=lambda s, p: any(
                obs.get("kind") == "depth_nearest_obstacle"
                and obs.get("confidence", 0) > 0.7
                and obs.get("attributes", {}).get("nearest_m", 999) < 0.8
                for obs in _get_facts(s).get("perception_top_observations", [])
            ),
            goal_title=lambda s: "halt motion and assess near-field obstacle detected by depth sensor",
            priority=98,
            cooldown_s=5.0,
            evidence_keys=["perception_top_observations"],
            auto_complete=lambda s: not any(
                obs.get("kind") == "depth_nearest_obstacle"
                and obs.get("attributes", {}).get("nearest_m", 999) < 0.8
                for obs in _get_facts(s).get("perception_top_observations", [])
            ),
            category="perception",
        ),

        SynthesisRule(
            rule_id="perception_ocr_error_visible",
            condition=lambda s, p: any(
                "error" in str(a).lower() or "traceback" in str(a).lower()
                for a in _get_facts(s).get("perception_alerts", [])
            ),
            goal_title=lambda s: "investigate visible error or traceback detected via OCR perception",
            priority=75,
            cooldown_s=45.0,
            evidence_keys=["perception_alerts"],
            category="perception",
        ),

        SynthesisRule(
            rule_id="perception_screen_change_spike",
            condition=lambda s, p: any(
                obs.get("kind") == "desktop_change"
                and obs.get("confidence", 0) > 0.85
                for obs in _get_facts(s).get("perception_top_observations", [])
            ),
            goal_title=lambda s: "assess unexpected desktop state change detected by screen capture",
            priority=55,
            cooldown_s=60.0,
            evidence_keys=["perception_top_observations"],
            category="perception",
        ),

        # ── Cognition rules ───────────────────────────────────────────────────

        SynthesisRule(
            rule_id="cognition_tier_degraded",
            condition=lambda s, p: (
                _get_facts(s).get("cognition_is_degraded") is True
                and _get_facts(p).get("cognition_is_degraded") is not True
            ),
            goal_title=lambda s: (
                f"restore primary cognition tier — currently degraded to "
                f"{_get_facts(s).get('cognition_tier', 'unknown')}: "
                f"{_get_facts(s).get('cognition_degradation_reason', '')[:80]}"
            ),
            priority=92,
            cooldown_s=20.0,
            evidence_keys=["cognition_is_degraded", "cognition_tier"],
            auto_complete=lambda s: _get_facts(s).get("cognition_is_degraded") is not True,
            category="cognition",
        ),

        SynthesisRule(
            rule_id="cognition_tier_recovered",
            condition=lambda s, p: (
                _get_facts(p).get("cognition_is_degraded") is True
                and _get_facts(s).get("cognition_is_degraded") is not True
            ),
            goal_title=lambda s: "verify primary cognition tier recovery and run smoke tests",
            priority=70,
            cooldown_s=30.0,
            evidence_keys=["cognition_is_degraded"],
            category="cognition",
        ),

        # ── Trust rules ───────────────────────────────────────────────────────

        SynthesisRule(
            rule_id="tool_trust_degraded",
            condition=lambda s, p: any(
                t.get("trust_level") == "degraded"
                for t in _get_facts(s).get("recent_tool_trust_profiles", [])
                if t not in _get_facts(p).get("recent_tool_trust_profiles", [])
            ),
            goal_title=lambda s: (
                "investigate degraded tool trust — "
                + ", ".join(
                    t.get("tool_name", "?")
                    for t in _get_facts(s).get("recent_tool_trust_profiles", [])
                    if t.get("trust_level") == "degraded"
                )[:80]
            ),
            priority=72,
            cooldown_s=120.0,
            evidence_keys=["recent_tool_trust_profiles"],
            category="trust",
        ),

        # ── Curriculum rules ──────────────────────────────────────────────────

        SynthesisRule(
            rule_id="curriculum_failure_cluster_spike",
            condition=lambda s, p: (
                _get_facts(s).get("curriculum_update_count", 0)
                > _get_facts(p).get("curriculum_update_count", 0) + 3
                and any(
                    u.get("outcome") == "failure"
                    for u in _get_facts(s).get("recent_curriculum_updates", [])[-3:]
                )
            ),
            goal_title=lambda s: (
                "run self-improvement cycle targeting curriculum failure cluster: "
                + (
                    _get_facts(s).get("recent_curriculum_updates", [{}])[-1].get("theme", "unknown")
                )
            ),
            priority=68,
            cooldown_s=180.0,
            evidence_keys=["curriculum_update_count", "recent_curriculum_updates"],
            category="curriculum",
        ),

        # ── FixNet rules ──────────────────────────────────────────────────────

        SynthesisRule(
            rule_id="fixnet_novel_error",
            condition=lambda s, p: (
                _get_facts(s).get("fixnet_case_count", 0)
                > _get_facts(p).get("fixnet_case_count", 0)
                and any(
                    c.get("novelty", {}).get("is_novel")
                    for c in _get_facts(s).get("recent_fixnet_cases", [])[-3:]
                )
            ),
            goal_title=lambda s: (
                "analyze and resolve novel FixNet error pattern: "
                + (_get_facts(s).get("recent_fixnet_cases", [{}])[-1].get("title", "unknown"))[:80]
            ),
            priority=78,
            cooldown_s=90.0,
            evidence_keys=["fixnet_case_count", "recent_fixnet_cases"],
            category="fixnet",
        ),

        # ── Self-improve rules ────────────────────────────────────────────────

        SynthesisRule(
            rule_id="self_improve_repeated_failure",
            condition=lambda s, p: (
                sum(
                    1 for r in _get_facts(s).get("recent_curriculum_updates", [])
                    if r.get("theme") == "self_improve" and r.get("outcome") == "failure"
                ) >= 2
            ),
            goal_title=lambda s: "diagnose repeated self-improvement validation failures and adjust patch strategy",
            priority=65,
            cooldown_s=240.0,
            evidence_keys=["recent_curriculum_updates"],
            category="self_improve",
        ),

        # ── Memory rules ──────────────────────────────────────────────────────

        SynthesisRule(
            rule_id="memory_archive_growth",
            condition=lambda s, p: (
                _get_facts(s).get("mirrored_live_memory_count", 0) > 50
                and _get_facts(s).get("mirrored_live_memory_count", 0)
                > _get_facts(p).get("mirrored_live_memory_count", 0) + 10
            ),
            goal_title=lambda s: "review and retire stale memory archives to maintain retrieval efficiency",
            priority=40,
            cooldown_s=600.0,
            evidence_keys=["mirrored_live_memory_count"],
            category="memory",
        ),
    ]


# ── GoalSynthesizer ───────────────────────────────────────────────────────────

class GoalSynthesizer:
    """Generates novel goals from observed world model deltas.

    Args:
        goal_engine:    GoalEngine to inject synthesized goals into.
        runtime:        LuciferRuntime for kernel event emission.
        custom_rules:   Additional SynthesisRule objects beyond defaults.
        max_active_synthesized: Cap on simultaneously active synthesized goals
            to prevent goal explosion (default 10).
    """

    def __init__(
        self,
        goal_engine: Any,
        runtime: Any = None,
        *,
        custom_rules: list[SynthesisRule] | None = None,
        max_active_synthesized: int = 10,
    ) -> None:
        self.goals = goal_engine
        self.runtime = runtime
        self.max_active = max_active_synthesized
        self._rules: list[SynthesisRule] = _build_default_rules()
        if custom_rules:
            self._rules.extend(custom_rules)
        self._synthesized: list[SynthesizedGoal] = []
        self._prev_snapshot: dict[str, Any] = {}
        self._tick_count = 0

    def tick(self, world_model: Any) -> list[SynthesizedGoal]:
        """Call once per loop tick. Returns any goals synthesized this tick."""
        snapshot = world_model.snapshot() if hasattr(world_model, "snapshot") else world_model
        prev = self._prev_snapshot
        self._tick_count += 1
        new_goals: list[SynthesizedGoal] = []

        # Auto-complete check on pending synthesized goals
        self._check_auto_complete(snapshot)

        # Count active synthesized goals
        active_count = sum(1 for g in self._synthesized if not g.auto_completed)
        if active_count >= self.max_active:
            self._prev_snapshot = snapshot
            return []

        facts = snapshot.get("facts", {})

        for rule in self._rules:
            if not rule.is_ready():
                continue

            # Check evidence keys exist
            if any(k not in facts for k in rule.evidence_keys):
                continue

            try:
                fired = rule.condition(snapshot, prev)
            except Exception:
                fired = False

            if not fired:
                continue

            try:
                title = rule.goal_title(snapshot)
            except Exception:
                title = f"[synthesized] {rule.rule_id}"

            # Inject into GoalEngine
            goal = self.goals.add_goal(
                title,
                priority=rule.priority,
                compile=False,
                completion_criteria=["condition that triggered goal no longer active"],
                constraints=["do not interrupt operator directives with higher priority"],
                abort_conditions=["operator cancels synthesized goal"],
            )
            rule.mark_fired()

            evidence = {
                k: facts.get(k)
                for k in rule.evidence_keys
                if k in facts
            }

            sg = SynthesizedGoal(
                rule_id=rule.rule_id,
                goal_id=goal.goal_id,
                goal_title=title,
                priority=rule.priority,
                category=rule.category,
                evidence=evidence,
            )
            self._synthesized.append(sg)
            new_goals.append(sg)

            # Emit kernel event
            self._emit(sg)

        self._prev_snapshot = snapshot
        return new_goals

    def _check_auto_complete(self, snapshot: dict) -> None:
        """Mark synthesized goals done if their auto_complete condition fires."""
        for sg in self._synthesized:
            if sg.auto_completed:
                continue
            rule = next((r for r in self._rules if r.rule_id == sg.rule_id), None)
            if rule and rule.auto_complete:
                try:
                    if rule.auto_complete(snapshot):
                        sg.auto_completed = True
                        self.goals.complete_goal(sg.goal_id)
                        self._emit_complete(sg)
                except Exception:
                    pass

    def _emit(self, sg: SynthesizedGoal) -> None:
        if not self.runtime:
            return
        kernel = getattr(self.runtime, "kernel", None)
        if kernel:
            try:
                kernel.record_evaluation("goal_synthesizer", sg.to_dict())
            except Exception:
                pass

    def _emit_complete(self, sg: SynthesizedGoal) -> None:
        if not self.runtime:
            return
        kernel = getattr(self.runtime, "kernel", None)
        if kernel:
            try:
                kernel.record_evaluation("goal_synthesizer", {
                    **sg.to_dict(),
                    "kind": "synthesized_goal_auto_completed",
                })
            except Exception:
                pass

    def status(self) -> dict[str, Any]:
        return {
            "tick_count": self._tick_count,
            "rule_count": len(self._rules),
            "synthesized_total": len(self._synthesized),
            "synthesized_active": sum(1 for g in self._synthesized if not g.auto_completed),
            "synthesized_completed": sum(1 for g in self._synthesized if g.auto_completed),
            "recent": [g.to_dict() for g in self._synthesized[-10:]],
        }

    def add_rule(self, rule: SynthesisRule) -> None:
        self._rules.append(rule)
