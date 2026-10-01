# Project Overview — Supplier Radar

> ### Hackathon Day-1 amendment (2026-10-01)
> Product framing per the [organizer briefing](../sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md) and [Baseline §4](../HACKATHON_EXECUTION_BASELINE.md#4-product-problem--business-value):
> Supplier Radar turns a **procurement lot** (existing `lot_id` or free-text need) into (1) a ranked, explained shortlist of suppliers with relevant
> history, (2) a **supplier-pool health** verdict for the category, and (3) when the pool is weak, **verified external suppliers with roles**.
> Stakeholders served by **one** interface at three levels: procurement specialist (who to invite, how many, why) · procurement manager
> (diversity, dependency risk, expansion) · analyst (methodology, evidence, history, validation).
> Constraints updated: dataset known (§8 "unknown organizer dataset" is resolved); connectivity — offline demo required; performance ≤ 10 s.
> Glossary additions: **ProcurementLot**, **ProcurementItem (ТРУ)**, **SupplierHistory**, **ЭМ** (electronic store), **OKPD2**, **Supplier Pool Health**, **market role**, **entity type**.

> Sources: [Strategy Report](../sources/RLTHack_Initial_Strategy_Report.md) §1–5, 17–19 ·
> [Phase 0](../sources/Supplier_Radar_Phase_0_Product_Technical_Foundation_EN.md) §2–5, 105

## 1. One-line definition

**Supplier Radar turns a procurement requirement into an explainable, ranked market map of relevant
suppliers, manufacturers and distributors — including suppliers not yet active in the procurement
ecosystem — with the evidence behind every recommendation.**

Context: RLT.Hack 2026 challenge — intelligent supplier/manufacturer/distributor search for
**AIS ГЗ** and the **Saint Petersburg electronic procurement store** (Roseltorg / RLT).

## 2. The problem

A procurement specialist has a requirement but no fast, trustworthy way to turn it into a
comprehensive, ranked and verifiable supplier shortlist. Relevant information is fragmented across
procurement data, company registries, manufacturer registries, product catalogs and the open web.
Traditional search depends on exact keywords, category codes, previously-known companies and rigid
filters, producing:

> **Poor discovery + limited supplier pool + manual verification.**

## 3. Target users

| Persona | Priority | Need |
|---|---|---|
| **Procurement / Sourcing Specialist** | Primary | Quickly get a relevant, verifiable shortlist for a requirement |
| Category / Procurement Analyst | Secondary | Analyze market, compare companies, discover new suppliers |
| Procurement Manager | Secondary | Assess sourcing quality, supplier-pool concentration |
| Data / System Administrator | Not MVP | Source monitoring, refresh, data quality |
| **Hackathon jury** *(implicit)* | Demo-critical | Understand business value "within seconds" |

**JTBD:** *When I have a procurement requirement, I want to quickly obtain a relevant and verifiable
supplier shortlist so I can understand the market without manually searching multiple disconnected sources.*

## 4. Value proposition

Not "AI search for suppliers" but **"Discover more relevant suppliers with evidence you can trust."**

| Pillar | Meaning |
|---|---|
| **Discovery** | Find companies the user did not already know (Market Expansion — the "killer feature") |
| **Relevance** | Rank suppliers for *this* requirement (hybrid lexical + semantic + structured + history) |
| **Trust** | Every recommendation shows sources, evidence, confidence and risk flags |

Business chain: more relevant suppliers → more competition → better procurement options → better
pricing and resilience.

## 5. Differentiation

An explainable supplier-discovery system that (1) combines procurement data with open-market
evidence, (2) discovers new suppliers, (3) distinguishes manufacturers from distributors,
(4) ranks with verifiable evidence, and (5) **proves** measurable improvement over keyword search
(benchmark + temporal holdout).

## 6. Product priority order

`Working → Measurable → Explainable → Useful → Beautiful` — never the reverse.
Core principle (Phase 0): **Value → Speed → Simplicity → Measurability → Scalability.**

## 7. Scope at a glance

| In MVP (Must) | Should | Could | Out of scope |
|---|---|---|---|
| Free-text search, query parsing, hybrid retrieval, ranking, evidence, known/new classification, supplier profile, region/type filters, manufacturer/distributor classification, ranking explanation, benchmark vs keyword baseline | Comparison, feedback, analytics, session history, CSV export, richer profile, source refresh | LLM query expansion, LLM paraphrasing, LTR, live web discovery, saved searches, alerts | Multi-tenancy, billing, full RBAC, admin dashboard, K8s, microservices, event streaming, agents, messaging, contracting, graph DB, pricing intelligence, mobile |

Full detail: [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md).

**Scope gate** for any new idea (BR-27): *Does this improve supplier discovery accuracy, market
expansion, explainability, measurable business value, or demo clarity?* If not → outside MVP.

## 8. Constraints

- **Time:** hackathon window (event days per plan: 2026-10-01 → 10-02). Pre-event preparation
  legality unverified (A-12, OQ-01).
- **Unknown organizer dataset** → canonical internal schema + adapters.
- **Connectivity not guaranteed** → pre-indexed data, offline-capable demo.
- **Data quality not guaranteed** → INN may be missing, categories unstandardized, text dirty.
- **Legal/ToS** of external sources unverified (A-05).

## 9. Product evolution (context only — build V1 only)

V1 Search suppliers → V2 Understand the market → V3 Manage sourcing → V4 Procurement Intelligence Platform.
Stage gates: Hackathon product → Pilot (auth, orgs, RBAC, scheduled ingestion, monitoring) →
Production SaaS (multi-tenancy, billing, LTR, SSO…). See [PRODUCT_REQUIREMENTS §8](PRODUCT_REQUIREMENTS.md#8-future-requirements-not-mvp--do-not-build).

## 10. Glossary

| Term | Definition |
|---|---|
| **AIS ГЗ** | Saint Petersburg's automated information system for state procurement (the target ecosystem) |
| **EIS / ЕИС** | Russian unified federal procurement information system |
| **ФНС / Прозрачный бизнес / ЕГРЮЛ** | Federal Tax Service services for legal-entity data (INN, OGRN, status, OKVED) |
| **ГИСП** | State industrial information system — registry of Russian industrial products/manufacturers |
| **INN / OGRN / KPP** | Taxpayer ID (10 digits legal entity, 12 individual) / state registration number (13 / 15) / registration reason code (9) |
| **OKVED** | Classifier of economic activity codes |
| **Known supplier** | Supplier already present in the AIS/organizer procurement ecosystem (`is_known_supplier=true`) — exact definition open: OQ-17 |
| **External / New supplier** | Supplier discovered outside that ecosystem |
| **Product Offering** | A product/service a supplier offers — **the primary search unit** |
| **Match Score** | How relevant a supplier is to *this* request (0–1 API / 0–100 UI) |
| **Confidence Score** | How strong the evidence supporting the recommendation is |
| **Risk Flag** | Separate, non-scoring warning (e.g. `STALE_INFORMATION`) |
| **Reason code** | Structured, enumerable explanation token (e.g. `CATEGORY_MATCH`) |
| **Evidence** | A sourced claim (`source`, `url/ref`, `observed_at`) supporting a supplier/offering fact |
| **Search projection** | Denormalized, rebuildable search index table — never the source of truth |
| **Qrels** | Query relevance judgments (grades 0/1/2) |
| **Temporal holdout** | Evaluation that hides post-cutoff outcomes and asks whether the system would have found the eventual supplier |
| **Baseline** | PostgreSQL keyword/FTS-only search used as the comparison reference |
