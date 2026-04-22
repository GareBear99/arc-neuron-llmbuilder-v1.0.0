"""ImmutableBaseline — explicit protection policy for critical runtime files.

A self-modifying system that can patch its own policy engine, its own
critic, or its own fallback layer is a system that can reason its way
around its own guardrails. This module makes the protection explicit and
enforced at the PolicyEngine level, not just by convention.

ImmutableBaseline maintains a manifest of protected paths and subsystems.
Any SelfImprove patch targeting a protected path is:
  1. Intercepted before promotion
  2. Logged as a policy violation in the kernel event log
  3. Blocked — requires explicit operator override with reason

Three protection tiers:
  FROZEN     — never modifiable without operator override + audit event
  GUARDED    — modifiable only after DriftDetector confirms no active drift
               AND CriticService scores the patch >= 0.80
  SUPERVISED — modifiable with standard review, but flagged for extra audit

Default manifest protects:
  FROZEN:     policy, verifier, drift_detector, immutable_baseline itself,
              arc_kernel (schemas, engine, event_log)
  GUARDED:    critic, fallback_consciousness, cognition_core, stream_session
  SUPERVISED: fixnet, memory_subsystem, curriculum_trainer

Operator override:
  runtime.immutable_baseline.override(path, reason="...", operator="gary")
  Creates a time-limited window (default 300s) for that path.
  Kernel event emitted. Window expires automatically.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProtectionTier(str, Enum):
    FROZEN     = "frozen"
    GUARDED    = "guarded"
    SUPERVISED = "supervised"


@dataclass
class ProtectedPath:
    path_pattern: str          # glob or exact path fragment
    tier: ProtectionTier
    reason: str
    added_at: str = field(default_factory=_utcnow)

    def matches(self, candidate: str) -> bool:
        """True if candidate path contains this pattern."""
        return self.path_pattern.lower() in candidate.lower()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d


@dataclass
class OverrideWindow:
    path_pattern: str
    reason: str
    operator: str
    expires_at: float     # monotonic time
    granted_at: str = field(default_factory=_utcnow)

    @property
    def active(self) -> bool:
        return time.monotonic() < self.expires_at


@dataclass
class BaselineDecision:
    allowed: bool
    tier: ProtectionTier | None
    reason: str
    requires_override: bool = False
    audit_required: bool = False
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "tier": self.tier.value if self.tier else None,
            "reason": self.reason,
            "requires_override": self.requires_override,
            "audit_required": self.audit_required,
            "path": self.path,
        }


# ── Default manifest ──────────────────────────────────────────────────────────

def _default_manifest() -> list[ProtectedPath]:
    """Default protection manifest. Never modify without operator sign-off."""
    frozen = [
        # Core kernel — audit trail integrity is paramount
        ("arc_kernel/schemas",    "Kernel event schema is the source of truth for replay"),
        ("arc_kernel/engine",     "Kernel engine manages the entire audit log"),
        ("arc_kernel/event_log",  "Event log persistence — corruption is unrecoverable"),
        ("arc_kernel/policy",     "Policy engine must not be self-modified"),
        # Safety systems
        ("verifier/",             "Verifier layer must not be self-modified"),
        ("verifier/safety",       "Workspace safety bounds — escape is critical failure"),
        # Drift and baseline — the guardians cannot guard themselves
        ("drift_detector",        "DriftDetector must not be modified while active"),
        ("immutable_baseline",    "ImmutableBaseline cannot modify its own rules"),
        # Fallback system — must survive any model failure
        ("resilience/continuity", "Continuity shell is the last recovery surface"),
        ("resilience/fallback_p", "Fallback policy must be stable"),
    ]
    guarded = [
        ("cognition_services/critic",               "CriticService scores patch quality — must not be self-optimized away"),
        ("cognition_services/fallback_consciousness","Consciousness layer must remain independent of execution"),
        ("cognition_services/cognition_core",        "CognitionCore tier logic — self-modification risks infinite loop"),
        ("cognition_services/stream_session",        "StreamSession injection API — modification could expose operator"),
        ("cognition_services/goal_synthesizer",      "GoalSynthesizer rules — self-modification could suppress safety goals"),
    ]
    supervised = [
        ("fixnet/",               "FixNet is high-value — changes should be audited"),
        ("memory_subsystem/",     "Memory system changes affect long-term state"),
        ("cognition_services/curriculum_trainer", "Training pipeline — changes affect future model behavior"),
        ("self_improve/promotion","Promotion gate — loosening it requires audit"),
    ]
    result = []
    for pattern, reason in frozen:
        result.append(ProtectedPath(pattern, ProtectionTier.FROZEN, reason))
    for pattern, reason in guarded:
        result.append(ProtectedPath(pattern, ProtectionTier.GUARDED, reason))
    for pattern, reason in supervised:
        result.append(ProtectedPath(pattern, ProtectionTier.SUPERVISED, reason))
    return result


# ── ImmutableBaseline ─────────────────────────────────────────────────────────

class ImmutableBaseline:
    """Policy enforcement layer for protected runtime files.

    Args:
        workspace_root: Runtime workspace root.
        runtime:        LuciferRuntime for kernel event emission.
        drift_detector: DriftDetector for GUARDED tier checks.
        guarded_critic_threshold: Minimum CriticService score for GUARDED patches.
        custom_manifest: Additional ProtectedPath entries.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        runtime: Any = None,
        *,
        drift_detector: Any = None,
        guarded_critic_threshold: float = 0.80,
        custom_manifest: list[ProtectedPath] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self._runtime = runtime
        self._drift_detector = drift_detector
        self.guarded_critic_threshold = guarded_critic_threshold

        self._manifest: list[ProtectedPath] = _default_manifest()
        if custom_manifest:
            self._manifest.extend(custom_manifest)

        self._overrides: list[OverrideWindow] = []
        self._violation_count = 0
        self._violation_log: list[dict[str, Any]] = []

        # Persist manifest
        self._manifest_path = (
            self.workspace_root / ".arc_lucifer" / "immutable_baseline.json"
        )
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_manifest()

    # ── Core check ────────────────────────────────────────────────────────────

    def check(
        self,
        path: str,
        critique_score: float | None = None,
    ) -> BaselineDecision:
        """Check whether a patch to `path` is permitted under current policy.

        Args:
            path:           Path of the file being patched (relative or absolute).
            critique_score: CriticService score for the proposed patch.
                            Required for GUARDED tier checks.

        Returns:
            BaselineDecision. If `allowed=False`, do NOT apply the patch.
        """
        canonical = str(path).replace("\\", "/")

        # Check active overrides first
        active_overrides = [o for o in self._overrides if o.active and o.path_pattern in canonical]
        if active_overrides:
            ov = active_overrides[0]
            self._emit_kernel("baseline_override_used", {
                "path": canonical, "operator": ov.operator, "reason": ov.reason
            })
            return BaselineDecision(
                allowed=True, tier=None, audit_required=True,
                reason=f"operator override active (expires in {ov.expires_at - time.monotonic():.0f}s)",
                path=canonical,
            )

        # Find matching protection
        matched: list[ProtectedPath] = []
        for pp in self._manifest:
            if pp.matches(canonical):
                matched.append(pp)

        if not matched:
            return BaselineDecision(
                allowed=True, tier=None,
                reason="path not in protection manifest",
                path=canonical,
            )

        # Use highest tier match
        tier_order = {ProtectionTier.FROZEN: 0, ProtectionTier.GUARDED: 1, ProtectionTier.SUPERVISED: 2}
        worst = min(matched, key=lambda p: tier_order[p.tier])
        tier = worst.tier

        if tier == ProtectionTier.FROZEN:
            self._record_violation(canonical, tier, "frozen path requires operator override")
            return BaselineDecision(
                allowed=False, tier=tier,
                reason=f"FROZEN: {worst.reason}. Operator override required.",
                requires_override=True, audit_required=True,
                path=canonical,
            )

        if tier == ProtectionTier.GUARDED:
            # Block if drift is active
            if self._drift_detector and self._drift_detector.drift_detected:
                self._record_violation(canonical, tier, "drift active — guarded path blocked")
                return BaselineDecision(
                    allowed=False, tier=tier,
                    reason="GUARDED: drift detected — no modifications while system is drifting.",
                    requires_override=False, audit_required=True,
                    path=canonical,
                )
            # Require sufficient critique score
            if critique_score is not None and critique_score < self.guarded_critic_threshold:
                self._record_violation(canonical, tier, f"critique score {critique_score:.2f} below {self.guarded_critic_threshold}")
                return BaselineDecision(
                    allowed=False, tier=tier,
                    reason=f"GUARDED: critique score {critique_score:.2f} < threshold {self.guarded_critic_threshold}.",
                    requires_override=False, audit_required=True,
                    path=canonical,
                )
            if critique_score is None:
                return BaselineDecision(
                    allowed=False, tier=tier,
                    reason="GUARDED: critique score required but not provided.",
                    requires_override=False, audit_required=True,
                    path=canonical,
                )
            self._emit_kernel("baseline_guarded_approved", {"path": canonical, "critique_score": critique_score})
            return BaselineDecision(
                allowed=True, tier=tier,
                reason=f"GUARDED: approved (score={critique_score:.2f})",
                audit_required=True,
                path=canonical,
            )

        # SUPERVISED
        self._emit_kernel("baseline_supervised_flagged", {"path": canonical})
        return BaselineDecision(
            allowed=True, tier=tier,
            reason="SUPERVISED: permitted but flagged for audit",
            audit_required=True,
            path=canonical,
        )

    # ── Override management ───────────────────────────────────────────────────

    def override(
        self,
        path_pattern: str,
        reason: str,
        operator: str = "operator",
        duration_s: float = 300.0,
    ) -> OverrideWindow:
        """Grant a time-limited override for a protected path.

        Always emits a kernel event. Override expires automatically.
        """
        ow = OverrideWindow(
            path_pattern=path_pattern,
            reason=reason,
            operator=operator,
            expires_at=time.monotonic() + duration_s,
        )
        self._overrides.append(ow)
        self._emit_kernel("baseline_override_granted", {
            "path_pattern": path_pattern,
            "reason": reason,
            "operator": operator,
            "duration_s": duration_s,
        })
        return ow

    def revoke_expired_overrides(self) -> int:
        before = len(self._overrides)
        self._overrides = [o for o in self._overrides if o.active]
        return before - len(self._overrides)

    # ── Status ────────────────────────────────────────────────────────────────

    def add_protection(self, path_pattern: str, tier: ProtectionTier, reason: str) -> None:
        """Add a new protected path at runtime. Persisted immediately."""
        pp = ProtectedPath(path_pattern=path_pattern, tier=tier, reason=reason)
        self._manifest.append(pp)
        self._save_manifest()
        self._emit_kernel("baseline_protection_added", pp.to_dict())

    def status(self) -> dict[str, Any]:
        return {
            "protected_paths": len(self._manifest),
            "frozen": sum(1 for p in self._manifest if p.tier == ProtectionTier.FROZEN),
            "guarded": sum(1 for p in self._manifest if p.tier == ProtectionTier.GUARDED),
            "supervised": sum(1 for p in self._manifest if p.tier == ProtectionTier.SUPERVISED),
            "active_overrides": sum(1 for o in self._overrides if o.active),
            "violation_count": self._violation_count,
            "recent_violations": self._violation_log[-10:],
            "manifest_path": str(self._manifest_path),
        }

    def manifest(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._manifest]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _record_violation(self, path: str, tier: ProtectionTier, reason: str) -> None:
        self._violation_count += 1
        record = {
            "timestamp": _utcnow(),
            "path": path,
            "tier": tier.value,
            "reason": reason,
        }
        self._violation_log.append(record)
        self._emit_kernel("baseline_violation", {"kind": "baseline_violation", **record})

    def _emit_kernel(self, kind: str, payload: dict) -> None:
        if not self._runtime:
            return
        kernel = getattr(self._runtime, "kernel", None)
        if kernel:
            try:
                kernel.record_evaluation("immutable_baseline", {"kind": kind, **payload})
            except Exception:
                pass

    def _save_manifest(self) -> None:
        try:
            self._manifest_path.write_text(
                json.dumps(
                    {"protected_paths": [p.to_dict() for p in self._manifest]},
                    indent=2, sort_keys=True,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
