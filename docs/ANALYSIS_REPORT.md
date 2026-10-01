# Supplier Radar — Project Analysis & Engineering Preparation Report

**Date:** 2026-09-29 · **Scope:** analysis only; no implementation started
**Inputs:** 3 source documents (~5,250 lines) in [sources/](sources/): Initial Strategy Report (STR), Phase 0 Product & Technical Foundation (P0), P1-001 Canonical Data & Benchmark Seed spec (P1S).
**Outcome:** *The project is implementation-ready, but no implementation has started yet.* The only condition: the blocking decisions in P0 must be closed first.


> ## ⚠️ Hackathon Day-1 addendum (2026-10-01) — read this first
> This report is the **pre-hackathon analysis (2026-09-29)** and is now **historical/reference**. The authoritative plan is
> **[HACKATHON_EXECUTION_BASELINE.md](HACKATHON_EXECUTION_BASELINE.md)** (decisions: [ADR-H1](decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md)).
>
> What changed on day 1:
> - **Organizer briefing** captured ([source](sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md)): regional suppliers/manufacturers/distributors; roles with evidence;
>   OKPD2 not sole criterion; simple explainable scoring; precomputed offline enrichment; one UI for specialist/manager/analyst;
>   scoring: integrity 30 · matching 25 · UI 10; ≤ 10 s per recommendation.
> - **Real dataset analyzed** ([analysis](analysis/REAL_DATASET_ANALYSIS_2024_2025.md)): 604,452 lots · 1,010,138 supplier rows · 2,971,651 ТРУ items ·
>   44,196 supplier INNs · 2,785 customers · 8,453 OKPD2; `lot_id` joins all; АИС ГЗ supplier rows are **100% winners**, ЭМ has winner and non-winner rows;
>   no supplier catalogs, names or description field.
> - **Invalidated assumptions:** synthetic seed as foundation (§8 P1) · ProductOffering as the only search unit · unknown dataset / adapter-first uncertainty ·
>   uniform winner/participant semantics · live external adapters · Match Score v1 feature table · seed benchmark first · 2.5 s latency as the acceptance bar.
> - **Still valid:** modular monolith, PostgreSQL, FastAPI/Next.js stack, Design System + built UI (ED-25…28), Match/Confidence/Risk separation,
>   deterministic ranking, reason codes + evidence, LLM only for interpretation, baseline before tuning, holdout discipline, offline demo.
> - **Roadmap v2** (P1-001A…F → P1-002 → P2-001…003 → P3-001…003 → P4 → P5) replaces the v1 phases in §8 below; v1 task IDs are frozen as `v1/Pn-nnn`.
> - **Most important next action:** P1-001A (reproducible dataset profiling) on the owner's command; ask organizers **OQ-33** (АИС ГЗ `is_winner` semantics).

## Pre-hackathon report (historical)

---

## 1. Executive project analysis

- **Verdict:** The concept and plan are strong and hackathon-appropriate. The problem is clear, and the scope cuts are explicit. The architecture is the right size: a modular monolith on PostgreSQL with FTS, pgvector and pg_trgm. Evaluation is designed first, not bolted on at the end. **I recommend no architectural change.**
- **Main weaknesses found:** missing operational definitions (8 ranking features, 5 confidence components, "known supplier", aggregation, score normalization). There is a state gap between search and profile, compare and feedback. The temporal holdout needs *valid-time* data that the model did not carry. And external dependencies could invalidate the timeline: pre-event coding rules, legality of external sources, and the unknown organizer dataset.
- **Findings:** 19 conflicts (C-00…C-19) · 37 quality gaps (G-xx) · 32 open questions (12 of them new) · 32 risks · 24 proposed engineering decisions (ED-xx) · 90 tasks in 9 phases.
- **Top 3 risks:** R-01 pre-event coding may be disallowed · R-09 the seed benchmark is self-designed, so it proves little to the jury · R-02 organizer data may be poor or late.
- **Most important next action:** execute Phase **P0**, the decision tasks, before writing any code.

## 2. Project understanding

→ [product/PROJECT_OVERVIEW.md](product/PROJECT_OVERVIEW.md)

Supplier Radar turns a free-text procurement requirement into an explainable market map of suppliers, manufacturers and distributors. It covers both known AIS ГЗ suppliers and new external ones. Each result shows Match, Confidence, Risk flags and sourced evidence. The primary user is a procurement or sourcing specialist. The value pillars are **Discovery, Relevance and Trust**. The differentiator is *measured* improvement over keyword search, including a temporal holdout test.

## 3. Requirements summary

- Use cases UC-01…08, user stories US-01…08, FR-01…16 (+ 3 recommended: FR-17…19) → [PRODUCT_REQUIREMENTS](product/PRODUCT_REQUIREMENTS.md)
- NFRs: P95 ≤ 2.5 s indexed and ≤ 5 s end-to-end · determinism · reason codes for every result · traceability · offline-safe · untrusted external content → [NON_FUNCTIONAL_REQUIREMENTS](requirements/NON_FUNCTIONAL_REQUIREMENTS.md)
- 42 testable business rules → [BUSINESS_RULES](requirements/BUSINESS_RULES.md) · 40+ edge cases → [EDGE_CASES](requirements/EDGE_CASES.md)
- Roles: a single anonymous role plus an operator using the CLI; no auth (D-12) → [USER_ROLES_AND_PERMISSIONS](product/USER_ROLES_AND_PERMISSIONS.md)
- Screens S-00…S-05, with states, data and actions only (no visual design) → [SCREENS](product/SCREENS.md)
- Flows: 9 user journeys and 7 system flows → [USER_FLOWS](flows/USER_FLOWS.md)

## 4. Domain breakdown

→ [domain/DOMAINS.md](domain/DOMAINS.md), [domain/DOMAIN_MODEL.md](domain/DOMAIN_MODEL.md)

D1 Query Understanding · D2 Supplier Registry · D3 Ingestion & Entity Resolution · D4 Search & Retrieval · D5 Ranking & Explainability (pure) · D6 Evidence & Trust · D7 Procurement History (new module, ED-20) · D8 Evaluation · D9 Presentation · D0 Shared.
Core entities: Supplier, ProductOffering (the search unit), ProcurementRecord, Evidence, DataSource, RawSourceRecord, SearchDocument (projection), plus the recommended SearchRun and SupplierRedirect.

## 5. System architecture proposal

→ [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md), [SEARCH_AND_RANKING](architecture/SEARCH_AND_RANKING.md), [API_CONTRACTS](architecture/API_CONTRACTS.md), [EVALUATION](architecture/EVALUATION.md)

- Next.js → REST `/api/v1` → FastAPI modular monolith → PostgreSQL (FTS, pg_trgm, pgvector). CLI handles ingestion, indexing and benchmarks. Deployment is Docker Compose with 3 containers.
- Hybrid retrieval: 4 branches → ≤ 500 candidates → deterministic weighted ranking → Top 20. Match, Confidence and Risk stay separate. The LLM is optional and limited to query interpretation.
- Cross-cutting concerns: typed error envelope, degradation through `warnings[]`, `request_id` with structured logs, `/health`, and a 7-level testing strategy.
- Deliberately excluded: Redis, Celery, OpenSearch, Kubernetes, microservices. The scale path is documented instead.

## 6. Dependency map

→ [implementation/DEPENDENCY_MAP.md](implementation/DEPENDENCY_MAP.md)

`Readiness → Foundation → Contracts & fixtures → Data layer → Baseline vertical slice → Hybrid retrieval & ranking ∥ Real organizer data → Trust layer (evidence/confidence) → Product UI (needs Design System) → Proof & hardening → Demo readiness`

## 7. Documentation structure

→ [README.md](README.md)

- `docs/`: product · requirements · domain · flows · architecture · decisions · analysis · implementation · sources (the original documents, moved here unchanged).

## 8. Implementation roadmap

→ [implementation/IMPLEMENTATION_ROADMAP.md](implementation/IMPLEMENTATION_ROADMAP.md)

| Phase | Name | Exit criterion |
|---|---|---|
| P0 | Implementation Readiness (no code) | Blocking decisions closed, plus explicit go-ahead |
| P1 | Foundation & Contracts | Stack healthy; contracts, seed and benchmark v0.1 validate; seed is deterministic |
| P2 | Keyword Baseline Vertical Slice | A real query runs end-to-end; baseline metrics exist |
| P3 | Hybrid Retrieval & Ranking | Hybrid beats baseline on nDCG@10 (dev); deterministic |
| P4 | Organizer Data & Entity Resolution | Real data ingested and deduplicated; real benchmark exists |
| P5 | Evidence, Confidence & Market Expansion | Top 5 carry reason + evidence + confidence |
| P6 | Product Experience (Design System) | UF-01/03/05 pass E2E |
| P7 | Evaluation & Hardening | Every claim backed by a metric; security and resilience checks pass |
| P8 | Demo & Release Readiness | Two clean-start dry runs, one offline |

## 9. Task breakdown

→ [implementation/tasks/](implementation/tasks/) — 90 tasks (P0-001 … P8-007). Each task has: Objective · Context · Dependencies · Requirements · Expected Output · Acceptance Criteria · Validation · Out of Scope. Status is tracked only in the index. The legacy IDs from the sources (P1-001, P1-002, E0…E9) are mapped to the new IDs.

## 10. Risk register

→ [analysis/RISK_REGISTER.md](analysis/RISK_REGISTER.md) — 32 risks with impact, probability, mitigation and deadline.

## 11. Open questions

→ [analysis/OPEN_QUESTIONS.md](analysis/OPEN_QUESTIONS.md) — the most critical: OQ-01 (pre-event coding rules) · OQ-17 (definition of "known supplier") · OQ-08 (allowed external sources) · OQ-22 (UI language vs the Arabic/English Design System) · OQ-20/21 (long specs, multi-lot requests).

## 12. Assumptions

→ [analysis/ASSUMPTIONS.md](analysis/ASSUMPTIONS.md) — 20 source assumptions plus 12 new ones (A-101…A-112).

## 13. Conflicts found

→ [analysis/CONFLICTS.md](analysis/CONFLICTS.md) — the most impactful: C-01 (ranking weights) · C-04 (meaning of "new") · C-05 (score scale 0–1 vs 0–100) · C-07 (editable parsed intent has no API path) · C-11 (determinism vs LLM) · C-12 (100% vs 90% evidence) · C-19 (Russian UI vs Arabic/English Design System). Every conflict has a recommended resolution with status *Proposed*.

## 14. Recommended engineering decisions

→ [decisions/DECISION_LOG.md](decisions/DECISION_LOG.md) §2 — highlights: ED-02 persist search runs · ED-03 rule-based parser by default · ED-04 valid-time + `as_of` · ED-06 separate embeddings table · ED-09 max aggregation + deterministic tie-break · ED-10 no min-max normalization · ED-14 known-supplier definition · ED-19 `intent_overrides`.

## 15. Recommended next step

1. **P0-002** today: confirm pre-event coding rules and source legality. This determines the whole timeline.
2. **P0-001 + P0-004**: approve or reject conflicts and ED items that block P1–P3 (list in [REQUIREMENTS_REVIEW §4](analysis/REQUIREMENTS_REVIEW.md#4-decisions-required-before-implementation-blocking-set)).
3. **P0-005**: Design System mapping plus the UI-language decision, before any frontend work.
4. After an explicit command → **P1-001**.
