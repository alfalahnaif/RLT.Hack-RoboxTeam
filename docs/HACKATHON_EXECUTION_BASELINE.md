# Supplier Radar — Hackathon Execution Baseline

```text
Status: AUTHORITATIVE — HACKATHON DAY 1
Supersedes: pre-hackathon assumptions where conflicts exist
Date: 2026-10-01 · Owner-commanded reconciliation · Decisions: ADR-H1 (HD-01…HD-10) · Amended 2026-10-01 (A1, A2)
```

> **Amendments (2026-10-01, owner):**
> **A1 — АИС ГЗ semantics are not confirmed.** The only confirmed fact is that *every provided АИС ГЗ supplier row has `is_winner=true`*.
> "АИС ГЗ = awarded suppliers only" is a **working interpretation pending OQ-33**; all calculations stay conservative (HD-05). Encoded as the observation `coverage_semantics = WINNER_ROWS_ONLY_OBSERVED` (A3).
> **A2 — Manufacturer classification tightened.** `VERIFIED` manufacturer requires strong evidence (official manufacturer/industrial registry entry
> or explicit first-party production evidence). Manufacturing OKVED alone yields at most `INFERRED_MANUFACTURER_CANDIDATE` (low confidence);
> a company is **never** labelled `VERIFIED_MANUFACTURER` from OKVED alone (HD-09, §6, BR-47).

> This is the **implementation baseline for the rest of the hackathon**. Where it conflicts with a pre-hackathon document,
> this document wins (see [README §2](README.md#2-source-of-truth-hierarchy)); the conflict is logged in
> [CONFLICTS.md](analysis/CONFLICTS.md) (C-20…C-27). Facts come from:
> [Organizer briefing](sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md) (rank 1) ·
> [Real dataset analysis](analysis/REAL_DATASET_ANALYSIS_2024_2025.md) (verified numbers) ·
> [ADR-H1](decisions/ADR-HACKATHON-DAY1-REAL-DATA-BASELINE.md) (decisions).

---

## 1. Official organizer requirements (condensed)

| # | Requirement | Where it lands |
|---|---|---|
| O-1 | Identify **regional suppliers, manufacturers, distributors**; fit real procurement processes | §4, §5 |
| O-2 | Expand the supplier pool → competition, price, less dependence, less disruption risk | §4, §11 |
| O-3 | Enrich organizations with **roles** (manufacturer, distributor, supplier, dealer, reseller, other intermediary); role must be **explainable with evidence** | §6, §12 |
| O-4 | **First step: analyze the provided CSVs** (real 2024–2025 data) | Done → dataset analysis; P1-001A |
| O-5 | Understand OKPD2 and its levels, but **don't rely only on OKPD2** | §8 |
| O-6 | Explain why selected, why A > B, which criteria combined, which weighed more; methodology **understandable by the whole team** | §8, §9 |
| O-7 | Simple scoring is fine; **no AI for its own sake** | §7, §8 |
| O-8 | Validate existing suppliers, identify roles, expand via open sources; *low diversity → risk → new suppliers → enrich* | §10, §11 |
| O-9 | Enrichment may be **precomputed**; **no live-internet dependency** in the defense | §11 |
| O-10 | **One integrated UI** serving specialist / manager / analyst | §12 |
| O-11 | ≈ 5–10 s per recommendation acceptable; 1 min not; several demo cases within a ~5-min pre-defense | §16 |

## 2. Evaluation criteria → what we optimize

| Criterion | Points | Our answer | Proof in the demo |
|---|---:|---|---|
| Functionality & integrity | **30** | One working path: real lot → shortlist → explanation → pool health → external expansion | Live click-through of 3+ golden lots, no manual steps |
| Matching quality | **25** | Item-level text + OKPD2 hierarchy + history (awards, participation, customer) with visible contributions | Temporal replay metrics vs OKPD2 baseline (claims register) |
| Pool enrichment | n/a (OQ-41) | Curated, verified external suppliers with roles for 1–2 weak categories | "Sources used · records analyzed · N new suppliers · roles" panel |
| Explainability | n/a (OQ-41) | Reason codes + per-feature points + evidence; role basis + evidence | "Why" expansion on every card; role badge with source |
| UI | **10** | Existing Design System UI, adapted — **not** the main time sink | Clean, Russian, fast |

Rule: **integration first** (30 pts) → ranking quality (25) → enrichment/explainability → UI polish last.

## 3. Real dataset — what we actually have

Three CSVs joined by `lot_id`: **604,452 lots** (АИС ГЗ 332,646 · ЭМ 271,806) · **1,010,138 supplier rows**
(44,196 INNs) · **2,971,651 ТРУ items** (8,453 OKPD2 codes) · 2,785 customers (+ 8,449 lots with empty customer INN) · 2024-01-08 → 2025-12-31.

Facts that shape the design (details and numbers: [dataset analysis](analysis/REAL_DATASET_ANALYSIS_2024_2025.md)):
1. `lot_id` joins everything with **0 orphans**; `procedure_id` is 1:1 with `lot_id`.
2. ТРУ `product_name` is the richest text (≈ 94% of items add text not in the lot title); **no separate description field**.
3. `procedure_name` = `subject` in 99.1% of lots → index only one.
4. **Every provided АИС ГЗ supplier row has `is_winner=true`** (confirmed fact). Whether АИС ГЗ records only awarded suppliers is a *working interpretation* pending OQ-33 (A1). **ЭМ** rows include winners and non-winners (≈ 2.7 suppliers per lot).
5. 54,279 АИС ГЗ lots (16.3%) have **no supplier relation** — kept, not used as ground truth.
6. 53.4% of distinct suppliers are **individuals/IEs** (12-digit INN) → personal-data minimization.
7. OKPD2 is mostly full-depth but mixed-depth and sometimes noisy (`32.99.59.000` "other products").
8. Replay: 92.5% of 2025 ЭМ winners had earlier awards in the same OKPD2 class → **ranking, not recall, is the hard part**; discovery must come from external expansion.
9. Data has **no supplier names, regions (except INN prefix), OGRN, contract outcome or item price**.

## 4. Product problem & business value

**Problem.** A procurement specialist preparing a lot does not know who, beyond the usual winner, can supply it; a manager
cannot see where the city depends on one or two suppliers. Classifier lookups (OKPD2) are noisy and hide the products
actually bought; supplier roles (manufacturer vs reseller) are invisible.

**Product.** *Supplier Radar* turns a procurement lot (existing `lot_id` or free-text need) into:
1. a **ranked, explained shortlist** of suppliers with relevant history (who to invite and why),
2. a **supplier-pool health** verdict for the category (how many, how recent, how concentrated),
3. when the pool is weak, **verified external suppliers with roles** (manufacturer/distributor…) to widen competition.

**Value chain** (organizer §2): more relevant invitees → more competition → better prices, lower dependence and disruption risk.

## 5. Updated domain model (canonical)

```text
ProcurementLot (lot_id)                       ← Извещения
│  publish_date, platform {AIS_GZ, EM}, customer_inn, start_price, subject, is_smp, reqnum, procedure_id
├── ProcurementItem[]  (lot_id, line_no)      ← ТРУ
│     product_name (raw + normalized), okpd2_code (+ okpd2 levels), extracted attributes (later)
└── SupplierHistory[] (lot_id, supplier_inn)  ← Поставщики
      is_winner, supplier_kpp, coverage_semantics {WINNER_ROWS_ONLY_OBSERVED (АИС ГЗ — observation; award-only = working interpretation, OQ-33), MIXED_WINNER_NONWINNER_ROWS_OBSERVED (ЭМ — winner + non-winner rows; completeness not claimed)}

Supplier (supplier_id = UUIDv5(inn))          ← distinct INNs + enrichment
│  inn (string), entity_type {legal_entity, individual_entrepreneur, unknown}, inn_region_code,
│  is_known_supplier (as_of), data_quality_flags
└── SupplierProfile (enrichment; optional)
      display_name, ogrn, legal_status, region, website,
      market_role {manufacturer, distributor, dealer, supplier, reseller, other_intermediary, unknown},
      role_basis {registry, catalog, website, procurement_pattern, declared, manual_verified}, role_confidence
      └── SupplierEvidence[]  (claim, evidence_type, source_name, source_url|record_ref, observed_at)

CategoryPoolHealth (okpd2_code, level, window, as_of)  ← derived
ExternalCandidate = Supplier with is_known_supplier=false + SupplierProfile + Evidence (curated, pre-loaded)
RawSourceRecord (file, row_no, payload, checksum)       ← every CSV row, never discarded (BR-31)
```

Rules: `entity_type` (legal form, from INN) and `market_role` (business role, from evidence) are **never mixed** (HD-09).
INN is a string, validated, never cast to int; KPP optional, never identity. Fuzzy matches are `possible_match`, never auto-merged.
Full field list: [DOMAIN_MODEL §0](domain/DOMAIN_MODEL.md#0-hackathon-v2-canonical-model-authoritative).

## 6. Supplier roles (classification)

| Role | Basis (best → weakest) | Explainable as |
|---|---|---|
| manufacturer — **VERIFIED** | official manufacturer / industrial registry entry (e.g. ГИСП, реестр российской промышленной продукции) · explicit first-party production evidence (own plant/production on the company's site or catalog, with address) | "Listed in <registry> as producer of <product> (source, date)" |
| manufacturer — **INFERRED_MANUFACTURER_CANDIDATE** | manufacturing OKVED (sections 10–32) **alone**, or weak/indirect signals; low confidence; never shown as verified | "Possible manufacturer: manufacturing OKVED <code> (ЕГРЮЛ, date) — not verified" |
| distributor / dealer | official dealer/distributor certificate or brand page · OKVED 46.x wholesale primary | "Authorized distributor of <brand> per <source>" |
| reseller / other intermediary | OKVED 47.x / 46.x with broad unrelated assortment · procurement pattern (wins across many unrelated OKPD2 sections) | "Supplies 40+ unrelated categories (procurement pattern)" — flagged as *inferred* |
| supplier | known procurement supplier without role evidence | default for known suppliers |
| unknown | nothing verified | shown as "role not verified" |

`role_verification ∈ {VERIFIED, INFERRED, UNVERIFIED}` accompanies every role. `procurement_pattern` and OKVED-only bases are *inferred* (lower confidence, labelled as such).
**A company is never labelled `VERIFIED_MANUFACTURER` from OKVED alone** (A2). The LLM never assigns roles (BR-09).
For the hackathon, roles are assigned for **pre-selected suppliers only** (golden lots' top suppliers + external candidates), not for 44k INNs.

## 7. Search strategy

Two entry points, one pipeline:
- **By lot** (`lot_id` of an existing procurement) — primary demo path; items and OKPD2 are taken from ТРУ.
- **By text** (existing S-01 free-text box) — the text becomes a virtual one-item target lot; OKPD2 inferred from matching items.

```text
Target Procurement Lot
  → Load detailed ТРУ items
  → Normalize product text (NFC, lower, ё→е, footnotes ¹, "тип N", units/numbers)
  → Interpret procurement need (rule-based; LLM optional & never authoritative)
  → Retrieve similar historical lots (as_of = target publish_date)
       ├── Product text (PostgreSQL FTS on item names; russian + simple configs)
       ├── OKPD2 (exact → XX.XX.XX → XX.XX prefix)
       ├── Semantic similarity (P2-001, only if it beats the baseline)
       └── Procurement context (same customer, price band)
  → Extract historical suppliers (SupplierHistory of retrieved lots)
  → Aggregate supplier evidence (per supplier: matched lots, awards, participations, customers, recency)
  → Explainable ranking (§8)
  → Known supplier recommendations (Top N, one per supplier)
  → Supplier pool health (§10)
  → If weak/concentrated → external expansion (§11) → verified manufacturer/distributor candidates
```

Retrieval caps (config): ≤ 2,000 similar items → ≤ 500 lots → ≤ 300 suppliers ranked → Top 20 shown.
Text signal is counted **once**: item text (high) + lot subject (low); `procedure_name` not indexed (duplicate).

## 8. Ranking strategy (configurable, benchmarked)

Deterministic weighted sum of normalized features (0–1), weights in a **versioned config** — *initial values are a starting point, not truth*.

| Feature | Definition (v1) | Applies when | Initial weight |
|---|---|---|---:|
| `product_text_relevance` | best text similarity between target items and the supplier's historical items (normalized FTS rank `r/(r+k)`) | always | 0.30 |
| `okpd2_relevance` | best hierarchy match of supplier's historical items: exact 1.0 · `XX.XX.XX` 0.7 · `XX.XX` 0.4 · else 0 | target has OKPD2 | 0.20 |
| `semantic_relevance` | cosine of e5 embeddings (floor-calibrated) | semantic index exists **and** beats baseline | 0.15 |
| `relevant_historical_awards` | saturating `1 − e^(−n/3)`, n = awards on *relevant* lots before `as_of` (both platforms) | always | 0.15 |
| `marketplace_participation` | saturating over ЭМ participations on relevant lots (ЭМ only) | relevant ЭМ history exists | 0.05 |
| `customer_context_experience` | 1 if supplied this customer on relevant lots, 0.5 any lot for this customer, else 0 | always | 0.08 |
| `recency` | 1 if last relevant award ≤ 180 days before `as_of`, linear decay to 0 at 730 days | always | 0.05 |
| `procurement_value_similarity` | `1 − |log10(p_target) − log10(p_hist_median)| / 2`, clipped (scale of contract, **not** price competitiveness — D-13 holds) | both prices > 0 | 0.02 |

- **Renormalization:** features not applicable to the query are removed and weights renormalized (BR-05); per-feature contributions are kept.
- **No global win rate** across platforms (HD-05). `marketplace_win_count` may appear as *evidence text*, not as a feature, until OQ-33 is answered.
- **Tie-break:** score desc → relevant awards desc → `supplier_id` asc (determinism, NFR-DET-01).
- Match ≠ Confidence ≠ Risk (BR-02): role/enrichment evidence feeds Confidence and badges, not Match.
- Weights are tuned **only on the dev split** of the replay benchmark; holdout untouched (BR-21).

Internal output (per supplier):
```json
{
  "supplier_id": "…", "match_score": 91, "ranking_version": "1.0.0",
  "components": { "product_text": 31, "okpd2": 20, "historical_awards": 16, "customer_context": 9, "recency": 7, "value_similarity": 2, "marketplace_participation": 6 },
  "not_applicable": ["semantic"],
  "reason_codes": ["PRODUCT_TEXT_MATCH", "OKPD2_EXACT", "RELEVANT_AWARDS", "SAME_CUSTOMER", "RECENT_ACTIVITY", "KNOWN_SUPPLIER"],
  "evidence": [{ "type": "PROCUREMENT_HISTORY", "lot_id": "5659204", "publish_date": "2025-04-24", "item": "Ноутбук …", "is_winner": true }]
}
```

## 9. Explainability strategy

1. **Why this supplier** — reason codes (controlled vocabulary) + points per feature summing to the score + 1–3 *evidence lots* (date, item text, won/participated, customer).
2. **Why A above B** — difference of contributions, top 1–2 drivers named in a template ("ranks higher mainly because of 12 relevant awards vs 3").
3. **Why this role** — `market_role` + `role_basis` + evidence (source, URL/ref, `observed_at`); inferred roles labelled *inferred*.
4. **Methodology page** (analyst level) — the feature table above, weights, data sources, records analyzed, benchmark results; one page the whole team can explain.
5. Templates in Russian (UI default) and English; never LLM-generated as canonical (BR-12).

Reason-code vocabulary v2 (additions): `PRODUCT_TEXT_MATCH`, `OKPD2_EXACT`, `OKPD2_RELATED`, `RELEVANT_AWARDS`, `MARKETPLACE_PARTICIPATION`, `SAME_CUSTOMER`, `RECENT_ACTIVITY`, `SIMILAR_CONTRACT_SCALE`, `SEMANTIC_MATCH`, `VERIFIED_MANUFACTURER` (strong evidence only), `INFERRED_MANUFACTURER_CANDIDATE`, `VERIFIED_DISTRIBUTOR`, `REGIONAL_SUPPLIER`, `KNOWN_SUPPLIER`, `EXTERNAL_SUPPLIER`.

## 10. Supplier Pool Health

Answers: *How large is the historical pool? How many are recent? How concentrated are awards? Are we dependent on a very small set? Should we expand?*

| Metric | Definition (per category = OKPD2 code at chosen level; window = 24 months before `as_of`) |
|---|---|
| `unique_supplier_count` | distinct winners (awards) in the category |
| `observed_supplier_count` | distinct suppliers incl. ЭМ non-winning participants |
| `recent_supplier_count` | distinct winners in the last 6 months |
| `top_supplier_share` | awards of the #1 supplier / all awards |
| `top_3_supplier_share` | awards of top 3 / all awards |
| `lots`, `customers` | demand size |
| HHI | deferred (computed in analysis only) |

Verdict (config thresholds, v1): **CONCENTRATED** if `top_supplier_share ≥ 0.5` or `top_3_supplier_share ≥ 0.8`;
**THIN** if `recent_supplier_count ≤ 3` while `customers ≥ 10`; else **HEALTHY**. CONCENTRATED/THIN → "Expand the pool" action.

Flow: **weak/concentrated pool → expansion recommendation → external discovery (pre-loaded) → verified candidates.**
Demo categories (to confirm in P3-001): **10.51.11.141 sterilized milk** (top-1 94%, 40 customers) primary;
01.25.19.150 cranberry / 10.61.22.130 rice flour backup; 10.39.17.111 tomato purée (top-3 76%) as a third example.

## 11. External enrichment (precomputed)

```text
Target weak category → find a small number of high-quality companies → verify identity (INN/OGRN, active)
→ classify market role (with basis) → collect product evidence → store source + URL + observed_at → pre-index for demo
```

- Quality over quantity: **~10 genuinely relevant, verified external companies** per demo category is the target.
- Sources (legality per OQ-08): ГИСП (industrial products/manufacturers), ФНС ЕГРЮЛ / «Прозрачный бизнес» (identity, status, OKVED), manufacturer websites/catalogs. Open web = discovery only, never sole verification (BR-38).
- Stored as a versioned, file-based curated dataset (`data/enrichment/…`, JSON/CSV with evidence) loaded by the same ingestion CLI; demo runs fully offline.
- Optionally validate **existing** top suppliers of the demo categories (role + identity) the same way.
- External companies are marked `is_known_supplier=false`; no procurement history ≠ penalty (risk flag `NO_PROCUREMENT_HISTORY` only).

## 12. Updated architecture

Unchanged foundation: **modular monolith** (FastAPI) + **PostgreSQL** (FTS, pg_trgm; pgvector only when P2-001 starts) + **Next.js** UI (existing Design System) + **CLI** batch jobs + Docker Compose. No Redis/Celery/ES/K8s/microservices.

| Module | Responsibility (v2) |
|---|---|
| `ingestion/` | CSV → `raw_*` staging (COPY) → canonical tables; normalization; quality flags; idempotent; curated enrichment loader |
| `procurement/` | lots, items, supplier history, `as_of` filtering (valid time = `publish_date`) |
| `search/` | target-lot loader, text/OKPD2/(semantic)/context retrieval, candidate supplier extraction |
| `ranking/` | pure: features, scorer, renormalization, contributions, reason codes, templates |
| `suppliers/` | supplier + profile + evidence + role; known/external |
| `pool_health/` | category metrics + verdict (precomputed table + on-demand for a target) |
| `evaluation/` | replay benchmark builder, runner, metrics, reports, claims |
| `api/` | REST `/api/v1` |

API v2 (analysis level; replaces nothing yet built):
`POST /api/v1/recommendations` (`{lot_id}` or `{text}`, `as_of?`, `limit`) · `GET /api/v1/lots/{lot_id}` ·
`GET /api/v1/categories/{okpd2}/pool-health` · `GET /api/v1/suppliers/{id}` (+ evidence, history) · `GET /api/v1/meta` (sources, records analyzed, versions) · `GET /api/v1/health`.
`POST /search` (free text) maps onto `/recommendations {text}`. Typed client mock mode stays until the live API exists (ED-27).

Scale: 3M items fit single PostgreSQL with GIN FTS; target ≤ 10 s per recommendation (internal goal ≤ 5 s).

## 13. Implementation order (Roadmap v2)

Full task definitions: [tasks/HACKATHON_V2_TASKS.md](implementation/tasks/HACKATHON_V2_TASKS.md) · status: [ROADMAP task index](implementation/IMPLEMENTATION_ROADMAP.md#task-index-roadmap-v2).

| Order | ID | Task | Output |
|---:|---|---|---|
| 1 | **P1-001A** | Actual dataset profiling (reproducible) | profiling script + report reproducing §3 numbers |
| 2 | P1-001B | Canonical mapping | field → canonical mapping, contracts v0.2 |
| 3 | P1-001C | Normalization rules | text/INN/OKPD2 normalization + tests |
| 4 | P1-001D | PostgreSQL ingestion | compose DB, migrations, idempotent CSV load |
| 5 | P1-001E | Temporal benchmark seed | replay cases (dev/holdout), labels 2/1/0 |
| 6 | P1-001F | Golden demo cases | frozen demo lots + expected story |
| 7 | P1-002 | Historical keyword + OKPD2 baseline | end-to-end baseline + baseline metrics |
| 8 | P2-001 | Semantic retrieval | embeddings on items (only kept if it helps) |
| 9 | P2-002 | Hybrid candidate generation | union of branches, caps |
| 10 | P2-003 | Explainable supplier ranking | §8 scorer + reasons + evidence |
| 11 | P3-001 | Supplier pool health | metrics + verdict + category selection |
| 12 | P3-002 | Supplier role enrichment | roles with basis/evidence for selected suppliers |
| 13 | P3-003 | Targeted external supplier expansion | ~10 verified externals per demo category, pre-loaded |
| 14 | P4 | Integrated product UI | existing UI wired to live API; three stakeholder levels |
| 15 | P5 | Evaluation + demo freeze | final metrics, claims register, frozen demo, offline dry run |

Critical path: P1-001A → B → C → D → E → P1-002 (first end-to-end result) — then P2-003 and P3-001 before any semantic work.
P3-002/P3-003 (curation) can run in parallel by a second person once P3-001 picks the categories.

## 14. Golden demo strategy

Demo (~5 min, several cases): 
1. **Generic title, specific item** — lot 5718896 *"Поставка компьютерного оборудования"* → item *Ноутбук Acer Aspire 5…* → laptop suppliers ranked, actual winner high (naive rank 2), reasons visible.
2. **Spec-rich goods** — lot 5545252 (office chair spec) or 5659204 (ASUS laptops): shortlist + "why A > B".
3. **Concentrated category** — sterilized milk 10.51.11.141: pool health CONCENTRATED (top-1 94%) → "Expand the pool" → ~10 verified external manufacturers with roles and sources.
4. **Honest hard case (backup/Q&A)** — gloves 5542696: winner had only one prior relevant award; show what the system can and cannot know.
5. **Methodology view** — features, weights, sources, records analyzed (604k lots / 1.01M supplier rows / 2.97M items), replay metrics.

Golden lots are frozen in P1-001F, excluded from tuning, and replayed with `as_of` = their publish date (no leakage).
**Frozen 2026-10-01 (P1-001F):** primary 5718896 · 5545252 · 5542696; backup 6022687 · 5612123 — cards and stories in [`benchmark/golden/`](../benchmark/golden/README.md) (qualitative only).

## 15. Open organizer questions (top)

Full list: [OPEN_QUESTIONS — Organizer question pack](analysis/OPEN_QUESTIONS.md#organizer-question-pack--hackathon-day-1).
1. **OQ-33 (critical):** АИС ГЗ supplier rows are 100% `is_winner=true`, ЭМ has winners and non-winners — does АИС ГЗ contain only awarded suppliers, not the participant list?
2. OQ-34: exact meaning of `is_eshop_or_aisgz` values (ЭМ = Электронный магазин СПб?), and of procedures without supplier rows.
3. OQ-35/36: `is_smp` (why never true on ЭМ) and `reqnum`.
4. OQ-38: expected role classification (which roles count, what evidence is acceptable).
5. OQ-39: "regional" — St Petersburg + Leningrad oblast only? Hard filter or preference?
6. OQ-40/41: how the jury evaluates matching quality; point split for enrichment/explainability.

## 16. Risks (top)

| Risk | Mitigation |
|---|---|
| Integration slips (30 pts) — modules done, product not connected | P1-002 delivers an end-to-end baseline first; daily end-to-end check |
| Wrong `is_winner` interpretation inflates metrics | HD-05 platform-separated counters; OQ-33 |
| History-based ranking ≈ OKPD2 lookup (no added value) | Benchmark vs naive baseline; keep only features that help on dev |
| External enrichment time sink / unverifiable sources | Pick 1–2 categories; 10 verified companies; evidence template; legal sources only |
| Personal data of IEs (53% of suppliers) | Show INN-only identity for IEs unless public registry data; no contact scraping |
| Ingestion time on 3M rows | COPY into staging, set-based SQL; measured in P1-001D |
| Latency > 10 s | Candidate caps, GIN indexes, precomputed pool health |
| UI over-investment | UI = 10 pts; reuse existing screens; wire live API only |
Full register: [RISK_REGISTER](analysis/RISK_REGISTER.md).

## 17. Explicitly out of scope (hackathon)

Real-time crawling/live web discovery · enrichment of all 44k suppliers · LLM-assigned roles, facts or ranking ·
learning-to-rank · global cross-platform win rate · price-competitiveness scoring · contact scraping of individuals ·
three separate apps / role-based dashboards · authentication, RBAC, billing, multi-tenancy · microservices, Kubernetes, Redis/queues ·
AIS ГЗ integration · re-designing the Design System or rewriting the frontend · synthetic seed as product data.
