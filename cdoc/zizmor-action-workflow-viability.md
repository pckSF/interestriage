---
type: decision
tags: [security, github-actions, zizmor, code-scanning, supply-chain]
created: 2026-04-25
updated: 2026-04-25
status: active
related: [supply-chain-hardening-pinning-cooldown.md, .github/workflows/ci.yml, _index.md]
---
# Viability Of A Dedicated zizmor GitHub Action Workflow

## Context
The repository already enforces workflow hardening through pre-commit (`zizmor` hook) and immutable SHA pinning, but it does not currently run `zizmor-action` as a dedicated GitHub workflow that publishes SARIF findings into GitHub code scanning.

The proposed workflow is:
- Triggered on `push` to `main` and all `pull_request` events.
- Uses `ubuntu-latest`.
- Grants `security-events: write`, `contents: read`, and `actions: read` for the job.
- Runs `actions/checkout` and `zizmorcore/zizmor-action` pinned to immutable SHAs.

## Research Findings
- Current CI (`.github/workflows/ci.yml`) runs tests, linting, npm audit, pip-audit, and build checks, but has no dedicated GitHub code-scanning upload step for workflow analysis.
- The repository already uses `zizmor` in pre-commit, which catches issues before push, but this path does not provide SARIF-backed historical triage in GitHub Security.
- Upstream `zizmor-action` recommends Advanced Security mode by default (`advanced-security: true`), which uploads SARIF and requires `security-events: write`.
- Upstream docs indicate `contents: read` and `actions: read` are only required for private/internal repositories when using Advanced Security mode.
- `zizmor-action` is a container action and expects a container runtime; `ubuntu-latest` satisfies this on GitHub-hosted runners.
- In Advanced Security mode, `zizmor-action` does not fail the job solely for findings; merge blocking is typically enforced via code-scanning rulesets.
- The sample workflow pattern and SHA pinning are aligned with upstream examples for `zizmor-action@b1d7e1fb5de872772f31590499237e7cce841e8e`.
- Existing cdoc decision `supply-chain-hardening-pinning-cooldown.md` explicitly endorsed workflow auditing with `zizmor`; adding a dedicated workflow is additive and does not conflict.

## Options Considered
#### Option 1: Keep only pre-commit zizmor (no dedicated workflow)
- Description: Continue relying on local/pre-commit `zizmor` checks and existing CI gates without a standalone `zizmor-action` workflow.
- Pros: Minimal operational complexity; no additional workflow runtime/cost.
- Cons: No SARIF upload to code scanning; weaker centralized triage and historical visibility; dependent on developer hook compliance.
- Ruled out: It leaves a gap between local checks and repository-level security observability.

#### Option 2: Add dedicated `zizmor-action` workflow in Advanced Security mode (chosen)
- Description: Add a standalone workflow closely matching the proposed YAML, with immutable SHA pinning and job-level least-privilege permissions.
- Pros: Centralized and stateful code-scanning visibility; independent CI-time enforcement path; aligns with upstream recommended usage.
- Cons: Requires code-scanning availability (public repo or paid feature for private/internal repos); findings do not automatically fail CI unless rulesets are configured.

#### Option 3: Run zizmor as plain CLI in existing CI without SARIF upload
- Description: Install/run `zizmor` in CI logs only, skipping Advanced Security integration.
- Pros: Simpler permission model; easier to make findings fail the job directly.
- Cons: Loses stateful GitHub Security triage and code-scanning UX; duplicates behavior already partially covered by pre-commit.
- Ruled out: Lower long-term operational value than SARIF-backed analysis.

## Decision
Choose Option 2: add a dedicated `zizmor-action` workflow in Advanced Security mode.

This option preserves the strongest security visibility tradeoff: it keeps immutable pinning and least-privilege permissions while adding code-scanning integration that Option 1 lacks. Compared to Option 3, it retains GitHub Security tab triage and longitudinal tracking rather than ephemeral log-only findings.

## Pre-mortem
- Failure mode: The repository lacks Advanced Security entitlement for private/internal usage, causing failed or ineffective SARIF uploads.
  Reflection in note: Scope requires validating repository visibility/licensing before rollout; if unavailable, switch to `advanced-security: false` as fallback.
- Failure mode: Teams expect PR checks to hard-fail automatically on findings, but Advanced Security mode does not fail on findings by default.
  Reflection in note: Merge protection must be handled with code-scanning rulesets, not assumed from action exit behavior.
- Failure mode: Permission scope is broader than needed for public repositories.
  Reflection in note: `contents: read` and `actions: read` should be retained only where repository type requires them.
- Failure mode: Self-hosted or non-Linux runners are used later and lack Docker runtime.
  Reflection in note: Keep `runs-on: ubuntu-latest` (or equivalent Docker-capable Linux runners) for this job.

## Assumptions
- [confident] The proposed workflow syntax and SHA pins are valid for current `zizmor-action` guidance.
- [likely] The repository can benefit from SARIF-based workflow finding triage beyond pre-commit-only feedback.
- [uncertain] Current repository plan includes code-scanning entitlement if private/internal; this must be verified at rollout time.

## Changelog
- 2026-04-25: Created decision record evaluating viability of a dedicated `zizmor-action` workflow.
