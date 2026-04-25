# Architecture And Deviation Decisions

This file records decisions under the deviation clause in the specification.

## 2026-04-25 - Stage 0 Foundation Defaults

- Original prescription: local dev may use self-signed TLS or plain HTTP on localhost behind a proxy.
- Decision: use plain HTTP on localhost for the default dev stack and reserve TLS for production compose.
- Justification: faster onboarding in dev containers, no local certificate trust setup, no security loss for localhost-only binding.
- Risks introduced: developers may ignore HTTPS-only behavior unless they also test production compose.
- Mitigation: production compose enforces TLS via Caddy, and docs call out the difference explicitly.

## 2026-04-25 - Shared Backend Image

- Original prescription: backend and worker may run as one image with separate entry points.
- Decision: implement a shared backend image with separate commands for API, worker, and parser-sandbox.
- Justification: guarantees dependency parity and satisfies the "same images in dev and prod" requirement.
- Risks introduced: image size includes components not needed by every process.
- Mitigation: revisit image split only if measurable startup or footprint issues appear.

## 2026-04-25 - Workspace Tooling

- Original prescription: use TS for extension/web, Python for backend/worker, with lockfiles.
- Decision: npm workspaces for JS projects and uv lockfile management for Python dependencies.
- Justification: single JS lockfile and reproducible Python environment with fast CI sync.
- Risks introduced: uv becomes an additional tooling dependency.
- Mitigation: Makefile and docs bootstrap uv automatically when missing.

## 2026-04-25 - Server Runtime Container Minimalism Policy

- Original prescription: security controls require minimised exposed surface, strong supply-chain hygiene, and documented hardening for server-hosted deployments.
- Decision: all containers and services deployed on servers must use minimal runtime images by default, with no interactive shell, no package manager, and no unnecessary CLI tooling in the runtime layer.
- Justification: this reduces post-compromise pivot capability, shrinks attack surface, and aligns with the "minimised exposed surface" and hardening controls in the specification.
- Risks introduced: incident response and live debugging can become harder if operators expect shell access in production containers.
- Mitigation: use multi-stage builds (tooling in build stage only), keep dedicated debug images/procedures out of normal production deployment, and document approved break-glass workflows in runbooks.
