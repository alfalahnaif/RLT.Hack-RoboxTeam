# Supplier Radar — Phase 0: Product & Technical Foundation

**Status:** Implementation Blueprint  
**Project:** RLT.Hack 2026  
**Working Product Name:** Supplier Radar  
**Core Principle:** **Value → Speed → Simplicity → Measurability → Scalability**

---

# 1. Phase 0 Master Roadmap

We will not follow the original sequence blindly:

`PRD → Scope → Data → Retrieval → Ranking → Architecture → APIs → Benchmark → Backlog`

The engineering sequence below is more practical:

| # | Stage | Why Now? | Deliverable |
|---|---|---|---|
| 0 | Problem + Assumption Contract | Prevent building for an unverified problem | Problem Statement + Assumption Log |
| 1 | Success & Evaluation Contract | Define success before implementation | Metrics + Benchmark Contract |
| 2 | Product Vision + PRD | Define who we serve and what we build | PRD v1 |
| 3 | MVP Scope | Prevent feature creep | Must/Should/Could/Out |
| 4 | Core User Flow | Define the end-to-end experience | User/System Flow |
| 5 | Data Contract | Search design depends on the data unit | Canonical Data Model |
| 6 | Retrieval Design | Define how candidates are discovered | Retrieval Spec |
| 7 | Candidate Generation | Control recall, latency, and candidate volume | Candidate Pipeline |
| 8 | Ranking + Explainability | Rank results in a defensible way | Ranking Spec |
| 9 | Architecture | Build the smallest architecture that satisfies the requirements | Architecture v1 |
| 10 | Interfaces + APIs | Fix contracts before parallel implementation | API Contracts |
| 11 | Benchmark Design | Measure the system reproducibly | Benchmark Dataset Spec |
| 12 | Risks + Decisions | Avoid repeatedly reopening decisions | Logs & Register |
| 13 | Development Backlog | Convert the design into implementation work | Prioritized Backlog |
| 14 | Execution Plan | Define actual build order | Phase 1–6 Plan |

## Why Evaluation Comes Early

One of the biggest mistakes we can make is building a search system that looks impressive but cannot prove that it performs better than traditional search.

Before adding AI, we must define:

> What exactly is a relevant supplier?

And:

> How will we prove that Supplier Radar finds relevant suppliers better than a traditional baseline?

---

# 2. Problem Definition

## 2.1 Core Problem

A procurement specialist has a procurement requirement but lacks a fast and trustworthy way to transform that requirement into:

**A comprehensive, ranked, and verifiable shortlist of relevant suppliers, manufacturers, and distributors.**

Relevant information is fragmented across:

- procurement data,
- company data,
- product catalogs,
- manufacturer registries,
- open sources,
- historical supplier activity.

Traditional supplier search often depends on:

- exact keywords,
- category codes,
- previously known companies,
- rigid filters.

This creates:

**Poor Discovery + Limited Supplier Pool + Manual Verification.**

---

## 2.2 Primary User

### Procurement / Sourcing Specialist

A person responsible for identifying potential suppliers before or during procurement preparation.

### Job To Be Done

> When I have a procurement requirement, I want to quickly obtain a relevant and verifiable supplier shortlist so I can understand the market without manually searching multiple disconnected sources.

---

## 2.3 Secondary Users

### Category / Procurement Analyst

Needs to:

- analyze the market,
- compare companies,
- discover new suppliers,
- understand supplier competition.

### Procurement Manager

Needs to:

- assess sourcing quality,
- monitor supplier coverage,
- understand dependency on a limited supplier pool.

### Data / System Administrator

Not a primary MVP user.

Later responsibilities may include:

- monitoring data sources,
- managing data refreshes,
- monitoring ingestion failures,
- managing data quality.

---

# 3. Problem Priority

| Level | Problem |
|---|---|
| **Core** | Find and rank suppliers relevant to a procurement requirement |
| **Core** | Discover suppliers outside the already known supplier pool |
| **Core** | Provide evidence explaining why each supplier is relevant |
| Secondary | Identify Manufacturer / Distributor / Supplier |
| Secondary | Aggregate company data from multiple sources |
| Secondary | Compare suppliers |
| Secondary | Assess supplier profile completeness |
| Nice-to-have | Price intelligence |
| Nice-to-have | Automatic RFQ |
| Nice-to-have | Supplier outreach |
| Nice-to-have | Recommendation alerts |
| Nice-to-have | Contract risk scoring |
| Nice-to-have | Forecasting |

## Initial Product Focus

> **Given a procurement requirement, return a ranked, evidence-backed shortlist of relevant known and new suppliers.**

If we cannot do this well, additional features do not matter.

---

# 4. Product Vision

## Product Vision Statement

> **Supplier Radar turns a procurement requirement into an explainable market map of relevant suppliers, manufacturers, and distributors by combining procurement data, company data, product evidence, and semantic retrieval.**

## Who Is the Product For?

Procurement professionals.

## What Does It Do?

It turns a procurement description into a supplier list that is:

- relevant,
- ranked,
- verified,
- explainable.

## Why Is It Better Than Traditional Search?

It does not rely only on keyword matching.

It combines:

**Lexical Search + Semantic Search + Structured Filters + Procurement History + Evidence.**

---

# 5. Core Value Proposition

The value proposition is not:

> AI Search for suppliers.

It is:

> **Discover more relevant suppliers with evidence you can trust.**

Three core value pillars:

### Discovery

Find companies the user did not already know.

### Relevance

Rank suppliers according to the current procurement requirement.

### Trust

Show the source and evidence behind each recommendation.

---

# 6. PRD — Product Requirements Document

## 6.1 Primary User Goal

Enter a procurement requirement and receive the most relevant potential suppliers with clear reasons for recommendation.

---

## 6.2 Main Use Cases

### UC-01 Search Suppliers

The user enters:

> Interactive panel, 75 inches, for educational institutions.

The system returns ranked suppliers.

### UC-02 Discover New Suppliers

The user selects:

**External / New Suppliers**

The system returns suppliers discovered outside the already known supplier base.

### UC-03 Inspect Supplier

The user opens a Supplier Profile and sees:

- company information,
- products,
- evidence,
- procurement history,
- sources.

### UC-04 Filter Results

Examples:

- Manufacturer
- Distributor
- Region
- New Supplier
- Existing Supplier

### UC-05 Understand Recommendation

The user needs to understand:

> Why did this supplier appear?

The system exposes feature contributions and supporting evidence.

---

# 7. User Stories

### US-01

As a procurement specialist, I want to describe a purchasing need in natural language so I do not need to know all classification codes in advance.

### US-02

I want the most relevant suppliers shown first.

### US-03

I want to see suppliers that are not already present in the existing supplier base.

### US-04

I want to know whether a company is a Manufacturer or Distributor.

### US-05

I want evidence showing that the company actually offers the requested product.

### US-06

I want to filter companies by region and supplier type.

### US-07

I want to understand why Supplier A ranks above Supplier B.

### US-08

I want to open a supplier profile without rerunning the search.

---

# 8. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Free-text procurement search | Must |
| FR-02 | Query parsing | Must |
| FR-03 | Keyword retrieval | Must |
| FR-04 | Semantic retrieval | Must |
| FR-05 | Hybrid candidate generation | Must |
| FR-06 | Supplier ranking | Must |
| FR-07 | Supplier evidence | Must |
| FR-08 | Existing/New supplier classification | Must |
| FR-09 | Supplier profile | Must |
| FR-10 | Region/type filters | Must |
| FR-11 | Manufacturer/Distributor classification | Must |
| FR-12 | Ranking explanation | Must |
| FR-13 | Search analytics | Should |
| FR-14 | Supplier comparison | Should |
| FR-15 | User relevance feedback | Should |
| FR-16 | Live external discovery | Could |

---

# 9. Non-Functional Requirements

## Performance

Indexed search:

**P95 ≤ 2.5 seconds**

End-to-end search including optional query parsing:

**P95 target ≤ 5 seconds**

## Reliability

Failure of an external data source must not break core indexed search.

## Determinism

The same:

- dataset,
- query,
- version,
- ranking configuration

should produce reproducible results.

## Explainability

Every top result must include:

- reason codes,
- source evidence.

## Observability

Each request receives a:

`request_id`

with:

- timings,
- candidate counts,
- ranking version,
- parsing version.

## Data Traceability

Any important external fact must include:

- source,
- URL/reference,
- observed_at.

## Security

All external content must be treated as:

**Untrusted Input.**

---

# 10. Constraints

### Time

The hackathon implementation window is limited.

### Unknown Organizer Dataset

The actual schema has not yet been provided.

Therefore, we define a:

**Canonical Internal Schema**

and build an adapter that maps organizer data into it.

### External Connectivity

We do not assume internet access or external APIs will always be stable.

### Data Quality

We do not assume that:

- INN is always available,
- categories are standardized,
- product descriptions are clean,
- company names are normalized.

---

# 11. Acceptance Criteria — Product

The core MVP is considered functional when it can:

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

---

# 12. Scope Definition

## Must Have

### Search

- procurement text input,
- query normalization,
- keyword search,
- semantic search,
- filters.

### Ranking

- hybrid score,
- category match,
- attribute match,
- geography,
- experience.

### Supplier

- identity,
- product evidence,
- company type,
- procurement history.

### Market Expansion

- source flag,
- existing/new classification.

### Explainability

- reason codes,
- source evidence.

### Evaluation

- keyword baseline,
- benchmark runner,
- ranking metrics.

---

# 13. Should Have

- Supplier comparison
- Relevant / Not Relevant feedback
- Query analytics
- Search session history
- CSV export
- Richer supplier profile
- External source refresh

---

# 14. Could Have

- LLM-generated query expansion
- LLM explanation paraphrasing
- Learning-to-Rank
- Live web discovery
- Saved searches
- Supplier alerts
- Procurement-category analytics
- Automated category mapping

---

# 15. Out of Scope — MVP

Do not implement now:

- Multi-tenancy
- Billing
- Subscription plans
- Full RBAC
- Complex admin dashboard
- Kubernetes
- Microservices
- Event streaming
- Autonomous agents
- Supplier messaging
- Automated contracting
- Recommendation emails
- Graph database
- Full procurement workflow
- Complex risk model
- Dynamic pricing intelligence
- Mobile app

These are not Phase 1 problems.

---

# 16. Core User Flow

```text
User Procurement Requirement
            ↓
      Query Validation
            ↓
     Query Normalization
            ↓
     Query Understanding
            ↓
 Structured Search Intent
            ↓
     Candidate Retrieval
       ↙          ↘
 Lexical          Semantic
       ↘          ↙
        Candidate Union
             ↓
       Hard Filtering
             ↓
      Supplier Aggregation
             ↓
         Ranking
             ↓
    Confidence / Evidence
             ↓
      Explainability
             ↓
         Results
             ↓
      Supplier Profile
```

---

# 17. Query Understanding

Input:

```json
{
  "query": "Interactive panel, 75 inches, for schools in Saint Petersburg"
}
```

Canonical interpretation:

```json
{
  "product": "interactive panel",
  "category_terms": [
    "interactive panels",
    "educational equipment"
  ],
  "attributes": {
    "screen_size_inches": 75
  },
  "region": "Saint Petersburg",
  "supplier_types": [],
  "mandatory_constraints": []
}
```

### Rule

LLM extraction is not treated as a verified fact.

It is only:

**Query Interpretation.**

---

# 18. Data Strategy

We need five main data groups.

### Procurement Data

- procurement title,
- description,
- category,
- buyer,
- date,
- winner/participants.

### Supplier Data

- legal identity,
- names,
- location,
- status,
- business classification.

### Product / Offering Data

- supplier,
- product,
- description,
- category,
- attributes.

### Evidence Data

- source,
- URL,
- claim,
- observation date.

### Search / Evaluation Data

- query,
- candidates,
- ranking scores,
- relevance labels.

---

# 19. Canonical Data Model

## Supplier

```text
supplier
──────────────────────────
id UUID
name
normalized_name
inn
ogrn
kpp
supplier_type
legal_status
region_code
region_name
city
website
okved_codes[]
is_known_supplier
profile_completeness
created_at
updated_at
```

### supplier_type

```text
manufacturer
distributor
supplier
service_provider
unknown
```

---

# 20. ProductOffering

This will be the main search unit.

```text
product_offering
──────────────────────────
id UUID
supplier_id FK
title
normalized_title
description
category_code
category_name
attributes JSONB
brand
model
source_id
source_url
source_observed_at
embedding VECTOR
created_at
updated_at
```

### Important Decision

We will not create one embedding for the entire company.

A large company may offer thousands of products.

Search should operate on:

> **Product Offering**

and then aggregate results back to the Supplier level.

This should significantly improve search precision.

---

# 21. Procurement History

```text
procurement_record
──────────────────────────
id
procurement_external_id
supplier_id
title
description
category_code
region
amount
currency
role
procurement_date
source_id
```

`role` examples:

```text
winner
participant
supplier
unknown
```

---

# 22. Evidence

```text
evidence
──────────────────────────
id
supplier_id
offering_id nullable
evidence_type
claim
source_name
source_url
source_record_id
observed_at
confidence
```

Example:

```text
evidence_type = PRODUCT_CATALOG
claim = "75-inch interactive panels are listed."
```

---

# 23. Data Source

```text
data_source
──────────────────────────
id
name
source_type
base_url
trust_level
last_sync_at
status
```

---

# 24. Search Document

For performance, create a search projection:

```text
supplier_search_document
──────────────────────────
offering_id
supplier_id
search_text
search_vector
embedding
category_code
region_code
supplier_type
source_flags
updated_at
```

This is not the source of truth.

It is a:

**Search Projection.**

---

# 25. Relationships

```text
Supplier
   │
   ├── ProductOffering
   │       └── Evidence
   │
   ├── ProcurementRecord
   │
   └── Evidence
```

---

# 26. Required Fields

Minimum fields required to make a supplier searchable:

- supplier_id,
- supplier name,
- offering/product text.

Preferred:

- INN,
- category,
- region,
- supplier type,
- source.

---

# 27. Data Normalization

### Company Names

Original:

`ООО "РОМАШКА ТЕХНОЛОГИИ"`

Normalized alias:

`ромашка технологии`

The original legal name is always preserved.

### Text

- Unicode normalization
- lowercase search representation
- punctuation normalization
- whitespace normalization
- optional `ё → е` search alias

### Categories

Each source category should map to a:

`canonical_category`

when possible.

---

# 28. Entity Resolution / Deduplication

Confidence hierarchy:

### Level 1

Exact INN.

**Auto merge.**

### Level 2

Exact OGRN.

**Auto merge.**

### Level 3

Normalized:

`Company Name + Domain/Address`

High-confidence merge.

### Level 4

Fuzzy:

`Name + Region + Business Category`

Do not perform a destructive merge automatically.

Store as:

`possible_match`.

### Principle

Never discard source records.

Always preserve:

```text
Canonical Entity
        ↑
Source Records
```

---

# 29. Data Quality Flags

```text
MISSING_INN
MISSING_CATEGORY
UNKNOWN_SUPPLIER_TYPE
STALE_DATA
CONFLICTING_REGION
UNVERIFIED_PRODUCT
DUPLICATE_CANDIDATE
```

---

# 30. Retrieval Strategy

| Approach | Advantage | Limitation | MVP |
|---|---|---|---|
| Exact keyword | Very fast | Weak recall | Yes |
| Full-text | Strong textual retrieval | Synonym gap | Yes |
| Filters | Precise | Requires structured data | Yes |
| Semantic | Better meaning matching | May return loosely related results | Yes |
| Hybrid | Best precision/recall balance | Slightly more complexity | **Chosen** |
| Knowledge Graph | Strong relational modeling | Expensive to build now | Later |
| LLM Retrieval | Flexible | Latency/hallucination | No |
| LLM Agent Search | Attractive demo | Unreliable | No |

## Phase 0 Decision

> **Hybrid Retrieval = Full-Text + Semantic + Structured Filters.**

---

# 31. Lexical Retrieval

PostgreSQL:

- FTS
- `tsvector`
- Russian dictionary
- `pg_trgm`

Use:

- exact product terms,
- phrase matching,
- trigram similarity,
- category matching.

---

# 32. Semantic Retrieval

Use a multilingual embedding model.

Default model class:

**multilingual-e5-base**

Requirements:

- strong Russian support,
- CPU compatibility,
- easy SentenceTransformers integration.

The model must sit behind an adapter, not inside core business logic.

---

# 33. Candidate Generation

Do not rank millions of suppliers directly.

Use:

```text
Large Dataset
    ↓
Retrieval
    ↓
~300–500 Candidates
    ↓
Ranking
    ↓
Top 20
```

---

# 34. Retrieval Branches

### Branch A — Lexical

Top:

`200 offerings`

### Branch B — Semantic

Top:

`200 offerings`

### Branch C — Exact Category

Top:

`100 suppliers`

### Branch D — Historical Similarity

If data is available:

`100 suppliers`

---

# 35. Candidate Union

```text
Lexical Candidates
        +
Semantic Candidates
        +
Category Candidates
        +
Historical Candidates
        ↓
Deduplication
        ↓
≤ 500 Suppliers
```

Then:

`Top 100` enter full ranking.

Then:

`Top 20` are shown to the user.

These numbers are tunable parameters, not permanent constants.

---

# 36. Hard Filters

Use a hard filter only when the procurement requirement makes it mandatory.

Examples:

- inactive company,
- explicitly required region,
- mandatory certification,
- prohibited supplier type.

### Important

Region should usually not be a hard filter.

A company in Moscow may still deliver to Saint Petersburg.

Therefore:

**Location = soft signal**

unless local presence is explicitly required.

---

# 37. Ranking System

Initial version:

**Deterministic Weighted Ranking**

Not an ML model.

Why?

- faster,
- configurable,
- explainable,
- no training labels required,
- suitable for the hackathon.

---

# 38. Match Score v1

Each feature is normalized to:

`0 → 1`

Formula:

```text
MatchScore =
  0.30 SemanticRelevance
+ 0.20 LexicalRelevance
+ 0.15 CategoryMatch
+ 0.15 AttributeCoverage
+ 0.08 ProcurementExperience
+ 0.05 GeographicFit
+ 0.04 SupplierTypeFit
+ 0.03 DeliveryFit
```

Final result:

`0–100`.

---

# 39. Weight Behavior

If a feature is not applicable, such as Location when the user did not specify a region:

Do not assign everyone a zero.

Remove that weight and perform:

**weight renormalization.**

---

# 40. Certifications

If a certification is mandatory:

**Eligibility Constraint.**

If it is only beneficial:

**Ranking Feature.**

It should not have a fixed weight for every query.

---

# 41. Price

Do not include Price in Ranking v1.

Price comparison without:

- quantity,
- configuration,
- VAT,
- delivery,
- date,
- contract conditions

can be misleading.

Add it later only if structured, comparable price data becomes available.

---

# 42. Reliability

A larger number of historical contracts does not automatically mean:

“better company.”

Use historical procurement activity primarily as relevance evidence.

A separate:

**Reliability Score**

can be introduced later.

---

# 43. Confidence Score

Match is different from Confidence.

Example:

```text
Match: 94
Confidence: 55
```

Initial formula:

```text
Confidence =
  0.30 ProductEvidenceQuality
+ 0.25 LegalIdentityVerification
+ 0.15 SourceRecency
+ 0.15 MultiSourceAgreement
+ 0.15 ProfileCompleteness
```

---

# 44. Risk Flags

Keep risk separate from Match Score.

```text
LOW_EVIDENCE
STALE_INFORMATION
UNVERIFIED_MANUFACTURER
UNKNOWN_LEGAL_STATUS
AMBIGUOUS_ENTITY
NO_PROCUREMENT_HISTORY
```

---

# 45. Explainability Layer

Do not ask an LLM to invent an explanation.

Generate structured reason codes first:

```json
{
  "reason_codes": [
    "EXACT_CATEGORY",
    "ATTRIBUTE_MATCH",
    "RELEVANT_PROCUREMENT_HISTORY",
    "VERIFIED_MANUFACTURER"
  ]
}
```

Then render a template:

> This supplier ranks highly because its catalog contains products matching the requested category and attributes, and relevant procurement history was found.

---

# 46. Why Supplier A Ranks Above Supplier B

Compute feature contributions.

Example:

```text
Supplier A
Semantic       +27
Category       +15
Attributes     +14
Experience      +6

Supplier B
Semantic       +25
Category       +15
Attributes      +7
Experience      +2
```

The UI can say:

> Supplier A ranks higher mainly because it matches more requested attributes and has stronger relevant procurement experience.

This explanation is derived directly from the ranking engine.

---

# 47. LLM Role

## Use LLMs For

- query extraction,
- synonym generation if needed,
- optional natural-language explanation.

## Do Not Use LLMs For

- company verification,
- legal status,
- source of truth,
- final supplier ranking,
- unsupported evidence generation.

## Fallback

If the LLM is unavailable:

Search must still work.

---

# 48. System Architecture

Chosen architecture:

> **Modular Monolith.**

Not microservices.

```text
┌──────────────────────┐
│      Next.js UI      │
└──────────┬───────────┘
           │ REST
┌──────────▼────────────────────────────┐
│              FastAPI                  │
│                                       │
│ Query Module                          │
│ Search Module                         │
│ Ranking Module                        │
│ Supplier Module                       │
│ Evidence Module                       │
│ Evaluation Module                     │
└───────┬───────────────────────────────┘
        │
┌───────▼───────────────────────────────┐
│ PostgreSQL                            │
│                                      │
│ Relational Data                      │
│ PostgreSQL FTS                       │
│ pg_trgm                              │
│ pgvector                             │
└───────────────────────────────────────┘

       Data Ingestion
             │
    ┌────────▼─────────┐
    │ Source Adapters  │
    └──────────────────┘
```

---

# 49. Why Modular Monolith?

A small team and short deadline make microservices unnecessary.

Microservices would add:

- network complexity,
- service discovery,
- distributed logging,
- deployment complexity,
- versioning overhead,
- harder debugging.

without meaningful MVP value.

Modular boundaries still prevent a spaghetti monolith.

---

# 50. Backend Modules

```text
app/
  query/
  search/
  ranking/
  suppliers/
  evidence/
  ingestion/
  evaluation/
  shared/
```

Each module owns:

- schemas,
- service,
- repository,
- domain logic.

---

# 51. Data Ingestion

No Airflow is needed for the MVP.

```text
Source
   ↓
Adapter
   ↓
Raw Record
   ↓
Normalize
   ↓
Entity Resolve
   ↓
Canonical DB
   ↓
Search Projection
   ↓
Embedding Generation
```

CLI jobs are sufficient.

Examples:

```text
ingest organizer_dataset
ingest external_source
rebuild search_index
build_embeddings
```

---

# 52. Live External Search

Do not make live external search the default path.

It may introduce:

- latency,
- blocking,
- rate limits,
- website changes.

The primary product should use:

**Pre-indexed Data.**

Later, we may add:

**Search Open Market**

as secondary asynchronous enrichment.

---

# 53. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js + TypeScript | Fast product UI development |
| UI | Tailwind | Fast implementation |
| Backend | FastAPI | Strong fit for Python/Data/ML |
| Validation | Pydantic | Strong API contracts |
| DB | PostgreSQL | Relational + search |
| Vector | pgvector | Avoid a separate vector DB |
| Text Search | PostgreSQL FTS | Simplicity |
| Fuzzy | pg_trgm | Company/product matching |
| ORM | SQLAlchemy | Mature and explicit |
| Migrations | Alembic | Versioned DB changes |
| Data | Polars/Pandas | EDA/ETL |
| Embeddings | SentenceTransformers-compatible model | Local and simple |
| Testing | pytest | Backend testing |
| Frontend tests | Vitest/Playwright | Core product flows |
| Packaging | Docker Compose | Reproducibility |

---

# 54. What We Explicitly Do Not Add

## Redis

Not now.

Introduce it only when there is a proven need for:

- distributed cache,
- queue,
- rate limiter.

## Elasticsearch / OpenSearch

Not for the MVP.

PostgreSQL is sufficient to validate the product.

## Celery

Not required now.

Batch CLI jobs are sufficient.

---

# 55. Deployment

Hackathon:

```text
Docker Compose
├── frontend
├── api
└── postgres
```

Production pilot later:

```text
Managed PostgreSQL
API Container
Frontend
Object Storage
Worker
Monitoring
```

---

# 56. API Design

API prefix:

`/api/v1`

## POST /search

### Input

```json
{
  "query": "Interactive panel, 75 inches",
  "filters": {
    "region": null,
    "supplier_type": null,
    "market_scope": "all"
  },
  "limit": 20
}
```

### Output

```json
{
  "request_id": "uuid",
  "parsed_query": {},
  "total_candidates": 318,
  "results": [],
  "timings": {
    "retrieval_ms": 180,
    "ranking_ms": 35
  },
  "warnings": []
}
```

### Errors

- `400 QUERY_TOO_SHORT`
- `422 INVALID_FILTER`
- `503 SEARCH_UNAVAILABLE`

---

# 57. GET /suppliers/{supplier_id}

Returns:

- company,
- products,
- history,
- evidence,
- source metadata,
- confidence,
- risk flags.

Errors:

- `404 SUPPLIER_NOT_FOUND`

---

# 58. GET /suppliers/{supplier_id}/evidence

Returns supplier evidence separately.

---

# 59. GET /meta/filters

Returns:

- regions,
- supplier types,
- source types,
- categories.

---

# 60. POST /feedback

Should-have, not a blocker.

```json
{
  "request_id": "...",
  "supplier_id": "...",
  "relevance": "relevant"
}
```

Allowed values:

```text
relevant
not_relevant
unsure
```

This can later become training data.

---

# 61. GET /health

Checks:

- API,
- DB,
- search index.

---

# 62. Internal Ranking API

Do not expose:

`POST /rank`

as a public endpoint.

Ranking remains internal to `/search`.

If needed for experiments:

```text
/api/v1/debug/rank
```

available only when:

`DEBUG=true`.

---

# 63. API Design Principles

- versioned APIs,
- Pydantic validation,
- typed error codes,
- correlation/request IDs,
- pagination,
- ISO-8601 timestamps,
- no direct database entities in API responses,
- API DTOs separated from ORM models.

---

# 64. Benchmark Strategy

Build a baseline before improving the system.

### Baseline

**PostgreSQL keyword/full-text search only.**

### Challenger

**Hybrid Supplier Radar.**

---

# 65. Benchmark Dataset

Fast target:

**30 Procurement Queries**

Split:

```text
20 Development
10 Frozen Holdout
```

Do not tune ranking weights using the holdout set.

---

# 66. Benchmark Query Schema

```text
query_id
query_text
category
cutoff_date
mandatory_attributes
relevant_supplier_ids
relevance_grade
notes
```

---

# 67. Graded Relevance

Use graded relevance rather than simple binary labels:

```text
0 = irrelevant
1 = plausible supplier
2 = strongly relevant supplier
```

This allows us to use:

**nDCG.**

---

# 68. Ground Truth

Use two sources.

### Weak Labels

- winner,
- participants,
- previous similar procurements.

### Human Judgment

Manually review a small subset of results.

Important:

> Winner ≠ only relevant supplier.

Do not treat the winner as absolute truth.

---

# 69. Temporal Holdout

Strongest validation experiment:

```text
Historical Procurement
        ↓
Cutoff Date
        ↓
Hide Future Supplier Outcome
        ↓
Run Supplier Radar using past data
        ↓
Was eventual supplier discovered?
```

This reduces data leakage.

---

# 70. Metrics

## Precision@5

Among the top 5 results, how many suppliers are relevant?

## Recall@20

Among all relevant suppliers, how many were retrieved in the top 20?

## nDCG@10

Measures:

**Ranking Quality + Position.**

Primary ranking metric.

## MRR

Measures the rank position of the first relevant supplier.

## Coverage

Measures how often the system returns enough candidates.

## Evidence Coverage

Measures how many Top 5 results contain supporting evidence.

## Latency

Track P50 and P95.

---

# 71. Benchmark Success Target

Supplier Radar should:

## Ranking

Beat the Keyword Baseline on:

`nDCG@10`

with an initial target of:

**≥ 10% relative improvement**

while not reducing Recall@20 by more than:

**5%**

## Discovery

For at least 70% of suitable queries, return:

**≥ 2 evidence-backed external/new suppliers**

if the available data supports it.

## Explainability

**100% of Top 5**

must contain reason codes.

## Evidence

**≥ 90% of Top 5**

must contain source evidence.

---

# 72. MVP Success Criteria

We consider the MVP successful when all gate conditions are met.

## Product

- End-to-end search works.
- Supplier profile works.
- Market Expansion is visible.

## Data

- At least one real dataset is ingested.
- At least one external/enrichment source is used.
- Entity resolution works.

## Retrieval

- Lexical retrieval works.
- Semantic retrieval works.

## Ranking

- Deterministic ranking works.
- Feature contributions are explainable.

## Evaluation

- At least 20 meaningful benchmark queries if 30 cannot be reached.
- Baseline exists.
- Challenger exists.
- Metrics are generated automatically.

## Performance

- Indexed search P95 ≤ 2.5 sec target.
- Full search P95 ≤ 5 sec target.

## Reliability

- External source failure does not break indexed search.

## Demo

The full demo runs without manual database editing.

---

# 73. Technical Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Organizer dataset poor | High | High | Canonical adapter layer |
| Missing IDs | High | High | Multi-stage entity resolution |
| Poor search relevance | Medium | High | Hybrid retrieval + benchmark |
| No ground truth | High | High | Weak labels + human grading |
| LLM hallucination | Medium | High | LLM not source-of-truth |
| External API unavailable | High | Medium | Pre-index/cache data |
| Search latency | Medium | Medium | Candidate limits + indexes |
| Embedding model slow | Medium | Medium | Precompute vectors |
| Duplicate suppliers | High | Medium | INN/OGRN/entity resolver |
| Unknown categories | High | Medium | Semantic fallback |
| Internet unavailable | Medium | High | Local indexed demo |
| Data leakage in benchmark | Medium | High | Temporal cutoff |
| Scraping restrictions | Medium | High | Approved/allowed sources only |
| Scope creep | High | High | MoSCoW + scope freeze |
| Demo failure | Medium | High | Docker + frozen demo queries |
| Dataset larger than expected | Medium | Medium | Batched ingestion/indexing |

---

# 74. Security Risks

Even a hackathon MVP should address obvious risks.

## External Content

Never trust external HTML.

## LLM

External page content must not be able to:

- call tools,
- execute instructions,
- modify ranking.

## API

Validate:

- lengths,
- enum values,
- pagination,
- filter values.

## URLs

External adapters use controlled source definitions.

## Secrets

Environment variables only.

Never commit API keys.

---

# 75. Assumption Log

| ID | Assumption | Status |
|---|---|---|
| A-01 | Organizer data contains identifiable suppliers | Unverified |
| A-02 | Product/procurement description text exists | Unverified |
| A-03 | Russian is the dominant query language | Likely |
| A-04 | Historical procurements exist | Unverified |
| A-05 | External company data can legally be accessed | Must verify |
| A-06 | Discovering new suppliers is valuable to the organizer | Strong but verify |
| A-07 | Manufacturer status can be determined from available sources | Partial |
| A-08 | Price data is incomplete/non-comparable | Likely |
| A-09 | Main search corpus fits PostgreSQL MVP architecture | Likely |
| A-10 | Stable internet is not guaranteed | Conservative assumption |
| A-11 | Historical participation can be used as a weak relevance signal | Needs validation |
| A-12 | Pre-event coding rules permit planned preparation | Must verify separately |

---

# 76. Decision Log

| ID | Decision | Reason |
|---|---|---|
| D-01 | Modular Monolith | Fastest reliable architecture |
| D-02 | PostgreSQL | One data/search platform |
| D-03 | pgvector | Avoid a separate vector DB |
| D-04 | Hybrid retrieval | Best recall/precision tradeoff |
| D-05 | Search ProductOffering | Better product-level relevance |
| D-06 | Weighted ranking v1 | Explainable and no training need |
| D-07 | Separate Match/Confidence/Risk | Avoid misleading single score |
| D-08 | LLM only as supporting layer | Reduce hallucination |
| D-09 | Pre-indexed data as primary path | Predictable latency |
| D-10 | Benchmark before tuning | Prevent subjective optimization |
| D-11 | No microservices | No current value |
| D-12 | No auth for hackathon demo | Focus on core value |
| D-13 | No price scoring initially | Data comparability risk |
| D-14 | Preserve raw source records | Traceability |

---

# 77. Open Questions

These questions should be validated with organizers or domain experts:

1. What exactly qualifies as a relevant supplier?
2. Are suppliers outside AIS ГЗ explicitly desirable?
3. What datasets will be provided?
4. What identifiers are present?
5. What is the expected dataset size?
6. Is historical supplier participation considered relevance?
7. Which fields will be used during evaluation?
8. What external sources are preferred or allowed?
9. How should manufacturer vs distributor be defined?
10. Is geography a hard restriction or a ranking preference?
11. Does delivery capability matter?
12. What is the expected production integration model?
13. What latency is considered acceptable?
14. Which matters more: Precision or Recall?
15. Are there categories where false positives are especially costly?
16. Are there existing supplier-search workflows we can observe?

Most important question:

> **If we solve only one problem perfectly, which problem would create the greatest business impact?**

---

# 78. Deferred Features List

Do not forget these, but do not build them now.

## Product

- saved searches,
- procurement alerts,
- supplier watchlists,
- comparison reports,
- sourcing collaboration.

## Intelligence

- Learning-to-Rank,
- feedback-trained reranker,
- supplier similarity,
- automated taxonomy learning,
- price intelligence,
- risk modeling.

## SaaS

- organizations,
- tenants,
- subscription plans,
- billing,
- quotas.

## Platform

- RBAC,
- audit log,
- admin panel,
- API keys,
- webhooks.

## Analytics

- search funnel,
- zero-result analytics,
- feature adoption,
- A/B tests.

---

# 79. Development Backlog

## EPIC E0 — Foundation

| Task | Priority | Dependencies | Output | Definition of Done |
|---|---|---|---|---|
| E0-T1 Repo skeleton | P0 | — | FE/BE/infra dirs | Local startup works |
| E0-T2 Docker Compose | P0 | T1 | Reproducible environment | One command starts stack |
| E0-T3 Configuration | P0 | T1 | env/settings | Secrets excluded |
| E0-T4 CI baseline | P1 | T1 | lint/test | PR checks run |

---

# 80. EPIC E1 — Data Foundation

| Task | Priority | Dependencies | Output | Definition of Done |
|---|---|---|---|---|
| E1-T1 Canonical schemas | P0 | E0 | Models | Migrations pass |
| E1-T2 Organizer adapter | P0 | Schema | Mapped records | Sample imports |
| E1-T3 Normalization | P0 | Adapter | Normalized records | Tests pass |
| E1-T4 Entity resolver | P0 | Normalize | Canonical suppliers | Duplicate tests pass |
| E1-T5 Search projection | P0 | Schema | Indexed docs | Rebuild succeeds |
| E1-T6 Embeddings batch | P0 | Offerings | Vectors | All searchable docs embedded |

---

# 81. EPIC E2 — Benchmark

| Task | Priority | Dependencies | Output | Definition of Done |
|---|---|---|---|---|
| E2-T1 Query set | P0 | Data | benchmark.csv | ≥20 usable cases |
| E2-T2 Relevance labels | P0 | T1 | qrels | Grades 0/1/2 |
| E2-T3 Baseline runner | P0 | Index | Metrics | Reproducible report |
| E2-T4 Holdout split | P0 | qrels | dev/test | Frozen test set |

The benchmark begins early.

It is not postponed until the end.

---

# 82. EPIC E3 — Retrieval

| Task | Priority | Dependency | Output | Definition of Done |
|---|---|---|---|---|
| E3-T1 FTS search | P0 | Search docs | Lexical results | Baseline query works |
| E3-T2 Trigram matching | P1 | T1 | Fuzzy results | Typo cases improve |
| E3-T3 Vector search | P0 | Embeddings | Semantic results | Top-K returned |
| E3-T4 Hybrid union | P0 | T1/T3 | Candidate set | Deduplication works |
| E3-T5 Filters | P0 | Union | Filtered pool | Filter tests pass |

---

# 83. EPIC E4 — Ranking

| Task | Priority | Dependency | Output | Definition of Done |
|---|---|---|---|---|
| E4-T1 Feature extractor | P0 | Candidates | Feature vector | Deterministic |
| E4-T2 Weighted scorer | P0 | Features | MatchScore | Unit tested |
| E4-T3 Confidence score | P0 | Evidence | Confidence | Explainable |
| E4-T4 Risk flags | P1 | Data | Flags | UI-safe |
| E4-T5 Contribution map | P0 | Score | Explainability | Every result explains |

---

# 84. EPIC E5 — API

| Task | Priority | Output |
|---|---|---|
| Search endpoint | P0 | `/search` |
| Supplier endpoint | P0 | `/suppliers/{id}` |
| Metadata endpoint | P1 | `/meta/filters` |
| Evidence endpoint | P1 | Evidence |
| Feedback endpoint | P2 | Feedback |

---

# 85. EPIC E6 — Product UI

### P0

Search page.

### P0

Results page.

### P0

Supplier detail.

### P1

Filters.

### P1

Supplier comparison.

### P2

Search history.

---

# 86. EPIC E7 — Market Expansion

| Task | Priority |
|---|---|
| Source adapter interface | P0 |
| First external source | P0 |
| External supplier marker | P0 |
| Evidence capture | P0 |
| Second external source | P1 |
| Live discovery | P2 |

---

# 87. EPIC E8 — Evaluation

- benchmark runner,
- metrics,
- baseline comparison,
- temporal holdout,
- latency profiling,
- error analysis.

All are P0 except extensive error analytics, which is P1.

---

# 88. EPIC E9 — Demo

- Docker clean-start test
- predefined fallback queries
- seeded stable dataset
- demo story
- metrics slide
- architecture slide
- failure recovery
- offline-safe mode

---

# 89. Actual Execution Order

Recommended implementation order:

```text
1. Repository
2. Canonical Data Model
3. Small Real/Sample Dataset
4. Benchmark Queries
5. Keyword Baseline
6. Backend Vertical Slice
7. Minimal Results UI
8. Semantic Retrieval
9. Hybrid Retrieval
10. Ranking
11. Evidence / Explanation
12. External Supplier Adapter
13. Supplier Detail
14. Benchmark Comparison
15. Tune Ranking
16. Filters
17. Compare — if time
18. Deployment
19. Demo Freeze
```

---

# 90. Why Build the Baseline Early?

Because:

```text
AI System = 0.71 nDCG
```

means very little by itself.

But:

```text
Keyword Baseline: 0.54
Supplier Radar:   0.71
```

is measurable evidence.

---

# 91. Phase 1 — Working Vertical Slice

## Goal

The first query travels through the entire product.

```text
Query
→ API
→ DB
→ Search
→ Result
→ UI
```

### Tasks

- repository,
- DB,
- 100–1000 sample records,
- keyword search,
- `/search`,
- minimal results UI.

### Deliverable

Working end-to-end search.

### Exit Criteria

The user enters a query and sees real suppliers returned from the database.

### Not Allowed Yet

AI optimization before this works.

---

# 92. Phase 2 — Core Search & Ranking

## Goal

Turn search into a real relevance system.

### Tasks

- embeddings,
- vector index,
- hybrid retrieval,
- candidate union,
- ranking features,
- MatchScore.

### Deliverable

Hybrid Search v1.

### Exit Criteria

The benchmark runner can compare:

Baseline vs Hybrid.

---

# 93. Phase 3 — Intelligence & Evidence

## Goal

Make recommendations explainable.

### Tasks

- query extraction,
- attributes,
- confidence,
- evidence,
- risk flags,
- external source adapter.

### Deliverable

Evidence-backed search.

### Exit Criteria

Top 5 results contain:

Reason + Evidence + Confidence.

---

# 94. Phase 4 — Product Experience

## Goal

Turn the engine into a usable product.

### Tasks

- polished search,
- filters,
- result cards,
- supplier profile,
- New Supplier badge,
- comparison if time allows.

### Deliverable

Hackathon-quality interface.

---

# 95. Phase 5 — Evaluation

## Goal

Prove value.

### Tasks

- frozen benchmark,
- P@5,
- Recall@20,
- nDCG@10,
- MRR,
- coverage,
- latency,
- error analysis,
- temporal holdout.

### Deliverable

`evaluation_report.json`

plus presentation-ready metrics.

### Exit Criterion

No accuracy claim appears in the pitch without a supporting metric.

---

# 96. Phase 6 — Deployment & Demo

## Goal

Turn the development build into a reliable demo.

### Tasks

- Docker clean environment,
- deployment,
- seed,
- health endpoint,
- backup dataset,
- offline mode,
- demo queries.

### Exit Criterion

The demo runs from a clean startup without manual fixes.

---

# 97. Suggested Engineering Timeboxes

These are work boundaries designed to prevent overengineering, not guaranteed estimates.

| Phase | Target Engineering Window |
|---|---:|
| Vertical Slice | 2h |
| Search Core | 3h |
| Ranking | 2–3h |
| Evidence/Enrichment | 2–3h |
| UI Productization | 3h |
| Benchmark/Tuning | 2–3h |
| Deployment/Demo | 2h |

Work can run in parallel once contracts are fixed.

---

# 98. Definition of Done

A task is not Done simply because:

> “The code is written.”

Definition of Done:

### Code

Implemented.

### Test

Core behavior tested.

### Integration

Connected to upstream and downstream components.

### Observable

Failures are visible.

### Demo

Usable from the product flow.

---

# 99. Phase 0 Deliverables Checklist

## Product

- [x] Problem Definition
- [x] Primary User
- [x] JTBD
- [x] Product Vision
- [x] Value Proposition
- [x] PRD
- [x] Use Cases
- [x] User Stories
- [x] Functional Requirements
- [x] Non-Functional Requirements

## Scope

- [x] Must Have
- [x] Should Have
- [x] Could Have
- [x] Out of Scope
- [x] Deferred Features

## Search

- [x] Retrieval Strategy
- [x] Candidate Generation
- [x] Filtering Strategy
- [x] Ranking v1
- [x] Confidence Score
- [x] Explainability
- [x] LLM Boundaries

## Data

- [x] Entities
- [x] Relationships
- [x] Canonical Schema
- [x] Normalization
- [x] Entity Resolution
- [x] Evidence Model
- [x] Search Projection

## Engineering

- [x] Architecture
- [x] Technology Stack
- [x] Module Boundaries
- [x] API Contracts
- [x] Deployment Approach

## Evaluation

- [x] Baseline
- [x] Benchmark Structure
- [x] Metrics
- [x] Temporal Holdout
- [x] MVP Success Gates

## Governance

- [x] Assumption Log
- [x] Decision Log
- [x] Risk Register
- [x] Open Questions
- [x] Deferred Features List

## Execution

- [x] Epics
- [x] Priority
- [x] Dependencies
- [x] Definition of Done
- [x] Execution Order
- [x] Phase Plan

---

# 100. Next Phases Roadmap

```text
Idea
 ↓
Phase 0
Product & Technical Foundation
 ↓
Phase 1
Working Vertical Slice
 ↓
Phase 2
Search MVP
 ↓
Phase 3
Intelligence + Evidence
 ↓
Phase 4
Hackathon Product
 ↓
Phase 5
Pilot
 ↓
Phase 6
Production SaaS
```

---

# 101. Hackathon-Ready Product

Requires only:

- working ingestion,
- hybrid search,
- ranking,
- explanations,
- external supplier discovery,
- UI,
- benchmark,
- reliable demo.

It does not require full SaaS infrastructure.

---

# 102. Pilot-Ready Product

This is where the system expands.

## Identity

- Authentication
- Organizations
- RBAC

## Platform

- Admin tools
- Automated ingestion
- Scheduled refresh
- Source health

## Product

- Saved searches
- Feedback
- Analytics
- Exports

## Operations

- Monitoring
- Alerts
- Backups
- CI/CD

## Security

- Rate limiting
- Audit logs
- Secret management

---

# 103. Production-Ready SaaS

After product-market fit is demonstrated, add:

## SaaS

- Multi-tenancy
- Usage limits
- Subscription
- Billing
- API keys

## Scale

- Workers
- Queues
- Redis
- Dedicated search cluster when needed

## Intelligence

- Learning-to-Rank
- User-feedback training
- A/B testing
- Model registry
- Model evaluation
- Drift monitoring

## Enterprise

- SSO
- Fine-grained RBAC
- Audit trail
- Tenant isolation
- SLA
- Data retention policies

---

# 104. Evolution of Search Architecture

Do not start with:

```text
OpenSearch + Kafka + Kubernetes + Redis + ML Serving
```

Start with:

### MVP

```text
Postgres
+
FTS
+
pgvector
```

### When a Search Bottleneck Appears

```text
OpenSearch
```

### When Async Workload Appears

```text
Queue + Worker
```

### When Multi-Instance Caching Becomes Necessary

```text
Redis
```

### When Sufficient Training Data Exists

```text
Learning-to-Rank
```

Every technology must be introduced because it solves a proven problem.

---

# 105. Product Evolution

## V1

Search suppliers.

## V2

Understand the market.

## V3

Manage sourcing.

## V4

Procurement Intelligence Platform.

For now, we build only:

> **The best possible Supplier Discovery Engine.**

---

# 106. Phase 0 Final Architecture Decision

> **Build a Modular Monolith using PostgreSQL as the system of record and lexical/vector search platform. Search at the Product Offering level and aggregate back to Suppliers. Use Hybrid Retrieval to generate approximately 300–500 candidates, then apply a deterministic weighted ranker to produce the Top 20. Keep Match Score separate from Confidence and Risk. Add an Evidence layer so every result is explainable. Use an LLM only for query understanding and optional explanation wording, never as the source of truth or ranking authority.**

---

# 107. Immediate Next Action

Do not start with the frontend.

Do not start with the LLM.

Do not start with external scraping.

## First Implementation Task

### P1-001 — Canonical Data + Benchmark Seed

Create the repository and establish the core contracts:

```text
/contracts
    supplier.schema
    product_offering.schema
    search_query.schema
    search_response.schema

/data
    sample_suppliers
    sample_offerings

/benchmark
    queries.csv
    qrels.csv
```

Then prepare:

- 100–1000 initial Supplier/Offering records,
- 10 initial procurement queries,
- simple relevance judgments.

Immediately after that:

### P1-002 — Keyword Baseline Vertical Slice

Implement:

```text
POST /search
        ↓
PostgreSQL FTS
        ↓
Top Suppliers
        ↓
Minimal Results Page
```

Once this works, establish Baseline Metrics.

Only then move to:

**Semantic Retrieval → Hybrid → Ranking → Evidence.**

---

# 108. First Technical Milestone

The first milestone is not:

> Database finished.

And not:

> Frontend finished.

It is:

> **One real procurement query goes through the entire product and returns measurable supplier results.**

This is the first proof that the project has moved from blueprint to product.

---

# Phase 0 Status

**Product Definition:** READY  
**MVP Scope:** READY  
**Data Contract:** READY at canonical level  
**Retrieval Design:** READY  
**Candidate Strategy:** READY  
**Ranking v1:** READY  
**Explainability:** READY  
**Architecture:** READY  
**API Design:** READY  
**Evaluation Strategy:** READY  
**Risk/Decision/Assumption Logs:** READY  
**Development Backlog:** READY

## Pending External Validation

The following items cannot be treated as facts before the organizer dataset or official answers are available:

- actual dataset schema,
- dataset volume,
- official relevance definition,
- available identifiers,
- exact external-source restrictions,
- actual ground truth,
- final production integration constraints.

These do not block implementation because they are explicitly tracked in the **Assumption Log + Open Questions** instead of being guessed.
