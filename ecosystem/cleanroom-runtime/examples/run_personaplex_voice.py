"""run_personaplex_voice.py — PersonaPlex as the AGI voice module.

Full end-to-end wiring of PersonaPlex into ARC Lucifer as:
  1. Perception adapter  (hears operator)
  2. Cognition tier      (speaks + thinks when primary GGUF fails)
  3. Action adapter      (voice output)

With consciousness-aware persona hot-swap — when the system degrades to
the PersonaPlex tier, the voice model is told about its own fallback state
and speaks accordingly.

Prerequisites:
    pip install 'arc-lucifer-cleanroom-runtime[voice]'
    export HF_TOKEN=<your_hf_token>
    SSL_DIR=$(mktemp -d); python -m moshi.server --ssl "$SSL_DIR"

Then run this file. The system will:
  - Connect to PersonaPlex on wss://localhost:8998
  - Register the voice module in all three adapter roles
  - Start the perception loop (hearing operator)
  - Start a streaming cognition session
  - Simulate primary GGUF failure → PersonaPlex takes over → consciousness
    prefix injected into persona prompt → voice model speaks degraded state
"""
from __future__ import annotations

import sys, os, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lucifer_runtime.runtime import LuciferRuntime
from arc_kernel.engine import KernelEngine
from cognition_services.world_model import WorldModel
from cognition_services.cognition_core import (
    CognitionCore, TierChangeEvent,
    TIER_PRIMARY, TIER_SECONDARY, TIER_ECHO,
)
from cognition_services.cognition_runtime_extension import build_cognition_core, patch_runtime
from cognition_services.fallback_consciousness import FallbackConsciousnessLayer
from perception_adapters import (
    AdapterRegistry, AdapterSchedule, OptionalAdapterConfig,
    PerceptionFusionEngine, PerceptionLoop,
)
from perception_adapters.personaplex_adapter import (
    VoiceProfile, build_personaplex_module,
)

PERSONAPLEX_URL = "wss://localhost:8998"
VOICE_ID        = "NATM1"          # change to any NAT/VAR voice
RUN_SECONDS     = 60


def main() -> None:
    print("=" * 70)
    print("ARC Lucifer — PersonaPlex Voice Module Integration")
    print("=" * 70)

    # ── 1. Runtime + world model ──────────────────────────────────────────────
    kernel = KernelEngine()
    runtime = LuciferRuntime(kernel=kernel)
    runtime.world_model = WorldModel()

    # ── 2. Cognition core ─────────────────────────────────────────────────────
    core, consciousness, sessions = build_cognition_core(runtime)
    patch_runtime(runtime)

    # ── 3. PersonaPlex voice module ───────────────────────────────────────────
    print(f"\nConnecting to PersonaPlex at {PERSONAPLEX_URL} ...")
    profile = VoiceProfile(
        voice_id=VOICE_ID,
        text_prompt=(
            "You are an autonomous AI runtime assistant named Lucifer. "
            "You are helpful, precise, and aware of your own system state. "
            "When you are in fallback mode you say so clearly."
        ),
    )

    module = build_personaplex_module(
        url=PERSONAPLEX_URL,
        profile=profile,
        ssl_verify=False,      # self-signed dev cert
        connect_timeout=10.0,
    )

    if not module["connected"]:
        print("⚠  PersonaPlex not reachable — running in stub mode")
        print("   Start server: SSL_DIR=$(mktemp -d); python -m moshi.server --ssl \"$SSL_DIR\"")
    else:
        print(f"✓ PersonaPlex connected ({VOICE_ID})")

    # ── 4. Register PersonaPlex as TIER_SECONDARY cognition backend ───────────
    core.add_tier(
        TIER_SECONDARY,
        module["cognition"],
        capabilities=["generate", "stream", "voice", "full_duplex"],
    )
    # Primary tier would be your GGUF — simulated as unavailable for this demo
    # core.add_tier(TIER_PRIMARY, LlamafileBackend(...))

    # ── 5. Consciousness → PersonaPlex persona hot-swap ───────────────────────
    # When CognitionCore switches tiers, update PersonaPlex's text prompt
    # so the voice model is aware of its own degraded state.

    _original_on_tier_change = consciousness.on_tier_change

    def _on_tier_change_with_voice(evt: TierChangeEvent) -> None:
        _original_on_tier_change(evt)  # runs FixNet, curriculum, world model
        prefix = consciousness.build_prefix()
        if prefix and module["connected"]:
            updated = profile.with_consciousness_prefix(prefix)
            module["connection"].update_persona(updated)
            print(f"\n[voice persona updated — {evt.from_tier}→{evt.to_tier}]")

    core.on_tier_change = _on_tier_change_with_voice

    # ── 6. Register perception adapter (hearing operator) ─────────────────────
    adapter_registry = AdapterRegistry()
    adapter_registry.register_perception(
        "voice_in",
        module["perception"],
        OptionalAdapterConfig(enabled=True, mode="perception"),
    )

    # ── 7. Register action adapter (speaking) ─────────────────────────────────
    adapter_registry.register_action(
        "voice_out",
        module["voice"],
        OptionalAdapterConfig(enabled=True, mode="action"),
    )

    # ── 8. Perception loop ────────────────────────────────────────────────────
    fusion = PerceptionFusionEngine(confidence_floor=0.50)
    perc_loop = PerceptionLoop(
        runtime=runtime,
        world_model=runtime.world_model,
        fusion_engine=fusion,
        on_alert=lambda alert: print(f"\n⚠ PERCEPTION ALERT: {alert}"),
    )
    perc_loop.register(
        "voice_in",
        module["perception"],
        schedule=AdapterSchedule(tick_hz=2.0),
    )
    perc_loop.start(daemon=True)
    print("✓ Perception loop started (voice_in @ 2Hz)")

    # ── 9. Boot continuity ────────────────────────────────────────────────────
    runtime.boot_continuity(notes="personaplex voice demo boot")
    runtime.register_directive(
        title="maintain voice awareness",
        instruction=(
            "Listen for operator voice input. Respond through PersonaPlex. "
            "If primary model fails, continue via voice tier. "
            "Keep world model updated with all voice transcripts."
        ),
        priority=85,
        scope="global",
        persistence_mode="forever",
    )

    # ── 10. Streaming cognition session ───────────────────────────────────────
    print("\nStarting cognition stream session ...")
    print("(Primary GGUF not configured → will fall through to PersonaPlex voice tier)")
    print()

    session, events = runtime.cognition_stream(
        "Describe your current operational status and any active perception streams.",
        session_id="voice-demo-session",
    )

    print("Response: ", end="", flush=True)
    for event in events:
        if event.sequence == -1:
            print(f"\n{event.text.strip()}", flush=True)
            print("Response: ", end="", flush=True)
        elif event.text:
            print(event.text, end="", flush=True)
    print()

    if session.receipt:
        print(f"\n✓ Session: tier={session.receipt.tier_used} | "
              f"status={session.receipt.final_status} | "
              f"injections={len(session.receipt.injections)}")

    # ── 11. Demonstrate mid-stream injection via voice awareness ──────────────
    print("\n─ Testing operator voice injection mid-stream ─")
    session2, events2 = runtime.cognition_stream(
        "Walk me through the FixNet repair ledger.",
        session_id="voice-inject-demo",
    )

    def _voice_inject():
        time.sleep(0.3)
        # Simulating operator speaking — in production this comes from
        # PersonaPlexPerceptionAdapter receiving live mic audio
        print(f"\n[OPERATOR VOICE → inject: 'focus on memory timeout errors']")
        runtime.cognition_inject("voice-inject-demo", "focus on memory timeout errors")
        # Also send to PersonaPlex so voice model hears the update
        if module["connected"]:
            module["connection"].send_text("focus on memory timeout errors")

    t = threading.Thread(target=_voice_inject, daemon=True)
    t.start()

    print("Response: ", end="", flush=True)
    for event in events2:
        if event.sequence == -1:
            print(f"\n{event.text.strip()}", flush=True)
            print("Response: ", end="", flush=True)
        elif event.text:
            print(event.text, end="", flush=True)
    t.join()
    print()

    # ── 12. Final status ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Final status")
    print("=" * 70)

    ws_status = module["connection"].status()
    cog_status = runtime.cognition_status()
    perc_status = perc_loop.status()

    print(f"PersonaPlex connected   : {ws_status['connected']}")
    print(f"Voice frames received   : {ws_status['frames_received']}")
    print(f"Transcript chunks recv  : {ws_status['text_chunks_received']}")
    print(f"Cognition tier          : {cog_status['cognition_core']['active_tier']}")
    print(f"Is degraded             : {cog_status['cognition_core']['is_degraded']}")
    print(f"Perception ticks        : {perc_status['total_ticks']}")
    print(f"Adapter registry        : {list(adapter_registry.describe()['perception'].keys())}")

    perc_loop.stop()
    module["connection"].disconnect()
    print("\nDone.")


if __name__ == "__main__":
    main()
