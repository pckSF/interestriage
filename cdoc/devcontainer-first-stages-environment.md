---
type: decision
tags: [devcontainer, stage-0, stage-1, stage-2, docker-compose]
created: 2026-04-26
updated: 2026-04-26
status: active
related: [specification.md, _index.md]
---
# Devcontainer Baseline For First Stages

## Context
The project currently has only the product specification and cdoc index. Stage 0 through Stage 2 in the specification require a reproducible local environment that can bootstrap tooling and run early dependencies, while not prematurely forcing all later-stage services.

## Content
### Research Findings
- The repository currently has no existing infrastructure conventions to preserve beyond [specification.md](../specification.md).
- Stage 0 defines a full local stack shape, but Stage 1 and Stage 2 can begin with a smaller dependency set if the topology can expand without redesign.
- The devcontainer reference allows Docker Compose-backed development containers with a dedicated service and sidecar dependencies.
- Docker Compose supports healthcheck-gated startup using long-form depends_on with service_healthy.
- The user requirement forbids introducing new VS Code extensions; the container configuration should therefore avoid extension installation directives.

### Options Considered
#### Option 1: Minimal early-stage dependency stack (workspace + Postgres + Redis)
- Description: Use one workspace service for tooling and two dependency services needed by early backend work, leaving later pipeline services deferred.
- Pros: Fast startup, low operational overhead, supports Stage 0-2 iteration, keeps architecture ready for staged expansion.
- Cons: Not a full fidelity representation of Stage 0 target topology on day one.

#### Option 2: Full Stage 0 topology immediately (workspace + backend + worker + proxy + parser-sandbox + db + evil-server)
- Description: Build every described service now, even before corresponding application code exists.
- Pros: Topology parity from the beginning; less future compose growth.
- Cons: Adds placeholder complexity, more brittle startup, higher maintenance before real services exist.
- Ruled out because it increases setup burden before there is runnable code for most services.

#### Option 3: Single-container devcontainer without Docker Compose
- Description: Put all tools and dependencies in one container and avoid sidecars.
- Pros: Fewer files and less compose orchestration.
- Cons: Poor parity with the server-first architecture, weak separation of concerns, harder transition to stage-level service boundaries.
- Ruled out because it conflicts with the spec's multi-service architecture and makes later migration harder.

### Decision
Choose Option 1. It preserves fast iteration and straightforward onboarding while keeping service boundaries explicit. Compared to Option 2, it avoids premature complexity and maintenance overhead. Compared to Option 3, it keeps alignment with the architecture and provides a clean path to add backend/worker/proxy/parser-sandbox/evil-server as those stages become active.

### Pre-Mortem
- Failure mode: The minimal stack drifts from later-stage topology and causes integration surprises.
  Mitigation in note: This note explicitly scopes itself to Stage 0-2 and records deferred services as follow-up work.
- Failure mode: Redis is unnecessary early and adds noise.
  Mitigation in note: Treat Redis as optional early dependency that can be removed if unused in initial implementation commits.
- Failure mode: Developers assume extension auto-install should occur in container startup.
  Mitigation in note: The implementation intentionally omits extension installation directives to satisfy the user constraint.

### Assumptions
- [confident] Stage 0-2 work can proceed productively with workspace, Postgres, and optional Redis while backend/worker code is being created.
- [likely] The team will add compose services incrementally as Stage 3+ security pipeline components are implemented.
- [uncertain] Redis will be needed before Stage 3, since the specification does not require it explicitly in early acceptance criteria.

## Changelog
- 2026-04-26: Created decision note for first-stage devcontainer strategy.
