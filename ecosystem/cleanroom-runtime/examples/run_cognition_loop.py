"""run_cognition_loop.py — swappable cognition core with live streaming injection.

Demonstrates:
  1. Tiered backend setup (primary → secondary → echo)
  2. Simulated primary failure mid-stream → automatic tier switch
  3. Operator injecting text mid-stream while generation is running
  4. Redirect (abandon + restart) within the same session
  5. FallbackConsciousnessLayer building degradation prefix
  6. Self-improvement goal generated from fallback event
  7. Full kernel audit trail of all cognition events

Run:
    python examples/run_cognition_loop.py

No hardware required — uses stub backends to simulate all behaviors.
"""
from __future__ import annotations

import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lucifer_runtime.runtime import LuciferRuntime
from arc_kernel.engine import KernelEngine
from cognition_services.world_model import WorldModel
from cognition_services.cognition_core import (
    CognitionCore, CognitionTier,
    TIER_PRIMARY, TIER_SECONDARY, TIER_ECHO,
)
from cognition_services.fallback_consciousness import FallbackConsciousnessLayer
from cognition_services.stream_session import StreamSessionManager
from cognition_services.cognition_runtime_extension import (
    build_cognition_core, patch_runtime,
)
from model_services.interfaces import StreamEvent


# ── Stub backends for demonstration ──────────────────────────────────────────

class _StubStreamBackend:
    """Generates a slow token-by-token stream with a configurable failure point."""

    def __init__(
        self,
        name: str,
        words: list[str],
        fail_at_word: int | None = None,
        delay_s: float = 0.08,
    ) -> None:
        self.name = name
        self.words = words
        self.fail_at_word = fail_at_word
        self.delay_s = delay_s
        self._call_count = 0

    def generate(self, prompt: str, **_):
        return f"[{self.name}] response to: {prompt[:60]}"

    def stream_generate(self, prompt: str, **_):
        self._call_count += 1
        words = self.words + [f"(via {self.name})"]
        for i, word in enumerate(words):
            if self.fail_at_word is not None and i >= self.fail_at_word:
                raise RuntimeError(f"{self.name}: simulated failure at word {i}")
            time.sleep(self.delay_s)
            text = word + " "
            done = (i == len(words) - 1)
            yield StreamEvent(
                text=text,
                sequence=i,
                chars_emitted=len(text),
                words_emitted=1,
                estimated_tokens=1,
                done=done,
            )


# ── Demo ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("ARC Lucifer — Swappable Cognition Core + Live Streaming Demo")
    print("=" * 70)

    # 1. Build runtime + world model
    kernel = KernelEngine()
    runtime = LuciferRuntime(kernel=kernel)
    runtime.world_model = WorldModel()

    # 2. Build and wire cognition core
    core, consciousness, sessions = build_cognition_core(runtime)
    patch_runtime(runtime)

    # 3. Register tiered backends
    # Primary: fails after 5 words — simulates model crash mid-stream
    primary_backend = _StubStreamBackend(
        name="primary-70B",
        words="The world model currently shows three active perception streams with motion detected in sector four and audio events flagged.".split(),
        fail_at_word=5,   # crashes mid-sentence
        delay_s=0.06,
    )
    # Secondary: completes successfully
    secondary_backend = _StubStreamBackend(
        name="secondary-7B",
        words="Continuing from primary failure — secondary cognition online. Perception data integrated. Memory subsystem nominal.".split(),
        delay_s=0.05,
    )

    core.add_tier(TIER_PRIMARY, primary_backend,
                  capabilities=["generate", "stream", "code", "plan", "reason"])
    core.add_tier(TIER_SECONDARY, secondary_backend,
                  capabilities=["generate", "stream"])
    # TIER_ECHO always present automatically

    print(f"\nTier status: {[t['name'] for t in core.status()['tiers']]}")
    print(f"Active tier: {core.active_tier}")
    print()

    # ── Demo 1: Streaming with automatic tier failover ────────────────────────
    print("─" * 70)
    print("DEMO 1: Stream with mid-stream primary failure → automatic failover")
    print("─" * 70)
    print("Streaming: ", end="", flush=True)

    session1, events1 = runtime.cognition_stream(
        "Summarize the current world model state and any active alerts."
    )

    for event in events1:
        if event.sequence == -1:
            # Control event — tier switch or injection notification
            print(f"\n{event.text.strip()}", flush=True)
            print("Streaming: ", end="", flush=True)
        else:
            print(event.text, end="", flush=True)

    print()
    receipt1 = session1.receipt
    if receipt1:
        print(f"\n✓ Session complete: tier={receipt1.tier_used} | "
              f"tokens≈{receipt1.token_count} | elapsed={receipt1.elapsed_s:.2f}s | "
              f"status={receipt1.final_status}")

    # ── Demo 2: Operator injection mid-stream ────────────────────────────────
    print()
    print("─" * 70)
    print("DEMO 2: Operator injects mid-stream (WarpAI-style)")
    print("─" * 70)

    # Reset secondary backend so it doesn't fail
    secondary_backend.fail_at_word = None
    secondary_backend.words = (
        "Analyzing the FixNet repair ledger. Found twelve repair patterns. "
        "Top cluster is model timeout. Recommendation: increase retry budget. "
        "Memory subsystem is healthy with six archived items."
    ).split()

    session2, events2 = runtime.cognition_stream(
        "Give me a detailed breakdown of the repair ledger.",
        session_id="demo-session-2",
    )

    def _inject_after_delay():
        time.sleep(0.4)  # let a few words stream first
        print(f"\n[OPERATOR → injecting mid-stream]", flush=True)
        runtime.cognition_inject("demo-session-2", "focus specifically on memory timeout patterns")

    inject_thread = threading.Thread(target=_inject_after_delay, daemon=True)
    inject_thread.start()

    print("Streaming: ", end="", flush=True)
    for event in events2:
        if event.sequence == -1:
            print(f"\n{event.text.strip()}", flush=True)
            print("Streaming: ", end="", flush=True)
        else:
            print(event.text, end="", flush=True)
    inject_thread.join()
    print()

    # ── Demo 3: Redirect mid-session ─────────────────────────────────────────
    print()
    print("─" * 70)
    print("DEMO 3: Operator redirects session (abandon + restart in-session)")
    print("─" * 70)

    secondary_backend.words = (
        "The curriculum memory shows seventeen recent training events. "
        "Five relate to self-improvement cycles. Three relate to patch validation."
    ).split()

    session3, events3 = runtime.cognition_stream(
        "Walk me through the curriculum memory in detail.",
        session_id="demo-session-3",
    )

    def _redirect_after_delay():
        time.sleep(0.3)
        print(f"\n[OPERATOR → redirecting session]", flush=True)
        runtime.cognition_redirect("demo-session-3",
                                   "actually — what is the FixNet novelty score on the latest fix?")

    redirect_thread = threading.Thread(target=_redirect_after_delay, daemon=True)
    redirect_thread.start()

    print("Streaming: ", end="", flush=True)
    for event in events3:
        if event.sequence == -1:
            print(f"\n{event.text.strip()}", flush=True)
            print("Streaming: ", end="", flush=True)
        else:
            print(event.text, end="", flush=True)
    redirect_thread.join()
    print()

    # ── Demo 4: Consciousness prefix when degraded ───────────────────────────
    print()
    print("─" * 70)
    print("DEMO 4: FallbackConsciousnessLayer prefix (what the model sees when degraded)")
    print("─" * 70)

    # Force a degradation event to populate consciousness state
    from cognition_services.cognition_core import TierChangeEvent
    fake_evt = TierChangeEvent(
        from_tier=TIER_PRIMARY,
        to_tier=TIER_SECONDARY,
        reason="simulated: primary model port 8080 connection refused",
        timestamp="2026-01-01T00:00:00+00:00",
        direction="degraded",
    )
    consciousness.on_tier_change(fake_evt)

    prefix = consciousness.build_prefix()
    print("Consciousness prefix injected into prompt:")
    print()
    print(prefix or "(none — primary tier healthy)")

    # ── Final status dump ─────────────────────────────────────────────────────
    print()
    print("─" * 70)
    print("FINAL: Cognition system status")
    print("─" * 70)
    status = runtime.cognition_status()
    core_status = status["cognition_core"]
    fb_status = status["fallback_consciousness"]

    print(f"Active tier       : {core_status['active_tier']}")
    print(f"Is degraded       : {core_status['is_degraded']}")
    print(f"Tier changes      : {core_status['tier_change_count']}")
    print(f"Fallback episodes : {fb_status['episode_count']}")
    print(f"Total fallback s  : {fb_status['total_fallback_duration_s']}")
    print(f"Active sessions   : {status['stream_sessions']['active_session_count']}")

    print()
    print("World model cognition keys:")
    wm = runtime.world_model.snapshot().get("facts", {})
    for k, v in wm.items():
        if k.startswith("cognition"):
            print(f"  {k}: {v}")

    print()
    print("Kernel cognition events:")
    kernel_state = kernel.state()
    cog_evals = [e for e in kernel_state.evaluations if e.get("kind", "").startswith("cognition")]
    print(f"  {len(cog_evals)} cognition evaluation events logged")
    for e in cog_evals[-5:]:
        print(f"  [{e.get('kind')}] tier={e.get('tier', '—')} session={e.get('session_id', '—')}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
