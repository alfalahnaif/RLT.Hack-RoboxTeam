# Domain Model

> Sources: Phase 0 §18–29, P1-001 §4–17, §31, §36. **This is a logical model, not a DB schema.**
> Physical schemas are created in tasks P1-007/P1-008 (JSON Schema contracts) and P2-001 (DB migration).
> Once contracts exist, `/contracts/*.schema.json` becomes the field-level source of truth (see docs/README §2).
> Fields/entities marked **[ER]** are recommended additions — pending acceptance (P0-004).

> **2026-10-01 — Hackathon day 1:** §0 below is the **authoritative canonical model** (ADR-H1, HD-02/03/09), derived from the real
> organizer data. Sections §1–§5 are the **pre-hackathon model**: still valid for evidence, enums, search/evaluation entities,
> invariants and identifiers, but **superseded where they conflict with §0** (notably §2.1 `supplier_type`, §2.2 offering as the
> only search unit, §2.3 ProcurementRecord shape).

## 0. Hackathon v2 canonical model (authoritative)

```text
ProcurementLot (lot_id) ──┬──< ProcurementItem (lot_id, line_no)          ← ТРУ
                          └──< SupplierHistory (lot_id, supplier_inn) >── Supplier (INN)   ← Поставщики
Supplier ──1:0..1── SupplierProfile ──< SupplierEvidence                  ← curated enrichment
Supplier (origin=EXTERNAL_ENRICHMENT) + Profile + Evidence = ExternalCandidate
CategoryPoolHealth (okpd2_code, level, window_months, as_of)              ← derived
RawSourceRecord (dataset, row_number, payload, checksum)                  ← every CSV row (BR-31; P1-001D)
```

> **Field-level source of truth since P1-001B (2026-10-01): [`/contracts/*.schema.json`](../../contracts/) v0.2.0.** Column-by-column rules,
> identity templates, derived fields and quality flags: [DATA_MAPPING.md](DATA_MAPPING.md). The tables below summarize the contracts.

### 0.1 ProcurementLot (core aggregate — HD-02) · `procurement_lot.schema.json`
| Field | Type | Rule |
|---|---|---|
| id | UUID | UUIDv5(`lot:`+lot_id) (BR-30) |
| lot_id | string | canonical procurement key; joins items and supplier history; never cast to int |
| procedure_id | string | attribute only (1:1 with lot_id in this extract) |
| publish_date | date | **valid-time anchor** for `as_of` (ED-04, HD-06) |
| platform | enum `AIS_GZ · EM` | from `is_eshop_or_aisgz` |
| subject | string? | canonical lot title (low-weight context); null → `MISSING_SUBJECT` |
| procedure_name_variant | string? | `procedure_name` only when it differs from `subject` (~0.9%); not indexed by default (BR-44) |
| start_price | decimal string? | Decimal semantics; zero preserved + `ZERO_START_PRICE`; null + `MISSING_START_PRICE`; context only (D-13) |
| reqnum | string? | opaque (OQ-36) |
| is_smp | bool | platform-dependent (true only on AIS_GZ; OQ-35); not a ranking feature |
| customer_inn / customer_kpp | string? / string? | nullable with `MISSING_INN` / `MISSING_KPP`; malformed kept + flagged |
| has_supplier_history | bool (optional) | dataset-coverage attribute; false for 54,279 AIS_GZ lots → target-only, never ground truth |
| data_quality_flags, source_ref | | §DATA_MAPPING 5; `{dataset, row_number}` |

### 0.2 ProcurementItem (primary search unit for known suppliers — HD-03) · `procurement_item.schema.json`
| Field | Type | Rule |
|---|---|---|
| id | UUID | UUIDv5(`item:`+lot_id+`:`+line_no) |
| lot_id, line_no | string, int | `line_no` = ordinal of the row within its lot in source-file order (no source item id exists) |
| content_hash | sha256 hex | drift detection on re-delivery (not identity) |
| product_name_raw | string | byte-exact as delivered (may be empty → `MISSING_PRODUCT_NAME`) |
| product_name_normalized | string? | produced by P1-001C; null until normalized / when empty |
| is_generic_type_name | bool? (optional) | e.g. `Пюре томатное тип 1` (P1-001C) |
| okpd2_code_raw / okpd2_code | string / string? | raw kept; normalized null when missing/invalid (`MISSING_OKPD2` / `INVALID_OKPD2`) |
| okpd2_depth, okpd2_section, okpd2_class, okpd2_subclass, okpd2_group, okpd2_subgroup, okpd2_kind | derived | ОКПД2 hierarchy (DATA_MAPPING §4.1); null above the code's depth |
| data_quality_flags, source_ref | | |
Not in v0.2.0: extracted attributes (numbers + units) — a later minor version if P2 needs them.

### 0.3 SupplierHistory (supplier ↔ lot relation) · `supplier_history.schema.json`
| Field | Type | Rule |
|---|---|---|
| id | UUID | UUIDv5(`history:`+lot_id+`:`+supplier_inn); dedup key (lot_id, supplier_inn) — 31 duplicate pairs merged (is_winner = OR, first non-empty KPP), all raw rows in `source_refs` + `DUPLICATE_SUPPLIER_RELATION` |
| lot_id, supplier_id, supplier_inn | string, UUID, string | identity by INN; KPP never identity |
| supplier_kpp | string? | as delivered; `MISSING_KPP` when empty |
| is_winner | bool | as delivered |
| platform, publish_date | enum, date | denormalized from the lot for `as_of` filtering |
| coverage_semantics | enum `WINNER_ROWS_ONLY_OBSERVED · MIXED_WINNER_NONWINNER_ROWS_OBSERVED` | AIS_GZ → `WINNER_ROWS_ONLY_OBSERVED` (observation: all delivered АИС ГЗ rows have `is_winner=true`; "award-only" is a working interpretation pending OQ-33); EM → `MIXED_WINNER_NONWINNER_ROWS_OBSERVED` (winner and non-winner rows observed; participant-list completeness **not** claimed). Replaces `AWARD_ONLY_ASSUMED · PARTICIPANT_LIST` (ADR-H1 A3, A4) |
| data_quality_flags, source_refs | | |

Derived per supplier (always with `as_of`, never stored as global truth): `historical_award_count` (both platforms) · `marketplace_participation_count`,
`marketplace_win_count` (EM only) · `last_award_at` · `customers_served`. **No cross-platform `win_rate`.**

### 0.4 Supplier · `supplier.schema.json`
| Field | Type | Rule |
|---|---|---|
| supplier_id | UUID | UUIDv5(`supplier:inn:`+inn) |
| inn | string | trimmed as delivered; never int; malformed kept + `INVALID_INN_FORMAT`; checksum failure → `INVALID_INN_CHECKSUM` |
| entity_type | enum `legal_entity · individual_entrepreneur · unknown` | from INN shape (10 / 12 digits / other); **not** a market role (HD-09) |
| inn_region_code | string(2)? | INN prefix = tax-registration region evidence (A-115), not delivery; null if malformed |
| origin | enum `ORGANIZER_DATA · EXTERNAL_ENRICHMENT` | |
| first_seen_publish_date | date? | earliest related lot date (null for external). **Known at T := first_seen_publish_date < T** — no stored `is_known_supplier` |
| data_quality_flags | | entity-level INN flags |

### 0.5 SupplierProfile (enrichment; only for selected suppliers) · `supplier_profile.schema.json`
| Field | Type | Rule |
|---|---|---|
| supplier_id | UUID | 1:0..1 with Supplier |
| display_name, ogrn, legal_status, region, city, website, okved_primary | optional | registry / company-site facts, each evidence-backed |
| market_role | enum `manufacturer · distributor · dealer · supplier · reseller · other_intermediary · unknown` | evidence-based (HD-09) |
| role_basis | enum `official_registry · first_party_production · dealer_certificate · company_website · okved · procurement_history · procurement_pattern · declared · manual_review` or null | null only for `unknown` |
| role_verification | enum `VERIFIED · INFERRED · UNVERIFIED` | manufacturer `VERIFIED` only with `official_registry` or `first_party_production`; `okved`/`procurement_pattern`/`declared` ⇒ never VERIFIED, confidence ≤ 0.4 (manufacturer + INFERRED is shown as `INFERRED_MANUFACTURER_CANDIDATE`) — ADR-H1 A2 |
| role_confidence | 0–1 | separate from Match (BR-02) |
| role_evidence_ids | UUID[] | ≥ 1 for any role other than `unknown` (BR-47) |
| observed_at | date-time | |
Individuals/IEs: only registry-public fields; no contacts (NFR-PRIV-01).

### 0.6 SupplierEvidence · `supplier_evidence.schema.json`
`evidence_id, supplier_id, claim, evidence_type {PROCUREMENT_HISTORY · OFFICIAL_REGISTRY · LEGAL_REGISTRY · FIRST_PARTY_PRODUCTION · COMPANY_WEBSITE · DEALER_CERTIFICATE · PRODUCT_CATALOG},
supports {MARKET_ROLE · PRODUCT_RELEVANCE · LEGAL_IDENTITY}, source_name, source_url | source_record_ref (≥ 1 required; PROCUREMENT_HISTORY → `lot:{lot_id}`), observed_at, verification_status {VERIFIED · UNVERIFIED}, confidence, related_okpd2_codes?`.
Supersedes the §0.6 draft type list (`ROLE_REGISTRY`, `ROLE_WEBSITE`, `LEGAL_IDENTITY` as a type) and §3.2.

### 0.7 CategoryPoolHealth (derived — HD-08)
`okpd2_code, level, window_months, as_of, lots, customers, unique_supplier_count, observed_supplier_count, recent_supplier_count,
top_supplier_share, top_3_supplier_share, hhi (analysis only), verdict {HEALTHY, CONCENTRATED, THIN}, thresholds_version`.

### 0.8 Recommendation output (value object)
`target {lot_id | text}, as_of, ranking_version, suppliers[{supplier_id, match_score 0–100, components{}, not_applicable[], reason_codes[], evidence_lots[], market_role?, known_at_as_of}], pool_health, external_candidates[], warnings[], timings`.

## 1. Entity map (pre-hackathon)

```text
DataSource ──< RawSourceRecord >── (maps to) ──┐
                                                ▼
                  ┌──────────── Supplier ───────────────┐
                  │   (canonical; SupplierSourceRef[])  │
                  │                                     │
          ProductOffering ──< Evidence >──┐     ProcurementRecord
          (search unit)                   │     (history; valid-time)
                  │                       │
       OfferingEmbedding [ER]      Evidence (supplier-level)
                  │
     SupplierSearchDocument (projection; rebuildable, NOT truth)

PossibleMatch [ER] (supplier ↔ supplier, unresolved ER candidates)
SupplierRedirect [ER] (merged old_id → canonical_id)

SearchRun [ER] ──< SearchResult [ER] ──> Supplier      Feedback ──> SearchRun, Supplier
BenchmarkQuery ──< Qrel ──> Supplier                   BenchmarkManifest
```

Aggregate ownership: **Supplier** is the root for identity; **ProductOffering**, **Evidence**,
**ProcurementRecord** reference it by `supplier_id`. Projections and embeddings are derived.

## 2. Entities

### 2.1 Supplier (canonical company)

| Field | Type | Req | Rule / meaning |
|---|---|:-:|---|
| id | UUID | ✅ | Stable canonical ID (BR-30) |
| name | string 2–300 | ✅ | Original legal name, preserved |
| normalized_name | string | ✅ | BR-33 |
| aliases **[ER]** | string[] | | Other observed names after ER |
| inn | string | | 10/12 digits |
| ogrn | string | | 13/15 digits |
| kpp | string | | 9 digits (list if branches — EC-23 [ER]) |
| supplier_type | enum | ✅ | `manufacturer · distributor · supplier · service_provider · unknown` — **superseded by `entity_type` + `market_role` (§0.4–0.5, HD-09)** |
| supplier_type_basis **[ER]** | enum | | How type was determined: `registry · catalog · procurement · declared · inferred · unknown` |
| legal_status | enum | ✅ | `active · inactive · unknown` |
| region_code / region_name / city | string | | Location (soft signal) |
| website | URL | | http/https |
| okved_codes | string[] | | |
| is_known_supplier | bool | ✅ | Known vs external (BR-19, OQ-17) |
| first_seen_in_procurement_at **[ER]** | date | | Enables "new" semantics & temporal holdout (ED-04) |
| profile_completeness | float 0–1 | ✅ | Derived — formula undefined (G-21) |
| data_quality_flags **[ER]** | enum[] | | See §3.3 |
| source_ids | {source_name, external_id}[] | ✅ non-empty | Source references (P1-001) |
| created_at / updated_at | ISO-8601 | ✅ | System (ingestion) time — **not** real-world time |

### 2.2 ProductOffering (search unit for **external** suppliers; known suppliers use §0.2 — HD-03)

| Field | Type | Req | Rule |
|---|---|:-:|---|
| id | UUID | ✅ | |
| supplier_id | UUID FK | ✅ | Must reference existing Supplier |
| title | string 2–500 | ✅ | |
| normalized_title | string | ✅ | |
| description | string | ✅ | May be empty only if title descriptive (BR-39) |
| category_code / category_name | string? | | Source category |
| canonical_category **[source: P0 §27]** | string? | | Mapped category (P4-006) |
| attributes | JSON object | ✅ | Flexible per category; promote hot keys later |
| brand / model | string? | | |
| source_name / source_external_id | string | ✅ | Unique per source (C-03 naming) |
| source_url | URL? | | |
| source_observed_at | ISO-8601? | | Required for non-internal sources [ER] (C-16) |
| created_at / updated_at | ISO-8601 | ✅ | |

Embedding is **not** a canonical field — see OfferingEmbedding (C-14 / ED-06).

### 2.3 ProcurementRecord (history) — *superseded by §0.1–0.3 (HD-02)*

| Field | Req | Notes |
|---|:-:|---|
| id, procurement_external_id | ✅ | |
| supplier_id | ✅ | |
| title, description | ✅/– | Text used for historical similarity (Branch D) |
| category_code | | Classification used by organizer (ОКПД2/КТРУ? — OQ-29) |
| region, buyer **[P0 §18]** | | `buyer` listed in data strategy but missing from entity — G-22 |
| amount, currency | | Not used in ranking (BR-07) |
| role | ✅ | `winner · participant · supplier · unknown` |
| procurement_date | ✅ for temporal holdout | Valid-time anchor (BR-29) |
| source_id | ✅ | |

### 2.4 Evidence

| Field | Req | Notes |
|---|:-:|---|
| id | ✅ | |
| supplier_id | ✅ | |
| offering_id | | Nullable (supplier-level evidence) |
| evidence_type | ✅ | Enum — only `PRODUCT_CATALOG` defined in sources; proposed set §3.2 |
| claim | ✅ | Short factual statement, generated from structured data (not LLM-invented) |
| source_name, source_url, source_record_id | ✅ one of url/record_id | BR-35, EC-32 |
| observed_at | ✅ | NFR-TRC-01 |
| confidence | ✅ | 0–1 evidence-level confidence (method: G-21) |

### 2.5 DataSource

| Field | Notes |
|---|---|
| id | **Slug string** in P1-001 example (`"seed"`) vs UUID elsewhere — C-03 |
| name, source_type, base_url | `source_type`: `internal_seed · organizer_dataset · government_registry · manufacturer_registry · company_catalog · procurement_history · open_web` |
| trust_level | Values beyond `controlled` undefined — proposed: `controlled · official · verified · unverified` [ER] |
| last_sync_at, status | status values undefined — proposed: `active · degraded · disabled` [ER] |

### 2.6 RawSourceRecord (future ingestion; principle binding now)

`id, source_name, external_id, payload JSON, ingested_at, checksum` — never deleted (BR-31).

### 2.7 SupplierSearchDocument (projection)

`offering_id, supplier_id, search_text, search_vector (tsvector), embedding (see ED-06), category_code,
region_code, supplier_type, source_flags, updated_at` (+ **[ER]** `is_known_supplier`, `legal_status`,
`index_version`). Rebuildable at any time; never edited directly.

### 2.8 Search / evaluation entities

| Entity | Fields | Status |
|---|---|---|
| SearchRun **[ER] ED-02** | request_id, query, parsed_query, filters, versions (parser, ranking, index, embedding), timings, candidate counts, warnings, created_at | Proposed |
| SearchResult **[ER]** | request_id, rank, supplier_id, matched_offering_id, match_score, confidence_score, contributions JSON, reason_codes, risk_flags | Proposed |
| Feedback | request_id, supplier_id, relevance ∈ {relevant, not_relevant, unsure}, created_at | Source (P0 §60) |
| BenchmarkQuery | query_id, query_text, category, difficulty (easy/medium/hard), cutoff_date?, notes (+ `split` dev/holdout [ER]) | Source (P1-001 §26) |
| Qrel | query_id, supplier_id, relevance_grade 0/1/2, judgment_source (seed_design/human/historical), notes | Source (P1-001 §27) |
| BenchmarkManifest | name, version, created_at, counts, relevance_scale, notes (+ corpus/index version [ER]) | Source (P1-001 §30) |

### 2.9 Value objects

| Value object | Shape |
|---|---|
| **SearchIntent** (parsed query) | `product, category_terms[], attributes{}, region, supplier_types[], mandatory_constraints[]` (+ `quantity` per Strategy §11 — G-06; + `field_origin{extracted/user}` [ER]) |
| **MatchBreakdown** | per-feature `{raw_value 0–1, weight, applicable, contribution}` |
| **ConfidenceBreakdown** | 5 components 0–1 + total |
| **SourceRef** | `{source_name, external_id}` |

## 3. Enumerations (controlled vocabularies)

### 3.1 Reason codes
Initial: `LEXICAL_MATCH, EXACT_TITLE_MATCH, CATEGORY_MATCH, ATTRIBUTE_MATCH, REGION_MATCH, KNOWN_SUPPLIER, EXTERNAL_SUPPLIER`
Later: `SEMANTIC_MATCH, PROCUREMENT_EXPERIENCE, VERIFIED_MANUFACTURER, STRONG_PRODUCT_EVIDENCE, MULTI_SOURCE_VERIFICATION`
Seen in Phase 0 examples: `EXACT_CATEGORY` (→ same as `CATEGORY_MATCH`? C-17), `RELEVANT_PROCUREMENT_HISTORY` (→ `PROCUREMENT_EXPERIENCE`?).

### 3.2 Evidence types [ER — only PRODUCT_CATALOG is sourced]
`PRODUCT_CATALOG, MANUFACTURER_REGISTRY, LEGAL_REGISTRY, PROCUREMENT_HISTORY, COMPANY_WEBSITE, DELIVERY_REGION, CERTIFICATION, OPEN_WEB_MENTION`

### 3.3 Data-quality flags (record-level, internal)
`MISSING_INN, MISSING_CATEGORY, UNKNOWN_SUPPLIER_TYPE, STALE_DATA, CONFLICTING_REGION, UNVERIFIED_PRODUCT, DUPLICATE_CANDIDATE`

### 3.4 Risk flags (result-level, user-facing)
`LOW_EVIDENCE, STALE_INFORMATION, UNVERIFIED_MANUFACTURER, UNKNOWN_LEGAL_STATUS, AMBIGUOUS_ENTITY, NO_PROCUREMENT_HISTORY`
Overlap with 3.3 → C-09 (proposed: quality flags are inputs, risk flags are derived outputs).

### 3.5 Other
`supplier_type`, `legal_status`, `market_scope {all, known, external}`, `procurement role`,
`relevance grade {0,1,2}`, `feedback relevance`, `difficulty {easy, medium, hard}`, `source_type`.

## 4. Invariants (enforced by validators and DB constraints)

**Supplier:** unique id · INN unique when present (unless flagged source duplicate) · source ids unique within source · `profile_completeness ∈ [0,1]` · `source_ids` non-empty.
**Offering:** unique id · FK to supplier · non-empty title · `source_external_id` unique per source.
**Benchmark:** qrels reference existing queries & suppliers · grades ∈ {0,1,2} · every query has ≥1 grade-2 · preferably ≥1 grade-0 · unique query ids.
**Search response:** result supplier/offering IDs valid · score ∈ [0,1] · reason codes non-empty · sorted desc · one result per supplier.
**Temporal [ER]:** any fact used under `as_of=T` must have valid-time ≤ T.

## 5. Identifier strategy

- Canonical: UUID; seed: UUIDv5(namespace, stable source key).
- External IDs kept in `source_ids` / `SupplierSourceRef`; never replace canonical IDs.
- Entity-resolution merges keep the surviving canonical ID and record `SupplierRedirect` [ER] — protects qrels and search-run references (EC-22).
- `request_id`: UUID per search request.
