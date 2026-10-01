# Search, Ranking, Confidence & Explainability — Specification

> ### Hackathon Day-1 amendment (2026-10-01, ADR-H1)
> **Superseded where conflicting** by [Execution Baseline §7–9](../HACKATHON_EXECUTION_BASELINE.md#7-search-strategy):
> - Retrieval runs on **historical ТРУ items** (product text + OKPD2 hierarchy + procurement context) and extracts suppliers from
>   `SupplierHistory`; semantic retrieval (Branch B) becomes optional (v2 P2-001, kept only if it beats the baseline).
> - **§3 Match Score v1 feature table and weights are superseded** (C-24) by the configurable v2 feature set: `product_text_relevance`,
>   `okpd2_relevance`, `semantic_relevance`, `relevant_historical_awards`, `marketplace_participation` (ЭМ only), `customer_context_experience`,
>   `recency`, `procurement_value_similarity`. No cross-platform win rate (HD-05).
> - Still valid: renormalization (BR-05), lexical normalization `r/(r+k)` (ED-10), max-aggregation & deterministic tie-break (ED-09),
>   Match/Confidence/Risk separation, reason codes + contributions + templates (§6), LLM only for interpretation (§7), versioning (§9).
> - Baseline for comparison (§8) is now the **historical keyword + OKPD2 baseline** on real data (v2 P1-002).

> Sources: Phase 0 §17, §30–47; Strategy §5, §7; P1-001 §15–17, §46.
> **[ER]** = proposed detail filling a gap; must be confirmed in the owning task (feature definitions are
> intentionally left as "v1 proposal" — tune only against the benchmark dev split).

## 1. Retrieval strategy (D-04)

**Hybrid = Full-text + Semantic + Structured filters.** Rejected for MVP: knowledge graph (later), LLM retrieval, LLM agent search.

| Branch | Unit | Cap (tunable) | Mechanism |
|---|---|---:|---|
| A Lexical | offerings | 200 | PostgreSQL FTS (`russian` config; weights title A, category B, description C [ER]) + phrase matching; exact title bonus |
| A' Fuzzy (P1 priority) | offerings / names | shares A cap | `pg_trgm` similarity on normalized title/brand/model (typos) |
| B Semantic | offerings | 200 | pgvector cosine on e5 embeddings; **similarity floor** (ED-13) |
| C Category | suppliers | 100 | Exact canonical category match from intent |
| D Historical | suppliers | 100 | Similar past procurements (only if procurement data present) |

Union → dedupe by supplier → ≤ 500 suppliers → hard filters → aggregation → Top 100 fully ranked → Top N (default 20).

### Embeddings
- Default model: **multilingual-e5-base** (Russian support, CPU, SentenceTransformers) behind an `EmbeddingProvider` adapter.
- [ER] e5 requires prefixes: `"query: "` for queries, `"passage: "` for offerings; L2-normalize; record `model_name@revision` as `embedding_version`.
- Offering text for embedding [ER]: `title + category_name + key attributes + description (truncated ~512 tokens)`.
- Precompute offering vectors in batch (SF-03); only the query is embedded at request time.

### Lexical score normalization [ER ED-10]
Raw `ts_rank_cd` is unbounded and query-dependent. **Do not min-max per query** (a single weak hit would become 1.0 — EC-37). v1: `s = r / (r + k)` with `k` calibrated on the dev split; same approach for trigram similarity (already 0–1) and cosine (map `[floor,1] → [0,1]`).

### Offering → supplier aggregation [ER ED-09]
v1: supplier feature value = **max** over its matched offerings (best offering), matched offering = argmax. Rationale: prevents large catalogs from winning by breadth (EC-27). Alternatives (top-k mean, soft-OR) evaluated only on dev split.

## 2. Hard filters (BR-04)

Applied after union, before ranking, **only** for mandatory constraints:
inactive company (default policy A-104) · explicitly required region/local presence · mandatory certification · explicitly prohibited supplier type · user-applied UI filters (`market_scope`, `supplier_type`, `region` — semantics OQ-19).

## 3. Match Score v1 (D-06)

Deterministic weighted sum; every feature normalized to **0–1**; output 0–1 in API, 0–100 in UI.

| Feature | Weight | Meaning | v1 definition proposal [ER] | Applicable when |
|---|---:|---|---|---|
| SemanticRelevance | 0.30 | Meaning similarity | normalized cosine of best offering | semantic branch available |
| LexicalRelevance | 0.20 | Term overlap | normalized ts_rank_cd / trgm of best offering | always |
| CategoryMatch | 0.15 | Category alignment | 1 exact canonical category; 0.5 parent/related; 0 otherwise | intent has category |
| AttributeCoverage | 0.15 | Requested attributes satisfied | matched / requested attributes (numeric tolerance e.g. ±0 for sizes unless range given) | intent has ≥1 attribute |
| ProcurementExperience | 0.08 | Relevant past procurement | saturating `1 − e^(−n/3)` over similar records (n = count with similarity ≥ τ, before `as_of`) | procurement data exists in corpus |
| GeographicFit | 0.05 | Location vs requested region | 1 same region; 0.5 adjacent/federal district [needs mapping]; 0 otherwise | intent has region |
| SupplierTypeFit | 0.04 | Type vs requested type | 1 match; 0.5 unknown; 0 mismatch | intent has supplier type (soft) |
| DeliveryFit | 0.03 | Delivery capability to region | 1 if DELIVERY_REGION evidence covers region; else 0 | intent has region **and** delivery data exists (G-10) |

**Renormalization (BR-05):** `MatchScore = Σ w_i·f_i / Σ w_i` over *applicable* features. N/A is decided **per query** (and per corpus capability), never per supplier.

Weights live in a versioned config file (`ranking_config vX.Y.Z`); `ranking_version` is returned and logged.
Strategy-report weights (30/25/20/15/10) are **superseded** by these (C-01).

### Tie-break (ED-09)
`MatchScore desc → ConfidenceScore desc → supplier_id asc`.

### Not in ranking v1
Price (BR-07) · reliability/contract volume as quality (BR-08) · risk flags (BR-02) · LLM judgments (BR-09) · user feedback (future LTR).

## 4. Confidence Score (D-07)

"How strong is the evidence supporting this recommendation?" — separate from Match.

| Component | Weight | v1 definition proposal [ER] |
|---|---:|---|
| ProductEvidenceQuality | 0.30 | best evidence for the matched offering: official catalog/registry 1.0 · company website 0.7 · organizer data 0.6 · open web 0.3 · none 0 |
| LegalIdentityVerification | 0.25 | 1 INN+OGRN verified in legal registry & active · 0.6 INN present unverified · 0 none |
| SourceRecency | 0.15 | 1 if newest relevant evidence ≤ 90 days; linear decay to 0 at 730 days (thresholds OQ-26) |
| MultiSourceAgreement | 0.15 | independent sources confirming product/identity: 1 source 0.3 · 2 → 0.7 · ≥3 → 1 |
| ProfileCompleteness | 0.15 | `profile_completeness` (formula G-21: share of preferred fields present — INN, category, region, type, website, OKVED) |

## 5. Risk flags (separate from score)

`LOW_EVIDENCE` (ProductEvidenceQuality < 0.3) · `STALE_INFORMATION` (recency < threshold) · `UNVERIFIED_MANUFACTURER` (type=manufacturer without registry/catalog basis) · `UNKNOWN_LEGAL_STATUS` · `AMBIGUOUS_ENTITY` (open `possible_match`) · `NO_PROCUREMENT_HISTORY`. Thresholds [ER] tuned in P5-006.

## 6. Explainability (BR-12)

1. Engine emits **reason codes** from feature values with thresholds [ER], e.g. `CATEGORY_MATCH` if CategoryMatch = 1; `ATTRIBUTE_MATCH` if AttributeCoverage ≥ 0.5; `SEMANTIC_MATCH` if Semantic ≥ 0.6; `PROCUREMENT_EXPERIENCE` if n ≥ 1; `VERIFIED_MANUFACTURER`; `STRONG_PRODUCT_EVIDENCE`; `MULTI_SOURCE_VERIFICATION`; `KNOWN_SUPPLIER`/`EXTERNAL_SUPPLIER` (always one of them → reason codes never empty).
2. **Contribution map:** `contribution_i = 100 · w_i·f_i / Σ w_applicable` (points summing to Match 0–100).
3. **Template text** (RU default) rendered from codes + parameters (counts, attribute names). LLM paraphrase is Could-tier, never canonical.
4. **A vs B:** sort features by `contribution_A − contribution_B`; template names the top 1–2 differences ("ranks higher mainly because it matches more requested attributes and has stronger relevant procurement experience").

## 7. Query understanding (D1)

Canonical intent: `{product, category_terms[], attributes{}, region, supplier_types[], mandatory_constraints[]}` (+ `quantity` G-06).
- **v1 rule-based parser [ER ED-03]:** dictionaries (categories/synonyms, regions incl. "СПб/Санкт-Петербург/Петербург", supplier-type phrases "производитель/дистрибьютор"), regex for numbers+units (inches `"`/дюйм, cm→inch, ГБ/ТБ, liters, pieces for quantity), mandatory-constraint phrases ("только", "обязательно", "не менее").
- **Optional LLM parser** behind adapter: JSON-schema-constrained output, temperature 0, timeout (~1.5 s), cache keyed by `(normalized_query, parser_version)`; any failure → rule-based result + `LLM_UNAVAILABLE` warning.
- Intent is **interpretation**, never fact (BR-09). Benchmark runs in deterministic mode (rule-based or cached LLM) — NFR-DET-02.

## 8. Baseline vs challenger

| | Baseline | Challenger (Supplier Radar) |
|---|---|---|
| Retrieval | FTS only (Branch A lexical, no trigram) | Branches A, A', B, C, D |
| Ranking | normalized lexical score, best offering per supplier | Match Score v1 |
| Parser | none (raw query) | rule-based (+ optional LLM, cached) |
| Code path | `SearchService.search(mode="baseline")` | `mode="hybrid"` |
Both share aggregation, filters and response shape, so comparisons isolate retrieval/ranking quality.

## 9. Versioning

Every response/log/benchmark report records: `parser_version`, `ranking_version` (config), `index_version` (projection build), `embedding_version`, `benchmark_version`. Determinism (NFR-DET-01) holds only when all five match.
