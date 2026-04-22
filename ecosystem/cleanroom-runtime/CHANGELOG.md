## v2.17.0

- added optional `bluetooth_bridge` with trusted device registry, bounded profiles, policy checks, and receipt-bearing actions
- added mock local signal generation modes for beacon advertising and local peripheral serving
- added CLI surface for bluetooth bridge inspection, registration, policy checks, signal summaries, and bounded perform flows
- added docs/tests/smoke coverage for the bluetooth bridge

## v2.15.0

- added optional `robotics_bridge/` with deterministic interlocks, mock dog-body and tentacle-arm adapters, and bounded robot CLI commands
- added optional `robotics_mapping/` with occupancy-grid updates, coverage summaries, and deterministic route planning
- added canonical `spatial_truth/` for anchors, structured observations, transform helpers, and confidence summaries
- added optional `geo_overlay/` inspired by the spatial reference package's local address tiling concepts
- extended smoke tests and CLI coverage for robot, mapping, spatial, and geo surfaces

## v2.11.2

- added a production hardening pass for release discipline and repository hygiene
- fixed public version drift across `pyproject.toml`, `README.md`, and generated package metadata
- replaced shell-based candidate validation with argv-based subprocess execution via deterministic command normalization
- added a version audit script and wired it into the release check flow
- added missing repo hygiene files (`.gitignore` and GitHub Actions CI workflow) so the public tree matches the stated release posture
- preserved optional perception and robotics adapter direction while tightening trust and maintainability

## v2.10.5

- clarified the public direction around optional perception, multimodal, and robotics adapters
- added `perception_adapters/` contracts so embodiment layers can be attached without becoming hard runtime requirements
- expanded packaging extras for optional vision/audio/robotics experimentation while keeping the base install dependency-light
- updated README and architecture docs to present the repo honestly as an autonomy foundation rather than a finished living machine
- added docs for vision runtime flow, optional adapter doctrine, and public direction goals

## v2.10.4

- cleaned release artifacts from the tracked tree and added a root `.gitignore` for caches, local state, and generated outputs
- restored a real GitHub Actions CI workflow covering Python 3.11, 3.12, and 3.13
- added a `Makefile` for install/test/smoke/release-check/clean flows
- made bootstrap and release-check scripts more portable by defaulting to `python3` and invoking smoke through `bash`
- corrected README quick-start and repo-structure docs so they match the actual package layout

## v2.10.3

- Added first-class directive ledger with persisted operator directives, priorities, supersession, and completion state.
- Added continuity shell with boot receipts, heartbeat tracking, watchdog health, and primary/fallback mode selection.
- Projected directives and continuity events into runtime world state for durable observability.
- Added CLI surfaces for `directive` and `continuity` administration.
- Added tests for directive round-tripping, continuity boot/heartbeat behavior, and state projection.

## v2.10.2
- added structured goal compilation with constraints, invariants, evidence requirements, and archive mode
- added shadow predicted-vs-actual comparison recording
- added promotion-court review for self-improvement runs before promotion
- auto-emitted FixNet records from candidate scoring and best-candidate selection
- synced package version and README state to the current release

## v2.9.1
- added FixNet dossier recording and embedded archive packs so repair intelligence can be persisted into branch-visible runtime history
- projected FixNet case/archive counts into runtime state world model
- added CLI support for `fixnet record` and `fixnet embed`


# Changelog

## v2.9.0
- Added open-ended model profile registry for GGUF/local/external backends.
- Added training corpus export commands for supervised and preference JSONL.
- Active model profiles now feed prompt configuration automatically.
- Kept the runtime open-ended for future custom GGUF learning work while preserving current llamafile flow.

## v2.8.0
- Production release hygiene pass
- Added CI workflow for Python 3.11, 3.12, and 3.13
- Added smoke-test and release-check scripts
- Added CONTRIBUTING and SECURITY docs
- Cleaned packaged tree and refreshed README to current package capabilities

## v2.7.0
- Added adversarial self-improvement fault injection and cycle testing

## v2.6.0
- Added multi-candidate self-improvement generation, scoring, and best-candidate execution

## v2.5.0
- Added memory search/ranking and planning influence from mirrored memory

## v2.4.0
- Added early archive mirroring with mirror-then-retire lifecycle

## v2.3.0
- Added deterministic sandbox patch/validate/promote cycle

## v2.2.0
- Added resilience and fallback subsystem with degraded completion states

## v2.1.0
- Added exact line/symbol-grounded code editing and promotion validation

## v2.0.0
- Added self-improvement planning and scaffolded run worktrees

## v2.11.2 — Full-Spectrum Perception Adapters

### New: `perception_adapters/adapters/` — six concrete PerceptionAdapter implementations

- **`FFmpegVideoAdapter`** (`[vision]`) — FFmpeg-backed video stream ingestion with
  OpenCV motion detection, scene-change detection, and luminance tracking.
- **`WhisperSpeechAdapter`** (`[audio]`) — speech-to-text via openai-whisper or
  faster-whisper with dual-backend support, segment timestamps, language detection,
  and built-in vocal distress / command keyword alerting.
- **`AudioEventAdapter`** (`[audio]`) — non-speech environmental sound classification
  via spectral heuristics (always available with librosa) or ONNX inference
  (YAMNet/PANNs). Covers machinery, alarms, impacts, animal sounds, silence.
- **`OCRAdapter`** (`[vision]`) — text extraction from visual frames via EasyOCR
  (primary) or pytesseract (fallback), with alert-pattern scanning for ERROR /
  WARNING / CRITICAL / TRACEBACK / IP address keywords.
- **`DesktopCaptureAdapter`** (`[vision]`) — cross-platform screen capture via mss,
  with luminance tracking, pixel-change detection, and activity-region fingerprinting.
- **`DepthSensorAdapter`** (`[robotics]`) — spatial awareness from Intel RealSense,
  Azure Kinect, simulation arrays, or raw bytes. Near/mid/far zone occupancy and
  obstacle proximity alerting.

### New: `perception_adapters/fusion.py` — `PerceptionFusionEngine`

Multi-adapter ObservationBatch fusion with temporal smoothing, confidence gating,
alert deduplication, and `FusedWorldUpdate.to_world_facts()` for direct WorldModel
injection.

### New: `perception_adapters/perception_loop.py` — `PerceptionLoop`

Threaded sense-integrate-act loop. Polls adapters at their configured Hz,
fuses outputs, writes to WorldModel under `perception_*` keys, emits kernel
evaluation events for full audit/replay, and fires synchronous alert callbacks
for interrupt-grade response. Adapter crash isolation: one failing sensor cannot
kill the loop.

### Updated: `pyproject.toml`

- `[audio]` extras now include `openai-whisper`, `ffmpeg-python`, `librosa`, `soundfile`
- `[vision]` extras now include `ffmpeg-python`, `mss`, `easyocr`
- `[robotics]` extras include `numpy` (pyrealsense2 noted as manual install)
- New `[audio-fast]` extra for `faster-whisper` users
- `[full]` updated to cover complete perception stack

### Updated: `perception_adapters/__init__.py`

Exports `PerceptionFusionEngine`, `FusedWorldUpdate`, `PerceptionLoop`, `AdapterSchedule`.

### New: `examples/run_perception_loop.py`

Full end-to-end AGI loop example demonstrating all six adapters wired into
LuciferRuntime, WorldModel, PersistentLoop, and GoalEngine. Includes synthetic
packet injection for no-hardware testing.

### New: `docs/perception_adapters_implementation.md`

DARPA-grade implementation doctrine: adapter inventory, data flow diagram,
temporal smoothing rationale, alert escalation contract, Hz recommendations,
dependency isolation guarantees, and wiring cookbook.
