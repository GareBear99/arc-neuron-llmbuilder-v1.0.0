"""DesktopCaptureAdapter — screen-state perception for agent oversight.

Captures the host desktop and emits structured Observations about the
visible UI state. Useful for agents operating as desktop operators,
test runners, or oversight monitors.

Optional deps: mss, Pillow, numpy, opencv-python
Install: pip install 'arc-lucifer-cleanroom-runtime[vision]'
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..interfaces import Observation, ObservationBatch, SensorPacket

_MISSING: list[str] = []

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False
    _MISSING.append("numpy")

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore
    _HAS_CV2 = False
    _MISSING.append("opencv-python")

try:
    from PIL import Image, ImageStat
    _HAS_PIL = True
except ImportError:
    Image = None  # type: ignore
    ImageStat = None  # type: ignore
    _HAS_PIL = False
    _MISSING.append("Pillow")

try:
    import mss  # type: ignore
    _HAS_MSS = True
except ImportError:
    mss = None  # type: ignore
    _HAS_MSS = False
    _MISSING.append("mss")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class DesktopCaptureAdapter:
    """Perception adapter for desktop screen state.

    Captures a screenshot and emits visual metrics as structured
    Observations: mean luminance, change ratio vs previous frame,
    and dominant color region fingerprint. Does not OCR or write
    pixel buffers into world state — use OCRAdapter for text extraction.

    Args:
        monitor: Monitor index for mss (1 = primary, 0 = all monitors).
        resize_width: Analysis resize width (default 320 — keeps compute low).
        resize_height: Analysis resize height (default 180).
        change_threshold: Pixel-diff ratio to trigger change alert (default 0.10).
        confidence_floor: Drop observations below this (default 0.20).
    """

    def __init__(
        self,
        monitor: int = 1,
        *,
        resize_width: int = 320,
        resize_height: int = 180,
        change_threshold: float = 0.10,
        confidence_floor: float = 0.20,
    ) -> None:
        self.monitor = monitor
        self.resize_width = resize_width
        self.resize_height = resize_height
        self.change_threshold = change_threshold
        self.confidence_floor = confidence_floor
        self._prev_gray: Any = None

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "DesktopCaptureAdapter",
            "modality": "desktop_capture",
            "monitor": self.monitor,
            "analysis_resolution": f"{self.resize_width}x{self.resize_height}",
            "available": not bool(_MISSING),
            "missing_deps": list(_MISSING),
            "capabilities": ["screen_luminance", "screen_change_detection", "dominant_color"],
        }

    def process(self, packet: SensorPacket) -> ObservationBatch:
        if _MISSING:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=(f"DesktopCaptureAdapter unavailable — missing: {', '.join(_MISSING)}",),
                raw_summary="desktop capture degraded",
            )

        frame = self._capture(packet)
        if frame is None:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("desktop capture returned no frame",),
                raw_summary="capture failure",
            )

        small = cv2.resize(frame, (self.resize_width, self.resize_height))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        observations: list[Observation] = []
        alerts: list[str] = []

        # Luminance
        mean_lum = float(np.mean(gray))
        lum_conf = round(min(1.0, mean_lum / 128.0), 3)
        if lum_conf >= self.confidence_floor:
            observations.append(Observation(
                kind="desktop_luminance",
                confidence=lum_conf,
                attributes={"mean_luminance": round(mean_lum, 2)},
            ))

        # Screen change vs previous frame
        if self._prev_gray is not None:
            diff = cv2.absdiff(gray, self._prev_gray)
            changed = int(np.sum(diff > 20))
            total = gray.size
            change_ratio = round(changed / max(total, 1), 4)
            change_conf = round(min(1.0, change_ratio * 5), 3)
            if change_conf >= self.confidence_floor:
                observations.append(Observation(
                    kind="desktop_change",
                    confidence=change_conf,
                    attributes={"change_ratio": change_ratio, "changed_pixels": changed},
                ))
            if change_ratio >= self.change_threshold:
                alerts.append(f"desktop screen change: {change_ratio*100:.1f}% pixels changed")

        self._prev_gray = gray

        # Dominant color region (split into 3x3 grid, find brightest block)
        h, w = small.shape[:2]
        bh, bw = h // 3, w // 3
        block_means = []
        for row in range(3):
            for col in range(3):
                block = small[row*bh:(row+1)*bh, col*bw:(col+1)*bw]
                block_means.append(float(np.mean(block)))
        brightest_block = int(np.argmax(block_means))
        observations.append(Observation(
            kind="desktop_activity_region",
            confidence=round(min(1.0, block_means[brightest_block] / 200.0), 3),
            attributes={
                "brightest_block": brightest_block,
                "block_row": brightest_block // 3,
                "block_col": brightest_block % 3,
            },
        ))

        observations = [o for o in observations if o.confidence >= self.confidence_floor]
        summary = f"{len(observations)} desktop observations, {len(alerts)} alerts"
        return ObservationBatch(
            source=packet.source,
            timestamp=_utcnow(),
            observations=tuple(observations),
            alerts=tuple(alerts),
            raw_summary=summary,
        )

    def _capture(self, packet: SensorPacket) -> Any:
        # Allow pre-supplied frame bytes from packet (testing / replay)
        raw = packet.payload.get("frame_bytes") or packet.payload.get("bytes")
        if raw and np is not None and cv2 is not None:
            arr = np.frombuffer(raw, dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if not _HAS_MSS or np is None or cv2 is None:
            return None

        with mss.mss() as sct:
            monitors = sct.monitors
            mon_idx = min(self.monitor, len(monitors) - 1)
            mon = monitors[mon_idx]
            img = sct.grab(mon)
            frame = np.frombuffer(img.bgra, dtype=np.uint8).reshape((img.height, img.width, 4))
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
