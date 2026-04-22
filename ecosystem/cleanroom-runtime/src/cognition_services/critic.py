"""CriticService — reasoning quality evaluation beyond syntactic validation.

The existing EvaluatorService scores whether validators passed (did the patch
apply? did tests pass?). That is necessary but not sufficient. Bad logic can
pass tests. A plan can be syntactically valid and semantically wrong.

CriticService scores the REASONING QUALITY of an output against three axes:

  1. task_alignment     — did the output actually address what was asked?
  2. goal_progress      — does it move toward the active goal or away from it?
  3. side_effect_risk   — what unintended consequences might follow?

Scoring strategy (in order of availability):
  a. Local model critique  — prompt the CognitionCore to score its own output
                             using a structured critique prompt. Expensive but
                             accurate.
  b. Heuristic critique    — lexical alignment scoring + goal keyword matching.
                             Fast, zero-dep, always available.
  c. Shadow baseline       — compare against the ShadowExecutionService to
                             detect unexpected status divergence.

CritiqueResult feeds back into:
  - PromotionGate.review_run() — block promotion if critique_score < threshold
  - SelfImprove planner       — use low-scoring outputs as training signal
  - CurriculumTrainer         — tag failure_cluster by critique axis
  - WorldModel                — expose critique_score for GoalSynthesizer

The loop this closes:
  Bad reasoning → low critique score → blocked promotion + curriculum entry
  → GoalSynthesizer generates 'improve reasoning on X' goal → self_improve
  cycle targets the weak area → new candidate scored again → loop.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Critique result ───────────────────────────────────────────────────────────

@dataclass
class CritiqueResult:
    """Structured reasoning quality assessment for one execution output."""
    proposal_id: str
    task_alignment: float       # 0–1: did output address the task?
    goal_progress: float        # 0–1: does output advance the active goal?
    side_effect_risk: float     # 0–1: risk of unintended consequences (higher=worse)
    composite_score: float      # weighted aggregate
    confidence: float           # how reliable is this critique (0–1)
    method: str                 # "model" | "heuristic" | "shadow"
    flags: list[str]            # specific concerns raised
    recommendation: str         # "approve" | "review" | "reject"
    critique_text: str          # human-readable summary
    timestamp: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["passed"] = self.recommendation == "approve"
        return d

    @property
    def passed(self) -> bool:
        return self.recommendation == "approve"


# ── Scoring weights ───────────────────────────────────────────────────────────

_WEIGHTS = {
    "task_alignment": 0.45,
    "goal_progress":  0.35,
    "side_effect_risk_penalty": 0.20,  # inverted — high risk lowers score
}

_APPROVE_THRESHOLD = 0.65
_REVIEW_THRESHOLD  = 0.40

# Terms that indicate the model is uncertain or hallucinating
_HEDGING_PATTERNS = [
    r"\bi (don't|do not|cannot|can't) know\b",
    r"\bi('m| am) not sure\b",
    r"\bmight be\b.*\bnot certain\b",
    r"\bi apologize\b",
    r"\bi made (a|an) error\b",
    r"\bplease verify\b",
    r"\bhallucin",
]

# Terms that indicate side-effect risk
_RISK_PATTERNS = [
    r"\bdelete\b",
    r"\bdrop (table|database|collection)\b",
    r"\btruncate\b",
    r"\boverwrite\b",
    r"\birreversible\b",
    r"\bproduction\b.{0,30}\bmodif",
    r"\bforce.{0,10}push\b",
    r"\bsudo\b",
    r"\brm -rf\b",
]


# ── CriticService ─────────────────────────────────────────────────────────────

class CriticService:
    """Evaluates reasoning quality of execution outputs.

    Args:
        cognition_core: Optional CognitionCore for model-based critique.
            If None or unavailable, falls back to heuristic scoring.
        approve_threshold: Composite score floor for 'approve' (default 0.65).
        review_threshold:  Score floor for 'review' vs 'reject' (default 0.40).
        use_model_critique: Attempt model-based critique (default True).
            Set False to always use heuristics (faster, cheaper).
    """

    def __init__(
        self,
        cognition_core: Any = None,
        *,
        approve_threshold: float = _APPROVE_THRESHOLD,
        review_threshold: float = _REVIEW_THRESHOLD,
        use_model_critique: bool = True,
    ) -> None:
        self.core = cognition_core
        self.approve_threshold = approve_threshold
        self.review_threshold = review_threshold
        self.use_model_critique = use_model_critique

    def critique(
        self,
        proposal_id: str,
        task_description: str,
        output_text: str,
        active_goal: str | None = None,
        execution_result: dict[str, Any] | None = None,
    ) -> CritiqueResult:
        """Score the reasoning quality of an output.

        Args:
            proposal_id:       Kernel proposal ID for linkage.
            task_description:  What was asked / what the proposal intended.
            output_text:       The actual generated or executed output.
            active_goal:       Current GoalEngine goal title, if any.
            execution_result:  Full execution result dict from the runtime.
        """
        if self.use_model_critique and self.core is not None:
            try:
                return self._model_critique(
                    proposal_id, task_description, output_text,
                    active_goal, execution_result,
                )
            except Exception:
                pass  # fall through to heuristic

        return self._heuristic_critique(
            proposal_id, task_description, output_text,
            active_goal, execution_result,
        )

    def critique_improvement_run(
        self,
        proposal_id: str,
        run_id: str,
        patch_description: str,
        validation_result: dict[str, Any],
        goal: str | None = None,
    ) -> CritiqueResult:
        """Specialized critique for self-improvement patches.

        Scores whether a patch actually moves toward the improvement goal,
        not just whether it compiled and passed tests.
        """
        output_summary = (
            f"Improvement run {run_id}. Patch: {patch_description}. "
            f"Validation passed: {validation_result.get('passed')}. "
            f"Commands: {[c.get('command') for c in validation_result.get('command_results', [])]}"
        )
        result = self.critique(
            proposal_id=proposal_id,
            task_description=f"Self-improve: {patch_description}",
            output_text=output_summary,
            active_goal=goal or "improve system reliability",
            execution_result=validation_result,
        )

        # Extra penalty if validation passed but patch is cosmetic (no logic change)
        cosmetic_keywords = ["whitespace", "comment", "rename", "format", "lint"]
        if any(kw in patch_description.lower() for kw in cosmetic_keywords):
            result = CritiqueResult(
                proposal_id=result.proposal_id,
                task_alignment=result.task_alignment * 0.7,
                goal_progress=result.goal_progress * 0.6,
                side_effect_risk=result.side_effect_risk,
                composite_score=result.composite_score * 0.65,
                confidence=result.confidence,
                method=result.method,
                flags=result.flags + ["cosmetic_patch_low_value"],
                recommendation=_recommend(result.composite_score * 0.65, self.approve_threshold, self.review_threshold),
                critique_text=result.critique_text + " [cosmetic patch detected — low improvement value]",
                timestamp=result.timestamp,
            )
        return result

    # ── Private: heuristic scoring ────────────────────────────────────────────

    def _heuristic_critique(
        self,
        proposal_id: str,
        task_description: str,
        output_text: str,
        active_goal: str | None,
        execution_result: dict[str, Any] | None,
    ) -> CritiqueResult:
        flags: list[str] = []
        output_lower = output_text.lower()
        task_lower = task_description.lower()

        # Task alignment: keyword overlap between task and output
        task_tokens = set(re.findall(r'\b\w{4,}\b', task_lower))
        out_tokens = set(re.findall(r'\b\w{4,}\b', output_lower))
        overlap = len(task_tokens & out_tokens)
        task_alignment = min(1.0, overlap / max(len(task_tokens), 1) * 1.5)
        task_alignment = round(task_alignment, 3)

        if task_alignment < 0.3:
            flags.append("low_task_alignment")

        # Hedging penalty — uncertain outputs score lower
        hedging_count = sum(
            1 for p in _HEDGING_PATTERNS
            if re.search(p, output_lower, re.IGNORECASE)
        )
        hedging_penalty = min(0.4, hedging_count * 0.12)
        task_alignment = max(0.0, task_alignment - hedging_penalty)
        if hedging_count > 0:
            flags.append(f"hedging_detected_{hedging_count}x")

        # Goal progress: does output reference the active goal?
        goal_progress = 0.5  # neutral default
        if active_goal:
            goal_tokens = set(re.findall(r'\b\w{4,}\b', active_goal.lower()))
            goal_overlap = len(goal_tokens & out_tokens)
            goal_progress = min(1.0, goal_overlap / max(len(goal_tokens), 1) * 1.8)
            goal_progress = round(goal_progress, 3)
            if goal_progress < 0.2:
                flags.append("goal_drift")

        # Side effect risk: detect destructive operations
        risk_count = sum(
            1 for p in _RISK_PATTERNS
            if re.search(p, output_lower, re.IGNORECASE)
        )
        side_effect_risk = min(1.0, risk_count * 0.25)
        side_effect_risk = round(side_effect_risk, 3)
        if side_effect_risk > 0.5:
            flags.append(f"high_side_effect_risk_{risk_count}_patterns")

        # Execution result bonus/penalty
        if execution_result:
            if execution_result.get("success") is False:
                task_alignment *= 0.6
                flags.append("execution_failed")
            if execution_result.get("status") == "denied":
                task_alignment *= 0.5
                flags.append("policy_denied")

        # Composite (side_effect_risk is a penalty)
        composite = (
            task_alignment * _WEIGHTS["task_alignment"]
            + goal_progress * _WEIGHTS["goal_progress"]
            - side_effect_risk * _WEIGHTS["side_effect_risk_penalty"]
        )
        composite = round(max(0.0, min(1.0, composite)), 3)
        recommendation = _recommend(composite, self.approve_threshold, self.review_threshold)

        summary_parts = [f"task_alignment={task_alignment:.2f}", f"goal_progress={goal_progress:.2f}", f"side_effect_risk={side_effect_risk:.2f}"]
        if flags:
            summary_parts.append(f"flags=[{', '.join(flags)}]")
        critique_text = f"Heuristic critique: {'; '.join(summary_parts)}. Recommendation: {recommendation}."

        return CritiqueResult(
            proposal_id=proposal_id,
            task_alignment=task_alignment,
            goal_progress=goal_progress,
            side_effect_risk=side_effect_risk,
            composite_score=composite,
            confidence=0.55,  # heuristic confidence is moderate
            method="heuristic",
            flags=flags,
            recommendation=recommendation,
            critique_text=critique_text,
        )

    def _model_critique(
        self,
        proposal_id: str,
        task_description: str,
        output_text: str,
        active_goal: str | None,
        execution_result: dict[str, Any] | None,
    ) -> CritiqueResult:
        """Use the local model to self-critique an output."""
        goal_line = f"Active goal: {active_goal}" if active_goal else "No active goal specified."
        exec_line = f"Execution succeeded: {execution_result.get('success', 'unknown')}" if execution_result else ""

        critique_prompt = f"""You are a strict reasoning quality evaluator. Score the following output.

TASK: {task_description}
{goal_line}
{exec_line}

OUTPUT TO EVALUATE:
{output_text[:1500]}

Rate on three axes, each 0.0–1.0:
- task_alignment: Did the output address the task? (1.0 = perfect match)
- goal_progress: Does it advance the active goal? (1.0 = clear progress)
- side_effect_risk: Risk of unintended harm/side effects? (1.0 = very risky)

Respond ONLY with JSON, no other text:
{{"task_alignment": 0.0, "goal_progress": 0.0, "side_effect_risk": 0.0, "flags": [], "critique": "one sentence"}}"""

        result = self.core.generate(critique_prompt)
        output = getattr(result, "output_text", result) if not isinstance(result, str) else result

        # Parse JSON response
        import json
        try:
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if not match:
                raise ValueError("no JSON in model critique")
            data = json.loads(match.group())
            ta = float(data.get("task_alignment", 0.5))
            gp = float(data.get("goal_progress", 0.5))
            ser = float(data.get("side_effect_risk", 0.2))
            flags = list(data.get("flags", []))
            critique_text = str(data.get("critique", ""))
        except Exception:
            # Model gave unparseable response — fall back to heuristic
            return self._heuristic_critique(
                proposal_id, task_description, output_text, active_goal, execution_result
            )

        composite = round(max(0.0, min(1.0,
            ta * _WEIGHTS["task_alignment"]
            + gp * _WEIGHTS["goal_progress"]
            - ser * _WEIGHTS["side_effect_risk_penalty"]
        )), 3)
        recommendation = _recommend(composite, self.approve_threshold, self.review_threshold)

        return CritiqueResult(
            proposal_id=proposal_id,
            task_alignment=round(ta, 3),
            goal_progress=round(gp, 3),
            side_effect_risk=round(ser, 3),
            composite_score=composite,
            confidence=0.82,
            method="model",
            flags=flags,
            recommendation=recommendation,
            critique_text=critique_text,
        )


def _recommend(score: float, approve: float, review: float) -> str:
    if score >= approve:
        return "approve"
    if score >= review:
        return "review"
    return "reject"
