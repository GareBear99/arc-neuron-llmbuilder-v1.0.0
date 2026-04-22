"""perception_adapters — optional sensory layer for ARC Lucifer Cleanroom Runtime.

All adapters are optional. Missing dependencies degrade to stub ObservationBatches
with descriptive alerts. The base runtime install is unaffected.

Quick start::

    from perception_adapters import (
        AdapterRegistry, OptionalAdapterConfig,
        SensorPacket, Observation, ObservationBatch,
        PerceptionFusionEngine, PerceptionLoop, AdapterSchedule,
    )
    from perception_adapters.adapters import (
        FFmpegVideoAdapter,
        WhisperSpeechAdapter,
        AudioEventAdapter,
        OCRAdapter,
        DesktopCaptureAdapter,
        DepthSensorAdapter,
    )

Extras map:
    ``.[vision]``     — FFmpegVideoAdapter, DesktopCaptureAdapter, OCRAdapter
    ``.[audio]``      — WhisperSpeechAdapter, AudioEventAdapter
    ``.[robotics]``   — DepthSensorAdapter (+ pyrealsense2 for live capture)
    ``.[full]``       — all of the above
"""
from .interfaces import (
    ActionAdapter,
    Observation,
    ObservationBatch,
    OptionalAdapterConfig,
    PerceptionAdapter,
    SensorPacket,
)
from .registry import AdapterRegistry
from .fusion import FusedWorldUpdate, PerceptionFusionEngine
from .perception_loop import AdapterSchedule, PerceptionLoop

__all__ = [
    # Interfaces
    "ActionAdapter",
    "AdapterRegistry",
    "Observation",
    "ObservationBatch",
    "OptionalAdapterConfig",
    "PerceptionAdapter",
    "SensorPacket",
    # Fusion
    "FusedWorldUpdate",
    "PerceptionFusionEngine",
    # Loop
    "AdapterSchedule",
    "PerceptionLoop",
]
