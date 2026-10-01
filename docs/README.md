# Supplier Radar — Project Knowledge Base

**Project:** Supplier Radar — evidence-based supplier discovery for public procurement (RLT.Hack 2026)
**Knowledge base version:** 2.0 (2026-10-01 — Hackathon Day 1 reconciliation)
**Project state:** Hackathon day 1 · real dataset analyzed · UI layer built on a mock API · backend/data implementation NOT started (each task needs an explicit owner command)

This folder is the **single source of truth** for building Supplier Radar. It restructures the three
original documents in [`sources/`](sources/) into small, engineering-oriented reference files, and adds
the analysis (gaps, conflicts, risks, decisions, roadmap, tasks) needed to start implementation.

Start with **[HACKATHON_EXECUTION_BASELINE.md](HACKATHON_EXECUTION_BASELINE.md)** (§0 below). The pre-hackathon executive view is [ANALYSIS_REPORT.md](ANALYSIS_REPORT.md) (historical).

---

## 0. Start here — current (authoritative) documents

| Document | Role |
|---|---|
| **[HACKATHON_EXECUTION_BASELINE.md](HACKATHON_EXECUTION_BASELINE.md)** | **AUTHORITATIVE implementation baseline for the rest of the hackathon** — requirements, data facts, model, search, ranking, explainability, pool health, enrichment, architecture, order, demo, risks, scope |
| [analysis/REAL_DATASET_ANALYSIS_2024_2025.md](analysis/REAL_DATASET_ANALYSIS_2024_2025.md) | Verified facts about the organizer CSVs (counts, keys, `is_winner` semantics, ТРУ, OKPD2, replay feasibility, golden lots, pool health) |
| [sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md](sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md) | Official organizer challenge clarification (rank-1 source) |
| [decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md](decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md) | Decisions HD-01…HD-10 and what they supersede |
| [implementation/tasks/HACKATHON_V2_TASKS.md](implementation/tasks/HACKATHON_V2_TASKS.md) + [roadmap Part A / task index](implementation/IMPLEMENTATION_ROADMAP.md#task-index) | Roadmap v2 tasks and their status |
| [analysis/OPEN_QUESTIONS.md — organizer pack](analysis/OPEN_QUESTIONS.md#organizer-question-pack--hackathon-day-1) | Questions to ask the organizers now (OQ-33 critical) |

**Historical / reference (pre-hackathon, 2026-09-28/29):** [ANALYSIS_REPORT.md](ANALYSIS_REPORT.md) (with a day-1 addendum), the Phase-0 KB files below,
roadmap v1 (Part B of the roadmap, phase files `tasks/P0…P8_*.md`, IDs referenced as `v1/Pn-nnn`), and the original documents in
[`sources/`](sources/) (Strategy report, Phase 0 foundation, P1-001 seed spec). They are **not deleted**; files that changed carry a
"Hackathon Day-1 amendment" block at the top, and where they conflict with the baseline the baseline wins.
Still valid from that work: modular monolith, FastAPI/PostgreSQL, explainability goals, hybrid retrieval direction, Design System + UI decisions (ED-25…ED-28).

---

## 1. Map of the knowledge base

| Area | File | Answers |
|---|---|---|
| **Authoritative** | [HACKATHON_EXECUTION_BASELINE.md](HACKATHON_EXECUTION_BASELINE.md) | What do we build during the hackathon, in what order, and why? |
| Analysis | [analysis/REAL_DATASET_ANALYSIS_2024_2025.md](analysis/REAL_DATASET_ANALYSIS_2024_2025.md) | What is really in the organizer data? |
| Executive (historical) | [ANALYSIS_REPORT.md](ANALYSIS_REPORT.md) | What did the pre-hackathon analysis conclude? (+ day-1 addendum) |
| Product | [product/PROJECT_OVERVIEW.md](product/PROJECT_OVERVIEW.md) | Problem, users, value, scope, glossary |
| Product | [product/PRODUCT_REQUIREMENTS.md](product/PRODUCT_REQUIREMENTS.md) | Use cases, user stories, FRs, MoSCoW, acceptance & success gates |
| Product | [product/USER_ROLES_AND_PERMISSIONS.md](product/USER_ROLES_AND_PERMISSIONS.md) | Who can do what (MVP and later) |
| Product | [product/SCREENS.md](product/SCREENS.md) | Screen inventory: responsibilities, states, data, actions (for Design System mapping) |
| Requirements | [requirements/NON_FUNCTIONAL_REQUIREMENTS.md](requirements/NON_FUNCTIONAL_REQUIREMENTS.md) | Performance, reliability, determinism, security, observability |
| Requirements | [requirements/BUSINESS_RULES.md](requirements/BUSINESS_RULES.md) | Numbered, testable rules `BR-xx` |
| Requirements | [requirements/EDGE_CASES.md](requirements/EDGE_CASES.md) | Edge cases & expected behavior `EC-xx` |
| Domain | [domain/DOMAIN_MODEL.md](domain/DOMAIN_MODEL.md) | Entities, fields, enums, invariants, identifiers |
| Domain | [domain/DOMAINS.md](domain/DOMAINS.md) | Business domains, responsibilities, module boundaries |
| Flows | [flows/USER_FLOWS.md](flows/USER_FLOWS.md) | User journeys `UF-xx` and system flows `SF-xx` |
| Architecture | [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) | Architecture proposal & cross-cutting concerns |
| Architecture | [architecture/SEARCH_AND_RANKING.md](architecture/SEARCH_AND_RANKING.md) | Retrieval, candidates, ranking, confidence, explainability |
| Architecture | [architecture/API_CONTRACTS.md](architecture/API_CONTRACTS.md) | Public API surface (analysis-level contracts) |
| Architecture | [architecture/EVALUATION.md](architecture/EVALUATION.md) | Benchmark, metrics, temporal holdout, success targets |
| Decisions | [decisions/DECISION_LOG.md](decisions/DECISION_LOG.md) | Accepted decisions (incl. HD-01…HD-10) + proposed engineering decisions |
| Decisions | [decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md](decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md) | Day-1 real-data decisions and supersessions |
| Analysis | [analysis/REQUIREMENTS_REVIEW.md](analysis/REQUIREMENTS_REVIEW.md) | Ambiguities, gaps, missing states/flows/validation |
| Analysis | [analysis/CONFLICTS.md](analysis/CONFLICTS.md) | Contradictions between sources `C-xx` |
| Analysis | [analysis/OPEN_QUESTIONS.md](analysis/OPEN_QUESTIONS.md) | Unresolved questions `OQ-xx` |
| Analysis | [analysis/ASSUMPTIONS.md](analysis/ASSUMPTIONS.md) | Working assumptions `A-xx` |
| Analysis | [analysis/RISK_REGISTER.md](analysis/RISK_REGISTER.md) | Risks `R-xx` |
| Implementation | [implementation/DEPENDENCY_MAP.md](implementation/DEPENDENCY_MAP.md) | Build order & dependency graph |
| Implementation | [implementation/IMPLEMENTATION_ROADMAP.md](implementation/IMPLEMENTATION_ROADMAP.md) | Phases, goals, exit criteria, **task status index** |
| Implementation | [implementation/tasks/HACKATHON_V2_TASKS.md](implementation/tasks/HACKATHON_V2_TASKS.md) | **Current** tasks (roadmap v2) |
| Implementation | [implementation/tasks/](implementation/tasks/) | Frozen v1 tasks `v1/Pn-nnn` (one file per phase) |
| Implementation | [implementation/DEFINITION_OF_DONE.md](implementation/DEFINITION_OF_DONE.md) | Project-wide Definition of Done |
| Sources | [sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md](sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md) | Official organizer briefing (rank 1) |
| Sources | [sources/](sources/) | Original pre-hackathon documents — historical input, not edited |

---

## 2. Source-of-truth hierarchy

When two sources disagree, the **higher** one wins, and the disagreement must be logged in
[analysis/CONFLICTS.md](analysis/CONFLICTS.md) (or resolved via a decision entry).

| Rank | Source | Scope |
|---:|---|---|
| 1 | **Official organizer rules, dataset and answers** (RLT.Hack) — [briefing](sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md), `data/raw/*.csv` ([analysis](analysis/REAL_DATASET_ANALYSIS_2024_2025.md)) | External constraints. Overrides everything. Record answers in OPEN_QUESTIONS / ASSUMPTIONS. |
| 1a | **[HACKATHON_EXECUTION_BASELINE.md](HACKATHON_EXECUTION_BASELINE.md)** + [ADR-H1](decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md) | Authoritative team interpretation for the hackathon. Overrides ranks 2–10 where they conflict (conflicts C-20…C-27). |
| 2 | [PRODUCT_REQUIREMENTS.md](product/PRODUCT_REQUIREMENTS.md) | What we build, priorities, acceptance |
| 3 | [BUSINESS_RULES.md](requirements/BUSINESS_RULES.md) + [NON_FUNCTIONAL_REQUIREMENTS.md](requirements/NON_FUNCTIONAL_REQUIREMENTS.md) | Behavioral rules & quality constraints |
| 4 | [DOMAIN_MODEL.md](domain/DOMAIN_MODEL.md) → later superseded field-by-field by `/contracts/*.schema.json` once created (P1-007/P1-008) | Data meaning & shape |
| 5 | [DECISION_LOG.md](decisions/DECISION_LOG.md) (status **Accepted** only) | Architecture & engineering choices |
| 6 | Architecture specs: [ARCHITECTURE](architecture/ARCHITECTURE.md), [SEARCH_AND_RANKING](architecture/SEARCH_AND_RANKING.md), [API_CONTRACTS](architecture/API_CONTRACTS.md), [EVALUATION](architecture/EVALUATION.md) | How it works |
| 7 | [USER_FLOWS.md](flows/USER_FLOWS.md), [SCREENS.md](product/SCREENS.md) (+ Design System after P0-005) | Experience |
| 8 | [Task files](implementation/tasks/) | Unit of execution — may narrow, never contradict, ranks 2–7 |
| 9 | Existing code | Reflects the above; if code disagrees with docs, the docs win unless a decision is logged |
| 10 | [sources/](sources/) originals | Historical baseline. Where the KB differs, the reason is recorded in CONFLICTS or DECISION_LOG |

Within the original sources: `P1-001 spec` > `Phase 0 foundation` > `Initial strategy report`
for any topic the more specific / later document covers (see [CONFLICTS.md](analysis/CONFLICTS.md) C-00).

**Proposed** items (Engineering Recommendations, proposed decisions `ED-xx`, recommended conflict
resolutions) are **not binding** until marked *Accepted* (task P0-001 / P0-004).

---

## 3. ID conventions

| Prefix | Meaning | Defined in |
|---|---|---|
| `UC-xx`, `US-xx`, `FR-xx` | Use cases, user stories, functional requirements (IDs preserved from sources) | PRODUCT_REQUIREMENTS |
| `NFR-xx` | Non-functional requirements | NON_FUNCTIONAL_REQUIREMENTS |
| `BR-xx` | Business rules | BUSINESS_RULES |
| `EC-xx` | Edge cases | EDGE_CASES |
| `UF-xx` / `SF-xx` | User flows / system flows | USER_FLOWS |
| `S-xx` | Screens | SCREENS |
| `D-xx`, `P1D-xxx` | Accepted decisions (from sources) | DECISION_LOG |
| `ED-xx` | Proposed engineering decisions (this analysis) | DECISION_LOG |
| `A-xx`, `P1A-xxx` | Assumptions (from sources) / `A-1xx` new | ASSUMPTIONS |
| `OQ-xx` | Open questions | OPEN_QUESTIONS |
| `C-xx` | Conflicts | CONFLICTS |
| `G-xx` | Gaps / quality findings | REQUIREMENTS_REVIEW |
| `R-xx` | Risks | RISK_REGISTER |
| `Pn-nnn` / `P1-001A…F` | Implementation tasks — **roadmap v2** (current) | tasks/HACKATHON_V2_TASKS.md |
| `v1/Pn-nnn` | Frozen roadmap-v1 tasks (pre-hackathon) | implementation/tasks/P0…P8_*.md |
| `HD-xx` | Hackathon day-1 decisions | ADR-HACKATHON-DAY1-REAL-DATA-BASELINE |

IDs are **stable**: never renumber; deprecate instead. Handled explicitly on 2026-10-01: roadmap v2 reuses some `Pn-nnn` numbers with new meaning, so every roadmap-v1 task is referenced with the `v1/` prefix (HD-10).

## 4. Change policy

1. Change the lowest-ranked file that fully captures the change; do not copy content across files — link.
2. Any change to ranks 2–5 requires a DECISION_LOG entry (or conflict resolution) referencing the reason.
3. Contract changes follow semver (BR-25) and require re-running validation and the benchmark.
4. Keep task status only in the index in [IMPLEMENTATION_ROADMAP.md](implementation/IMPLEMENTATION_ROADMAP.md#task-index).
