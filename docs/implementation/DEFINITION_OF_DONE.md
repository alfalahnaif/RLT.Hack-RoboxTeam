# Definition of Done

> Base: P0 §98 ("not Done because the code is written": Code · Test · Integration · Observable · Demo) and P1S §50.
> A task is **Done** only when every applicable item below is true **and** the task's own Acceptance Criteria pass.
> Items marked (if applicable) may be skipped only with a one-line justification in the task's completion note.

## 1. Functionality
- [ ] All Acceptance Criteria of the task are met and demonstrated (command output, test, or screenshot).
- [ ] Behavior matches the referenced BR/NFR/EC IDs; no scope beyond the task's *Out of Scope* boundary.
- [ ] Connected to upstream and downstream components (no orphan code) — *Integration*.
- [ ] Usable from the product flow or CLI as intended — *Demo*.

## 2. Code quality
- [ ] Follows module boundaries ([DOMAINS §3](../domain/DOMAINS.md#3-module-boundary-rules)); no cross-module repository imports.
- [ ] Lint clean (ruff / ESLint); formatted.
- [ ] No dead code, commented-out blocks, or TODOs without a task ID.
- [ ] Configurable values (caps, weights, thresholds, timeouts) live in versioned config, not literals.

## 3. Type safety
- [ ] Python: type hints on public functions; mypy passes on touched domain modules.
- [ ] TypeScript: `strict` passes; API types come from generated OpenAPI types (ED-08), no `any` on API data.
- [ ] API DTOs separate from ORM models.

## 4. Validation
- [ ] Inputs validated at the boundary (Pydantic / JSON Schema) with explicit limits and enums.
- [ ] Contract/seed/benchmark validators pass (`validate_contracts`, `validate_seed`, `validate_benchmark`) when data or contracts are touched.

## 5. Error handling
- [ ] Errors use the typed error envelope and codes; no stack traces leak to clients.
- [ ] Degraded paths emit `warnings[]` instead of failing (NFR-REL-*).
- [ ] Failures are visible in logs with `request_id` — *Observable*.

## 6. Tests
- [ ] Unit tests for new logic (happy path + edge cases listed in the task).
- [ ] Integration test against real PostgreSQL when SQL/search is touched.
- [ ] Determinism check when retrieval/ranking/parsing is touched (same input → same ordered output).
- [ ] Benchmark re-run (dev split) when retrieval/ranking/parser/corpus changes; no unexplained regression in nDCG@10 (if applicable).
- [ ] All tests pass in CI.

## 7. Security
- [ ] No secrets in code or history; config via env.
- [ ] External/untrusted content handled as text, sanitized, length-capped (if applicable).
- [ ] No new public endpoint without validation; debug-only features gated by `DEBUG`.

## 8. Accessibility (UI tasks)
- [ ] Keyboard reachable controls, visible focus, labeled inputs, status not conveyed by color alone.
- [ ] Loading / empty / error / partial states implemented per [SCREENS.md](../product/SCREENS.md).
- [ ] Uses Design System components/tokens only (after P0-005).

## 9. Performance (if applicable)
- [ ] Stays within the latency budget of NFR-PERF-01/02 on the seed corpus; timing recorded.
- [ ] New queries use appropriate indexes (EXPLAIN checked for search SQL).

## 10. Documentation
- [ ] Task status updated in the [task index](IMPLEMENTATION_ROADMAP.md#task-index).
- [ ] Contract/API/config changes reflected in the relevant KB file and versioned (BR-25).
- [ ] New decisions → DECISION_LOG; new questions → OPEN_QUESTIONS; new conflicts → CONFLICTS.
- [ ] READMEs for new top-level folders (contracts, data, benchmark, scripts).

## 11. Observability
- [ ] Request paths log request_id, stage timings, counts, and versions (NFR-OBS-01).
- [ ] CLI jobs print a summary (counts, errors, warnings, duration) and exit non-zero on failure.

## 12. Data & evaluation integrity
- [ ] Synthetic data remains marked and fictional (BR-20).
- [ ] Holdout untouched by tuning (BR-21); benchmark version bumped on judgment changes.
- [ ] Any metric quoted is reproducible from a stored report with versions.

---

## Phase-level Done
A phase is Done when all its Must tasks are Done **and** the phase Exit Criteria in the
[roadmap](IMPLEMENTATION_ROADMAP.md) are demonstrated end-to-end from a clean start.
