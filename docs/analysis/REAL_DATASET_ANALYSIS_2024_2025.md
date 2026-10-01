# Real Dataset Analysis — Organizer Data 2024–2025

> **Status:** CURRENT · verified 2026-10-01 (hackathon day 1) · feeds [HACKATHON_EXECUTION_BASELINE.md](../HACKATHON_EXECUTION_BASELINE.md)
> **Method:** full scan of all three files (no sampling) with the reproducible stdlib-only profiler **`scripts/profile_dataset.py`** (P1-001A, v1.0.0).
> Machine-readable source of every number: `reports/dataset_profile.json` (deterministic; repeat runs byte-identical) · readable: `reports/dataset_profile.md`.
> Runtime 2–4 min on the team laptop. **Verified by P1-001A on 2026-10-01**; corrections from that verification are marked *(P1-001A)*.
> **Terminology (P1-001B):** "OKPD2 class (`XX.XX`)" below means the ОКПД2 **group** (`XX.XX`); класс is `XX` (DATA_MAPPING §4.1). Numbers unchanged.
> **Raw files:** temporarily missing during P1-001B (~12:46); restored files verified byte-identical to P1-001A (SHA-256).
> **Privacy:** 12-digit INNs (individual entrepreneurs, personal data — NFR-PRIV-01) are deliberately not printed here.
> Legend: ✅ confirmed · ⚠️ confirmed with correction · ❌ preliminary claim not confirmed · ❓ open (organizer question).

---

## 1. Files

| File (in `data/raw/`) | Size | Rows (excl. header) | Columns |
|---|---:|---:|---|
| `Извещения_24-25.csv` (notices / lots) | 294 MB | **604,452** | `publish_date; procedure_id; lot_id; start_price; reqnum; procedure_name; subject; is_smp; customer_inn; customer_kpp; is_eshop_or_aisgz` |
| `Поставщики_24-25.csv` (supplier relations) | 38 MB | **1,010,138** | `lot_id; supplier_inn; supplier_kpp; is_winner` |
| `ТРУ_24-25.csv` (goods/works/services items) | 379 MB | **2,971,651** | `lot_id; product_name; okpd2_code` |

✅ Row counts match the preliminary values (~604,452 / ~1,010,138 / ~2,971,651).

**Not in the data** (corrects preliminary assumptions):
- ⚠️ **No separate product description field.** ТРУ has only `product_name` (often long and spec-like) + `okpd2_code`.
  "Detailed product description" in the search-field priority list therefore maps to the same `product_name` text (see §6).
- No supplier names, OGRN, addresses, regions, contract dates, contract prices, quantities, units, КТРУ codes or OKPD2 titles.
  Supplier display names and OKPD2 titles must come from enrichment / a classifier dictionary (P1-001B/C).
- No item-level price; `start_price` is lot-level.

## 2. Cardinalities

| Measure | Value | Preliminary | |
|---|---:|---:|:-:|
| Unique `lot_id` (notices) | **604,452** (no duplicates) | ~604k | ✅ |
| Unique `procedure_id` | **604,452** — exactly 1 lot per procedure | — | new |
| Unique supplier INNs | **44,196** | ~44k | ✅ |
| Unique customer INNs | **2,785** non-empty *(P1-001B: P1-001A's 2,786 included the empty value; 8,449 lots have an empty customer INN)* | ~2.7k | ✅ |
| Unique OKPD2 codes (ТРУ) | **8,453** | ~8.4k | ✅ |
| Date range (`publish_date`) | 2024-01-08 → 2025-12-31 | 2024–2025 | ✅ |
| Lots per year | 2024: 303,538 · 2025: 300,914 | — | |

### By platform (`is_eshop_or_aisgz`)

| Platform | 2024 lots | 2025 lots | Total | Share |
|---|---:|---:|---:|---:|
| **АИС ГЗ** | 169,494 | 163,152 | 332,646 | 55.0% |
| **ЭМ** (electronic store) | 134,044 | 137,762 | 271,806 | 45.0% |

## 3. Relationships — `lot_id` is the key ✅

```text
ProcurementLot (Извещения, 604,452)
   ├── SupplierHistory (Поставщики, 1,010,138 rows → 550,173 lots)
   └── ProcurementItem (ТРУ, 2,971,651 rows → 604,436 lots)
```

| Integrity check | Result |
|---|---|
| Supplier rows whose `lot_id` is not in notices | **0** |
| ТРУ rows whose `lot_id` is not in notices | **0** |
| Lots without any ТРУ item | **16** (all АИС ГЗ) |
| Lots without any supplier relation | **54,279** — **all АИС ГЗ** (16.3% of АИС ГЗ lots; 0 on ЭМ) ✅ |
| Lots with neither | 14 |
| Duplicate (`lot_id`, `supplier_inn`) pairs | 31 (keep raw; de-duplicate in canonical layer) |

`procedure_id` ↔ `lot_id` is 1:1 in this extract, so `procedure_id` carries no extra grouping information.
**Decision HD-02:** `ProcurementLot` (keyed by `lot_id`) is the core aggregate.

Lots without suppliers are spread over the whole period (2024: 22,511 · 2025: 31,768; highest in 2025-12: 4,094 —
plausibly not yet contracted). They are **kept** as possible recommendation targets but are **not** benchmark ground truth.

## 4. Notice fields

| Field | Finding |
|---|---|
| `procedure_name` vs `subject` | **Identical in 591,813 lots (97.9%)**; identical after normalization (case/punctuation/ё) in **598,919 (99.1%)** ✅ → index one of them only (HD-03). |
| `subject` | 1 empty value |
| `start_price` | 3 empty, 21 zero; median 92,374 ₽; P25 24,500 ₽; P75 388,333 ₽; P99 19.9 M₽ |
| `reqnum` | Filled in 231,513 lots (38.3%); meaning unknown ❓ (OQ-36) |
| `is_smp` | `true` **only on АИС ГЗ** (149,963 = 45.1% of АИС ГЗ lots); **always `false` on ЭМ** → platform-dependent semantics ❓ (OQ-35) |
| `customer_inn` | 2,785 distinct customers (St Petersburg state customers). *(Verified in P1-001B)* 8,449 lots have an **empty** customer INN and empty KPP (4,648 АИС ГЗ, 3,801 ЭМ); 0 malformed non-empty values; 0 checksum failures |

## 5. Supplier relations and the `is_winner` semantics ✅ (critical)

| Platform / year | Lots | Lots with supplier | Supplier rows | `is_winner=true` | `is_winner=false` | Lots with ≥ 2 suppliers | Lots with 0 winners |
|---|---:|---:|---:|---:|---:|---:|---:|
| АИС ГЗ 2024 | 169,494 | 146,983 | 147,610 | 147,610 | **0** | 267 | 0 |
| АИС ГЗ 2025 | 163,152 | 131,384 | 131,421 | 131,421 | **0** | 12 | 0 |
| ЭМ 2024 | 134,044 | 134,044 | 352,674 | 130,749 | 221,925 | 77,083 (57.5%) | 3,304 (2.5%) |
| ЭМ 2025 | 137,762 | 137,762 | 378,433 | 134,098 | 244,335 | 82,001 (59.5%) | 3,666 (2.7%) |

Findings:
1. **Every provided АИС ГЗ supplier row has `is_winner=true`** (not "almost": 279,031 of 279,031) — this is the confirmed fact.
   *Working interpretation (not confirmed, pending OQ-33):* АИС ГЗ records awarded suppliers only, not the participant list (ADR-H1 amendment A1).
   The few АИС ГЗ lots with 2–13 "winners" *(P1-001A: max 13, not 8)* are mostly services
   (insurance, maintenance, medical examinations) — plausibly several contracts per lot.
2. **ЭМ delivers winner and non-winner rows** (completeness of participant lists not confirmed — A4): mean 2.63 (2024) / 2.75 (2025) suppliers per lot, 42.5% / 40.5% single-participant lots, 57.5% / 59.5% with ≥ 2;
   ~2.6% of ЭМ lots have no winner (probably failed/cancelled procedures ❓).
3. Therefore a single cross-platform win rate is **misleading** (АИС ГЗ would show 100%). **HD-05:**
   - `historical_award_count` — both platforms (winner rows).
   - `marketplace_participation_count`, `marketplace_win_count` — **ЭМ only**.
   - No `win_rate` across platforms until OQ-33 is answered.

**Organizer question OQ-33 (critical):** *Does АИС ГЗ supplier data contain only awarded suppliers rather than the full participant list?*

### Supplier identifiers
| Check | Value |
|---|---|
| INN length (rows) | 10 digits: 706,494 (69.9%) · 12 digits: 303,637 (30.1%) · other lengths: 7 rows |
| Unique INNs by type | legal entity (10): **20,591 (46.6%)** · individual / IE (12): **23,597 (53.4%)** · malformed: 8 |
| INN checksum *(P1-001A)* | 14 well-formed INNs fail the FNS control-digit check (flag, keep) · KPP values all match the 9-char format |
| Non-digit INN rows | 6 |
| `supplier_kpp` empty | 191,361 rows (18.9%) — KPP is optional, never part of identity |
| Platform overlap of INNs | АИС ГЗ only 25,375 · ЭМ only 8,482 · both 10,339 |
| ЭМ participants that never won on ЭМ | 4,679 |
| Supplier registration region (INN prefix) | unique INNs: 78 St Petersburg 52.8% · 77 Moscow 6.7% · 47 Leningrad obl. 5.3%; rows: 78 = 74.4%, 47 = 5.6%, 77 = 3.8% |

Rules: INN stays a **string** (leading zeros, 12-digit IEs), validated by length + digits (+ checksum in P1-001C);
malformed INNs are kept with a quality flag, never dropped. The INN region prefix is a free, explainable
"regional supplier" signal (tax-registration region, not delivery capability).
More than half of distinct suppliers are individuals/IEs → **personal-data minimization applies** (NFR-PRIV-01, OQ-24).

## 6. ТРУ items (product-level data) ✅

| Measure | Value |
|---|---|
| Items per lot | mean 4.9 · 1 item: 323,791 lots (53.6%) · 2–10: 225,198 (37.3%) · ≥ 11: 55,447 (9.2%) |
| Distinct OKPD2 per lot | 1: 501,236 (82.9%) · 2: 44,733 · 3: 18,096 · ≥ 4: 40,367 → **17.1% of lots span several codes** |
| `product_name` length | median 41 chars · P75 71 · P95 160 *(P1-001A: 161 came from a 1-in-20 sample)* (spec-like texts exist, e.g. full chair spec with dimensions, load, warranty) |
| `product_name` = lot subject (normalized) | 111,500 rows (3.8%); contained in subject: 64,813 (2.2%) → **≈ 94% of item rows add text not present in the lot title** |
| Empty `product_name` | 114 rows |

**Generic title + specific item** is common, e.g.:

| lot_id | Lot subject | Item(s) |
|---|---|---|
| 5718896 | Поставка компьютерного оборудования | Ноутбук Acer Aspire 5 A515-57-50R7 15.6" |
| 5875992 | Поставка оргтехники | Мышь компьютерная Acer OMW136 · Телевизор Xiaomi TV Pro 75 |
| 6022687 | Поставка компьютерной техники в 2025 году | МФУ HP LaserJet Pro 4103dw · Ноутбук ASUS VivoBook 17X … |
| 5510873 | Поставка хозяйственных товаров | Швабра флаундер с мопом 60x9 см · Насадка МОП … |
| 4900162 | Поставка строительных товаров и материалов | Сверло по металлу Практика 13х151 мм · Растворитель 646 … (all coded `32.99.59.000`) |

Caveats observed:
- **Normalized "type" names**: many items are catalog-style generic names, e.g. `Пюре томатное тип 1`, `Ноутбук¹ тип 3`,
  `Йогурт тип 2` — low information; OKPD2 and lot context carry more weight there. Footnote characters (`¹`) must be normalized.
- **OKPD2 noise**: e.g. lot 4900162 codes drills, solvent and sealing paste as `32.99.59.000`
  ("other products n.e.c."). → OKPD2 alone is unreliable (organizer §6, HD-04).

Search-field priority (**configurable, to be benchmarked**, HD-03):

| Signal | Field(s) | Initial priority |
|---|---|---|
| Item product text | `ТРУ.product_name` | VERY HIGH |
| Item spec detail | same field (no separate description exists) | HIGH (via attribute/number extraction, P1-001C) |
| OKPD2 | `ТРУ.okpd2_code` + hierarchy | HIGH |
| Lot context | other items of the lot, customer, price band | MEDIUM |
| Procedure name / subject | `subject` (one of the two duplicates) | LOW |

## 7. OKPD2

| Measure | Value |
|---|---|
| Distinct codes | 8,453 |
| Code depth (rows) | `XX.XX.XX.XXX` (full, 4 segments): 2,816,402 (94.8%) · 3 segments: 79,848 (2.7%) · `XX.XX` only: 75,124 (2.5%) · 1 segment: 39 |
| Empty / malformed | 238 empty · 1 malformed |
| Largest sections (rows) | 32 (incl. medical devices 32.50) 396k · 21 pharma 249k · 86 health services 170k · 33 repair 147k · 20 chemicals 138k · 29 vehicle parts 138k |
| Top codes (rows) | 29.32.30.390 (vehicle parts) 120,865 · 21.20 (class-level code) 70,046 · 21.20.23.110 60,695 · 32.50.50.190 56k · 86.90.19.110 51k |
| Hierarchy *(P1-001A)* | distinct prefixes by segment level: `XX` 83 · `XX.XX` 578 · 3-segment 2,809 · 4-segment 6,708; distinct codes by depth: 4 seg 6,708 · 3 seg 1,475 · 2 seg 261 · 1 seg 9 |

OKPD2 hierarchy (ОК 034-2014, КПЕС 2008): section (letter) → class `XX` → subclass `XX.X` → group `XX.XX` →
subgroup `XX.XX.X` → kind `XX.XX.XX` → category `XX.XX.XX.X` → subcategory `XX.XX.XX.XXX`.
Codes appear at **mixed depths** → relevance must use prefix matching (exact > same `XX.XX.XX` > same `XX.XX` > same `XX`).
The dataset does not include OKPD2 titles; an official classifier dictionary is needed for display (OQ-37).

## 8. Temporal replay feasibility ✅

Replay = for a target lot, use only lots with **strictly earlier** `publish_date`.
For ЭМ 2025 lots with a winner and ТРУ items (**134,095 lots**):

| Was the eventual winner visible in earlier history? | Lots | Share |
|---|---:|---:|
| as a supplier on any earlier lot | 131,943 | **98.4%** |
| … on an earlier lot with an OKPD2 **class** (`XX.XX`) in common | 124,104 | **92.5%** *(P1-001A: was mis-rounded as 92.6%)* |
| … on an earlier lot with the **same full OKPD2 code** | 114,665 | 85.5% |
| … with the **same customer** | 89,610 | 66.8% |

All ЭМ 2025 participants: 93.5% (342,069 / 365,829) had earlier history in the same OKPD2 class.

Implications:
- Recall from history is high → replay benchmark is meaningful; **the hard problem is ranking** among
  hundreds of historical candidates (golden lots below show 175–519 same-code candidates).
- A naive OKPD2 + award-count lookup is a **strong, honest baseline** (P1-002) that the product must beat.
- Few winners are "new" in replay → the *discovery* story must come from **external expansion** (HD-07/HD-08), not from history.

Benchmark pool (weak labels 2 = winner, 1 = participant, 0 = not observed):

| Pool | Lots |
|---|---:|
| ЭМ 2025, winner + ТРУ + ≥ 2 participants (**primary**) | 79,047 |
| ЭМ 2024, same criteria (dev / warm-up) | 74,489 |
| АИС ГЗ lots with a winner (winner rows only → grade-2 labels; no participant information, so no grade-1 or negative inference) | 278,364 |

Limitation (BR-22): a supplier not observed on a lot is **not** proven irrelevant; it did not bid on this platform.
Report metrics as "hit rate of actual winner/participants", not as precision.

## 9. Golden demonstration cases (verified)

All five preliminary lots exist, are **ЭМ 2025** with winners and participants. "Naive rank" = rank of the actual
winner when ranking all suppliers by count of earlier awards in the same full OKPD2 code (preview of the P1-002 baseline; not a product metric).
*(P1-001A)* Ranks are now **tie-independent**: best rank = 1 + suppliers with strictly more awards; the range shows the tie span
(the earlier single numbers depended on arbitrary tie order).

| lot_id | Date | Subject → item | OKPD2 | Participants | Same-code candidates | Naive rank of winner | Verdict |
|---|---|---|---|---:|---:|---:|---|
| 5612123 | 2025-03-25 | Поставка интерактивной панели → *Поставка интерактивной панели* | 26.20.13.000 | 10 | 178 | 9–10 | ⚠️ item text is **not** more specific than title; keep as category case, not as "product detail" case |
| 5545252 | 2025-02-04 | Поставка кресел … → *Кресло офисное Бюрократ CH-695NLT, сетка/ткань, высота 445–540 мм …* | 31.01.11.150 | 14 | 463 | 70–83 | ✅ strong spec-detail case; hard for naive baseline |
| 5542696 | 2025-02-03 | Поставка перчаток … нитриловых → *Перчатки смотровые/процедурные нитриловые, неопудренные, нестерильные* | 22.19.60.119 | 15 | 290 | 155–290 | ✅ hard case (winner had 1 prior same-code award) — honest limitation example |
| 5659204 | 2025-04-24 | Ноутбуки ASUS Vivobook 15 X1504ZA … → same text | 26.20.11.110 | 17 | 262 | 12–13 | ✅ detailed title = item |
| 5718896 | 2025-06-16 | **Поставка компьютерного оборудования** → *Ноутбук Acer Aspire 5 A515-57-50R7 15.6"* | 26.20.11.110 | 13 | 294 | 2 | ✅ **best "generic title + specific item" case** |

Additional verified candidates (ЭМ 2025, generic subject, specific item, ≥ 12 participants): 5875992 (оргтехника → mouse + 75" TV),
6022687 (компьютерная техника → MFP + laptop), 5510873 (хозтовары → mop, 18 participants), 5548828 (mouse; naive rank 63–175 — hard).
*(P1-001A, corrected)* The winner of 5718896 also participates in 5612123, 5659204, 5875992 and 6022687, and the winner of 5659204 participates in 5718896
(the winner of 5612123 does not appear in the other golden lots) → a laptop/IT supplier story across cases.

Final demo set is frozen in **P1-001F** (mix of easy/hard; never tuned on — BR-21).

## 10. Supplier pool health (preliminary computation)

Per full OKPD2 code; a lot counts if any item has the code; awards = winner rows; "recent" = won a lot published ≥ 2025-07-01.
Shortlist = goods (sections 01–32), ≥ 40 lots, ≥ 8 customers, ranked by top-supplier share.

| OKPD2 | Product (from item names) | Lots | Customers | Observed suppliers | Winning suppliers | Recent winners | Top-1 share | Top-3 share | HHI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **10.51.11.141** | Sterilized drinking milk 2.5% | 182 | 40 | 6 | 5 | 3 | **94.2%** | 98.8% | 0.89 |
| 10.42.10.111 | Margarine | 44 | 32 | 7 | 4 | 3 | 90.0% | 97.5% | 0.81 |
| **01.25.19.150** | Cranberry | 227 | 73 | 16 | 15 | 11 | **88.1%** | 92.7% | 0.78 |
| **10.61.22.130** | Rice flour | 136 | 79 | 11 | 9 | 7 | **86.4%** | 90.9% | 0.75 |
| 10.62.11.112 | Corn starch | 83 | 55 | 14 | 12 | 5 | 80.0% | 86.7% | 0.64 |
| 01.13.16.000 | Spinach | 144 | 83 | 19 | 16 | 5 | 77.6% | 84.8% | 0.61 |
| 10.12.10.170 | Chilled chicken fillet | 258 | 82 | 18 | 14 | 9 | 69.6% | 89.6% | 0.52 |
| 10.51.52.111 | Yogurt | 724 | 89 | 21 | 16 | 8 | 58.9% | 88.7% | 0.40 |
| **10.39.17.111** | Tomato purée ("пюре томатное тип 1") | 337 | 194 | 16 | 12 | 8 | 38.7% | 75.7% | 0.25 |

- ⚠️ **10.39.17.111 (tomato purée) is confirmed as concentrated** (12 winners for 194 customers; top-3 = 75.7%) but it is
  **not the strongest** case. Stronger candidates: **10.51.11.141 sterilized milk**, **01.25.19.150 cranberry**, **10.61.22.130 rice flour**.
- Recommendation for the expansion demo (to confirm in P3-001/P3-003 after checking that external manufacturers can be
  verified): **primary 10.51.11.141 (milk)** — many customers, extreme concentration, a market with many Russian
  manufacturers (strong "direct manufacturer" story); **backup 01.25.19.150 (cranberry)** or 10.61.22.130 (rice flour);
  keep 10.39.17.111 as a third example.
- Caveats: АИС ГЗ lots without suppliers are excluded from award counts; food categories are dominated by school/kindergarten
  catering; concentration may reflect logistics/framework purchasing rather than market failure — present it as
  "dependency risk", not as wrongdoing.

## 11. Assumption / claim verification summary

| Preliminary claim | Result |
|---|---|
| ~604k lots, ~1.01M supplier rows, ~2.97M ТРУ rows | ✅ exact: 604,452 / 1,010,138 / 2,971,651 |
| ~44k supplier INNs, ~2.7k customers, ~8.4k OKPD2 | ✅ 44,196 / 2,785 (+ empty) / 8,453 |
| `lot_id` connects all files | ✅ 0 orphans |
| ТРУ much richer than titles; multi-item, multi-OKPD2 lots | ✅ 46% multi-item; 17% multi-code; 94% of item rows add text |
| "Detailed product description" field | ❌ does not exist — only `product_name` |
| `procedure_name` ≈ `subject` | ✅ 97.9% identical, 99.1% after normalization |
| `supplier_inn` strongest key; KPP optional | ✅ (18.9% empty KPP; 8 malformed INNs) |
| АИС ГЗ ≈ all winners, ЭМ winners + non-winners | ✅ АИС ГЗ **100%** winners; ЭМ 36% winners |
| Lots without supplier relation, mostly АИС ГЗ | ✅ 54,279, **all** АИС ГЗ |
| ЭМ 2025 useful for replay | ✅ 79,047 lots with ≥ 2 participants |
| Golden lots 5612123 / 5545252 / 5542696 / 5659204 / 5718896 | ✅ all exist; ⚠️ 5612123 has no extra item detail |
| 10.39.17.111 concentrated | ✅ but ⚠️ not the strongest category |
| New: `is_smp` only true on АИС ГЗ; procedure ↔ lot 1:1; >50% of suppliers are IEs; INN region prefix available | new facts |
