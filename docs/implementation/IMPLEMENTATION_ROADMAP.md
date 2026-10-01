# Implementation Roadmap

> ⛔ **No task may start without an explicit go-ahead from the project owner naming it.**
> **Current plan: Roadmap v2 (Part A) — authoritative from 2026-10-01 (hackathon day 1, ADR-H1 / HD-10).**
> Roadmap v1 (Part B) is **frozen history**: its task IDs are referenced as `v1/Pn-nnn` and never reused silently.
> Baseline: [HACKATHON_EXECUTION_BASELINE.md](../HACKATHON_EXECUTION_BASELINE.md) · Task definitions: [tasks/HACKATHON_V2_TASKS.md](tasks/HACKATHON_V2_TASKS.md).

# Part A — Roadmap v2 (hackathon, real data)

## 1. Phase overview (v2)

| Phase | Name | Goal | Exit criterion |
|---|---|---|---|
| **P1** | Real-data foundation | Organizer CSVs profiled, mapped, normalized, loaded; replay benchmark + golden cases; **first end-to-end baseline** | P1-002: golden lot → shortlist end-to-end < 10 s; baseline metrics on dev generated automatically |
| **P2** | Retrieval & ranking | Hybrid candidates + explainable weighted ranking that beats the baseline on dev | P2-003 report vs P1-002 (honest if not better); 100% reason codes; deterministic |
| **P3** | Pool health & enrichment | Category pool health; roles with evidence; ~10 verified external suppliers per demo category, pre-loaded | Concentrated category demo works offline with sourced roles |
| **P4** | Integrated product UI | Existing UI wired to the live API; specialist / manager / analyst levels in one interface | Golden cases run end-to-end in the UI |
| **P5** | Evaluation + demo freeze | Holdout run, claims register, snapshot, offline dry run | Two clean-start dry runs, one offline; every pitch number traceable |

Order and critical path: `P1-001A → B → C → D → E/F → P1-002 → P2-002 → P2-003 → P3-001 → (P3-002 ∥ P3-003) → P4 → P5`; P2-001 (semantic) is optional and kept only if it improves dev metrics.
Parallel tracks (4 people, A-102): **Data** P1-001A…E, P3-001 · **Search/ranking** P1-002, P2-* , evaluation · **Enrichment** P3-002/003 (starts once P3-001 picks categories; evidence template can start immediately) · **UI** P4 (live-API wiring; no redesign; UI = 10 pts, not the time sink).

## 2. Cut list (v2, in order)
1. P2-001 semantic retrieval (keep text + OKPD2 + history)
2. `procurement_value_similarity` and `marketplace_participation` features
3. Role enrichment of known suppliers (keep external candidates only)
4. Second demo expansion category
5. Analyst methodology page → static section in the pitch
Never cut: end-to-end path, OKPD2/keyword baseline, replay metrics, reason codes + evidence lots, pool health for the demo category, ≥ 8 verified external suppliers, offline demo.

## 3. Mapping roadmap v1 → v2

| v1 (frozen) | v2 | Note |
|---|---|---|
| v1/P0-001…P0-004, P0-006, P0-007 | absorbed into ADR-H1 + this baseline | Remaining open decisions are organizer questions OQ-33…OQ-44 |
| v1/P0-005 Design System plan | kept (Done) | ED-25…ED-28 still valid |
| v1/P1-001…P1-006 (repo, backend, frontend, compose, migrations, CI) | P1-001A (repo bits), P1-001D (compose, migrations), P1-002 (backend skeleton) | Frontend skeleton already exists |
| v1/P1-007…P1-009 contracts | P1-001B (contracts v0.2.0 for real entities) | |
| v1/P1-010 normalization | P1-001C | Extended to INN/OKPD2 |
| v1/P1-011…P1-014 synthetic seed + seed benchmark | **Superseded** (HD-01) — optional unit-test fixtures only | |
| v1/P2-001…P2-011 keyword baseline slice | P1-001D (schema) + P1-002 (baseline on real data) | |
| v1/P3-001…P3-003 embeddings/semantic | P2-001 | Optional |
| v1/P3-004…P3-007 trigram/parser/category/union | P2-002 (+ normalization in P1-001C) | Category = OKPD2 hierarchy |
| v1/P3-008 seed history/evidence fixtures | **Superseded** (real history) | |
| v1/P3-009…P3-011 features/scorer/reasons | P2-003 | New feature set (baseline §8) |
| v1/P3-012…P3-014 hybrid pipeline + seed benchmark compare | P2-002/P2-003 + P1-001E | |
| v1/P4-001 EDA | P1-001A (preliminary analysis done 2026-10-01) | |
| v1/P4-002, P4-003, P4-008 adapter, procurement records, scale | P1-001D | |
| v1/P4-004 entity resolution | P1-001D (INN-exact only); fuzzy ER not needed for organizer data (INN on every row) | |
| v1/P4-005 known/external | P1-001D + P3-003 | Known = has history before `as_of` |
| v1/P4-006 category mapping | P1-001C (OKPD2 levels) | |
| v1/P4-007 historical branch | P1-002 / P2-002 (core, not "Should") | |
| v1/P4-009 real benchmark | P1-001E | Replay, not hand-made qrels |
| v1/P5-001 evidence storage | P1-001B + P3-002 | |
| v1/P5-002…P5-004 live external adapters | P3-002/P3-003 **precomputed curated** enrichment (HD-07) | |
| v1/P5-005, P5-006 confidence & risk flags | P2-003 (minimal) + P3-002 | Keep separate from Match |
| v1/P5-007 templates, A-vs-B | P2-003 | |
| v1/P5-008 LLM parser | Cut (Could) | |
| v1/P5-009 market summary | P3-001 (pool health) + P4 | |
| v1/P6-001…P6-012 product UI | P4 | UI already built on mock API carries over |
| v1/P7-*, v1/P8-* | P5 | |

<a id="task-index"></a>
## Task index (roadmap v2)

Status values: `Not started · In progress · In review · Done · Blocked · Cut`. **This table is the only place v2 task status is tracked.**

| ID | Title | Depends on | Status |
|---|---|---|---|
| P1-001A | Actual dataset profiling | — | **Done (2026-10-01)** — `scripts/profile_dataset.py` → `reports/dataset_profile.json/.md`; 2 runs byte-identical; 130–250 s; docs corrected where numbers differed |
| P1-001B | Canonical mapping | P1-001A | **Done (2026-10-01)** — contracts v0.2.0 (6 entities + common), `docs/domain/DATA_MAPPING.md`, `scripts/validate_contracts.py`; fixtures + 29 negative cases + full raw-row validation PASS on hash-verified restored files (DATA_MAPPING §9) |
| P1-001C | Normalization rules | P1-001B | **Done (2026-10-01)** — `backend/app/shared/normalize.py` v1.0.0; 221 pytest cases pass; `scripts/verify_normalization.py` 27/27 real-data checks, 0 reference mismatches (DATA_MAPPING §10) |
| P1-001D | PostgreSQL ingestion | P1-001C | **Done (2026-10-01)** — Docker Compose (postgres 16 + backend), Alembic `0001_organizer_schema`, `python -m app.cli ingest organizer /data/raw`; full load 865 s, reconciliation 35/35 PASS, idempotent re-run verified, 234 tests pass (DATA_MAPPING §11) |
| P1-001E | Temporal benchmark seed | P1-001D | **Done (2026-10-01)** — `benchmark/replay/` (300 dev / 300 holdout / 50 warm-up, 2,207 dev+holdout qrels), `python -m app.cli benchmark generate|validate`; 15/15 checks incl. leakage + byte-identical regeneration; report `reports/benchmark_seed_report.*` |
| P1-001F | Golden demo cases | P1-001D | **Done (2026-10-01)** — `benchmark/golden/golden_cases.json` (3 primary: 5718896, 5545252, 5542696; 2 backup: 6022687, 5612123); 9/9 checks incl. DB-fact match + no replay overlap |
| P1-002 | Historical keyword + OKPD2 baseline | P1-001D, P1-001E | **Done (2026-10-01)** — `app/search/` + `recommend lot` / `evaluate baseline`; DEV: winner coverage 89.7%, W-R@10 65.3%, MRR 0.389, nDCG@10 0.506; p95 2.9 s; migrations 0002/0003; holdout sealed (reports/p1_002_baseline.*) |
| P2-001 | Semantic retrieval (optional) | P1-002 | Not started |
| P2-002 | Hybrid candidate generation | P1-002 | Not started |
| P2-003 | Explainable supplier ranking | P2-002 | **Done (2026-10-01)** — ranking-only study on DEV (retrieval frozen): diagnosis + 9 configs, accepted `C2 relevance-dominant` (Δ weighted nDCG@10 +0.016, CI90 [+0.005, +0.027]); now `DEFAULT_CONFIG`; holdout sealed (reports/p2_003_*) |
| P3-001 | Supplier pool health | P1-001D | Not started — preliminary category shortlist in dataset analysis §10 |
| P3-002 | Supplier role enrichment | P1-001B, P3-001 | Not started |
| P3-003 | Targeted external supplier expansion | P3-001, P3-002 | Not started |
| P4 | Integrated product UI | P1-002, P2-003, P3-001 | Partly done — UI S-00…S-05 built on mock API (v1/P6-005…P6-011); live wiring + stakeholder levels pending |
| P5 | Evaluation + demo freeze | P4 | Not started |

---

# Part B — Roadmap v1 (frozen, historical — pre-hackathon, 2026-09-28)

> Kept for history and for reusable task detail. **Do not execute v1 tasks**; refer to them as `v1/Pn-nnn`.
> Superseded by Part A (ADR-H1). Statuses below are as of 2026-10-01 and are no longer updated.
> Original v1 header: *"No phase may start without an explicit go-ahead from the project owner. Current state: Phase P0 ready to execute (decision tasks only). Phase structure resolves C-02/C-13 (proposed ED-21). Timeboxes follow P0 §97."*


## v1-1. Phase overview

| Phase | Name | Goal | Maps to sources | Timebox (target) |
|---|---|---|---|---|
| **P0** | Implementation Readiness | Close blocking decisions; no code | P0 §77 questions, STR §14–15 | 0.5 day (before coding) |
| **P1** | Engineering Foundation & Contracts | Runnable empty stack + stable contracts, seed and benchmark v0.1 | WP "P1-001" spec + Epic E0 | ~2–3 h |
| **P2** | Keyword Baseline Vertical Slice | One real query travels Query→API→DB→Search→UI; baseline metrics exist | WP "P1-002", Phase 1 §91 | ~2 h |
| **P3** | Hybrid Retrieval & Ranking | Semantic + lexical + category → deterministic Match Score; beats baseline on dev | Phase 2 §92, E3, E4 | ~5–6 h |
| **P4** | Organizer Data & Entity Resolution | Real data ingested, deduplicated, known/external classified; real benchmark | E1-T2…T4, E2 | ~3 h (event day 1, parallel) |
| **P5** | Evidence, Confidence & Market Expansion | Top 5 have reason + evidence + confidence; ≥1 external source | Phase 3 §93, E7 | ~2–3 h |
| **P6** | Product Experience | Four screens on the Design System | Phase 4 §94, E5, E6 | ~3 h |
| **P7** | Evaluation & Hardening | Prove value; security & resilience | Phase 5 §95, E8 | ~2–3 h |
| **P8** | Demo & Release Readiness | Clean-start, offline-safe, rehearsed demo | Phase 6 §96, E9 | ~2 h |

Calendar (if pre-event work is allowed — OQ-01): P0 on 09-28/29 · P1–P3 on 09-29/30 (dry run with public/seed data on 09-29 per STR §14) · P4–P6 on 10-01 · P7–P8 on 10-02.
If not allowed: P0 before the event; P1–P2 event morning; P3 + P4 in parallel; P5–P6 afternoon; P7–P8 day 2.

## v1-2. Phase details

### P0 — Implementation Readiness
- **Goal:** Every blocking question/conflict/decision for P1–P3 is answered or explicitly assumed.
- **Scope:** approve KB, resolve C-xx, accept ED-xx, confirm rules & source legality, DS plan, runtime choices, team allocation. **No code.**
- **Dependencies:** this knowledge base.
- **Deliverables:** updated CONFLICTS/DECISION_LOG/OPEN_QUESTIONS/ASSUMPTIONS; DS mapping in SCREENS.md; team plan.
- **Exit criteria:** blocking set in [REQUIREMENTS_REVIEW §4](../analysis/REQUIREMENTS_REVIEW.md#4-decisions-required-before-implementation-blocking-set) is resolved for P1–P3; owner gives explicit go-ahead.

### P1 — Engineering Foundation & Contracts
- **Goal:** `docker compose up` starts an empty but healthy stack; contracts, seed and benchmark v0.1.0 validate.
- **Scope:** repo, backend/frontend skeletons, compose, migrations baseline, CI, 5–6 JSON Schemas, normalization lib, deterministic seed generator, benchmark seed, validators.
- **Dependencies:** P0 (ED-01, ED-05, ED-11, ED-12, ED-23 accepted; C-03, C-05, C-18 resolved; P0-005 for P1-003).
- **Deliverables:** `/backend /frontend /contracts /data/seed /benchmark /scripts /infra`, CI green.
- **Exit criteria:** P1S §50 DoD fully checked; `/api/v1/health` returns ok in compose; seed regenerated twice → identical files (hash).

### P2 — Keyword Baseline Vertical Slice
- **Goal:** First measurable end-to-end query.
- **Scope:** canonical schema (with valid-time), seed loader, projection+FTS, lexical branch, aggregation, `POST /search` (baseline), logging, minimal results page, benchmark runner, baseline report.
- **Dependencies:** P1.
- **Deliverables:** working search on seed data; `evaluation_report.json` (baseline, benchmark 0.1.0).
- **Exit criteria:** user enters a query and sees real suppliers from the DB (P0 §91); baseline metrics generated automatically; e2e test green.

### P3 — Hybrid Retrieval & Ranking
- **Goal:** Hybrid Search v1 with explainable deterministic ranking.
- **Scope:** embedding adapter & batch, semantic/trigram/category branches, rule-based parser, union+hard filters, seed extension (history/evidence fixtures), 8 features, scorer+renormalization+contributions, reason codes, hybrid `/search`, benchmark v0.2.0 with holdout, comparison.
- **Dependencies:** P2; ED-03/04/09/10/13 accepted; C-01 resolved.
- **Deliverables:** hybrid mode; ranking config 1.0.0; comparison report (dev).
- **Exit criteria:** runner compares Baseline vs Hybrid (P0 §92); hybrid nDCG@10 > baseline on dev; determinism test passes; indexed P95 ≤ 2.5 s on seed.

### P4 — Organizer Data & Entity Resolution
- **Goal:** Real dataset searchable with deduplicated suppliers and history.
- **Scope:** EDA & mapping, raw store + adapter, procurement records, ER L1–L4 + redirects, known/external, category mapping, historical branch, scale checks, real benchmark v1.0.0.
- **Dependencies:** P2-001 schema, P1-010 normalization; dataset availability; OQ-17/29 answers.
- **Deliverables:** ingestion report; ER report; real benchmark files.
- **Exit criteria:** MVP data gates: ≥1 real dataset ingested, ER works (tests + report), re-ingestion idempotent; real benchmark ≥ 20 queries (or documented shortfall).

### P5 — Evidence, Confidence & Market Expansion
- **Goal:** Evidence-backed search.
- **Scope:** evidence store, source adapter framework, ГИСП adapter, ФНС/ЕГРЮЛ adapter (P1 priority), confidence, flags, templates + A-vs-B, market summary, optional LLM parser.
- **Dependencies:** P3 scorer, P4 ER (for matching external records), P0-002 legal clearance.
- **Deliverables:** `/search` returns confidence, risk flags, top evidence, explanation, market summary.
- **Exit criteria:** Top 5 contain Reason + Evidence + Confidence (P0 §93) — measured: 100% reason codes, ≥ 90% evidence; ≥1 external source used; LLM failure test passes.

### P6 — Product Experience
- **Goal:** Hackathon-quality interface on the Design System.
- **Scope:** profile/meta/search-run APIs, typed client, S-01…S-03 (Must), S-04 compare & feedback (Should), states & a11y, E2E.
- **Dependencies:** P0-005 DS mapping; P5 response fields (can mock while P5 finishes).
- **Deliverables:** four screens; Playwright E2E for UF-01/03/05(/06).
- **Exit criteria:** UF-01, UF-03, UF-05 pass E2E from a clean start; US-08 verified; market expansion visible.

### P7 — Evaluation & Hardening
- **Goal:** Prove value; make it safe and robust.
- **Scope:** frozen holdout runs, temporal holdout, latency profiling, error analysis, security review, resilience tests, final report & claims register.
- **Dependencies:** P3–P6.
- **Deliverables:** `evaluation_report.json` (final), claims register, security checklist.
- **Exit criteria:** no pitch claim without a metric (P0 §95); success targets reported honestly (met or not); resilience tests green.

### P8 — Demo & Release Readiness
- **Goal:** Reliable demo from clean startup without manual fixes.
- **Scope:** clean start + snapshot, offline mode, deployment (+ protection), demo script & fallback queries, health/smoke, pitch technical assets, freeze & dry run.
- **Dependencies:** P7.
- **Exit criteria:** two consecutive clean-start dry runs of UF-09 succeed, one of them offline (P0 §96).

## v1-3. Legacy ID mapping (C-13)

| Source ID | Now |
|---|---|
| WP **P1-001** Canonical Data + Benchmark Seed (spec) | P1-007 … P1-014 (+ P1-001 repo) |
| WP **P1-002** Keyword Baseline Vertical Slice | Phase P2 (P2-001 … P2-011) |
| E0-T1…T4 | P1-001, P1-004, P1-002/P1-004 config, P1-006 |
| E1-T1 / T2 / T3 / T4 / T5 / T6 | P2-001 / P4-002 / P1-010 / P4-004 / P2-003 / P3-002 |
| E2-T1…T4 | P1-012, P3-013, P2-009, P3-013 (+ P4-009 real) |
| E3-T1…T5 | P2-004, P3-004, P3-003, P3-007, P3-007 |
| E4-T1…T5 | P3-009, P3-010, P5-005, P5-006, P3-010 |
| E5 (API) | P2-006, P6-001, P6-002, P6-001, P6-010 |
| E6 (UI) | P2-008, P6-005…P6-009, S-05 deferred |
| E7 (market expansion) | P5-002, P5-003, P4-005, P5-001, P5-004, FR-16 deferred |
| E8 (evaluation) | P2-009, P7-001…P7-004 |
| E9 (demo) | P8-001…P8-007 |

## 4. Parallel tracks (4-person team, A-102)

| Track | Owner role | Main tasks |
|---|---|---|
| Integration & contracts | Tech/Product Lead | P0-*, P1-001, P1-007/008, P2-006, P3-012, P7-007, P8-* ; daily end-to-end check (R-20) |
| Search & evaluation | Data/ML | P1-011/012, P2-004, P2-009/010, P3-001…P3-014, P4-009, P7-001…004 |
| Data & backend | Backend/Data | P1-002, P1-004/005, P2-001…003, P4-*, P5-001…004, P6-001…003 |
| Product & UI | Frontend/Product | P0-005, P1-003, P2-008, P6-004…P6-012, P8-004/006 |

## v1-5. Cut list (pre-agreed, in order, if time runs out — R-30)
1. S-05 search history, CSV export (already deferred)
2. P5-008 LLM parser (rule-based stays)
3. P6-010 feedback
4. P5-004 second external source (keep one)
5. P6-009 compare → demo shows two profiles instead (C-08)
6. P3-004 trigram
7. P4-007 historical branch (experience via simple category/text overlap instead)
Never cut: baseline, benchmark runner, reason codes, evidence for Top 5, known/external, offline-safe demo.

---

## Task index — roadmap v1 (frozen)

Status values as recorded on 2026-10-01 (frozen).
Priority: M = Must · S = Should · C = Could.

| ID | Title | Pri | Depends on | Status |
|---|---|:-:|---|---|
| P0-001 | Approve knowledge base & resolve conflicts | M | — | Not started |
| P0-002 | Verify event rules & external-source legality | M | — | Not started |
| P0-003 | Organizer question pack & answer capture | M | — | Not started |
| P0-004 | Accept/reject proposed engineering decisions | M | P0-001 | Not started |
| P0-005 | Design System integration plan | M | P0-001 | Done (2026-10-01) — locale ED-25, DS ED-26, mapping + gaps in SCREENS.md, UI decisions ED-27/ED-28 |
| P0-006 | Runtime environment decisions | M | P0-002 | Not started |
| P0-007 | Team allocation & event timebox plan | M | P0-004 | Not started |
| P1-001 | Repository skeleton & VCS conventions | M | P0-004 | Not started |
| P1-002 | Backend application skeleton | M | P1-001 | Not started |
| P1-003 | Frontend application skeleton | M | P1-001, P0-005 | Partly done — Next.js app, DS, i18n, API base URL env, S-01, health indicator exist; remaining: Vitest |
| P1-004 | Docker Compose stack | M | P1-002 | Not started |
| P1-005 | Database migration baseline | M | P1-004 | Not started |
| P1-006 | CI baseline | S | P1-002, P1-003 | Not started |
| P1-007 | Entity contracts (supplier, offering, data_source) | M | P1-001 | Not started |
| P1-008 | Search & error contracts | M | P1-007 | Not started |
| P1-009 | Contract validation script | M | P1-007, P1-008 | Not started |
| P1-010 | Text & name normalization library | M | P1-002 | Not started |
| P1-011 | Deterministic seed generator | M | P1-007, P1-010 | Not started |
| P1-012 | Benchmark seed v0.1.0 | M | P1-011 | Not started |
| P1-013 | Seed validation script | M | P1-009, P1-011 | Not started |
| P1-014 | Benchmark validation script | M | P1-012 | Not started |
| P2-001 | Canonical DB schema v1 | M | P1-005, P1-007 | Not started |
| P2-002 | Seed loader CLI | M | P2-001, P1-013 | Not started |
| P2-003 | Search projection & FTS rebuild | M | P2-002 | Not started |
| P2-004 | Lexical retrieval branch | M | P2-003 | Not started |
| P2-005 | Supplier aggregation & deterministic ordering | M | P2-004 | Not started |
| P2-006 | POST /api/v1/search (baseline) | M | P2-005, P1-008 | Not started |
| P2-007 | Structured request logging & timings | M | P2-006 | Not started |
| P2-008 | Minimal results page | M | P2-006, P1-003 | Not started |
| P2-009 | Benchmark runner & metrics library | M | P2-005, P1-014 | Not started |
| P2-010 | Baseline report v0.1.0 | M | P2-009 | Not started |
| P2-011 | Vertical-slice end-to-end test | M | P2-008, P2-010 | Not started |
| P3-001 | Embedding provider adapter | M | P1-002 | Not started |
| P3-002 | Offering embeddings batch & vector index | M | P3-001, P2-003 | Not started |
| P3-003 | Semantic retrieval branch | M | P3-002 | Not started |
| P3-004 | Trigram fuzzy branch | S | P2-004 | Not started |
| P3-005 | Rule-based query parser v1 | M | P1-010 | Not started |
| P3-006 | Category retrieval branch | M | P3-005, P2-003 | Not started |
| P3-007 | Candidate union, dedupe & hard filters | M | P3-003, P3-006 | Not started |
| P3-008 | Seed extension: history & evidence fixtures | M | P1-011, P2-001 | Not started |
| P3-009 | Ranking feature extractor | M | P3-007, P3-008 | Not started |
| P3-010 | Weighted scorer, renormalization, contributions | M | P3-009 | Not started |
| P3-011 | Reason codes v1 | M | P3-010 | Not started |
| P3-012 | Hybrid pipeline in /search | M | P3-011 | Not started |
| P3-013 | Benchmark v0.2.0 (20–30 queries, holdout) | M | P2-010 | Not started |
| P3-014 | Baseline vs hybrid comparison & dev tuning | M | P3-012, P3-013 | Not started |
| P4-001 | Organizer dataset EDA & mapping report | M | dataset, P1-007 | Not started |
| P4-002 | Raw record store & organizer adapter | M | P4-001, P2-001 | Not started |
| P4-003 | Procurement records ingestion | M | P4-002 | Not started |
| P4-004 | Entity resolution v1 | M | P4-002 | Not started |
| P4-005 | Known/external classification | M | P4-003, P4-004 | Not started |
| P4-006 | Category mapping | S | P4-002 | Not started |
| P4-007 | Historical branch & real experience feature | S | P4-003, P3-009 | Not started |
| P4-008 | Ingestion at scale | S | P4-004 | Not started |
| P4-009 | Real benchmark v1.0.0 | M | P4-005 | Not started |
| P5-001 | Evidence storage & traceability | M | P2-001 | Not started |
| P5-002 | External source adapter framework | M | P5-001, P0-002 | Not started |
| P5-003 | ГИСП manufacturer registry adapter | M | P5-002, P4-004 | Not started |
| P5-004 | Legal identity enrichment adapter (ФНС/ЕГРЮЛ) | S | P5-002, P4-004 | Not started |
| P5-005 | Confidence score & profile completeness | M | P5-001, P3-010 | Not started |
| P5-006 | Risk & data-quality flags | M | P5-005 | Not started |
| P5-007 | Explanation templates & A-vs-B | M | P3-011 | Not started |
| P5-008 | Optional LLM query parser adapter | C | P3-005, P0-006 | Not started |
| P5-009 | Market summary in search response | S | P4-005, P3-012 | Not started |
| P6-001 | Supplier profile & evidence endpoints | M | P5-006 | Not started |
| P6-002 | Filters metadata endpoint | S | P2-001 | Not started |
| P6-003 | Search-run persistence & retrieval | M | P3-012 | Not started |
| P6-004 | Typed API client from OpenAPI | M | P2-006, P1-003 | Not started |
| P6-005 | S-01 Search screen & editable intent | M | P6-004, P0-005 | In progress — UI built on mock API (2026-10-01); remaining: live API wiring, Vitest/Playwright |
| P6-006 | S-02 Results screen, filters & summary | M | P6-005, P5-009 | In progress — UI built on mock API (2026-10-01); remaining: live API wiring, Vitest/Playwright |
| P6-007 | Why-matched panel | M | P6-006, P5-007 | In progress — UI built on mock API (2026-10-01); remaining: live API wiring, Vitest/Playwright |
| P6-008 | S-03 Supplier profile screen | M | P6-001, P6-003 | In progress — UI built on mock API (2026-10-01); remaining: live API wiring, Vitest/Playwright |
| P6-009 | S-04 Compare suppliers | S | P6-006, P6-003 | In progress — UI built on mock API (2026-10-01); remaining: live API wiring, Vitest/Playwright |
| P6-010 | Relevance feedback | S | P6-003 | In progress — UI control + mock endpoint done; `POST /feedback` backend pending |
| P6-011 | Cross-screen states & accessibility pass | M | P6-005…P6-008 | In progress — all S-01…S-05 states, keyboard/labels, demo notice, warnings done; axe check pending |
| P6-012 | E2E tests for core flows | M | P6-011 | Not started |
| P7-001 | Final benchmark runs on holdout | M | P3-014, P4-009, P5-006 | Not started |
| P7-002 | Temporal holdout experiment | M | P4-007, P4-009 | Not started |
| P7-003 | Latency profiling & optimization | M | P5-006 | Not started |
| P7-004 | Error analysis & dev-only tuning | S | P7-001 | Not started |
| P7-005 | Security hardening review | M | P6-011 | Not started |
| P7-006 | Resilience / degraded-mode tests | M | P5-008 or P5-002 | Not started |
| P7-007 | Final evaluation report & claims register | M | P7-001, P7-002 | Not started |
| P8-001 | Clean start & snapshot restore | M | P7-006 | Not started |
| P8-002 | Offline-safe mode | M | P8-001 | Not started |
| P8-003 | Demo deployment & access protection | S | P8-001, P0-006 | Not started |
| P8-004 | Demo script & frozen queries | M | P6-012, P7-007 | Not started |
| P8-005 | Full health check & smoke test | M | P8-001 | Not started |
| P8-006 | Pitch technical assets | M | P7-007 | Not started |
| P8-007 | Demo freeze & dry run | M | P8-002, P8-004, P8-005 | Not started |
