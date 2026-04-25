# Deployment Modes

Interestriage supports two modes from the same codebase and images.

## Local-Only Mode

- INTERESTRIAGE_MODE=local
- Backend binds to localhost-equivalent defaults.
- HTTP is acceptable when bound to localhost only.
- Intended for single-machine privacy-first setup.

## Server-Hosted Mode (Default)

- INTERESTRIAGE_MODE=server
- Deploy via infra/production/docker-compose.yml
- Reverse proxy terminates TLS with Let's Encrypt.
- HSTS is enabled at the proxy layer.

## Production Bring-Up

1. Build and publish images using make build.
2. Set environment values for PUBLIC_BASE_URL and LETSENCRYPT_EMAIL.
3. Launch production stack:
   - docker compose -f infra/production/docker-compose.yml up -d
4. Validate HTTPS and API health.

## Security Baseline

- Per-device auth tokens (implemented in Stage 2).
- Secret scanning and dependency scanning in CI.
- Private-by-default output directories.
