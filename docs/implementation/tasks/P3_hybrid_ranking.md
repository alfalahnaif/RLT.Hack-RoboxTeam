# Phase P3 — Hybrid Retrieval & Ranking

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Exit: benchmark runner compares Baseline vs Hybrid; hybrid beats baseline nDCG@10 on dev; deterministic; indexed P95 ≤ 2.5 s on seed.
> Spec: [SEARCH_AND_RANKING](../../architecture/SEARCH_AND_RANKING.md). Tune on **dev split only** (BR-21).

### P3-001 — Embedding provider adapter
- **Objective:** Pluggable embedding interface with e5 implementation.
- **Context:** NFR-MNT-05, ED-17, A-106, SEARCH_AND_RANKING §1 Embeddings.
- **Dependencies:** P1-002.
- **Requirements:** `EmbeddingProvider` protocol (`embed_queries`, `embed_passages`, `version`); e5 impl with `query:`/`passage:` prefixes, L2 normalization, batching; model weights baked into API image (offline); fake provider for tests.
- **Expected Output:** `search/embeddings/`, Dockerfile update.
- **Acceptance Criteria:** container embeds a query offline; version string stable; unit tests use fake provider.
- **Validation:** tests + container run with network disabled.
- **Out of Scope:** vector storage.

### P3-002 — Offering embeddings batch & vector index
- **Objective:** Precompute and index offering vectors.
- **Context:** ED-06, SF-03, R-12.
- **Dependencies:** P3-001, P2-003.
- **Requirements:** `offering_embedding` table (offering_id, embedding_version, content_hash, vector); `cli build_embeddings` embeds only new/changed content; HNSW index (cosine); projection exposes vector; coverage reported.
- **Expected Output:** migration, builder, CLI.
- **Acceptance Criteria:** 100% searchable offerings embedded; rerun without changes embeds 0.
- **Validation:** integration test; timing logged.
- **Out of Scope:** retrieval logic.

### P3-003 — Semantic retrieval branch
- **Objective:** Top-N offerings by vector similarity above a floor.
- **Context:** BR-15, ED-13, EC-36, NFR-REL-03.
- **Dependencies:** P3-002.
- **Requirements:** cap 200; configurable floor; score mapped `[floor,1]→[0,1]`; same pre-filters as lexical; failure → branch skipped + `SEMANTIC_UNAVAILABLE`.
- **Expected Output:** `search/branches/semantic.py`.
- **Acceptance Criteria:** hard query Q010 retrieves relevant camera offerings absent from lexical results; model failure does not fail the request.
- **Validation:** integration tests + fault injection.
- **Out of Scope:** union.

### P3-004 — Trigram fuzzy branch (Should)
- **Objective:** Recover typos and model-number variants.
- **Context:** EC-06, R-23.
- **Dependencies:** P2-004.
- **Requirements:** GIN trgm index on normalized title/brand/model; similarity threshold config; merged into lexical signal (max) per SEARCH_AND_RANKING.
- **Expected Output:** branch + migration.
- **Acceptance Criteria:** misspelled benchmark variants retrieve the correct anchors.
- **Validation:** tests with typo queries.
- **Out of Scope:** company-name fuzzy ER (P4-004).

### P3-005 — Rule-based query parser v1
- **Objective:** Deterministic SearchIntent extraction.
- **Context:** SEARCH_AND_RANKING §7, ED-03, BR-09, EC-04, EC-07, EC-09, EC-10, EC-14.
- **Dependencies:** P1-010.
- **Requirements:** dictionaries (categories/synonyms for seed categories, regions incl. СПб variants, supplier-type phrases); regex for numbers+units (inch/`"`/дюйм, cm→inch, ГБ/ТБ, л, шт → quantity); mandatory-constraint phrases; multi-item detection warning; `parser_version`; `field_origin`.
- **Expected Output:** `query/parser_rules.py`, dictionary files.
- **Acceptance Criteria:** all 10 benchmark queries produce the expected intents (golden file); unparseable input yields empty-but-valid intent.
- **Validation:** golden-file unit tests.
- **Out of Scope:** LLM (P5-008).

### P3-006 — Category retrieval branch
- **Objective:** Suppliers with offerings in the intent's category.
- **Context:** BR-15, EC-34.
- **Dependencies:** P3-005, P2-003.
- **Requirements:** cap 100 suppliers; branch skipped when intent has no category.
- **Expected Output:** `search/branches/category.py`.
- **Acceptance Criteria:** returns only matching-category suppliers; skipped cleanly otherwise.
- **Validation:** tests.
- **Out of Scope:** category mapping of organizer data (P4-006).

### P3-007 — Candidate union, dedupe & hard filters
- **Objective:** Merge branches into ≤ 500 supplier candidates and apply eligibility.
- **Context:** BR-03, BR-04, BR-06, BR-15, EC-14, EC-15, A-104.
- **Dependencies:** P3-003, P3-006 (P3-004 optional).
- **Requirements:** union by supplier keeping per-branch signals; caps from config; hard filters only for mandatory constraints + explicit UI filters; per-branch counts reported.
- **Expected Output:** `search/candidates.py`.
- **Acceptance Criteria:** region in query without "обязательно/местное присутствие" does not exclude other regions; inactive suppliers excluded; counts logged.
- **Validation:** unit + integration tests.
- **Out of Scope:** scoring.

### P3-008 — Seed extension: procurement & evidence fixtures [ER ED-24]
- **Objective:** Make experience/confidence testable before organizer data.
- **Context:** G-18, BR-20.
- **Dependencies:** P1-011, P2-001.
- **Requirements:** generator emits `procurement_records.jsonl` (dated, roles) and `evidence.jsonl` (types, observed_at, source) for anchors and some background suppliers; external suppliers mostly without history; loader extended; contracts added (MINOR).
- **Expected Output:** seed files, schemas, loader update.
- **Acceptance Criteria:** deterministic; validators pass; known suppliers have history, external mostly not.
- **Validation:** validators + load test.
- **Out of Scope:** real sources.

### P3-009 — Ranking feature extractor
- **Objective:** Compute the 8 features (0–1) with applicability.
- **Context:** SEARCH_AND_RANKING §3, BR-05, BR-08, ED-04 (`as_of`), G-20, G-21.
- **Dependencies:** P3-007, P3-008.
- **Requirements:** pure functions per feature over prepared inputs; query-level applicability; per-supplier missing data = 0; `as_of` respected by input loaders; definitions documented in code and SEARCH_AND_RANKING.
- **Expected Output:** `ranking/features.py`, input gatherer in `search/`.
- **Acceptance Criteria:** unit test per feature incl. edge values; deterministic.
- **Validation:** pytest.
- **Out of Scope:** confidence (P5-005).

### P3-010 — Weighted scorer, renormalization, contributions
- **Objective:** Match Score v1 with explainable contributions.
- **Context:** C-01, BR-02, BR-05, BR-14, ED-09, EC-38, EC-39.
- **Dependencies:** P3-009.
- **Requirements:** weights from versioned config (`ranking_config.yaml`, version 1.0.0); renormalize over applicable; contribution points summing to Match×100; tie-break; Top 100 ranked.
- **Expected Output:** `ranking/scorer.py`, config file.
- **Acceptance Criteria:** contributions sum equals score (±0.01); N/A features excluded; config change changes `ranking_version`.
- **Validation:** unit + property tests.
- **Out of Scope:** confidence tie-break (add in P5-005).

### P3-011 — Reason codes v1
- **Objective:** Deterministic reason codes from features.
- **Context:** BR-12, C-17, SEARCH_AND_RANKING §6.
- **Dependencies:** P3-010.
- **Requirements:** thresholds in config; canonical vocabulary only; always includes known/external code.
- **Expected Output:** `ranking/reasons.py`.
- **Acceptance Criteria:** 100% results non-empty; codes consistent with feature values.
- **Validation:** unit tests.
- **Out of Scope:** templated text (P5-007).

### P3-012 — Hybrid pipeline in /search
- **Objective:** Wire hybrid mode into the public endpoint.
- **Context:** SF-01, API_CONTRACTS evolution P3, SEARCH_AND_RANKING §8–9.
- **Dependencies:** P3-011.
- **Requirements:** `mode=hybrid` default in API, `baseline` for benchmark; response adds `parsed_query`, `match_score` (+`score` alias), `contributions`, `versions`, `ranking_ms`; `intent_overrides` if ED-19 accepted; contract bumped (MINOR).
- **Expected Output:** service/router updates, schema 0.2.0.
- **Acceptance Criteria:** responses validate; determinism test passes; P95 ≤ 2.5 s on seed.
- **Validation:** API + determinism + latency tests.
- **Out of Scope:** evidence fields.

### P3-013 — Benchmark v0.2.0 (20–30 queries, holdout)
- **Objective:** Larger seed benchmark with frozen holdout.
- **Context:** EVALUATION §2, BR-21, BR-40.
- **Dependencies:** P2-010.
- **Requirements:** 20–30 queries covering all categories and difficulties; `split` column (≈2/3 dev, 1/3 holdout); anchors added via generator; manifest 0.2.0.
- **Expected Output:** updated benchmark files.
- **Acceptance Criteria:** validators pass; holdout list recorded before any tuning.
- **Validation:** P1-014.
- **Out of Scope:** real benchmark (P4-009).

### P3-014 — Baseline vs hybrid comparison & dev tuning
- **Objective:** Show and document measurable improvement.
- **Context:** EVALUATION §6, R-28.
- **Dependencies:** P3-012, P3-013.
- **Requirements:** run both modes on dev; tune `k`, floor, caps, thresholds (not weights beyond documented v1 unless justified) on dev only; tuning log; one holdout run at the end.
- **Expected Output:** comparison report + tuning log.
- **Acceptance Criteria:** hybrid nDCG@10 > baseline on dev; Recall@20 guard respected; holdout result recorded honestly.
- **Validation:** reproducible reports.
- **Out of Scope:** LTR.
