# Interestriage — Engineering Specification

> **Document purpose.** This specification is written to be executed by coding agents (and human engineers reviewing their work). It defines the product, the architecture, the data model, and a sequenced implementation plan with stage-level acceptance criteria. Security is treated as a first-class concern at every stage, not as an appendix.

---

## 0. How To Use This Specification

### 0.1 Audience

This document targets:

- AI coding agents executing the project stage by stage.
- Human engineers reviewing or auditing agent work.
- Maintainers extending the system after MVP.

### 0.2 The Deviation Clause

If, at any point during implementation, an agent identifies a different approach that is materially better than what this specification prescribes, the agent **may deviate**, provided that:

1. The deviation is documented in the relevant stage's `DECISIONS.md` (or equivalent ADR file) with:
   - the original prescription,
   - the proposed alternative,
   - a concrete justification (correctness, security, cost, maintainability, latency, simplicity),
   - a list of any new risks introduced by the change.
2. The deviation does **not weaken any explicit security control** (Section 14) without an equivalent or stronger replacement, also documented.
3. The acceptance criteria of the stage are still met (or replaced by criteria that are at least as strict).
4. Public interfaces between stages are preserved, or the change to the interface is propagated to all dependent stages in the same change set.

This clause exists to prevent the spec from forcing inferior decisions, while still keeping changes auditable. **Silent deviations are not acceptable.** A change that is not documented is treated as a defect.

### 0.3 How To Read The Stages

Stages in Section 12 are ordered by dependency. Each stage contains:

- **Goal** — what is being built.
- **Deliverables** — concrete artifacts produced.
- **Acceptance criteria** — testable conditions for "done".
- **Security gates** — security controls that must be in place before the stage is considered complete.
- **Out of scope for this stage** — explicit deferral list, to prevent scope creep.

A stage is not complete until all acceptance criteria **and** all security gates pass.

---

## 1. Product Concept

Interestriage is a personal content triage system. Throughout the day a user encounters articles, PDFs, notes, or links that look interesting but cannot be consumed immediately. Interestriage offers a low-friction capture mechanism — a browser extension and a drag-and-drop intake — that pushes these items into a per-day queue.

At a user-defined time (default: midnight local), Interestriage processes the day's queue. Each source is fetched or parsed, summarized by a language model, and the summaries are synthesized into a coherent written daily report with sections, key points, and source references. The report is then rendered into a podcast-style audio briefing (single-host or two-host conversational) using a Python text-to-speech pipeline.

The next morning, the user can listen to a 5–20 minute audio briefing of yesterday's collected interests and decide which sources warrant deeper engagement. The original sources are preserved so the user can return to them with full context.

The system favors **low-friction capture, batch nightly synthesis, and dual text+audio output**, shifting consumption from reactive browsing to structured digestion.

### 1.1 Deployment Model

**Interestriage is server-first by default**, with full support for a local-only deployment. This decision shapes the architecture and the security posture, so it is documented up front.

**Default deployment target.** A single small server (a VPS, a home server, or any always-on machine) running the backend, the worker, the scheduler, and the storage layer. The browser extension and any future client (web dashboard, mobile app) communicate with this server over HTTPS. The owner of the deployment is also the user of the service; this is *self-hosted single-user*, not multi-tenant SaaS.

**Why server-first.**

- *Multi-device access by construction.* The extension already speaks HTTP to the backend; a phone, a work laptop, or a tablet are simply additional clients. With local-only, multi-device requires inventing a sync layer.
- *Reliable nightly batch.* The scheduler needs the host to be awake at the configured time. Laptops sleep; servers don't.
- *Output reachability.* The morning audio briefing should be playable from a phone without the laptop being open. A server-hosted artifact behind a signed URL is the simplest path.
- *No code-path divergence.* The same backend code runs in both modes. Local-only is just a configuration where the server happens to be `localhost` and the firewall is the local network stack.

**Local-only mode remains a first-class option.** Users who want the strongest privacy posture, or who only ever use one device, can run the same software bound to `localhost` (or to a LAN interface) and skip the public-exposure controls. The spec must not produce a system that *requires* internet exposure or external providers to function. Local-only is selected by configuration; no code changes.

**Implications cascading through the spec.**

- *Authentication and TLS become non-negotiable in the default deployment* (see Stage 2). They are already strongly recommended; in a server-exposed setting they are baseline.
- *Per-device credentials.* The auth model must support multiple enrolled clients per user (laptop extension + phone app + work browser), each with its own revocable token, so the user can revoke a stolen device without invalidating the others.
- *Rate-limiting and abuse handling matter more.* A `localhost`-bound service has an implicit firewall; a publicly reachable one is probed continuously.
- *Privacy boundary shifts subtly.* Source content lives on the server, not on the capture device. Disclosure language in the UI must reflect this: the user is trusting the server operator (themselves, in the self-hosted case) in addition to any external LLM/TTS providers they configure.
- *Operational surface appears.* TLS certificate management, backups, updates, and basic intrusion logging become real concerns. The Stage 11 runbook must cover them.

**What this is not.** This is not a commitment to multi-tenant SaaS. The architecture allows multi-user as a future path — per-user namespacing is enforced at the storage layer from Stage 1 — but multi-tenancy hardening, billing, account lifecycle, and abuse handling are explicitly outside MVP and are noted in Section 16 (Outlook).

### 1.2 Build and Deployment Topology

**Repo structure is not deployment structure.** Interestriage is developed as a single monorepo (one git history, multiple subprojects under one root) but it deploys as several independent artifacts, each going to its own destination. This is the standard pattern for projects of this shape; it is documented here so the agent does not conflate "everything is in one repo" with "everything runs as one binary."

**Artifacts produced from the monorepo:**

| Artifact | Source directory | Built by | Deployed to |
|---|---|---|---|
| Backend image (FastAPI + worker + scheduler) | `backend/`, `worker/` | CI / `docker build` | Server host (or `localhost` in local-only mode) |
| Dashboard static bundle | `web/` | CI / framework build | Served by the backend container, the reverse proxy, or a CDN |
| Browser extension package (`.zip` / `.crx`) | `extension/` | CI / `web-ext build` | Chrome Web Store, then users' browsers |
| Mobile app binary (post-MVP, see §16.1) | `mobile/` | Platform-specific CI | Apple App Store / Google Play, then users' devices |

The backend and worker may run as one container or two; the spec does not constrain this. They share a codebase and dependency set, so packaging them as one image with two entry points (`api` and `worker`) is the default. Splitting them is a permitted deviation if a clear reason emerges (e.g., the worker needs GPU and the API does not).

**The flow:**

```
                    ┌──────────────────────────────────┐
                    │         Monorepo (git)           │
                    │   developer machines + CI        │
                    └────────────────┬─────────────────┘
                                     │  CI build step
                  ┌──────────────────┼──────────────────┬─────────────┐
                  │                  │                  │             │
                  ▼                  ▼                  ▼             ▼
        ┌──────────────────┐ ┌──────────────┐ ┌────────────────┐ ┌─────────┐
        │ Backend image    │ │ Dashboard    │ │ extension.zip  │ │ Mobile  │
        │ (api + worker)   │ │ static files │ │                │ │ binary  │
        └────────┬─────────┘ └──────┬───────┘ └────────┬───────┘ └────┬────┘
                 │                  │                  │              │
                 ▼                  ▼                  ▼              ▼
         Server / VPS         Server, proxy,     Chrome Web         App
         (or localhost)       or CDN             Store              stores
```

**You do not "split the repo" before deploying.** The monorepo stays whole; the CI pipeline is what produces the separate artifacts. Each artifact only contains what its destination needs. The server never sees the extension's source code; the Chrome Web Store never sees the backend.

**For self-hosted personal deployment:** the simplest production setup is a `docker-compose.yml` under `infra/production/` that runs the backend image behind a Caddy or nginx reverse proxy with TLS via Let's Encrypt. The dashboard's static files can be served by either the backend or the proxy. The extension is built and uploaded to the Chrome Web Store separately (or loaded unpacked during personal use). The mobile app, when it exists, is distributed through app stores and is fully decoupled from the server's release cycle.

**Same images run in dev and prod.** A core design rule: the Docker images built for production are the same images run during local development. Local dev differs only in configuration (bind addresses, TLS off, smaller resource limits, faked clock, stub model adapters — see §1.3). This eliminates "works on my machine" by construction.

### 1.3 Local Development Environment

**Principle: the local stack faithfully replicates production.** Running the system on a developer's laptop must use the same container images, the same network shape, and the same configuration loader as a real server deployment. Differences between dev and prod are *only* configuration, never separate code paths. This makes per-stage testing (Section 12) mechanically reliable: an acceptance test that passes locally is meaningful evidence that the same scenario passes on the server.

**The local stack.** A `docker-compose.yml` at `infra/dev/` (or the repo root) brings up:

- `backend` — the FastAPI service. Bound to the internal Docker network, not directly to the host.
- `worker` — the batch pipeline process. Same image as `backend` with a different entry point if combined; separate container if split.
- `db` — Postgres (optional in MVP — SQLite-on-volume is the default; Postgres becomes useful when validating the post-MVP migration path).
- `proxy` — Caddy or nginx. The only container with a host port mapped, standing in for the production reverse proxy. Serves the dashboard's static bundle and proxies API requests.
- `evil-server` — a deliberately hostile HTTP server used by Stage 3 SSRF tests (see below). Not started in normal `docker compose up`; brought up by the test harness.
- `parser-sandbox` — the sandboxed PDF/HTML parser worker (Stage 3). Resource-capped to validate that sandboxing actually holds in development, not only in production.

The browser extension during development points at `https://localhost` (with a self-signed certificate trusted by the developer's browser) or at `http://localhost:8080` if TLS is disabled for that session. The same extension build, with a different configured backend URL, talks to a real server in production.

**The `evil-server` container.** A small HTTP server purpose-built to test Stage 3's SSRF and parser defenses. It serves, among other things:

- Redirects to private IPs (`127.0.0.1`, `10.0.0.1`, `169.254.169.254`).
- DNS-rebinding scenarios (a hostname that resolves to a public IP on first lookup and a private IP on second).
- Slow-loris responses (one byte per second to test fetch timeouts).
- Oversized payloads (multi-gigabyte responses to test size caps).
- Content-type mismatches (claims `application/json`, returns HTML).
- PDF "bombs" (highly compressed, deeply nested objects designed to exhaust parser memory).
- Markdown files containing inline HTML/JS (to verify the markdown parser treats them as text).

Stage 3's acceptance tests issue requests **through the backend container** to URLs hosted by `evil-server`, asserting that each attack is refused. This is a real network test, not a mock — the only way to credibly verify the SSRF defenses.

**The TTS stub adapter.** Stage 8's audio generation calls a TTS engine that may be slow, expensive, or both. For day-to-day iteration the spec mandates a `TTSAdapter` implementation called `StubTTS` that returns a short silent MP3 of a deterministic length proportional to the input text. The dev `docker-compose.yml` configures the worker to use `StubTTS` by default. Real TTS adapters (Coqui, Kokoro, ElevenLabs, etc.) are exercised by a separate `make test-audio` target (or equivalent) that the developer runs deliberately. This keeps the inner loop fast while still allowing real audio tests on demand.

**Optional: `mitmproxy` for outbound inspection.** A `mitmproxy` container can be inserted between the worker and any external LLM/TTS provider during testing to verify that the credential-redaction sweeps in Stages 5–8 are actually stripping what they're supposed to before sending prompts off-host. Useful for security tests; not part of the default dev stack.

**Caveats the agent should know:**

- Docker on macOS is slower than on Linux due to the file-sharing layer. Acceptable for development; throughput benchmarks should run on a Linux host.
- The first build of an image is slow (dependency installs); subsequent builds are fast due to layer caching.
- Local TTS engines with heavy models may run better on the host than in a container, especially without GPU passthrough. The `TTSAdapter` interface lets the agent swap in a host-process adapter without touching the rest of the worker.
- `docker compose down -v` wipes all dev state including the database volume; this is a feature, not a bug, but is worth knowing before doing it accidentally on a long-lived dev instance.

**Out of scope for the local stack.** Production-grade orchestration (Kubernetes, Nomad), multi-host networking, blue-green deployment. Self-hosted single-user deployment via `docker-compose` is sufficient for MVP and well into post-MVP.

---

## 2. Goals and Non-Goals

### 2.1 Product goals

- Capture a source in under five seconds from any tab or local file.
- Process the daily queue automatically at a configured time.
- Produce a written report that stands on its own without the audio.
- Produce an audio briefing of 5–20 minutes by default.
- Keep marginal cost low enough to run daily.
- Preserve original sources for later deep reading.
- Allow the user to inspect, edit, or remove queued items before processing.
- Support multi-device access: the same queue, reports, and episodes are reachable from any of the user's enrolled clients (laptop extension, phone, etc.) through one backend.

### 2.2 Non-goals (MVP)

- Real-time collaboration or sharing.
- Replacing a note-taking system.
- Acting as a general knowledge base or search index.
- Fact-checking or verifying source claims.
- Multi-tenant SaaS hosting (single-user / self-hosted is the MVP target).

---

## 3. Landscape and Reuse

The deep-research review (see `deep-research-report.md`) confirms that no off-the-shelf product covers this exact workflow end-to-end, but each subsystem has prior art that should be evaluated before writing code from scratch:

- **Article-to-podcast generation:** `ArticleCast`, `Podcastfy.ai`, `TwoCast`, `AutoPod` (n8n + Raindrop), NVIDIA's open `PDF-to-Podcast` blueprint.
- **TTS engines:** ElevenLabs, Coqui TTS, Google WaveNet, Amazon Polly, open-source Kokoro-82M.
- **LLM providers (current pricing reference):** Anthropic Claude (Sonnet ~ $3 / $15 per 1M input/output tokens, Haiku ~ $1 / $5), OpenAI GPT-class models (~$2.50 / $15 per 1M tokens). Local models (Llama, Mistral variants) are an option for the per-source pass to control cost.
- **NotebookLM:** Generates audio overviews but **does not expose its Audio Overview feature via public API**. The Vertex AI Enterprise tier exposes some notebook management endpoints but not audio generation. NotebookLM is therefore out of scope as an automated dependency.

**Implementation guidance:** before writing a custom subsystem, the agent should evaluate the relevant existing project. If reusing it (as a library, a forked component, or a Docker service) materially reduces effort or risk, that decision should be recorded under the deviation clause (0.2). Reuse must still satisfy the security gates of the relevant stage — an external library is not an excuse to skip SSRF protection, sandboxing, or prompt-injection handling.

---

## 4. User Experience Summary

### 4.1 Daily flow

1. During the day the user encounters something interesting (article, PDF, link, note).
2. They click the browser extension button **or** drop a file into the local intake UI **or** paste a URL.
3. The item lands in today's queue with status `captured`.
4. The user can optionally tag, annotate, mark-important, reorder, or remove queued items.
5. At the configured trigger time the system processes the queue:
   normalize → summarize per-source → synthesize daily report → script → audio.
6. Outputs are saved to a stable per-day location.
7. The next morning the user listens to the briefing and can open the written report and any source for deeper reading.

### 4.2 Key UX principles

- Capture must never block the user on network or processing.
- The queue must be visible and editable before processing runs.
- Processing must be idempotent for a given calendar day.
- Outputs from previous days must remain reachable in a stable archive.

---

## 5. Functional Requirements

### 5.1 Source capture

Supported in MVP: browser extension (one-click), URL paste, drag-and-drop of `.txt`, `.md`, `.pdf`.
Deferred: screenshots, RSS, email-forward, mobile share-sheet.

### 5.2 Queue management

The user can: list, view, remove, reorder, mark-important, tag, annotate, and manually trigger early processing of the day's queue.

### 5.3 Per-source summarization

Each source produces:

- a concise summary,
- a short list of key points,
- optional topic labels,
- provenance metadata (which model, when, on what extracted text hash).

### 5.4 Daily report

A single Markdown (canonical) and HTML (rendered) report containing:

- title and date,
- executive overview,
- one section per source or topic cluster,
- bullets of key points,
- source links / file references with stable identifiers,
- optional "why this matters" line per section.

### 5.5 Podcast script and audio

A script transformed from the report, with two output modes:

- **single-host briefing** (default for short days),
- **two-host dialogue** (default for richer days, configurable).

Audio output: 5–20 minutes by default, MP3 (or another well-supported format), with intro and outro segments and clear transitions between sources.

### 5.6 Scheduling

Configurable daily trigger (default midnight local), idempotent per calendar day, retries on transient failure, archives the queue after success, leaves the queue intact on failure for re-run.

### 5.7 Delivery

MVP: local folder + downloadable from the web dashboard.
Optional later: email, podcast feed (RSS), cloud-storage drop, mobile push.

---

## 6. System Architecture

### 6.1 Component overview

The architecture is the same in local-only and server-hosted deployments; only the network exposure of the backend differs. Multiple clients (browser extension, web dashboard, future mobile/desktop app) talk to one backend.

```
┌────────────────┐    ┌────────────────────────────────────────────┐
│ Browser ext.   │───▶│                                            │
└────────────────┘    │            Backend API                     │
┌────────────────┐    │  (auth, capture, queue, normalization,     │
│ Web dashboard  │───▶│   per-device token issuance & revocation)  │
└────────────────┘    │                                            │
┌────────────────┐    │                                            │
│ Mobile app     │───▶│                                            │
│ (future, §16)  │    │                                            │
└────────────────┘    └─────────────────┬──────────────────────────┘
                                        │
                                        ▼
                      ┌──────────────────────────────────────────┐
                      │          Storage layer                   │
                      │  metadata DB + content blob store        │
                      └─────────────────┬────────────────────────┘
                                        │
                                        ▼
                      ┌──────────────────────────────────────────┐
                      │          Batch worker                    │
                      │ normalize → summarize → synthesize →     │
                      │ script → TTS → publish                   │
                      └──────────────────────────────────────────┘
```

In server-hosted deployments, the backend sits behind a TLS-terminating reverse proxy (Caddy or nginx are sensible defaults). In local-only deployments, the same backend binds to `localhost` and the proxy is optional.

### 6.2 Components

- **Browser extension** — captures current URL, page title, optional selected text. Calls the backend over HTTPS with a per-device token. Holds no secrets beyond the bound token.
- **Web dashboard** — queue management, calendar, report viewer, episode player, device-token management.
- **Mobile app (future, see §16)** — capture via OS share-sheet, queue management, listening. Treated as just another API client; no backend changes are required to add it.
- **Backend API** — authenticates requests (per-device tokens, revocable individually), validates inputs, stores queue items, exposes queue management, dashboard, and manual-trigger endpoints. In server-hosted mode, designed to sit behind a TLS reverse proxy.
- **Storage layer** — metadata database (SQLite for MVP, Postgres later), content blob store (filesystem for MVP, object storage later). Per-user namespacing enforced at the repository layer.
- **Batch worker** — runs the daily pipeline, isolated from the API process, with its own resource limits.
- **Model adapters** — pluggable interfaces for LLMs (per-source summarizer, synthesizer, script writer) and TTS engines. The adapter contract is fixed; the concrete provider is configurable.
- **Scheduler** — triggers the batch worker daily and on manual request, holding a per-day lock.

### 6.3 Trust boundaries

| Boundary | From → To | Notes |
|---|---|---|
| B1 | Extension → API | Authenticated, HTTPS, narrow surface. |
| B2 | API → External web | SSRF-hardened fetcher only. |
| B3 | API/Worker → File parsers | Sandboxed parser process. |
| B4 | Worker → LLM/TTS providers | Outbound only, via adapter, with redaction. |
| B5 | Worker → Storage | Per-user namespace, integrity hashing. |
| B6 | Scheduler → Worker | Locked, authenticated trigger. |

Each boundary is referenced from the security controls in Section 14.

---

## 7. Data Model

All entities below are persisted in the metadata DB. Large blobs (raw HTML, PDF bytes, extracted text, audio files) are persisted in the blob store and referenced by an opaque identifier and a SHA-256 content hash.

### 7.1 `Source`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `user_id` | UUID | Owner. |
| `type` | enum | `url`, `pdf`, `markdown`, `text`. |
| `title` | string | Best-effort, populated post-normalize. |
| `original_reference` | string | URL or original filename. |
| `captured_at` | timestamp | UTC. |
| `capture_day` | date | Local-day bucket for batching. |
| `tags` | string[] | User-supplied. |
| `note` | string | User-supplied. |
| `status` | enum | `captured`, `normalized`, `summarized`, `included`, `failed`, `archived`, `removed`. |
| `raw_content_ref` | string | Blob handle for raw bytes. |
| `extracted_content_ref` | string | Blob handle for cleaned text. |
| `extracted_content_hash` | string | SHA-256, used to detect duplicates and tampering. |
| `sensitivity` | enum | `default`, `private`. `private` may suppress audio inclusion. |

### 7.2 `SummaryItem`

| Field | Type |
|---|---|
| `id`, `source_id` | UUID |
| `summary_text` | string |
| `key_points` | string[] |
| `topics` | string[] |
| `model_used` | string |
| `prompt_version` | string |
| `input_hash` | string (SHA-256 of the exact input sent to the model) |
| `created_at` | timestamp |

### 7.3 `DailyReport`

| Field | Type |
|---|---|
| `report_date` | date |
| `user_id` | UUID |
| `title` | string |
| `overview` | string |
| `sections` | structured (ordered list of `{heading, summary, key_points, source_refs, why_it_matters}`) |
| `references` | source_id[] |
| `markdown_ref`, `html_ref` | blob handles |
| `created_at` | timestamp |
| `report_hash` | string (SHA-256 of the canonical Markdown) |

### 7.4 `PodcastEpisode`

| Field | Type |
|---|---|
| `report_date`, `user_id` | composite key |
| `script_ref` | blob handle |
| `audio_ref` | blob handle |
| `audio_format` | string |
| `duration_seconds` | int |
| `voice_configuration` | structured |
| `script_hash`, `audio_hash` | SHA-256 |
| `created_at` | timestamp |

### 7.5 `JobRun`

A durable audit record for every batch invocation: trigger source (cron/manual), start/end times, per-stage outcomes, error traces (with secrets redacted), and the lock identifier that prevented concurrent runs.

### 7.6 `DeviceToken`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `user_id` | UUID | Owner. |
| `label` | string | User-supplied (e.g. "Home Chrome", "Pixel phone"). |
| `token_hash` | string | Hash of the bearer token; the raw token is shown to the user once at issuance. |
| `created_at` | timestamp | |
| `last_used_at` | timestamp | Updated on each successful auth. |
| `expires_at` | timestamp | Tokens have a finite lifetime; renewable. |
| `revoked_at` | timestamp | Null if active. |
| `scopes` | string[] | E.g., `capture`, `manage`, `listen`. Reserved for future fine-grained access. |

Per-device tokens let the user enroll multiple clients and revoke any single one (e.g., a lost phone) without disrupting the others.

---

## 8. Processing Pipeline

The worker processes a calendar-day queue through fixed stages, persisting state at every step. A failure in one stage does not consume sources from the queue; the day can be re-run.

| Step | Input | Output | Failure behavior |
|---|---|---|---|
| **A. Capture** | User action | `Source` row, raw blob | Reject input, return error to client. |
| **B. Normalize** | `Source` raw | extracted text + metadata | Mark source `failed` with reason; continue with remaining sources. |
| **C. Per-source summary** | extracted text | `SummaryItem` | Mark source `failed`; daily report still produced from successful items. |
| **D. Daily synthesis** | all `SummaryItem`s of the day | `DailyReport` | Retry once; on failure, abort day and surface error. |
| **E. Script generation** | `DailyReport` | script blob | Retry once; on failure, leave report intact and abort audio. |
| **F. Audio generation** | script | `PodcastEpisode` audio | Retry once; on failure, surface error, keep script. |
| **G. Delivery** | report + audio | published artifacts | Retry; surface error; do not lose artifacts. |

Re-running a calendar day is allowed and idempotent: the same input set must produce the same canonical Markdown and the same audio file (modulo TTS non-determinism, which is recorded but does not cause divergent state).

---

## 9. Model Strategy

### 9.1 Layered approach

- **Per-source summary** uses a cheap model (small local model **or** a low-cost hosted tier such as Claude Haiku). Per-article work is the volume bulk and benefits most from cost control.
- **Daily synthesis** uses a stronger model (e.g., Claude Sonnet or GPT-class) since coherence and structure matter most here.
- **Script generation** uses the synthesis tier or one step down, with a prompt tuned for spoken delivery.
- **TTS** uses a configurable adapter (ElevenLabs / Coqui / Kokoro / Polly / WaveNet). MVP can ship with one adapter; the contract must allow swap.

The model adapter is a stable interface; the concrete model is configuration. This is what makes hybrid local-plus-cloud feasible without rewrites.

### 9.2 Cost controls

- Truncate or chunk extracted text before per-source summarization (target a small bounded token budget per source).
- Cache summaries by `extracted_content_hash`: if the same content is captured twice, reuse the prior summary.
- Skip synthesis if the day has zero successful summaries; emit an empty-day notice instead.

---

## 10. Audio Format Requirements

- Default duration: 5–20 minutes; strict cap: 30 minutes (DoS guard).
- Format: MP3 (mandatory), with optional WAV/Opus.
- Clear section boundaries; sources named in spoken form.
- Mobile-playback intelligible; mono is acceptable for MVP.
- Optional later: chapter markers, intro jingle, custom voices, per-host voice profiles.

---

## 11. MVP Scope

**In MVP:** browser-extension capture (Chromium first), URL paste, file drop for `.txt`/`.md`/`.pdf`, queue management UI, daily summarization job, Markdown + HTML report, podcast script (both single-host and two-host), Python TTS pipeline producing MP3, local-folder delivery, manual trigger, baseline auth.

**Excluded from MVP:** mobile native app, multi-user collaboration, NotebookLM integration, semantic search across history, source fact-checking, social sharing, public podcast feed.

---

## 12. Implementation Stages

The following stages are dependency-ordered. Each stage produces a runnable, testable increment. **A stage is complete only when its acceptance criteria pass and its security gates are satisfied.** Earlier stages do not depend on later ones, so partial deployments at the end of any stage are valid system states.

> **General rule for every stage:** write tests before declaring done. Both unit tests for individual modules and a stage-level integration test that exercises the new capability end-to-end.

---

### Stage 0 — Project foundation

**Goal.** Set up the repository, dependency management, baseline tooling, deployment scaffolding, and security plumbing so subsequent stages do not have to revisit it.

**Deliverables.**
- **Monorepo** with these directories: `extension/`, `backend/`, `worker/`, `web/`, `mobile/` (placeholder for §16.1, may contain only a README at this stage), `shared/` (cross-component schemas and types), `infra/`, `prompts/`, `docs/`, `tests/`. The monorepo maps to multiple deployment artifacts as described in §1.2; splitting into multiple repos is permitted under the deviation clause (0.2) only with concrete justification.
- Language baselines: TypeScript for extension and dashboard, Python for backend and worker. Lockfiles (`package-lock.json` / `pnpm-lock.yaml`, `uv.lock` or `poetry.lock`).
- Workspace configuration (e.g., `pnpm` workspaces or `npm` workspaces for the JS side; `uv` workspaces or a top-level `pyproject.toml` referencing `backend/` and `worker/` for the Python side). Subprojects build independently but share lockfiles where the ecosystem supports it.
- `DECISIONS.md` initialized for the deviation clause (0.2).
- `.env.example` documenting every required variable; **no real secrets in the repo**.
- Pre-commit hooks: linter, formatter, `detect-secrets` (or equivalent) scanner.
- CI pipeline running: lint, type-check, tests, dependency vulnerability scan (e.g., `pip-audit`, `npm audit --audit-level=high`), SBOM generation. CI builds each artifact (backend image, dashboard bundle, extension package) independently but from the same commit.
- README covering local-dev bring-up; `DEPLOYMENT.md` covering both local-only and server-hosted modes; `DEVELOPMENT.md` covering the local Docker workflow per §1.3.
- **Deployment scaffolding under `infra/`** organized as:
  - `infra/dev/docker-compose.yml` — the local development stack per §1.3 (`backend`, `worker`, `db`, `proxy`, `parser-sandbox`).
  - `infra/dev/evil-server/` — the hostile HTTP server container used by Stage 3 SSRF tests (image definition + canned attack scenarios).
  - `infra/production/docker-compose.yml` — production deployment template (same images, production configuration, TLS via Caddy or nginx + Let's Encrypt).
  - `infra/Dockerfile.backend` — the shared image for `backend` and `worker` entry points.
  - `infra/Dockerfile.dashboard` — the dashboard build/serve image (or a static-bundle output if served by the proxy).
- Configuration loader that reads a single `INTERESTRIAGE_MODE` setting (`local` or `server`) and applies the right defaults for bind address, TLS, rate limits, CORS, and external-fetch behavior. The agent must not introduce divergent code paths for the two modes — only configuration and middleware composition differ.
- A `StubTTS` adapter (Stage 8 contract) that returns a deterministic short silent MP3. Wired as the default TTS in the dev `docker-compose.yml`. Real TTS adapters are tested separately, not in the inner loop.
- A `Makefile` (or task runner equivalent: `just`, `task`, etc.) exposing at minimum: `make dev` (bring up the dev stack), `make test` (run all unit + integration tests), `make test-ssrf` (run Stage 3 SSRF tests against `evil-server`), `make test-audio` (run real-TTS tests), `make build` (produce all deployment artifacts), `make down` (tear down dev stack).

**Acceptance criteria.**
- A fresh clone bootstraps with documented commands and runs `make test` green.
- `make dev` brings up the local Docker stack and the dashboard is reachable through the local proxy with a self-signed cert (or plain HTTP on `localhost`, per the dev configuration choice recorded in `DECISIONS.md`).
- `make build` produces three artifacts: a backend Docker image, a dashboard static bundle, an extension `.zip`. None of the three contains source from the others.
- CI fails the build on a known-vulnerable dependency.
- Pre-commit blocks a commit that introduces a fake secret string.
- The dev stack and the production stack are launched from the **same** image tags; only the compose file and environment differ. A test asserts the image SHAs match.

**Security gates.**
- Secret-scanning pre-commit and CI step both active.
- Dependency vulnerability scanning active and blocking on `high`+.
- Lockfiles present for every language ecosystem.
- `.gitignore` covers `.env`, blob store paths, audio outputs, generated certificates, `infra/dev/data/`.
- The `evil-server` container is **never** started by the default dev stack and **never** exposed on a host port; it is only accessible from within the test Docker network when explicitly invoked by the test harness. This prevents a developer accidentally running it as a real service.

**Out of scope.** Production-grade orchestration (Kubernetes, Nomad), blue-green deployment, multi-host scaling.

---

### Stage 1 — Storage and data model

**Goal.** Stand up the persistence layer with the entities from Section 7.

**Deliverables.**
- Schema migrations (SQLite for dev) for `Source`, `SummaryItem`, `DailyReport`, `PodcastEpisode`, `JobRun`, `User`.
- Blob store abstraction with a local-filesystem implementation behind a stable interface (`put(bytes) -> handle`, `get(handle) -> bytes`, `delete(handle)`, `hash(handle) -> sha256`).
- Repository / DAO layer with typed methods.
- Per-user namespacing enforced at the repository layer (no cross-user reads possible from the API path).
- Database file and blob root paths configurable; restrictive default permissions (0600 for DB file, 0700 for blob root).

**Acceptance criteria.**
- Round-trip tests for every entity (create, read, update, delete).
- A test that proves user A cannot retrieve user B's records via the repository API.
- Blob handles cannot be guessed (random IDs of sufficient entropy).

**Security gates.**
- Encryption-at-rest decision recorded in `DECISIONS.md`. MVP minimum: filesystem-level permissions and an explicit threat-model note. If full at-rest encryption is deferred, the deferral is documented with rationale and a follow-up issue.
- Per-user authorization enforced at the repository layer, not just at the API layer (defense in depth).
- No PII or secrets in log output from the storage layer.

**Out of scope.** Multi-tenant scaling, sharded storage, replication.

---

### Stage 2 — Authenticated backend API and queue

**Goal.** Expose HTTP endpoints for capturing sources, listing the queue, mutating queue items, triggering processing, and managing per-device tokens. The API is designed to be reachable from multiple clients over the public internet (server-hosted mode) without code changes from the local-only mode.

**Deliverables.**
- Endpoints (versioned under `/api/v1`):
  - `POST /sources` — submit a URL or file (multipart).
  - `GET /sources?day=YYYY-MM-DD` — list queue.
  - `PATCH /sources/{id}` — tags, note, importance, sensitivity, reorder hint.
  - `DELETE /sources/{id}` — remove from queue.
  - `POST /runs` — manual trigger for a given day.
  - `GET /runs/{id}` — run status.
  - `GET /reports/{date}` and `GET /episodes/{date}` — read outputs (post Stage 6/8).
  - `POST /devices` — issue a new device token (returns the raw token *once*).
  - `GET /devices` — list enrolled devices for the user.
  - `DELETE /devices/{id}` — revoke a device token.
- Authentication: per-device bearer tokens, hashed at rest (`token_hash` in §7.6), with finite lifetime, refreshable, and individually revocable. Token enrolment requires a primary credential (password or passkey — choice recorded in `DECISIONS.md`).
- Strict input validation on every endpoint (Pydantic, zod, or equivalent).
- Rate limiting on capture, run-trigger, and device-enrolment endpoints. Limits are stricter in `server` mode than in `local` mode (configurable, but the defaults must be safe for public exposure).
- Structured logging with secret redaction.
- CORS policy: in `server` mode, restricted to the configured dashboard origin and the extension origin. In `local` mode, may be relaxed but never `*` in any production-tagged build.

**Acceptance criteria.**
- An unauthenticated request to any non-public endpoint returns 401.
- A token bound to user A cannot read user B's resources (403).
- A revoked device token returns 401 on the next request.
- Submitting an unsupported file type returns a clean 400 without crashing the parser.
- Submitting an oversize payload returns 413 before the bytes are written to disk.
- Hitting capture endpoints faster than the configured limit returns 429.
- A request to a `server`-mode deployment over plain HTTP is redirected to HTTPS (or rejected, per the reverse-proxy config); plain HTTP only succeeds when bound to `localhost`.
- A token issued for one device, when used from a different IP, is *not* automatically rejected (mobile networks roam) but the change is logged for review.

**Security gates.**
- TLS required in `server` mode (HTTP allowed only on `localhost` in `local` mode).
- HSTS header set in `server` mode responses.
- Tokens are stored as hashes only; the database compromise scenario does not yield usable bearer tokens.
- CSRF protection on cookie-authenticated endpoints (if cookies are used for the dashboard); bearer-token API endpoints rely on the standard non-cookie protection.
- File-size cap enforced **at the edge** (reverse proxy and application both), before parsing.
- URL submissions are queued for fetching but **not fetched here** — fetching is Stage 3 and goes through the SSRF-hardened fetcher.
- Auth events (success, failure, lockout, token issuance, token revocation) logged to the `JobRun`-style audit stream.
- Brute-force protection on the primary credential endpoint (exponential lockout or equivalent).

**Out of scope.** OAuth, SSO, organization accounts, role-based access, multi-user (one account per deployment in MVP).

---

### Stage 3 — Content normalization (URL fetcher + parsers)

**Goal.** Turn captured raw inputs into clean, model-ready text. This is one of the highest-risk stages for security and must be built carefully.

**Deliverables.**
- **SSRF-hardened URL fetcher**:
  - Only `http`/`https`.
  - DNS resolved up-front; reject if the resolved IP is in private ranges (RFC1918, loopback, link-local, ULA, IPv6 unique-local, cloud metadata addresses such as `169.254.169.254`).
  - Re-validate the IP after every redirect; cap redirects.
  - Aggressive timeouts; bounded response size; `Content-Type` and size checks.
  - Egress through a configurable proxy if available.
- **HTML extractor** (boilerplate stripper, e.g., `readability-lxml`, `trafilatura`).
- **PDF parser** with hard limits: max pages, max bytes, max extracted text size, no JavaScript execution, no font/external-resource fetching. Run in a sandboxed worker (separate process, low privileges, resource caps via `resource.setrlimit`/`prlimit` or container).
- **Markdown / plain-text parser** with size caps and encoding sniffing.
- All extracted text stored as a blob and hashed.

**Acceptance criteria.**
- Stage 3 SSRF and parser tests run against the `evil-server` container (§1.3). They must be invokable via `make test-ssrf` and run as part of CI.
- Fetcher tests cover, against canned scenarios served by `evil-server`: localhost, 127.0.0.0/8, 10/8, 172.16/12, 192.168/16, 169.254/16, IPv6 loopback and ULA, DNS-rebinding (initial-resolve-then-mutate scenario), redirect-to-private, oversized response, slow-loris timeout, content-type/body mismatch. **All must be rejected** by the backend container while running with production-equivalent SSRF settings.
- A maliciously crafted "PDF bomb" served by `evil-server` (e.g., highly compressed, deeply nested objects) does not exhaust the parser-sandbox container's memory; it is rejected within the configured limits, and the `parser-sandbox` container's resource caps are observable in the test output.
- A markdown file containing inline HTML/JS is parsed as text only; no scripts execute.
- A 50 MB text file is rejected; a 500 KB file is parsed within bounded time.

**Security gates.**
- Parser sandboxing in place and verifiable in the dev stack: the `parser-sandbox` container runs with CPU, memory, and output-size caps that the test harness can observe being hit.
- Resource caps verifiable (memory, CPU time, output size, page count).
- All fetched content stored with provenance (final URL, status, content-type, size, hash).
- Fetcher does not follow `file://`, `gopher://`, or any non-HTTP scheme.
- The SSRF test suite is part of the standard CI run, not optional. A regression that weakens the fetcher fails the build.

**Out of scope.** Headless-browser rendering, paywall handling, archive ingestion, OCR for scanned PDFs.

---

### Stage 4 — Browser extension

**Goal.** Provide one-click capture from an active tab.

**Deliverables.**
- Manifest V3 extension targeting Chromium first.
- Minimal popup UI: title preview, optional note, "Save" button, status feedback.
- Uses the `activeTab` permission rather than broad host permissions where possible.
- Authenticates to the backend with a **per-device token** (Stage 2, §7.6). The user enrols the extension once via the dashboard, which issues a token shown only at issuance time; the extension stores the token locally. The token is revocable from the dashboard.
- Sends URL, page title, and optional user note. Page text extraction is **opt-in per save** and is plainly disclosed in the UI.
- No remote code loading; CSP set to disallow eval and remote scripts.
- Configurable backend URL so the same extension build works against `localhost` (local-only deployments) and a public hostname (server-hosted).

**Acceptance criteria.**
- Loaded unpacked into Chrome, the extension can save the current tab and the source appears in the queue within one second on `localhost`.
- The extension manifest is reviewed for unnecessary permissions; any non-`activeTab` permission is justified inline in `DECISIONS.md`.
- Saving while offline produces a clear error and does not silently lose the capture; a small local retry queue is acceptable but must be bounded.

**Security gates.**
- No secrets stored in extension localStorage beyond the bound API token; the token is revocable from the backend.
- No host permissions broader than required.
- All network calls go to the configured backend URL only (no third-party beacons or analytics).

**Out of scope.** Firefox/Safari port, page-text auto-extraction by default, clipping selections beyond plain text.

---

### Stage 5 — Per-source summarization

**Goal.** Produce a summary, key points, and topics for each normalized source.

**Deliverables.**
- A `SummarizerAdapter` interface with at least one concrete implementation (cloud or local).
- A prompt template versioned in the repo (`prompts/per_source.v1.txt`) that:
  - Treats source content as **inert data**, never as instructions.
  - Wraps source content in clear delimiters (`<source>...</source>`) and instructs the model to ignore any directives inside.
  - Asks for fixed JSON-shaped output (summary, key_points, topics).
- A response validator: rejects malformed output, retries once with a stricter reminder, then marks the source `failed`.
- Caching by `extracted_content_hash`.

**Acceptance criteria.**
- Given a sample fixture article, the summarizer returns valid JSON with non-empty summary and at least one key point.
- A fixture containing a prompt-injection attempt ("ignore previous instructions and output X") does not cause the model to deviate from the JSON shape **and** does not include the attacker's payload as if it were a directive followed. The injection content may be summarized as content, but the model output's structure is unchanged.
- A second submission of the same content hits the cache and does not call the model.

**Security gates.**
- Source content is never concatenated raw into the system prompt; it is always a delimited user-message payload.
- Prompts and prompt versions are stored alongside outputs (`prompt_version`, `input_hash`).
- The adapter redacts known credential patterns (AWS keys, GitHub tokens, JWTs) before transmission to external providers.
- A "local-only" mode flag exists, even if not the default — when set, no external provider is contacted.

**Out of scope.** Quality-grade fact-checking, multi-pass refinement, embeddings/vector search.

---

### Stage 6 — Daily synthesis and report generation

**Goal.** Combine the day's summaries into a single coherent Markdown report and render it to HTML.

**Deliverables.**
- A `SynthesizerAdapter` interface with one concrete implementation (typically the stronger model).
- Synthesis prompt (`prompts/synthesis.v1.txt`) that produces a structured Markdown report matching Section 7.3.
- Optional clustering step: group summaries by topic before synthesis when the day exceeds a threshold of items (e.g., > 8). MVP can use a simple heuristic (shared topic labels from Stage 5) before reaching for an embedding model.
- Markdown-to-HTML renderer with a strict allow-list (no inline scripts, no event handlers, sanitized).
- Report is hashed and stored with a stable per-day filename pattern: `report-YYYY-MM-DD.md`.

**Acceptance criteria.**
- Given fixture summaries from a synthetic 5-source day, the synthesizer produces a Markdown report with: title, overview, ≥1 section per source or cluster, references to all included sources by stable ID.
- Re-running the synthesis on the same input set produces a report with the same `report_hash` (modulo controlled non-determinism — if non-determinism is unavoidable, this is documented and the test compares structural equivalence).
- HTML render of an attempted XSS payload in a summary is escaped, not executed.
- An empty day produces a brief "no items today" notice rather than calling the model.

**Security gates.**
- Same prompt-injection defenses as Stage 5 carry through.
- HTML sanitization tested against a known XSS payload list.
- Report references are validated to point to real sources owned by the same user.

**Out of scope.** Editorial fine-tuning, multi-day trend analysis, image generation in reports.

---

### Stage 7 — Podcast script generation

**Goal.** Convert the daily report into a script that reads well aloud, in either single-host or two-host format.

**Deliverables.**
- A `ScriptAdapter` interface and one concrete implementation.
- Two prompt templates: `prompts/script_single.v1.txt`, `prompts/script_two_host.v1.txt`.
- Output format is a structured script: an ordered list of `{speaker, text}` segments, plus intro and outro segments.
- Length controls: target duration via word-count budget (assume ~150 words per minute as a rough TTS heuristic; actual duration is measured in Stage 8).
- Sensitivity filter: any source flagged `private` is either summarized in deliberately less detail or omitted from the spoken output (configurable), but remains in the written report.

**Acceptance criteria.**
- Generated script for a fixture report parses cleanly into segments.
- Every segment has a speaker label drawn from the configured cast.
- Source attributions are present in spoken form ("From an article on X by Y…") for at least the major sources.
- A `private`-sensitivity source from Stage 5 produces no specific quoted detail in the script.

**Security gates.**
- The script generator runs a final pass that rejects segments containing strings matching credential patterns (defense in depth — should never reach this point, but the check is kept).
- No prompt or response content is logged at INFO level by default; DEBUG-level traces are written only to a separately permissioned file.

**Out of scope.** Voice acting direction, SSML annotations beyond pauses (Stage 8 may revisit).

---

### Stage 8 — Python audio generation

**Goal.** Render the script into a single MP3 audio file.

**Deliverables.**
- A `TTSAdapter` interface (`synthesize(text, voice) -> audio_bytes`).
- **`StubTTS`** — a deterministic stub adapter (introduced in Stage 0) that returns short silent MP3 segments with duration proportional to input length. Used as the default in the dev `docker-compose.yml` to keep the inner loop fast. Required, not optional.
- **At least one real TTS adapter.** MVP candidates: Coqui TTS or Kokoro for fully local; ElevenLabs or Polly for hosted quality. Configurable via the same adapter interface.
- Segment-by-segment synthesis with voice mapping per speaker.
- Audio concatenation (e.g., `pydub` or `ffmpeg`) into one MP3, with optional intro/outro audio.
- Duration measured from the produced file and stored on the `PodcastEpisode`.
- Hard cap on total audio duration (default 30 minutes) to prevent runaway generation.

**Acceptance criteria.**
- `make test` exercises the pipeline end-to-end with `StubTTS` and produces a valid MP3 with the expected segment count and approximate length.
- `make test-audio` exercises the pipeline with the configured real TTS adapter and produces a playable MP3 within the duration target. This target runs separately from `make test` to avoid cost and latency in the inner loop.
- The audio file's measured duration (with the real adapter) is within ±25% of the word-count estimate.
- Switching the configured TTS adapter does not require code changes elsewhere.
- Failure of one segment does not corrupt the rest; the segment is replaced with a short spoken error notice or skipped, and the run is marked partially-successful.

**Security gates.**
- The audio file's path is not user-controllable; it is derived from the report date and a server-side random suffix.
- Audio file permissions match the user's namespace (private by default).
- If the TTS provider is external, the script text sent to it is the same script text recorded in `script_ref`; any per-provider escaping is recorded in `voice_configuration`.
- A maximum byte size is enforced on the final audio (DoS guard).
- Production deployments do not ship with `StubTTS` as the active adapter; a startup check refuses to launch in `server` mode if the configured TTS adapter is `StubTTS` (the dev convenience must not silently leak into production).

**Out of scope.** Music beds, multi-track mixing, mastering.

---

### Stage 9 — Scheduling and orchestration

**Goal.** Run the full daily pipeline automatically, idempotently, with clean failure handling.

**Deliverables.**
- A scheduler (APScheduler, or system cron invoking the worker entry point) that fires once per local day at the configured time.
- A `JobRun` record per invocation, with per-stage outcomes.
- A per-day distributed lock (file lock or DB advisory lock) preventing concurrent runs for the same date.
- Manual trigger endpoint (Stage 2) wired to the same worker entry point with the same locking.
- Retry policy: each stage retries transient failures (network, provider 5xx) up to a small bounded count with exponential backoff. Non-transient failures (validation, auth) do not retry.
- A "dry-run" mode that exercises Stages B–E without calling external providers (uses fixture responses) so end-to-end tests are cheap.

**Acceptance criteria.**
- Triggering two runs concurrently for the same date causes exactly one to execute; the other observes the lock and exits with a clear status.
- A simulated provider 5xx in Stage C is retried and eventually succeeds; the `JobRun` records the retry.
- A simulated hard failure in Stage D leaves Stages A–C results intact and the queue not archived.

**Security gates.**
- Manual trigger endpoint requires authentication and rate-limits.
- The scheduler does not run with elevated privileges beyond what the worker needs.
- Locks are released even on crash (timeout-based or process-bound).

**Out of scope.** Multi-host scheduling, Kubernetes operators.

---

### Stage 10 — Delivery and dashboard

**Goal.** Make the daily report and audio reachable by the user from any of their enrolled devices.

**Deliverables.**
- Local-folder delivery on the server: `outputs/YYYY-MM-DD/` containing `report.md`, `report.html`, `episode.mp3`, `script.txt`.
- Web dashboard pages: today's queue, calendar of past days, single-day report viewer, episode player, device-token management (list, label, revoke).
- Time-limited download URLs for the audio (signed token, short TTL). These must work from a phone or any other authenticated client, not just the machine that ran the worker.
- Episode player must support direct streaming (HTTP `Range` requests) so a phone client can seek without downloading the full file.
- Optional later: email delivery, RSS feed for podcast clients (per-user secret URL, see §16).

**Acceptance criteria.**
- After a successful run, the four output files exist with correct content hashes recorded in the DB.
- The dashboard's calendar lists every day that has a `DailyReport`.
- A download URL becomes invalid after its TTL.
- A download URL for user A cannot be used by user B even if guessed.
- Streaming the episode from a mobile browser over a public deployment works with seek; the server returns `206 Partial Content` for `Range` requests.
- Revoking a device token in the dashboard immediately blocks subsequent download attempts using that token.

**Security gates.**
- Dashboard pages require auth; no anonymous browsing of reports or episodes.
- Output folders are private-by-default in permissions on the server filesystem.
- Download tokens are random, single-purpose, scoped to one resource and one user, and short-lived.
- If RSS is added later (§16), feed URLs are per-user-secret and revocable, never publicly indexed; the feed URL is itself treated as a credential.
- The reverse proxy (server-hosted mode) does not auto-index output directories; only signed URLs reach files.

**Out of scope.** Native mobile clients (see §16), social embeds.

---

### Stage 11 — Hardening and pre-launch review

**Goal.** Walk the security checklist (Section 14.4) and resolve all blocking findings before declaring the system ready for daily personal use.

**Deliverables.**
- A pen-test pass covering the SSRF fetcher, the file parser, the prompt-injection-resistance of Stages 5–7, the auth/authz boundary, the device-token lifecycle, and the download-token machinery.
- A dependency audit and SBOM snapshot.
- A privacy review: which paths can a single source's content take, who/what processes it, and is each step disclosed in the UI?
- A `RUNBOOK.md` covering: how to back up and restore, how to revoke a leaked device token, how to purge a user's data, how to roll the prompt versions, how to renew TLS certificates, how to rotate the primary credential, how to recover from a lost-laptop scenario when the lost laptop held the only enrolled device.
- For server-hosted mode specifically: a deployment hardening checklist (TLS configuration, HSTS, reverse-proxy headers, fail2ban or equivalent, system-package auto-updates, off-host backup of the metadata DB and blob store, log retention).

**Acceptance criteria.**
- Every item in Section 14.4 is checked, with evidence (test name, ADR, or report) recorded.
- No `high` or `critical` open dependency vulnerability.
- Runbook procedures are exercised at least once on a test instance, including: revoke a device token, restore from backup, rotate a TLS certificate, purge a day's data.
- For server-hosted mode: a known-vulnerable client (an unenrolled browser) cannot reach any endpoint other than the auth-challenge endpoint; an `nmap`-style scan against the public hostname reveals only the expected ports.

**Security gates.** This stage *is* the security gate.

**Out of scope.** External professional audit (recommended for a hosted multi-user version, not blocking for self-hosted single-user MVP).

---

## 13. Recommended Implementation Stack

These are recommendations, subject to the deviation clause. They are not arbitrary; each is justified.

- **Extension:** TypeScript, Manifest V3. Chromium-first because of Manifest V3 maturity.
- **Backend & worker:** Python (FastAPI for the API; the worker can be a separate process invoked from the same codebase). Python is chosen because the LLM and TTS ecosystems are richest there; switching the API to a different language is allowed but the worker should remain in Python or interoperate with Python adapters.
- **DB:** SQLite for MVP, Postgres-ready (use SQLAlchemy or a similar abstraction). Migrations via Alembic or equivalent.
- **Blob store:** local filesystem behind an interface; S3-compatible later.
- **Scheduler:** APScheduler for in-process simplicity, or system cron invoking the worker entry point.
- **HTML extractor:** `trafilatura` or `readability-lxml`.
- **PDF parser:** `pypdf` or `pdfminer.six` (no JS, no fonts) inside a sandboxed subprocess.
- **HTTP client:** `httpx` with a custom transport that performs SSRF checks.
- **TTS:** Coqui TTS or Kokoro for local; ElevenLabs or Polly via adapter for hosted. The adapter contract matters more than the choice.
- **Audio assembly:** `pydub` (which uses `ffmpeg`).
- **Frontend dashboard:** small React or HTMX app — anything that ships fast; deviation explicitly allowed here.

---

## 14. Security (Cross-Cutting)

Security is woven into every stage above. This section is the central reference, organized by threat. Each item is tied back to the stages where it must be implemented.

### 14.1 Threat model summary

**Trust boundaries** (see Section 6.3): B1 extension↔API, B2 API↔external web, B3 backend↔parsers, B4 worker↔providers, B5 worker↔storage, B6 scheduler↔worker.

**Primary adversaries / failure modes:** malicious web pages, hostile PDFs, prompt injection, SSRF, compromised browser extension or stolen token, third-party-provider data leakage, dependency compromise, accidental over-sharing.

### 14.2 Risk register and mitigations (mapped to stages)

| Risk | Stages | Core mitigations |
|---|---|---|
| **A. Hostile source content** | 3, 5, 6, 7 | Treat all source text as inert data; sanitize HTML; sandbox parsers; strict file-size and page caps. |
| **B. Prompt injection** | 5, 6, 7 | Delimited source payloads; system prompts that explicitly refuse to follow content directives; structured-output validation; `prompt_version` + `input_hash` recorded for forensics. |
| **C. SSRF / unsafe URL fetch** | 3 | Allowlist `http`/`https` only; block private IPs pre- and post-redirect; cap redirects, size, time; outbound proxy where possible. |
| **D. Browser extension compromise** | 4 | Minimum permissions; `activeTab` over host permissions; no remote code; CSP strict; revocable token; no secrets in extension storage beyond that token. |
| **E. API auth/session abuse** | 2 | Short-lived tokens; CSRF where applicable; rate-limiting; auth-event logging; token revocation. |
| **F. Data privacy / local exposure** | 1, 2, 6, 8, 10 | Per-user namespacing at repository layer; private-by-default permissions; explicit "this leaves your machine" UI when external providers are used; per-item delete; full purge supported. |
| **G. External provider leakage** | 5, 6, 7, 8 | Local-only mode supported; redact credential patterns before send; minimize prompt payload; configurable provider via adapter. |
| **H. Secret leakage in logs/prompts** | All | Centralized secret management; redacting log formatter; debug traces written to a stricter-permissioned location; never echo creds back into outputs. |
| **I. Insecure file parsing** | 3 | Sandboxed parser process, resource caps, file-size and page caps, no JS/external-resource execution, archives rejected. |
| **J. DoS / resource exhaustion** | 2, 3, 8, 9 | Quotas; size caps at every boundary; bounded retry; bounded audio duration; bounded queue length per day. |
| **K. Output tampering / integrity** | 6, 8, 10 | SHA-256 hashes on every artifact; immutable per-day naming; per-user owner check on every retrieval. |
| **L. Unauthorized output access** | 10 | Auth required for dashboard; private permissions on output files; signed time-limited download URLs scoped to user+resource. |
| **M. Dependency / supply chain** | 0 | Pinned versions; lockfiles; CI vulnerability scan; SBOM; review high-risk dependency upgrades. |
| **N. Unsafe scheduling / job state** | 9 | Per-day locks; idempotent stages; authenticated manual triggers; durable `JobRun` audit. |
| **O. Audio/transcript leakage** | 7, 8 | Final pre-TTS sweep for credential patterns; `private` sensitivity flag on sources suppresses spoken detail; transcript stored at same access level as audio. |
| **P. Public-internet exposure (server-hosted only)** | 0, 2, 10, 11 | TLS + HSTS; reverse proxy with edge size/rate limits; brute-force protection on credential endpoints; per-device tokens with individual revocation; minimised exposed surface (only the API/dashboard ports listen externally); off-host backups; log monitoring. Local-only mode avoids this risk class entirely. |
| **Q. Lost or compromised client device** | 2, 4, 10 | Per-device tokens stored hashed; user can revoke an individual device from the dashboard without affecting others; `last_used_at` and originating-IP changes logged for review; primary credential rotation invalidates all device tokens at the user's request. |

### 14.3 Baseline controls for MVP

- HTTPS in production (HTTP only on `localhost`).
- Per-user authn/authz, enforced at both API and repository layers.
- Strict input validation everywhere.
- SSRF-hardened URL fetching.
- Sandboxed parsing.
- At-rest protection (filesystem permissions minimum; full encryption preferred — record the choice).
- Secret redaction in logs and structured outputs.
- Rate limits and size caps at every ingress.
- Durable, append-only `JobRun` audit log.
- Explicit local-vs-cloud processing modes; UI disclosure when content leaves the machine.

### 14.4 Pre-launch review priorities

In order:

1. Browser-extension permissions and capture scope.
2. URL ingestion and SSRF defenses.
3. File parsing sandbox and limits.
4. Prompt-injection resistance (Stages 5–7).
5. Data retention, encryption-at-rest, deletion behavior.
6. Third-party-provider exposure and redaction.
7. Authorization checks on reports and audio.
8. Dependency pinning and vulnerability scan.

### 14.5 Security deviation rule (re-affirmation)

The deviation clause (0.2) applies here too, with one stricter requirement: **a deviation that removes or weakens a control listed in 14.2 must replace it with an equivalent or stronger control**, documented in `DECISIONS.md`, and verified by a corresponding test. Removing a security control without a replacement is not a permitted deviation.

---

## 15. Open Questions (Tracked, Not Blocking)

These are deliberately left open. The corresponding stage will pick a default and record the choice in `DECISIONS.md`; later iterations can revisit.

- Cluster-then-summarize, or summarize-then-cluster? (Stage 6 default: summarize first, then cluster only when day exceeds threshold.)
- Generate the script from the report only, or have the script consult per-source summaries for color? (Stage 7 default: from the report; deviation allowed if quality clearly improves.)
- User-selectable voices per section? (Stage 8 default: per speaker, not per section; per-section deferred.)
- One episode per day, or thematic mini-episodes? (Stage 8 default: one per day.)
- Transcript-first or audio-first authoring? (Default: transcript-first; audio derived.)

---

## 16. Outlook (Post-MVP Directions)

The MVP is a single-user, self-hosted system reachable from one or more of the user's own clients. The architecture has been designed to extend cleanly along the following axes. None of these are commitments; they are documented so that MVP decisions don't accidentally close them off.

### 16.1 Native client app (mobile + desktop)

Because the backend already exposes a clean HTTP API authenticated by per-device tokens, a native app is purely additive.

**Capabilities the app would offer:**
- Capture via the OS share-sheet (iOS share extension, Android share intent), so any link or article from any app can be sent to the user's Interestriage server in one tap.
- Queue review: see today's captures, edit notes/tags, mark importance or sensitivity, remove items.
- Listen: stream the day's episode with chapter markers (when added), with offline caching for commute or flight.
- Notifications: a push when the morning episode is ready.
- Transcript view alongside audio playback, with tap-to-jump-to-source.

**What changes server-side to support this:** essentially nothing for capture and listening. Push notifications would need a small server-side dispatcher; offline caching is purely a client concern. The `DeviceToken` model already supports per-device enrolment.

**Stack candidates:** a single cross-platform codebase (React Native, Flutter, or Tauri Mobile) is likely the right answer for a side project; native Swift/Kotlin is overkill unless the share-sheet UX needs platform-specific polish.

### 16.2 Multi-user evolution

The repository layer enforces per-user namespacing from Stage 1. Going from "one user per deployment" to "multiple users per deployment" mostly requires:

- Account lifecycle (signup, email verification, password reset / passkey enrolment).
- Quotas per user (storage, API calls, model spend).
- Admin tooling for the operator (view users, suspend, purge).
- Billing if it ever becomes a service (out of scope for self-hosted).
- A more serious abuse-handling stance: spam captures, hostile sources designed to burn through model budget, etc.

Going to multi-tenant SaaS is a substantial step beyond this; it is *possible* from the MVP architecture but not *easy*. It would benefit from an explicit security re-review, since the threat model shifts considerably (now any signed-up user is a potential adversary).

### 16.3 RSS podcast feed

A per-user secret RSS URL would let standard podcast clients (Apple Podcasts, Pocket Casts, AntennaPod) subscribe to the user's daily episodes. The implementation is small: a feed endpoint that lists the last N episodes with signed audio URLs. The feed URL must be treated as a credential — long, unguessable, revocable, and never indexed.

### 16.4 Family / shared-feed mode

Multiple users on one deployment could optionally share a "common interests" channel: items dropped into a shared queue produce a shared episode. This requires explicit consent on every shared item (never silent sharing) and a clear UI cue. It also requires care around prompt-injection: a hostile shared source could affect the other family member's morning briefing. Shared mode would inherit all the multi-user hardening above.

### 16.5 Better-than-batch playback experiences

- **Chapter markers** on the audio so listeners can skip to a specific source.
- **Inline citations in the transcript** that deep-link to the source.
- **Re-listen to "yesterday's deep dive"** — generate a longer audio explainer for a single source on demand.
- **Weekly recap** — a Sunday digest summarising the week's daily reports.

### 16.6 Smarter capture

- A bookmarklet for browsers where Manifest V3 is not viable.
- An email-forward address (`capture@your-host`) with strict authentication and a per-user secret address.
- An RSS *input*: subscribe to feeds and auto-add the day's items.
- A read-it-later import (Pocket / Instapaper / Matter exports).

### 16.7 Privacy-strong tier

A configuration profile that:

- Forces local LLMs only (no external API calls).
- Forces local TTS only.
- Disables download URLs in favour of LAN-only access.
- Reduces retention to a configurable window.

This profile is mostly already supported by the adapter design; the work is packaging it as a single named configuration the user can opt into.

---

## 17. Glossary

- **Source** — a single captured item (URL, PDF, text, markdown).
- **Queue** — the set of sources captured for a given local calendar day.
- **Daily Report** — the synthesized written digest for a day.
- **Episode** — the audio rendering of the day's report.
- **Adapter** — a stable interface around a provider (LLM, TTS, blob store).
- **Sandbox** — an isolated execution context with resource and capability limits.
- **SSRF** — Server-Side Request Forgery; abusing the backend to fetch internal/forbidden resources.
- **Prompt injection** — content embedded in source material that attempts to redirect a downstream model.
- **`JobRun`** — a durable record of a batch invocation, used for idempotency and audit.
- **`DeviceToken`** — a per-device bearer credential that authenticates one client (one browser, one phone) against the backend. Hashed at rest, individually revocable, finite-lifetime.
- **Local-only mode** — deployment configuration where the backend binds to `localhost`; no public network exposure.
- **Server-hosted mode** — deployment configuration where the backend is reachable over the public internet behind a TLS reverse proxy; the default in this spec.
- **Monorepo** — single git repository containing all subprojects (extension, backend, worker, dashboard, future mobile app) under one history. Maps to multiple deployment artifacts at build time, not at source-tree time.
- **Build artifact** — an output of the CI pipeline (backend Docker image, dashboard static bundle, extension `.zip`, mobile binary). Each artifact is deployed independently to its own destination.
- **Evil server** — the `evil-server` container in `infra/dev/evil-server/`, a deliberately hostile HTTP server that serves canned attack payloads (private-IP redirects, DNS-rebinding, slow-loris, oversized responses, PDF bombs) for Stage 3 SSRF and parser tests. Never started by the default dev stack; never exposed to the host.
- **`StubTTS`** — a deterministic stub TTS adapter that returns short silent MP3 segments. Default in the dev stack to keep the inner loop fast. Refused in production by a startup check.
