"""personaplex_adapter.py — PersonaPlex voice module for ARC Lucifer.

PersonaPlex (NVIDIA/personaplex) is a real-time full-duplex speech-to-speech
model. It runs as a WebSocket server and does ASR + LLM + TTS in a single
neural pass — no pipeline latency.

This module wires PersonaPlex into ARC Lucifer in THREE roles simultaneously:

  1. PerceptionAdapter  — hears the operator/environment. Receives Opus audio
                          frames and text transcripts from the PersonaPlex server,
                          emits Observation(kind="speech_transcript") into the
                          world model via the PerceptionLoop.

  2. CognitionTier      — PersonaPlex can occupy TIER_SECONDARY in the
                          CognitionCore ladder. If the primary GGUF model fails,
                          the system's voice stays live. The FallbackConsciousness
                          Layer prefix is injected as the PersonaPlex text prompt,
                          so the voice model knows it's in fallback mode.

  3. ActionAdapter      — speaks responses. Receives text from StreamSession
                          output, sends it to PersonaPlex for synthesis, streams
                          Opus audio back to the speaker.

Protocol (from personaplex/client/src/protocol/encoder.ts):
  Client → Server:
    0x00 + version(u8) + model(u8)   handshake
    0x01 + opus_bytes                audio frame (user mic, 24kHz, ~1920 samples)
    0x02 + utf8_text                 text message / persona prompt

  Server → Client:
    0x01 + opus_bytes                AI audio response frame
    0x02 + utf8_text                 AI text transcript chunk
    0x03 + json_metadata             control/metadata

Architecture diagram:

    ┌──────────────────────────────────────────────────────────────────┐
    │ PersonaPlex Server (port 8998, WSS)                              │
    │   Mimi codec → Helium LLM → Moshi full-duplex → Mimi decode     │
    └───────────────────┬──────────────────────────────────────────────┘
          WebSocket      │
    ┌──────────────────────────────────────────────────────────────────┐
    │ PersonaPlexAdapter (this file)                                   │
    │                                                                  │
    │  Mic audio ──► 0x01 frames ──► WS server                        │
    │  WS server ──► 0x01 frames ──► Speaker (ActionAdapter.speak())  │
    │  WS server ──► 0x02 text   ──► PerceptionAdapter.process()      │
    │                               → Observation(speech_transcript)  │
    │                               → WorldModel.update_fact()        │
    │                               → StreamSession.inject()          │
    │  CognitionBackend.stream() ──► 0x02 text ──► WS server          │
    │                               ← 0x02 response text ◄─           │
    │                               → StreamEvent yield chain         │
    └──────────────────────────────────────────────────────────────────┘

Fallback consciousness integration:
    When CognitionCore switches tiers, FallbackConsciousnessLayer.build_prefix()
    returns a degradation description. This module sends it to PersonaPlex as a
    0x02 text message (persona prompt update), so the voice model speaks with
    awareness of the system's current state.

Optional deps: websockets, numpy, opuslib or pyogg
Install: pip install 'arc-lucifer-cleanroom-runtime[voice]'
"""
from __future__ import annotations

import asyncio
import json
import queue
import struct
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterator

# ── Optional imports ──────────────────────────────────────────────────────────

_MISSING: list[str] = []

try:
    import websockets  # type: ignore
    import websockets.sync.client as _ws_sync  # type: ignore
    _HAS_WS = True
except ImportError:
    websockets = None  # type: ignore
    _ws_sync = None  # type: ignore
    _HAS_WS = False
    _MISSING.append("websockets>=12")

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False
    _MISSING.append("numpy")

try:
    import opuslib  # type: ignore
    _HAS_OPUS = True
except ImportError:
    opuslib = None  # type: ignore
    _HAS_OPUS = False
    # Opus decode/encode will pass raw bytes through — PersonaPlex server handles it

# ── Perception adapter interface (avoid circular import) ─────────────────────
# We import lazily so this file can be used standalone

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Protocol constants ────────────────────────────────────────────────────────

PROTO_HANDSHAKE = 0x00
PROTO_AUDIO     = 0x01
PROTO_TEXT      = 0x02
PROTO_META      = 0x03

PERSONAPLEX_VERSION = 1
PERSONAPLEX_MODEL   = 0

SAMPLE_RATE  = 24000
FPS          = 12.5
FRAME_SAMPLES = int(SAMPLE_RATE / FPS)   # 1920 samples per frame


# ── Voice profile ─────────────────────────────────────────────────────────────

@dataclass
class VoiceProfile:
    """Persona configuration for a PersonaPlex session.

    Args:
        voice_id:    Pre-packaged voice embedding ID, e.g. ``"NATM1"`` or
                     ``"NATF2"``. Must match a .pt file in the server's
                     voice prompt directory.
        text_prompt: Behavioral persona description. The FallbackConsciousness
                     Layer's degradation prefix is appended to this when active.
        language:    BCP-47 language code (default ``"en"``).
        seed:        Deterministic seed for reproducible voice output (default 42).
    """
    voice_id: str = "NATM1"
    text_prompt: str = "You are a wise and helpful assistant. Be concise and precise."
    language: str = "en"
    seed: int = 42424242

    def with_consciousness_prefix(self, prefix: str | None) -> "VoiceProfile":
        """Return a new profile with the consciousness prefix appended."""
        if not prefix:
            return self
        combined = f"{self.text_prompt}\n\n[SYSTEM STATE]:\n{prefix}"
        return VoiceProfile(
            voice_id=self.voice_id,
            text_prompt=combined,
            language=self.language,
            seed=self.seed,
        )


# ── Shared WebSocket connection (one per PersonaPlex server) ──────────────────

class PersonaPlexConnection:
    """Manages one persistent WebSocket connection to a PersonaPlex server.

    Runs a background thread that:
    - Continuously reads frames from the server
    - Queues audio frames for the speaker
    - Queues text chunks for the perception adapter and cognition backend
    - Routes audio frames from the mic to the server

    All three adapter roles share a single connection instance.

    Args:
        url:     PersonaPlex server WSS URL, e.g. ``"wss://localhost:8998"``.
        profile: Voice profile and persona configuration.
        ssl_verify: Set False for self-signed certs in development (default False).
    """

    def __init__(
        self,
        url: str = "wss://localhost:8998",
        profile: VoiceProfile | None = None,
        ssl_verify: bool = False,
    ) -> None:
        self.url = url
        self.profile = profile or VoiceProfile()
        self.ssl_verify = ssl_verify

        self._audio_out_queue: queue.Queue[bytes] = queue.Queue(maxsize=64)
        self._text_out_queue: queue.Queue[str] = queue.Queue(maxsize=256)
        self._audio_in_queue: queue.Queue[bytes] = queue.Queue(maxsize=64)
        self._meta_queue: queue.Queue[dict] = queue.Queue(maxsize=32)

        self._ws = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._connected = threading.Event()
        self._lock = threading.Lock()
        self._error: str = ""
        self._frame_count = 0
        self._text_count = 0

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    @property
    def last_error(self) -> str:
        return self._error

    def connect(self, timeout: float = 10.0) -> bool:
        """Establish WebSocket connection and start background reader thread."""
        if not _HAS_WS:
            self._error = f"websockets not installed — missing: {_MISSING}"
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="PersonaPlexConnection",
            daemon=True,
        )
        self._thread.start()
        return self._connected.wait(timeout=timeout)

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        self._connected.clear()

    def send_audio_frame(self, opus_bytes: bytes) -> None:
        """Send one Opus audio frame from the microphone to the server."""
        try:
            self._audio_in_queue.put_nowait(opus_bytes)
        except queue.Full:
            pass  # drop frame rather than block

    def send_text(self, text: str) -> None:
        """Send a text message (persona update or operator injection) to the server."""
        # Will be picked up by the write loop
        try:
            self._audio_in_queue.put_nowait(_encode_text(text))
        except queue.Full:
            pass

    def recv_audio_frame(self, timeout: float = 0.1) -> bytes | None:
        """Get one AI audio frame (Opus) for the speaker. Non-blocking."""
        try:
            return self._audio_out_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def recv_text(self, timeout: float = 0.05) -> str | None:
        """Get one AI text transcript chunk. Non-blocking."""
        try:
            return self._text_out_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def update_persona(self, profile: VoiceProfile) -> None:
        """Hot-swap persona mid-session by sending a new text prompt."""
        with self._lock:
            self.profile = profile
        self.send_text(profile.text_prompt)

    def status(self) -> dict[str, Any]:
        return {
            "connected": self.is_connected,
            "url": self.url,
            "voice_id": self.profile.voice_id,
            "frames_received": self._frame_count,
            "text_chunks_received": self._text_count,
            "audio_out_queue_size": self._audio_out_queue.qsize(),
            "text_out_queue_size": self._text_out_queue.qsize(),
            "last_error": self._error,
            "missing_deps": _MISSING,
        }

    # ── Background I/O loop ──────────────────────────────────────────────────

    def _run_loop(self) -> None:
        import ssl as _ssl
        ssl_ctx = _ssl.create_default_context()
        if not self.ssl_verify:
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = _ssl.CERT_NONE
        try:
            with _ws_sync.connect(self.url, ssl=ssl_ctx) as ws:
                self._ws = ws
                # Handshake
                ws.send(bytes([PROTO_HANDSHAKE, PERSONAPLEX_VERSION, PERSONAPLEX_MODEL]))
                # Send voice profile
                ws.send(_encode_text(self.profile.text_prompt))
                self._connected.set()

                # Start writer thread
                writer = threading.Thread(target=self._write_loop, args=(ws,), daemon=True)
                writer.start()

                # Reader loop
                while not self._stop_event.is_set():
                    try:
                        msg = ws.recv(timeout=0.5)
                    except TimeoutError:
                        continue
                    if isinstance(msg, bytes):
                        self._handle_server_message(msg)
                    elif isinstance(msg, str):
                        self._handle_text_message(msg)

                writer.join(timeout=2.0)
        except Exception as exc:
            self._error = str(exc)
        finally:
            self._connected.clear()

    def _write_loop(self, ws: Any) -> None:
        """Drain audio_in_queue and send frames to the server."""
        while not self._stop_event.is_set():
            try:
                data = self._audio_in_queue.get(timeout=0.1)
                ws.send(data)
            except queue.Empty:
                continue
            except Exception as exc:
                self._error = f"write error: {exc}"
                break

    def _handle_server_message(self, msg: bytes) -> None:
        if not msg:
            return
        kind = msg[0]
        payload = msg[1:]
        if kind == PROTO_AUDIO:
            self._frame_count += 1
            try:
                self._audio_out_queue.put_nowait(payload)
            except queue.Full:
                pass
        elif kind == PROTO_TEXT:
            self._text_count += 1
            try:
                self._text_out_queue.put_nowait(payload.decode("utf-8", errors="replace"))
            except queue.Full:
                pass
        elif kind == PROTO_META:
            try:
                meta = json.loads(payload.decode("utf-8", errors="replace"))
                self._meta_queue.put_nowait(meta)
            except Exception:
                pass

    def _handle_text_message(self, msg: str) -> None:
        try:
            self._text_out_queue.put_nowait(msg)
        except queue.Full:
            pass


def _encode_text(text: str) -> bytes:
    return bytes([PROTO_TEXT]) + text.encode("utf-8")


# ── PerceptionAdapter role ────────────────────────────────────────────────────

class PersonaPlexPerceptionAdapter:
    """Perception adapter — hears the operator via PersonaPlex full-duplex stream.

    Reads text transcript chunks from the PersonaPlexConnection and emits
    ``Observation(kind="speech_transcript")`` batches. Replaces WhisperSpeechAdapter
    for live conversational voice — PersonaPlex does ASR internally as part of
    the full-duplex pass, so no separate Whisper call is needed.

    Wire into PerceptionLoop at 2–4 Hz (PersonaPlex chunks arrive ~12.5fps but
    transcript text accumulates; polling at 2Hz is sufficient for world model updates).

    Args:
        connection: Shared PersonaPlexConnection instance.
        confidence_floor: Drop observations below this (default 0.60 — PersonaPlex
            transcripts are high quality so floor can be higher than Whisper).
        alert_keywords: Spoken words that trigger runtime alerts.
    """

    def __init__(
        self,
        connection: PersonaPlexConnection,
        *,
        confidence_floor: float = 0.60,
        alert_keywords: list[str] | None = None,
    ) -> None:
        self.connection = connection
        self.confidence_floor = confidence_floor
        self.alert_keywords = alert_keywords or ["stop", "abort", "emergency", "help", "fire"]

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "PersonaPlexPerceptionAdapter",
            "modality": "audio_speech",
            "backend": "personaplex_fullduplex",
            "available": _HAS_WS and self.connection.is_connected,
            "missing_deps": list(_MISSING),
            "connected": self.connection.is_connected,
            "capabilities": ["speech_transcript", "full_duplex", "real_time_asr"],
        }

    def process(self, packet: Any) -> Any:
        """Drain pending transcript chunks and return as ObservationBatch."""
        from perception_adapters.interfaces import Observation, ObservationBatch

        if not self.connection.is_connected:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                alerts=("PersonaPlex not connected",),
                raw_summary="not connected",
            )

        chunks: list[str] = []
        while True:
            text = self.connection.recv_text(timeout=0.01)
            if text is None:
                break
            chunks.append(text)

        if not chunks:
            return ObservationBatch(
                source=packet.source,
                timestamp=_utcnow(),
                raw_summary="no new transcript",
            )

        full_text = " ".join(chunks)
        observations = []
        alerts = []

        observations.append(
            Observation(
                kind="speech_transcript",
                confidence=0.85,  # PersonaPlex integrated ASR is high quality
                attributes={
                    "text": full_text,
                    "language": self.connection.profile.language,
                    "chunk_count": len(chunks),
                    "backend": "personaplex",
                    "voice_id": self.connection.profile.voice_id,
                },
            )
        )

        # Alert scan
        lowered = full_text.lower()
        for kw in self.alert_keywords:
            if kw in lowered:
                alerts.append(f"vocal keyword detected: '{kw}' in operator speech")

        return ObservationBatch(
            source=packet.source,
            timestamp=_utcnow(),
            observations=tuple(o for o in observations if o.confidence >= self.confidence_floor),
            alerts=tuple(alerts),
            raw_summary=f"transcript: {full_text[:80]!r}",
        )


# ── CognitionTier backend role ────────────────────────────────────────────────

class PersonaPlexCognitionBackend:
    """StreamingModel-compatible backend that uses PersonaPlex as the cognition core.

    Occupies TIER_SECONDARY (or any tier) in CognitionCore. When the primary
    GGUF model fails, this backend keeps the system conversationally alive via
    full-duplex voice.

    Text in → sent as 0x02 to PersonaPlex → server responds with text chunks
    → yielded as StreamEvent tokens. Audio is handled in parallel by the
    ActionAdapter (speaker output) and PerceptionAdapter (mic input).

    The FallbackConsciousnessLayer prefix is sent as a persona prompt update
    before each generation, so PersonaPlex speaks with awareness of the system's
    current tier state.

    Args:
        connection: Shared PersonaPlexConnection instance.
        response_timeout_s: Max seconds to wait for first response token (default 5.0).
        stream_end_silence_s: Silence window to declare stream complete (default 1.5).
    """

    def __init__(
        self,
        connection: PersonaPlexConnection,
        *,
        response_timeout_s: float = 5.0,
        stream_end_silence_s: float = 1.5,
    ) -> None:
        self.connection = connection
        self.response_timeout_s = response_timeout_s
        self.stream_end_silence_s = stream_end_silence_s

    def generate(self, prompt: str, context: dict | None = None, options: dict | None = None) -> str:
        """Blocking generate — collects full stream response."""
        return "".join(
            event.text
            for event in self.stream_generate(prompt, context=context, options=options)
            if event.text and not event.text.startswith("[")
        )

    def stream_generate(
        self,
        prompt: str,
        context: dict | None = None,
        options: dict | None = None,
    ) -> Iterator[Any]:
        """Stream text response from PersonaPlex as StreamEvents."""
        from model_services.interfaces import StreamEvent

        if not self.connection.is_connected:
            text = "[PersonaPlex not connected — voice tier unavailable]"
            yield StreamEvent(
                text=text, sequence=0,
                chars_emitted=len(text), words_emitted=len(text.split()),
                estimated_tokens=len(text) // 4, done=True,
            )
            return

        # Flush stale text from queue
        while self.connection.recv_text(timeout=0.001) is not None:
            pass

        # Send prompt as text message
        self.connection.send_text(prompt)

        seq = 0
        total_chars = 0
        total_words = 0
        last_text_at = time.monotonic()
        deadline = time.monotonic() + self.response_timeout_s

        while True:
            text = self.connection.recv_text(timeout=0.05)

            if text:
                last_text_at = time.monotonic()
                total_chars += len(text)
                total_words += len(text.split())
                yield StreamEvent(
                    text=text,
                    sequence=seq,
                    chars_emitted=total_chars,
                    words_emitted=total_words,
                    estimated_tokens=total_chars // 4,
                    done=False,
                )
                seq += 1
            else:
                now = time.monotonic()
                # Timed out waiting for first token
                if seq == 0 and now > deadline:
                    err = "[PersonaPlex response timeout]"
                    yield StreamEvent(
                        text=err, sequence=0,
                        chars_emitted=len(err), words_emitted=1,
                        estimated_tokens=5, done=True,
                    )
                    return
                # Silence window after receiving some text = stream complete
                if seq > 0 and (now - last_text_at) > self.stream_end_silence_s:
                    yield StreamEvent(
                        text="",
                        sequence=seq,
                        chars_emitted=total_chars,
                        words_emitted=total_words,
                        estimated_tokens=total_chars // 4,
                        done=True,
                    )
                    return


# ── ActionAdapter role ────────────────────────────────────────────────────────

class PersonaPlexVoiceOutputAdapter:
    """Action adapter — speaks StreamSession text output through PersonaPlex.

    Receives text from the cognition layer (via StreamSession or direct call),
    sends it to PersonaPlex as a 0x02 message, and plays back the AI audio
    response in real time.

    Playback is via sounddevice (if available) or saved to a buffer for
    external consumption.

    Args:
        connection: Shared PersonaPlexConnection instance.
        sample_rate: Speaker output sample rate (default 24000).
        use_sounddevice: Attempt real-time playback via sounddevice (default True).
    """

    def __init__(
        self,
        connection: PersonaPlexConnection,
        *,
        sample_rate: int = SAMPLE_RATE,
        use_sounddevice: bool = True,
    ) -> None:
        self.connection = connection
        self.sample_rate = sample_rate
        self.use_sounddevice = use_sounddevice
        self._sd = None
        if use_sounddevice:
            try:
                import sounddevice as sd  # type: ignore
                self._sd = sd
            except (ImportError, OSError):
                pass

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "PersonaPlexVoiceOutputAdapter",
            "mode": "action",
            "available": _HAS_WS and self.connection.is_connected,
            "playback": "sounddevice" if self._sd else "buffer_only",
            "capabilities": ["text_to_speech", "full_duplex_voice", "persona_voice"],
        }

    def perform(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Speak the given text through PersonaPlex.

        Action string: ``"speak"``
        Params: ``{"text": "Hello, world", "update_persona": "<optional prefix>"}``
        """
        p = params or {}
        text = p.get("text", action)
        persona_update = p.get("update_persona")

        if persona_update:
            updated = self.connection.profile.with_consciousness_prefix(persona_update)
            self.connection.update_persona(updated)

        if not self.connection.is_connected:
            return {"status": "error", "reason": "PersonaPlex not connected"}

        self.connection.send_text(text)

        # Collect and optionally play back audio response
        audio_frames: list[bytes] = []
        silence_start = time.monotonic()
        while time.monotonic() - silence_start < 3.0:
            frame = self.connection.recv_audio_frame(timeout=0.1)
            if frame:
                audio_frames.append(frame)
                silence_start = time.monotonic()

        if self._sd and audio_frames and _HAS_OPUS:
            try:
                pcm = self._decode_opus_frames(audio_frames)
                self._sd.play(pcm, samplerate=self.sample_rate)
                self._sd.wait()
            except Exception as exc:
                return {"status": "partial", "audio_frames": len(audio_frames), "playback_error": str(exc)}

        return {
            "status": "ok",
            "text_spoken": text,
            "audio_frames": len(audio_frames),
            "audio_bytes": sum(len(f) for f in audio_frames),
        }

    def _decode_opus_frames(self, frames: list[bytes]) -> Any:
        if not _HAS_OPUS or not _HAS_NUMPY:
            return None
        decoder = opuslib.Decoder(self.sample_rate, 1)  # mono
        pcm_chunks = []
        for frame in frames:
            try:
                pcm = decoder.decode(frame, FRAME_SAMPLES)
                arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
                pcm_chunks.append(arr)
            except Exception:
                continue
        return np.concatenate(pcm_chunks) if pcm_chunks else np.zeros(0, dtype=np.float32)


# ── Convenience builder ───────────────────────────────────────────────────────

def build_personaplex_module(
    *,
    url: str = "wss://localhost:8998",
    profile: VoiceProfile | None = None,
    ssl_verify: bool = False,
    connect_timeout: float = 10.0,
) -> dict[str, Any]:
    """Build and connect all three PersonaPlex adapter roles.

    Returns a dict with keys:
      - ``connection``  — shared PersonaPlexConnection
      - ``perception``  — PersonaPlexPerceptionAdapter  (PerceptionAdapter)
      - ``cognition``   — PersonaPlexCognitionBackend   (CognitionTier backend)
      - ``voice``       — PersonaPlexVoiceOutputAdapter (ActionAdapter)
      - ``connected``   — bool

    Usage::

        from perception_adapters.personaplex_adapter import build_personaplex_module
        from cognition_services import TIER_SECONDARY

        module = build_personaplex_module(url="wss://localhost:8998")

        # 1. Register as perception adapter
        perception_loop.register("voice_in", module["perception"],
                                 schedule=AdapterSchedule(tick_hz=2.0))

        # 2. Register as CognitionCore tier
        cognition_core.add_tier(TIER_SECONDARY, module["cognition"],
                                capabilities=["generate", "stream", "voice"])

        # 3. Register as action adapter
        adapter_registry.register_action("voice_out", module["voice"])

        # 4. Wire consciousness prefix to persona hot-swap
        def on_tier_change(evt):
            prefix = consciousness.build_prefix()
            if prefix:
                module["connection"].update_persona(
                    profile.with_consciousness_prefix(prefix)
                )
        cognition_core.on_tier_change = on_tier_change
    """
    vp = profile or VoiceProfile()
    conn = PersonaPlexConnection(url=url, profile=vp, ssl_verify=ssl_verify)
    connected = conn.connect(timeout=connect_timeout)

    return {
        "connection": conn,
        "perception": PersonaPlexPerceptionAdapter(conn),
        "cognition":  PersonaPlexCognitionBackend(conn),
        "voice":      PersonaPlexVoiceOutputAdapter(conn),
        "connected":  connected,
        "profile":    vp,
        "url":        url,
    }
