"""CognitionCore — swappable, tiered, fallback-aware cognition backend.

This is the unified reasoning engine that replaces the scattered
BackendRegistry + prompt_model() pattern in LuciferRuntime. It owns:

  - An ordered list of backend tiers (primary → secondary → local → echo)
  - Automatic failover with full tier-state awareness
  - Injecting fallback context into prompts ("I am in tier-2 because X")
  - Emitting tier-change events to the kernel for audit/replay
  - Exposing the active tier so the rest of the system can gate behavior

Tier ladder (configured per deployment):
  primary    — best available model (70B GGUF, cloud API, etc.)
  secondary  — capable fallback (smaller GGUF, alternate API)
  local      — deterministic local stub (always available)
  echo       — identity stub (last resort, zero-dep)

Any StreamingModel-compatible backend can occupy any tier slot. The
CognitionCore does not care what the backend IS — only where it sits
in the priority ladder and whether it responds.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterator

from model_services.interfaces import BaseModel, StreamEvent, StreamingModel


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Tier definitions ─────────────────────────────────────────────────────────

TIER_PRIMARY   = "primary"
TIER_SECONDARY = "secondary"
TIER_LOCAL     = "local"
TIER_ECHO      = "echo"

TIER_ORDER = [TIER_PRIMARY, TIER_SECONDARY, TIER_LOCAL, TIER_ECHO]


@dataclass
class CognitionTier:
    """One slot in the backend ladder.

    Args:
        name:        Tier label — one of TIER_* constants.
        backend:     Any StreamingModel / BaseModel-compatible object.
        priority:    Lower = preferred. Derived from TIER_ORDER if not set.
        health_check: Optional callable() → bool. Called before each use.
            Return False to skip this tier even if it hasn't failed yet.
        capabilities: Free-form list of what this tier can do.
            Used to build the fallback context prefix injected into prompts.
    """
    name: str
    backend: Any
    priority: int = 0
    health_check: Callable[[], bool] | None = None
    capabilities: list[str] = field(default_factory=lambda: ["generate"])
    error_count: int = field(default=0, init=False)
    last_error: str = field(default="", init=False)
    last_used_at: str = field(default="", init=False)
    available: bool = field(default=True, init=False)

    def is_healthy(self) -> bool:
        if not self.available:
            return False
        if self.health_check is not None:
            try:
                return bool(self.health_check())
            except Exception:
                return False
        return True

    def record_failure(self, reason: str) -> None:
        self.error_count += 1
        self.last_error = reason
        if self.error_count >= 3:
            self.available = False

    def record_success(self) -> None:
        self.error_count = 0
        self.last_error = ""
        self.available = True
        self.last_used_at = _utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "priority": self.priority,
            "available": self.available,
            "healthy": self.is_healthy(),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_used_at": self.last_used_at,
            "capabilities": list(self.capabilities),
        }


# ── Tier-change event ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TierChangeEvent:
    from_tier: str
    to_tier: str
    reason: str
    timestamp: str
    direction: str  # "degraded" | "recovered"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "cognition_tier_change",
            "from_tier": self.from_tier,
            "to_tier": self.to_tier,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "direction": self.direction,
        }


# ── Echo stub (always-available last resort) ──────────────────────────────────

class _EchoBackend:
    """Zero-dependency stub that echoes the prompt back.

    The CognitionCore always adds this as the final tier automatically
    so there is always something that can respond, even with all models down.
    The FallbackConsciousnessLayer will prepend context explaining the state.
    """

    def generate(self, prompt: str, **_: Any) -> str:
        return f"[echo-stub] {prompt}"

    def stream_generate(self, prompt: str, **_: Any) -> Iterator[StreamEvent]:
        text = f"[echo-stub] {prompt}"
        yield StreamEvent(
            text=text,
            sequence=0,
            chars_emitted=len(text),
            words_emitted=len(text.split()),
            estimated_tokens=len(text) // 4,
            done=True,
        )


# ── CognitionCore ─────────────────────────────────────────────────────────────

class CognitionCore:
    """Tiered, fallback-aware cognition backend manager.

    Usage::

        core = CognitionCore()
        core.add_tier(TIER_PRIMARY,   my_llamafile_backend)
        core.add_tier(TIER_SECONDARY, my_api_backend)
        # TIER_LOCAL (echo stub) is always added automatically

        for event in core.stream(prompt, session_id="abc"):
            print(event.text, end="", flush=True)

    Args:
        on_tier_change: Optional callback(TierChangeEvent). Called synchronously
            on every tier switch so the runtime can emit kernel events and update
            world model before the next token arrives.
        recovery_probe_interval_s: How often (seconds) to re-probe disabled tiers
            and attempt recovery. Set 0 to disable. Default 60.
    """

    def __init__(
        self,
        on_tier_change: Callable[[TierChangeEvent], None] | None = None,
        recovery_probe_interval_s: float = 60.0,
    ) -> None:
        self._tiers: list[CognitionTier] = []
        self._active_tier_name: str = TIER_ECHO
        self._lock = threading.RLock()
        self.on_tier_change = on_tier_change
        self.recovery_probe_interval_s = recovery_probe_interval_s
        self._tier_change_history: list[TierChangeEvent] = []
        self._recovery_thread: threading.Thread | None = None

        # Echo stub always present as final tier
        self._echo_tier = CognitionTier(
            name=TIER_ECHO,
            backend=_EchoBackend(),
            priority=999,
            capabilities=["echo"],
        )
        self._echo_tier.available = True

    # ── Registration ──────────────────────────────────────────────────────────

    def add_tier(
        self,
        name: str,
        backend: Any,
        *,
        priority: int | None = None,
        health_check: Callable[[], bool] | None = None,
        capabilities: list[str] | None = None,
    ) -> "CognitionCore":
        """Register a backend at the given tier slot. Chainable."""
        if priority is None:
            priority = TIER_ORDER.index(name) if name in TIER_ORDER else 50
        tier = CognitionTier(
            name=name,
            backend=backend,
            priority=priority,
            health_check=health_check,
            capabilities=capabilities or ["generate", "stream"],
        )
        with self._lock:
            # Remove existing tier with same name
            self._tiers = [t for t in self._tiers if t.name != name]
            self._tiers.append(tier)
            self._tiers.sort(key=lambda t: t.priority)
            # Set active to best available
            self._active_tier_name = self._best_available_tier().name
        return self

    def remove_tier(self, name: str) -> None:
        with self._lock:
            self._tiers = [t for t in self._tiers if t.name != name]

    # ── Core generate interface ───────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        *,
        context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        session_id: str | None = None,
        consciousness_prefix: str | None = None,
    ) -> dict[str, Any]:
        """Generate with automatic tier failover. Returns full output dict."""
        full_prompt = self._build_prompt(prompt, consciousness_prefix)
        tier, result, used_fallback = self._execute_with_failover(
            full_prompt, context=context, options=options, stream=False
        )
        return {
            "output_text": result,
            "tier": tier.name,
            "used_fallback": used_fallback,
            "session_id": session_id,
        }

    def stream(
        self,
        prompt: str,
        *,
        context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        session_id: str | None = None,
        consciousness_prefix: str | None = None,
        on_tier_switch: Callable[[TierChangeEvent], None] | None = None,
    ) -> Iterator[StreamEvent]:
        """Stream with automatic mid-stream tier failover.

        If the primary tier fails mid-stream:
        1. The partial output is preserved.
        2. A TierChangeEvent is fired.
        3. The next tier picks up with full context of what was already emitted.
        4. A special StreamEvent with kind='tier_switch' is yielded so the caller
           can surface the transition to the operator in real time.
        """
        full_prompt = self._build_prompt(prompt, consciousness_prefix)
        yield from self._stream_with_failover(
            full_prompt,
            context=context,
            options=options,
            session_id=session_id,
            on_tier_switch=on_tier_switch,
        )

    # ── Status ───────────────────────────────────────────────────────────────

    @property
    def active_tier(self) -> str:
        with self._lock:
            return self._active_tier_name

    @property
    def is_degraded(self) -> bool:
        """True whenever the active tier is below primary — any fallback counts."""
        return self.active_tier != TIER_PRIMARY

    @property
    def degradation_depth(self) -> int:
        """0 = primary, 1 = secondary, 2 = local, 3 = echo."""
        try:
            return TIER_ORDER.index(self.active_tier)
        except ValueError:
            return len(TIER_ORDER)

    def status(self) -> dict[str, Any]:
        with self._lock:
            all_tiers = list(self._tiers) + [self._echo_tier]
            return {
                "active_tier": self._active_tier_name,
                "is_degraded": self.is_degraded,
                "degradation_depth": self.degradation_depth,
                "tiers": [t.to_dict() for t in all_tiers],
                "tier_change_count": len(self._tier_change_history),
                "recent_tier_changes": [e.to_dict() for e in self._tier_change_history[-5:]],
            }

    def active_capabilities(self) -> list[str]:
        with self._lock:
            tier = self._get_tier(self._active_tier_name)
            return list(tier.capabilities) if tier else ["echo"]

    # ── Recovery probing ─────────────────────────────────────────────────────

    def start_recovery_probe(self, daemon: bool = True) -> None:
        """Background thread that re-probes disabled tiers and attempts recovery."""
        if self.recovery_probe_interval_s <= 0:
            return
        if self._recovery_thread and self._recovery_thread.is_alive():
            return
        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            name="CognitionCoreRecovery",
            daemon=daemon,
        )
        self._recovery_thread.start()

    def _recovery_loop(self) -> None:
        while True:
            time.sleep(self.recovery_probe_interval_s)
            with self._lock:
                for tier in self._tiers:
                    if not tier.available and tier.error_count < 10:
                        tier.available = True  # tentative re-enable
                        if not tier.is_healthy():
                            tier.available = False  # re-disable if still unhealthy
                        else:
                            # Recovery — if this tier is better than current active
                            current_depth = self.degradation_depth
                            recovered_depth = TIER_ORDER.index(tier.name) if tier.name in TIER_ORDER else 99
                            if recovered_depth < current_depth:
                                prev = self._active_tier_name
                                self._active_tier_name = tier.name
                                evt = TierChangeEvent(
                                    from_tier=prev,
                                    to_tier=tier.name,
                                    reason=f"tier '{tier.name}' recovered during background probe",
                                    timestamp=_utcnow(),
                                    direction="recovered",
                                )
                                self._record_tier_change(evt)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _best_available_tier(self) -> CognitionTier:
        for tier in self._tiers:
            if tier.is_healthy():
                return tier
        return self._echo_tier

    def _get_tier(self, name: str) -> CognitionTier | None:
        if name == TIER_ECHO:
            return self._echo_tier
        return next((t for t in self._tiers if t.name == name), None)

    def _build_prompt(self, prompt: str, consciousness_prefix: str | None) -> str:
        if consciousness_prefix:
            return f"{consciousness_prefix}\n\n{prompt}"
        return prompt

    def _record_tier_change(self, evt: TierChangeEvent) -> None:
        """Record and fire callbacks. Must be called under self._lock."""
        self._tier_change_history.append(evt)
        if self.on_tier_change:
            try:
                self.on_tier_change(evt)
            except Exception:
                pass

    def _execute_with_failover(
        self,
        prompt: str,
        *,
        context: dict[str, Any] | None,
        options: dict[str, Any] | None,
        stream: bool,
    ) -> tuple[CognitionTier, Any, bool]:
        with self._lock:
            ordered = list(self._tiers) + [self._echo_tier]

        used_fallback = False
        prev_tier_name = self._active_tier_name

        for tier in ordered:
            if not tier.is_healthy():
                continue
            try:
                if stream:
                    result = tier.backend.stream_generate(prompt, context=context, options=options)
                else:
                    result = tier.backend.generate(prompt, context=context, options=options)
                tier.record_success()
                with self._lock:
                    if self._active_tier_name != tier.name:
                        direction = (
                            "recovered"
                            if TIER_ORDER.index(tier.name) < TIER_ORDER.index(prev_tier_name)
                            else "degraded"
                        ) if tier.name in TIER_ORDER and prev_tier_name in TIER_ORDER else "degraded"
                        evt = TierChangeEvent(
                            from_tier=prev_tier_name,
                            to_tier=tier.name,
                            reason=f"switched from '{prev_tier_name}' (unavailable) to '{tier.name}'",
                            timestamp=_utcnow(),
                            direction=direction,
                        )
                        self._active_tier_name = tier.name
                        self._record_tier_change(evt)
                        used_fallback = tier.name != TIER_PRIMARY
                return tier, result, used_fallback
            except Exception as exc:
                tier.record_failure(str(exc))
                continue

        # Should never reach here — echo always succeeds
        return self._echo_tier, "[echo-stub] all tiers exhausted", True

    def _stream_with_failover(
        self,
        prompt: str,
        *,
        context: dict[str, Any] | None,
        options: dict[str, Any] | None,
        session_id: str | None,
        on_tier_switch: Callable[[TierChangeEvent], None] | None,
    ) -> Iterator[StreamEvent]:
        with self._lock:
            ordered = list(self._tiers) + [self._echo_tier]

        partial_text = ""
        prev_tier_name = self._active_tier_name

        for tier_idx, tier in enumerate(ordered):
            if not tier.is_healthy():
                continue

            # If we have partial output from a failed tier, rebuild the prompt
            # so the next tier continues from where the last one stopped
            active_prompt = prompt
            if partial_text:
                active_prompt = (
                    f"{prompt}\n\n[CONTINUATION — previous tier '{prev_tier_name}' failed "
                    f"mid-stream after emitting the following partial output. "
                    f"Continue seamlessly from where it left off:]\n\n{partial_text}"
                )

            try:
                if tier.name != prev_tier_name:
                    direction = "recovered" if (
                        tier.name in TIER_ORDER and prev_tier_name in TIER_ORDER and
                        TIER_ORDER.index(tier.name) < TIER_ORDER.index(prev_tier_name)
                    ) else "degraded"
                    evt = TierChangeEvent(
                        from_tier=prev_tier_name,
                        to_tier=tier.name,
                        reason=f"stream tier switch from '{prev_tier_name}' to '{tier.name}'"
                               + (f" (resuming after {len(partial_text)} chars)" if partial_text else ""),
                        timestamp=_utcnow(),
                        direction=direction,
                    )
                    with self._lock:
                        self._active_tier_name = tier.name
                        self._record_tier_change(evt)
                    if on_tier_switch:
                        try:
                            on_tier_switch(evt)
                        except Exception:
                            pass
                    # Yield a special meta-event so streaming callers can surface this
                    yield StreamEvent(
                        text=f"\n[cognition tier switch: {prev_tier_name} → {tier.name}]\n",
                        sequence=-1,
                        chars_emitted=0,
                        words_emitted=0,
                        estimated_tokens=0,
                        done=False,
                    )
                    prev_tier_name = tier.name

                stream_iter = tier.backend.stream_generate(
                    active_prompt, context=context, options=options
                )
                for event in stream_iter:
                    if event.text:
                        partial_text += event.text
                    tier.record_success()
                    yield event
                    if event.done:
                        return  # clean completion

            except Exception as exc:
                tier.record_failure(str(exc))
                # Don't return — try next tier with accumulated partial_text
                continue

        # Absolute fallback
        fallback_text = f"[echo-stub: all tiers failed] {prompt}"
        yield StreamEvent(
            text=fallback_text,
            sequence=0,
            chars_emitted=len(fallback_text),
            words_emitted=len(fallback_text.split()),
            estimated_tokens=len(fallback_text) // 4,
            done=True,
        )
