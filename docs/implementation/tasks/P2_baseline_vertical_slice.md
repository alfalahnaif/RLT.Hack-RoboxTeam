# Phase P2 — Keyword Baseline Vertical Slice

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Implements source work package "P1-002". Exit: a user query travels Query → API → DB → Search → UI and returns real suppliers; baseline metrics are generated automatically.
> Rule: no AI optimization before this works (BR-41).

### P2-001 — Canonical DB schema v1
- **Objective:** Physical schema for canonical, source and projection tables.
- **Context:** [DOMAIN_MODEL](../../domain/DOMAIN_MODEL.md), [ARCHITECTURE §7](../../architecture/ARCHITECTURE.md#7-data-layer), ED-04, ED-05, ED-06, ED-22, BR-31.
- **Dependencies:** P1-005, P1-007.
- **Requirements:** tables `data_source`, `raw_source_record`, `supplier`, `supplier_source_ref`, `product_offering`, `procurement_record`, `evidence`, `supplier_redirect`, `possible_match` (latter three may be empty until P4/P5); valid-time columns (`source_observed_at`, `procurement_date`, `first_seen_in_procurement_at`); constraints (FK, CHECK digit patterns & ranges, UNIQUE source keys, partial unique INN); ORM models + repositories in owning modules; DTOs separate.
- **Expected Output:** Alembic revision, models, repositories.
- **Acceptance Criteria:** migration up/down clean; constraint tests reject invalid INN, dangling FK, duplicate source key.
- **Validation:** integration tests against compose Postgres.
- **Out of Scope:** projection tuning, embeddings table data (P3-002), search_run (P6-003).

### P2-002 — Seed loader CLI
- **Objective:** Load seed JSONL idempotently.
- **Context:** SF-02, EC-33, BR-31.
- **Dependencies:** P2-001, P1-013.
- **Requirements:** `cli ingest seed`: validate first (reuse validators), upsert by canonical ID, store raw records with checksum, summary output, non-zero exit on errors.
- **Expected Output:** ingestion adapter `ingestion/adapters/seed.py`.
- **Acceptance Criteria:** running twice yields identical row counts and IDs; counts equal file counts.
- **Validation:** integration test (load twice, compare).
- **Out of Scope:** organizer data (P4-002).

### P2-003 — Search projection & FTS rebuild
- **Objective:** Rebuildable `supplier_search_document` with Russian FTS.
- **Context:** DOMAIN_MODEL §2.7, SEARCH_AND_RANKING §1, EC-05, EC-28, R-23.
- **Dependencies:** P2-002.
- **Requirements:** `cli rebuild search_index`: full rebuild in a transaction; `tsvector` = weighted `russian` (title A, category B, description C) + `simple` config for Latin/alphanumeric tokens (brands/models); GIN index; carries `supplier_type`, `region_code`, `is_known_supplier`, `legal_status`, `index_version`; dedupe duplicate offerings.
- **Expected Output:** projection builder in `ingestion/`, migration for projection table.
- **Acceptance Criteria:** row count = searchable offerings; `index_version` updated; rebuild is repeatable.
- **Validation:** integration test; `EXPLAIN` shows GIN usage for `@@` query.
- **Out of Scope:** embeddings, trigram.

### P2-004 — Lexical retrieval branch
- **Objective:** Top-N offerings by FTS with a normalized 0–1 score.
- **Context:** BR-15, ED-10, EC-37, SEARCH_AND_RANKING §1.
- **Dependencies:** P2-003.
- **Requirements:** `websearch_to_tsquery`/`plainto_tsquery` on normalized query; `ts_rank_cd`; cap 200 (config); normalization `r/(r+k)` with configurable `k`; exact-title flag for `EXACT_TITLE_MATCH`; supports market_scope/supplier_type/region pre-filters.
- **Expected Output:** `search/branches/lexical.py` + repository query.
- **Acceptance Criteria:** Q001-style easy queries return anchor offerings in top positions; single-hit query does not get score 1.0 by construction.
- **Validation:** integration tests on seed.
- **Out of Scope:** semantic, trigram.

### P2-005 — Supplier aggregation & deterministic ordering
- **Objective:** One result per supplier with best offering; stable order.
- **Context:** BR-01, BR-14, ED-09, EC-27, EC-39.
- **Dependencies:** P2-004.
- **Requirements:** aggregate offering candidates → supplier (max score, argmax offering); tie-break score desc → supplier_id asc (confidence added later); `total_candidates` = distinct suppliers.
- **Expected Output:** `search/aggregation.py` (pure function).
- **Acceptance Criteria:** no duplicate suppliers; repeated runs identical; big-catalog supplier not boosted by count.
- **Validation:** unit tests incl. ties.
- **Out of Scope:** ranking features.

### P2-006 — POST /api/v1/search (baseline)
- **Objective:** Public search endpoint conforming to contract 0.1.0.
- **Context:** [API_CONTRACTS](../../architecture/API_CONTRACTS.md), BR-12, BR-13, BR-28, EC-01…03, EC-12, EC-13, EC-35, ED-07.
- **Dependencies:** P2-005, P1-008.
- **Requirements:** Pydantic request/response matching JSON Schemas; validation errors with typed codes; reason codes `LEXICAL_MATCH`/`EXACT_TITLE_MATCH` + `KNOWN_SUPPLIER|EXTERNAL_SUPPLIER`; filters market_scope/supplier_type/region; timings; warnings (`NO_RESULTS`); 503 on DB failure; `SearchService.search(request, mode="baseline")` as the single entry point.
- **Expected Output:** router + `search/service.py`.
- **Acceptance Criteria:** responses validate against `search_response.schema.json`; invalid inputs return the specified codes; zero results → 200 + warning.
- **Validation:** API tests + schema validation of responses.
- **Out of Scope:** parsed_query, ranking.

### P2-007 — Structured request logging & timings
- **Objective:** Observability for every search.
- **Context:** NFR-OBS-01/02, ED-16.
- **Dependencies:** P2-006.
- **Requirements:** one structured log line per search with request_id, query length (not necessarily full text — decide privacy), per-stage timings, candidate counts per branch, versions, warnings, status.
- **Expected Output:** logging in search service/middleware.
- **Acceptance Criteria:** log line parseable as JSON and contains all fields.
- **Validation:** test capturing logs.
- **Out of Scope:** persistence of runs (P6-003).

### P2-008 — Minimal results page
- **Objective:** Thin UI proving the vertical slice.
- **Context:** P0 §91, SCREENS S-01/S-02 (subset), DS mapping from P0-005.
- **Dependencies:** P2-006, P1-003.
- **Requirements:** query input + submit; list with supplier name, type, region, known/external, score (0–100), matched offering, reason codes; loading/empty/error states; DS components only.
- **Expected Output:** frontend route.
- **Acceptance Criteria:** query in browser shows seed suppliers from DB via API.
- **Validation:** manual + one Playwright smoke.
- **Out of Scope:** filters, profile, polish (P6).

### P2-009 — Benchmark runner & metrics library
- **Objective:** Reproducible evaluation CLI.
- **Context:** [EVALUATION](../../architecture/EVALUATION.md), SF-04, EC-50, EC-51, EC-53, BR-21.
- **Dependencies:** P2-005, P1-014.
- **Requirements:** `cli benchmark --mode baseline|hybrid --split dev|holdout|all`; in-process `SearchService`; metrics: nDCG@10, P@5, R@20, MRR, coverage, reason-code & evidence coverage, new-suppliers-discovered, latency P50/P95; version checks vs manifest; JSON report + markdown summary; unjudged results listed.
- **Expected Output:** `evaluation/` module, `reports/` output folder (git-ignored except accepted reports).
- **Acceptance Criteria:** metric functions match hand-computed fixtures; two runs produce identical metrics (latency excluded).
- **Validation:** unit tests on metrics; run on seed.
- **Out of Scope:** temporal holdout (P7-002).

### P2-010 — Baseline report v0.1.0
- **Objective:** Freeze the first measurable reference.
- **Context:** D-10, BR-42, P0 §90.
- **Dependencies:** P2-009.
- **Requirements:** run baseline on benchmark 0.1.0; commit report with versions; short analysis of failures (expected on hard queries).
- **Expected Output:** `benchmark/reports/baseline_v0.1.0.json` + summary.
- **Acceptance Criteria:** report reproducible from clean start.
- **Validation:** rerun and diff.
- **Out of Scope:** tuning.

### P2-011 — Vertical-slice end-to-end test
- **Objective:** Automated proof of the first milestone.
- **Context:** P0 §108 "one real procurement query goes through the entire product".
- **Dependencies:** P2-008, P2-010.
- **Requirements:** script: compose up → migrate → ingest seed → rebuild index → API query → UI shows results → benchmark runs.
- **Expected Output:** `scripts/e2e_slice.sh` (or Make target) + Playwright test.
- **Acceptance Criteria:** passes from clean volumes without manual steps.
- **Validation:** run in CI (if resources allow) or locally.
- **Out of Scope:** hybrid features.
