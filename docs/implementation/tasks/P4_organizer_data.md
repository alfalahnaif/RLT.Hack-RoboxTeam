# Phase P4 — Organizer Data & Entity Resolution

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Triggered by dataset availability (event day 1); runs in parallel with P3 once P2-001 exists.
> Exit: ≥1 real dataset ingested, ER works, re-ingestion idempotent, real benchmark ≥ 20 queries (or documented shortfall).

### P4-001 — Organizer dataset EDA & mapping report
- **Objective:** Understand the real data before writing the adapter.
- **Context:** OQ-07, OQ-17, OQ-29, A-01…A-04, A-08, A-09, P1A-003/006, BR-37, R-02.
- **Dependencies:** dataset, P1-007.
- **Requirements:** notebook/script (Polars): files, row counts, fields, types, null rates, identifier coverage (INN/OGRN), text availability, classifications used, date ranges, duplicates, language; field → canonical mapping table (source-specific / canonical / search-only); list of new concepts.
- **Expected Output:** `docs/data/ORGANIZER_DATASET.md` (mapping report); assumptions updated.
- **Acceptance Criteria:** every canonical required field has a mapping or an explicit gap; assumptions A-01…A-04 marked Confirmed/Invalidated.
- **Validation:** Lead review.
- **Out of Scope:** code in `backend/`.

### P4-002 — Raw record store & organizer adapter
- **Objective:** Map organizer suppliers/offerings into canonical tables.
- **Context:** SF-02, BR-31, BR-37, NFR-PRIV-01, EC-24, EC-33, G-34.
- **Dependencies:** P4-001, P2-001.
- **Requirements:** `cli ingest organizer_dataset <path>`; raw payload + checksum; deterministic canonical IDs (UUIDv5 from source key); per-record error report & quarantine; personal-data minimization; offerings derived per mapping; contract changes via DECISION_LOG.
- **Expected Output:** `ingestion/adapters/organizer.py`, ingestion report.
- **Acceptance Criteria:** second run changes nothing; error rate reported; all loaded records satisfy DB constraints.
- **Validation:** integration test on a sample slice; full run timing.
- **Out of Scope:** ER merges (P4-004).

### P4-003 — Procurement records ingestion
- **Objective:** Load procurement history with valid time.
- **Context:** DOMAIN_MODEL §2.3, BR-29, OQ-30, G-22.
- **Dependencies:** P4-002.
- **Requirements:** records with role, date, category, region, buyer (optional), amount; link to supplier via source keys; `first_seen_in_procurement_at` computed.
- **Expected Output:** adapter extension + tests.
- **Acceptance Criteria:** every record has supplier_id and date (or is quarantined); counts reconciled with EDA.
- **Validation:** integration tests.
- **Out of Scope:** similarity search (P4-007).

### P4-004 — Entity resolution v1
- **Objective:** Deduplicate suppliers safely.
- **Context:** BR-32, ED-22, EC-20…EC-23, EC-25, R-03, R-18.
- **Dependencies:** P4-002.
- **Requirements:** L1 INN, L2 OGRN auto-merge; L3 normalized name + domain/address merge; L4 name+region+category → `possible_match` only; aliases kept; `supplier_redirect` on merge; source refs preserved; `AMBIGUOUS_ENTITY` inputs; ER report (merges per level).
- **Expected Output:** `ingestion/entity_resolution.py`, CLI `resolve_entities`.
- **Acceptance Criteria:** seed duplicate fixtures resolved as designed; no L4 destructive merge; redirects resolve old IDs.
- **Validation:** unit tests on fixtures + report review.
- **Out of Scope:** ML-based matching.

### P4-005 — Known/external classification
- **Objective:** Compute `is_known_supplier` from real data.
- **Context:** BR-19, BR-19a, ED-14, OQ-17, C-04.
- **Dependencies:** P4-003, P4-004.
- **Requirements:** rule per accepted ED-14/organizer answer; recomputed after ER; projection updated.
- **Expected Output:** classification job.
- **Acceptance Criteria:** counts reported; merged entity with any AIS source is known.
- **Validation:** tests.
- **Out of Scope:** new-to-category summary (P5-009).

### P4-006 — Category mapping (Should)
- **Objective:** Map source categories to canonical categories.
- **Context:** P0 §27, OQ-29, EC-34, G-23, R-13.
- **Dependencies:** P4-002.
- **Requirements:** use organizer classification as canonical if present; mapping table file; parser dictionaries extended to real categories; unmapped → `MISSING_CATEGORY`.
- **Expected Output:** mapping file + job.
- **Acceptance Criteria:** mapping coverage reported (% offerings mapped).
- **Validation:** report.
- **Out of Scope:** automated taxonomy learning.

### P4-007 — Historical branch & real experience feature (Should)
- **Objective:** Branch D and ProcurementExperience on real history.
- **Context:** SEARCH_AND_RANKING §1, §3, BR-08, BR-29, OQ-28, EC-26.
- **Dependencies:** P4-003, P3-009.
- **Requirements:** similar procurements (FTS/embedding over record titles) with `as_of`; cap 100 suppliers; experience feature from similar-record counts; pseudo-offerings from contract titles if OQ-28 accepted.
- **Expected Output:** `procurement/` service + branch.
- **Acceptance Criteria:** `as_of` excludes later records (test); branch skipped when no data.
- **Validation:** unit/integration tests.
- **Out of Scope:** reliability score.

### P4-008 — Ingestion at scale (Should)
- **Objective:** Keep ingestion/indexing within the event window.
- **Context:** NFR-SCL-02, R-12, R-16, OQ-11.
- **Dependencies:** P4-004.
- **Requirements:** batched COPY/upserts; progress output; measured throughput; embedding batch sizing; subset strategy documented if full corpus is infeasible.
- **Expected Output:** performance notes in ingestion README.
- **Acceptance Criteria:** full pipeline (ingest→ER→projection→embeddings) completes within agreed budget or subset documented.
- **Validation:** timed run.
- **Out of Scope:** workers/queues.

### P4-009 — Real benchmark v1.0.0
- **Objective:** Credible benchmark on organizer data.
- **Context:** EVALUATION §2–3, BR-21, BR-22, R-05, R-09.
- **Dependencies:** P4-005.
- **Requirements:** ≥ 20 queries (target 30) from real procurement texts; weak labels (winner/participants/similar) + human grading of top results from both modes (pooling); `cutoff_date`; dev/holdout split; manifest 1.0.0; kept separate from seed benchmark.
- **Expected Output:** `benchmark/real/…`.
- **Acceptance Criteria:** validators pass; judgment sources recorded per qrel.
- **Validation:** P1-014 validator on real set.
- **Out of Scope:** tuning on holdout.
