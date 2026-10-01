# Conflicts Between Sources

> Sources abbreviated: **STR** = Initial Strategy Report · **P0** = Phase 0 Foundation · **P1S** = P1-001 Spec.
> Per instruction, no conflict is silently decided. Each has a **Recommended Resolution** with status
> **Proposed** until accepted in task P0-001. The knowledge base follows the recommended resolution
> provisionally and marks affected places with the conflict ID.

| Status legend | |
|---|---|
| Proposed | Recommendation written, awaiting owner approval |
| Accepted / Rejected | Decided by the team (record date + who) |

---

**Conflict ID:** C-00 — Precedence between the original documents
**Source A:** STR ("should remain the strategic baseline", §20)
**Source B:** P0 ("Implementation Blueprint", later and more detailed); P1S (task spec, latest)
**Conflict:** STR says it stays the baseline, while P0/P1S refine and in places change its content (weights, priorities, schemas).
**Impact:** Any disagreement below has no tie-break rule.
**Recommended Resolution:** STR governs *strategy & intent* (why, differentiation, scope gate); P0 governs *product & technical design*; P1S governs *contracts & seed/benchmark details*. More specific + later wins on the topic it covers. **Status:** Proposed.

---

**Conflict ID:** C-01 — Match Score weights
**Source A:** STR §7.1 — Semantic 30%, Product/category 25%, Exact attribute 20%, Procurement experience 15%, Geography 10%.
**Source B:** P0 §38 — Semantic 0.30, Lexical 0.20, Category 0.15, Attribute 0.15, Experience 0.08, Geographic 0.05, SupplierType 0.04, Delivery 0.03.
**Conflict:** Different feature sets and weights (experience 15% vs 8%; lexical absent in STR).
**Impact:** Ranking behavior and discoverability of new suppliers.
**Recommended Resolution:** Use P0 v1 weights (STR itself calls weights a baseline to tune). Record as ranking config 1.0.0. **Status:** Proposed.

---

**Conflict ID:** C-02 — Phase numbering & naming
**Source A:** P0 §89–96 execution phases: 1 Vertical Slice · 2 Core Search & Ranking · 3 Intelligence & Evidence · 4 Product Experience · 5 Evaluation · 6 Deployment & Demo.
**Source B:** P0 §100 roadmap: 1 Vertical Slice · 2 Search MVP · 3 Intelligence+Evidence · 4 Hackathon Product · **5 Pilot · 6 Production SaaS**.
**Conflict:** "Phase 5/6" mean Evaluation/Deployment in one place and Pilot/SaaS in another. Also "Phase 0" = the planning phase (done) in P0, while the requested roadmap uses Phase 0 for the first engineering phase.
**Impact:** Ambiguous references in discussions and task IDs.
**Recommended Resolution:** Adopt the roadmap in [IMPLEMENTATION_ROADMAP](../implementation/IMPLEMENTATION_ROADMAP.md) (P0 Readiness … P8 Demo Readiness) with an explicit mapping table; call product-evolution stages "Stage: Hackathon / Pilot / SaaS", not phases. **Status:** Proposed (ED-21).

---

**Conflict ID:** C-03 — How entities reference their data source
**Source A:** P0 §20–23 — offering has `source_id`; procurement_record `source_id`; evidence `source_name` + `source_record_id`; data_source `id` (type unspecified, UUID implied by "id UUID" elsewhere).
**Source B:** P1S §6, §9, §12 — supplier `source_ids[{source_name, external_id}]`; offering `source_name` + `source_external_id`; data_source `id: "seed"` (slug).
**Conflict:** Three naming conventions; slug vs UUID for DataSource id.
**Impact:** Schema churn in P1-007 / P2-001; broken joins in ingestion.
**Recommended Resolution:** DataSource id = stable **slug** (`seed`, `organizer`, `gisp`…). All entities reference `source_name` (= DataSource slug) + `source_external_id` / `source_record_id`. Follow P1S (latest). **Status:** Proposed (ED-05).

---

**Conflict ID:** C-04 — Meaning of "new" supplier
**Source A:** STR §4/§10 — "4 new high-confidence suppliers **not previously active in this procurement category**" and "4 companies are **NEW to AIS procurement history**".
**Source B:** P1S §21, P1A-007 — single boolean `is_known_supplier` per supplier (global).
**Conflict:** Category-relative novelty vs global novelty.
**Impact:** Market-expansion metric, summary counts, UI badges, benchmark "new suppliers discovered".
**Recommended Resolution:** Keep global boolean for MVP (P1S); add *derived, per-query* `new_to_category` count in `market_summary` if procurement data supports it (Should). Confirm definition with organizers (OQ-17). **Status:** Proposed (ED-14).

---

**Conflict ID:** C-05 — Score scale and naming
**Source A:** STR §3/§10–11, P0 §38 — Match and Confidence shown as **0–100**; P0 "Final result: 0–100".
**Source B:** P1S §15–16 — public contract field `score` normalized **0–1**.
**Conflict:** Scale and field naming (`score` vs Match/Confidence).
**Impact:** API contract stability, UI formatting, benchmark reports.
**Recommended Resolution:** API uses 0–1 floats (`match_score`, `confidence_score`; `score` kept as alias of `match_score` until contract 1.0); UI renders integer 0–100. **Status:** Proposed (ED-01).

---

**Conflict ID:** C-06 — Validation error status codes
**Source A:** P0 §56 — `400 QUERY_TOO_SHORT`, `422 INVALID_FILTER`.
**Source B:** P1S §14 — full validation rules (length 3–1000, limit 1–100) without status codes; FastAPI/Pydantic default is 422 for all.
**Conflict:** Mixed 400/422 for the same class (input validation); too-long query / bad limit unspecified.
**Impact:** Frontend error handling; contract tests.
**Recommended Resolution:** All request-validation errors → **422** with typed `code` (`QUERY_TOO_SHORT`, `QUERY_TOO_LONG`, `INVALID_FILTER`, `VALIDATION_ERROR`); 400 reserved for malformed JSON. Alternative: keep 400 for `QUERY_TOO_SHORT` as written. **Status:** Proposed (ED-07).

---

**Conflict ID:** C-07 — Editable extracted fields vs API
**Source A:** STR §11 Screen 1 — system extracts Category/Product/Characteristics/Quantity/Region/Supplier Type and **the user may edit** them.
**Source B:** P0 §56 / P1S §13 — `POST /search` accepts only `query`, `filters`, `limit`; no way to submit edited intent; no parse-only endpoint.
**Conflict:** A required UX capability has no API path.
**Impact:** UC-08 unimplementable as specified; demo flow.
**Recommended Resolution:** Add optional `intent_overrides` to `POST /search` (MINOR, non-breaking). No separate parse endpoint (keeps one round-trip). **Status:** Proposed (ED-19).

---

**Conflict ID:** C-08 — Priority of supplier comparison
**Source A:** STR §10–11 — Compare is one of **four core screens** and part of the live demo script.
**Source B:** P0 FR-14 **Should**; §85 P1; §89 "Compare — if time".
**Conflict:** Demo-critical vs optional.
**Impact:** Planning of Phase P6 and demo script.
**Recommended Resolution:** Keep Should priority but schedule S-04 as the first Should item in P6 because it is in the demo script; demo script has a fallback without compare. **Status:** Proposed.

---

**Conflict ID:** C-09 — Data-quality flags vs risk flags overlap
**Source A:** P0 §29 — `STALE_DATA, UNVERIFIED_PRODUCT, DUPLICATE_CANDIDATE, UNKNOWN_SUPPLIER_TYPE…`
**Source B:** P0 §44 / STR §7.3 — `STALE_INFORMATION, LOW_EVIDENCE, AMBIGUOUS_ENTITY, UNVERIFIED_MANUFACTURER…`
**Conflict:** Near-duplicate concepts with different names (duplicated requirement).
**Impact:** Two parallel vocabularies; UI confusion.
**Recommended Resolution:** Data-quality flags = internal, record-level **inputs**; risk flags = user-facing, result-level **derived outputs** with an explicit mapping (STALE_DATA→STALE_INFORMATION, DUPLICATE_CANDIDATE→AMBIGUOUS_ENTITY, UNVERIFIED_PRODUCT→LOW_EVIDENCE). **Status:** Proposed.

---

**Conflict ID:** C-10 — Benchmark query schema
**Source A:** P0 §66 — single schema with `mandatory_attributes, relevant_supplier_ids, relevance_grade`.
**Source B:** P1S §26–27 — `queries.csv` (with `difficulty`) + separate `qrels.csv`; no `mandatory_attributes`.
**Conflict:** Different file structures.
**Impact:** Runner implementation.
**Recommended Resolution:** Follow P1S (queries + qrels); add optional `mandatory_attributes` (JSON) column to `queries.csv` later for attribute-coverage analysis and `split` column [ER]. **Status:** Proposed.

---

**Conflict ID:** C-11 — Determinism vs LLM query parsing
**Source A:** P0 §9 Determinism — same dataset/query/version/config ⇒ reproducible results.
**Source B:** P0 §47, FR-02 — LLM used for query extraction (non-deterministic, external).
**Conflict:** Internal tension within P0.
**Impact:** Unreproducible benchmark; flaky tests; offline demo failure.
**Recommended Resolution:** Rule-based parser is the default and the benchmark mode; LLM optional, temperature 0, schema-constrained, cached by `(normalized_query, parser_version)`; parser version part of the determinism key. **Status:** Proposed (ED-03).

---

**Conflict ID:** C-12 — Evidence coverage requirement
**Source A:** P0 §9 — "Every top result must include reason codes **and source evidence**."
**Source B:** P0 §71 — "**≥ 90%** of Top 5 must contain source evidence."
**Conflict:** 100% vs 90%.
**Impact:** Acceptance; pressure to fabricate weak evidence to hit 100%.
**Recommended Resolution:** Reason codes 100% (hard); source evidence ≥ 90% of Top 5 (measured target); results without evidence carry `LOW_EVIDENCE`. **Status:** Proposed.

---

**Conflict ID:** C-13 — Task ID scheme
**Source A:** P0 §79–88 — epics `E0…E9` with tasks `E0-T1`; P0 §107 & P1S — work packages `P1-001`, `P1-002` (each large).
**Source B:** Current planning instruction — small tasks with IDs `P0-001`, `P1-001`, … per phase.
**Conflict:** Existing `P1-001` / `P1-002` names denote large packages, not small tasks.
**Impact:** Reference confusion.
**Recommended Resolution:** New stable task IDs per [IMPLEMENTATION_ROADMAP](../implementation/IMPLEMENTATION_ROADMAP.md); legacy IDs kept as *work package* names ("WP P1-001 spec" = tasks P1-007…P1-014; "WP P1-002" = Phase P2) with a mapping table. **Status:** Proposed (ED-21).

---

**Conflict ID:** C-14 — Where embeddings are stored
**Source A:** P0 §20 — `product_offering.embedding VECTOR`.
**Source B:** P0 §24 — `supplier_search_document.embedding` (projection).
**Conflict:** Duplicated field in canonical entity and projection.
**Impact:** Recompute cost on projection rebuild; model-version ambiguity.
**Recommended Resolution:** Neither canonical table: separate `offering_embedding(offering_id, embedding_version, content_hash, vector)`; projection joins/copies it. Canonical offering stays model-agnostic. **Status:** Proposed (ED-06).

---

**Conflict ID:** C-15 — Experience weight vs not penalizing new suppliers
**Source A:** STR §7.3 — risk kept separate "to preserve discoverability of new suppliers without automatically penalizing them for having little historical data".
**Source B:** P0 §38 — ProcurementExperience 0.08 is part of Match Score (new suppliers get 0 on it).
**Conflict:** New suppliers are structurally capped at 92/100.
**Impact:** Market expansion vs ranking of known suppliers.
**Recommended Resolution:** Keep 0.08 (small, explicitly designed) for v1; measure external-supplier recall on dev; if discovery target is missed, evaluate alternative (experience as N/A for external suppliers — would require changing BR-05 semantics). **Status:** Proposed.

---

**Conflict ID:** C-16 — `observed_at` requirement
**Source A:** P0 §9 — any important external fact must include source, URL/reference, observed_at.
**Source B:** P1S §10 — offering `source_observed_at` optional.
**Conflict:** Mandatory vs optional.
**Impact:** Traceability, SourceRecency feature, temporal holdout.
**Recommended Resolution:** Conditionally required: mandatory when `source_type ∉ {internal_seed}`; the seed generator sets it anyway. **Status:** Proposed.

---

**Conflict ID:** C-17 — Reason-code vocabulary
**Source A:** P0 §45 — `EXACT_CATEGORY`, `RELEVANT_PROCUREMENT_HISTORY`, `ATTRIBUTE_MATCH`, `VERIFIED_MANUFACTURER`.
**Source B:** P1S §17 — `CATEGORY_MATCH`, `PROCUREMENT_EXPERIENCE`, … ("do not allow arbitrary strings").
**Conflict:** Two names for the same concept.
**Impact:** Enum drift.
**Recommended Resolution:** P1S vocabulary is canonical; P0 names treated as illustrative. **Status:** Proposed.

---

**Conflict ID:** C-18 — Schema set completeness in P1-001
**Source A:** P1S §3, §51 — exactly **four** schemas (supplier, product_offering, search_query, search_response).
**Source B:** P1S §12, §25, §32 — `data_sources.jsonl` must exist and be validated ("Sources: 1 valid").
**Conflict:** A validated file has no schema.
**Impact:** `validate_seed.py` cannot contract-validate sources.
**Recommended Resolution:** Add `data_source.schema.json` (5th contract) and an `error.schema.json` [ER]; update "Contracts valid: N/N". **Status:** Proposed.

---

**Conflict ID:** C-19 — UI language vs Design System
**Source A:** STR §10–11, P1S §40–42 — Russian queries & data; Russian UI prompt ("Что необходимо закупить?"); St Petersburg procurement users.
**Source B:** Provided SafarFlow Design System — Arabic RTL default + English LTR, next-intl.
**Conflict:** Target user language (Russian) is not a DS locale; RTL-first rules.
**Impact:** Screen implementation, i18n setup, jury comprehension.
**Recommended Resolution:** Decide UI locale(s) in P0-005 (OQ-22). Likely: Russian UI (LTR) using DS tokens/components with an added `ru` locale; Arabic/English optional. **Status:** Resolved 2026-09-29 — ED-25 (ru default + en, LTR; Arabic dropped).

---

## Hackathon Day 1 conflicts (2026-10-01) — pre-hackathon KB vs organizer briefing / real data

> All resolved by [ADR-H1](../decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md); the organizer briefing and dataset rank 1 in the hierarchy.

**Conflict ID:** C-20 — Synthetic seed vs real data as foundation
**Source A:** P1S (P1-001 spec), roadmap v1 P1 — deterministic synthetic seed + seed benchmark first.
**Source B:** Organizer briefing §5 — first practical step is analyzing the provided CSVs; real 2024–2025 data exists.
**Resolution:** Real data is primary (HD-01); seed only as optional test fixtures. **Status:** Resolved 2026-10-01.

---

**Conflict ID:** C-21 — Search unit
**Source A:** BR-01 / D-05 / P1D-001 — search unit = supplier ProductOffering (catalog).
**Source B:** Dataset — no supplier catalogs; product text exists only as procurement ТРУ items linked by `lot_id`.
**Resolution:** Known suppliers: historical ProcurementItem aggregated per supplier; external: ProductOffering (HD-03). **Status:** Resolved 2026-10-01.

---

**Conflict ID:** C-22 — Procurement record shape
**Source A:** DOMAIN_MODEL §2.3 — ProcurementRecord per supplier with title/description/role.
**Source B:** Dataset — Lot (notice) → Items (ТРУ) and Lot → SupplierHistory (is_winner); no description field.
**Resolution:** ProcurementLot aggregate with ProcurementItem[] and SupplierHistory[] (HD-02). **Status:** Resolved 2026-10-01.

---

**Conflict ID:** C-23 — Participation semantics / win rate
**Source A:** DOMAIN_MODEL `role ∈ {winner, participant, …}` uniform across data; ProcurementExperience feature.
**Source B:** Dataset — АИС ГЗ rows 100% winners; ЭМ has winner and non-winner rows (participant-list completeness unconfirmed — ADR-H1 A4).
**Resolution:** Platform-separated counters; no global win rate until OQ-33 (HD-05). **Status:** Resolved (conditional) 2026-10-01.

---

**Conflict ID:** C-24 — Ranking feature set
**Source A:** SEARCH_AND_RANKING §3 — Semantic 0.30 / Lexical 0.20 / Category 0.15 / Attribute 0.15 / Experience 0.08 / Geo 0.05 / Type 0.04 / Delivery 0.03 (never accepted).
**Source B:** Organizer §6–7, §11 — OKPD2 + history signals (similar experience, customer, participation, wins), simple scoring, explain influence; data has no supplier attributes/delivery/region beyond INN.
**Resolution:** New configurable feature set (baseline §8); weights to be benchmarked. **Status:** Resolved 2026-10-01.

---

**Conflict ID:** C-25 — Supplier type vs role
**Source A:** `supplier_type ∈ {manufacturer, distributor, supplier, service_provider, unknown}`.
**Source B:** Organizer §3 roles (manufacturer, distributor, supplier, dealer, reseller, other intermediary); data shows 53% IEs (legal form).
**Resolution:** `entity_type` separate from `market_role` with basis + evidence (HD-09). **Status:** Resolved 2026-10-01.

---

**Conflict ID:** C-26 — External sources live vs precomputed
**Source A:** v1/P5-002…P5-004 — adapter framework + live ГИСП/ФНС adapters.
**Source B:** Organizer §9 — enrichment may be precomputed; no live-internet dependency.
**Resolution:** Curated, pre-loaded enrichment for 1–2 weak categories (HD-07). **Status:** Resolved 2026-10-01.

---

**Conflict ID:** C-27 — Performance targets
**Source A:** NFR-PERF-01/02 — P95 ≤ 2.5 s indexed / ≤ 5 s end-to-end.
**Source B:** Organizer §12 — 5–10 s acceptable, 1 min not.
**Resolution:** Acceptance bound ≤ 10 s per recommendation; ≤ 5 s kept as internal goal. **Status:** Resolved 2026-10-01.
