# Interestriage

Interestriage is a server-first personal content triage system. This repository is a monorepo that builds separate deployment artifacts for backend/worker, dashboard, and browser extension.

## Quick Start

1. Install prerequisites: Docker, Docker Compose, Node.js 18+, Python 3.12+, and uv.
2. Copy environment defaults if needed:
   - cp .env.example .env
3. Run tests:
   - make test
4. Start local stack:
   - make dev
5. Open dashboard:
   - http://localhost:8080

## Stage 0 Deliverables In This Repo

- Monorepo folders for extension, backend, worker, web, mobile, shared, infra, prompts, docs, tests.
- Shared backend image for API and worker entry points.
- Dev and production compose stacks using the same image tag.
- CI with linting, typing, tests, dependency scans, and SBOM generation.
- Pre-commit hooks with immutable SHA pinning, betterleaks secret scanning, zizmor, and actionlint.

See DEVELOPMENT.md for local workflow and DEPLOYMENT.md for server-hosted deployment.
