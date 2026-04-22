"""FFmpegVideoAdapter — video stream ingestion and frame analysis.

Decodes RTSP, webcam, or file sources via FFmpeg into numpy frames,
then runs OpenCV-based scene analysis to emit structured Observations.

Optional deps: ffmpeg-python, numpy, opencv-python
Install: pip install 'arc-lucifer-cleanroom-runtime[vision]'
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ..interfaces import Observation, ObservationBatch, PerceptionAdapter, SensorPacket

_MISSING: list[str] = []
try:
    import numpy as np
except ImportError:
    np = None  # type: ignore
    _MISSING.append("numpy")

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore
    _MISSING.append("opencv-python")

try:
    import ffmpeg as ffmpeg_lib
except ImportError:
    ffmpeg_lib = None  # type: ignore
    _MISSING.append("ffmpeg-python")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class FFmpegVideoAdapter:
    """Perception adapter for live video streams and recorded files.

    Reads frames from any FFmpeg-compatible source, runs motion detection
    and scene-change analysis via OpenCV, and emits structured Observations
    safe for the world model. Never writes raw pixel data to world state.

    Args:
        source: FFmpeg-compatible source string. Examples:
            - ``"0"``                  — default webcam
            - ``"rtsp://…"``           — RTSP network stream
            - ``"/path/to/clip.mp4"``  — video file
        width: Decode width in pixels (default 640).
        height: Decode height in pixels (default 480).
        motion_threshold: Pixel-diff mean threshold for motion alert (default 8.0).
        scene_change_threshold: Frame difference ratio for scene cut (default 0.35).
        confidence_floor: Discard observations below this confidence (default 0.25).
        max_frames_per_packet: Frames to sample per SensorPacket (default 4).
    """

    def __init__(
        self,
        source: str = "0",
        *,
        width: int = 640,
        height: int = 480,
        motion_threshold: float = 8.0,
        scene_change_threshold: float = 0.35,
        confidence_floor: float = 0.25,
        max_frames_per_packet: int = 4,
    ) -> None:
        self.source = source
        self.width = width
        self.height = height
        self.motion_threshold = motion_threshold
        self.scene_change_threshold = scene_change_threshold
        self.confidence_floor = confidence_floor
        self.max_frames_per_packet = max_frames_per_packet
        self._prev_gray: Any = None
        self._frame_count = 0

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "FFmpegVideoAdapter",
            "modality": "video",
            "source": self.source,
            "resolution": f"{self.width}x{self.height}",
            "available": not bool(_MISSING),
            "missing_deps": list(_MISSING),
            "capabilities": ["motion_detection", "scene_change", "frame_luminance"],
        }

    def process(self, packet: SensorPacket) -> ObservationBatch:
        """Decode frames from source and emit scene observations."""
        if _MISSING:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=(f"FFmpegVideoAdapter unavailable — missing: {', '.join(_MISSING)}",),
                raw_summary="video adapter degraded",
            )

        frames = self._capture_frames(packet)
        if not frames:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("no frames captured from video source",),
                raw_summary="empty capture",
            )

        observations: list[Observation] = []
        alerts: list[str] = []

        for frame in frames:
            self._frame_count += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Luminance observation — always present
            mean_lum = float(np.mean(gray))
            lum_conf = min(1.0, mean_lum / 128.0)
            if lum_conf >= self.confidence_floor:
                observations.append(
                    Observation(
                        kind="visual_luminance",
                        confidence=round(lum_conf, 3),
                        attributes={"mean_luminance": round(mean_lum, 2), "frame_index": self._frame_count},
                    )
                )

            # Motion detection vs previous frame
            if self._prev_gray is not None:
                diff = cv2.absdiff(gray, self._prev_gray)
                motion_score = float(np.mean(diff))
                motion_conf = min(1.0, motion_score / (self.motion_threshold * 2))
                if motion_conf >= self.confidence_floor:
                    observations.append(
                        Observation(
                            kind="visual_motion",
                            confidence=round(motion_conf, 3),
                            attributes={
                                "motion_score": round(motion_score, 3),
                                "threshold": self.motion_threshold,
                                "frame_index": self._frame_count,
                            },
                        )
                    )
                if motion_score > self.motion_threshold:
                    alerts.append(f"motion detected (score={motion_score:.2f}) at frame {self._frame_count}")

                # Scene-change detection
                h, w = gray.shape
                pixel_total = h * w
                changed_pixels = int(np.sum(diff > 30))
                change_ratio = changed_pixels / max(pixel_total, 1)
                if change_ratio >= self.scene_change_threshold:
                    observations.append(
                        Observation(
                            kind="visual_scene_change",
                            confidence=min(1.0, round(change_ratio, 3)),
                            attributes={
                                "change_ratio": round(change_ratio, 4),
                                "changed_pixels": changed_pixels,
                                "frame_index": self._frame_count,
                            },
                        )
                    )
                    alerts.append(f"scene change detected ({change_ratio*100:.1f}% pixels changed)")

            self._prev_gray = gray

        summary = (
            f"processed {len(frames)} frames from {self.source}; "
            f"{len(observations)} observations, {len(alerts)} alerts"
        )
        return ObservationBatch(
            source=packet.source,
            timestamp=_utcnow(),
            observations=tuple(observations),
            alerts=tuple(alerts),
            raw_summary=summary,
        )

    def _capture_frames(self, packet: SensorPacket) -> list[Any]:
        """Pull frames from packet payload or live capture via FFmpeg."""
        # If the packet already carries raw frame bytes (e.g. from a robot bridge)
        raw_frames = packet.payload.get("frames")
        if raw_frames and np is not None and cv2 is not None:
            decoded = []
            for raw in raw_frames[: self.max_frames_per_packet]:
                arr = np.frombuffer(raw, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    decoded.append(frame)
            return decoded

        # Live capture via OpenCV (backed by FFmpeg on most platforms)
        if cv2 is None:
            return []
        cap = cv2.VideoCapture(int(self.source) if self.source.isdigit() else self.source)
        if not cap.isOpened():
            return []
        frames = []
        for _ in range(self.max_frames_per_packet):
            ret, frame = cap.read()
            if not ret:
                break
            resized = cv2.resize(frame, (self.width, self.height))
            frames.append(resized)
        cap.release()
        return frames
