"""WhisperSpeechAdapter — speech transcription via OpenAI Whisper.

Decodes audio from PCM bytes or file paths (via FFmpeg) and produces
structured transcript Observations with language, confidence, and
segment metadata. Never writes raw audio bytes to world state.

Optional deps: openai-whisper (or faster-whisper), numpy, ffmpeg-python
Install: pip install 'arc-lucifer-cleanroom-runtime[audio]'
"""
from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from ..interfaces import Observation, ObservationBatch, SensorPacket

_MISSING: list[str] = []
_WHISPER_BACKEND: str = "none"

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False
    _MISSING.append("numpy")

try:
    import whisper as _whisper_mod  # openai-whisper
    _WHISPER_BACKEND = "openai-whisper"
    _HAS_WHISPER = True
except ImportError:
    _whisper_mod = None  # type: ignore
    _HAS_WHISPER = False

if not _HAS_WHISPER:
    try:
        from faster_whisper import WhisperModel as _FasterWhisperModel  # type: ignore
        _WHISPER_BACKEND = "faster-whisper"
        _HAS_WHISPER = True
    except ImportError:
        _FasterWhisperModel = None  # type: ignore

if not _HAS_WHISPER:
    _MISSING.append("openai-whisper or faster-whisper")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# Module-level model cache — loaded once per process
_MODEL_CACHE: dict[str, Any] = {}


def _load_model(model_size: str) -> Any:
    if model_size in _MODEL_CACHE:
        return _MODEL_CACHE[model_size]
    if _WHISPER_BACKEND == "openai-whisper" and _whisper_mod is not None:
        model = _whisper_mod.load_model(model_size)
    elif _WHISPER_BACKEND == "faster-whisper" and _FasterWhisperModel is not None:
        model = _FasterWhisperModel(model_size, compute_type="int8")
    else:
        return None
    _MODEL_CACHE[model_size] = model
    return model


class WhisperSpeechAdapter:
    """Perception adapter for speech transcription.

    Accepts SensorPackets carrying raw PCM audio bytes, a file path, or
    a numpy float32 array under ``packet.payload["audio"]``. Transcribes
    via Whisper and emits ``Observation(kind="speech_transcript")``.

    Args:
        model_size: Whisper model variant. One of ``"tiny"``, ``"base"``,
            ``"small"``, ``"medium"``, ``"large"`` (default ``"base"``).
        language: Force language code (e.g. ``"en"``). ``None`` = auto-detect.
        sample_rate: Expected audio sample rate in Hz (default 16000).
        confidence_floor: Drop segments below this confidence (default 0.3).
        min_segment_chars: Drop segments shorter than this (default 3).
    """

    def __init__(
        self,
        model_size: str = "base",
        *,
        language: str | None = None,
        sample_rate: int = 16000,
        confidence_floor: float = 0.30,
        min_segment_chars: int = 3,
    ) -> None:
        self.model_size = model_size
        self.language = language
        self.sample_rate = sample_rate
        self.confidence_floor = confidence_floor
        self.min_segment_chars = min_segment_chars

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "WhisperSpeechAdapter",
            "modality": "audio_speech",
            "model_size": self.model_size,
            "backend": _WHISPER_BACKEND,
            "language": self.language or "auto",
            "available": not bool(_MISSING),
            "missing_deps": list(_MISSING),
            "capabilities": ["speech_transcript", "language_detection", "segment_timestamps"],
        }

    def process(self, packet: SensorPacket) -> ObservationBatch:
        """Transcribe speech audio from the sensor packet."""
        if _MISSING:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=(f"WhisperSpeechAdapter unavailable — missing: {', '.join(_MISSING)}",),
                raw_summary="speech adapter degraded",
            )

        audio_data = self._extract_audio(packet)
        if audio_data is None:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("no audio data found in packet payload",),
                raw_summary="no audio",
            )

        model = _load_model(self.model_size)
        if model is None:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("Whisper model could not be loaded",),
                raw_summary="model load failure",
            )

        segments, language, full_text = self._transcribe(model, audio_data)
        observations: list[Observation] = []
        alerts: list[str] = []

        for seg in segments:
            text = seg.get("text", "").strip()
            conf = float(seg.get("confidence", seg.get("avg_logprob", -1.0)))
            # avg_logprob is negative — convert to [0,1] range
            if conf < 0:
                conf = max(0.0, 1.0 + conf)  # e.g. -0.3 → 0.7
            conf = round(min(1.0, conf), 3)

            if conf < self.confidence_floor:
                continue
            if len(text) < self.min_segment_chars:
                continue

            observations.append(
                Observation(
                    kind="speech_transcript",
                    confidence=conf,
                    attributes={
                        "text": text,
                        "language": language,
                        "start_s": round(seg.get("start", 0.0), 2),
                        "end_s": round(seg.get("end", 0.0), 2),
                        "model": self.model_size,
                        "backend": _WHISPER_BACKEND,
                    },
                )
            )

        if full_text.strip():
            alerts_from_content = self._scan_for_alerts(full_text)
            alerts.extend(alerts_from_content)

        summary = (
            f"transcribed {len(segments)} segments in {language}; "
            f"{len(observations)} accepted; full text: {full_text[:120]!r}"
        )
        return ObservationBatch(
            source=packet.source,
            timestamp=_utcnow(),
            observations=tuple(observations),
            alerts=tuple(alerts),
            raw_summary=summary,
        )

    def _extract_audio(self, packet: SensorPacket) -> Any:
        """Return a numpy float32 array at self.sample_rate, or None."""
        payload = packet.payload

        # Already a numpy array
        audio = payload.get("audio")
        if audio is not None and np is not None:
            if hasattr(audio, "dtype"):
                return audio.astype(np.float32)

        # File path
        path = payload.get("path") or payload.get("file")
        if path and _HAS_WHISPER and np is not None:
            if _WHISPER_BACKEND == "openai-whisper":
                return _whisper_mod.load_audio(str(path))
            # faster-whisper accepts file paths directly during transcribe
            return str(path)

        # Raw PCM bytes
        raw = payload.get("pcm_bytes") or payload.get("bytes")
        if raw and np is not None:
            arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return arr

        return None

    def _transcribe(self, model: Any, audio_data: Any) -> tuple[list[dict], str, str]:
        """Run transcription, normalize output across backends."""
        segments_out: list[dict] = []
        language = self.language or "unknown"
        full_text = ""

        if _WHISPER_BACKEND == "openai-whisper":
            opts: dict[str, Any] = {"fp16": False}
            if self.language:
                opts["language"] = self.language
            result = model.transcribe(audio_data, **opts)
            language = result.get("language", "unknown")
            full_text = result.get("text", "")
            for seg in result.get("segments", []):
                segments_out.append({
                    "text": seg.get("text", ""),
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", 0.0),
                    "confidence": seg.get("avg_logprob", -0.5),
                })

        elif _WHISPER_BACKEND == "faster-whisper":
            kwargs: dict[str, Any] = {}
            if self.language:
                kwargs["language"] = self.language
            segs, info = model.transcribe(audio_data, **kwargs)
            language = info.language if hasattr(info, "language") else "unknown"
            texts: list[str] = []
            for seg in segs:
                texts.append(seg.text)
                segments_out.append({
                    "text": seg.text,
                    "start": seg.start,
                    "end": seg.end,
                    "confidence": getattr(seg, "avg_logprob", -0.5),
                })
            full_text = " ".join(texts)

        return segments_out, language, full_text

    @staticmethod
    def _scan_for_alerts(text: str) -> list[str]:
        """Flag acoustically important keywords for the runtime alert channel."""
        keywords = {
            "help": "vocal distress keyword detected: 'help'",
            "emergency": "vocal distress keyword detected: 'emergency'",
            "fire": "vocal distress keyword detected: 'fire'",
            "stop": "vocal command detected: 'stop'",
            "abort": "vocal command detected: 'abort'",
        }
        lowered = text.lower()
        return [msg for kw, msg in keywords.items() if kw in lowered]
