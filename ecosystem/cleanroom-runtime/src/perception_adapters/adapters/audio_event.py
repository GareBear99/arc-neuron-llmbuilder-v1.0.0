"""AudioEventAdapter — non-speech environmental sound classification.

Fills the gap Whisper leaves: machinery noise, impact sounds, alarms,
animal calls, and ambient audio fingerprinting. Uses librosa for
feature extraction and a pluggable classifier backend.

Three classifier tiers, used in order of availability:
  1. ONNX model (fastest, most accurate — user-supplied or auto-downloaded)
  2. Spectral heuristics (zero-dep fallback — always available if librosa present)
  3. Stub degraded mode (no observation, alert only)

Optional deps: librosa, numpy, soundfile
Install: pip install 'arc-lucifer-cleanroom-runtime[audio]'
"""
from __future__ import annotations

import math
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
    import librosa  # type: ignore
    _HAS_LIBROSA = True
except ImportError:
    librosa = None  # type: ignore
    _HAS_LIBROSA = False
    _MISSING.append("librosa")

try:
    import soundfile as sf  # type: ignore
    _HAS_SF = True
except ImportError:
    sf = None  # type: ignore
    _HAS_SF = False

try:
    import onnxruntime as ort  # type: ignore
    _HAS_ONNX = True
except ImportError:
    ort = None  # type: ignore
    _HAS_ONNX = False


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Spectral heuristic classifier ───────────────────────────────────────────

# Each rule: (label, test_fn) where test_fn(features) → bool
# features = {"centroid": float, "zcr": float, "rmse": float,
#              "rolloff": float, "bandwidth": float}

_HEURISTIC_RULES: list[tuple[str, Any]] = [
    # Silence / very low energy
    ("silence", lambda f: f["rmse"] < 0.01),
    # High ZCR + low centroid → crackling / fire
    ("crackling", lambda f: f["zcr"] > 0.20 and f["centroid"] < 2000),
    # High centroid + high rolloff → alarm / siren
    ("alarm_or_siren", lambda f: f["centroid"] > 4000 and f["rolloff"] > 6000),
    # Mid centroid + low ZCR → machinery hum
    ("machinery_hum", lambda f: 200 < f["centroid"] < 1200 and f["zcr"] < 0.08),
    # High energy + wide bandwidth → impact / explosion
    ("impact_or_bang", lambda f: f["rmse"] > 0.40 and f["bandwidth"] > 3000),
    # Low freq + periodic → engine / motor
    ("engine_or_motor", lambda f: f["centroid"] < 600 and f["zcr"] < 0.05 and f["rmse"] > 0.05),
    # Moderate energy + moderate centroid → speech-like (catch-all before fallback)
    ("speech_like", lambda f: 800 < f["centroid"] < 3500 and 0.04 < f["zcr"] < 0.20),
    # Fallback
    ("unclassified_audio", lambda f: True),
]

# Alert-worthy labels for immediate kernel notification
_ALERT_LABELS = frozenset({
    "alarm_or_siren", "impact_or_bang", "crackling",
    "gunshot", "glass_breaking", "dog_bark",  # ONNX may produce these
})


class AudioEventAdapter:
    """Perception adapter for non-speech environmental sound events.

    Produces ``Observation(kind="audio_event")`` for ambient sounds that
    Whisper would ignore: machinery, impacts, alarms, animal calls, etc.

    Args:
        sample_rate: Target sample rate in Hz (default 22050, librosa's native).
        hop_length: STFT hop size (default 512).
        confidence_floor: Drop observations below this threshold (default 0.30).
        onnx_model_path: Optional path to a YAMNet/PANNs ONNX model file.
            If None and ONNX is not available, falls back to spectral heuristics.
        onnx_labels: Label list matching ONNX model output indices.
        top_k: Number of top ONNX predictions to emit as observations (default 3).
    """

    def __init__(
        self,
        sample_rate: int = 22050,
        *,
        hop_length: int = 512,
        confidence_floor: float = 0.30,
        onnx_model_path: str | None = None,
        onnx_labels: list[str] | None = None,
        top_k: int = 3,
    ) -> None:
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.confidence_floor = confidence_floor
        self.onnx_model_path = onnx_model_path
        self.onnx_labels = onnx_labels or []
        self.top_k = top_k
        self._onnx_session: Any = None
        if onnx_model_path and _HAS_ONNX:
            try:
                self._onnx_session = ort.InferenceSession(onnx_model_path)
            except Exception:
                self._onnx_session = None

    def describe(self) -> dict[str, Any]:
        backend = "onnx" if self._onnx_session else ("spectral_heuristics" if _HAS_LIBROSA else "stub")
        return {
            "adapter": "AudioEventAdapter",
            "modality": "audio_events",
            "backend": backend,
            "sample_rate": self.sample_rate,
            "available": not bool(_MISSING),
            "missing_deps": list(_MISSING),
            "onnx_model": self.onnx_model_path,
            "capabilities": ["sound_event_classification", "alarm_detection", "impact_detection", "machinery_detection"],
        }

    def process(self, packet: SensorPacket) -> ObservationBatch:
        """Classify environmental audio events from the sensor packet."""
        if _MISSING:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=(f"AudioEventAdapter unavailable — missing: {', '.join(_MISSING)}",),
                raw_summary="audio event adapter degraded",
            )

        audio = self._extract_audio(packet)
        if audio is None:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("no audio data in packet for event classification",),
                raw_summary="no audio",
            )

        if self._onnx_session is not None:
            observations, alerts = self._classify_onnx(audio)
        else:
            observations, alerts = self._classify_heuristic(audio)

        observations = [o for o in observations if o.confidence >= self.confidence_floor]
        summary = (
            f"{len(observations)} audio events from {packet.source}; "
            f"backend={'onnx' if self._onnx_session else 'heuristic'}"
        )
        return ObservationBatch(
            source=packet.source,
            timestamp=_utcnow(),
            observations=tuple(observations),
            alerts=tuple(alerts),
            raw_summary=summary,
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _extract_audio(self, packet: SensorPacket) -> Any:
        payload = packet.payload

        # numpy array already loaded by caller
        arr = payload.get("audio")
        if arr is not None and np is not None and hasattr(arr, "dtype"):
            y = arr.astype(np.float32)
            sr = payload.get("sample_rate", self.sample_rate)
            if _HAS_LIBROSA and sr != self.sample_rate:
                y = librosa.resample(y, orig_sr=sr, target_sr=self.sample_rate)
            return y

        # File path — let librosa/soundfile load it
        path = payload.get("path") or payload.get("file")
        if path and _HAS_LIBROSA:
            y, _ = librosa.load(str(path), sr=self.sample_rate, mono=True)
            return y

        # Raw PCM int16 bytes
        raw = payload.get("pcm_bytes") or payload.get("bytes")
        if raw and np is not None:
            y = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            src_sr = packet.payload.get("sample_rate", 16000)
            if _HAS_LIBROSA and src_sr != self.sample_rate:
                y = librosa.resample(y, orig_sr=src_sr, target_sr=self.sample_rate)
            return y

        return None

    def _extract_features(self, y: Any) -> dict[str, float]:
        """Compute scalar spectral features for heuristic classification."""
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=self.sample_rate, hop_length=self.hop_length)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y, hop_length=self.hop_length)))
        rmse = float(np.mean(librosa.feature.rms(y=y, hop_length=self.hop_length)))
        rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=self.sample_rate, hop_length=self.hop_length)))
        bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=self.sample_rate, hop_length=self.hop_length)))
        return {
            "centroid": centroid,
            "zcr": zcr,
            "rmse": rmse,
            "rolloff": rolloff,
            "bandwidth": bandwidth,
        }

    def _classify_heuristic(self, y: Any) -> tuple[list[Observation], list[str]]:
        features = self._extract_features(y)
        observations: list[Observation] = []
        alerts: list[str] = []

        for label, test in _HEURISTIC_RULES:
            try:
                matched = test(features)
            except Exception:
                matched = False
            if matched:
                # Confidence derived from energy for all non-silence labels
                conf = round(min(1.0, features["rmse"] * 4.0 + 0.35), 3)
                if label == "silence":
                    conf = round(1.0 - features["rmse"] * 10, 3)
                conf = max(0.0, conf)

                observations.append(
                    Observation(
                        kind="audio_event",
                        confidence=conf,
                        attributes={
                            "label": label,
                            "features": {k: round(v, 4) for k, v in features.items()},
                            "classifier": "spectral_heuristic",
                        },
                    )
                )
                if label in _ALERT_LABELS and conf >= 0.50:
                    alerts.append(f"audio alert: {label} detected (conf={conf:.2f})")
                break  # first-match wins for heuristics

        return observations, alerts

    def _classify_onnx(self, y: Any) -> tuple[list[Observation], list[str]]:
        """Run inference through a YAMNet/PANNs-compatible ONNX model."""
        if np is None:
            return [], []

        # Most audio classifiers expect a fixed-size float32 input
        input_name = self._onnx_session.get_inputs()[0].name
        input_shape = self._onnx_session.get_inputs()[0].shape
        target_len = input_shape[-1] if isinstance(input_shape[-1], int) else self.sample_rate
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)))
        else:
            y = y[:target_len]

        inp = y.reshape(1, -1).astype(np.float32)
        try:
            outputs = self._onnx_session.run(None, {input_name: inp})
        except Exception as exc:
            return [], [f"ONNX inference error: {exc}"]

        scores = np.squeeze(outputs[0])
        if scores.ndim == 0:
            return [], []

        top_indices = np.argsort(scores)[::-1][: self.top_k]
        observations: list[Observation] = []
        alerts: list[str] = []

        for idx in top_indices:
            conf = float(scores[idx])
            conf = round(min(1.0, max(0.0, conf)), 3)
            label = self.onnx_labels[int(idx)] if self.onnx_labels and int(idx) < len(self.onnx_labels) else f"class_{idx}"
            observations.append(
                Observation(
                    kind="audio_event",
                    confidence=conf,
                    attributes={
                        "label": label,
                        "class_index": int(idx),
                        "classifier": "onnx",
                    },
                )
            )
            if label in _ALERT_LABELS and conf >= 0.50:
                alerts.append(f"audio alert: {label} (conf={conf:.2f})")

        return observations, alerts
