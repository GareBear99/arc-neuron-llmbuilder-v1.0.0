"""OCRAdapter — text extraction from camera frames, screenshots, and images.

Bridges visual perception into the language/planning layer by reading
text visible in the environment. Feeds terminal output, signage,
instrument readouts, and UI text into the world model as structured facts.

Two backend tiers:
  1. EasyOCR  — better accuracy, GPU-optional, multi-language
  2. Tesseract (pytesseract) — fast, CPU-only, widely available

Optional deps: easyocr OR pytesseract + Pillow, numpy
Install: pip install 'arc-lucifer-cleanroom-runtime[vision]'
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from ..interfaces import Observation, ObservationBatch, SensorPacket

_MISSING: list[str] = []
_OCR_BACKEND = "none"

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False
    _MISSING.append("numpy")

try:
    from PIL import Image as _PILImage
    _HAS_PIL = True
except ImportError:
    _PILImage = None  # type: ignore
    _HAS_PIL = False

try:
    import easyocr  # type: ignore
    _OCR_BACKEND = "easyocr"
    _HAS_EASYOCR = True
except ImportError:
    easyocr = None  # type: ignore
    _HAS_EASYOCR = False

if not _HAS_EASYOCR:
    try:
        import pytesseract  # type: ignore
        _OCR_BACKEND = "pytesseract"
        _HAS_TESSERACT = True
    except ImportError:
        pytesseract = None  # type: ignore
        _HAS_TESSERACT = False
else:
    _HAS_TESSERACT = False

if _OCR_BACKEND == "none":
    _MISSING.append("easyocr or pytesseract")

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore
    _HAS_CV2 = False


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# Cached EasyOCR reader (heavy to init)
_EASYOCR_READER: Any = None


def _get_easyocr_reader(languages: list[str]) -> Any:
    global _EASYOCR_READER
    if _EASYOCR_READER is None and _HAS_EASYOCR:
        _EASYOCR_READER = easyocr.Reader(languages, gpu=False, verbose=False)
    return _EASYOCR_READER


# Alert patterns — regex patterns that trigger runtime alerts when found in OCR text
_ALERT_PATTERNS: list[tuple[str, str]] = [
    (r"\bERROR\b", "error keyword visible in scene"),
    (r"\bFAILED?\b", "failure keyword visible in scene"),
    (r"\bWARNING\b", "warning keyword visible in scene"),
    (r"\bCRITICAL\b", "critical keyword visible in scene"),
    (r"\bPASSWORD\b", "password keyword visible in scene — sensitive content flag"),
    (r"\bTRACEBACK\b", "Python traceback visible in scene"),
    (r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "IP address visible in scene"),
]


class OCRAdapter:
    """Perception adapter for text extraction from visual inputs.

    Accepts SensorPackets with image bytes, numpy arrays, or file paths.
    Runs OCR and emits ``Observation(kind="ocr_text")`` with the extracted
    text, confidence, and bounding box metadata.

    Args:
        languages: Language codes for EasyOCR (default ``["en"]``).
        confidence_floor: Drop text blocks below this OCR confidence (default 0.40).
        min_text_length: Discard single characters or noise (default 2).
        preprocess: Apply adaptive thresholding before OCR (improves accuracy
            on low-contrast inputs, costs ~5ms, default True).
        alert_on_patterns: Run alert-pattern scan on extracted text (default True).
    """

    def __init__(
        self,
        languages: list[str] | None = None,
        *,
        confidence_floor: float = 0.40,
        min_text_length: int = 2,
        preprocess: bool = True,
        alert_on_patterns: bool = True,
    ) -> None:
        self.languages = languages or ["en"]
        self.confidence_floor = confidence_floor
        self.min_text_length = min_text_length
        self.preprocess = preprocess
        self.alert_on_patterns = alert_on_patterns

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "OCRAdapter",
            "modality": "ocr",
            "backend": _OCR_BACKEND,
            "languages": self.languages,
            "available": _OCR_BACKEND != "none" and _HAS_NUMPY,
            "missing_deps": list(_MISSING),
            "capabilities": ["text_extraction", "bounding_boxes", "alert_pattern_scan"],
        }

    def process(self, packet: SensorPacket) -> ObservationBatch:
        if _OCR_BACKEND == "none" or not _HAS_NUMPY:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=(f"OCRAdapter unavailable — missing: {', '.join(_MISSING)}",),
                raw_summary="ocr adapter degraded",
            )

        image = self._extract_image(packet)
        if image is None:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("no image data found in OCR packet",),
                raw_summary="no image",
            )

        if self.preprocess and cv2 is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            image = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )

        if _OCR_BACKEND == "easyocr":
            blocks = self._run_easyocr(image)
        else:
            blocks = self._run_tesseract(image)

        observations: list[Observation] = []
        alerts: list[str] = []
        all_text_parts: list[str] = []

        for block in blocks:
            text = block.get("text", "").strip()
            conf = float(block.get("confidence", 0.0))
            if conf < self.confidence_floor or len(text) < self.min_text_length:
                continue
            all_text_parts.append(text)
            observations.append(
                Observation(
                    kind="ocr_text",
                    confidence=round(conf, 3),
                    attributes={
                        "text": text,
                        "bbox": block.get("bbox"),
                        "backend": _OCR_BACKEND,
                    },
                )
            )

        if self.alert_on_patterns:
            full_text = " ".join(all_text_parts)
            for pattern, alert_msg in _ALERT_PATTERNS:
                if re.search(pattern, full_text, re.IGNORECASE):
                    alerts.append(alert_msg)

        summary = (
            f"OCR extracted {len(observations)} text blocks via {_OCR_BACKEND}; "
            f"full text preview: {' '.join(all_text_parts)[:100]!r}"
        )
        return ObservationBatch(
            source=packet.source,
            timestamp=_utcnow(),
            observations=tuple(observations),
            alerts=tuple(alerts),
            raw_summary=summary,
        )

    def _extract_image(self, packet: SensorPacket) -> Any:
        payload = packet.payload

        arr = payload.get("frame") or payload.get("image")
        if arr is not None and np is not None:
            return np.asarray(arr, dtype=np.uint8)

        raw = payload.get("frame_bytes") or payload.get("bytes")
        if raw and np is not None and cv2 is not None:
            arr = np.frombuffer(raw, dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)

        path = payload.get("path") or payload.get("file")
        if path and cv2 is not None:
            return cv2.imread(str(path))

        return None

    def _run_easyocr(self, image: Any) -> list[dict[str, Any]]:
        reader = _get_easyocr_reader(self.languages)
        if reader is None:
            return []
        try:
            results = reader.readtext(image, detail=1)
        except Exception:
            return []
        blocks = []
        for bbox, text, conf in results:
            blocks.append({"text": text, "confidence": conf, "bbox": [list(p) for p in bbox]})
        return blocks

    def _run_tesseract(self, image: Any) -> list[dict[str, Any]]:
        if pytesseract is None:
            return []
        try:
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                lang=self.languages[0] if self.languages else "eng",
            )
        except Exception:
            return []
        blocks = []
        for i, text in enumerate(data.get("text", [])):
            text = str(text).strip()
            raw_conf = data["conf"][i]
            if raw_conf < 0:
                continue
            conf = float(raw_conf) / 100.0
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            blocks.append({
                "text": text,
                "confidence": conf,
                "bbox": [[x, y], [x+w, y], [x+w, y+h], [x, y+h]],
            })
        return blocks
