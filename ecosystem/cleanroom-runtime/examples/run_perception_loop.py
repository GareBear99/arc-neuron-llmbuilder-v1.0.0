"""run_perception_loop.py — Full AGI sense-integrate-act loop example.

Demonstrates every adapter wired into the runtime with the complete
perception → fusion → world model → goal engine → planning → action
cycle. Run this to validate the end-to-end loop without real hardware
by injecting synthetic SensorPackets.

Usage:
    python examples/run_perception_loop.py

Hardware modes (uncomment relevant sections):
    - Webcam:      set VIDEO_SOURCE = "0"
    - RTSP stream: set VIDEO_SOURCE = "rtsp://192.168.1.100:554/stream"
    - RealSense:   ensure pyrealsense2 is installed
    - Microphone:  replace synthetic audio with pyaudio capture
"""
from __future__ import annotations

import time
import sys
import os

# Allow running from repo root without install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lucifer_runtime.runtime import LuciferRuntime
from arc_kernel.engine import KernelEngine
from cognition_services.world_model import WorldModel
from cognition_services.persistent_loop import PersistentLoop

from perception_adapters import (
    AdapterRegistry,
    AdapterSchedule,
    OptionalAdapterConfig,
    PerceptionFusionEngine,
    PerceptionLoop,
    SensorPacket,
)
from perception_adapters.adapters import (
    AudioEventAdapter,
    DepthSensorAdapter,
    DesktopCaptureAdapter,
    FFmpegVideoAdapter,
    OCRAdapter,
    WhisperSpeechAdapter,
)

# ── Configuration ─────────────────────────────────────────────────────────

VIDEO_SOURCE = "0"           # webcam index or RTSP URL
WHISPER_MODEL = "base"       # tiny / base / small / medium / large
RUN_SECONDS = 30             # how long to run the demo loop
PRINT_WORLD_STATE = True     # print world model snapshot each tick


# ── Alert handler — wired to runtime for interrupt-grade response ──────────

def on_perception_alert(alert: str) -> None:
    """Called synchronously before world model write on every new alert.

    In a production system this might:
    - Trigger runtime.handle("stop all motion — obstacle detected")
    - Escalate to operator via notification channel
    - Inject a high-priority goal into the GoalEngine
    """
    print(f"\n⚠️  PERCEPTION ALERT: {alert}")


# ── Synthetic sensor packet generators (for demo without hardware) ─────────

def _make_synthetic_video_packet(source: str) -> SensorPacket:
    """Inject a synthetic video packet — replace with live camera in production."""
    try:
        import numpy as np
        import cv2
        # Random noise frame to exercise the motion/scene-change pipeline
        frame = np.random.randint(0, 200, (480, 640, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", frame)
        return SensorPacket(
            source=source,
            modality="video",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            payload={"frames": [buf.tobytes()]},
        )
    except ImportError:
        return SensorPacket(
            source=source,
            modality="video",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


def _make_synthetic_audio_packet(source: str) -> SensorPacket:
    """Inject a synthetic audio packet — replace with mic capture in production."""
    try:
        import numpy as np
        # 1s of 22050 Hz white noise
        audio = np.random.randn(22050).astype(np.float32) * 0.1
        return SensorPacket(
            source=source,
            modality="audio",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            payload={"audio": audio, "sample_rate": 22050},
        )
    except ImportError:
        return SensorPacket(
            source=source,
            modality="audio",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


# ── Custom PerceptionLoop subclass that injects synthetic payloads ─────────

class SyntheticPerceptionLoop(PerceptionLoop):
    """PerceptionLoop that overrides _make_packet to inject synthetic data.

    In production, replace with the base PerceptionLoop + real hardware
    adapters that pull data from their own sources.
    """

    def _make_packet(self, slot) -> SensorPacket:
        source = slot.schedule.source_override or f"perception.{slot.name}"
        modality = slot.adapter.describe().get("modality", "unknown")

        if modality == "video":
            return _make_synthetic_video_packet(source)
        if modality in ("audio_speech", "audio_events"):
            return _make_synthetic_audio_packet(source)

        # Desktop, depth, OCR — no-payload packet (adapters handle their own capture)
        from datetime import datetime, timezone
        return SensorPacket(
            source=source,
            modality=modality,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("ARC Lucifer — Full AGI Perception Loop")
    print("=" * 70)

    # 1. Kernel + runtime
    kernel = KernelEngine()
    runtime = LuciferRuntime(kernel=kernel)

    # 2. World model — shared between perception loop and planning loop
    world_model = WorldModel()

    # 3. Adapter registry — documents all configured adapters
    registry = AdapterRegistry()

    # 4. Build all adapters
    adapters = {
        "video": (
            FFmpegVideoAdapter(
                source=VIDEO_SOURCE,
                motion_threshold=6.0,
                scene_change_threshold=0.30,
            ),
            AdapterSchedule(tick_hz=5.0),
        ),
        "speech": (
            WhisperSpeechAdapter(
                model_size=WHISPER_MODEL,
                language="en",
                confidence_floor=0.35,
            ),
            AdapterSchedule(tick_hz=1.0),
        ),
        "audio_events": (
            AudioEventAdapter(
                confidence_floor=0.30,
                top_k=3,
            ),
            AdapterSchedule(tick_hz=2.0),
        ),
        "ocr": (
            OCRAdapter(
                languages=["en"],
                confidence_floor=0.45,
                alert_on_patterns=True,
            ),
            AdapterSchedule(tick_hz=0.5),
        ),
        "desktop": (
            DesktopCaptureAdapter(
                monitor=1,
                change_threshold=0.08,
            ),
            AdapterSchedule(tick_hz=0.5),
        ),
        "depth": (
            DepthSensorAdapter(
                near_threshold_m=0.60,
                confidence_floor=0.25,
            ),
            AdapterSchedule(tick_hz=5.0),
        ),
    }

    # Register in AdapterRegistry for describe() surface
    for name, (adapter, _) in adapters.items():
        registry.register_perception(
            name, adapter,
            OptionalAdapterConfig(enabled=True, mode="perception"),
        )

    print("\nAdapter descriptions:")
    for name, (adapter, _) in adapters.items():
        desc = adapter.describe()
        status = "✓" if desc.get("available") else f"⚠  (missing: {desc.get('missing_deps')})"
        print(f"  [{name:14s}] {status}")

    # 5. Fusion engine — temporal smoothing over 3 ticks, 5-tick alert dedup
    fusion = PerceptionFusionEngine(
        confidence_floor=0.25,
        temporal_window=3,
        alert_dedup_window=5,
    )

    # 6. Perception loop
    loop = SyntheticPerceptionLoop(
        runtime=runtime,
        world_model=world_model,
        fusion_engine=fusion,
        on_alert=on_perception_alert,
        max_adapter_errors=5,
    )
    for name, (adapter, schedule) in adapters.items():
        loop.register(name, adapter, schedule=schedule)

    # 7. Persistent goal loop — reads world_model.snapshot() each tick
    runtime.world_model = world_model  # wire world model into runtime
    persistent = PersistentLoop(goal_engine=runtime.goals, world_model=world_model)

    # 8. Register a sample directive and goal
    runtime.register_directive(
        title="maintain situational awareness",
        instruction=(
            "Continuously process perception data. Escalate if near-field obstacles "
            "are detected or alarm-class audio events occur. Keep world model current."
        ),
        priority=90,
        scope="global",
        persistence_mode="forever",
    )
    runtime.goals.add_goal(
        "process incoming sensor data and update world model",
        priority=80,
        compile=True,
    )

    # 9. Boot continuity
    runtime.boot_continuity(notes="perception loop demo boot")

    print(f"\nStarting perception loop for {RUN_SECONDS}s …")
    print("-" * 70)

    loop.start(daemon=True)

    start = time.time()
    tick = 0
    try:
        while (elapsed := time.time() - start) < RUN_SECONDS:
            time.sleep(2.0)
            tick += 1

            # Run one planning loop tick
            world_state = world_model.snapshot()
            loop_status = loop.status()

            print(f"\n[T+{elapsed:5.1f}s | tick {tick}]")
            print(f"  Perception ticks: {loop_status['total_ticks']}")

            if PRINT_WORLD_STATE:
                facts = world_state.get("facts", {})
                obs_count = facts.get("perception_observation_count", 0)
                alerts = facts.get("perception_alerts", [])
                sources = facts.get("perception_sources", [])
                top = facts.get("perception_top_observations", [])
                print(f"  Sources active : {sources}")
                print(f"  Observations   : {obs_count}")
                if alerts:
                    print(f"  Active alerts  : {alerts}")
                if top:
                    top_str = ", ".join(
                        f"{o['kind']}({o['confidence']:.2f})" for o in top[:3]
                    )
                    print(f"  Top perception : {top_str}")

            # Heartbeat to continuity shell
            runtime.continuity_heartbeat(notes=f"perception loop tick {tick}")

    except KeyboardInterrupt:
        print("\nInterrupted by operator.")
    finally:
        loop.stop()

    print("\n" + "=" * 70)
    print("Final loop status:")
    final = loop.status()
    print(f"  Total fusion ticks : {final['total_ticks']}")
    for name, info in final["adapters"].items():
        print(f"  [{name:14s}] ticks={info['ticks']:4d}  errors={info['errors']}  enabled={info['enabled']}")

    print("\nFinal world model snapshot (perception keys):")
    for key, val in world_model.snapshot().get("facts", {}).items():
        if key.startswith("perception"):
            if isinstance(val, list) and len(val) > 3:
                print(f"  {key}: [{len(val)} items]")
            else:
                print(f"  {key}: {val}")

    print("\nDone.")


if __name__ == "__main__":
    main()
