# Phase P7 — Evaluation & Hardening

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Exit: no pitch claim without a metric; targets reported honestly; security checklist done; resilience tests green.

### P7-001 — Final benchmark runs on holdout
- **Objective:** Official numbers for seed (engineering) and real (pitch) benchmarks.
- **Context:** EVALUATION §6, BR-21, A-110.
- **Dependencies:** P3-014, P4-009, P5-006.
- **Requirements:** both modes on holdout splits with frozen versions; all metrics incl. evidence/reason coverage and discovery; stored reports.
- **Expected Output:** `benchmark/reports/final_*.json` + summaries.
- **Acceptance Criteria:** reproducible from clean start; versions recorded.
- **Validation:** rerun & diff.
- **Out of Scope:** further tuning.

### P7-002 — Temporal holdout experiment
- **Objective:** "Could we have found the supplier before the procurement?"
- **Context:** EVALUATION §5, SF-05, BR-29, ED-04, EC-52, R-10, OQ-30.
- **Dependencies:** P4-007, P4-009.
- **Requirements:** runner with `as_of` per case; leakage tests (future records/evidence invisible); hit@5/10/20 and MRR for eventual winners/participants; baseline comparison.
- **Expected Output:** temporal report.
- **Acceptance Criteria:** leakage test passes; ≥ 20 cases or documented shortfall.
- **Validation:** tests + report review.
- **Out of Scope:** snapshot databases.

### P7-003 — Latency profiling & optimization
- **Objective:** Meet P95 targets on the demo corpus.
- **Context:** NFR-PERF-01…04, R-11.
- **Dependencies:** P5-006.
- **Requirements:** per-stage percentiles from benchmark and a small concurrency script; EXPLAIN on hot queries; index/cap adjustments.
- **Expected Output:** latency report.
- **Acceptance Criteria:** indexed P95 ≤ 2.5 s, full P95 ≤ 5 s (or documented gap with cause).
- **Validation:** rerun measurements.
- **Out of Scope:** new infrastructure (Redis/OpenSearch).

### P7-004 — Error analysis & dev-only tuning (Should)
- **Objective:** Understand failures; small safe improvements.
- **Context:** EVALUATION §7, R-28.
- **Dependencies:** P7-001.
- **Requirements:** categorize failures on dev; adjust dictionaries/thresholds on dev only; re-run; no holdout re-tuning.
- **Expected Output:** error-analysis table.
- **Acceptance Criteria:** every change logged with before/after dev metrics.
- **Validation:** reports.
- **Out of Scope:** new features.

### P7-005 — Security hardening review
- **Objective:** Close obvious security gaps before exposure.
- **Context:** ARCHITECTURE §13, NFR-SEC-01…07, NFR-PRIV-01, R-25…R-27.
- **Dependencies:** P6-011.
- **Requirements:** checklist: input limits, enums, pagination caps, CORS, debug gating, secrets scan, external text rendering, dependency lock, personal-data review, rate limit plan.
- **Expected Output:** security checklist in `docs/engineering/SECURITY_CHECKLIST.md`.
- **Acceptance Criteria:** all items pass or have an accepted exception.
- **Validation:** review + targeted tests.
- **Out of Scope:** penetration testing.

### P7-006 — Resilience / degraded-mode tests
- **Objective:** Prove degradation instead of failure.
- **Context:** NFR-REL-01…03, BR-10, BR-11.
- **Dependencies:** P5-002 (P5-008 if built).
- **Requirements:** fault injection: embedding model missing, LLM down/slow, external snapshots missing, DB down (→ 503).
- **Expected Output:** resilience test suite.
- **Acceptance Criteria:** each case returns the specified warning/status.
- **Validation:** pytest.
- **Out of Scope:** chaos testing.

### P7-007 — Final evaluation report & claims register
- **Objective:** Pitch-ready, verifiable numbers.
- **Context:** BR-23, NFR-QUAL-01, BR-20.
- **Dependencies:** P7-001, P7-002.
- **Requirements:** `evaluation_report.json` final; claims register table (claim ↔ metric ↔ report file ↔ dataset version); seed vs real clearly labeled.
- **Expected Output:** `docs/engineering/CLAIMS_REGISTER.md`.
- **Acceptance Criteria:** every numeric claim in the pitch appears in the register.
- **Validation:** Lead review.
- **Out of Scope:** slide design.
