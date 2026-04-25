from __future__ import annotations

from io import BytesIO

from interestriage_worker.tts import StubTTS, load_tts_adapter
from pydub import AudioSegment


def duration_ms(payload: bytes) -> int:
    return len(AudioSegment.from_file(BytesIO(payload), format="mp3"))


def test_stub_tts_returns_mp3_bytes() -> None:
    adapter = StubTTS()
    audio = adapter.synthesize("hello world", voice="default")

    assert isinstance(audio, bytes)
    assert len(audio) > 0


def test_stub_tts_is_deterministic_for_same_input() -> None:
    adapter = StubTTS()
    first = adapter.synthesize("repeatable text", voice="a")
    second = adapter.synthesize("repeatable text", voice="a")

    assert len(first) == len(second)
    assert duration_ms(first) == duration_ms(second)


def test_stub_tts_duration_scales_with_text_length() -> None:
    adapter = StubTTS()
    short_audio = adapter.synthesize("short", voice="default")
    long_audio = adapter.synthesize(
        "this is significantly longer text for duration scaling", voice="default"
    )

    assert duration_ms(long_audio) >= duration_ms(short_audio)


def test_load_tts_adapter_defaults_to_stub(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("TTS_ADAPTER", raising=False)
    adapter = load_tts_adapter()
    assert isinstance(adapter, StubTTS)
