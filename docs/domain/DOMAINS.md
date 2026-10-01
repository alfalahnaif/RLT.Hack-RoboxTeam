# Business Domains & Module Boundaries

> ### Hackathon Day-1 amendment (2026-10-01, ADR-H1)
> - **D7 Procurement History is now the core domain** (lots, items, supplier history with `as_of`) — the search corpus for known suppliers.
> - **New D10 Supplier Pool Health (`pool_health/`)**: category metrics (unique/recent suppliers, top-1/top-3 share) and verdict that triggers expansion (HD-08).
> - D2 Supplier Registry: suppliers come from INNs in the data; `entity_type` ≠ `market_role` (HD-09). D3 Ingestion: CSV staging + curated enrichment files; ER = INN-exact.
> - D6 Evidence & Trust: role evidence + procurement-history evidence; external enrichment precomputed (HD-07).
> - D1 Query Understanding: also handles a **target lot** (items + OKPD2) as input, not only free text.
> Canonical model: [DOMAIN_MODEL §0](../domain/DOMAIN_MODEL.md#0-hackathon-v2-canonical-model-authoritative).

> Derived from Phase 0 §48–51 (modules: query, search, ranking, suppliers, evidence, ingestion, evaluation, shared).
> This analysis keeps that module list and adds one module, **`procurement`** (ED-20 [ER]), because
> procurement history has distinct temporal semantics (temporal holdout) and feeds three other domains.

## 1. Domain map

```text
                    ┌──────────────────────┐
  user text ──────▶ │ D1 Query Understanding│── SearchIntent ─┐
                    └──────────────────────┘                  ▼
┌──────────────────┐      ┌────────────────────┐     ┌──────────────────────┐
│ D2 Supplier       │◀────│ D4 Search &         │────▶│ D5 Ranking &          │
│   Registry        │ read │   Retrieval         │cands│   Explainability      │
│ (suppliers,       │      │ (branches, union,   │     │ (features, score,     │
│  offerings)       │      │  filters, aggreg.)  │     │  contributions,       │
└───────▲───────────┘      └─────────▲──────────┘     │  reason codes)        │
        │ writes                      │ read           └───────▲──────────────┘
┌───────┴───────────┐      ┌──────────┴────────┐              │ inputs
│ D3 Ingestion &     │─────▶│ D7 Procurement    │──────────────┤
│   Entity Resolution│      │   History         │              │
└───────┬───────────┘      └───────────────────┘      ┌───────┴──────────────┐
        └──────────────────────────────────────────▶ │ D6 Evidence & Trust   │
                                                       │ (evidence, confidence,│
                                                       │  risk & quality flags)│
                                                       └──────────────────────┘
 D8 Evaluation ── calls D4/D5 through the same SearchService used by the API
 D9 Presentation (frontend) ── calls public API only
 D0 Platform/Shared ── config, logging, request context, errors, db session, text normalization
```

## 2. Domains

### D1 — Query Understanding (`query/`)
- **Responsibilities:** validate & normalize query text; extract SearchIntent (product, category terms, attributes, region, supplier types, mandatory constraints, quantity); apply user overrides; version the parser.
- **Entities / VOs:** SearchIntent, ParserVersion.
- **Main actions:** `validate(query)`, `normalize(text)`, `parse(query) → SearchIntent`, `merge(intent, overrides)`.
- **Dependencies:** D0 (normalization); optional LLM adapter.
- **External integrations:** LLM provider (optional, Could-tier enhancement; FR-02 must work without it).
- **Business rules:** BR-09, BR-10, BR-28; EC-01…15.
- **Permissions:** anonymous.
- **Flows:** UF-01, UF-02, SF-01 steps 1–4.

### D2 — Supplier Registry (`suppliers/`)
- **Responsibilities:** canonical Supplier and ProductOffering read/write; supplier profile assembly; known/external status; profile completeness; redirect of merged IDs.
- **Entities:** Supplier, ProductOffering, SupplierSourceRef, SupplierRedirect [ER].
- **Main actions:** `get_supplier`, `get_profile(supplier_id, request_ctx?)`, `list_offerings`, `upsert_*` (ingestion only).
- **Dependencies:** D0; reads D6 (evidence, confidence, flags) and D7 (history) for profile assembly via their service interfaces.
- **Business rules:** BR-19, BR-30, BR-33, BR-34, BR-36, BR-39.
- **Flows:** UF-01 (profile), UF-08.

### D3 — Ingestion & Entity Resolution (`ingestion/`)
- **Responsibilities:** source adapters (seed, organizer, registries, catalogs); raw record preservation; normalization; entity resolution (L1–L4); category mapping; rebuild search projection; build embeddings. **CLI only** — never on the request path.
- **Entities:** DataSource, RawSourceRecord, PossibleMatch [ER].
- **Main actions:** `ingest <source>`, `resolve_entities`, `rebuild search_index`, `build_embeddings`.
- **Dependencies:** D2, D6, D7 write interfaces; D0.
- **External integrations:** organizer dataset (files), ГИСП, ФНС/ЕГРЮЛ, company catalogs (allowlisted, legal-cleared).
- **Business rules:** BR-31, BR-32, BR-35, BR-37, BR-38.
- **Flows:** SF-02, SF-03, SF-06.

### D4 — Search & Retrieval (`search/`)
- **Responsibilities:** orchestrate the search pipeline; run retrieval branches (lexical, semantic, category, historical); candidate union & dedupe; hard filters; offering→supplier aggregation; `as_of` support [ER ED-04]; persist SearchRun [ER ED-02].
- **Entities:** SupplierSearchDocument (projection), OfferingEmbedding [ER], SearchRun/SearchResult [ER].
- **Main actions:** `SearchService.search(request, as_of=None, mode=hybrid|baseline)`.
- **Dependencies:** D1 (intent), D5 (ranking), D2 (read), D7 (historical branch), embedding adapter.
- **Business rules:** BR-01, BR-03, BR-04, BR-11, BR-15, BR-19c.
- **Flows:** SF-01.

### D5 — Ranking & Explainability (`ranking/`)
- **Responsibilities:** feature extraction (8 features, 0–1, applicability); weighted Match Score with renormalization; contribution map; reason codes; explanation templates; A-vs-B comparison; ranking config versioning.
- **Entities / VOs:** RankingConfig (versioned file), FeatureVector, MatchBreakdown.
- **Main actions:** `rank(candidates, intent) → ranked results`, `explain(result)`, `compare(a, b)`.
- **Dependencies:** D6 (confidence inputs), D7 (experience), D1 (intent). **No DB access of its own** — pure functions over provided data (testability).
- **Business rules:** BR-02, BR-05, BR-06, BR-07, BR-08, BR-12, BR-13, BR-14.
- **Flows:** SF-01 steps 8–10, UF-05.

### D6 — Evidence & Trust (`evidence/`)
- **Responsibilities:** evidence storage & retrieval; Confidence Score; risk flags; data-quality flags; traceability validation.
- **Entities:** Evidence, ConfidenceBreakdown, flags.
- **Main actions:** `evidence_for(supplier_id|offering_id)`, `confidence(supplier)`, `risk_flags(supplier)`.
- **Dependencies:** D2 (read), D0.
- **Business rules:** BR-16, BR-35, BR-38, C-09.
- **Flows:** UF-05, profile.

### D7 — Procurement History (`procurement/`) [ER ED-20]
- **Responsibilities:** procurement records; experience signals; historical similarity branch data; first-seen dates for known/new; strict `as_of` filtering.
- **Entities:** ProcurementRecord.
- **Main actions:** `history_for(supplier_id, as_of)`, `similar_procurements(intent, as_of)`, `experience_signal(supplier_id, intent, as_of)`.
- **Dependencies:** D0. Populated by D3.
- **Business rules:** BR-08, BR-19, BR-22, BR-29.

### D8 — Evaluation (`evaluation/`)
- **Responsibilities:** benchmark datasets (queries, qrels, manifest, splits); runner (baseline vs hybrid); metrics (P@5, R@20, nDCG@10, MRR, coverage, evidence coverage, latency P50/P95, new-supplier discovery); temporal holdout; reports.
- **Dependencies:** D4 `SearchService` in-process (same code path as API — no HTTP needed); D0.
- **Business rules:** BR-21, BR-22, BR-23, BR-29, BR-40, BR-42.
- **Flows:** SF-04, SF-05.

### D9 — Presentation (`frontend/`)
- **Responsibilities:** screens S-00…S-04; client state (results, compare tray); rendering scores and explanations **as provided by API** (no scoring logic client-side).
- **Dependencies:** public API only; Design System (P0-005).

### D0 — Platform / Shared (`shared/`)
- Config (env), DB session, request context (`request_id`, anonymous actor), structured logging, error envelope & error codes, text normalization, time/clock abstraction (for `as_of` and determinism), UUIDv5 helpers.
- **Must not** contain business logic.

## 3. Module boundary rules

1. A module exposes a **service interface** (`<module>/service.py`) and DTOs; other modules never import its repository or ORM models.
2. Allowed dependency direction (no cycles):
   `api → search → {query, ranking, suppliers, evidence, procurement} → shared`;
   `ranking → (DTOs of) evidence, procurement, query`;
   `ingestion → {suppliers, evidence, procurement} write services → shared`;
   `evaluation → search → …`.
3. `ranking` is pure (no I/O). `search` gathers inputs and calls `ranking`.
4. API layer is thin: validation → service call → DTO mapping → error envelope.
5. Adapters (LLM, embeddings, external sources) live behind interfaces in the owning module (`query/adapters`, `search/embeddings`, `ingestion/adapters`).
6. Optional enforcement: `import-linter` contract in CI (Could).
