# Phase P5 — Evidence, Confidence & Market Expansion

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Exit: Top 5 contain Reason + Evidence + Confidence (100% reason codes, ≥ 90% evidence); ≥ 1 external source used; LLM failure does not affect search.

### P5-001 — Evidence storage & traceability
- **Objective:** Persist and serve evidence with enforced traceability.
- **Context:** DOMAIN_MODEL §2.4, §3.2, BR-35, NFR-TRC-01, C-16, EC-32.
- **Dependencies:** P2-001.
- **Requirements:** evidence repository/service; validation: source + (url or record id) + observed_at; evidence type enum; organizer procurement records exposed as `PROCUREMENT_HISTORY` evidence (G-25); `as_of` filter.
- **Expected Output:** `evidence/` module.
- **Acceptance Criteria:** invalid evidence rejected; seed fixtures load; query by supplier/offering works.
- **Validation:** unit + integration tests.
- **Out of Scope:** external fetching.

### P5-002 — External source adapter framework
- **Objective:** Safe, allowlisted batch enrichment.
- **Context:** SF-06, NFR-SEC-01/04, BR-38, R-06, R-27, P0-002 allowlist.
- **Dependencies:** P5-001, P0-002.
- **Requirements:** adapter interface (fetch → parse → match → evidence); source definitions config (allowlist, rate limits, timeouts); text-only sanitization & length caps; local snapshot cache for offline replay; DataSource status updates; failures isolated per record.
- **Expected Output:** `ingestion/adapters/base_external.py`, snapshot folder convention.
- **Acceptance Criteria:** adapter can replay from snapshot without network; network failure produces a report, not a crash.
- **Validation:** tests with recorded fixtures.
- **Out of Scope:** live search at request time (FR-16).

### P5-003 — ГИСП manufacturer registry adapter
- **Objective:** Verify manufacturers and add product evidence.
- **Context:** STR §6 (strongest differentiator), FR-11, OQ-06, A-07.
- **Dependencies:** P5-002, P4-004.
- **Requirements:** access method as approved in P0-002; match by INN/OGRN first, name fallback → possible match only; evidence `MANUFACTURER_REGISTRY` (+ products); `supplier_type_basis=registry`.
- **Expected Output:** adapter + snapshot.
- **Acceptance Criteria:** match rate reported; no evidence without source/observed_at; verified manufacturers get `VERIFIED_MANUFACTURER` path.
- **Validation:** fixture tests + report.
- **Out of Scope:** scraping not approved in P0-002.

### P5-004 — Legal identity enrichment adapter (ФНС/ЕГРЮЛ) (Should)
- **Objective:** Legal status, OKVED and identifiers verification.
- **Context:** STR §6, BR-04, A-104, OQ-25.
- **Dependencies:** P5-002, P4-004.
- **Requirements:** approved access only; update `legal_status`, OKVED, OGRN; `LEGAL_REGISTRY` evidence; personal-data minimization for ИП.
- **Expected Output:** adapter + snapshot.
- **Acceptance Criteria:** status coverage reported; inactive suppliers excluded by hard filter.
- **Validation:** fixture tests.
- **Out of Scope:** financial/risk scoring.

### P5-005 — Confidence score & profile completeness
- **Objective:** Confidence v1 separate from Match.
- **Context:** SEARCH_AND_RANKING §4, BR-02, G-21, OQ-26, OQ-27, EC-41.
- **Dependencies:** P5-001, P3-010.
- **Requirements:** 5 components with v1 definitions; `profile_completeness` formula; config-versioned; breakdown returned; confidence used only as tie-break (if OQ-27 accepted).
- **Expected Output:** `evidence/confidence.py`.
- **Acceptance Criteria:** unit tests per component; Match unchanged by confidence.
- **Validation:** tests + benchmark rerun (ordering changes only in ties).
- **Out of Scope:** ML calibration.

### P5-006 — Risk & data-quality flags
- **Objective:** User-facing risk flags derived from quality inputs.
- **Context:** DOMAIN_MODEL §3.3–3.4, C-09, EC-31.
- **Dependencies:** P5-005.
- **Requirements:** quality flags computed at ingestion; risk flags derived at query time with thresholds from config; mapping per C-09.
- **Expected Output:** `evidence/flags.py`.
- **Acceptance Criteria:** each flag has a positive and negative test; flags never alter Match.
- **Validation:** tests.
- **Out of Scope:** complex risk model.

### P5-007 — Explanation templates & A-vs-B
- **Objective:** Human-readable, deterministic explanations.
- **Context:** BR-12, SEARCH_AND_RANKING §6, US-07.
- **Dependencies:** P3-011.
- **Requirements:** RU templates per reason code with parameters; top-difference comparison function; no free text generation; locale-ready keys (OQ-22).
- **Expected Output:** `ranking/explain.py`, template file.
- **Acceptance Criteria:** every result has explanation text; A-vs-B names the largest contribution differences.
- **Validation:** snapshot tests.
- **Out of Scope:** LLM paraphrasing (Could).

### P5-008 — Optional LLM query parser adapter (Could)
- **Objective:** Better intent extraction without compromising determinism.
- **Context:** ED-03, BR-09, BR-10, EC-11, EC-42, R-07, R-24, P0-006.
- **Dependencies:** P3-005, P0-006.
- **Requirements:** adapter behind feature flag; JSON-schema output validated into SearchIntent; temp 0; timeout; cache by (normalized query, parser_version); merges with rule-based result; fallback + warning on any failure; only query text sent.
- **Expected Output:** `query/adapters/llm.py`.
- **Acceptance Criteria:** injection test cannot change filters beyond schema; disabled flag → identical results to rule-based.
- **Validation:** tests with mocked provider; resilience test.
- **Out of Scope:** LLM explanations, agents.

### P5-009 — Market summary in search response (Should)
- **Objective:** Make market expansion visible in numbers.
- **Context:** FR-17, C-04, ED-14, STR §4/§10.
- **Dependencies:** P4-005, P3-012.
- **Requirements:** `market_summary` (known, external, by_type, new_to_category if available) over the full candidate set after hard filters; response contract MINOR bump.
- **Expected Output:** service + schema update.
- **Acceptance Criteria:** counts consistent with results under each `market_scope`.
- **Validation:** API tests.
- **Out of Scope:** analytics dashboards.
