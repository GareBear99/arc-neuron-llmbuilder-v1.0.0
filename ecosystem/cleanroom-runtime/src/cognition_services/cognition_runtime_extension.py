"""cognition_runtime_extension.py — wires CognitionCore into LuciferRuntime.

Rather than rewriting the entire runtime.py, this module provides:

  1. `build_cognition_core(runtime)` — constructs and wires CognitionCore +
     FallbackConsciousnessLayer + StreamSessionManager into an existing
     LuciferRuntime instance.

  2. `CognitionRuntimeMixin` — methods to add to LuciferRuntime (or call
     standalone) for streaming sessions, tier management, and status.

Call `build_cognition_core(runtime)` once after constructing your runtime:

    from lucifer_runtime.runtime import LuciferRuntime
    from cognition_services.cognition_runtime_extension import build_cognition_core

    runtime = LuciferRuntime(workspace_root="/my/project")
    core, consciousness, sessions = build_cognition_core(runtime)

    # Register your backends
    from model_services import LlamafileBackend, LlamafileProcessManager
    from cognition_services import TIER_PRIMARY, TIER_SECONDARY

    core.add_tier(TIER_PRIMARY, LlamafileBackend(...), capabilities=["generate", "stream", "code", "plan"])
    core.add_tier(TIER_SECONDARY, my_api_backend, capabilities=["generate", "stream"])
    # TIER_ECHO is always present automatically

    # Start a streaming session the operator can talk to mid-stream
    session = sessions.begin(core, "explain the current world state")
    for event in session.stream():
        print(event.text, end="", flush=True)

    # Inject mid-stream from another thread or the operator interface
    session.inject("focus on the memory subsystem specifically")
    session.redirect("actually, what's the status of the FixNet?")
    session.interrupt()
"""
from __future__ import annotations

from typing import Any, Iterator

from cognition_services.cognition_core import (
    CognitionCore, TierChangeEvent,
    TIER_PRIMARY, TIER_SECONDARY, TIER_LOCAL, TIER_ECHO,
)
from cognition_services.fallback_consciousness import FallbackConsciousnessLayer
from cognition_services.stream_session import StreamSession, StreamSessionManager, StreamReceipt
from model_services.interfaces import StreamEvent


def build_cognition_core(
    runtime: Any,
    *,
    recovery_probe_interval_s: float = 60.0,
    improvement_cooldown_s: float = 30.0,
) -> tuple[CognitionCore, FallbackConsciousnessLayer, StreamSessionManager]:
    """Construct and fully wire CognitionCore into an existing runtime.

    Returns (core, consciousness, sessions) — all three are stored on
    the runtime as runtime.cognition_core, runtime.consciousness,
    runtime.stream_sessions for convenience.
    """
    world_model = getattr(runtime, "world_model", None)

    core = CognitionCore(recovery_probe_interval_s=recovery_probe_interval_s)
    consciousness = FallbackConsciousnessLayer(
        core,
        improvement_cooldown_s=improvement_cooldown_s,
    )
    sessions = StreamSessionManager()

    # Wire tier-change callback
    core.on_tier_change = consciousness.on_tier_change

    # Wire runtime + world model into consciousness
    consciousness.wire(runtime=runtime, world_model=world_model)

    # Start background recovery probe
    core.start_recovery_probe()

    # Attach to runtime for easy access
    runtime.cognition_core = core
    runtime.consciousness = consciousness
    runtime.stream_sessions = sessions

    return core, consciousness, sessions


# ── Standalone streaming helpers (usable with or without runtime) ─────────────

def stream_with_consciousness(
    core: CognitionCore,
    consciousness: FallbackConsciousnessLayer,
    sessions: StreamSessionManager,
    prompt: str,
    *,
    session_id: str | None = None,
    context: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    on_tier_switch: Any = None,
) -> tuple[StreamSession, Iterator[StreamEvent]]:
    """Begin a streaming session with full consciousness prefix injection.

    Returns (session, event_iterator). Iterate the event_iterator to stream.
    The session object gives you inject/interrupt/redirect controls.

    Example::

        session, events = stream_with_consciousness(core, consciousness, sessions,
                                                    "what is the world model state?")
        for event in events:
            print(event.text, end="", flush=True)
            # From another thread: session.inject("also check perception alerts")
    """
    prefix = consciousness.build_prefix()  # None when healthy, descriptive when degraded
    session = sessions.begin(
        core,
        prompt,
        session_id=session_id,
        context=context,
        options=options,
        consciousness_prefix=prefix,
    )
    return session, session.stream()


def cognition_status(
    core: CognitionCore,
    consciousness: FallbackConsciousnessLayer,
    sessions: StreamSessionManager,
) -> dict[str, Any]:
    """Unified status dict for dashboard/kernel logging."""
    return {
        "cognition_core": core.status(),
        "fallback_consciousness": consciousness.fallback_stats(),
        "stream_sessions": sessions.status(),
        "prefix_active": consciousness.build_prefix() is not None,
    }


# ── Runtime method patches (monkey-patch onto existing LuciferRuntime) ────────

def patch_runtime(runtime: Any) -> None:
    """Add cognition-core methods directly to an existing LuciferRuntime instance.

    Call after build_cognition_core(runtime). Adds:
      - runtime.cognition_stream(prompt, ...)
      - runtime.cognition_inject(session_id, text)
      - runtime.cognition_interrupt(session_id)
      - runtime.cognition_redirect(session_id, new_prompt)
      - runtime.cognition_status()
      - runtime.cognition_tier_status()
    """

    core: CognitionCore = runtime.cognition_core
    consciousness: FallbackConsciousnessLayer = runtime.consciousness
    sessions: StreamSessionManager = runtime.stream_sessions

    def _cognition_stream(
        prompt: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[StreamSession, Iterator[StreamEvent]]:
        """Begin a new streaming session through the consciousness layer.

        Returns (session, event_iterator).
        - Iterate events to stream tokens.
        - Call session.inject(text) mid-stream to talk to the running generation.
        - Call session.interrupt() to stop cleanly.
        - Call session.redirect(new_prompt) to abandon and restart in-session.

        Emits kernel evaluation events on every tier switch and completion.
        """
        kernel = getattr(runtime, "kernel", None)
        if kernel:
            kernel.record_evaluation("cognition", {
                "kind": "cognition_stream_begin",
                "session_id": session_id,
                "prompt_chars": len(prompt),
                "tier": core.active_tier,
                "is_degraded": core.is_degraded,
            })

        session, events_iter = stream_with_consciousness(
            core, consciousness, sessions, prompt,
            session_id=session_id, context=context, options=options,
        )

        def _instrumented_events() -> Iterator[StreamEvent]:
            for event in events_iter:
                yield event
            # After completion, emit kernel event and record trust
            receipt = session.receipt
            if receipt and kernel:
                kernel.record_evaluation("cognition", {
                    "kind": "cognition_stream_complete",
                    **receipt.to_dict(),
                    "tier": core.active_tier,
                })
            if receipt:
                try:
                    runtime.record_tool_outcome(
                        f"cognition_tier_{receipt.tier_used}",
                        succeeded=receipt.final_status == "complete",
                        notes=f"stream session {receipt.session_id}",
                        evidence={"receipt": receipt.to_dict()},
                    )
                except Exception:
                    pass

        return session, _instrumented_events()

    def _cognition_inject(session_id: str, text: str) -> dict[str, Any]:
        ok = sessions.inject(session_id, text)
        kernel = getattr(runtime, "kernel", None)
        if kernel:
            kernel.record_evaluation("cognition", {
                "kind": "cognition_inject",
                "session_id": session_id,
                "text_chars": len(text),
                "found": ok,
            })
        return {"status": "ok" if ok else "not_found", "session_id": session_id}

    def _cognition_interrupt(session_id: str) -> dict[str, Any]:
        ok = sessions.interrupt(session_id)
        return {"status": "ok" if ok else "not_found", "session_id": session_id}

    def _cognition_redirect(session_id: str, new_prompt: str) -> dict[str, Any]:
        ok = sessions.redirect(session_id, new_prompt)
        return {"status": "ok" if ok else "not_found", "session_id": session_id}

    def _cognition_status() -> dict[str, Any]:
        return {"status": "ok", **cognition_status(core, consciousness, sessions)}

    def _cognition_tier_status() -> dict[str, Any]:
        return {"status": "ok", **core.status()}

    runtime.cognition_stream = _cognition_stream
    runtime.cognition_inject = _cognition_inject
    runtime.cognition_interrupt = _cognition_interrupt
    runtime.cognition_redirect = _cognition_redirect
    runtime.cognition_status = _cognition_status
    runtime.cognition_tier_status = _cognition_tier_status
