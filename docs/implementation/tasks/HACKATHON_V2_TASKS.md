# Roadmap v2 — Hackathon Tasks (authoritative from 2026-10-01)

> Defined by the owner on hackathon day 1 (ADR-H1, HD-10). Replaces the critical path of roadmap v1
> (v1 tasks are frozen and referenced as `v1/Pn-nnn` — mapping in [IMPLEMENTATION_ROADMAP §3](../IMPLEMENTATION_ROADMAP.md#3-mapping-roadmap-v1--v2)).
> Baseline: [HACKATHON_EXECUTION_BASELINE.md](../../HACKATHON_EXECUTION_BASELINE.md) · Data: [REAL_DATASET_ANALYSIS_2024_2025.md](../../analysis/REAL_DATASET_ANALYSIS_2024_2025.md).
> ⛔ Each task starts only on the owner's explicit command naming it. Status lives only in the [task index](../IMPLEMENTATION_ROADMAP.md#task-index-roadmap-v2).
> Where a v1 task already specified useful detail, it is cited as "reuse v1/…".

---

## P1 — Real-data foundation

### P1-001A — Actual dataset profiling
- **Objective:** Reproducible profiling of the three organizer CSVs.
- **Context:** Dataset analysis §1–10; HD-01; organizer briefing §5.
- **Dependencies:** — (repo skeleton parts of v1/P1-001 as needed: `/backend`, `/scripts`, `.gitignore` for `data/raw`).
- **Requirements:** one script (`scripts/profile_dataset.py`, Polars or stdlib) producing `reports/dataset_profile.json` + markdown; covers row counts, keys/orphans, platform × year, `is_winner` semantics, INN validity/types, ТРУ depth, OKPD2 depth, duplicates, replay feasibility, pool-health shortlist; no network.
- **Expected Output:** script + report; dataset analysis doc updated if any number differs.
- **Acceptance Criteria:** reproduces every number in the dataset analysis (or the doc is corrected); runtime < 5 min.
- **Validation:** run twice → identical JSON.
- **Out of Scope:** DB loading.

### P1-001B — Canonical mapping
- **Objective:** Map every CSV column to the v2 canonical model.
- **Context:** DOMAIN_MODEL §0; HD-02, HD-09; BR-37; reuse v1/P1-007 (JSON Schema rules).
- **Dependencies:** P1-001A.
- **Requirements:** mapping table (column → entity.field, type, nullability, transform, quality rule); `coverage_semantics` per platform (renamed from `record_semantics`, ADR-H1 A3); contracts v0.2.0 for `procurement_lot`, `procurement_item`, `supplier_history`, `supplier`, `supplier_profile`, `supplier_evidence`; open items logged.
- **Expected Output:** `contracts/*.schema.json` (v0.2.0) + `docs/domain/DATA_MAPPING.md`.
- **Acceptance Criteria:** every column mapped or explicitly dropped with reason; schemas validate sample rows from each file.
- **Validation:** `scripts/validate_contracts.py` + sample validation.
- **Out of Scope:** enrichment sources mapping (P3-002).

### P1-001C — Normalization rules
- **Objective:** One normalization library for text, INN, KPP, OKPD2, dates, prices.
- **Context:** BR-33, BR-34; dataset analysis §5–7; reuse v1/P1-010.
- **Dependencies:** P1-001B.
- **Requirements:** product text: NFC, lower, ё→е, footnote marks (`¹`), quotes, whitespace, `тип N` detection, number+unit tokens; INN: string, digits, length 10/12, checksum flag, `entity_type`, `inn_region_code`; KPP optional 9 digits; OKPD2: validate, levels (`XX`, `XX.XX`, `XX.XX.X`, `XX.XX.XX`, full), parent chain; booleans; prices as Decimal.
- **Expected Output:** `backend/app/shared/normalize.py` + table-driven tests.
- **Acceptance Criteria:** idempotent; malformed values flagged, never dropped; examples from the analysis pass.
- **Validation:** pytest.
- **Out of Scope:** stemming/synonyms (search config).

### P1-001D — PostgreSQL ingestion
- **Objective:** Load all three files into PostgreSQL, idempotently, with raw rows preserved.
- **Context:** HD-01/02, BR-31, ARCHITECTURE v2 §A; reuse v1/P1-002, P1-004, P1-005, P4-002, P4-003.
- **Dependencies:** P1-001C.
- **Requirements:** compose `postgres` (+ `pg_trgm`), Alembic baseline; `cli ingest organizer <dir>`: COPY → `raw_*` staging (+ checksum) → canonical tables via set-based SQL; dedupe 31 duplicate (lot, inn) pairs in canonical layer only; `supplier` from distinct INNs (UUIDv5); FTS columns/indexes on item names; ingestion report (counts reconcile with P1-001A).
- **Expected Output:** migrations, ingestion CLI, report.
- **Acceptance Criteria:** counts match profiling; second run changes nothing; full load time measured and documented.
- **Validation:** integration test on a slice + full timed run.
- **Out of Scope:** embeddings, enrichment.

### P1-001E — Temporal benchmark seed
- **Objective:** Real replay benchmark cases with weak labels.
- **Context:** HD-06; EVALUATION §0; BR-21, BR-22, BR-29; reuse v1/P4-009.
- **Dependencies:** P1-001D.
- **Requirements:** sample ЭМ lots (2025, winner, ≥ 2 participants, has items) stratified by OKPD2 section and difficulty; labels 2 winner / 1 participant / unjudged others; `cutoff = publish_date`; split by time (dev = 2025-01…06, holdout = 2025-07…12) + small ЭМ-2024 warm-up set; manifest with versions; golden lots excluded.
- **Expected Output:** `benchmark/replay/queries.csv`, `qrels.csv`, `manifest.json` (v1.0.0).
- **Acceptance Criteria:** ≥ 200 dev + ≥ 200 holdout cases (generated, reproducible seed); validators pass.
- **Validation:** benchmark validator; regeneration identical.
- **Out of Scope:** human grading (optional later).

### P1-001F — Golden demo cases
- **Objective:** Freeze the demo lots and their expected story.
- **Context:** Baseline §14; dataset analysis §9.
- **Dependencies:** P1-001D.
- **Requirements:** 4–6 lots (5718896, 5545252 or 5659204, 5542696 as hard case, + concentrated-category lot after P3-001); per lot: items, actual outcome, what the demo should show, risks; excluded from tuning.
- **Expected Output:** `benchmark/golden/golden_cases.yaml` + short demo note.
- **Acceptance Criteria:** each case replayable with `as_of`; owner approves the set.
- **Validation:** review.
- **Out of Scope:** demo script (P5).

### P1-002 — Historical keyword + OKPD2 baseline
- **Objective:** First end-to-end recommendation path and baseline metrics.
- **Context:** HD-03/04; baseline §7; reuse v1/P2-004…P2-006, P2-009, P2-010.
- **Dependencies:** P1-001D, P1-001E.
- **Requirements:** FastAPI skeleton (`/health`, error envelope, request_id); `POST /api/v1/recommendations` (lot_id | text, as_of); retrieval by FTS on item names + OKPD2 prefix; supplier score = awards count on retrieved lots (naive baseline) **and** OKPD2-only lookup baseline; benchmark runner (hit@5/10/20, MRR, nDCG@10 with 2/1 labels, latency).
- **Expected Output:** working endpoint + `reports/baseline_v1.json`.
- **Acceptance Criteria:** golden lot returns a shortlist end-to-end < 10 s; baseline metrics on dev generated automatically; deterministic.
- **Validation:** API tests, runner, repeat-run determinism.
- **Out of Scope:** weighted ranking, UI wiring.

## P2 — Retrieval & ranking

### P2-001 — Semantic retrieval
- **Objective:** Add item-text embeddings as a retrieval branch **only if it improves dev metrics**.
- **Context:** D-03; reuse v1/P3-001…P3-003; organizer §7 (no AI for its own sake).
- **Dependencies:** P1-002.
- **Requirements:** multilingual-e5 (or smaller) on **distinct normalized item names** (dedupe first); pgvector HNSW; similarity floor; offline weights.
- **Expected Output:** embeddings job, branch, comparison report.
- **Acceptance Criteria:** dev comparison vs P1-002 recorded; branch disabled by config if it does not help.
- **Validation:** benchmark runner.
- **Out of Scope:** LLM.

### P2-002 — Hybrid candidate generation
- **Objective:** Union of text, OKPD2, (semantic), context branches with caps.
- **Context:** Baseline §7.
- **Dependencies:** P1-002 (P2-001 optional).
- **Requirements:** branch caps in config; `as_of` on every branch; candidate counts per branch logged; warnings when a branch is unavailable.
- **Expected Output:** search pipeline module.
- **Acceptance Criteria:** recall@300 of winner on dev ≥ baseline; leakage test passes.
- **Validation:** tests + runner.
- **Out of Scope:** scoring.

### P2-003 — Explainable supplier ranking
- **Objective:** Weighted, renormalized, explainable ranking (baseline §8–9).
- **Context:** HD-05; BR-02, BR-05, BR-12; reuse v1/P3-009…P3-011, P5-007.
- **Dependencies:** P2-002.
- **Requirements:** features as in baseline §8; versioned `ranking_config`; contributions; reason codes v2; evidence lots; A-vs-B template; no cross-platform win rate.
- **Expected Output:** `ranking/` module, config 1.0.0, report vs baseline (dev).
- **Acceptance Criteria:** beats P1-002 on dev nDCG@10 (or the shortfall is reported honestly); 100% results with reason codes; deterministic.
- **Validation:** unit tests (pure), runner, determinism test.
- **Out of Scope:** tuning on holdout.

## P3 — Pool health & enrichment

### P3-001 — Supplier pool health
- **Objective:** Category pool metrics + verdict; choose demo expansion categories.
- **Context:** HD-08; baseline §10; dataset analysis §10.
- **Dependencies:** P1-001D.
- **Requirements:** metrics per OKPD2 (configurable level/window/as_of); verdict thresholds in config; precomputed table + on-demand for a target lot; category shortlist report; owner picks 1–2 demo categories.
- **Expected Output:** `pool_health/` module, `GET /categories/{okpd2}/pool-health`, report.
- **Acceptance Criteria:** numbers reconcile with the dataset analysis; verdict shown in recommendation response.
- **Validation:** tests on fixtures + report.
- **Out of Scope:** HHI in UI.

### P3-002 — Supplier role enrichment
- **Objective:** Assign `market_role` with basis and evidence for selected suppliers.
- **Context:** HD-09; baseline §6; BR-35, BR-38; OQ-08, OQ-38.
- **Dependencies:** P1-001B, P3-001.
- **Requirements:** evidence template (source, URL/ref, observed_at, claim); roles for top suppliers of golden lots + demo categories; `procurement_pattern` inference labelled *inferred*; curated file loaded by CLI.
- **Expected Output:** `data/enrichment/roles.*` + loader + role badges in API.
- **Acceptance Criteria:** every non-unknown role has ≥ 1 evidence item; no LLM-assigned role.
- **Validation:** validator on the curated file.
- **Out of Scope:** roles for all 44k suppliers.

### P3-003 — Targeted external supplier expansion
- **Objective:** ~10 verified external suppliers per demo category, pre-loaded.
- **Context:** HD-07; baseline §11; organizer §8–9.
- **Dependencies:** P3-001, P3-002 (evidence template).
- **Requirements:** discovery offline/before demo; identity verification (INN/OGRN, active); role + product evidence; not present in organizer data (else mark as known); stored with provenance; shown when pool verdict is CONCENTRATED/THIN.
- **Expected Output:** `data/enrichment/external_<okpd2>.*` + "sources used / records analyzed / new suppliers / roles" summary.
- **Acceptance Criteria:** ≥ 8–10 relevant, verified companies for the primary category; demo works offline.
- **Validation:** validator + manual spot check by a second team member.
- **Out of Scope:** live crawling.

## P4 — Integrated product UI

### P4 — Integrated product UI (single task group)
- **Objective:** Wire the existing UI (S-00…S-05, ED-27/28) to the live API and add the stakeholder levels.
- **Context:** Baseline §12; SCREENS.md; organizer §10; reuse v1/P6-005…P6-012 work.
- **Dependencies:** P1-002 (live path), P2-003, P3-001 (P3-003 for expansion).
- **Requirements:** lot-id entry + free text; shortlist with counts and "why"; pool-health panel + "expand" action (manager level); methodology/evidence view (analyst level); role badges with sources; live mode default for the demo, mock kept for development; no redesign, no new dependencies.
- **Expected Output:** updated screens; Playwright smoke of the golden path.
- **Acceptance Criteria:** golden cases run end-to-end in the UI; one interface, three levels of detail.
- **Validation:** E2E smoke, manual demo rehearsal.
- **Out of Scope:** new screens beyond the above, auth.

## P5 — Evaluation + demo freeze

### P5 — Evaluation + demo freeze (single task group)
- **Objective:** Final metrics, claims register, frozen offline demo.
- **Context:** BR-21, BR-23; reuse v1/P7-001, P7-002, P7-007, P8-001…P8-007.
- **Dependencies:** P4.
- **Requirements:** holdout run (once) baseline vs final; latency P50/P95; claims register; snapshot (`pg_dump`) + clean-start script; offline dry run; demo script ≤ 5 min with backups.
- **Expected Output:** `reports/final_evaluation.json`, claims register, demo script.
- **Acceptance Criteria:** every pitch number traceable to a report; two clean-start dry runs, one offline.
- **Validation:** dry runs.
- **Out of Scope:** new features after freeze.
