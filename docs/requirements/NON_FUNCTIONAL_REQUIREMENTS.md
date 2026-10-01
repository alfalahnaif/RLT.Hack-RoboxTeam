# Non-Functional Requirements

> ### Hackathon Day-1 amendment (2026-10-01)
> - **NFR-PERF-00 (organizer, rank 1):** a recommendation completes in **≤ 10 s** (5–10 s acceptable; 1 min is not). NFR-PERF-01/02 remain internal goals (C-27).
> - **NFR-DEMO-01:** several demonstration cases must run back-to-back inside a ~5-minute pre-defense (precomputed pool health, warm caches).
> - **NFR-REL-05** reinforced: no live-internet dependency in the defense; external enrichment is pre-loaded (HD-07).
> - **NFR-PRIV-01** reinforced: 53% of distinct supplier INNs are individuals/IEs — show INN + entity type only.
> - **NFR-DET-01** applies to `as_of` replay: same data + target + `as_of` + versions ⇒ identical ranking.

> Source: Phase 0 §9, §10, §63, §72, §74. New items marked **[ER]** (Engineering Recommendation).

| ID | Category | Requirement | Target / Rule | Verified by |
|---|---|---|---|---|
| NFR-PERF-01 | Performance | Indexed search latency (retrieval + ranking, no LLM) | **P95 ≤ 2.5 s** | Benchmark latency report (P7-003) |
| NFR-PERF-02 | Performance | End-to-end search including optional query parsing | **P95 ≤ 5 s** | Same |
| NFR-PERF-03 **[ER]** | Performance | Supplier profile load | P95 ≤ 1 s | Smoke test |
| NFR-PERF-04 **[ER]** | Performance | Concurrency assumed for demo | ≤ 5 concurrent searches without violating PERF-01 (OQ-13 for production volume) | Simple load script |
| NFR-REL-01 | Reliability | Failure of an external data source must not break indexed search | Degrade with `warnings[]` | Resilience test (P7-006) |
| NFR-REL-02 | Reliability | Search must work when the LLM is unavailable | Rule-based parser fallback | Resilience test |
| NFR-REL-03 **[ER]** | Reliability | Semantic branch failure (model not loaded) degrades to lexical + category | Warning `SEMANTIC_UNAVAILABLE` | Resilience test |
| NFR-REL-04 | Reliability | Demo runs from clean start with no manual DB edits | One command + seed | P8-001 |
| NFR-REL-05 | Reliability | Demo runs without internet (offline-safe mode) | Pre-indexed data, cached evidence, model baked in image | P8-002 |
| NFR-DET-01 | Determinism | Same dataset + query + version + ranking config ⇒ identical results | Includes ordering (tie-break, ED-09) | Repeat-run test |
| NFR-DET-02 **[ER]** | Determinism | Non-deterministic components (LLM parse) must be cached/versioned or disabled in benchmark mode | ED-03 | Benchmark reproducibility check |
| NFR-EXP-01 | Explainability | Every top result includes reason codes and source evidence | 100% reason codes (all results); ≥90% Top-5 evidence (target, see C-12) | Benchmark evidence coverage |
| NFR-OBS-01 | Observability | Every request has a `request_id` with timings, candidate counts, ranking version, parsing version | In response + structured log | API test |
| NFR-OBS-02 **[ER]** | Observability | Structured (JSON) logs; request_id propagated to all log lines of a request | ED-16 | Log inspection |
| NFR-OBS-03 | Observability | `GET /health` checks API, DB, search index | Returns component status | API test |
| NFR-TRC-01 | Traceability | Any important external fact includes source, URL/reference, `observed_at` | Enforced at evidence write | Validation |
| NFR-TRC-02 | Traceability | Raw source records are preserved; canonical entities link to them | D-14 | Ingestion test |
| NFR-SEC-01 | Security | All external content is untrusted input | No HTML rendering; sanitize; size limits | Security review (P7-005) |
| NFR-SEC-02 | Security | External content cannot call tools, execute instructions or modify ranking via LLM | LLM gets query only; no external text in prompts for MVP | Review |
| NFR-SEC-03 | Security | API validates lengths, enums, pagination, filter values | Pydantic, typed error codes | API tests |
| NFR-SEC-04 | Security | External adapters use controlled source definitions (no arbitrary URLs from users) | Allowlist | Review |
| NFR-SEC-05 | Security | Secrets via environment variables only; never committed | `.env` git-ignored; example file only | CI secret scan (Could) |
| NFR-SEC-06 **[ER]** | Security | Debug routes not registered unless `DEBUG=true` | Route registration check | Test |
| NFR-SEC-07 **[ER]** | Security | Public demo protected by shared credential + rate limit | ED-15 | Deploy checklist |
| NFR-PRIV-01 **[ER]** | Privacy | Minimize personal data of individual entrepreneurs (store only what is needed; no scraping of personal contacts) | OQ-24 | Review |
| NFR-MNT-01 | Maintainability | Modular monolith with module-owned schemas/service/repository/domain logic | D-01, [ARCHITECTURE](../architecture/ARCHITECTURE.md) | Import-boundary check (Could: import-linter) |
| NFR-MNT-02 | Maintainability | API DTOs separated from ORM models; no DB entities in responses | Phase 0 §63 | Review |
| NFR-MNT-03 | Maintainability | Versioned API (`/api/v1`), ISO-8601 timestamps, typed error codes | Phase 0 §63 | API tests |
| NFR-MNT-04 | Maintainability | Contracts versioned with semver | BR-25 | Contract validation |
| NFR-MNT-05 | Maintainability | Embedding model and LLM behind adapters, not in business logic | Phase 0 §32 | Review |
| NFR-SCL-01 | Scalability | Architecture must *demonstrate* a scale path, not build it | OpenSearch/workers/Redis only when proven | Architecture doc |
| NFR-SCL-02 | Scalability | Batched ingestion & indexing for datasets larger than expected | Risk register | P4-008 |
| NFR-SCL-03 | Scalability | Candidate caps (≈300–500) keep ranking cost bounded | Tunable config | Latency report |
| NFR-PORT-01 | Portability | Docker Compose: `frontend`, `api`, `postgres` | One command | P8-001 |
| NFR-LANG-01 | Localization | Search corpus and queries primarily **Russian**; English secondary later | FTS config `russian`; e5 multilingual | Benchmark in Russian |
| NFR-A11Y-01 **[ER]** | Accessibility | Keyboard navigation, labels, non-color status cues on core screens | WCAG 2.1 AA-inspired checklist | Manual check |
| NFR-QUAL-01 | Quality | No accuracy claim in pitch without a supporting metric | BR-23 | Claims register (P7-007) |
