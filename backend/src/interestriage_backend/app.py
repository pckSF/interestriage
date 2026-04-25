from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from interestriage_backend.config import AppConfig, load_config


def create_app(config: AppConfig | None = None) -> FastAPI:
    active_config = config or load_config()

    app = FastAPI(title="Interestriage API", version="0.1.0")

    if active_config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(active_config.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/api/v1/health")
    def health() -> dict[str, str | int | bool]:
        return {
            "status": "ok",
            "mode": active_config.mode,
            "require_tls": active_config.require_tls,
            "rate_limit_per_minute": active_config.rate_limit_per_minute,
            "external_fetch_enabled": active_config.external_fetch_enabled,
        }

    return app


app = create_app()
