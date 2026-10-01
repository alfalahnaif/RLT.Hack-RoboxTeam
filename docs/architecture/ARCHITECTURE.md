# System Architecture Proposal (analysis level)

> ### Hackathon Day-1 amendment (2026-10-01, ADR-H1)
> Stance unchanged: **modular monolith + PostgreSQL + Next.js + CLI + Docker Compose** (D-01…D-16 hold). Changes ([Baseline §12](../HACKATHON_EXECUTION_BASELINE.md#12-updated-architecture)):
> - Data layer: `raw_*` staging tables (COPY of the three CSVs, checksums) → canonical `procurement_lot`, `procurement_item`, `supplier_history`,
>   `supplier`, `supplier_profile`, `supplier_evidence`, `category_pool_health`; GIN FTS on item names; pgvector only if v2 P2-001 is kept.
> - Modules: add **`pool_health/`**; `procurement/` becomes core (ED-20 effectively accepted); `ingestion/` loads CSVs + curated enrichment files;
>   external adapters (§2 ГИСП/ФНС) are **offline curation**, not runtime integrations (HD-07). Entity resolution reduces to INN-exact (INN on every row).
> - API v2 (analysis level): `POST /recommendations` (lot_id | text, as_of), `GET /lots/{id}`, `GET /categories/{okpd2}/pool-health`,
>   `GET /suppliers/{id}`, `GET /meta`, `GET /health`; `POST /search` maps onto `/recommendations {text}`.
> - Performance: acceptance ≤ 10 s per recommendation (organizer), internal goal ≤ 5 s.

> Status: **Proposal.** Base decisions D-01…D-14 are accepted in the sources (Phase 0 §48–55, §76, §106).
> Items tagged `ED-xx` are this analysis's proposed engineering decisions ([DECISION_LOG](../decisions/DECISION_LOG.md)).
> Nothing here is implemented yet.

## 1. Architectural stance

**Modular monolith + PostgreSQL as the single data and search platform.** It is the simplest
architecture that satisfies all current requirements (hybrid search, explainability, benchmark,
offline demo) for a 4-person team in a 2-day event, while leaving a documented scale path.

> Build a Modular Monolith using PostgreSQL as the system of record and lexical/vector search platform.
> Search at the Product Offering level and aggregate back to Suppliers. Use Hybrid Retrieval to generate
> ~300–500 candidates, then a deterministic weighted ranker to produce the Top 20. Keep Match separate from
> Confidence and Risk. Add an Evidence layer so every result is explainable. Use an LLM only for query
> understanding and optional explanation wording. — *Phase 0 §106*

## 2. System boundaries (context)

```text
            ┌────────────────────────── Supplier Radar ──────────────────────────┐
 User ─────▶│ Next.js UI ──REST /api/v1──▶ FastAPI modular monolith ──▶ PostgreSQL │
 (browser)  │                                   │   ▲                (FTS, trgm, │
            │                                   │   │                 pgvector)  │
            │           Operator CLI ───────────┘   │ (ingest/rebuild/benchmark) │
            └───────────────────────────────────┬───┴────────────────────────────┘
                                                │ (batch, allowlisted, optional)
            Organizer dataset (files) · ГИСП · ФНС/ЕГРЮЛ · company catalogs · [LLM provider, optional]
```
- **Inside:** UI, API, domain modules, DB, CLI jobs, embedding model (local).
- **Outside:** data sources (pulled in batch), optional LLM (query parsing only).
- **Not integrated in MVP:** AIS ГЗ itself (standalone app; integration model is OQ-12).

## 3. Containers (Docker Compose — hackathon)

| Container | Tech | Responsibility |
|---|---|---|
| `frontend` | Next.js + TypeScript (+ Tailwind, per Design System) | Screens, client state; calls API only |
| `api` | FastAPI + Pydantic + SQLAlchemy; same image hosts CLI jobs | Domain modules, REST, CLI (`python -m app.cli …`) |
| `postgres` | PostgreSQL + `pgvector` + `pg_trgm` (+ `russian` FTS config) | System of record, search projection, vectors, search runs |

Explicitly **not** added: Redis, Celery, Elasticsearch/OpenSearch, Kubernetes, message brokers, graph DB (D-11, Phase 0 §54).
Embedding model weights are **baked into the `api` image** for offline operation (ED-17).

## 4. Backend module layout

```text
backend/app/
  api/            # routers (thin), DTO mapping, error handlers, request-id middleware
  query/          # D1  service, intent parser (rules), adapters/llm (optional)
  search/         # D4  pipeline orchestrator, branches, union, filters, aggregation, embeddings adapter, search_run
  ranking/        # D5  pure: features, scorer, contributions, reason codes, templates, config loader
  suppliers/      # D2  repositories, profile assembly, redirects
  evidence/       # D6  evidence repo, confidence, risk/quality flags
  procurement/    # D7  [ED-20] procurement records, experience, as_of filtering
  ingestion/      # D3  adapters (seed, organizer, gisp, fns…), normalization pipeline, ER, projection & embedding builders
  evaluation/     # D8  datasets loader, runner, metrics, temporal holdout, reports
  shared/         # D0  config, db, logging, errors, request context, text normalization, clock, ids
  cli.py          # entry points: ingest, rebuild, build-embeddings, benchmark, generate-seed
```
Each module owns `schemas` (DTOs), `service`, `repository`, domain logic (Phase 0 §50). Boundary rules: [DOMAINS §3](../domain/DOMAINS.md#3-module-boundary-rules).

### Repository layout (monorepo) — ED-11
```text
/backend   /frontend   /contracts   /data/seed   /benchmark   /scripts   /infra (compose, db init)   /docs
```
`/contracts`, `/data`, `/benchmark` are kept **separate from application code** (P1-001 §3).

## 5. Frontend / backend responsibilities

| Concern | Backend | Frontend |
|---|---|---|
| Validation | Authoritative (Pydantic) | UX-only mirror (length, required) |
| Parsing, retrieval, ranking, confidence, reason codes, explanation text | ✅ all | ❌ never recomputed |
| Score scaling for display | Returns 0–1 | Renders 0–100 integer (ED-01) |
| Filtering | Server-side re-query (ED-19 recommended) | Holds filter state in URL |
| Session state (results, compare tray) | SearchRun persisted by request_id (ED-02) | URL (`?q=&filters=`) + in-memory cache; restore without re-run |
| Localization of reason-code text | Provides codes + template params (+ default RU text) | Renders localized strings (OQ-22) |

## 6. API boundaries

Public REST `/api/v1`: `POST /search`, `GET /suppliers/{id}`, `GET /suppliers/{id}/evidence`,
`GET /meta/filters`, `POST /feedback` (Should), `GET /health`; `/debug/*` only with `DEBUG=true`.
Ranking is never a public endpoint. Details: [API_CONTRACTS.md](API_CONTRACTS.md).
Types for the frontend generated from FastAPI OpenAPI (ED-08); JSON Schema contracts in `/contracts` remain canonical for seed/benchmark files and are tested for equivalence with Pydantic DTOs.

## 7. Data layer

- **PostgreSQL** tables: canonical (`supplier`, `supplier_source_ref`, `product_offering`, `evidence`, `procurement_record`, `data_source`, `raw_source_record`), derived (`supplier_search_document`, `offering_embedding` ED-06), operational (`search_run`, `search_result` ED-02, `feedback`), ER (`possible_match`, `supplier_redirect`).
- Indexes: GIN on `tsvector`; GIN trgm on normalized title/name; HNSW (or IVFFlat) on embeddings; B-tree on FKs, `inn`, `ogrn`, `(source_name, external_id)`.
- **Migrations:** Alembic, forward-only during event; seed/demo snapshot via `pg_dump` (P8-001).
- **Temporal support (ED-04):** valid-time columns (`procurement_date`, `source_observed_at`, `first_seen_*`) + `as_of` parameter in repositories used by search/ranking.
- Attributes as JSONB; promote hot keys to columns only when proven.

## 8. Authentication & authorization

- MVP: **none** (D-12). Single anonymous actor object carried in request context (future-proofing).
- If publicly deployed: shared credential at reverse proxy + rate limit (ED-15).
- Operator actions via CLI only (no HTTP admin surface).
- Pilot: AuthN (OIDC/SSO), organizations, RBAC — see [USER_ROLES_AND_PERMISSIONS](../product/USER_ROLES_AND_PERMISSIONS.md).

## 9. State management

- **Server:** stateless request handling; durable state only in PostgreSQL. SearchRun snapshot = authoritative record of what the user saw (explanations reproducible after index changes).
- **Client:** URL as source of truth for query/filters; lightweight cache (e.g. TanStack Query or equivalent — decide in P1-003 with DS constraints) keyed by `request_id`; compare tray scoped to one `request_id` (EC-43). No global state framework unless the Design System requires one.

## 10. Validation

| Layer | Mechanism |
|---|---|
| Contract files (seed, benchmark) | JSON Schema 2020-12 + `scripts/validate_*.py` (P1-001 spec) |
| API input | Pydantic models with explicit limits (BR-28) |
| Ingestion | Adapter-level validation → per-record error report; invalid records quarantined, not dropped silently |
| LLM output | Parsed into SearchIntent schema; invalid → discard + fallback |
| DB | NOT NULL, FK, CHECK (grade ranges, digit patterns), UNIQUE (source keys, INN rule) |

## 11. Error handling

- Uniform error envelope (ED-07): `{ "error": { "code": "QUERY_TOO_SHORT", "message": "...", "details": {...}, "request_id": "..." } }`.
- Typed codes: `QUERY_TOO_SHORT`, `QUERY_TOO_LONG` [ER], `INVALID_FILTER`, `VALIDATION_ERROR` [ER], `SUPPLIER_NOT_FOUND`, `REQUEST_NOT_FOUND` [ER], `SEARCH_UNAVAILABLE`, `INTERNAL_ERROR` [ER].
- **Degradation over failure:** branch/LLM/external failures → `warnings[]` codes (`SEMANTIC_UNAVAILABLE`, `LLM_UNAVAILABLE`, `PARSER_FALLBACK`, `HISTORY_UNAVAILABLE`, `STALE_EXTERNAL_DATA`, `MULTI_ITEM_QUERY_DETECTED`, `NO_RESULTS`).
- `503 SEARCH_UNAVAILABLE` only when DB or all retrieval branches fail.
- No stack traces in responses; full detail in logs with `request_id`.

## 12. Observability & logging (ED-16)

- `request_id` generated (or accepted from `X-Request-ID`) by middleware; returned in body and header.
- Structured JSON logs (stdlib logging/structlog): request, per-stage timings, candidate counts per branch, versions (parser, ranking config, index, embedding model), warnings, error codes.
- Timings in the response (`retrieval_ms`, `ranking_ms`, `parse_ms`, `total_ms`).
- `/health`: api, db, search index (projection row count > 0, embedding coverage), model loaded.
- Metrics dashboards: **not** in MVP; benchmark report covers latency percentiles.

## 13. Security

- External content untrusted: stored as text, sanitized, length-capped; never rendered as HTML; never placed into LLM prompts in MVP (NFR-SEC-01/02).
- Adapters use allowlisted source definitions; no user-supplied URLs fetched.
- Input limits on all fields; enum validation; pagination caps.
- Secrets via env only; `.env.example` committed, `.env` ignored.
- CORS restricted to the frontend origin.
- Debug routes unregistered unless `DEBUG=true`.
- Dependency pinning (lock files). Personal data minimization for individual entrepreneurs (NFR-PRIV-01).

## 14. Testing strategy

| Level | Scope | Tools |
|---|---|---|
| Unit | normalization, parser rules, feature functions, scorer/renormalization, confidence, reason codes, metrics math, ER rules | pytest |
| Contract | JSON Schemas valid; seed/benchmark validate; Pydantic DTO ↔ JSON Schema equivalence; OpenAPI snapshot | pytest + jsonschema |
| Integration | repositories + FTS/trgm/pgvector queries against real Postgres (Docker) | pytest + compose DB |
| API | endpoints, validation errors, error envelope, degraded modes | pytest + httpx TestClient |
| Quality (offline eval) | benchmark runner: baseline vs hybrid; regression guard: hybrid nDCG@10 on dev must not drop vs last accepted run | evaluation CLI |
| E2E | UF-01, UF-03, UF-05, UF-06 | Playwright |
| Frontend unit | rendering of states, score formatting | Vitest |
| Resilience | LLM down, semantic down, external source down | pytest with fault injection |
Determinism test: same query twice → identical ordered output.

## 15. Deployment considerations

- **Hackathon:** Docker Compose (`frontend`, `api`, `postgres`), one command start, seed/demo snapshot restore, offline-safe mode, health check, fallback laptop.
- Target host (laptop vs VPS) — OQ-23. If public: reverse proxy (TLS, shared credential, rate limit).
- **Pilot path:** managed PostgreSQL, API container, frontend hosting, object storage (raw snapshots), worker (scheduled ingestion), monitoring (Phase 0 §55).
- **Scale path (only when proven):** OpenSearch for search bottleneck · queue+worker for async enrichment · Redis for multi-instance cache · LTR when labels suffice (Phase 0 §104).

## 16. Quality attribute fit

| Attribute | How the proposal delivers it | Guard against overengineering |
|---|---|---|
| Maintainable | Module boundaries, service interfaces, pure ranking | No DDD ceremony, no CQRS/event sourcing |
| Scalable | Candidate caps, projection table, batched ingestion, documented scale path | No distributed infra |
| Testable | Pure ranking/metrics, deterministic seed, benchmark as regression test | No test-infra beyond Docker Postgres |
| Secure | Untrusted content handling, validation, secrets, debug gating | No full RBAC/audit in MVP |
| Extensible | Adapters (sources, LLM, embeddings), versioned configs & contracts | No plugin framework |
| Production-ready (pilot) | Observability basics, migrations, health, reproducible builds | Production SaaS items deferred |
