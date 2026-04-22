"""PerceptionLoop — the unified sense-integrate-act cycle.

This is the AGI loop's sensory front-end. It:

1. Polls every registered perception adapter at its configured cadence.
2. Fuses all ObservationBatches through PerceptionFusionEngine.
3. Writes the fused world update into WorldModel.update_fact().
4. Emits kernel evaluation events for audit / replay.
5. Fires high-priority interrupt callbacks for time-critical alerts.

The loop is fully synchronous (threading.Thread-safe) and runs inside
the same process as LuciferRuntime. No asyncio required.

Integration point with PersistentLoop:
    The PersistentLoop's GoalEngine reads world_model.snapshot(), which
    now includes all perception facts under "perception_*" keys. Goals
    can therefore reference sensory state in their constraints and abort
    conditions, enabling truly grounded autonomy.

Usage::

    from perception_adapters.perception_loop import PerceptionLoop, AdapterSchedule
    from perception_adapters.adapters import (
        FFmpegVideoAdapter, WhisperSpeechAdapter,
        AudioEventAdapter, OCRAdapter,
        DesktopCaptureAdapter, DepthSensorAdapter,
    )
    from perception_adapters import AdapterRegistry, OptionalAdapterConfig

    loop = PerceptionLoop(runtime=my_runtime, world_model=my_world_model)
    loop.register(
        "video", FFmpegVideoAdapter(source="0"),
        schedule=AdapterSchedule(tick_hz=5.0),
    )
    loop.register(
        "speech", WhisperSpeechAdapter(),
        schedule=AdapterSchedule(tick_hz=1.0),
    )
    loop.register(
        "audio_events", AudioEventAdapter(),
        schedule=AdapterSchedule(tick_hz=2.0),
    )
    loop.register(
        "ocr", OCRAdapter(),
        schedule=AdapterSchedule(tick_hz=0.5),
    )
    loop.start()          # background thread
    # … later …
    loop.stop()
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .fusion import FusedWorldUpdate, PerceptionFusionEngine
from .interfaces import ObservationBatch, PerceptionAdapter, SensorPacket


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AdapterSchedule:
    """Timing configuration for a single adapter slot.

    Args:
        tick_hz: Target poll frequency in Hz (default 1.0).
            - Video: 5–10 Hz
            - Audio events: 2–4 Hz
            - Speech: 0.5–2 Hz (Whisper is heavy)
            - Depth: 5–30 Hz
            - Desktop: 0.25–1 Hz
            - OCR: 0.1–0.5 Hz (heavy)
        enabled: Set False to disable without removing adapter (default True).
        source_override: Override the SensorPacket source string.
    """
    tick_hz: float = 1.0
    enabled: bool = True
    source_override: str | None = None


@dataclass
class _SlotState:
    adapter: PerceptionAdapter
    schedule: AdapterSchedule
    name: str
    last_tick: float = 0.0
    tick_count: int = 0
    error_count: int = 0
    last_error: str = ""

    @property
    def interval_s(self) -> float:
        return 1.0 / max(self.schedule.tick_hz, 0.001)


class PerceptionLoop:
    """Continuous multi-adapter perception loop wired into the AGI runtime.

    Args:
        runtime: LuciferRuntime instance. Used to emit kernel evaluation events
            so all perception activity is auditable and replayable.
        world_model: WorldModel instance. Receives fused perception facts.
        fusion_engine: Optional custom PerceptionFusionEngine. Defaults to
            a standard engine with recommended parameters.
        on_alert: Optional callback(alert_str: str) called on every new
            high-priority alert before the world model is written. Use this
            for real-time interrupt handling.
        loop_sleep_s: Main loop sleep interval in seconds (default 0.02 = 50Hz
            scheduler resolution). Keep small for precise Hz control.
        max_adapter_errors: Disable an adapter after this many consecutive
            errors (default 10). Set 0 to never auto-disable.
    """

    def __init__(
        self,
        runtime: Any,
        world_model: Any,
        *,
        fusion_engine: PerceptionFusionEngine | None = None,
        on_alert: Callable[[str], None] | None = None,
        loop_sleep_s: float = 0.02,
        max_adapter_errors: int = 10,
    ) -> None:
        self.runtime = runtime
        self.world_model = world_model
        self.fusion = fusion_engine or PerceptionFusionEngine()
        self.on_alert = on_alert
        self.loop_sleep_s = loop_sleep_s
        self.max_adapter_errors = max_adapter_errors

        self._slots: dict[str, _SlotState] = {}
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._tick_count = 0
        self._started_at: str | None = None

    # ── Public API ──────────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        adapter: PerceptionAdapter,
        *,
        schedule: AdapterSchedule | None = None,
    ) -> None:
        """Register a perception adapter under the given name.

        Can be called before or after ``start()``. Thread-safe.
        """
        sched = schedule or AdapterSchedule()
        with self._lock:
            self._slots[name] = _SlotState(
                adapter=adapter,
                schedule=sched,
                name=name,
            )

    def unregister(self, name: str) -> None:
        with self._lock:
            self._slots.pop(name, None)

    def enable(self, name: str) -> None:
        with self._lock:
            if name in self._slots:
                self._slots[name].schedule.enabled = True

    def disable(self, name: str) -> None:
        with self._lock:
            if name in self._slots:
                self._slots[name].schedule.enabled = False

    def start(self, *, daemon: bool = True) -> None:
        """Start the perception loop in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_at = _utcnow()
        self._thread = threading.Thread(
            target=self._loop,
            name="PerceptionLoop",
            daemon=daemon,
        )
        self._thread.start()
        self._emit_kernel_event("perception_loop_started", {
            "adapters": list(self._slots.keys()),
            "started_at": self._started_at,
        })

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the loop to stop and wait for thread exit."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._emit_kernel_event("perception_loop_stopped", {
            "total_ticks": self._tick_count,
            "stopped_at": _utcnow(),
        })

    def tick_once(self) -> FusedWorldUpdate | None:
        """Run a single manual tick across all due adapters. Useful for testing
        and for integrating into an existing event loop without threads."""
        return self._run_tick(time.monotonic())

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": bool(self._thread and self._thread.is_alive()),
                "total_ticks": self._tick_count,
                "started_at": self._started_at,
                "adapters": {
                    name: {
                        "enabled": slot.schedule.enabled,
                        "tick_hz": slot.schedule.tick_hz,
                        "ticks": slot.tick_count,
                        "errors": slot.error_count,
                        "last_error": slot.last_error,
                        "describe": slot.adapter.describe(),
                    }
                    for name, slot in self._slots.items()
                },
            }

    # ── Internal loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            now = time.monotonic()
            self._run_tick(now)
            time.sleep(self.loop_sleep_s)

    def _run_tick(self, now: float) -> FusedWorldUpdate | None:
        """Poll all due adapters, fuse, and write to world model."""
        with self._lock:
            due_slots = [
                slot for slot in self._slots.values()
                if slot.schedule.enabled and (now - slot.last_tick) >= slot.interval_s
            ]

        if not due_slots:
            return None

        batches: list[ObservationBatch] = []
        for slot in due_slots:
            packet = self._make_packet(slot)
            batch = self._safe_process(slot, packet, now)
            batches.append(batch)

        if not batches:
            return None

        fused = self.fusion.fuse(batches)
        self._write_world_model(fused)
        self._handle_alerts(fused)
        self._emit_kernel_event("perception_fusion_tick", {
            "tick_index": self._tick_count,
            "adapters_polled": [s.name for s in due_slots],
            **fused.to_world_facts(),
        })
        self._tick_count += 1
        return fused

    def _make_packet(self, slot: _SlotState) -> SensorPacket:
        source = slot.schedule.source_override or f"perception.{slot.name}"
        return SensorPacket(
            source=source,
            modality=slot.adapter.describe().get("modality", "unknown"),
            timestamp=_utcnow(),
        )

    def _safe_process(self, slot: _SlotState, packet: SensorPacket, now: float) -> ObservationBatch:
        """Process with full error isolation — an adapter crash cannot kill the loop."""
        try:
            batch = slot.adapter.process(packet)
            slot.tick_count += 1
            slot.last_tick = now
            if slot.error_count > 0:
                slot.error_count = 0  # reset on success
            return batch
        except Exception as exc:
            slot.error_count += 1
            slot.last_error = str(exc)
            slot.last_tick = now
            if self.max_adapter_errors and slot.error_count >= self.max_adapter_errors:
                slot.schedule.enabled = False
                self._emit_kernel_event("perception_adapter_disabled", {
                    "adapter": slot.name,
                    "reason": f"exceeded {self.max_adapter_errors} consecutive errors",
                    "last_error": str(exc),
                })
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=(f"adapter '{slot.name}' error: {exc}",),
                raw_summary=f"error in {slot.name}: {exc}",
            )

    def _write_world_model(self, fused: FusedWorldUpdate) -> None:
        """Inject fused facts into the world model."""
        facts = fused.to_world_facts()
        self.world_model.update_fact("perception_last_fused_at", facts["fused_at"])
        self.world_model.update_fact("perception_sources", facts["sources"])
        self.world_model.update_fact("perception_observation_count", facts["observation_count"])
        self.world_model.update_fact("perception_alert_count", facts["alert_count"])
        self.world_model.update_fact("perception_alerts", facts["alerts"])
        self.world_model.update_fact("perception_top_observations", facts["top_observations"])
        self.world_model.update_fact("perception_by_kind", facts["by_kind"])
        self.world_model.update_fact("perception_raw_summaries", facts["raw_summaries"])

        # Per-kind facts for fine-grained goal engine access
        for kind, obs_list in facts["by_kind"].items():
            self.world_model.update_fact(f"perception_kind_{kind}", obs_list)

    def _handle_alerts(self, fused: FusedWorldUpdate) -> None:
        """Fire alert callback and optionally interrupt the runtime."""
        for alert in fused.alerts:
            if self.on_alert:
                try:
                    self.on_alert(alert)
                except Exception:
                    pass  # callback errors must never kill the perception loop

    def _emit_kernel_event(self, kind: str, payload: dict[str, Any]) -> None:
        """Write perception activity into the kernel event log for audit/replay."""
        if self.runtime is None:
            return
        kernel = getattr(self.runtime, "kernel", None)
        if kernel is None:
            return
        try:
            kernel.record_evaluation("perception", {"kind": kind, **payload})
        except Exception:
            pass  # kernel failures must not crash the perception loop
