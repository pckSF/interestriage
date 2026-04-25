# Development Workflow

## Prerequisites

- Docker and Docker Compose
- Node.js 18+
- Python 3.12+
- uv (https://docs.astral.sh/uv/)

## Bring Up Local Stack

- make dev

The dev stack launches through infra/dev/docker-compose.yml with these services:

- backend (FastAPI)
- worker (batch process)
- db (Postgres)
- proxy (nginx)
- parser-sandbox (resource-capped process)

The dashboard is served through the proxy at http://localhost:8080.

## Test Commands

- make test: lint, type-check, and Python tests.
- make test-ssrf: Stage 3 scaffold tests with evil-server profile.
- make test-audio: real TTS test target (skips unless configured).
- make pip-audit-container: build and run pip-audit in an isolated hardened container.

Containerized pip-audit examples:

- make pip-audit-container
- make pip-audit-container PIP_AUDIT_ARGS=". --ignore-vuln CVE-2026-3219"

## Notes

- The evil-server service is profile-gated and never starts in default make dev.
- StubTTS is the default adapter in local development.
