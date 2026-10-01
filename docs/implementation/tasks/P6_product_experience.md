# Phase P6 — Product Experience

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> **Requires P0-005 (Design System mapping + UI locale).** All UI uses Design System components/tokens only.
> Screens and states are specified in [SCREENS.md](../../product/SCREENS.md). Exit: UF-01, UF-03, UF-05 pass E2E from a clean start; US-08 verified.

### P6-001 — Supplier profile & evidence endpoints
- **Objective:** `GET /suppliers/{id}` and `/evidence`.
- **Context:** API_CONTRACTS, FR-09, UC-03, ED-02, ED-22, EC-22, EC-46.
- **Dependencies:** P5-006 (and P6-003 for `request_id` context).
- **Requirements:** identity, type+basis, known/external, offerings (paginated), history, evidence, confidence breakdown, risk flags; `?request_id=` adds query context; redirect handling; 404 envelope.
- **Expected Output:** router + profile assembly in `suppliers/`.
- **Acceptance Criteria:** response validates against OpenAPI; merged ID resolves; unknown request_id → profile without context.
- **Validation:** API tests; P95 ≤ 1 s on seed.
- **Out of Scope:** contact data (OQ-18).

### P6-002 — Filters metadata endpoint (Should)
- **Objective:** `GET /meta/filters`.
- **Context:** API_CONTRACTS, FR-10.
- **Dependencies:** P2-001.
- **Requirements:** regions, supplier types, source types, categories with counts.
- **Expected Output:** router.
- **Acceptance Criteria:** values match DB; enums match contracts.
- **Validation:** API test.
- **Out of Scope:** dynamic facet counts per query.

### P6-003 — Search-run persistence & retrieval
- **Objective:** Persist what the user saw (ED-02).
- **Context:** G-07, US-08, EC-40, FR-13.
- **Dependencies:** P3-012.
- **Requirements:** `search_run`/`search_result` tables; write after response computed (failure logged, not surfaced); `GET /searches/{request_id}`; retention note.
- **Expected Output:** migration, repository, router.
- **Acceptance Criteria:** results returned by `/searches/{id}` equal the original response ordering and scores.
- **Validation:** API tests.
- **Out of Scope:** analytics UI.

### P6-004 — Typed API client from OpenAPI
- **Objective:** Frontend types generated, not hand-written.
- **Context:** ED-08.
- **Dependencies:** P2-006, P1-003.
- **Requirements:** generation script from `/openapi.json`; CI check that generated types are current; thin fetch wrapper handling error envelope and warnings.
- **Expected Output:** `frontend/src/lib/api/…`.
- **Acceptance Criteria:** no `any` on API data; build fails on drift.
- **Validation:** type-check + CI.
- **Out of Scope:** caching strategy beyond the chosen library.

### P6-005 — S-01 Search screen & editable intent
- **Objective:** Capture requirement and allow correcting the interpretation.
- **Context:** S-01, UF-01, UF-02, UC-08, ED-19, EC-01…03, EC-47.
- **Dependencies:** P6-004, P0-005.
- **Requirements:** input with validation; example queries; parsed intent display with extracted/edited markers; re-search with `intent_overrides`; market scope selector; all S-01 states.
- **Expected Output:** route/components (DS-based).
- **Acceptance Criteria:** all S-01 states reachable; overrides reflected in results.
- **Validation:** Vitest + Playwright.
- **Out of Scope:** voice/file upload.

### P6-006 — S-02 Results screen, filters & summary
- **Objective:** Ranked market map with filters and state restoration.
- **Context:** S-02, UF-01/03/04, US-06, US-08, EC-45, OQ-19.
- **Dependencies:** P6-005, P5-009.
- **Requirements:** summary bar; result cards per SCREENS; filters (type, region, scope, experience, min confidence) in URL; server re-query; back-navigation restores without re-run; all S-02 states.
- **Expected Output:** route/components.
- **Acceptance Criteria:** known/external split visible; filtered-empty and degraded states render correctly.
- **Validation:** Playwright UF-01, UF-03, UF-04.
- **Out of Scope:** CSV export.

### P6-007 — Why-matched panel
- **Objective:** Explain a result in ≤ 1 interaction.
- **Context:** UF-05, FR-12, BR-12, NFR-EXP-01.
- **Dependencies:** P6-006, P5-007.
- **Requirements:** reason codes (templated text), contributions breakdown, top evidence with source links (safe external links).
- **Expected Output:** component.
- **Acceptance Criteria:** contributions shown sum to the displayed Match; evidence links open safely.
- **Validation:** component tests + E2E.
- **Out of Scope:** LLM text.

### P6-008 — S-03 Supplier profile screen
- **Objective:** Evidence-backed supplier view with query context.
- **Context:** S-03, UC-03, UF-08, EC-30, EC-46.
- **Dependencies:** P6-001, P6-003.
- **Requirements:** all sections and empty states from SCREENS; query context when available; back to results preserves state.
- **Expected Output:** route/components.
- **Acceptance Criteria:** unknown values displayed as unknown; 404 and context-expired states implemented.
- **Validation:** Playwright.
- **Out of Scope:** editing supplier data.

### P6-009 — S-04 Compare suppliers (Should)
- **Objective:** 2–5 suppliers side by side; "why A above B".
- **Context:** S-04, UC-06, US-07, C-08, EC-43, EC-44.
- **Dependencies:** P6-006, P6-003.
- **Requirements:** compare tray scoped to one request_id; fields per SCREENS; contribution differences highlighted.
- **Expected Output:** route/components.
- **Acceptance Criteria:** 6th selection rejected; different-search conflict handled.
- **Validation:** Playwright UF-06.
- **Out of Scope:** exporting comparison reports.

### P6-010 — Relevance feedback (Should)
- **Objective:** Capture relevant/not relevant/unsure.
- **Context:** FR-15, UF-07, SF-07.
- **Dependencies:** P6-003.
- **Requirements:** `POST /feedback` (validates request_id exists, upsert); UI control on cards/profile with confirmation.
- **Expected Output:** endpoint + UI control.
- **Acceptance Criteria:** repeated feedback overwrites; invalid request_id → 404.
- **Validation:** API + component tests.
- **Out of Scope:** using feedback in ranking.

### P6-011 — Cross-screen states & accessibility pass
- **Objective:** Consistent states and accessibility across screens.
- **Context:** SCREENS cross-screen requirements, NFR-A11Y-01, DoD §8, BR-20 demo-data notice.
- **Dependencies:** P6-005…P6-008.
- **Requirements:** loading/empty/error/partial everywhere; keyboard paths; labels; non-color status; demo-data notice when seed active; warnings displayed.
- **Expected Output:** fixes + checklist.
- **Acceptance Criteria:** checklist 100% for S-01…S-03.
- **Validation:** manual keyboard pass + automated a11y lint (e.g. axe in Playwright).
- **Out of Scope:** full WCAG audit.

### P6-012 — E2E tests for core flows
- **Objective:** Regression safety for the demo.
- **Context:** UF-01, UF-03, UF-05, UF-06, UF-09.
- **Dependencies:** P6-011.
- **Requirements:** Playwright suite against compose stack with seed data; deterministic assertions (top supplier IDs for demo queries).
- **Expected Output:** `frontend/e2e/`.
- **Acceptance Criteria:** suite green twice in a row from clean start.
- **Validation:** run locally/CI.
- **Out of Scope:** visual regression.
