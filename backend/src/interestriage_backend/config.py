from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class RuntimeDefaults:
    bind_host: str
    require_tls: bool
    rate_limit_per_minute: int
    cors_origins: tuple[str, ...]
    external_fetch_enabled: bool


@dataclass(frozen=True)
class AppConfig:
    mode: str
    bind_host: str
    port: int
    require_tls: bool
    rate_limit_per_minute: int
    cors_origins: tuple[str, ...]
    external_fetch_enabled: bool


DEFAULTS_BY_MODE: dict[str, RuntimeDefaults] = {
    "local": RuntimeDefaults(
        bind_host="127.0.0.1",
        require_tls=False,
        rate_limit_per_minute=240,
        cors_origins=("http://localhost:8080",),
        external_fetch_enabled=False,
    ),
    "server": RuntimeDefaults(
        bind_host="0.0.0.0",
        require_tls=True,
        rate_limit_per_minute=60,
        cors_origins=(),
        external_fetch_enabled=True,
    ),
}


def _parse_origins(value: str | None, defaults: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return defaults

    parsed = tuple(origin.strip() for origin in value.split(",") if origin.strip())
    return parsed or defaults


def load_config() -> AppConfig:
    mode = getenv("INTERESTRIAGE_MODE", "local").strip().lower()
    if mode not in DEFAULTS_BY_MODE:
        raise ValueError("INTERESTRIAGE_MODE must be either 'local' or 'server'")

    defaults = DEFAULTS_BY_MODE[mode]
    bind_host = getenv("API_BIND_HOST", defaults.bind_host)
    port = int(getenv("API_PORT", "8000"))
    rate_limit_per_minute = int(
        getenv("RATE_LIMIT_PER_MINUTE", str(defaults.rate_limit_per_minute))
    )
    cors_origins = _parse_origins(getenv("CORS_ORIGINS"), defaults.cors_origins)
    external_fetch_enabled = getenv(
        "EXTERNAL_FETCH_ENABLED", str(defaults.external_fetch_enabled)
    ).strip().lower() in {"1", "true", "yes", "on"}

    return AppConfig(
        mode=mode,
        bind_host=bind_host,
        port=port,
        require_tls=defaults.require_tls,
        rate_limit_per_minute=rate_limit_per_minute,
        cors_origins=cors_origins,
        external_fetch_enabled=external_fetch_enabled,
    )
