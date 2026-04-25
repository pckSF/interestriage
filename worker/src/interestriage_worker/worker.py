from __future__ import annotations

from os import getenv

from interestriage_worker.tts import load_tts_adapter


def run_worker_once() -> str:
    adapter_name = getenv("TTS_ADAPTER", "stub")
    adapter = load_tts_adapter()
    _ = adapter.synthesize("Stage 0 readiness check", voice="default")
    return adapter_name


if __name__ == "__main__":
    used = run_worker_once()
    print(f"worker booted with tts adapter: {used}")
