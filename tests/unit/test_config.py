from __future__ import annotations

import pytest
from interestriage_backend.config import load_config


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERESTRIAGE_MODE", raising=False)
    monkeypatch.delenv("API_BIND_HOST", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("EXTERNAL_FETCH_ENABLED", raising=False)


def test_load_config_defaults_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERESTRIAGE_MODE", "local")
    config = load_config()

    assert config.mode == "local"
    assert config.bind_host == "127.0.0.1"
    assert config.require_tls is False
    assert config.rate_limit_per_minute == 240
    assert config.external_fetch_enabled is False
    assert "http://localhost:8080" in config.cors_origins


def test_load_config_uses_local_defaults_without_env() -> None:
    config = load_config()

    assert config.mode == "local"
    assert config.require_tls is False
    assert config.bind_host == "127.0.0.1"


def test_load_config_server_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERESTRIAGE_MODE", "server")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com,https://ext.example.com")
    config = load_config()

    assert config.mode == "server"
    assert config.bind_host == "0.0.0.0"
    assert config.require_tls is True
    assert config.rate_limit_per_minute == 60
    assert config.external_fetch_enabled is True
    assert config.cors_origins == ("https://app.example.com", "https://ext.example.com")


def test_invalid_mode_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERESTRIAGE_MODE", "invalid")

    with pytest.raises(ValueError):
        load_config()
