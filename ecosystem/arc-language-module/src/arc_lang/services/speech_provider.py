from __future__ import annotations
from abc import ABC, abstractmethod
from arc_lang.core.models import SpeechRequest


class SpeechProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def speak(self, req: SpeechRequest) -> dict:
        """Execute a speech synthesis request for the given text and language."""
        raise NotImplementedError


class DisabledSpeechProvider(SpeechProvider):
    name = "disabled"

    def speak(self, req: SpeechRequest) -> dict:
        """Execute a speech synthesis request for the given text and language."""
        return {
            "ok": False,
            "provider": self.name,
            "reason": "speech_disabled",
            "language_id": req.language_id,
            "text": req.text,
        }


class PersonaPlexAdapter(SpeechProvider):
    name = "personaplex"

    def speak(self, req: SpeechRequest) -> dict:
        """Execute a speech synthesis request for the given text and language."""
        return {
            "ok": True,
            "provider": self.name,
            "mode": "dry_run" if req.dry_run else "requested",
            "language_id": req.language_id,
            "voice_hint": req.voice_hint,
            "text": req.text,
            "notes": [
                "PersonaPlex is treated as an optional downstream speech provider.",
                "This adapter is a boundary stub; live integration requires NVIDIA-compatible runtime setup.",
            ],
        }


def get_provider(name: str | None) -> SpeechProvider:
    """Return a SpeechProvider instance by provider name (disabled, personaplex, or default)."""
    if not name or name == "disabled":
        return DisabledSpeechProvider()
    if name == "personaplex":
        return PersonaPlexAdapter()
    return DisabledSpeechProvider()
