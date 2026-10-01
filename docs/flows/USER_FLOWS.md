# User & System Flows

> ### Hackathon Day-1 amendment (2026-10-01)
> New primary journeys ([Baseline §7, §10–11, §14](../HACKATHON_EXECUTION_BASELINE.md)):
> - **UF-10 Lot → shortlist (primary demo):** user opens/enters a `lot_id` → sees lot items + OKPD2 → ranked suppliers with counts ("N suppliers found, M recent")
>   and "why" (points per feature + evidence lots) → opens a supplier (history, role badge with source).
> - **UF-11 Pool health → expansion:** for the lot's category the manager-level panel shows pool size, recent suppliers, top-1/top-3 share and a verdict;
>   on CONCENTRATED/THIN → "Expand the pool" → pre-loaded verified external candidates with role + evidence (offline).
> - **UF-12 Methodology (analyst):** features & weights, data sources and volumes, replay metrics, limitations.
> - **SF-08 Replay evaluation:** for each benchmark lot, run `/recommendations {lot_id, as_of=publish_date}`; score against winner (2) / participants (1).
> - **SF-09 Curated enrichment load:** curated files (roles, external candidates, evidence) → validator → ingestion CLI → profiles/evidence (no runtime calls).
> UF-01 (free text) remains as a secondary entry point; UF-03 "market expansion" now runs through UF-11. SF-05 is replaced by SF-08; SF-06 by SF-09.

> Sources: Strategy §3, §10–11 (demo flow & screens); Phase 0 §16 (core flow), §51 (ingestion), §64–69 (benchmark).
> Steps marked **[ER]** are recommended to close gaps (see [REQUIREMENTS_REVIEW](../analysis/REQUIREMENTS_REVIEW.md)).

## Part A — User journeys

### UF-01 Primary journey: requirement → shortlist → supplier (demo path)
1. User opens **S-01** and enters/pastes a requirement (e.g. `Интерактивная панель 75" для образовательных учреждений`).
2. System validates (3–1000 chars) and submits `POST /search`.
3. System returns results + `parsed_query`; **S-02** shows summary (e.g. *37 candidates · 12 AIS · 25 external · 6 distributors · 3 manufacturers · 4 new to AIS*) and Top 20 cards.
4. User opens a card → **S-03** with query context (Match 92, Confidence 96, evidence checklist).
5. User returns to S-02 — state restored without re-run (US-08).
**Failure branches:** validation error (inline), 503 (retry), zero results (UF-01a), degraded warnings (banner).

### UF-01a Zero / weak results
Zero candidates → S-02 zero state shows parsed intent and suggests removing constraints/filters → user edits (UF-02).

### UF-02 Correct the interpretation (Strategy §11 "user may edit extracted fields")
1. After search, user sees extracted Category / Product / Characteristics / Quantity / Region / Supplier type.
2. User edits or clears fields.
3. **[ER]** Client re-submits `POST /search` with `intent_overrides` (FR-18, ED-19).
4. Results re-ranked; overridden fields marked *user-edited*.
Open: whether parse should be a separate step before first search (C-07).

### UF-03 Market expansion
1. On S-02 user selects market scope **External / New**.
2. Results filtered to `is_known_supplier=false`; summary highlights new high-confidence suppliers.
3. User inspects one (UF-01 step 4) — sees evidence despite no procurement history (flag, not penalty).

### UF-04 Filter results
Filters: supplier type (manufacturer/distributor/…), region, market scope, relevant experience, min confidence.
Filtered-empty → "clear filters". Server vs client filtering: ED-19.

### UF-05 Understand a recommendation ("Why matched")
1. User clicks *Why matched* on a card.
2. System shows reason codes (templated text) + feature contributions (e.g. Semantic +27, Category +15, Attributes +14, Experience +6) + top evidence with links.
3. Optional: *Why A above B* via S-04 (UF-06) — explanation derived from contribution differences (BR-12).

### UF-06 Compare suppliers (Should)
1. User selects 2–5 cards → compare tray.
2. **S-04** shows fields side-by-side + largest contribution differences.
3. User opens a profile or removes a supplier.

### UF-07 Relevance feedback (Should)
User marks a result relevant / not relevant / unsure → `POST /feedback {request_id, supplier_id, relevance}` → acknowledgment; repeated feedback overwrites previous for same (request_id, supplier_id) [ER].

### UF-08 Open profile directly (deep link)
`/suppliers/{id}?request_id=…` → profile with query context if the SearchRun exists; otherwise without context (EC-46). Merged IDs redirect (EC-22).

### UF-09 Demo script (Strategy §10) — acceptance path for P8-004
Search → summary with known/external split → open supplier with evidence → compare 3 suppliers side by side → metrics slide (baseline vs Supplier Radar).

## Part B — System flows

### SF-01 Search pipeline (Phase 0 §16, §33–35)
```text
 1 Query validation            (D1)  → 422 on invalid
 2 Query normalization         (D1)
 3 Query understanding         (D1)  rule-based; optional LLM (timeout → fallback + warning)
 4 Structured SearchIntent     (D1)  + user overrides [ER]
 5 Candidate retrieval         (D4)  A lexical 200 offerings │ B semantic 200 offerings
                                     C category 100 suppliers │ D historical 100 suppliers (if data)
 6 Candidate union + dedupe    (D4)  ≤ 500 suppliers
 7 Hard filtering              (D4)  mandatory constraints only (BR-04)
 8 Supplier aggregation        (D4)  best offering per supplier (ED-09)
 9 Ranking (Top 100 fully)     (D5)  features → Match Score → renormalize → tie-break
10 Confidence / evidence       (D6)  confidence, risk flags, top evidence
11 Explainability              (D5)  reason codes + contributions + template text
12 Response (Top N=limit)      (D4)  request_id, parsed_query, totals, market summary, timings, versions, warnings
13 Persist SearchRun [ER]      (D4)  async-safe, failure must not fail the request
```
Budget: steps 5–12 ≤ 2.5 s P95; incl. step 3 ≤ 5 s P95. Each branch failure → continue with remaining branches + warning (NFR-REL-01/03).

### SF-02 Ingestion (Phase 0 §51)
`Source → Adapter → RawSourceRecord (checksum) → Normalize → Entity Resolve → Canonical DB → Search Projection → Embeddings`
- CLI: `ingest organizer_dataset`, `ingest external_source <name>`, `rebuild search_index`, `build_embeddings`.
- Idempotent (EC-33); per-record errors collected into an ingestion report, not fatal [ER].
- Batched for large datasets (NFR-SCL-02).

### SF-03 Index & embedding rebuild
Projection rebuilt from canonical tables (full rebuild in MVP); embeddings recomputed only for changed content hash (ED-06). Index version recorded for SearchRun and benchmark manifest.

### SF-04 Benchmark run (Phase 0 §64–71)
`load manifest → verify corpus/index versions → for each query (split=dev|holdout): SearchService.search(mode) → collect Top K → metrics vs qrels → evaluation_report.json (+ markdown summary)`
Modes: `baseline` (FTS only) and `hybrid`. Holdout only for final reporting (BR-21).

### SF-05 Temporal holdout (Strategy §9, Phase 0 §69)
`select historical procurement → cutoff = procurement date → hide outcome → SearchService.search(query_from_procurement, as_of=cutoff) → was eventual winner/participant in Top K?` Requires valid-time filtering across all branches and features (ED-04, EC-52).

### SF-06 External enrichment (batch, not request path)
`controlled source definition → fetch (timeout, rate limit, robots/ToS respected) → sanitize untrusted content → match to canonical supplier (ER) → write Evidence (source, url, observed_at) → update flags/confidence inputs → rebuild projection`
Snapshots cached locally for offline demo (P8-002).

### SF-07 Feedback capture (Should)
`POST /feedback → validate request_id exists [ER] → upsert → 202/200`. Stored for future LTR; not used in ranking v1.
