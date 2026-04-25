from __future__ import annotations

from io import BytesIO
from os import getenv
from typing import Protocol

from pydub import AudioSegment


class TTSAdapter(Protocol):
    def synthesize(self, text: str, voice: str) -> bytes:
        """Convert text into encoded audio bytes."""


class StubTTS:
    def synthesize(self, text: str, voice: str) -> bytes:
        duration_ms = max(750, min(12_000, len(text.strip()) * 28))
        segment = AudioSegment.silent(duration=duration_ms)
        output = BytesIO()
        segment.export(output, format="mp3", bitrate="64k")
        return output.getvalue()


class PlaceholderRealTTS:
    def synthesize(self, text: str, voice: str) -> bytes:
        raise NotImplementedError("Real TTS adapter integration starts in Stage 8")


def load_tts_adapter() -> TTSAdapter:
    adapter_name = getenv("TTS_ADAPTER", "stub").strip().lower()
    if adapter_name == "stub":
        return StubTTS()

    return PlaceholderRealTTS()
