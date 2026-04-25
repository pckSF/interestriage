---
type: decision
tags: [security, supply-chain, pip-audit, containers, chainguard]
created: 2026-04-25
updated: 2026-04-25
status: active
related: [stage-0-foundation-implementation-devcontainer.md, supply-chain-hardening-pinning-cooldown.md, .github/workflows/ci.yml, infra/Dockerfile.backend, _index.md]
---
# Viability Of Containerized pip-audit With Chainguard Python

## Context
The current CI executes Python dependency auditing as `uv run pip-audit --ignore-vuln CVE-2026-3219` in the workflow environment. The proposed alternative is an isolated containerized execution based on a pinned Chainguard Python image to avoid polluting local environments and allow disposable audit runs.

Proposed example:
- Uses `cgr.dev/chainguard/python@sha256:...`.
- Installs `pip-audit==2.9.0` inside the image.
- Runs `python -m pip_audit` via container entrypoint.

## Research Findings
- Current repo behavior uses environment-mode pip-audit in CI and currently reports no known vulnerabilities after one explicit ignore.
- In this repository, `pip-audit --locked .` fails with "no lockfiles found" because pip-audit lockfile mode currently supports `pyproject.toml` and `pylock.*.toml`, not `uv.lock`.
- `pip-audit .` succeeds for this project, indicating project-path auditing is workable without relying exclusively on active environment package listing.
- Official pip-audit documentation states exit code `1` is returned when vulnerabilities are found (useful for fail-fast security gates) and emphasizes that auditing untrusted dependency inputs has similar risk posture to installing them.
- Official pip-audit docs also provide a maintained GitHub Action (`pypa/gh-action-pip-audit`) as a first-party CI integration path.
- Chainguard Python documentation describes minimal and `-dev` variants, with guidance to use multi-stage builds for package installation and copy artifacts into minimal runtime.
- Chainguard Python images are documented as minimal, nonroot-by-default, and supply-chain focused (daily rebuilds, provenance/SBOM/signatures).
- This dev container currently has no Docker CLI available, so local containerized audit execution is not currently runnable in this environment.
- Existing cdoc decisions prioritize reproducible and pinned supply-chain controls; a digest-pinned Chainguard image is consistent with those constraints.

## Options Considered
#### Option 1: Keep current host-environment pip-audit in CI only
- Description: Continue using `uv run pip-audit` in CI and local development without dedicated audit containerization.
- Pros: Lowest complexity; fastest integration with current workflow; already working in this repo.
- Cons: Local runs can affect developer environment/tooling surface; weaker isolation boundary for ad hoc scans.

#### Option 2: Use official `pypa/gh-action-pip-audit` in CI
- Description: Replace manual pip-audit invocation with the maintained PyPA action.
- Pros: First-party integration surface; richer action-level configuration; less custom command glue.
- Cons: Another third-party workflow dependency to maintain/pin; does not directly solve local environment pollution concerns.
- Ruled out: Good CI option, but it does not address the local disposable-container goal directly.

#### Option 3: Use a hardened disposable container for pip-audit (chosen with constraints)
- Description: Run pip-audit from a digest-pinned Chainguard-based container for local/CI scans where Docker is available; treat the container as ephemeral and disposable.
- Pros: Strong isolation from host Python environment; aligns with immutable-image hardening; easy teardown after scan.
- Cons: Requires container runtime availability; can increase execution time due dependency resolution in-container; proposed single-stage Dockerfile may conflict with Chainguard guidance if package tooling is absent in minimal variant.

## Decision
Choose Option 3 as viable, but with explicit implementation constraints.

A disposable hardened container is a viable pattern for pip-audit when the goal is host isolation and fast disposal after findings. It improves local safety posture versus Option 1 while preserving pinned-supply-chain properties. However, viability depends on runner/runtime availability and image construction details: in practice, prefer Chainguard-documented multi-stage builds (install in `python:latest-dev`, run in minimal runtime) or otherwise verify the pinned digest includes required package tooling.

## Pre-mortem
- Failure mode: The chosen Chainguard base variant lacks package tooling needed for `python -m pip install`.
  Reflection in note: Require a multi-stage `latest-dev` install stage (or verified tooling presence in pinned digest) before adopting the exact snippet.
- Failure mode: Team assumes lockfile audit parity via `--locked` with `uv.lock` and gets false confidence.
  Reflection in note: Document that pip-audit lockfile mode does not currently consume `uv.lock`; use project-path or environment-mode audits instead.
- Failure mode: Local developers cannot run the container due missing Docker/Podman.
  Reflection in note: Treat containerized audit as conditional on runtime availability; retain non-container fallback in CI/dev where needed.
- Failure mode: Containerized mode is mistaken for a full defense against malicious dependency behavior.
  Reflection in note: Preserve pip-audit security-model caveat that dependency resolution/audit has install-equivalent trust assumptions.

## Assumptions
- [confident] Digest-pinned, nonroot Chainguard images are compatible with this repo's existing supply-chain hardening direction.
- [likely] Disposable container execution reduces local-environment contamination risk for ad hoc audits.
- [uncertain] The exact provided image digest includes the package tooling required by the single-stage Dockerfile as written.

## Changelog
- 2026-04-25: Created decision record evaluating viability of containerized pip-audit with Chainguard Python.
