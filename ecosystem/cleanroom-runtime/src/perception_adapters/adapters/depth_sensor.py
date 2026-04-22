"""DepthSensorAdapter — spatial awareness via depth cameras.

Ingests depth frames from Intel RealSense, Azure Kinect, or generic
depth arrays (simulation, file replay). Emits structured spatial
observations: nearest obstacle distance, depth variance, and zone
partitioning (near / mid / far field).

Optional deps: pyrealsense2 (for live RealSense), numpy
Install: pip install 'arc-lucifer-cleanroom-runtime[robotics]'
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
    import pyrealsense2 as rs  # type: ignore
    _HAS_RS = True
except ImportError:
    rs = None  # type: ignore
    _HAS_RS = False

# pyrealsense2 is optional even within [robotics] — adapter degrades gracefully


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# Zone thresholds in metres
_NEAR_M = 0.80
_MID_M = 2.50


class DepthSensorAdapter:
    """Perception adapter for depth / spatial data.

    Accepts SensorPackets whose payload carries one of:
    - ``"depth_array"``: numpy uint16 array (millimetres, HxW)
    - ``"depth_bytes"``: raw bytes that will be reshaped to (height, width)
    - No payload: attempts live RealSense capture if pyrealsense2 present

    Emits observations for nearest obstacle, depth variance, and zone
    occupancy fractions (near/mid/far). Fires an alert if any obstacle
    is within the critical near-field threshold.

    Args:
        width: Expected frame width (default 640).
        height: Expected frame height (default 480).
        near_threshold_m: Distance in metres for near-field alert (default 0.80).
        mid_threshold_m: Distance dividing mid from far field (default 2.50).
        max_valid_mm: Discard depth readings above this mm value (default 8000).
        confidence_floor: Drop observations below threshold (default 0.25).
        rs_serial: Optional RealSense device serial number for multi-camera setups.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        *,
        near_threshold_m: float = _NEAR_M,
        mid_threshold_m: float = _MID_M,
        max_valid_mm: int = 8000,
        confidence_floor: float = 0.25,
        rs_serial: str | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.near_threshold_m = near_threshold_m
        self.mid_threshold_m = mid_threshold_m
        self.max_valid_mm = max_valid_mm
        self.confidence_floor = confidence_floor
        self.rs_serial = rs_serial
        self._rs_pipeline: Any = None

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "DepthSensorAdapter",
            "modality": "depth",
            "resolution": f"{self.width}x{self.height}",
            "live_capture": _HAS_RS,
            "available": _HAS_NUMPY,
            "missing_deps": list(_MISSING),
            "near_threshold_m": self.near_threshold_m,
            "mid_threshold_m": self.mid_threshold_m,
            "capabilities": ["nearest_obstacle", "depth_variance", "zone_occupancy"],
        }

    def process(self, packet: SensorPacket) -> ObservationBatch:
        if not _HAS_NUMPY:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=(f"DepthSensorAdapter unavailable — missing: {', '.join(_MISSING)}",),
                raw_summary="depth adapter degraded",
            )

        depth_mm = self._extract_depth(packet)
        if depth_mm is None:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("no depth data available",),
                raw_summary="no depth data",
            )

        # Mask invalid readings
        valid_mask = (depth_mm > 0) & (depth_mm < self.max_valid_mm)
        valid_depths_mm = depth_mm[valid_mask]
        if valid_depths_mm.size == 0:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("depth frame contains no valid readings",),
                raw_summary="all-invalid depth frame",
            )

        valid_m = valid_depths_mm.astype(np.float32) / 1000.0
        nearest_m = float(np.min(valid_m))
        mean_m = float(np.mean(valid_m))
        variance = float(np.var(valid_m))
        total = valid_depths_mm.size
        near_frac = round(float(np.sum(valid_m < self.near_threshold_m)) / total, 4)
        mid_frac = round(float(np.sum((valid_m >= self.near_threshold_m) & (valid_m < self.mid_threshold_m))) / total, 4)
        far_frac = round(float(np.sum(valid_m >= self.mid_threshold_m)) / total, 4)

        observations: list[Observation] = []
        alerts: list[str] = []

        # Nearest obstacle
        obs_conf = round(min(1.0, 1.0 - nearest_m / 5.0), 3)
        obs_conf = max(0.0, obs_conf)
        observations.append(Observation(
            kind="depth_nearest_obstacle",
            confidence=obs_conf,
            attributes={
                "nearest_m": round(nearest_m, 3),
                "mean_m": round(mean_m, 3),
                "valid_pixel_count": int(total),
            },
        ))
        if nearest_m < self.near_threshold_m:
            alerts.append(f"obstacle in near field: {nearest_m:.2f}m (threshold={self.near_threshold_m}m)")

        # Depth variance (scene complexity indicator)
        var_conf = round(min(1.0, variance / 2.0), 3)
        if var_conf >= self.confidence_floor:
            observations.append(Observation(
                kind="depth_variance",
                confidence=var_conf,
                attributes={"variance_m2": round(variance, 4)},
            ))

        # Zone occupancy
        observations.append(Observation(
            kind="depth_zone_occupancy",
            confidence=0.90,
            attributes={
                "near_fraction": near_frac,
                "mid_fraction": mid_frac,
                "far_fraction": far_frac,
                "near_threshold_m": self.near_threshold_m,
                "mid_threshold_m": self.mid_threshold_m,
            },
        ))

        observations = [o for o in observations if o.confidence >= self.confidence_floor]
        summary = (
            f"depth: nearest={nearest_m:.2f}m mean={mean_m:.2f}m "
            f"near={near_frac*100:.1f}% mid={mid_frac*100:.1f}% far={far_frac*100:.1f}%"
        )
        return ObservationBatch(
            source=packet.source,
            timestamp=_utcnow(),
            observations=tuple(observations),
            alerts=tuple(alerts),
            raw_summary=summary,
        )

    def _extract_depth(self, packet: SensorPacket) -> Any:
        payload = packet.payload

        arr = payload.get("depth_array")
        if arr is not None and np is not None:
            return np.asarray(arr, dtype=np.uint16)

        raw = payload.get("depth_bytes") or payload.get("bytes")
        if raw and np is not None:
            arr = np.frombuffer(raw, dtype=np.uint16)
            return arr.reshape((self.height, self.width))

        # Live RealSense capture
        if _HAS_RS and np is not None:
            return self._capture_realsense()

        return None

    def _capture_realsense(self) -> Any:
        """Single-shot depth frame from a RealSense device."""
        if self._rs_pipeline is None:
            pipeline = rs.pipeline()
            cfg = rs.config()
            if self.rs_serial:
                cfg.enable_device(self.rs_serial)
            cfg.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, 30)
            try:
                pipeline.start(cfg)
                self._rs_pipeline = pipeline
            except RuntimeError:
                return None

        try:
            frames = self._rs_pipeline.wait_for_frames(timeout_ms=2000)
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                return None
            import pyrealsense2 as rs2  # local import in case of reload
            return np.asanyarray(depth_frame.get_data(), dtype=np.uint16)
        except Exception:
            return None

    def close(self) -> None:
        if self._rs_pipeline is not None:
            try:
                self._rs_pipeline.stop()
            except Exception:
                pass
            self._rs_pipeline = None
