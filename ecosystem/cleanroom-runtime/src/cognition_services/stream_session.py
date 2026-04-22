"""StreamSession — interactive streaming with mid-stream operator injection.

This is the WarpAI-style "talk to it while it's running" interface.

The operator can:
  - inject(text)     — queue a message that the session will surface on the
                       next chunk boundary and incorporate into continued generation
  - interrupt()      — stop cleanly with a partial receipt
  - redirect(prompt) — abandon current generation, start fresh in same session
                       with full context of what was already emitted
  - pause() / resume()

The session emits a unified stream of StreamEvent objects that includes both
model tokens and control events (injections, tier switches, pauses).
Callers iterate a single generator — the session handles all internal state.

Architecture:

    operator thread           session thread
    ─────────────             ──────────────────────────────────
    session.inject("stop")    → injection_queue.put(...)
                              → on next chunk: yield InjectionEvent
                              → rebuild prompt with injection context
                              → continue generation from that point

    session.interrupt()       → stop_event.set()
                              → generator exits, partial receipt emitted

    session.redirect(p)       → redirect_queue.put(p)
                              → generator abandons current stream
                              → restarts with new prompt + history context
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import uuid4

from model_services.interfaces import StreamEvent


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Session events ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SessionMeta:
    """Non-token event yielded inline with the stream."""
    kind: str          # "injection" | "redirect" | "paused" | "resumed" | "interrupted"
    content: str = ""
    timestamp: str = field(default_factory=_utcnow)

    def as_stream_event(self) -> StreamEvent:
        marker = f"\n[session:{self.kind}] {self.content}\n"
        return StreamEvent(
            text=marker,
            sequence=-1,
            chars_emitted=len(marker),
            words_emitted=len(marker.split()),
            estimated_tokens=0,
            done=False,
        )


@dataclass
class StreamReceipt:
    """Produced at the end of every session generation, successful or not."""
    session_id: str
    prompt: str
    output_text: str
    tier_used: str
    token_count: int
    elapsed_s: float
    interrupted: bool
    injections: list[str]
    redirects: int
    final_status: str  # "complete" | "interrupted" | "redirected" | "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "prompt_chars": len(self.prompt),
            "output_chars": len(self.output_text),
            "tier_used": self.tier_used,
            "token_count": self.token_count,
            "elapsed_s": round(self.elapsed_s, 3),
            "interrupted": self.interrupted,
            "injection_count": len(self.injections),
            "injections": self.injections,
            "redirects": self.redirects,
            "final_status": self.final_status,
        }


# ── StreamSession ─────────────────────────────────────────────────────────────

class StreamSession:
    """One interactive streaming conversation with the cognition core.

    Create via StreamSessionManager.begin(), not directly.

    Args:
        session_id: Unique session identifier.
        cognition_core: CognitionCore instance to generate from.
        initial_prompt: First prompt to begin streaming.
        context: Passed through to backend.stream_generate().
        options: Passed through to backend.stream_generate().
        consciousness_prefix: Injected by FallbackConsciousnessLayer when degraded.
        history_window: Max chars of prior output to include when rebuilding
            prompts after injection or redirect (default 2000).
    """

    def __init__(
        self,
        session_id: str,
        cognition_core: Any,  # CognitionCore — avoid circular import
        initial_prompt: str,
        *,
        context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        consciousness_prefix: str | None = None,
        history_window: int = 2000,
    ) -> None:
        self.session_id = session_id
        self.core = cognition_core
        self.initial_prompt = initial_prompt
        self.context = context or {}
        self.options = options or {}
        self.consciousness_prefix = consciousness_prefix
        self.history_window = history_window

        self._output_buffer: list[str] = []
        self._injections: list[str] = []
        self._redirect_count = 0
        self._start_time = time.monotonic()

        self._injection_queue: queue.Queue[str] = queue.Queue()
        self._redirect_queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially

        self._lock = threading.Lock()
        self._final_receipt: StreamReceipt | None = None
        self._token_count = 0

    # ── Operator control API (safe to call from any thread) ───────────────────

    def inject(self, text: str) -> None:
        """Queue operator text to be surfaced at next chunk boundary.

        The session will yield a SessionMeta event, then rebuild the prompt
        as: [original_prompt] + [output so far] + [injection] → continue.
        """
        self._injection_queue.put(text)
        self._injections.append(text)

    def interrupt(self) -> None:
        """Stop generation cleanly. A StreamReceipt will be emitted."""
        self._stop_event.set()

    def redirect(self, new_prompt: str) -> None:
        """Abandon current generation and start fresh with new_prompt.

        History context is preserved in the rebuilt prompt.
        """
        self._redirect_queue.put(new_prompt)

    def pause(self) -> None:
        """Pause streaming. Tokens stop flowing until resume() is called."""
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    @property
    def output_so_far(self) -> str:
        with self._lock:
            return "".join(self._output_buffer)

    @property
    def receipt(self) -> StreamReceipt | None:
        return self._final_receipt

    # ── Main generator (iterate this) ─────────────────────────────────────────

    def stream(self) -> Iterator[StreamEvent]:
        """Iterate to receive all events from this session."""
        prompt = self.initial_prompt

        while True:
            yield from self._run_generation(prompt)

            # Check if a redirect was queued
            try:
                new_prompt = self._redirect_queue.get_nowait()
                self._redirect_count += 1
                meta = SessionMeta(kind="redirect", content=new_prompt[:120])
                yield meta.as_stream_event()
                prompt = self._build_continuation_prompt(new_prompt)
                # Reset stop event for the new generation
                self._stop_event.clear()
                continue
            except queue.Empty:
                pass

            break

        # Final receipt
        elapsed = time.monotonic() - self._start_time
        self._final_receipt = StreamReceipt(
            session_id=self.session_id,
            prompt=self.initial_prompt,
            output_text=self.output_so_far,
            tier_used=getattr(self.core, "active_tier", "unknown"),
            token_count=self._token_count,
            elapsed_s=elapsed,
            interrupted=self._stop_event.is_set(),
            injections=list(self._injections),
            redirects=self._redirect_count,
            final_status=(
                "interrupted" if self._stop_event.is_set()
                else "redirected" if self._redirect_count > 0
                else "complete"
            ),
        )

    def _run_generation(self, prompt: str) -> Iterator[StreamEvent]:
        """Run one generation pass, handling injections and interrupts inline."""
        built_prompt = self._build_prompt(prompt)
        stream = self.core.stream(
            built_prompt,
            context=self.context,
            options=self.options,
            session_id=self.session_id,
            consciousness_prefix=self.consciousness_prefix,
        )

        for event in stream:
            # Pause gate
            self._pause_event.wait()

            # Check interrupt
            if self._stop_event.is_set():
                meta = SessionMeta(kind="interrupted", content="operator interrupt")
                yield meta.as_stream_event()
                return

            # Check redirect (takes priority over injection)
            if not self._redirect_queue.empty():
                return  # outer loop handles redirect

            # Check injection
            try:
                injection_text = self._injection_queue.get_nowait()
                meta = SessionMeta(kind="injection", content=injection_text)
                yield meta.as_stream_event()

                # Rebuild prompt incorporating injection and flush current stream
                # The injection becomes the new continuation point
                partial = self.output_so_far[-self.history_window:]
                continuation_prompt = (
                    f"{prompt}\n\n"
                    f"[PARTIAL OUTPUT SO FAR]:\n{partial}\n\n"
                    f"[OPERATOR INJECTION]: {injection_text}\n\n"
                    f"[Continue from the operator injection, incorporating it into your response]:"
                )
                # Recurse into a new generation pass with injected context
                yield from self._run_generation(continuation_prompt)
                return
            except queue.Empty:
                pass

            # Normal token
            if event.text:
                with self._lock:
                    self._output_buffer.append(event.text)
            if event.estimated_tokens:
                self._token_count += event.estimated_tokens

            yield event

            if event.done:
                return

    def _build_prompt(self, prompt: str) -> str:
        prefix = self.consciousness_prefix
        if prefix:
            return f"{prefix}\n\n{prompt}"
        return prompt

    def _build_continuation_prompt(self, new_prompt: str) -> str:
        """Build redirect prompt with history context."""
        partial = self.output_so_far[-self.history_window:]
        if not partial:
            return new_prompt
        return (
            f"[SESSION REDIRECT — previous generation history]:\n{partial}\n\n"
            f"[NEW DIRECTION]: {new_prompt}"
        )


# ── StreamSessionManager ──────────────────────────────────────────────────────

class StreamSessionManager:
    """Registry and lifecycle manager for active StreamSessions.

    Wired into LuciferRuntime. Lets the operator:
    - Begin a named session
    - Inject into any live session by session_id
    - Interrupt or redirect from outside the generator thread
    - Retrieve receipts for kernel logging
    """

    def __init__(self) -> None:
        self._sessions: dict[str, StreamSession] = {}
        self._lock = threading.Lock()

    def begin(
        self,
        cognition_core: Any,
        prompt: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        consciousness_prefix: str | None = None,
    ) -> StreamSession:
        """Create and register a new StreamSession."""
        sid = session_id or str(uuid4())
        session = StreamSession(
            session_id=sid,
            cognition_core=cognition_core,
            initial_prompt=prompt,
            context=context,
            options=options,
            consciousness_prefix=consciousness_prefix,
        )
        with self._lock:
            self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> StreamSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def inject(self, session_id: str, text: str) -> bool:
        session = self.get(session_id)
        if session:
            session.inject(text)
            return True
        return False

    def interrupt(self, session_id: str) -> bool:
        session = self.get(session_id)
        if session:
            session.interrupt()
            return True
        return False

    def redirect(self, session_id: str, new_prompt: str) -> bool:
        session = self.get(session_id)
        if session:
            session.redirect(new_prompt)
            return True
        return False

    def close(self, session_id: str) -> StreamReceipt | None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            session.interrupt()
            return session.receipt
        return None

    def active_sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "session_id": sid,
                    "output_chars": len(s.output_so_far),
                    "injections": len(s._injections),
                    "redirects": s._redirect_count,
                }
                for sid, s in self._sessions.items()
            ]

    def status(self) -> dict[str, Any]:
        return {
            "active_session_count": len(self._sessions),
            "sessions": self.active_sessions(),
        }
