from __future__ import annotations

import os

import pytest
from interestriage_worker.tts import load_tts_adapter


@pytest.mark.audio_real
def test_real_tts_adapter_path_configured() -> None:
    if os.getenv("TTS_ADAPTER", "stub").lower() == "stub":
        pytest.skip("Real adapter not configured")

    adapter = load_tts_adapter()
    with pytest.raises(NotImplementedError):
        adapter.synthesize("audio test", voice="default")
