# Decision Log

> Accepted decisions from the sources are binding. Proposed engineering decisions (`ED-xx`) from this
> analysis are **not binding until accepted** (task P0-004). To change an accepted decision, add a new
> entry that supersedes it — never edit history.

## 0. Hackathon Day-1 decisions — ADR-H1 (2026-10-01, Accepted)

Full record: [ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md](ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md) · Baseline: [HACKATHON_EXECUTION_BASELINE.md](../HACKATHON_EXECUTION_BASELINE.md).

| ID | Decision | Supersedes / amends | Status |
|---|---|---|---|
| HD-01 | Organizer real data (not synthetic seed) is the primary engineering foundation | P1-001 seed spec as primary path; P1D-003/004/008/009 (product corpus); ED-24 | Accepted |
| HD-02 | `lot_id` is the principal relationship key; `ProcurementLot` is the core aggregate | DOMAIN_MODEL §2.3 ProcurementRecord shape | Accepted |
| HD-03 | Detailed ТРУ item text is the primary search signal; procedure name/subject low and counted once | Amends D-05 / P1D-001 / BR-01 (known suppliers: ProcurementItem; external: ProductOffering) | Accepted |
| HD-04 | OKPD2 is a strong signal (hierarchy-aware), never the sole criterion | — | Accepted |
| HD-05 | No cross-platform global win rate until `is_winner` semantics are confirmed; platform-separated counters | — | Accepted (conditional on OQ-33) |
| HD-06 | Temporal historical replay (labels 2/1/0) is the primary evaluation strategy | EVALUATION §2 seed benchmark first; ED-04 accepted for `as_of = publish_date` | Accepted |
| HD-07 | External enrichment is precomputed and pre-loaded, not live | v1/P5-002…P5-004 live adapters | Accepted |
| HD-08 | Supplier Pool Health determines when external expansion is shown | New concept | Accepted |
| HD-09 | `entity_type` (legal form from INN) is separate from `market_role` (evidence-based) | `supplier_type` enum | Accepted |
| HD-10 | Roadmap v2 replaces roadmap v1; v1 IDs frozen as `v1/Pn-nnn` | ED-21 phase structure | Accepted |

**Status changes caused by ADR-H1** (history preserved — rows below are not edited except for the status note):
- P1D-003, P1D-004, P1D-008, P1D-009 → *Superseded for the product corpus by HD-01* (still valid if a synthetic unit-test fixture is ever generated).
- P1D-001 / D-05 → *Amended by HD-03*.
- P1D-009 "market expansion represented in seed" → replaced by curated real external candidates (HD-07).
- ED-04 → *Accepted (2026-10-01, HD-06)* for `as_of` = lot `publish_date`.
- ED-14 → *Superseded by HD-06/ADR-H1*: known = has ≥ 1 SupplierHistory row on a lot published before `as_of`.
- ED-21 → *Superseded by HD-10* (roadmap v2).
- ED-24 → *Superseded by HD-01* (real history exists).
- D-13 "no price scoring" → *still valid*; `procurement_value_similarity` (contract-scale similarity) is not price competitiveness.
- D-15 (stack) → *still valid*; Polars optional (stdlib/SQL acceptable for profiling and ingestion).
- ADR-H1 amendments: **A1** АИС ГЗ award-only = working interpretation (OQ-33) · **A2** VERIFIED manufacturer never from OKVED alone · **A3** `record_semantics` → `coverage_semantics` (P1-001B) · **A4** ЭМ value = `MIXED_WINNER_NONWINNER_ROWS_OBSERVED` (no participant-list completeness claim).
- P1D-010 (JSON Schema 2020-12 contracts) → *applied* in `/contracts` v0.2.0 (P1-001B); validated by a stdlib subset validator because no JSON Schema library is installed.

## 1. Accepted decisions (from sources)

| ID | Decision | Reason | Source |
|---|---|---|---|
| D-01 | Modular monolith | Fastest reliable architecture | P0 §76 |
| D-02 | PostgreSQL | One data/search platform | P0 |
| D-03 | pgvector | Avoid separate vector DB | P0 |
| D-04 | Hybrid retrieval (FTS + semantic + filters) | Best recall/precision trade-off | P0 |
| D-05 | Search ProductOffering | Product-level relevance | P0 · *Amended — HD-03* |
| D-06 | Weighted deterministic ranking v1 | Explainable; no training labels needed | P0 |
| D-07 | Separate Match / Confidence / Risk | Avoid misleading single score | P0 |
| D-08 | LLM only as supporting layer | Reduce hallucination | P0 |
| D-09 | Pre-indexed data as primary path | Predictable latency | P0 |
| D-10 | Benchmark before tuning | Prevent subjective optimization | P0 |
| D-11 | No microservices (and no Redis/Celery/ES for MVP) | No current value | P0 §54 |
| D-12 | No auth for hackathon demo | Focus on core value | P0 |
| D-13 | No price scoring initially | Data comparability risk | P0 |
| D-14 | Preserve raw source records | Traceability | P0 |
| D-15 | Tech stack: Next.js+TS, Tailwind, FastAPI, Pydantic, SQLAlchemy, Alembic, Polars/Pandas, SentenceTransformers-compatible embeddings (multilingual-e5-base), pytest, Vitest/Playwright, Docker Compose | Team fit, simplicity | P0 §53 |
| D-16 | Ingestion via CLI batch jobs (no Airflow) | Sufficient for MVP | P0 §51 |
| P1D-001 | Search unit is ProductOffering | Product-level relevance | P1S §47 · *Amended — HD-03* |
| P1D-002 | Canonical IDs are stable UUIDs | Source-independent API IDs | P1S |
| P1D-003 | Seed IDs use deterministic UUIDv5 | Regeneration preserves IDs | P1S · *UUIDv5 principle kept for organizer data (UUIDv5 of INN / lot_id); seed corpus superseded — HD-01* |
| P1D-004 | Seed files use JSONL | Simple, streamable | P1S · *Superseded for product data — HD-01* |
| P1D-005 | Benchmark uses CSV + qrels | Easy tooling | P1S |
| P1D-006 | Relevance scale 0/1/2 | Supports nDCG | P1S |
| P1D-007 | Query language primarily Russian | Deployment context | P1S |
| P1D-008 | Seed contains controlled negatives | Prevent easy benchmark | P1S · *Superseded — replay benchmark, HD-06* |
| P1D-009 | Market expansion represented in seed | Test known vs external early | P1S · *Superseded — curated real external candidates, HD-07* |
| P1D-010 | Contracts use JSON Schema (2020-12) | Language-neutral | P1S |
| P1D-011 | Organizer data enters through adapters | Avoid redesigning canonical model | P1S |

## 2. Proposed engineering decisions (this analysis)

| ID | Decision | Rationale | Alternatives considered | Resolves | Status |
|---|---|---|---|---|---|
| ED-01 | API scores are floats 0–1 (`match_score`, `confidence_score`; `score` alias until 1.0); UI shows integers 0–100 | Keeps P1S contract; UI matches STR | 0–100 ints in API | C-05 | Proposed |
| ED-02 | Persist **SearchRun + SearchResult** (request_id, intent, versions, results with contributions); `GET /suppliers/{id}?request_id=` and `GET /searches/{request_id}` | Enables US-08, profile context, compare, feedback, analytics, observability, reproducible explanations | Client-only state (breaks deep links, feedback validation) | G-07 | Proposed |
| ED-03 | Rule-based query parser is default and benchmark mode; LLM parser optional, schema-constrained, temp 0, cached, timed out → fallback | Determinism, offline, cost | LLM-first | C-11 | Proposed |
| ED-04 | Valid-time fields + `as_of` parameter across repositories used by search/ranking/evidence | Temporal holdout without leakage | Separate snapshot DB per cutoff (too heavy) | G-16, R-10 | **Accepted 2026-10-01 (HD-06)** — `as_of` = lot `publish_date` |
| ED-05 | DataSource id = slug; references via `source_name` + `source_external_id`/`source_record_id` | Follows latest spec; readable | UUID ids | C-03 | Proposed |
| ED-06 | Embeddings in `offering_embedding(offering_id, embedding_version, content_hash, vector)`; not in canonical offering | Model-agnostic canonical data; no recompute on projection rebuild | Column on offering or projection | C-14 | Proposed |
| ED-07 | Uniform error envelope; validation errors 422 with typed codes; 400 only malformed JSON | Consistency with FastAPI; simple FE handling | Keep 400 for QUERY_TOO_SHORT | C-06 | Proposed |
| ED-08 | Frontend types generated from FastAPI OpenAPI; JSON Schemas canonical for data files; equivalence test between both | Single source for API types, no hand-sync | Generate Pydantic from JSON Schema | — | Proposed |
| ED-09 | Aggregation = max over supplier's matched offerings; tie-break Match desc → Confidence desc → supplier_id asc | Prevents breadth bias; determinism | top-k mean, soft-OR | G-26, G-28 | Proposed |
| ED-10 | Lexical normalization `r/(r+k)` (k calibrated on dev); no per-query min-max | Comparable scores across queries | min-max, rank-based (RRF) | G-27 | Proposed |
| ED-11 | Monorepo: `/backend /frontend /contracts /data /benchmark /scripts /infra /docs` | P1S separation of contracts/data from code | Multi-repo | — | Proposed |
| ED-12 | Tooling: Python — uv (or pip-tools), ruff, mypy (strict on domain modules), pytest; TS — strict mode, ESLint, Vitest, Playwright; pre-commit | Fast, standard; type safety | Poetry, black+flake8 | — | Proposed |
| ED-13 | Semantic similarity floor (calibrated on dev) — below floor, candidates dropped | Avoid junk candidates | Fixed top-K only | G-29, EC-36 | Proposed |
| ED-14 | `is_known_supplier` = appears as winner/participant in provided AIS/organizer procurement data; `new_to_category` derived per query (Should) | Matches both STR notions pragmatically | Winner-only; time-windowed | C-04, OQ-17 | **Superseded 2026-10-01 (ADR-H1)** — known = SupplierHistory before `as_of` |
| ED-15 | Public demo protected by shared credential at reverse proxy + per-IP rate limit on `/search` | Cost/abuse control without user model | No protection | G-15, R-25 | Proposed |
| ED-16 | Structured JSON logging with request_id; per-stage timings; versions; no external observability stack | NFR-OBS with minimal infra | OpenTelemetry + collector | — | Proposed |
| ED-17 | Embedding model weights baked into API image; offline-safe mode flag | Offline demo | Download at startup | R-08 | Proposed |
| ED-18 | Personal-data minimization for individual entrepreneurs (store registry-public fields only; no contact scraping) | 152-ФЗ exposure | Full profile | G-32, R-17 | Proposed |
| ED-19 | `POST /search` accepts optional `intent_overrides`; UI filters are applied server-side via re-query (cheap with caps) | UC-08 without extra endpoint; consistent counts | Separate `/query/parse`; client-side filtering | C-07 | Proposed |
| ED-20 | Add `procurement` backend module (D7) | Temporal semantics, shared by search/ranking/suppliers | Keep inside `suppliers` | — | Proposed |
| ED-21 | Roadmap phases P0–P8 with stable `Pn-nnn` task IDs; legacy P1-001/P1-002/E-epics mapped | Small, reviewable tasks; unambiguous numbering | Keep epics | C-02, C-13 | **Superseded 2026-10-01 (HD-10)** — roadmap v2 |
| ED-22 | `SupplierRedirect(old_id → canonical_id)` on merges; APIs follow redirects | Stable references for qrels/search runs | Never merge after publish | G-30, R-18 | Proposed |
| ED-23 | Add `data_source.schema.json` and `error.schema.json` to contracts | Validated files need schemas | Validate sources ad hoc | C-18 | Proposed |
| ED-24 | Seed extension with procurement-record and evidence fixtures (synthetic, marked) | Test experience/confidence before organizer data | Wait for organizer data | G-18 | **Superseded 2026-10-01 (HD-01)** — real history available |
| ED-25 | UI locales: Russian (default, `/ru`) + English (`/en`), both LTR, via next-intl; Arabic dropped (the DS keeps logical utilities, so RTL can be re-added) | Users and data are Russian; English for reviewers/jury | Arabic RTL + English (DS default); Russian only | OQ-22, C-19 | Accepted (owner, 2026-09-29) |
| ED-26 | Design System installed in `/frontend` as a Next.js 16 app (same versions as the DS source: Next 16.3.6, React 19.2.8, Tailwind 4.3.3, next-intl 4.14.7, radix-ui 1.6.7); Inter (Latin + Cyrillic, self-hosted by next/font) replaces GraphikArabic, which has no Cyrillic glyphs; Saudi Riyal glyph and Hijri helpers removed | DS works unchanged on its native stack; Cyrillic coverage; no commercial-font licence dependency | Keep GraphikArabic for Latin + Inter for Cyrillic (mixed glyphs in one line); rebuild DS on another stack | A-111, R-21 | Accepted (owner delegated the choice, 2026-09-29) |

| ED-27 | Frontend runtime stack = the installed DS stack (ED-26) with **no new dependencies**: data through one typed client (`src/lib/api/client.ts`) with a **mock mode** (in-browser stand-in over a synthetic corpus, default) and a **live mode** (`NEXT_PUBLIC_API_MODE=live`); cross-screen state in a sessionStorage context; filters/overrides persisted with the search run (`request_id` URL) | UI can be built and demoed before the backend; one switch to go live; minimal surface for a hackathon | TanStack Query (+ Zustand); static mock pages | P0-005, US-08 | Accepted (owner, 2026-10-01) |
| ED-28 | UI patterns: **top navigation** shell (`TopBar`, not the sidebar `AppShell`); S-02 as **result cards + side filter panel** (drawer on mobile); "Why matched" as **inline expansion** in the card; demo states reachable through **demo queries + a mock-only scenario panel**; low-confidence notice threshold 0.4 (OQ-26 working assumption) | Demo clarity, four focused screens, explanation in ≤ 1 interaction (NFR-EXP-01) | Sidebar shell; dense table; side drawer for explanations; magic tokens in the query | P0-005, ED-19 | Accepted (owner, 2026-10-01) |
| ED-29 | P5-002A website discovery never scrapes web-search HTML result pages; search engines are used only through their official APIs (Brave Search API, Yandex Search API) activated by an env key. Compliant key-free providers: EGRUL-registered e-mail domain, Wikidata (OGRN P7011 → P856), legal-name domains (DNS-checked). checko.ru stays an OPTIONAL_SECONDARY_HINT. | robots.txt of Brave/Bing/Mojeek/DuckDuckGo disallows `/search` (checked 2026-10-02); DuckDuckGo html serves a bot challenge — bypassing it would be evasion. Owner chose the API-key path (2026-10-02). | Scrape HTML results (best coverage, violates site rules) | P5-002A | **Accepted (owner, 2026-10-02)** |
| ED-30 | Official-website identity rule (P5-002A): VERIFIED_STRONG = this company's INN or OGRN published on the site as self-identification; VERIFIED_COMPOSITE = exact legal-name core (word-bounded) + registered street & house, or + KPP. KPP alone, name similarity, an INN quoted only inside an impostor warning, and directory-like pages (≥3 other companies' INNs) never verify. A stored verified site is replaced only when it is re-checked and fails. | KPP is shared by every entity of a tax office; a fraud notice on a group site quoted the warned-about company's INN, KPP and address (golden case) | Accept KPP alone (task text) | P5-002A, A2 | Proposed |

## 3. Decision record template (for new entries)

```text
ID:            ED-xx / D-xx
Date / Owner:
Context:       (problem, constraints, linked OQ/C/G/R)
Decision:
Alternatives:
Consequences:  (what changes; which docs/tasks/contracts update)
Status:        Proposed | Accepted | Superseded by …
```
