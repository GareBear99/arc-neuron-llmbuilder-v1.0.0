"""perception_adapters.adapters — concrete PerceptionAdapter implementations.

All adapters use lazy optional imports. Missing deps degrade gracefully
to stub ObservationBatches with descriptive alerts rather than crashing.
"""
from .audio_event import AudioEventAdapter
from .depth_sensor import DepthSensorAdapter
from .desktop_capture import DesktopCaptureAdapter
from .ffmpeg_video import FFmpegVideoAdapter
from .ocr import OCRAdapter
from .whisper_speech import WhisperSpeechAdapter

__all__ = [
    "AudioEventAdapter",
    "DepthSensorAdapter",
    "DesktopCaptureAdapter",
    "FFmpegVideoAdapter",
    "OCRAdapter",
    "WhisperSpeechAdapter",
]
