# RLT.Hack 2026 — Initial Strategy Report

**Working Project Name:** Supplier Radar  
**Concept:** Evidence-based Supplier Discovery for Public Procurement  
**Purpose:** Build a real, measurable procurement intelligence product for discovering, enriching, ranking, and explaining relevant suppliers, manufacturers, and distributors for AIS ГЗ and the Saint Petersburg electronic procurement store.

---

## 1. Core Strategic Direction

The hackathon problem should not be treated as a simple supplier search task.

The real opportunity is to build a system that transforms a procurement request into a ranked, evidence-backed market map of relevant companies.

### Core product promise

> From a procurement description → to a verified shortlist of relevant suppliers, including previously unknown external suppliers, with clear evidence explaining why each company was recommended.

This turns the project from a normal hackathon demo into a Procurement Intelligence product.

---

## 2. What the Challenge Really Requires

The challenge is centered around creating an intelligent service for searching for:

- suppliers,
- manufacturers,
- distributors,

for use in:

- AIS ГЗ,
- the electronic procurement store of Saint Petersburg.

The expected solution should cover:

- analysis of the organizer's data,
- understanding the available fields,
- developing a supplier-selection methodology,
- searching open sources,
- enriching supplier/company data,
- building a usable web interface,
- testing on realistic procurement cases,
- demonstrating scalability.

The goal is therefore not merely to search for companies by name.

The system must understand procurement needs and identify companies that are likely capable of supplying the requested goods or services.

---

## 3. Proposed Product

# Supplier Radar

**Evidence-based Supplier Discovery for Public Procurement**

Example procurement request:

> We need 200 interactive displays for schools, 75 inches, with delivery to Saint Petersburg.

The system should perform the following pipeline:

```text
Procurement Request
        ↓
Query Understanding
        ↓
Product / Category / Attribute Extraction
        ↓
Candidate Retrieval
        ↓
Supplier Discovery
        ↓
Entity Resolution
        ↓
Supplier Enrichment
        ↓
Ranking
        ↓
Evidence + Confidence
        ↓
Shortlist
```

Instead of returning only:

```text
ООО Компания — Score 0.87
```

the system should return something understandable and useful:

```text
ООО Компания X

Match Score: 94/100
Confidence: 91/100

✓ Manufacturer
✓ Saint Petersburg
✓ Matching product catalog
✓ 17 relevant procurement contracts
✓ Verified INN
✓ Product evidence found in official catalog
```

With a clear explanation:

> Recommended because matching 75-inch interactive panels were found in the manufacturer's catalog, the company has relevant procurement experience, and its legal entity data is verified.

---

## 4. Killer Feature: Market Expansion

The system should not only rank suppliers already present in AIS ГЗ.

It should also discover external companies that are not yet active in the current procurement ecosystem.

The interface should clearly separate:

- **Existing AIS Supplier**
- **New External Supplier**

Example result:

```text
37 candidate suppliers found

12 existing AIS suppliers
25 external suppliers

Among them:
6 distributors
3 manufacturers
4 new high-confidence suppliers not previously active in this procurement category
```

### Why this matters

The real business value is not only finding the known suppliers faster.

It is expanding the competitive supplier pool.

Conceptually:

```text
More relevant suppliers
        ↓
More competition
        ↓
Better procurement options
        ↓
Potentially better pricing and resilience
```

This feature gives the product direct operational value.

---

## 5. Important Technical Principle

Do **not** make the LLM the entire system.

Avoid:

```text
GPT → "Find suppliers" → Results
```

This is difficult to verify, difficult to benchmark, and vulnerable to hallucination.

Instead use a hybrid architecture.

```text
Procurement Request
        ↓
Query Understanding
        ↓
Taxonomy / Attribute Extraction
        ↓
Candidate Retrieval
 ┌──────────────────┬──────────────────┐
 │ Keyword / BM25   │ Semantic Search  │
 │                  │ Embeddings       │
 └──────────────────┴──────────────────┘
        ↓
Entity Resolution
        ↓
Supplier Enrichment
        ↓
Hybrid Ranking
        ↓
Evidence + Confidence
        ↓
Supplier Shortlist
```

### Recommended role of the LLM

Use an LLM for:

- procurement request parsing,
- extracting attributes,
- normalizing terminology,
- generating short explanations,
- query expansion when needed.

Do not use it as the sole authority for:

- supplier existence,
- legal entity data,
- manufacturer status,
- ranking,
- final verification.

---

## 6. Data Sources Strategy

The project should combine several data layers.

| Source | What it provides | Product value |
|---|---|---|
| Organizer dataset | Procurement records, products, suppliers | Primary data layer |
| AIS ГЗ / EIS data | Procurement history and contracts | Supplier experience |
| Federal Tax Service / Прозрачный бизнес | INN, OGRN, OKVED, company status | Legal entity verification |
| ГИСП | Russian industrial products and manufacturers | Manufacturer verification |
| Company websites and catalogs | Actual products/services | Product evidence |
| Open web | Discovery of additional companies | Market expansion |

### Recommended source roles

#### Organizer data
Use as the main structured source and basis for benchmarking.

#### ФНС / Прозрачный бизнес
Useful for:

- validating company existence,
- checking company status,
- obtaining INN / OGRN,
- matching OKVED,
- resolving duplicate companies.

#### ГИСП
Especially valuable for identifying real manufacturers.

This may become one of the strongest differentiators of the system.

#### Company websites
Use for:

- confirming product availability,
- extracting product names and specifications,
- providing evidence links.

#### Open web
Use only for discovery and enrichment.

Do not rely on open-web text as the only verification source.

---

## 7. Ranking Model

Do not use a single unexplained number.

The system should separate three concepts.

### 7.1 Match Score

Answers:

> How relevant is this company to the procurement request?

Potential components:

```text
Semantic similarity       30%
Product/category match    25%
Exact attribute match     20%
Relevant procurement exp. 15%
Geography/logistics       10%
```

These weights should initially be treated as a baseline and later tuned from real data.

---

### 7.2 Confidence Score

Answers:

> How strong is the evidence supporting this recommendation?

Possible signals:

- official product catalog found,
- legal entity verified,
- INN match,
- manufacturer registry match,
- procurement history available,
- multiple independent evidence sources.

---

### 7.3 Risk Flags

Do not mix risk directly into the relevance score.

Display separate flags such as:

- unclear manufacturer status,
- stale company data,
- weak product evidence,
- no procurement history,
- ambiguous company identity.

This preserves discoverability of new suppliers without automatically penalizing them for having little historical data.

---

## 8. Evaluation Strategy

The project should be measurable.

Do not say only:

> Our AI gives more accurate results.

Build a baseline comparison.

### Baseline

Use traditional keyword search.

### Proposed system

Use the hybrid Supplier Radar ranking model.

### Metrics

Recommended metrics:

| Metric | Purpose |
|---|---|
| Precision@5 | Quality of top recommendations |
| Recall@20 | Coverage of relevant suppliers |
| nDCG@10 | Ranking quality |
| New Suppliers Discovered | Market expansion ability |
| Average Search Latency | Product usability |
| Evidence Coverage | Explainability quality |

Example presentation:

| Metric | Keyword Baseline | Supplier Radar |
|---|---:|---:|
| Precision@5 | measured | measured |
| Recall@20 | measured | measured |
| nDCG@10 | measured | measured |
| New suppliers discovered | measured | measured |
| Avg. search latency | measured | measured |

---

## 9. Strongest Validation Experiment: Temporal Holdout

This can become one of the strongest parts of the project.

### Procedure

1. Select historical procurement cases.
2. Choose a procurement event.
3. Hide the supplier that eventually won or participated.
4. Allow the system to use only information that existed before that procurement.
5. Ask the system to find relevant suppliers.
6. Check whether the later-known supplier appears in the recommended shortlist.

This creates a realistic historical simulation.

The question becomes:

> Could our system have discovered this supplier before the procurement happened?

If the answer is yes across multiple cases, the system demonstrates real market-discovery value.

---

## 10. Demo Strategy

The live demo must be simple and understandable.

Example input:

```text
Интерактивная панель 75" для образовательных учреждений
```

Expected output:

```text
37 candidates found

12 AIS suppliers
25 external suppliers

Top 10:
────────────────────
6 distributors
3 manufacturers
1 general supplier

4 companies are NEW to AIS procurement history
```

Then open a supplier:

```text
MATCH:       92
CONFIDENCE:  96

Evidence
✓ product found in official catalogue
✓ manufacturer registry match
✓ OKVED compatible
✓ 23 related contracts
✓ active company
✓ delivery evidence for Saint Petersburg
```

Then show:

```text
Compare Suppliers
```

with three companies side-by-side.

The demo should explain the business value within seconds even to a non-technical jury member.

---

## 11. MVP Interface

Do not build a large dashboard.

Build four excellent screens.

### Screen 1 — Search

Main input:

```text
Что необходимо закупить?
```

The user enters or pastes a procurement request.

The system automatically extracts:

```text
Category
Product
Characteristics
Quantity
Region
Required Supplier Type
```

The user may edit the extracted fields.

---

### Screen 2 — Search Results

Each supplier appears as a card.

Example:

```text
ООО Компания

Manufacturer

Match 94
Confidence 91

✓ 14 similar contracts
✓ official product evidence
✓ verified manufacturer

[Why matched]
[Compare]
```

Recommended filters:

- Manufacturer / Distributor
- Region
- Existing / New Supplier
- Relevant Experience
- Confidence

---

### Screen 3 — Supplier Profile

Show:

- company identity,
- INN / OGRN,
- role,
- relevant products,
- procurement history,
- evidence,
- source links,
- confidence,
- risk flags.

---

### Screen 4 — Compare Suppliers

Compare 3–5 suppliers side-by-side.

Recommended comparison fields:

- Match Score
- Confidence
- Manufacturer / Distributor
- Relevant contracts
- Region
- Product evidence
- Company status
- New / Existing supplier

---

## 12. Recommended Hackathon Architecture

Avoid unnecessary complexity.

| Layer | Recommended Technology |
|---|---|
| Frontend | Next.js |
| API | FastAPI |
| Data Processing | Python + Polars/Pandas |
| Database | PostgreSQL |
| Semantic Search | pgvector |
| Keyword Search | PostgreSQL FTS or lightweight BM25 |
| Embeddings | Multilingual / Russian embedding model |
| Ranking | Weighted hybrid ranker |
| Deployment | Docker Compose |
| Cache | Only if needed |

### Production scalability story

For the hackathon, keep the implementation compact.

In the architecture slide, explain that production can later evolve toward:

- OpenSearch / Elasticsearch,
- asynchronous workers,
- event-driven enrichment,
- scheduled data refresh,
- separate crawling services,
- supplier graph storage,
- monitoring and audit logs.

Do not build unnecessary Kubernetes infrastructure during the hackathon.

The goal is to demonstrate that the architecture **can** scale, not to spend the entire event building infrastructure.

---

## 13. Team Structure for Four People

| Role | Responsibility |
|---|---|
| Tech/Product Lead | Architecture, integration, product decisions |
| Data/ML Engineer | EDA, embeddings, retrieval, ranking, evaluation |
| Backend/Data Engineer | ETL, entity resolution, enrichment, APIs |
| Frontend/Product Engineer | UX, UI, demo, presentation |

### Integration rule

The Tech/Product Lead must continuously verify that this full path works:

```text
Data
  ↓
Retrieval
  ↓
Ranking
  ↓
API
  ↓
UI
  ↓
Demo
  ↓
Metrics
```

Avoid a situation where each person builds a technically impressive isolated component that does not integrate.

---

## 14. Pre-Hackathon Preparation Plan

### September 23
- Confirm registration
- Freeze the product vision
- Define the problem statement
- Define the MVP

### September 24
- Study AIS ГЗ, EIS, ФНС, ГИСП
- Create preliminary data model

### September 25
- Define search pipeline
- Define ranking methodology

### September 26
- Build evaluation methodology
- Prepare general benchmark cases

### September 27
- Design UX wireframes
- Finalize demo flow

### September 28
- Verify registration
- Review architecture
- Prepare questions for organizers and mentors

### September 29
- Run a complete dry run with public data

### September 30
- Freeze unnecessary features
- Prepare project templates
- Prepare pitch structure
- Prepare evaluation scripts

### October 1
- Analyze organizer dataset
- Adapt schemas
- Build end-to-end working MVP

### October 2
- Improve retrieval quality
- Tune ranking
- Run evaluation
- Stabilize demo
- Prepare final pitch

---

## 15. Questions to Ask the Organizers in the First Hour

Do not immediately start coding.

Ask:

1. What exactly defines a **relevant supplier**?
2. Is discovering new companies outside AIS ГЗ part of the desired result?
3. What ground truth will be used during evaluation?
4. Is historical procurement experience an important ranking signal?
5. How should manufacturer and distributor status be determined?
6. Which external/open sources are explicitly acceptable?
7. Is recall more important than precision, or vice versa?
8. What production data volume should the solution eventually handle?
9. Is integration into AIS ГЗ more important than a standalone application?
10. What is the biggest real-world pain point for procurement employees today?

### Most important question

```text
Если мы решим только одну проблему идеально,
какая проблема даст вам наибольший бизнес-эффект?
```

English meaning:

> If we solve only one problem perfectly, which problem would create the greatest business impact for you?

The answer may help prioritize the entire MVP.

---

## 16. What We Should NOT Build

Avoid wasting time on:

- a chatbot as the main interface,
- a large dashboard with unnecessary charts,
- multi-agent architecture only for appearance,
- scraping dozens of low-quality websites,
- excessive microservices,
- overly complex ML before establishing a baseline,
- unexplained AI scores,
- infrastructure that does not improve the demo,
- features unrelated to supplier discovery,
- last-minute presentation preparation.

---

## 17. Product Priority Order

The correct priority is:

```text
Working
   ↓
Measurable
   ↓
Explainable
   ↓
Useful
   ↓
Beautiful
```

Not the reverse.

---

## 18. Final Pitch Narrative

The final presentation should communicate this idea clearly:

> Today, procurement employees often search within a limited universe of already-known suppliers. Supplier Radar converts a procurement description into a market map in seconds. It does not only show who may be able to supply the requested product; it explains why the supplier is relevant, where the evidence came from, whether the company is a manufacturer or distributor, and whether it is already active in AIS ГЗ or represents a new market opportunity. We then validate the system against historical procurement cases and compare it with traditional keyword search.

---

## 19. Main Differentiation

The novelty is **not**:

> We used AI to search suppliers.

The real differentiation is:

> An explainable supplier-discovery system that combines procurement data with open-market evidence, discovers new suppliers, distinguishes manufacturers from distributors, ranks companies with verifiable evidence, and demonstrates measurable improvement over conventional search.

---

## 20. Phase 0 — Next Step

The next phase should convert this strategy into an executable project specification.

Phase 0 should produce:

- Product Requirement Document
- Problem Definition
- User Persona
- Main User Journey
- Scope / Non-Scope
- Data Schema
- Supplier Entity Model
- Retrieval Strategy
- Ranking Methodology
- Confidence Methodology
- Evidence Model
- Entity Resolution Method
- API Contracts
- MVP Screens
- Benchmark Plan
- Evaluation Dataset Structure
- Architecture Diagram
- Development Backlog
- Team Task Allocation
- Demo Scenario
- Pitch Structure
- Risk Register

This report should remain the strategic baseline.

Any new feature proposed during Phase 0 or the hackathon should answer one question:

> Does this improve supplier discovery accuracy, market expansion, explainability, measurable business value, or demo clarity?

If not, it is probably outside the MVP.

---

## Reference Links

- RLT.Hack challenge page:  
  https://www.хакатоны.рус/tpost/hscp3i3in1-rlthack-razrabotka-intellektualnogo-serv

- RLT University / Roseltorg:  
  https://uni.roseltorg.ru/

- Saint Petersburg Government:  
  https://www.gov.spb.ru/

- Federal Tax Service — online services:  
  https://www.nalog.gov.ru/donline/

- ГИСП industrial product registry:  
  https://portfolio.gisp.gov.ru/pp719v2/pub/prod/

- Контур.Фокус:  
  https://focus.kontur.ru/

- iSource / Effect:  
  https://isource.com/effect

---

**Status:** Initial strategic baseline saved before Phase 0.  
**Next:** Phase 0 — convert strategy into implementation-ready product, data, architecture, evaluation, and execution plan.
