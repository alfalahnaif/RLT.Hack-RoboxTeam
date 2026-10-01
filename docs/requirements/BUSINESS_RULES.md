# Business Rules

> Every rule is testable and traceable. `Source` cites the original document section.
> Rules marked **[ER]** are recommended additions (not binding until accepted — P0-004).
> Rules marked **(pending C-xx / OQ-xx)** depend on an unresolved conflict or question.

> ### Hackathon Day-1 amendment (2026-10-01, ADR-H1)
> BR-01 and BR-19 amended in place (marked). New rules BR-43…BR-50 at the end. Source: [Execution Baseline](../HACKATHON_EXECUTION_BASELINE.md).

## Search & results

| ID | Rule | Source |
|---|---|---|
| BR-01 | *(Amended 2026-10-01 by HD-03: for known suppliers the search unit is the historical **ProcurementItem** (ТРУ line) aggregated per supplier via SupplierHistory; ProductOffering applies to externally enriched suppliers. One result per supplier is unchanged.)* The search unit is the **ProductOffering**. Retrieval runs on offerings; results are aggregated to **one result per supplier**, showing the supplier's best-matching offering. No company-level embedding. | P0 §20, P1-001 §4, §16 |
| BR-02 | **Match, Confidence and Risk are separate.** Risk flags never change Match Score; Confidence never changes rank order in v1 **[ER: pending OQ-27 whether confidence may be a tie-breaker]**. | Strategy §7, P0 §43–44, D-07 |
| BR-03 | **Region is a soft signal** (GeographicFit feature) unless the requirement explicitly demands local presence, in which case it is a hard filter. | P0 §36 |
| BR-04 | **Hard filters only for mandatory constraints**: inactive company, explicitly required region, mandatory certification, explicitly prohibited supplier type. Everything else is a ranking feature. Default treatment of `legal_status=inactive`: excluded (A-104, pending OQ-25); `unknown`: kept + `UNKNOWN_LEGAL_STATUS` flag. | P0 §36 |
| BR-05 | If a ranking feature is **not applicable to the query** (e.g. no region given, no attributes extracted), its weight is removed and remaining weights are **renormalized**. Not applicable ≠ zero. Missing supplier data for an applicable feature scores **0** for that supplier (not N/A). | P0 §39; [ER] clarification of G-20 |
| BR-06 | Certifications: **mandatory → eligibility constraint** (hard filter); **beneficial → ranking feature** with no fixed global weight. | P0 §40 |
| BR-07 | **Price is not a ranking input** in v1. | P0 §41, D-13 |
| BR-08 | Historical procurement volume is **relevance evidence**, not a quality/reliability judgment. A separate Reliability Score is future work. | P0 §42 |
| BR-09 | **LLM output is an interpretation, never a fact.** The LLM must never be the authority for supplier existence, legal data, manufacturer status, ranking, verification or evidence. | Strategy §5, P0 §17, §47, D-08 |
| BR-10 | Search must work when the LLM is unavailable (fallback parser). | P0 §47 |
| BR-11 | Failure of an external source must never break indexed search; the primary path uses **pre-indexed data**. Live external search is never the default path. | P0 §9, §52, D-09 |
| BR-12 | Every result has **non-empty reason codes** from a controlled vocabulary. Explanations are rendered from reason codes and feature contributions via templates; arbitrary strings (incl. LLM text) are never the canonical explanation. | P0 §45–46, P1-001 §16–17 |
| BR-13 | Public scores are **normalized to 0–1**; internal retrieval scores (ts_rank, BM25, cosine) are never exposed in the public API. UI shows 0–100. | P1-001 §15, §46; ED-01 (pending C-05) |
| BR-14 | Results are ordered by Match Score descending; ties broken deterministically **[ER ED-09]**: Confidence desc → supplier_id asc. | P1-001 §16; NFR-DET-01 |
| BR-15 | Default result count 20; `limit` 1–100; candidate caps: lexical 200 offerings, semantic 200 offerings, category 100 suppliers, historical 100 suppliers, union ≤ 500 suppliers, full ranking Top 100. **All are tunable config, not constants.** | P0 §34–35, P1-001 §14 |
| BR-24 | **External content is untrusted**: it cannot call tools, execute instructions, or modify ranking; it is never rendered as HTML and (in MVP) never placed into LLM prompts. | P0 §9, §74 |
| BR-16 | **Every Top-5 result must carry source evidence** (target ≥ 90% measured; NFR states "every" — pending C-12). | P0 §9, §71 |

## Market expansion

| ID | Rule | Source |
|---|---|---|
| BR-19 | *(Resolved 2026-10-01, ADR-H1: Known = has ≥ 1 SupplierHistory row on a lot published before `as_of`.)* Each supplier is classified **Known** (active in the AIS/organizer procurement ecosystem) or **External/New**. Classification is a stored boolean `is_known_supplier` in MVP. Definition of "active" and whether "new to category" is also required: **pending OQ-17, C-04**. | Strategy §4, P1-001 §21, P1A-007 |
| BR-19a **[ER]** | After entity resolution, a canonical supplier is Known if **any** linked source record is from the AIS/organizer procurement data. | G-17 |
| BR-19b | New suppliers must not be automatically penalized for lacking history: `NO_PROCUREMENT_HISTORY` is a risk flag, not a score penalty. Note tension with the 0.08 ProcurementExperience weight — C-15. | Strategy §7.3 |
| BR-19c | `market_scope` filter: `all` (default) · `known` · `external`. | P1-001 §14 |

## Data, identity & traceability

| ID | Rule | Source |
|---|---|---|
| BR-20 | *(Still binding; synthetic seed is no longer the primary corpus — HD-01.)* **Synthetic data is never presented as real**: fictional company names, marked records/source (`internal_seed`), kept separate from organizer data; synthetic benchmark results are never presented as real market performance. | P1-001 §37 |
| BR-30 | Canonical IDs are **stable UUIDs**; seed IDs are deterministic **UUIDv5** from stable namespace + source key. Never use DB sequences as external IDs, names as IDs, or INN as primary key. External IDs stored separately. | P1-001 §5, P1D-002/003 |
| BR-31 | **Never discard source records.** Canonical entity ← source records link is always preserved (raw payload + checksum). | P0 §28, D-14, P1-001 §36 |
| BR-32 | Entity resolution levels: (1) exact INN → auto-merge; (2) exact OGRN → auto-merge; (3) normalized name + domain/address → high-confidence merge; (4) fuzzy name + region + category → **`possible_match` only, no destructive merge**. | P0 §28 |
| BR-33 | Original legal names are always preserved. Normalized aliases: NFC, lowercase, `ё→е`, whitespace/punctuation normalization, strip surrounding quotes, remove **only legal-form tokens** (ООО, АО, ПАО, ЗАО, ИП…), keep meaningful words, no transliteration by default. | P0 §27, P1-001 §8 |
| BR-34 | INN: 10 or 12 digits; OGRN: 13 or 15; KPP: 9; website: http/https URL. INN unique per canonical supplier unless flagged as source duplicate. | P1-001 §7, §31 |
| BR-35 | External facts require `source`, `url/reference`, `observed_at` (NFR-TRC-01). | P0 §9 |
| BR-36 | Minimum searchable supplier: `supplier_id` + name + offering/product text. Preferred: INN, category, region, supplier type, source. | P0 §26 |
| BR-37 | Organizer data enters **only through adapters** mapping into canonical contracts. New concepts: log → classify (source-specific / canonical / search-only) → extend canonical only if necessary. | P1-001 §35, P1D-011 |
| BR-38 | External sources are used only if **legally permitted/approved**; open web is for discovery and enrichment only, never the sole verification source. | Strategy §6, P0 §73, A-05 |
| BR-39 | Offering `description` may be empty only when the title is sufficiently descriptive (**[ER]** operationalize: title ≥ 3 tokens). | P1-001 §10, G-19 |

## Contracts & versioning

| ID | Rule | Source |
|---|---|---|
| BR-25 | Contracts carry a semver version (initial `0.1.0`): PATCH docs/clarification, MINOR new optional field, MAJOR breaking change. Schema change procedure: decision log → version contract → update seed → re-validate → re-run benchmark. | P1-001 §34, §52 |
| BR-26 | Public API is versioned under `/api/v1`; ranking is internal to `/search` (no public `/rank`); `/debug/*` only when `DEBUG=true`. | P0 §56, §62 |
| BR-28 | Search request validation: `query` required, 3–1000 chars; `filters` optional; `region` null/string; `supplier_type` null/enum; `market_scope` ∈ {all, known, external}; `limit` int 1–100, default 20. | P1-001 §14 |

## Evaluation & claims

| ID | Rule | Source |
|---|---|---|
| BR-21 | **Holdout is never used for tuning.** Benchmark version changes whenever judgments change. Hard queries are never modified to make the baseline look better or worse. | P0 §65, P1-001 §29–30 |
| BR-22 | **Winner ≠ the only relevant supplier.** Weak labels (winner/participants) are combined with human judgment. | P0 §68 |
| BR-23 | **No accuracy claim** appears in the pitch without a supporting measured metric. | P0 §95 |
| BR-29 | Temporal holdout: the system may use **only information that existed before the cutoff date** of the evaluated procurement. | Strategy §9, P0 §69 |
| BR-40 | Every benchmark query has ≥ 1 grade-2 supplier and preferably ≥ 1 grade-0 distractor; 3–8 plausible/relevant suppliers per query; relevance grades only 0/1/2. | P1-001 §29, §31 |

## Scope governance

| ID | Rule | Source |
|---|---|---|
| BR-27 | **Scope gate:** a new feature is in MVP only if it improves discovery accuracy, market expansion, explainability, measurable business value or demo clarity. | Strategy §20 |
| BR-41 | Do not build AI optimizations before the end-to-end vertical slice works; do not start with frontend, LLM or external scraping. | P0 §91, §107 |
| BR-42 | Baseline is built **before** tuning; benchmark starts early, not at the end. | D-10, P0 §81 |


## Hackathon Day-1 rules (2026-10-01, ADR-H1)

| ID | Rule | Source |
|---|---|---|
| BR-43 | `lot_id` is the procurement join key; **lots without supplier relations are kept** (targets) but never used as benchmark ground truth. | HD-02, dataset §3 |
| BR-44 | `procedure_name` and `subject` are one text signal (99.1% identical): index/score only one, at low weight; ТРУ item text has priority. | HD-03, dataset §4 |
| BR-45 | *(A1: АИС ГЗ award-only is a working interpretation; no participation/non-participation inference from АИС ГЗ.)* **No cross-platform win rate.** `historical_award_count` uses both platforms; participation/win counts use ЭМ only, until OQ-33 is answered. | HD-05 |
| BR-46 | OKPD2 is matched hierarchically and is **never the sole recommendation criterion**; every ranking shows which criteria contributed how much. | HD-04, organizer §6 |
| BR-47 | Every non-`unknown` `market_role` has a `role_basis` and ≥ 1 evidence item (source, URL/ref, observed_at); roles inferred from procurement patterns or OKVED are labelled *inferred*; a **VERIFIED manufacturer** requires an official manufacturer/industrial registry entry or explicit first-party production evidence — **never OKVED alone** (OKVED-only → `INFERRED_MANUFACTURER_CANDIDATE`, low confidence); the LLM never assigns roles. | HD-09 (A2), organizer §3, BR-09 |
| BR-48 | `entity_type` (from INN length) and `market_role` (from evidence) are separate fields and never derived from each other. | HD-09 |
| BR-49 | External enrichment is **precomputed and pre-loaded**; the demo/request path never calls the internet. | HD-07, organizer §9 |
| BR-50 | External expansion is offered when the category pool verdict is CONCENTRATED or THIN (thresholds in versioned config); suppliers in the pool-health headline are not named. | HD-08 |
