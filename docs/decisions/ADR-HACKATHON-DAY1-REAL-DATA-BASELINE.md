# ADR — Hackathon Day 1: Real-Data Baseline

| | |
|---|---|
| **ID** | ADR-H1 (decisions HD-01 … HD-10) |
| **Date** | 2026-10-01 (hackathon day 1) |
| **Owner / decider** | Project owner (explicit command "Documentation Reconciliation & Technical Baseline Update", 2026-10-01) |
| **Status** | **Accepted** (HD-05 is a *conditional* rule until OQ-33 is answered) |
| **Inputs** | [Organizer briefing](../sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md) · [Real dataset analysis](../analysis/REAL_DATASET_ANALYSIS_2024_2025.md) · pre-hackathon KB |
| **Baseline document** | [HACKATHON_EXECUTION_BASELINE.md](../HACKATHON_EXECUTION_BASELINE.md) |

## Context

The pre-hackathon knowledge base (2026-09-28/29) was written **before** the organizer dataset and briefing existed.
It assumed an unknown dataset, a synthetic seed corpus of supplier *product offerings* as the engineering foundation
(P1-001 spec), and a free-text search box as the only entry point.

On 2026-10-01 the organizers (1) delivered three CSV files of real 2024–2025 procurement data (lots, supplier
relations, ТРУ items with OKPD2), (2) stated that the first practical task is to analyze that data, and
(3) stressed end-to-end integrity, explainable matching, supplier-pool enrichment with roles, and precomputed
(offline) enrichment. The data has **no supplier catalog**: the only product text is attached to procurement lots.

## Decisions

### HD-01 — Real organizer data is the primary engineering foundation
- Use the organizer CSVs (`data/raw/*.csv`) as the corpus for ingestion, retrieval, ranking, benchmark and demo.
- The synthetic seed (P1-001 spec, P1D-003/004/008/009, ED-24) is **demoted** to an optional unit-test fixture
  source. It is no longer on the critical path and is never used for pitch metrics (BR-20, A-110 unchanged).
- **Supersedes:** P1-001 seed spec as primary plan; ED-24; tasks v1/P1-011…P1-014 and v1/P3-008 as critical path.

### HD-02 — `lot_id` is the principal procurement relationship key; `ProcurementLot` is the core aggregate
- All three files join on `lot_id` (verified: no orphan keys — see dataset analysis §3).
- `ProcurementLot` owns `ProcurementItem[]` (ТРУ lines) and `SupplierHistory[]` (supplier relations).
- `procedure_id` is kept as an attribute only (it is 1:1 with `lot_id` in this extract), not as the join key.
- **Amends:** DOMAIN_MODEL §2.3 `ProcurementRecord` (was one row per supplier with a free title).

### HD-03 — Detailed ТРУ item text is the primary search signal
- Retrieval and matching run on **ТРУ `product_name`** (per item), then OKPD2, then lot context; procedure name/subject are low-weight context only.
- `procedure_name` and `subject` are **not** both indexed as independent signals (near-total duplication — dataset analysis §4).
- **Amends** BR-01 / D-05 / P1D-001: the search unit for *known* suppliers is the **historical ProcurementItem**
  (aggregated to one result per supplier through `SupplierHistory`); `ProductOffering` remains the unit for
  *externally enriched* suppliers (catalog / registry evidence). One-result-per-supplier aggregation is unchanged.
- Field priorities and weights are **configurable and must be benchmarked**, not frozen.
- Note: the dataset has **no separate product description field** (ТРУ = `lot_id; product_name; okpd2_code`).

### HD-04 — OKPD2 is a strong signal, never the sole criterion
- OKPD2 relevance uses the classifier hierarchy (exact code > same subclass/group > same class), as one feature among several.
- The ranking must show which criteria were combined and how much each contributed (organizer §6).
- A pure OKPD2 lookup is the **baseline to beat** (P1-002), not the product.

### HD-05 — No cross-platform global win rate until `is_winner` semantics are confirmed *(conditional)*
- Confirmed fact: **every** provided АИС ГЗ supplier row has `is_winner=true`; ЭМ rows contain winners and non-winners (dataset analysis §5).
- "АИС ГЗ contains only awarded suppliers" is a **working interpretation, not a confirmed business semantic** (amendment A1); the contract encodes only the observation (`WINNER_ROWS_ONLY_OBSERVED`, amendment A3).
- Until the organizers answer **OQ-33**: compute `historical_award_count` (both platforms) and
  `marketplace_participation_count` / `marketplace_win_count` (ЭМ only, where participant coverage is known).
  **Never** compute or display `win_rate` across platforms.
- Re-open when OQ-33 is answered.

### HD-06 — Temporal historical replay is the primary evaluation strategy
- Benchmark cases are real target lots; the system only sees data with `publish_date` < target date (`as_of`, ED-04 — now Accepted for this purpose).
- Weak labels: `2 = actual winner`, `1 = actual participant (non-winner)`, `0 = not observed` (treated as *unjudged-negative*, with the documented limitation that "not observed" ≠ irrelevant, BR-22).
- ЭМ 2025 lots with ≥ 2 participants are the preferred pool; lots without supplier relations are **not** benchmark cases.
- Dev/holdout split by time; holdout never tuned on (BR-21).
- **Supersedes:** synthetic seed benchmark v0.1.0 as the first benchmark (EVALUATION §2).

### HD-07 — External enrichment is precomputed, not live
- Weak categories are chosen in advance; ~10 high-quality external companies are found, identity-verified,
  role-classified, evidence-captured (source + URL + `observed_at`) and **pre-loaded**.
- No live internet dependency in the demo (aligns D-09, BR-11, NFR-REL-05). FR-16 live discovery stays Could/out.
- **Amends:** v1/P5-002…P5-004 (adapter framework + live ГИСП/ФНС adapters) → curated, file-based enrichment set.

### HD-08 — Supplier Pool Health decides when external expansion is valuable
- Per category (OKPD2 level configurable) compute: `unique_supplier_count`, `recent_supplier_count`,
  `top_supplier_share`, `top_3_supplier_share` (HHI deferred).
- A weak/concentrated pool triggers an **expansion recommendation** and shows the pre-loaded external candidates.
- New domain concept; product-facing for the procurement-manager level of the UI.

### HD-09 — Separate legal entity type from market role
- `entity_type ∈ {legal_entity, individual_entrepreneur, unknown}` (derived from INN length/format) is distinct from
  `market_role ∈ {manufacturer, distributor, dealer, supplier, reseller, other_intermediary, unknown}` (evidence-based).
- Every non-`unknown` `market_role` carries `role_basis` + evidence (organizer §3) and a `role_verification` level.
- **Amendment A2:** a `VERIFIED` manufacturer requires an official manufacturer/industrial registry entry or explicit first-party production evidence;
  manufacturing OKVED alone yields only `INFERRED_MANUFACTURER_CANDIDATE` (low confidence). Never `VERIFIED_MANUFACTURER` from OKVED alone.
- **Supersedes** the mixed `supplier_type` enum (`manufacturer · distributor · supplier · service_provider · unknown`) in DOMAIN_MODEL §2.1.

### HD-10 — Roadmap v2 replaces roadmap v1; v1 task IDs are frozen under a `v1/` prefix
- The owner-defined sequence (P1-001A…F → P1-002 → P2-001…003 → P3-001…003 → P4 → P5) becomes the active task list.
- Because several IDs (P1-002, P2-001, …) existed with different meaning, **roadmap v1 IDs are referenced as `v1/Pn-nnn`** from now on
  (README §3 "never renumber" is honored: v1 IDs are frozen, not reused silently). Mapping: [IMPLEMENTATION_ROADMAP §3](../implementation/IMPLEMENTATION_ROADMAP.md#3-mapping-roadmap-v1--v2).
- UI work already done (v1/P6-005…P6-011 on a mock API) carries over into v2 **P4 Integrated Product UI**.

## Superseded / amended pre-hackathon items

| Old item | New status | Replaced by |
|---|---|---|
| P1-001 spec (seed + benchmark seed) as primary path | **Superseded** as primary; optional test fixtures | HD-01, HD-06 |
| P1D-003 / P1D-004 / P1D-008 / P1D-009 (seed design decisions) | **Superseded** for the product corpus (still valid if a test fixture is built) | HD-01 |
| D-05 / P1D-001 / BR-01 "search unit = ProductOffering" | **Amended** — known suppliers: ProcurementItem; external: ProductOffering | HD-03 |
| ED-14 "known = winner/participant anywhere" | **Refined** — known = has ≥ 1 `SupplierHistory` row with lot `publish_date` < `as_of` | HD-06 |
| ED-24 seed extension with synthetic history/evidence | **Superseded** — real history exists | HD-01 |
| `supplier_type` enum | **Superseded** | HD-09 |
| SEARCH_AND_RANKING §3 Match Score v1 feature set (Semantic 0.30 / Lexical 0.20 / Category 0.15 / Attribute 0.15 / Experience 0.08 / Geo 0.05 / Type 0.04 / Delivery 0.03) | **Superseded** as the starting feature set (weights were never accepted) | Baseline §8 configurable feature set |
| v1/P5-002…P5-004 live external adapters | **Amended** — precomputed curated enrichment | HD-07 |
| EVALUATION §2 seed benchmark first | **Superseded** — temporal replay benchmark first | HD-06 |
| Roadmap v1 phase order (seed → baseline → hybrid → organizer data …) | **Superseded** | HD-10 |
| NFR-PERF-01/02 (P95 2.5 s / 5 s) | **Kept as internal targets**; organizer acceptance bound = ≤ 10 s per recommendation | Baseline §16 |

## Still valid (explicitly preserved)

D-01 modular monolith · D-02 PostgreSQL · D-03 pgvector (when semantic retrieval is built) · D-04 hybrid retrieval direction ·
D-06 weighted deterministic ranking · D-07 Match / Confidence / Risk separation · D-08 LLM only as supporting layer ·
D-09 pre-indexed primary path · D-10 benchmark before tuning · D-11 no microservices · D-12 no auth · D-13 no price
*competitiveness* scoring · D-14 preserve raw records · D-15 stack (FastAPI, SQLAlchemy, Alembic, Next.js…) · D-16 CLI batch ingestion ·
ED-25…ED-28 (UI locale, Design System, frontend runtime, UI patterns).

## Amendments

| ID | Date | Amendment | Affects |
|---|---|---|---|
| A1 | 2026-10-01 (owner) | АИС ГЗ "award-only" is a working interpretation pending OQ-33, not a confirmed semantic; only "all provided АИС ГЗ rows have `is_winner=true`" is confirmed. Calculations stay conservative: award counts from winner rows only; no participation, non-participation or win-rate inference from АИС ГЗ. | HD-05, DOMAIN_MODEL §0.3, dataset analysis §5 |
| A3 | 2026-10-01 (P1-001B, owner-requested safer naming) | `SupplierHistory.record_semantics {AWARD_ONLY_ASSUMED, PARTICIPANT_LIST}` renamed to `coverage_semantics {WINNER_ROWS_ONLY_OBSERVED, PARTICIPANT_LIST_OBSERVED}` — values describe what was observed in the delivered rows, not an organizer semantic. Mapping AIS_GZ → WINNER_ROWS_ONLY_OBSERVED, EM → PARTICIPANT_LIST_OBSERVED is enforced by the contract. The old enum existed only in documentation (no code/data used it). | contracts v0.2.0, DOMAIN_MODEL §0.3, DATA_MAPPING §4 |
| A4 | 2026-10-01 (owner) | ЭМ coverage value `PARTICIPANT_LIST_OBSERVED` renamed to `MIXED_WINNER_NONWINNER_ROWS_OBSERVED`: only the presence of both winner and non-winner rows is observed; completeness of the participant list is not claimed until officially confirmed (OQ-33/34). АИС ГЗ keeps `WINNER_ROWS_ONLY_OBSERVED`. | contracts v0.2.0 (pre-release correction, no data uses it), DOMAIN_MODEL §0.3, DATA_MAPPING §4 |
| A2 | 2026-10-01 (owner) | Manufacturer verification tightened: VERIFIED requires registry or explicit first-party production evidence; OKVED alone → `INFERRED_MANUFACTURER_CANDIDATE` (low confidence). | HD-09, Baseline §6/§9, DOMAIN_MODEL §0.5, BR-47 |

## Consequences

- New documents: organizer briefing (source), dataset analysis, execution baseline (authoritative), this ADR.
- Updated: README, ANALYSIS_REPORT, DECISION_LOG, OPEN_QUESTIONS, ASSUMPTIONS, CONFLICTS, RISK_REGISTER, DOMAIN_MODEL,
  SEARCH_AND_RANKING, EVALUATION, ARCHITECTURE, PROJECT_OVERVIEW, PRODUCT_REQUIREMENTS, BUSINESS_RULES, NFR, USER_FLOWS,
  DOMAINS, IMPLEMENTATION_ROADMAP, tasks README.
- No product code is written by this ADR.
