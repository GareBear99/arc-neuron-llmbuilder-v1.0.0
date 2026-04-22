# Full-Spectrum Perception Adapter Implementation

## Doctrine

This document covers the complete implementation of all perception adapter
gaps. It follows the same optional-adapter doctrine as `vision_runtime_optional_adapters.md`
but specifies every concrete adapter, its dependency tier, its position in the
data flow, and exactly why each design decision was made the way it was.

## Adapter inventory

| Adapter | Modality | Extra | Dep tier | Covers |
|---|---|---|---|---|
| `FFmpegVideoAdapter` | `video` | `[vision]` | medium | Frame decode, motion detection, scene change |
| `WhisperSpeechAdapter` | `audio_speech` | `[audio]` | heavy | Speech-to-text, language ID, segment timestamps |
| `AudioEventAdapter` | `audio_events` | `[audio]` | medium | Non-speech sounds: machinery, alarms, impacts, animals |
| `OCRAdapter` | `ocr` | `[vision]` | heavy | Text extraction from visual frames — bridges vision→language |
| `DesktopCaptureAdapter` | `desktop_capture` | `[vision]` | light | Screen state, UI change detection |
| `DepthSensorAdapter` | `depth` | `[robotics]` | optional | Spatial awareness, obstacle proximity, zone occupancy |

## Why these six cover the gaps

**FFmpeg + Whisper** handle the two canonical channels: vision and speech.

**AudioEventAdapter** is the gap Whisper leaves. Whisper runs a speech
recognition model — it will not reliably classify a dog barking, a door
slamming, a piece of machinery humming, or a glass breaking. Those require
either a spectral heuristic classifier (always available if librosa is present)
or a dedicated audio classification model (YAMNet, PANNs) loaded via ONNX.
The adapter supports both, tries ONNX first, falls back to heuristics.

**OCRAdapter** bridges vision into the language/planning layer. An agent
operating a desktop, reading terminal output, or observing physical signage
cannot act on raw pixels — it needs text. OCR closes this gap without requiring
a vision-language model in the inference path.

**DesktopCaptureAdapter** is the agent oversight channel. When the runtime is
acting as a computer operator, it needs to see what is on screen independent of
whether OCR finds any text. Screen-change detection catches unexpected UI shifts,
errors, or modal dialogs that a purely text-driven operator would miss.

**DepthSensorAdapter** is the embodied safety channel. For any agent operating
in a physical environment, knowing that an obstacle is 0.5m away is safety-
critical information that must arrive before the planning layer commits to motion.
This adapter degrades gracefully: it accepts numpy arrays from simulation or
robot bridge code, and only requires pyrealsense2 for live RealSense hardware.

## Data flow

```
HARDWARE / ENVIRONMENT
        │
        ▼
  SensorPacket          (source, modality, timestamp, payload)
        │
        ▼
  PerceptionAdapter     (per-adapter: decode → analyse → structure)
        │
        ▼
  ObservationBatch      (observations: tuple[Observation], alerts: tuple[str])
        │
        ▼
  PerceptionFusionEngine
  ┌──────────────────────────────────────────────────────────────┐
  │  1. Confidence gate    (drop obs < global floor)             │
  │  2. Temporal smoothing (average confidence over window)      │
  │  3. Alert deduplication (suppress repeat alerts)             │
  │  4. Rank by confidence                                       │
  └──────────────────────────────────────────────────────────────┘
        │
        ▼
  FusedWorldUpdate      (observations, alerts, sources, timestamp)
        │
        ▼
  WorldModel.update_fact()    ← keyed by "perception_*" prefix
        │
        ▼
  PersistentLoop.tick()       ← reads world_model.snapshot()
        │
        ▼
  GoalEngine / Planner        ← grounded in real-world sensory state
        │
        ▼
  KernelEngine.record_evaluation("perception", …)   ← audit trail
```

## Temporal smoothing rationale

Raw sensor data is noisy. A single high-confidence motion observation
followed by two low-confidence frames should not whipsaw the world model.
The FusionEngine maintains a rolling window of recent confidence values per
observation kind and averages them. This gives the planner a stable signal.

Default window = 3 (configurable). Wider windows reduce reactivity.
DARPA-grade recommendation: 3 for safety-critical paths, 5–10 for ambient
background state.

## Alert escalation contract

Alerts flow out-of-band from observations through two channels:

1. `PerceptionLoop.on_alert` callback — synchronous, before world model write.
   Use for interrupt-grade response (e.g. stop motion on near-field obstacle).
2. `WorldModel.update_fact("perception_alerts", [...])` — inspectable by the
   goal engine and planner on their next tick.
3. `KernelEngine.record_evaluation("perception", {"kind": "perception_fusion_tick", ...})`
   — full audit trail in the event log for replay and post-mortem.

Alerts are deduplicated across `alert_dedup_window` fusion cycles (default 5).
An alarm that fires continuously will not spam the callback or the log.

## Dependency isolation

Every adapter wraps its optional imports in module-level try/except.
Import failure sets `_MISSING` and causes `process()` to return a degraded
`ObservationBatch` with a descriptive alert rather than raising.

The `PerceptionLoop._safe_process()` method additionally wraps every
`adapter.process()` call in try/except. An adapter that raises an exception
increments its error counter. After `max_adapter_errors` consecutive errors,
the adapter is automatically disabled and a kernel evaluation event is emitted.
The loop continues running all other adapters — one bad sensor cannot kill
the AGI loop.

## Hz recommendations by adapter

| Adapter | Minimum | Recommended | Maximum useful |
|---|---|---|---|
| FFmpegVideoAdapter | 1 Hz | 5–10 Hz | 30 Hz (display rate) |
| WhisperSpeechAdapter | 0.1 Hz | 0.5–2 Hz | 4 Hz (Whisper latency bound) |
| AudioEventAdapter | 1 Hz | 2–4 Hz | 10 Hz |
| OCRAdapter | 0.1 Hz | 0.25–0.5 Hz | 2 Hz (heavy inference) |
| DesktopCaptureAdapter | 0.1 Hz | 0.5–1 Hz | 5 Hz |
| DepthSensorAdapter | 1 Hz | 10–30 Hz | 90 Hz (hardware limit) |

## Installing the full stack

```bash
# Full perception stack
pip install 'arc-lucifer-cleanroom-runtime[full]'

# Audio only (speech + events)
pip install 'arc-lucifer-cleanroom-runtime[audio]'

# Vision only (video, desktop, OCR)
pip install 'arc-lucifer-cleanroom-runtime[vision]'

# Faster Whisper alternative (4x faster, same API)
pip install 'arc-lucifer-cleanroom-runtime[audio-fast]'

# RealSense depth (platform-specific, not on PyPI for all targets)
pip install pyrealsense2
pip install 'arc-lucifer-cleanroom-runtime[robotics]'
```

## ONNX audio model (for AudioEventAdapter full accuracy)

Download a YAMNet or PANNs model in ONNX format and pass the path:

```python
from perception_adapters.adapters import AudioEventAdapter

adapter = AudioEventAdapter(
    onnx_model_path="/models/yamnet.onnx",
    onnx_labels=open("/models/yamnet_labels.txt").read().splitlines(),
    top_k=3,
)
```

Without ONNX, the adapter falls back to spectral heuristics — adequate for
alarm/impact/machinery detection, not adequate for fine-grained classification
of 521 AudioSet classes.

## Wiring into an existing runtime

```python
from lucifer_runtime.runtime import LuciferRuntime
from cognition_services.world_model import WorldModel
from perception_adapters import PerceptionLoop, AdapterSchedule
from perception_adapters.adapters import (
    FFmpegVideoAdapter, WhisperSpeechAdapter,
    AudioEventAdapter, OCRAdapter,
)

runtime = LuciferRuntime()
world_model = WorldModel()

loop = PerceptionLoop(runtime=runtime, world_model=world_model)
loop.register("video",        FFmpegVideoAdapter("0"),     schedule=AdapterSchedule(tick_hz=5.0))
loop.register("speech",       WhisperSpeechAdapter(),      schedule=AdapterSchedule(tick_hz=1.0))
loop.register("audio_events", AudioEventAdapter(),         schedule=AdapterSchedule(tick_hz=2.0))
loop.register("ocr",          OCRAdapter(),                schedule=AdapterSchedule(tick_hz=0.5))

loop.start()
```

All perception activity writes to `world_model` under `perception_*` keys
and emits kernel evaluation events tagged `"perception"` for full audit.
