---
type: decision
tags: [security, supply-chain, github-actions, pre-commit, dependabot, stage-0]
created: 2026-04-26
updated: 2026-04-26
status: active
related: [specification.md, stage-0-foundation-implementation-devcontainer.md, _index.md]
---
# Supply Chain Hardening With SHA Pinning And Cooldowns

## Context
The repository already met Stage 0 baseline requirements, but GitHub Actions workflow actions were still pinned by mutable major tags and secret scanning relied on `detect-secrets` baseline workflows. The requested change was to implement stronger supply-chain defenses based on recent guidance: immutable pinning, workflow auditing, and delayed dependency adoption.

## Research Findings
- The referenced hardening guidance emphasizes three practical controls: `zizmor` audits, immutable SHA pinning for GitHub Actions/pre-commit hooks, and dependency cooldowns for update automation.
- Existing CI workflow used mutable tags (`@v4`, `@v5`, `@v6`) for actions and did not run `zizmor` or `actionlint` as guardrails.
- Existing pre-commit configuration used tag-based revisions and `detect-secrets`; this met baseline expectations but not strict immutable pinning.
- Verified immutable SHAs for currently used actions:
  - `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5` (`v4`)
  - `actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020` (`v4`)
  - `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065` (`v5`)
  - `docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8` (`v6`)
- Verified immutable SHAs for requested pre-commit hooks (`pre-commit-hooks`, `ruff-pre-commit`, `isort`, `zizmor-pre-commit`, `actionlint`, `betterleaks`) and applied them.
- Dependabot supports `cooldown` for `npm` and `uv` ecosystems, but cooldown semver controls are not supported for `github-actions` updates.
- A prior decision in [stage-0-foundation-implementation-devcontainer.md](stage-0-foundation-implementation-devcontainer.md) required security scanning and pinned/reproducible dependencies; this update strengthens those controls and does not conflict with that decision.
- `ty` initially failed module resolution under default execution; it became reliable with explicit `PYTHONPATH=backend/src:worker/src` in the hook entry.
- `actionlint-docker` cannot be executed in this dev-container session because Docker CLI is unavailable, but remains valid for CI runners with Docker.

## Options Considered
#### Option 1: Minimal hardening (keep existing scanners, pin workflow actions only)
- **Description:** Pin only GitHub Action `uses` references to SHAs and leave pre-commit and secret scanning stack mostly unchanged.
- **Pros:** Smallest change footprint; low operational risk.
- **Cons:** Leaves mutable pre-commit hook refs and weaker multi-layer workflow auditing coverage.

#### Option 2: Full hardening with immutable pinning + cooldown + modern scanner stack (chosen)
- **Description:** SHA-pin workflow actions and pre-commit hook repositories, add `zizmor` and `actionlint`, migrate secret scanning to `betterleaks`, and configure Dependabot cooldowns for package ecosystems.
- **Pros:** Strong defense-in-depth for workflow and dependency attack paths; aligns with modern guidance and explicit immutable-pinning best practices.
- **Cons:** More moving pieces; Docker-backed `actionlint-docker` cannot be run locally in this environment.

#### Option 3: Dependabot-only policy update without local tooling changes
- **Description:** Add cooldown config and rely on Dependabot + lockfiles, deferring pre-commit and workflow hardening.
- **Pros:** Very low immediate engineering effort.
- **Cons:** Fails to close mutable-reference risks and misses local guardrails before CI.
- **Ruled out:** Incomplete against the requested state-of-the-art hardening objective.

## Decision
Choose Option 2.

Option 2 provides measurable supply-chain hardening at both author-time and CI-time: immutable references for workflows/hooks, static workflow security auditing (`zizmor` + `actionlint`), and delayed update intake with Dependabot cooldowns. It avoids the partial-coverage weakness of Option 1 and the policy-only gap of Option 3.

## Pre-mortem
- Failure mode: Immutable pins go stale and security fixes are delayed.
  Reflection: Dependabot update automation is configured, and comments preserve upstream tag context to support routine refresh.
- Failure mode: Local developer UX degrades due stricter hooks and tool bootstrapping.
  Reflection: Hooks are deterministic and mostly auto-fixing; only Docker-dependent hook execution is deferred to CI when Docker is unavailable.
- Failure mode: Scanner migration introduces false positives that block development.
  Reflection: `.betterleaks.toml` allowlists are explicitly scoped to hash-pinning patterns to reduce noise without muting broad detection.
- Failure mode: Multiple import-format tools conflict and cause churn.
  Reflection: Import-ordering responsibility is delegated to `isort`, while Ruff import-order linting was removed to avoid formatter loops.

## Assumptions
- [confident] SHA-pinned action and pre-commit references materially reduce tag-mutation and dependency confusion risk.
- [likely] Dependabot cooldown windows (3/7/14 days) reduce exposure to fresh malicious releases while keeping update latency acceptable.
- [uncertain] `actionlint-docker` behavior in all CI environments will remain stable as runner/container defaults evolve.

## Changelog
- 2026-04-26: Recorded decision and implementation rationale for SHA pinning, scanner stack updates, and cooldown policy.
