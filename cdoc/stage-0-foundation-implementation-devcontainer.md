---
type: decision
tags: [stage-0, monorepo, infra, ci, security, tooling]
created: 2026-04-26
updated: 2026-04-26
status: active
related: [specification.md, devcontainer-first-stages-environment.md, _index.md]
---
# Stage 0 Foundation Implementation In Dev Container

## Context
The repository started with only the specification, a minimal devcontainer setup, and one prior cdoc decision note about first-stage environment strategy. The user requested full Stage 0 implementation from the specification while running inside the dev container.

## Research Findings
- Stage 0 in [specification.md](../specification.md) requires a monorepo scaffold, lockfiles, CI checks, deployment scaffolding under infra, a mode-based config loader, and a StubTTS adapter.
- Existing workspace state was minimal: specification, cdoc files, and a preliminary .devcontainer setup with Postgres/Redis sidecars.
- The environment did not have Docker CLI available in the running dev container session, so local validation could not execute Docker build/compose commands directly.
- uv was installable in user space and usable for lockfile management.
- npm workspace builds for shared/web/extension succeeded, including extension zip packaging and dashboard static bundle generation.
- make test succeeded after scaffolding (12 passed, 2 skipped), validating Python/TS lint+type checks and integration guards.
- pip-audit initially reported vulnerabilities; dependency set was adjusted and CI now runs pip-audit with one explicit ignore for an unfixed pip advisory (CVE-2026-3219).
- The evil-server requirement was implemented with compose profile gating and no host-port exposure by default.

## Options Considered
#### Option 1: Full Stage 0 scaffold now (chosen)
- Description: Implement all Stage 0 deliverables immediately, including directories, tooling, CI, Docker scaffolding, config loader, StubTTS, Makefile, tests, and docs.
- Pros: Meets specification intent directly; enables subsequent stages without re-laying foundation; keeps acceptance criteria visible early.
- Cons: Larger initial change set; some checks (Docker-based) cannot be fully executed from this container.

#### Option 2: Minimal foundation only, defer infra and CI details
- Description: Add only directory skeleton and placeholder files, leaving real CI/security/infrastructure for later commits.
- Pros: Smaller and faster initial commit.
- Cons: Fails Stage 0 acceptance and security gates; pushes risk to later stages.
- Ruled out: insufficient against explicit Stage 0 deliverables.

#### Option 3: Implement Stage 0 with temporary non-workspace tooling (ad hoc scripts, no lockfiles)
- Description: Use ad hoc commands and placeholders to move quickly, then normalize later.
- Pros: Short-term speed.
- Cons: Violates reproducibility requirement and lockfile/security expectations.
- Ruled out: contradicts Stage 0 goals and would create cleanup debt immediately.

## Decision
Choose Option 1.

This approach preserves specification fidelity by delivering the required monorepo structure, reproducible tooling, security checks, and deploy scaffolding in one coherent baseline. It avoids the compliance and debt risks in Options 2 and 3, while keeping unavoidable environment constraints explicit (Docker CLI unavailable in the current dev container session).

## Pre-mortem
- Failure mode: Docker-specific acceptance checks drift because they were scaffolded but not executed here.
  Reflection in note: explicitly documented environment limitation and left docker-validated tests in place for environments where Docker CLI is available.
- Failure mode: CI security checks become noisy due advisory churn.
  Reflection in note: explicit pip-audit ignore for one currently unfixed advisory only, with all other vulnerabilities still blocking.
- Failure mode: Stage 0 scaffolding is interpreted as finished product architecture.
  Reflection in note: placeholders are clearly marked (e.g., real TTS adapter deferred), and staged boundaries remain explicit.

## Assumptions
- [confident] The new structure and tooling satisfy most Stage 0 deliverables and security controls in a testable way.
- [likely] Docker-based validation will pass in a host/devcontainer environment with Docker CLI available.
- [uncertain] The pip advisory ignore (CVE-2026-3219) remains acceptable until an upstream fix is published.

## Changelog
- 2026-04-26: Created decision record for Stage 0 implementation in the active dev container environment.
