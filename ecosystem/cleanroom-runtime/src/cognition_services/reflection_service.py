"""ReflectionService — between-cycle inner critic for multi-output consistency.

CriticService scores one output against one task in isolation.
That's necessary but insufficient. A system can produce outputs that each
score well individually while drifting collectively — goals creeping,
reasoning style shifting, directive alignment eroding cycle by cycle.

ReflectionService runs BETWEEN execution cycles, not during them.
It reads the last N receipts and asks three questions that require
seeing multiple outputs together:

  1. Consistency   — are the last N outputs coherent with each other?
                     (same reasoning style, consistent facts, no contradiction)
  2. Directive     — is the system still aligned with its active directives?
                     (drift from directive = the most dangerous silent failure)
  3. Momentum      — is reasoning improving, stable, or degrading cycle-by-cycle?
                     (trend matters more than any single score)

ReflectionReport feeds into:
  - DriftDetector.feed_critic_score() — cycle-level signal
  - GoalSynthesizer — injects 'realign with directive' goal on directive drift
  - CurriculumMemory — logs reflection outcomes as training signal
  - WorldModel — exposes reflection_score and reflection_alerts
  - KernelEngine — full audit trail

Reflection is deliberately separate from execution:
  - Uses the same CognitionCore but with a distinct system prompt
  - Runs at lower frequency (every K cycles, not every cycle)
  - Does NOT take actions — only reports and feeds signals
  - Can be disabled cleanly without affecting execution

This closes the 'act → observe → critique → repair → remember → stabilize'
loop described in the DARPA assessment.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


REFLECTION_SYSTEM_PROMPT = """You are a strict consistency and alignment evaluator for an autonomous AI runtime.

You will be given:
- A list of recent execution receipts (what the system did and produced)
- The active directives (what the system is supposed to be doing)

Evaluate on THREE axes, each scored 0.0–1.0:

consistency: Are the recent outputs logically coherent with each other?
  1.0 = perfectly consistent, no contradictions
  0.0 = outputs contradict each other or show incoherent reasoning

directive_alignment: Is the system's recent behavior aligned with its active directives?
  1.0 = clearly advancing directive goals
  0.0 = ignoring or contradicting directives

momentum: Is reasoning quality improving, stable, or degrading across these outputs?
  1.0 = clearly improving
  0.5 = stable
  0.0 = clearly degrading

Respond ONLY with valid JSON. No other text, no markdown:
{"consistency": 0.0, "directive_alignment": 0.0, "momentum": 0.0, "alerts": [], "summary": "one sentence"}

alerts is a list of specific concerns as short strings. Empty list if none."""


# ── Reflection result ─────────────────────────────────────────────────────────

@dataclass
class ReflectionReport:
    """Result of one reflection cycle over N recent receipts."""
    cycle_index: int
    receipts_analyzed: int
    consistency: float          # 0–1: cross-output coherence
    directive_alignment: float  # 0–1: alignment with active directives
    momentum: float             # 0–1: reasoning trend (1=improving, 0.5=stable)
    composite_score: float      # weighted aggregate
    alerts: list[str]
    summary: str
    method: str                 # "model" | "heuristic"
    active_directive_titles: list[str]
    timestamp: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = "reflection_report"
        d["passed"] = self.composite_score >= 0.55
        return d

    @property
    def passed(self) -> bool:
        return self.composite_score >= 0.55

    @property
    def directive_drift_detected(self) -> bool:
        return self.directive_alignment < 0.45


# ── ReflectionService ─────────────────────────────────────────────────────────

class ReflectionService:
    """Between-cycle consistency and directive alignment evaluator.

    Args:
        cognition_core:   CognitionCore for model-based reflection.
                          Falls back to heuristic if unavailable.
        runtime:          LuciferRuntime for kernel events and directive access.
        reflect_every_n:  Run reflection every N execution cycles (default 5).
        receipt_window:   Number of recent receipts to analyze (default 10).
        directive_weight: Weight of directive alignment in composite (default 0.45).
        consistency_weight: Weight of consistency in composite (default 0.35).
        momentum_weight:  Weight of momentum in composite (default 0.20).
    """

    def __init__(
        self,
        cognition_core: Any = None,
        runtime: Any = None,
        *,
        reflect_every_n: int = 5,
        receipt_window: int = 10,
        directive_weight: float = 0.45,
        consistency_weight: float = 0.35,
        momentum_weight: float = 0.20,
    ) -> None:
        self.core = cognition_core
        self._runtime = runtime
        self.reflect_every_n = reflect_every_n
        self.receipt_window = receipt_window
        self.directive_weight = directive_weight
        self.consistency_weight = consistency_weight
        self.momentum_weight = momentum_weight

        self._cycle_count = 0
        self._reflection_count = 0
        self._reports: list[ReflectionReport] = []

    def wire(self, runtime: Any, cognition_core: Any | None = None) -> None:
        self._runtime = runtime
        if cognition_core:
            self.core = cognition_core

    # ── Public API ────────────────────────────────────────────────────────────

    def tick(self) -> ReflectionReport | None:
        """Call once per execution cycle. Returns ReflectionReport every N cycles.

        Returns None on cycles where reflection is not triggered.
        """
        self._cycle_count += 1
        if self._cycle_count % self.reflect_every_n != 0:
            return None
        return self.reflect()

    def reflect(self) -> ReflectionReport:
        """Force one reflection cycle regardless of tick count."""
        self._reflection_count += 1
        receipts = self._collect_receipts()
        directives = self._collect_directives()

        if self.core is not None:
            try:
                report = self._model_reflect(receipts, directives)
            except Exception:
                report = self._heuristic_reflect(receipts, directives)
        else:
            report = self._heuristic_reflect(receipts, directives)

        self._reports.append(report)
        self._side_effects(report)
        return report

    def status(self) -> dict[str, Any]:
        recent = self._reports[-5:]
        return {
            "cycle_count": self._cycle_count,
            "reflection_count": self._reflection_count,
            "reflect_every_n": self.reflect_every_n,
            "recent_reports": [r.to_dict() for r in recent],
            "last_composite": self._reports[-1].composite_score if self._reports else None,
            "last_directive_alignment": self._reports[-1].directive_alignment if self._reports else None,
        }

    # ── Private: data collection ──────────────────────────────────────────────

    def _collect_receipts(self) -> list[dict[str, Any]]:
        if not self._runtime:
            return []
        kernel = getattr(self._runtime, "kernel", None)
        if not kernel:
            return []
        try:
            state = kernel.state()
            recent = state.evaluations[-self.receipt_window:] if state.evaluations else []
            # Filter to meaningful execution outputs
            return [
                e for e in recent
                if e.get("kind") in {
                    "execution_evaluation", "model_prompt_complete",
                    "code_patch", "self_improve_patch",
                }
            ]
        except Exception:
            return []

    def _collect_directives(self) -> list[dict[str, Any]]:
        if not self._runtime:
            return []
        try:
            directives = getattr(self._runtime, "directives", None)
            if directives:
                return directives.active()[:5]
        except Exception:
            pass
        return []

    # ── Private: heuristic reflection ─────────────────────────────────────────

    def _heuristic_reflect(
        self,
        receipts: list[dict[str, Any]],
        directives: list[dict[str, Any]],
    ) -> ReflectionReport:
        alerts: list[str] = []

        # Consistency: check for result_keys stability across receipts
        if len(receipts) >= 2:
            all_keys = [set(r.get("result_keys", [])) for r in receipts]
            overlaps = []
            for i in range(len(all_keys) - 1):
                a, b = all_keys[i], all_keys[i + 1]
                if a or b:
                    overlaps.append(len(a & b) / max(len(a | b), 1))
            consistency = round(sum(overlaps) / max(len(overlaps), 1), 3) if overlaps else 0.7
        else:
            consistency = 0.7  # neutral default

        # Directive alignment: keyword overlap between directive instructions and receipts
        if directives and receipts:
            dir_text = " ".join(d.get("instruction", "") for d in directives).lower()
            dir_tokens = set(re.findall(r'\b\w{5,}\b', dir_text))
            receipt_text = " ".join(str(r) for r in receipts[-5:]).lower()
            rec_tokens = set(re.findall(r'\b\w{5,}\b', receipt_text))
            overlap = len(dir_tokens & rec_tokens)
            directive_alignment = round(min(1.0, overlap / max(len(dir_tokens), 1) * 1.5), 3)
            if directive_alignment < 0.3:
                alerts.append(f"low directive alignment ({directive_alignment:.2f}) — possible goal drift")
        else:
            directive_alignment = 0.6

        # Momentum: trend in validator_pass_rate across recent receipts
        pass_rates = [r.get("validator_pass_rate", 0.5) for r in receipts if "validator_pass_rate" in r]
        if len(pass_rates) >= 3:
            early = sum(pass_rates[:len(pass_rates)//2]) / max(len(pass_rates)//2, 1)
            late = sum(pass_rates[len(pass_rates)//2:]) / max(len(pass_rates) - len(pass_rates)//2, 1)
            momentum = round(0.5 + (late - early), 3)
            momentum = max(0.0, min(1.0, momentum))
            if momentum < 0.35:
                alerts.append(f"negative reasoning momentum ({momentum:.2f}) — quality degrading")
        else:
            momentum = 0.5

        composite = round(
            consistency * self.consistency_weight
            + directive_alignment * self.directive_weight
            + momentum * self.momentum_weight,
            3,
        )

        return ReflectionReport(
            cycle_index=self._reflection_count,
            receipts_analyzed=len(receipts),
            consistency=consistency,
            directive_alignment=directive_alignment,
            momentum=momentum,
            composite_score=composite,
            alerts=alerts,
            summary=f"heuristic reflection: consistency={consistency:.2f} alignment={directive_alignment:.2f} momentum={momentum:.2f}",
            method="heuristic",
            active_directive_titles=[d.get("title", "?") for d in directives],
        )

    # ── Private: model reflection ─────────────────────────────────────────────

    def _model_reflect(
        self,
        receipts: list[dict[str, Any]],
        directives: list[dict[str, Any]],
    ) -> ReflectionReport:
        receipts_text = json.dumps(receipts[-8:], indent=2)[:2000]
        directives_text = json.dumps([
            {"title": d.get("title"), "instruction": d.get("instruction")}
            for d in directives
        ], indent=2)[:600]

        prompt = (
            f"RECENT EXECUTION RECEIPTS:\n{receipts_text}\n\n"
            f"ACTIVE DIRECTIVES:\n{directives_text}\n\n"
            "Evaluate consistency, directive_alignment, and momentum. Respond with JSON only."
        )

        result = self.core.generate(
            prompt,
            context={"system": REFLECTION_SYSTEM_PROMPT},
        )
        output = result.get("output_text", "") if isinstance(result, dict) else str(result)

        try:
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if not match:
                raise ValueError("no JSON")
            data = json.loads(match.group())
            consistency = float(data.get("consistency", 0.7))
            directive_alignment = float(data.get("directive_alignment", 0.6))
            momentum = float(data.get("momentum", 0.5))
            alerts = list(data.get("alerts", []))
            summary = str(data.get("summary", ""))
        except Exception:
            return self._heuristic_reflect(receipts, directives)

        composite = round(
            consistency * self.consistency_weight
            + directive_alignment * self.directive_weight
            + momentum * self.momentum_weight,
            3,
        )

        return ReflectionReport(
            cycle_index=self._reflection_count,
            receipts_analyzed=len(receipts),
            consistency=consistency,
            directive_alignment=directive_alignment,
            momentum=momentum,
            composite_score=composite,
            alerts=alerts,
            summary=summary,
            method="model",
            active_directive_titles=[d.get("title", "?") for d in directives],
        )

    # ── Side effects ──────────────────────────────────────────────────────────

    def _side_effects(self, report: ReflectionReport) -> None:
        # Feed into DriftDetector
        if self._runtime:
            dd = getattr(self._runtime, "drift_detector", None)
            if dd:
                try:
                    dd.feed_critic_score(report.composite_score)
                except Exception:
                    pass

        # WorldModel update
        wm = getattr(self._runtime, "world_model", None) if self._runtime else None
        if wm:
            try:
                wm.update_fact("reflection_score", report.composite_score)
                wm.update_fact("reflection_directive_alignment", report.directive_alignment)
                wm.update_fact("reflection_alerts", report.alerts)
                wm.update_fact("reflection_momentum", report.momentum)
            except Exception:
                pass

        # Kernel event
        kernel = getattr(self._runtime, "kernel", None) if self._runtime else None
        if kernel:
            try:
                kernel.record_evaluation("reflection_service", report.to_dict())
            except Exception:
                pass

        # GoalSynthesizer — inject directive drift goal if needed
        if report.directive_drift_detected and self._runtime:
            goals = getattr(self._runtime, "goals", None)
            if goals:
                try:
                    directives_str = ", ".join(report.active_directive_titles[:3])
                    goals.add_goal(
                        f"realign execution with active directives: {directives_str}",
                        priority=85,
                        completion_criteria=["directive_alignment > 0.65 in next reflection"],
                        constraints=["do not abandon current task mid-execution"],
                        compile=False,
                    )
                except Exception:
                    pass

        # Curriculum signal
        if self._runtime:
            try:
                self._runtime.record_curriculum(
                    theme="reflection",
                    skill="directive_alignment",
                    failure_cluster=None if report.passed else "directive_drift",
                    outcome="success" if report.passed else "failure",
                    notes=f"composite={report.composite_score:.2f} momentum={report.momentum:.2f}",
                )
            except Exception:
                pass
