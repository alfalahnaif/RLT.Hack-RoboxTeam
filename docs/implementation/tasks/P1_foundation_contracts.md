# Phase P1 — Engineering Foundation & Contracts

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Implements the source spec [P1-001 Canonical Data + Benchmark Seed](../../sources/Supplier_Radar_P1-001_Canonical_Data_and_Benchmark_Seed.md) (tasks P1-007…P1-014) plus Epic E0 foundation (P1-001…P1-006).
> Exit: `docker compose up` → healthy stack; contracts, seed, benchmark v0.1.0 validate; seed deterministic.

### P1-001 — Repository skeleton & VCS conventions
- **Objective:** Create the monorepo structure and working conventions.
- **Context:** ED-11, ED-12, [ARCHITECTURE §4](../../architecture/ARCHITECTURE.md#4-backend-module-layout), R-26.
- **Dependencies:** P0-004.
- **Requirements:** `git init`; folders `/backend /frontend /contracts /data/seed /benchmark /scripts /infra /docs`; root README (run instructions placeholder); `.gitignore` (env, caches, model weights, node_modules, data dumps); `.editorconfig`; `.env.example`; commit convention (Conventional Commits with task ID, e.g. `feat(P2-004): …`).
- **Expected Output:** skeleton committed on `main`; work continues on branches `task/Pn-nnn-slug`.
- **Acceptance Criteria:** clean clone contains all folders with README; no secrets tracked.
- **Validation:** `git status` clean; `git ls-files | grep -i "\.env$"` empty.
- **Out of Scope:** application code.

### P1-002 — Backend application skeleton
- **Objective:** Runnable FastAPI app with cross-cutting plumbing.
- **Context:** [ARCHITECTURE §4, §11, §12](../../architecture/ARCHITECTURE.md), ED-07, ED-16, NFR-OBS-01, NFR-SEC-06, DOMAINS D0.
- **Dependencies:** P1-001.
- **Requirements:** module folders per ARCHITECTURE §4 (empty services); settings from env (Pydantic settings; `DEBUG`, `DATABASE_URL`, caps, timeouts); request-id middleware (accept/generate `X-Request-ID`); JSON structured logging; error envelope + exception handlers; `GET /api/v1/health` stub (api only); debug router registered only if `DEBUG=true`; CLI entry `python -m app.cli` with no-op command; pyproject with ruff/mypy/pytest config.
- **Expected Output:** `backend/app/...`, `backend/tests/`.
- **Acceptance Criteria:** `/api/v1/health` → 200 JSON with `request_id`; unknown route → 404 in error envelope; with `DEBUG=false` `/api/v1/debug/*` → 404.
- **Validation:** `pytest` (health, envelope, debug gating), `ruff`, `mypy`.
- **Out of Scope:** DB models, search logic.

### P1-003 — Frontend application skeleton
- **Objective:** Next.js + TypeScript app wired to the Design System foundations.
- **Context:** P0-005 mapping, `safarflow-design-system` skill, ED-08, OQ-22.
- **Dependencies:** P1-001, P0-005.
- **Requirements:** Next.js (App Router), TS `strict`, ESLint, Vitest; DS tokens/fonts/i18n setup per P0-005 decision (locale incl. `ru` if chosen); API base URL from env; placeholder route for S-01; health indicator calling `/api/v1/health`.
- **Expected Output:** `frontend/` app.
- **Acceptance Criteria:** `npm run build` and `npm run lint` pass; page renders with DS tokens and calls health.
- **Validation:** build/lint/test commands.
- **Out of Scope:** real screens.

### P1-004 — Docker Compose stack
- **Objective:** One-command reproducible environment.
- **Context:** NFR-PORT-01, NFR-REL-04, ED-17.
- **Dependencies:** P1-002 (P1-003 for frontend service).
- **Requirements:** services `postgres` (image with pgvector; init script enables `vector`, `pg_trgm`), `api`, `frontend`; healthchecks; named volume; env from `.env`; api waits for DB health.
- **Expected Output:** `infra/docker-compose.yml`, `infra/db/init.sql`, Dockerfiles.
- **Acceptance Criteria:** `docker compose up -d` from clean clone → all services healthy; `SELECT extname FROM pg_extension` lists `vector`, `pg_trgm`.
- **Validation:** compose up + health curl.
- **Out of Scope:** embedding model baking (P3-001), deployment (P8-003).

### P1-005 — Database migration baseline
- **Objective:** Alembic configured against compose DB.
- **Context:** D-15, ARCHITECTURE §7.
- **Dependencies:** P1-004.
- **Requirements:** Alembic env using app settings; baseline revision enabling extensions idempotently; CLI/Make target `migrate`.
- **Expected Output:** `backend/migrations/`.
- **Acceptance Criteria:** `alembic upgrade head` on empty DB succeeds twice (idempotent); `downgrade base` works.
- **Validation:** run commands in compose.
- **Out of Scope:** domain tables (P2-001).

### P1-006 — CI baseline
- **Objective:** Automated quality gate.
- **Context:** DoD §2–6.
- **Dependencies:** P1-002, P1-003.
- **Requirements:** on push/PR: backend lint+type+unit tests; frontend lint+type+build+unit; contract/seed/benchmark validators (once present); caching.
- **Expected Output:** CI workflow file (e.g. `.github/workflows/ci.yml`).
- **Acceptance Criteria:** CI green on skeleton; failing lint fails the job.
- **Validation:** push a branch.
- **Out of Scope:** deployment pipelines.

### P1-007 — Entity contracts: supplier, product_offering, data_source
- **Objective:** JSON Schema 2020-12 contracts for canonical entities.
- **Context:** [DOMAIN_MODEL §2.1–2.5](../../domain/DOMAIN_MODEL.md), P1S §6–12, BR-30, BR-34, C-03, C-16, C-18, ED-05, ED-23.
- **Dependencies:** P1-001.
- **Requirements:** field rules exactly per P1S tables (lengths, digit patterns, enums, URL format, 0–1 ranges, non-empty `source_ids`); `$id` + `version: 0.1.0`; conditional `source_observed_at` if C-16 accepted; optional [ER] fields only if accepted in P0-004; examples embedded.
- **Expected Output:** `contracts/supplier.schema.json`, `product_offering.schema.json`, `data_source.schema.json`, `contracts/README.md` (versioning rules BR-25).
- **Acceptance Criteria:** P1S full examples validate; crafted invalid examples (bad INN, bad enum, empty source_ids) fail.
- **Validation:** unit tests with `jsonschema`.
- **Out of Scope:** DB schema, Pydantic models.

### P1-008 — Search & error contracts
- **Objective:** Public request/response and error contracts.
- **Context:** [API_CONTRACTS](../../architecture/API_CONTRACTS.md), P1S §13–17, BR-13, BR-28, ED-01, ED-07.
- **Dependencies:** P1-007.
- **Requirements:** `search_query.schema.json` (query 3–1000, filters, market_scope enum, limit 1–100 default 20, optional `intent_overrides` if ED-19 accepted); `search_response.schema.json` at P2 level (P1S §15) with reason-code enum; `error.schema.json`; version 0.1.0.
- **Expected Output:** three schema files + README section.
- **Acceptance Criteria:** P1S examples validate; P1S §14 invalid examples fail; response requires non-empty `reason_codes`, `score` ∈ [0,1].
- **Validation:** unit tests.
- **Out of Scope:** later-phase response fields (added as MINOR versions).

### P1-009 — Contract validation script
- **Objective:** Validate schema files themselves.
- **Context:** P1S §32.
- **Dependencies:** P1-007, P1-008.
- **Requirements:** `scripts/validate_contracts.py` checks every `contracts/*.schema.json` against the 2020-12 metaschema, version present, embedded examples valid; non-zero exit on failure.
- **Expected Output:** script + CI step.
- **Acceptance Criteria:** prints `Contracts valid: N/N`; corrupting a schema fails the run.
- **Validation:** run locally and in CI.
- **Out of Scope:** seed validation.

### P1-010 — Text & name normalization library
- **Objective:** Single normalization implementation used by seed generator, ingestion and search.
- **Context:** BR-33, P1S §8, P0 §27, EC-08.
- **Dependencies:** P1-002.
- **Requirements:** `shared/text.py`: NFC, lowercase, `ё→е`, whitespace/punctuation normalization, quote stripping; `normalize_company_name` removing only legal-form tokens (ООО, АО, ПАО, ЗАО, ОАО, ИП, НКО…) incl. quoted/uppercase forms; no transliteration; pure functions.
- **Expected Output:** module + tests.
- **Acceptance Criteria:** `ООО "ТехноПанель"`→`технопанель`; `АО "Север Снаб"`→`север снаб`; meaningful words ("медицинские системы") preserved; idempotent (`f(f(x)) == f(x)`).
- **Validation:** pytest table-driven cases.
- **Out of Scope:** stemming, synonyms.

### P1-011 — Deterministic seed generator
- **Objective:** Generate reproducible seed suppliers/offerings/data sources.
- **Context:** P1S §18–25, §37–39, §43–45, BR-20, BR-30, R-29, R-31, R-32.
- **Dependencies:** P1-007, P1-010.
- **Requirements:** `scripts/generate_seed.py` (random_seed 42); UUIDv5 from fixed namespace + source key; ≥100 suppliers / ≥200 offerings (preferred 200/500); 10 categories; known 60–70%; type mix ~30/30/30/5/5; ~20% incomplete profiles; marked duplicate fixtures (`source_ids` note or flag); Russian titles/descriptions; fictional names; 70% background / 30% hand-crafted anchors (anchors defined in a readable data file, e.g. `scripts/seed_anchors.yaml`).
- **Expected Output:** `data/seed/suppliers.jsonl`, `product_offerings.jsonl`, `data_sources.jsonl`, `data/README.md`.
- **Acceptance Criteria:** two runs produce byte-identical files; all records validate against contracts; distribution report printed.
- **Validation:** run twice + `sha256sum` compare; contract validation.
- **Out of Scope:** procurement/evidence fixtures (P3-008), benchmark files (P1-012).

### P1-012 — Benchmark seed v0.1.0
- **Objective:** Queries, qrels and manifest for the lexical baseline.
- **Context:** [EVALUATION §2](../../architecture/EVALUATION.md#2-benchmark-datasets), P1S §26–30, §39–45, BR-21, BR-40.
- **Dependencies:** P1-011.
- **Requirements:** 10 Russian queries (4 easy / 4 medium / 2 hard) per P1S §40; qrels from anchors: 2–4 grade-2, 1–3 grade-1, 2–5 grade-0 per query; market-scope coverage (known/external × relevant/irrelevant); manifest v0.1.0 with counts.
- **Expected Output:** `benchmark/queries.csv`, `qrels.csv`, `benchmark_manifest.json`, `benchmark/README.md`.
- **Acceptance Criteria:** every query ≥1 grade-2 and ≥1 grade-0; qrels reference seed supplier IDs; generated by script (no manual edits).
- **Validation:** P1-014.
- **Out of Scope:** holdout split (P3-013).

### P1-013 — Seed validation script
- **Objective:** Enforce seed invariants.
- **Context:** P1S §31–32, [DOMAIN_MODEL §4](../../domain/DOMAIN_MODEL.md#4-invariants-enforced-by-validators-and-db-constraints), EC-29, BR-39.
- **Dependencies:** P1-009, P1-011.
- **Requirements:** `scripts/validate_seed.py`: JSONL parse, contract validation, FK offering→supplier, unique IDs, INN uniqueness rule, source-id uniqueness per source, completeness range, BR-39 description rule (warning), counts.
- **Expected Output:** script + CI step.
- **Acceptance Criteria:** output format per P1S §32 (`Suppliers: N valid … Errors: 0`); injected FK error is caught.
- **Validation:** tests with broken fixtures.
- **Out of Scope:** DB loading.

### P1-014 — Benchmark validation script
- **Objective:** Enforce benchmark invariants.
- **Context:** P1S §31–32, BR-40.
- **Dependencies:** P1-012.
- **Requirements:** `scripts/validate_benchmark.py`: unique query IDs, qrels→queries and →suppliers references, grades ∈ {0,1,2}, grade-2 coverage, distractor coverage (warning), manifest counts match files.
- **Expected Output:** script + CI step.
- **Acceptance Criteria:** prints `Queries: 10 · Qrels: N · Queries with grade-2: 10/10 · Invalid references: 0`.
- **Validation:** tests with broken fixtures.
- **Out of Scope:** metrics computation.
