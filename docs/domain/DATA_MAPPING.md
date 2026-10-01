# Data Mapping — Organizer CSVs → Canonical Contracts v0.2.0

> **Task:** P1-001B (roadmap v2) · **Date:** 2026-10-01 · **Contracts:** [`/contracts/*.schema.json`](../../contracts/) (JSON Schema 2020-12, version 0.2.0)
> **Machine-readable coverage:** [`contracts/source_mapping.json`](../../contracts/source_mapping.json) · **Validator:** `python scripts/validate_contracts.py [--raw data/raw]`
> **Evidence:** P1-001A [`reports/dataset_profile.json`](../../reports/dataset_profile.json) and [dataset analysis](../analysis/REAL_DATASET_ANALYSIS_2024_2025.md).
> **Decisions:** ADR-H1 HD-02/03/05/09 + amendments A1/A2/A3. Normalization *implementation* is P1-001C; ingestion is P1-001D. This document defines the contract.

---

## 1. Principles

1. **Raw is never lost.** Every CSV row goes to the raw store (P1-001D) with `(dataset, row_number, payload, checksum)` (BR-31). Canonical records point back via `source_ref` / `source_refs`.
2. **Structure vs quality.** A row is **structurally invalid** only when it cannot be represented canonically (wrong field count, unknown platform literal, non-boolean `is_smp`/`is_winner`, non-decimal `start_price`, empty `lot_id`/`supplier_inn`, supplier row whose lot is unknown) → quarantined with a reason, never silently dropped. Everything else that is merely *bad data* (missing/malformed INN, KPP, OKPD2, empty names, zero price, duplicates) is kept and **flagged** (§5). Schemas enforce that flags match values (e.g. a non-well-formed INN without `INVALID_INN_FORMAT` is rejected).
3. **Identifiers are strings.** `lot_id`, `procedure_id`, INN, KPP are never cast to numbers (leading zeros, 12-digit INNs).
4. **No invented fields.** The source has no product description, supplier name, region, OGRN, contract outcome or item price; those appear only via enrichment (SupplierProfile/Evidence) or not at all.
5. **Organizer semantics are not over-claimed.** Observations are encoded as observations (`coverage_semantics`, A1/A3); interpretations stay in docs with the open question.

## 2. Column mapping (all 18 source columns)

Source type of every CSV value is a UTF-8 string (`;`-separated, `"`-quoted, no BOM). "Req" = required in the canonical record (may still be `null` where stated).

### 2.1 `Извещения_24-25.csv` (dataset `notices_24_25`) → **ProcurementLot** (+ denormalized into SupplierHistory)

| Column | Canonical entity.field | Canonical type | Req | Transformation | Validation rule | Null behavior | Quality flags | Notes / business semantics |
|---|---|---|:-:|---|---|---|---|---|
| `publish_date` | ProcurementLot.publish_date; SupplierHistory.publish_date (denorm.); Supplier.first_seen_publish_date (aggregate) | date `YYYY-MM-DD` | ✅ | trim | ISO date | not nullable (structural if absent) | — | **Valid-time anchor** for `as_of`; history visible iff strictly earlier |
| `procedure_id` | ProcurementLot.procedure_id | string | ✅ | trim | `^\S{1,32}$` | not nullable | — | Attribute only; 1:1 with `lot_id` in this extract (P1-001A) — never a join key |
| `lot_id` | ProcurementLot.lot_id, ProcurementLot.id | string; uuid | ✅ | trim; `id = UUIDv5('lot:'+lot_id)` | `^\S{1,32}$`; unique | not nullable | — | **Canonical procurement key** (HD-02); joins items and supplier history |
| `start_price` | ProcurementLot.start_price | decimal **string** | ✅ (nullable) | trim; kept as delivered (e.g. `71985.00`) | `^[0-9]{1,15}(\.[0-9]{1,4})?$` else structural | `''` → `null` | `MISSING_START_PRICE` (3 lots), `ZERO_START_PRICE` (21) | RUB, lot level. Decimal semantics — never float business logic. Zero preserved; consumers treat zero/null as unknown. Context feature only (D-13) |
| `reqnum` | ProcurementLot.reqnum | string \| null | ✅ (nullable) | trim | — | `''` → `null` (61.7% of lots) | — | Opaque; meaning unknown (OQ-36). Not used in search/ranking |
| `procedure_name` | ProcurementLot.procedure_name_variant | string \| null | ✅ (nullable) | trim; set **only if** `cmp_norm(procedure_name) ≠ cmp_norm(subject)` | — | equal/empty → `null` | — | 97.9% identical, 99.1% identical after comparison normalization → kept only as a variant (~0.9% of lots), **not indexed by default** (no double counting, BR-44). Full raw value stays in the raw store |
| `subject` | ProcurementLot.subject | string \| null | ✅ (nullable) | trim | minLength 1 | `''` → `null` | `MISSING_SUBJECT` (1 lot) | **Chosen canonical lot title** (low-weight context; item text is primary) |
| `is_smp` | ProcurementLot.is_smp | boolean | ✅ | `'true'`→true, `'false'`→false | other literal = structural | not nullable | — | **Platform-dependent:** true only on AIS_GZ (45.1% of AIS_GZ lots); always false on EM — on EM `false` must not be read as "not SME-restricted" (OQ-35). Not a ranking feature |
| `customer_inn` | ProcurementLot.customer_inn | string \| null | ✅ (nullable) | trim; non-empty values kept as-is | well-formed = 10/12 digits; checksum | **only** `''` → `null` | `MISSING_INN` (8,449, all empty), `INVALID_INN_FORMAT` (0), `INVALID_INN_CHECKSUM` (0) | Buyer identity; 2,785 distinct customers (§9) |
| `customer_kpp` | ProcurementLot.customer_kpp | string \| null | ✅ (nullable) | trim | well-formed = `^[0-9]{4}[0-9A-Z]{2}[0-9]{3}$` | `''` → `null` | `MISSING_KPP` (8,449), `INVALID_KPP_FORMAT` (0 observed) | Never identity |
| `is_eshop_or_aisgz` | ProcurementLot.platform; SupplierHistory.platform (denorm.); SupplierHistory.coverage_semantics (derived) | enum `AIS_GZ · EM` | ✅ | `'АИС ГЗ'`→`AIS_GZ`, `'ЭМ'`→`EM` | other literal = structural | not nullable | — | ЭМ = SPb electronic store (OQ-34 to confirm wording) |

### 2.2 `Поставщики_24-25.csv` (dataset `suppliers_24_25`) → **SupplierHistory** + **Supplier**

| Column | Canonical entity.field | Canonical type | Req | Transformation | Validation rule | Null behavior | Quality flags | Notes / business semantics |
|---|---|---|:-:|---|---|---|---|---|
| `lot_id` | SupplierHistory.lot_id, SupplierHistory.id | string; uuid | ✅ | trim; `id = UUIDv5('history:'+lot_id+':'+inn)` | must exist in notices (0 orphans in P1-001A) else structural | not nullable | — | Relation key part 1 |
| `supplier_inn` | SupplierHistory.supplier_inn, .supplier_id; Supplier.inn, .supplier_id, .entity_type, .inn_region_code | string; uuid | ✅ | **trim only** (no other change — it feeds identity); `supplier_id = UUIDv5('supplier:inn:'+inn)` | well-formed = 10/12 digits; checksum (FNS control digits) | empty = structural | `INVALID_INN_FORMAT` (8 distinct INNs), `INVALID_INN_CHECKSUM` (14 distinct) | **Supplier identity = INN string** (BR-30: INN is not the PK; the UUID derived from it is). Malformed INNs remain distinct suppliers with `entity_type = unknown` |
| `supplier_kpp` | SupplierHistory.supplier_kpp | string \| null | ✅ (nullable) | trim; among duplicates take first non-empty | well-formed 9-char | `''` → `null` | `MISSING_KPP` (191,361 rows, 18.9%), `INVALID_KPP_FORMAT` (0 observed) | Not identity; not on Supplier (a supplier can have several KPPs) |
| `is_winner` | SupplierHistory.is_winner | boolean | ✅ | `'true'`/`'false'`; logical **OR** over duplicate rows | other literal = structural | not nullable | — | Counted per platform only; **no win rate** (HD-05, BR-45) |

### 2.3 `ТРУ_24-25.csv` (dataset `items_24_25`) → **ProcurementItem**

| Column | Canonical entity.field | Canonical type | Req | Transformation | Validation rule | Null behavior | Quality flags | Notes / business semantics |
|---|---|---|:-:|---|---|---|---|---|
| `lot_id` | ProcurementItem.lot_id, .line_no, .id | string; int; uuid | ✅ | trim; `line_no` = ordinal in file order within the lot; `id = UUIDv5('item:'+lot_id+':'+line_no)` | must exist in notices (0 orphans) else structural | not nullable | — | §3.2 identity strategy |
| `product_name` | ProcurementItem.product_name_raw, .product_name_normalized, .content_hash | string; string \| null; hex | ✅ | raw kept **byte-exact**; normalized by P1-001C | — | empty raw kept as `''`; normalized → `null` | `MISSING_PRODUCT_NAME` (114 rows) | **Primary search text** (HD-03). There is **no description field** in the source |
| `okpd2_code` | ProcurementItem.okpd2_code_raw, .okpd2_code, .okpd2_depth, .okpd2_section/class/subclass/group/subgroup/kind | string; string \| null; … | ✅ | raw kept; trim; validate; derive hierarchy (§4) | `^[0-9]{2}(\.([0-9]|[0-9]{2}(\.([0-9]|[0-9]{2}(\.[0-9]{1,3})?))?))?$` and class must belong to an ОКПД2 section | empty/invalid → normalized fields `null` | `MISSING_OKPD2` (238 rows), `INVALID_OKPD2` (1 malformed observed + any class outside sections) | Strong signal, never the sole criterion (HD-04). Mixed depth: 94.8% of rows are 4-segment |

**NOT_MAPPED columns:** none — all 18 columns are mapped (enforced by the validator against the P1-001A column lists).

**Not present in the source (must not be invented):** product description, quantity/unit, item price, КТРУ code, OKPD2 titles, supplier name/OGRN/address/region, contract result/date/price, participant bid prices.

## 3. Identity strategy

All canonical ids are UUIDv5 under the project namespace **`9a58f195-b16e-554c-b016-5a636976af05`** (= `UUIDv5(NAMESPACE_URL, "urn:supplier-radar:canonical")`). Same input → same id on every re-ingestion (BR-30, P1D-003 principle).

| Entity | Natural key | id name template |
|---|---|---|
| ProcurementLot | `lot_id` | `lot:{lot_id}` |
| ProcurementItem | (`lot_id`, `line_no`) | `item:{lot_id}:{line_no}` |
| SupplierHistory | (`lot_id`, `supplier_inn`) | `history:{lot_id}:{supplier_inn}` |
| Supplier | `inn` (trimmed string) | `supplier:inn:{inn}` |
| SupplierEvidence | (supplier, type, url or record ref) | `evidence:{supplier_id}:{evidence_type}:{source_url or source_record_ref}` |
| SupplierProfile | `supplier_id` (1:0..1) | — |

### 3.1 Supplier identity
- Identity = INN string after outer-whitespace trim; **KPP never participates** (one INN can appear with several KPPs).
- INN is not the primary key (BR-30); `supplier_id` is derived from it, so the mapping INN → id is stable and reversible only via the record.
- Malformed INNs (8 distinct) are separate suppliers with `entity_type = unknown`, `inn_region_code = null`, `INVALID_INN_FORMAT`. Checksum failures (14 distinct) keep their entity type and get `INVALID_INN_CHECKSUM`.
- No fuzzy merging (BR-32): INN-exact only; organizer data has an INN on every row.

### 3.2 ProcurementItem identity (no source item id)
- **Strategy:** `line_no` = 1-based ordinal of the row among rows of the same `lot_id`, counted in source-file order; `id = UUIDv5('item:{lot_id}:{line_no}')`; plus `source_ref.row_number` (provenance) and `content_hash = sha256(lot_id ␟ product_name_raw ␟ okpd2_code_raw)`.
- **Why not content-based ids:** identical lines can repeat inside a lot (e.g. the same item listed twice), so content alone is not unique.
- **Why not file row number as id:** it changes if any earlier row of any lot changes; the per-lot ordinal only changes if *that lot's* rows are reordered.
- **Trade-off / guard:** ids are stable for re-ingesting the same file and for appended lots; if the organizer re-delivers a lot with reordered lines, `line_no` shifts. Ingestion (P1-001D) compares `content_hash` per `(lot_id, line_no)` and reports drift instead of silently re-keying.
- **Immutability pin:** the raw files are hash-pinned (SHA-256 in `reports/dataset_profile.json`, re-verified after the files were restored). P1-001D must check the input hashes before ingesting; equal hashes ⇒ identical row order ⇒ identical `line_no` and item ids on every re-ingestion (confirmed by two independent passes, §9 item 7). A different hash is a new delivery and triggers the drift report.

### 3.3 SupplierHistory deduplication
- Canonical key `(lot_id, supplier_inn)`; 31 duplicate source pairs exist (P1-001A).
- Merge rule: `is_winner` = OR of the duplicates; `supplier_kpp` = first non-empty in file order; `source_refs` = **all** contributing rows (file order); flag `DUPLICATE_SUPPLIER_RELATION`. Raw duplicates stay in the raw store.
- Whether duplicates ever disagree on `is_winner`/KPP was not measured (raw files unavailable at P1-001B time, §9); P1-001D must report the disagreement count.

## 4. Derived Fields

| Derived field | Source inputs | Transformation | Deterministic | Lossless? | Confidence / limitation |
|---|---|---|:-:|---|---|
| `ProcurementLot.id`, `ProcurementItem.id`, `SupplierHistory.id`, `Supplier.supplier_id` | keys in §3 | UUIDv5 under project namespace | ✅ | n/a (identifier) | Item id depends on per-lot row order (§3.2) |
| `platform` | `is_eshop_or_aisgz` | `АИС ГЗ`→`AIS_GZ`, `ЭМ`→`EM` | ✅ | lossless (bijective on observed values) | Unknown literal = structural |
| `coverage_semantics` | lot `platform` | `AIS_GZ`→`WINNER_ROWS_ONLY_OBSERVED`; `EM`→`MIXED_WINNER_NONWINNER_ROWS_OBSERVED` | ✅ | n/a | **Observation, not organizer semantics.** Confirmed: all delivered АИС ГЗ rows have `is_winner=true`. "Award-only coverage" is a working interpretation pending **OQ-33** (A1, A3). For EM only the presence of both winner and non-winner rows is observed — **completeness of the participant list is not claimed** until officially confirmed (A4; A-114) |
| `procedure_name_variant` | `procedure_name`, `subject` | keep `procedure_name` iff comparison-normalized texts differ | ✅ | lossy in canonical (identical copies dropped); raw keeps everything | `cmp_norm` = lower, ё→е, non-word→space, collapse spaces (comparison only) |
| `entity_type` | `supplier_inn` | 10 digits → `legal_entity`; 12 digits → `individual_entrepreneur`; else `unknown` | ✅ | lossy | 12-digit INN = natural person (IE, or other individual such as self-employed); the enum value `individual_entrepreneur` is the agreed label (HD-09). **Never** a market role |
| `inn_region_code` | `supplier_inn` | first 2 digits if well-formed | ✅ | lossy | **Tax-registration region evidence** (A-115) — not delivery capability or production location; null for malformed INNs |
| `Supplier.first_seen_publish_date` | SupplierHistory `publish_date` | min over all the supplier's relations (any platform, winner or not) | ✅ | lossy | Basis for temporal knownness (§7) |
| `Supplier.origin` | presence in Поставщики / curated file | `ORGANIZER_DATA` or `EXTERNAL_ENRICHMENT` | ✅ | — | An enriched INN that also occurs in organizer data is `ORGANIZER_DATA` |
| `ProcurementLot.has_supplier_history` (optional) | Поставщики | lot has ≥ 1 relation | ✅ | — | Dataset-coverage attribute (54,279 AIS_GZ lots false); not temporal, not a ranking feature |
| `okpd2_code` | `okpd2_code` | trim + format + section check; else null | ✅ | lossless for valid codes (raw kept) | §4.1 |
| `okpd2_depth` | `okpd2_code` | number of dot segments (1–4) | ✅ | — | — |
| `okpd2_section` | `okpd2_class` | section letter by class range (§4.1) | ✅ | — | Class outside all sections → code treated as invalid |
| `okpd2_class/subclass/group/subgroup/kind` | `okpd2_code` | prefixes (§4.1); null when the code is shallower | ✅ | — | 4-segment detail beyond *kind* stays only in `okpd2_code` |
| `product_name_normalized` | `product_name` | `normalize_text` (§10, `NORMALIZATION_VERSION`) | ✅ (versioned) | lossy (raw kept) | Null for empty names and for punctuation-only placeholders (3 rows) |
| `is_generic_type_name` (optional) | `product_name` | `has_generic_type_marker` of `normalize_product_name` (`тип N` present, §10) | ✅ | — | Heuristic; low-information names |
| `content_hash` | `lot_id`, `product_name`, `okpd2_code` (raw) | sha256 with U+001F separators | ✅ | — | Drift detection only, not identity |

### 4.1 OKPD2 hierarchy (ОК 034-2014 / КПЕС 2008)

| Field | Shape | Name (RU) | Derivation from `okpd2_code` |
|---|---|---|---|
| `okpd2_section` | `A`…`U` | Раздел | from class: A 01–03 · B 05–09 · C 10–33 · D 35 · E 36–39 · F 41–43 · G 45–47 · H 49–53 · I 55–56 · J 58–63 · K 64–66 · L 68 · M 69–75 · N 77–82 · O 84 · P 85 · Q 86–88 · R 90–93 · S 94–96 · T 97–98 · U 99 |
| `okpd2_class` | `XX` | Класс | segment 1 |
| `okpd2_subclass` | `XX.X` | Подкласс | segment 1 + first digit of segment 2 (needs depth ≥ 2) |
| `okpd2_group` | `XX.XX` | Группа | segments 1–2 when segment 2 has 2 digits |
| `okpd2_subgroup` | `XX.XX.X` | Подгруппа | group + first digit of segment 3 (depth ≥ 3) |
| `okpd2_kind` | `XX.XX.XX` | Вид | group + segment 3 when it has 2 digits |
| `okpd2_code` | up to `XX.XX.XX.XXX` | full code (категория/подкатегория level when 4 segments) | — |

Examples: `26.20.11.110` → C · 26 · 26.2 · 26.20 · 26.20.1 · 26.20.11 · `33.12.1` → C · 33 · 33.1 · 33.12 · 33.12.1 · kind null · `21.20` → C · 21 · 21.2 · 21.20 · `33` → C · 33 only.
**Terminology note:** P1-001A's replay keys `…_same_class_xx_xx` and the dataset analysis's phrase "OKPD2 class (`XX.XX`)" refer to the ОКПД2 **group** (`XX.XX`) in this terminology; numbers are unchanged.

## 5. Data-quality flags (controlled vocabulary v0.2.0)

| Flag | Level | Applies to (field) | Meaning | Observed (P1-001A) |
|---|---|---|---|---|
| `MISSING_INN` | record | ProcurementLot (`customer_inn`) | empty customer INN (only when the source value is empty) | 8,449 lots (verified: all empty) |
| `INVALID_INN_FORMAT` | record + **entity** | ProcurementLot (`customer_inn`), SupplierHistory, Supplier | non-empty, not 10/12 digits (incl. letters); raw string preserved | 8 distinct supplier INNs (12 rows) · 0 customer INNs |
| `INVALID_INN_CHECKSUM` | record + **entity** | same | well-formed but FNS control digits fail | 14 distinct supplier INNs (119 relation rows) · 0 customer INNs |
| `MISSING_KPP` | record | ProcurementLot (`customer_kpp`), SupplierHistory (`supplier_kpp`) | empty KPP | 8,449 lots · 191,361 supplier rows |
| `INVALID_KPP_FORMAT` | record | same | non-empty, not 9-char KPP format | 0 (rule needed so a future value is kept, not rejected) |
| `MISSING_START_PRICE` | record | ProcurementLot | empty price | 3 |
| `ZERO_START_PRICE` | record | ProcurementLot | price = 0 | 21 |
| `MISSING_SUBJECT` | record | ProcurementLot | empty subject | 1 |
| `MISSING_PRODUCT_NAME` | record | ProcurementItem | empty/whitespace name | 114 |
| `MISSING_OKPD2` | record | ProcurementItem | empty code | 238 |
| `INVALID_OKPD2` | record | ProcurementItem | bad format or class outside sections | 1 (`25.71.11.1200`); 0 out-of-section |
| `DUPLICATE_SUPPLIER_RELATION` | record | SupplierHistory | ≥ 2 raw rows for (lot, INN) | 31 pairs |

Each entity schema restricts the flags it may carry (e.g. a lot cannot carry `MISSING_OKPD2`). Flags are emitted in this table's order (deterministic).

## 6. Enrichment entities (P3; not populated from the CSVs)

- **SupplierProfile** — `display_name, ogrn, legal_status, region, city, website, okved_primary` (each evidence-backed), `market_role` (`manufacturer · distributor · dealer · supplier · reseller · other_intermediary · unknown`), `role_basis`, `role_verification` (`VERIFIED · INFERRED · UNVERIFIED`), `role_confidence`, `role_evidence_ids`, `observed_at`.
  Rules enforced by the schema: non-`unknown` role ⇒ basis + ≥ 1 evidence · `unknown` ⇒ `UNVERIFIED` · basis `okved` / `procurement_pattern` / `declared` ⇒ not `VERIFIED` and confidence ≤ 0.4 · **manufacturer `VERIFIED` ⇒ basis `official_registry` or `first_party_production`** (OKVED alone → `INFERRED`, displayed as `INFERRED_MANUFACTURER_CANDIDATE`; A2).
- **SupplierEvidence** — `claim, evidence_type (PROCUREMENT_HISTORY · OFFICIAL_REGISTRY · LEGAL_REGISTRY · FIRST_PARTY_PRODUCTION · COMPANY_WEBSITE · DEALER_CERTIFICATE · PRODUCT_CATALOG), supports (MARKET_ROLE · PRODUCT_RELEVANCE · LEGAL_IDENTITY), source_name, source_url | source_record_ref, observed_at, verification_status, confidence, related_okpd2_codes?`. At least one of URL/record ref is required; `PROCUREMENT_HISTORY` evidence must reference `lot:{lot_id}`.
- `entity_type` (Supplier) and `market_role` (SupplierProfile) live in different entities and are never derived from each other (BR-48).

## 7. Temporal semantics (as_of)

- Valid time of every organizer fact = lot `publish_date` (denormalized onto SupplierHistory).
- For a replay target with date `T`: visible history = relations with `publish_date < T` (**strict**; same-day lots are invisible).
- **Known supplier at T** := `Supplier.first_seen_publish_date < T`. No global `is_known_supplier` is stored (the Supplier schema rejects it) — storing it would leak present-day knowledge into the benchmark.
- Supplier-level counts (`historical_award_count`, ЭМ-only `marketplace_participation_count` / `marketplace_win_count`, `last_award_at`) are **computed with `as_of`**, never stored as global truths. No cross-platform win rate (HD-05).
- External candidates (`EXTERNAL_ENRICHMENT`) are never "known"; their evidence carries its own `observed_at`.

## 8. Validation & fixtures

- `scripts/validate_contracts.py` (stdlib only — no JSON Schema library is installed; it implements exactly the keyword subset used and **rejects any other keyword**) checks: schema well-formedness; full column coverage vs `reports/dataset_profile.json`; reference-mapping of representative rows; enrichment fixtures; 29 negative cases; determinism; optional `--raw <dir>` real-row check.
- Fixtures (`contracts/fixtures/`) preserve **structure, not identity**: lot ids, dates, prices, subjects and item texts of real public lots (5718896, 5545252, 4900162, 2077538) are real; **all INNs/KPPs are synthetic masks** (format-preserving, checksum-valid where the case needs it); edge-case lots 9900001/9900002 are synthetic and cover every quality flag.
- The reference mapping inside the validator is a specification aid; P1-001C/D own production code and must reproduce its outputs.

## 9. Verification against the restored raw files (closed 2026-10-01)

The raw CSVs were temporarily missing during the first P1-001B pass; after restoration their SHA-256 hashes were confirmed identical to P1-001A and every open item was measured (full scan):

| # | Item | Result |
|---|---|---|
| 1 | Customer INN (8,449 non-well-formed) | **all 8,449 are empty** (4,648 АИС ГЗ, 3,801 ЭМ; customer KPP also empty in all of them) · non-empty malformed **0** · 10-digit checksum failures **0** · other **0** · 596,003 valid 10-digit. → `null` + `MISSING_INN` applies only to these empty values; a non-empty malformed value would be kept as-is with `INVALID_INN_FORMAT`. Distinct customers = **2,785** (+ the empty value; the earlier "2,786" counted the empty string) |
| 2 | 31 duplicate (lot, INN) relations | all exactly 2 copies; **0** `is_winner` conflicts; **0** conflicting non-empty KPPs → merge rule is lossless |
| 3 | Malformed supplier INN shapes (rows) | 2 letters + 8 digits (5 rows) · 9 digits (4) · 2 letters + 7 digits (1) · 13 digits (1) · 15 digits (1) — no inner spaces. **32 rows have outer whitespace** around the INN; the trim-only identity rule handles them |
| 4 | `start_price` literals | `digits.digits` in 604,449 rows, empty in 3 — decimal-string pattern holds |
| 5 | OKPD2 | 1 malformed code (`25.71.11.1200`, 4-digit last segment) · 0 codes with a class outside every section |
| 6 | `lot_id` / `procedure_id` | all digits, no whitespace |
| 8 | **Full-dataset contract validation** (reference mapping, every row, 1,536 s) | 0 structural errors · **0 invalid records**: 604,452 lots · 2,971,651 items · 1,010,107 supplier relations (1,010,138 rows − 31 duplicates) · 44,196 suppliers. Flags: lots `MISSING_INN` 8,449 · `MISSING_KPP` 8,449 · `ZERO_START_PRICE` 21 · `MISSING_START_PRICE` 3 · `MISSING_SUBJECT` 1; items `MISSING_OKPD2` 238 · `MISSING_PRODUCT_NAME` 114 · `INVALID_OKPD2` 1; relations `MISSING_KPP` 191,359 · `INVALID_INN_CHECKSUM` 119 · `INVALID_INN_FORMAT` 12 · `DUPLICATE_SUPPLIER_RELATION` 31; suppliers `INVALID_INN_CHECKSUM` 14 · `INVALID_INN_FORMAT` 8 |
| 7 | `line_no` stability | recomputed in two independent passes over the unchanged file: identical (2,980 sampled rows); the file is immutable (hash-pinned), so ids are stable across re-ingestion |

## 10. Normalization implementation (P1-001C)

Single implementation: [`backend/app/shared/normalize.py`](../../backend/app/shared/normalize.py) (`NORMALIZATION_VERSION = 1.0.0`, stdlib only, pure functions,
regexes compiled once). Tests: `backend/tests/shared/test_normalize.py` (`python -m pytest backend/tests`). Real-data check:
`python scripts/verify_normalization.py` → `reports/normalization_verification.json`. Every result carries the raw value next to the canonical one.

| Function | Feeds | Behaviour |
|---|---|---|
| `normalize_product_name(raw)` → `TextNorm(raw, normalized, type_marker, has_generic_type_marker, flags)` | item `product_name_raw/_normalized`, `is_generic_type_name` | `MISSING_PRODUCT_NAME` only when the source is empty/whitespace |
| `normalize_text(raw)` | search text (items, later subject) | rules below; idempotent |
| `normalize_subject(raw)` / `procedure_name_variant(pn, subject)` / `comparison_key(text)` | lot `subject`, `procedure_name_variant` | `comparison_key` = the §4 `cmp_norm` exactly (5,533 variant lots) |
| `normalize_inn(raw)` → `InnNorm(raw, inn, entity_type, inn_region_code, flags)` | customer/supplier INN, Supplier | empty → `None` + `MISSING_INN` (customer); a supplier row with an empty INN stays structural (0 observed); malformed non-empty kept + `INVALID_INN_FORMAT`; checksum failure keeps value and entity type + `INVALID_INN_CHECKSUM` |
| `normalize_kpp(raw)` → `KppNorm(raw, kpp, flags)` | customer/supplier KPP | contract format `^[0-9]{4}[0-9A-Z]{2}[0-9]{3}$`; malformed kept + flag |
| `normalize_okpd2(raw)` → `Okpd2Norm(okpd2_code_raw, okpd2_code, okpd2_depth, okpd2_section, okpd2_class, okpd2_subclass, okpd2_group, okpd2_subgroup, okpd2_kind, flags)` | item OKPD2 fields (names = contract fields) | §4.1; static versioned section map `OKPD2_SECTIONS_VERSION`; malformed never "fixed" (`25.71.11.1200` → `INVALID_OKPD2`) |
| `normalize_price(raw)` → `PriceNorm(raw, value: Decimal, flags)`; `price_to_contract(Decimal)` | lot `start_price` | Decimal with source scale; zero ≠ missing; non-decimal/negative → `NormalizationError` |
| `normalize_date(raw)` → `datetime.date` | `publish_date` | strict `YYYY-MM-DD`, no timezone; else `NormalizationError` |
| `parse_bool(raw)` | `is_smp`, `is_winner` | exactly `true`/`false` (outer whitespace ignored); never Python truthiness |
| `normalize_platform(raw)`, `coverage_semantics(platform)` | `platform`, `coverage_semantics` | `АИС ГЗ`→`AIS_GZ`, `ЭМ`→`EM`; coverage per A3/A4 |
| `sort_flags(flags)` | all | contract order, deduplicated |

**Text rules (search representation; raw always kept):** NFC (composes decomposed `й`) → delete soft hyphen / zero-width / bidi marks; control and private-use
characters → space → `ё→е` → typographic quotes `«»„“”‟` → space; `″ ʺ ＂` → `"`; quote/dash variants unified (`– — − ‑ ‐` → `-`); `×` → `x` → lowercase →
`м²/м³` (also `дм³`, `см²`) → `м2/м3`; other superscripts (footnote `¹`, `⁰` …) → space → remove other punctuation (`( ) № : ; ! ? ° º ± ' …`) →
keep `.`/`,` only between digits (`15.6`, `82,5` — **decimal commas are not converted**: lists like `№25,27` exist) → straight `"` kept only as an inch mark
after a digit when no quotation is open (`15.6"`, `3/4" и 1/2"`; `"СБиС 2"` → quotes removed) → `%` kept after a digit → `-`, `/`, `+` kept inside tokens
(`a515-57-50r7`, `б/к`, `16гб/512гб`, `дротаверин+кофеин`) → collapse spaces → **dimension join last, symmetric only**: `60x9`, `60*20*7`, `90 х 50`, `1/2 x 3/4`
→ `…x…` (Cyrillic/Latin x unified), but a model suffix such as `cf280x 6,8k` / `tl-5120х 15000` is never joined.
Not done (by design): stemming, stop-word removal, transliteration/homoglyph folding (`ѕ`, `і`, Latin look-alikes stay as written — BR-33), unit
conversion, attribute extraction (`numeric_tokens()` only lists digit-bearing tokens). `тип N` is **kept in the text** and exposed as `type_marker` /
`has_generic_type_marker` (305,284 item rows, mostly `тип 1`–`тип 5`) for retrieval weighting.

**Real-data verification (2026-10-01, all rows / all distinct values):** 27/27 fact checks equal to P1-001A/B (platform split, `is_smp`, 3 missing / 21 zero
prices, 1 missing subject, 8,449 empty customer INN/KPP, 44,196 distinct supplier INNs = 20,591 legal / 23,597 individual / 8 malformed, 14 distinct (119 rows)
checksum failures, 191,361 empty supplier KPP rows, 0 malformed KPP, 238 missing + 1 invalid OKPD2, 8,452 distinct valid OKPD2 (depth 1/2/3/4 = 9/261/1,475/6,707),
114 empty product names); **0 differences** from the P1-001B reference mapping for every distinct INN, KPP and OKPD2; 1,109,612 distinct product names:
0 non-idempotent, 0 digit-count losses; 3 placeholder names (`----`) normalize to null without a flag (flag stays "empty source value"); date literals all
`YYYY-MM-DD`; booleans only `true`/`false`; platforms only `АИС ГЗ`/`ЭМ`. Throughput (in-memory, laptop): ≈ 23k product names/s (≈ 2 min for 2.97M),
≈ 190k INN/s, ≈ 300k+ OKPD2/s.

## 11. PostgreSQL ingestion (P1-001D)

**Stack:** `docker-compose.yml` — `postgres` (PostgreSQL 16, UTF-8 / C.UTF-8, `pg_trgm`, named volume `postgres_data`, `pg_isready` healthcheck) and
`backend` (Python 3.11: Alembic, psycopg 3, pytest; `data/raw` mounted **read-only** at `/data/raw`). Commands: root [`README.md`](../../README.md).
**Schema:** Alembic `0001_organizer_schema` (`backend/migrations/`). Index DDL is defined once in `backend/app/db/schema.py`.

| Table | Key | Content |
|---|---|---|
| `source_file` | `sha256` | dataset, file name, size, header, data rows |
| `ingestion_delivery` | `delivery_id` = UUIDv5(three SHA-256 + normalization version) | completed load manifest |
| `raw_notice` / `raw_supplier_relation` / `raw_procurement_item` | (`source_sha256`, `source_row_no`) | every CSV row, typed text columns exactly as parsed (immutable) |
| `ingestion_quarantine` | (`source_sha256`, `source_row_no`) | structurally invalid rows + reason (0 in this delivery) |
| `procurement_lot` | `lot_id` (+ unique `id`) | contract fields; `start_price numeric` (Decimal) |
| `supplier` | `supplier_id` (+ unique `inn`) | contract fields |
| `supplier_history` | `id` (+ unique (`lot_id`, `supplier_inn`)) | contract fields; provenance `source_sha256` + `source_row_nos int[]` |
| `procurement_item` | `item_id` (= contract `id`) (+ unique (`lot_id`, `line_no`)) | contract fields; OKPD2 columns use the contract names (`okpd2_code`, not `okpd2_code_normalized`) |
| `supplier_profile`, `supplier_evidence` | contract keys | empty until P3; contract role rules as CHECK constraints |

Contract rules are also enforced by CHECK constraints (flag vocabulary per table, platform↔coverage, duplicate flag↔multiple source rows,
entity type↔INN shape, MISSING_INN↔NULL customer INN, MISSING_START_PRICE↔NULL price, origin↔first_seen) and FKs (item→lot, history→lot, history→supplier).

**Pipeline (`python -m app.cli ingest organizer /data/raw`):** verify files, SHA-256 against `reports/dataset_profile.json` (mismatch ⇒ stop +
`reports/source_drift_report.json`) and headers → check schema revision → delivery manifest → **one transaction**: suppliers (raw COPY;
group by (lot, INN) in memory) → notices (raw COPY, then `procurement_lot`) → `supplier` → `supplier_history` (dedup §3.3) → items (raw COPY, then
`procurement_item`, streamed; per-lot `line_no` counter) → quarantine → secondary indexes rebuilt (fresh load) → manifest → commit → ANALYZE →
reconciliation (35 checks against P1-001A/B/C facts) + md5 content fingerprints → `reports/ingestion_report.{json,md}` (+ volatile `.meta.json`).
Each file is parsed twice (raw pass, canonical pass) because a connection runs one COPY at a time; lots, items and supplier relations are
canonicalized independently (never a three-way raw join). All values come from `normalize.py` via `app/ingestion/mapping.py`.

**Idempotency:** deterministic primary keys everywhere + the delivery manifest. Same files again ⇒ verify-only (hashes + reconciliation, no
writes); `--force` ⇒ re-process into temp tables + `INSERT … ON CONFLICT DO NOTHING` (0 rows inserted, identical fingerprints — integration
test); a different delivery or normalization version ⇒ refused unless `--reset-organizer-data` (deletes organizer rows only; enrichment kept).

**Search preparation (no retrieval implemented):** btree `okpd2_code text_pattern_ops` (prefix), `okpd2_kind/group/class`; GIN `pg_trgm` on
`product_name_normalized`; GIN FTS expression indexes `to_tsvector('simple', …)` (exact technical tokens such as `a515-57-50r7`, `cf280x`) and
`to_tsvector('russian', …)` (morphology); time-aware composites `supplier_history (supplier_id, publish_date)`, `(platform, is_winner, publish_date)`,
`procurement_lot (platform, publish_date)`. No materialized statistics — every historical aggregate must be computed with `publish_date < as_of`.

**Full load result (2026-10-01):** reconciliation **PASS** (35/35); 604,452 lots · 2,971,651 items · 1,010,107 relations (1,010,138 raw − 31) ·
44,196 suppliers · 0 quarantined; 865 s total (COPY+normalize ≈ 9 min, index build 227 s, reconcile 63 s), peak RSS ≈ 0.7 GB, database 4.3 GiB.

**Schema additions after P1-001D (P1-002):** migration `0002_lexeme_stats` — `lexeme_stats(lexeme, ndoc)` + `lexeme_stats_meta`
(IDF snapshot of `russian`-config lexemes over items of lots published **before 2024-07-01**, earlier than every replay split; built by
`python -m app.cli search build-stats`). Migration `0003_item_publish_date` — `procurement_item.publish_date` (NOT NULL; physical copy of the
lot's `publish_date`, written by ingestion; not a contract field) with composite indexes `(okpd2_code|okpd2_kind|okpd2_group|okpd2_class,
publish_date DESC)`; reason: EXPLAIN ANALYZE showed OKPD2 retrieval walking all lots by date (389 ms) instead of an index range scan (22 ms after).
`docker-compose.yml` sets `shm_size: 1gb` for postgres (parallel VACUUM/index builds failed with the 64 MB default).

**Schema additions in P2-001 (semantic retrieval):** postgres image `pgvector/pgvector:pg16` (pgvector 0.8.x; `shm_size` raised to 4gb for the
HNSW build). Migration `0004_semantic` — `CREATE EXTENSION vector`; `semantic_text(text_hash char(32) PK = md5(product_name_normalized),
normalized_text, first_seen_publish_date, embedding vector(384), model_revision)` — one row per **distinct** normalized product text (993,289),
derived, rebuildable, never a source of facts; expression index `ix_item_name_md5_date (md5(product_name_normalized), publish_date DESC)` on
`procurement_item` maps a text back to its items. HNSW cosine index (m=16, ef_construction=64) is created by `semantic build`, not by the
migration. Model pinned in `backend/semantic_model.lock.json` (intfloat/multilingual-e5-small, exact revision, MIT), cached in the `models`
volume; commands `python -m app.cli semantic download-model | feasibility | build | status` (build is resumable; ~3.4 h on CPU).
Temporal rule: a text is eligible only if `first_seen_publish_date < as_of`, and every evidence item must have `publish_date < as_of` (SQL).
Ingestion `--reset-organizer-data` also drops the HNSW index and truncates `semantic_text`.
Hardening (2026-10-02): `semantic build` fails closed if stored embeddings carry a model revision other than the committed lock (`--reembed` re-embeds everything explicitly); `download-model` installs exactly the locked revision (`--update-lock` is a separate maintenance action). After validating invariants (all texts embedded, one pinned revision) the build stamps the HNSW index READY via a JSON `COMMENT ON INDEX` (model, revision, texts) in the same transaction; the build drops the index before embedding, so an interrupted build is never READY. Search checks lock + table + valid HNSW + READY stamp + revision with catalog lookups only; otherwise it returns P2-003 results with a `SEMANTIC_UNAVAILABLE` warning. `register_texts` moves `first_seen_publish_date` only earlier (`LEAST`) on backfill and never re-embeds an unchanged text. Storage: +4.0 GiB (table 3.9 GiB incl. 1.9 GiB HNSW; md5 index 125 MiB).
