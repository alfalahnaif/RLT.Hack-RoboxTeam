# Product Requirements

> ### Hackathon Day-1 amendment (2026-10-01, ADR-H1)
> Additional requirements from the [organizer briefing](../sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md) (rank 1); see [Baseline](../HACKATHON_EXECUTION_BASELINE.md):
>
> | ID | Requirement | Priority |
> |---|---|---|
> | FR-20 | Recommend suppliers for an **existing procurement lot** (`lot_id`) using its ТРУ items | Must |
> | FR-21 | **Supplier Pool Health** per category: unique/recent suppliers, top-1/top-3 share, verdict, "expand" action | Must |
> | FR-22 | **Market role** enrichment (manufacturer/distributor/dealer/supplier/reseller/other) with basis + evidence | Must (for selected suppliers) |
> | FR-23 | **Precomputed external expansion**: ~10 verified external suppliers for weak categories, offline | Must |
> | FR-24 | **Methodology view**: features, weights, data sources, records analyzed, replay metrics | Should |
> | FR-25 | Stakeholder levels (specialist / manager / analyst) in **one** interface | Must |
>
> Changed: FR-04 semantic retrieval → Should (only if it beats the baseline); FR-03 lexical retrieval runs on ТРУ items; FR-11 → FR-22;
> FR-16 live discovery stays out. §7 gates: "≥ 1 real dataset ingested" = all three organizer files; "≥ 20 benchmark queries" = replay cases (hundreds);
> performance gate = ≤ 10 s per recommendation (organizer), ≤ 5 s internal. Evaluation weights: integrity 30 · matching 25 · UI 10 (UI must not consume most time).

> Sources: [Phase 0](../sources/Supplier_Radar_Phase_0_Product_Technical_Foundation_EN.md) §6–15, 72, 78, 101–103 ·
> [Strategy](../sources/RLTHack_Initial_Strategy_Report.md) §3–4, 10–11, 16.
> IDs `UC/US/FR` are preserved from the sources. Items marked **[ER]** are Engineering Recommendations
> added by this analysis — not original requirements, not binding until accepted.

## 1. Primary goal

Enter a procurement requirement and receive the most relevant potential suppliers — known **and**
new — with clear reasons and evidence for each recommendation.

## 2. Core use cases

| ID | Use case | Description | Priority |
|---|---|---|---|
| UC-01 | Search suppliers | User enters a requirement (e.g. *"Interactive panel, 75 inches, for educational institutions"*); system returns ranked suppliers | Must |
| UC-02 | Discover new suppliers | User selects *External / New*; system returns suppliers outside the known base | Must |
| UC-03 | Inspect supplier | User opens a profile: company info, products, evidence, procurement history, sources | Must |
| UC-04 | Filter results | By manufacturer / distributor / region / new / existing | Must |
| UC-05 | Understand recommendation | "Why did this supplier appear?" — feature contributions + evidence | Must |
| UC-06 | Compare suppliers | 3–5 suppliers side by side (Strategy screen 4) | Should (see C-08) |
| UC-07 | Give relevance feedback | Mark relevant / not relevant / unsure | Should |
| UC-08 | Edit parsed intent **[source: Strategy §11]** | User corrects extracted category/product/attributes/region/type and re-runs | Must-ish — see C-07 |

## 3. User stories

| ID | Story | Covered by |
|---|---|---|
| US-01 | Describe a need in natural language without knowing classification codes | FR-01, FR-02 |
| US-02 | See most relevant suppliers first | FR-06 |
| US-03 | See suppliers not already in the existing supplier base | FR-08 |
| US-04 | Know whether a company is a Manufacturer or Distributor | FR-11 |
| US-05 | See evidence the company actually offers the product | FR-07 |
| US-06 | Filter by region and supplier type | FR-10 |
| US-07 | Understand why Supplier A ranks above Supplier B | FR-12 |
| US-08 | Open a supplier profile without rerunning the search | FR-09 + ED-02 |

## 4. Functional requirements

| ID | Requirement | Priority | Notes / Spec |
|---|---|---|---|
| FR-01 | Free-text procurement search | Must | 3–1000 chars (BR-28; see G-05 long specs) |
| FR-02 | Query parsing → structured intent | Must | Rule-based default; LLM optional (ED-03) |
| FR-03 | Keyword (lexical) retrieval | Must | PostgreSQL FTS (Russian) + pg_trgm |
| FR-04 | Semantic retrieval | Must | multilingual-e5-base behind adapter |
| FR-05 | Hybrid candidate generation | Must | Branches A–D, union, dedupe ([SEARCH_AND_RANKING](../architecture/SEARCH_AND_RANKING.md)) |
| FR-06 | Supplier ranking | Must | Deterministic weighted Match Score v1 |
| FR-07 | Supplier evidence | Must | Evidence entity with source/url/observed_at |
| FR-08 | Existing/New supplier classification | Must | `is_known_supplier`; definition OQ-17 |
| FR-09 | Supplier profile | Must | `GET /suppliers/{id}` |
| FR-10 | Region/type filters | Must | Semantics of `region` filter: OQ-19 |
| FR-11 | Manufacturer/Distributor classification | Must | `supplier_type` + verification evidence (ГИСП) |
| FR-12 | Ranking explanation | Must | Reason codes + contribution map + templates |
| FR-13 | Search analytics | Should | Built on persisted search runs (ED-02) |
| FR-14 | Supplier comparison | Should | UC-06 |
| FR-15 | User relevance feedback | Should | `POST /feedback` |
| FR-16 | Live external discovery | Could | Async only, never default path (D-09) |
| FR-17 **[ER]** | Market-expansion summary (known vs external counts, type breakdown) in results | Should | Strategy §4/§10 demo output; not an FR in Phase 0 — see G-12 |
| FR-18 **[ER]** | Submit edited/overridden parsed intent | Should | Needed for UC-08 (C-07) |
| FR-19 **[ER]** | Benchmark runner & evaluation report (CLI) | Must | Phase 0 lists it under scope/acceptance, not as FR — made explicit |

## 5. Scope (MoSCoW)

### Must
- **Search:** text input, query normalization, keyword search, semantic search, filters.
- **Ranking:** hybrid score, category match, attribute match, geography, experience.
- **Supplier:** identity, product evidence, company type, procurement history.
- **Market expansion:** source flag, existing/new classification.
- **Explainability:** reason codes, source evidence.
- **Evaluation:** keyword baseline, benchmark runner, ranking metrics.

### Should
Supplier comparison · relevant/not-relevant feedback · query analytics · search session history ·
CSV export · richer supplier profile · external source refresh.

### Could
LLM query expansion · LLM explanation paraphrasing · Learning-to-Rank · live web discovery ·
saved searches · supplier alerts · procurement-category analytics · automated category mapping.

### Out of scope (MVP)
Multi-tenancy · billing · subscription plans · full RBAC · complex admin dashboard · Kubernetes ·
microservices · event streaming · autonomous agents · supplier messaging · automated contracting ·
recommendation emails · graph database · full procurement workflow · complex risk model ·
dynamic pricing intelligence · mobile app · chatbot as main interface · large dashboards ·
multi-agent architecture "for appearance" · scraping dozens of low-quality sites.

## 6. Product acceptance criteria (core MVP functional when it can)

1. Accept procurement text.
2. Extract basic structured intent.
3. Retrieve candidates from the dataset.
4. Combine lexical and semantic retrieval.
5. Rank candidates.
6. Return Top 20 results.
7. Show evidence for Top 5.
8. Identify new vs existing suppliers.
9. Open a supplier profile.
10. Run a benchmark against a keyword baseline.

## 7. MVP success gates (all must pass)

| Area | Gate |
|---|---|
| Product | End-to-end search works · supplier profile works · market expansion visible |
| Data | ≥1 real dataset ingested · ≥1 external/enrichment source used · entity resolution works |
| Retrieval | Lexical works · semantic works |
| Ranking | Deterministic · feature contributions explainable |
| Evaluation | ≥20 meaningful benchmark queries (target 30) · baseline + challenger exist · metrics generated automatically |
| Performance | Indexed search P95 ≤ 2.5 s · full search P95 ≤ 5 s |
| Reliability | External source failure does not break indexed search |
| Demo | Full demo runs from clean start without manual DB editing |

Benchmark targets (nDCG, recall, discovery, explainability, evidence): [EVALUATION.md §6](../architecture/EVALUATION.md#6-success-targets-phase-0-71).

## 8. Future requirements (not MVP — do not build)

| Horizon | Items |
|---|---|
| Deferred product | Saved searches, procurement alerts, watchlists, comparison reports, sourcing collaboration |
| Deferred intelligence | LTR, feedback-trained reranker, supplier similarity, taxonomy learning, price intelligence, risk modeling, reliability score |
| Pilot | Authentication, organizations, RBAC, admin tools, automated/scheduled ingestion, source health, saved searches, analytics, exports, monitoring/alerts/backups, CI/CD, rate limiting, audit logs, secret management |
| Production SaaS | Multi-tenancy, usage limits, billing, API keys, webhooks, workers/queues/Redis, dedicated search cluster, model registry, drift monitoring, SSO, fine-grained RBAC, tenant isolation, SLA, retention policies |
| Search evolution | OpenSearch (when search bottleneck proven) · queue+worker (async workload) · Redis (multi-instance cache) · LTR (enough labels) |

Rule: every technology is introduced only when it solves a **proven** problem (Phase 0 §104).
