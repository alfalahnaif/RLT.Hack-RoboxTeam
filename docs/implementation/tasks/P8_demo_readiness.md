# Phase P8 — Demo & Release Readiness

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Exit: two consecutive clean-start dry runs of the demo script (UF-09) succeed, one of them offline.

### P8-001 — Clean start & snapshot restore
- **Objective:** Demo from zero without manual fixes.
- **Context:** NFR-REL-04, R-15.
- **Dependencies:** P7-006.
- **Requirements:** single command/script: compose up → migrate → restore demo snapshot (`pg_dump`) or full rebuild; backup snapshot stored outside the repo.
- **Expected Output:** `scripts/demo_up.sh`, snapshot procedure doc.
- **Acceptance Criteria:** fresh machine/volumes → working demo in documented time.
- **Validation:** timed run from clean volumes.
- **Out of Scope:** production backups.

### P8-002 — Offline-safe mode
- **Objective:** Demo without internet.
- **Context:** NFR-REL-05, ED-17, R-08.
- **Dependencies:** P8-001.
- **Requirements:** `OFFLINE=true`: LLM disabled, external adapters read snapshots only, model local, fonts/assets local.
- **Expected Output:** config flag + doc.
- **Acceptance Criteria:** full UF-09 passes with network disabled.
- **Validation:** dry run offline.
- **Out of Scope:** —

### P8-003 — Demo deployment & access protection (Should)
- **Objective:** Optional hosted demo.
- **Context:** ED-15, OQ-23, R-25.
- **Dependencies:** P8-001, P0-006.
- **Requirements:** deploy compose to chosen host; TLS reverse proxy; shared credential; rate limit on `/search`; DEBUG off.
- **Expected Output:** deployment notes.
- **Acceptance Criteria:** hosted URL passes smoke test; unauthenticated access blocked.
- **Validation:** P8-005 against hosted URL.
- **Out of Scope:** CI/CD, monitoring stack.

### P8-004 — Demo script & frozen queries
- **Objective:** A rehearsed, deterministic story.
- **Context:** UF-09, STR §10, §18, R-22.
- **Dependencies:** P6-012, P7-007.
- **Requirements:** 3 primary + 3 fallback queries with expected top results; talk track mapped to screens; fallback if compare cut (C-08).
- **Expected Output:** `docs/engineering/DEMO_SCRIPT.md`.
- **Acceptance Criteria:** each frozen query's top-3 is asserted in E2E.
- **Validation:** E2E + rehearsal.
- **Out of Scope:** slide visuals.

### P8-005 — Full health check & smoke test
- **Objective:** Fast go/no-go check.
- **Context:** NFR-OBS-03, API_CONTRACTS `/health`.
- **Dependencies:** P8-001.
- **Requirements:** `/health` reports db, index size, embedding coverage, model loaded, LLM status; `scripts/smoke.sh` runs health + one search + one profile.
- **Expected Output:** endpoint update + script.
- **Acceptance Criteria:** smoke exits 0 on healthy stack, non-zero with clear message otherwise.
- **Validation:** run with a stopped DB.
- **Out of Scope:** alerting.

### P8-006 — Pitch technical assets
- **Objective:** Content for architecture and metrics slides.
- **Context:** STR §12 scale story, §18–19, P7-007.
- **Dependencies:** P7-007.
- **Requirements:** architecture diagram (current + scale path), metrics table (baseline vs Supplier Radar, from claims register), temporal holdout result, limitations.
- **Expected Output:** `docs/engineering/PITCH_TECH_NOTES.md`.
- **Acceptance Criteria:** every number traceable to the claims register.
- **Validation:** Lead review.
- **Out of Scope:** slide design.

### P8-007 — Demo freeze & dry run
- **Objective:** Lock the build.
- **Context:** R-14, R-15, STR §14 ("freeze unnecessary features").
- **Dependencies:** P8-002, P8-004, P8-005.
- **Requirements:** tag release; only critical fixes afterwards; two full dry runs (one offline); fallback laptop prepared.
- **Expected Output:** git tag `demo-v1`, dry-run notes.
- **Acceptance Criteria:** phase exit criterion met.
- **Validation:** dry runs.
- **Out of Scope:** new features.
