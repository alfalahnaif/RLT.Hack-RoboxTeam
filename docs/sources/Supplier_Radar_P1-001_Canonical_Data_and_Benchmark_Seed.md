# Supplier Radar — P1-001: Canonical Data + Benchmark Seed

**Project:** Supplier Radar  
**Phase:** Phase 1 — Working Vertical Slice  
**Task ID:** P1-001  
**Status:** Implementation Specification  
**Primary Goal:** Establish stable canonical data contracts and a small benchmark seed so the team can build the first measurable search vertical slice without redesigning data structures later.

---

# 1. Purpose

P1-001 creates the minimum data foundation required before implementing search.

This task must produce:

1. Canonical supplier and product-offering contracts.
2. Search request and response contracts.
3. A small but realistic sample dataset.
4. A benchmark query set.
5. Relevance judgments for those benchmark queries.
6. Validation rules and invariants.
7. A repeatable seed format that can later be replaced by organizer data through adapters.

This task intentionally does **not** implement:

- semantic retrieval,
- ranking,
- external crawling,
- LLM query understanding,
- production ingestion pipelines,
- user interface.

The objective is to make the next task, **P1-002 — Keyword Baseline Vertical Slice**, straightforward and measurable.

---

# 2. Success Condition

P1-001 is complete when the repository contains stable contracts and seed data that satisfy all of the following:

- A supplier can be represented consistently.
- A product offering can be linked to a supplier.
- Search requests and responses have explicit schemas.
- At least 100 suppliers and 200 product offerings can be loaded from seed files.
- At least 10 benchmark procurement queries exist.
- Each benchmark query has relevance judgments.
- Data validation can reject malformed records.
- The same seed files can be loaded repeatedly without changing entity identifiers.
- The benchmark data can be used by P1-002 without modification.

---

# 3. Repository Structure

Recommended initial structure:

```text
supplier-radar/
│
├── contracts/
│   ├── supplier.schema.json
│   ├── product_offering.schema.json
│   ├── search_query.schema.json
│   ├── search_response.schema.json
│   └── README.md
│
├── data/
│   ├── seed/
│   │   ├── suppliers.jsonl
│   │   ├── product_offerings.jsonl
│   │   └── data_sources.jsonl
│   │
│   └── README.md
│
├── benchmark/
│   ├── queries.csv
│   ├── qrels.csv
│   ├── README.md
│   └── benchmark_manifest.json
│
├── scripts/
│   ├── validate_contracts.py
│   ├── validate_seed.py
│   └── validate_benchmark.py
│
└── docs/
    └── P1-001-canonical-data-and-benchmark-seed.md
```

The exact application structure can evolve later. The important point is to keep contracts, seed data, and benchmark data separate from application code.

---

# 4. Canonical Entity Strategy

The canonical model must separate:

1. **Supplier identity**
2. **Product offering**
3. **Source metadata**
4. **Search request**
5. **Search response**

The most important modeling decision is:

> Search operates primarily on `ProductOffering`, not directly on `Supplier`.

A supplier can offer many unrelated products. Searching a supplier-level text blob would reduce relevance quality.

Therefore:

```text
Procurement Query
      ↓
Product Offerings
      ↓
Relevant Offerings
      ↓
Supplier Aggregation
```

---

# 5. Identifier Strategy

All canonical entities must use stable UUIDs.

Recommended for the seed dataset:

**Deterministic UUIDv5 identifiers generated from stable namespaces and source keys.**

This is preferred over random UUIDv4 for seed data because regeneration must preserve identifiers exactly.

When importing organizer data later, external IDs are stored separately instead of replacing canonical IDs.

Example:

```text
canonical_id = deterministic UUID
external_id = source-specific identifier
source_name = organizer / registry / catalog / etc.
```

Do not use:

- database sequence IDs as external API identifiers,
- supplier name as an identifier,
- INN as the primary key.

INN is an important business identifier but may be missing in some records.

---

# 6. Supplier Contract

## 6.1 Purpose

Represents one canonical supplier/company entity.

## 6.2 Required Fields

```json
{
  "id": "uuid",
  "name": "string",
  "normalized_name": "string",
  "supplier_type": "manufacturer | distributor | supplier | service_provider | unknown",
  "legal_status": "active | inactive | unknown",
  "is_known_supplier": true,
  "source_ids": []
}
```

## 6.3 Full Canonical Shape

```json
{
  "id": "24b5a0d2-9e46-46bb-8ba7-88a2ee246a8f",
  "name": "ООО ТехноПанель",
  "normalized_name": "технопанель",
  "inn": "7812345678",
  "ogrn": "1237800000000",
  "kpp": "781201001",
  "supplier_type": "manufacturer",
  "legal_status": "active",
  "region_code": "78",
  "region_name": "Saint Petersburg",
  "city": "Saint Petersburg",
  "website": "https://example.com",
  "okved_codes": ["26.20", "46.51"],
  "is_known_supplier": true,
  "profile_completeness": 0.92,
  "source_ids": [
    {
      "source_name": "seed",
      "external_id": "SUP-0001"
    }
  ],
  "created_at": "2026-09-28T00:00:00Z",
  "updated_at": "2026-09-28T00:00:00Z"
}
```

---

# 7. Supplier Field Rules

| Field | Required | Rule |
|---|---|---|
| id | Yes | UUID |
| name | Yes | 2–300 characters |
| normalized_name | Yes | Lowercase normalized representation |
| inn | No | 10 or 12 numeric digits when present |
| ogrn | No | 13 or 15 numeric digits when present |
| kpp | No | 9 numeric digits when present |
| supplier_type | Yes | Enum |
| legal_status | Yes | Enum |
| region_code | No | String |
| region_name | No | String |
| city | No | String |
| website | No | Valid HTTP/HTTPS URL |
| okved_codes | No | Array of strings |
| is_known_supplier | Yes | Boolean |
| profile_completeness | Yes | Float 0–1 |
| source_ids | Yes | Non-empty array |
| created_at | Yes | ISO-8601 |
| updated_at | Yes | ISO-8601 |

---

# 8. Supplier Normalization Rules

## 8.1 Legal Prefixes

For search normalization, common legal prefixes may be removed from the normalized alias.

Examples:

```text
ООО "ТехноПанель"
→ технопанель

АО "Север Снаб"
→ север снаб
```

The original legal name must always be preserved.

## 8.2 Text Normalization

Recommended normalization:

1. Unicode NFC normalization.
2. Lowercase.
3. Replace `ё` with `е` in search aliases.
4. Remove repeated whitespace.
5. Normalize punctuation.
6. Strip surrounding quotes.
7. Preserve alphanumeric content.
8. Do not transliterate by default.

## 8.3 Do Not Over-Normalize

Do not remove meaningful words such as:

- technology,
- systems,
- medical,
- industrial,
- engineering.

Only legal-form noise should be removed.

---

# 9. Product Offering Contract

## 9.1 Purpose

Represents a product or service that a supplier can provide.

This is the primary searchable entity.

## 9.2 Required Fields

```json
{
  "id": "uuid",
  "supplier_id": "uuid",
  "title": "string",
  "normalized_title": "string",
  "description": "string",
  "category_code": "string or null",
  "category_name": "string or null",
  "attributes": {},
  "source_name": "string",
  "source_external_id": "string"
}
```

## 9.3 Full Example

```json
{
  "id": "68e4d459-f96a-43b7-88ea-a15e90857103",
  "supplier_id": "24b5a0d2-9e46-46bb-8ba7-88a2ee246a8f",
  "title": "Интерактивная панель 75 дюймов",
  "normalized_title": "интерактивная панель 75 дюймов",
  "description": "Interactive educational display with 4K resolution, touch input, Android module, and wall mounting support.",
  "category_code": "EDU-DISPLAY",
  "category_name": "Interactive Displays",
  "attributes": {
    "screen_size_inches": 75,
    "resolution": "4K",
    "touch": true,
    "installation": "wall_mount"
  },
  "brand": "TechPanel",
  "model": "TP-75EDU",
  "source_name": "seed",
  "source_external_id": "OFF-0001",
  "source_url": "https://example.com/products/tp-75edu",
  "source_observed_at": "2026-09-20T00:00:00Z",
  "created_at": "2026-09-28T00:00:00Z",
  "updated_at": "2026-09-28T00:00:00Z"
}
```

---

# 10. Product Offering Field Rules

| Field | Required | Rule |
|---|---|---|
| id | Yes | UUID |
| supplier_id | Yes | Must reference an existing Supplier |
| title | Yes | 2–500 characters |
| normalized_title | Yes | Normalized search representation |
| description | Yes | May be empty only if title is sufficiently descriptive |
| category_code | No | String |
| category_name | No | String |
| attributes | Yes | JSON object |
| brand | No | String |
| model | No | String |
| source_name | Yes | String |
| source_external_id | Yes | Unique within source |
| source_url | No | Valid URL |
| source_observed_at | No | ISO-8601 |
| created_at | Yes | ISO-8601 |
| updated_at | Yes | ISO-8601 |

---

# 11. Product Attribute Strategy

Attributes must be stored in flexible JSON.

Example:

```json
{
  "screen_size_inches": 75,
  "resolution": "4K",
  "touch": true
}
```

Another category may use:

```json
{
  "material": "stainless_steel",
  "capacity_liters": 50
}
```

This avoids prematurely creating category-specific SQL columns.

Later, frequently queried attributes can be promoted into dedicated indexed columns if needed.

---

# 12. Data Source Contract

A lightweight source model should exist from the beginning.

Example:

```json
{
  "id": "seed",
  "name": "P1-001 Seed Dataset",
  "source_type": "internal_seed",
  "base_url": null,
  "trust_level": "controlled",
  "last_sync_at": "2026-09-28T00:00:00Z",
  "status": "active"
}
```

Possible `source_type` values:

```text
internal_seed
organizer_dataset
government_registry
manufacturer_registry
company_catalog
procurement_history
open_web
```

---

# 13. Search Query Contract

## 13.1 Purpose

Defines the public request shape for search.

## 13.2 Canonical Input

```json
{
  "query": "Интерактивная панель 75 дюймов для школы",
  "filters": {
    "region": null,
    "supplier_type": null,
    "market_scope": "all"
  },
  "limit": 20
}
```

---

# 14. Search Query Validation

| Field | Rule |
|---|---|
| query | Required |
| query length | 3–1000 characters |
| filters | Optional object |
| region | Null or string |
| supplier_type | Null or valid enum |
| market_scope | `all`, `known`, or `external` |
| limit | Integer 1–100 |
| default limit | 20 |

Invalid examples:

```json
{
  "query": ""
}
```

```json
{
  "query": "TV",
  "limit": 10000
}
```

---

# 15. Search Response Contract

## 15.1 Response Shape

```json
{
  "request_id": "b48e4432-e864-4363-a7e5-5c19d121ed89",
  "query": "Интерактивная панель 75 дюймов",
  "parsed_query": null,
  "total_candidates": 42,
  "results": [
    {
      "supplier_id": "24b5a0d2-9e46-46bb-8ba7-88a2ee246a8f",
      "supplier_name": "ООО ТехноПанель",
      "supplier_type": "manufacturer",
      "region_name": "Saint Petersburg",
      "is_known_supplier": true,
      "matched_offering": {
        "offering_id": "68e4d459-f96a-43b7-88ea-a15e90857103",
        "title": "Интерактивная панель 75 дюймов",
        "category_name": "Interactive Displays"
      },
      "score": 0.87,
      "reason_codes": ["LEXICAL_MATCH"]
    }
  ],
  "timings": {
    "retrieval_ms": 25,
    "total_ms": 31
  },
  "warnings": []
}
```

For P1-002, `score` can be the normalized lexical relevance score.

Later phases can replace it with the hybrid Match Score.

---

# 16. Search Response Rules

For every result:

- `supplier_id` must reference a valid supplier.
- `matched_offering.offering_id` must reference a valid offering.
- `score` must be normalized to 0–1 for the public contract.
- `reason_codes` must be non-empty.
- Results must be ordered descending by score.
- Duplicate supplier results should eventually be aggregated.

For the first lexical slice, one supplier may have multiple matching offerings internally, but only the best matching offering should be returned in the initial supplier result list.

---

# 17. Reason Codes — Initial Set

P1-001 should reserve structured reason codes.

Initial vocabulary:

```text
LEXICAL_MATCH
EXACT_TITLE_MATCH
CATEGORY_MATCH
ATTRIBUTE_MATCH
REGION_MATCH
KNOWN_SUPPLIER
EXTERNAL_SUPPLIER
```

Later:

```text
SEMANTIC_MATCH
PROCUREMENT_EXPERIENCE
VERIFIED_MANUFACTURER
STRONG_PRODUCT_EVIDENCE
MULTI_SOURCE_VERIFICATION
```

Do not allow arbitrary explanation strings to become the canonical explanation mechanism.

---

# 18. Seed Dataset Objective

The seed dataset exists to:

1. Develop the first search slice.
2. Test schema validity.
3. Test retrieval behavior.
4. Create an initial benchmark.
5. Provide deterministic fallback data for demos.

It is **not** intended to represent real market statistics.

---

# 19. Seed Dataset Size

Minimum:

```text
100 Suppliers
200 Product Offerings
```

Preferred before P1-002 is complete:

```text
200 Suppliers
500 Product Offerings
```

Do not manually create thousands of records.

Quality and controlled relevance are more important than raw volume at this stage.

---

# 20. Seed Category Mix

Use at least 8–10 procurement categories.

Recommended seed categories:

1. Interactive educational displays
2. Laptops and computers
3. Office printers
4. Office furniture
5. Medical gloves
6. Cleaning products
7. Industrial pumps
8. LED lighting
9. Security cameras
10. Network equipment

This gives enough diversity to test lexical retrieval.

---

# 21. Supplier Distribution

Seed data should intentionally contain:

### Known Suppliers

Approximately:

**60–70%**

```json
"is_known_supplier": true
```

### External/New Suppliers

Approximately:

**30–40%**

```json
"is_known_supplier": false
```

This allows Market Expansion behavior to be tested from the beginning.

---

# 22. Supplier Type Distribution

The dataset should include:

```text
manufacturers
distributors
general suppliers
service providers
unknown
```

Suggested mix:

| Type | Target |
|---|---:|
| Manufacturer | 30% |
| Distributor | 30% |
| Supplier | 30% |
| Service Provider | 5% |
| Unknown | 5% |

Exact percentages are not important.

The purpose is to prevent the search layer from assuming all suppliers are identical.

---

# 23. Controlled Search Difficulty

The seed dataset should include different retrieval difficulty levels.

## Easy

Exact term matches.

Example query:

```text
интерактивная панель 75 дюймов
```

Offering:

```text
Интерактивная панель 75 дюймов
```

## Medium

Partial lexical overlap.

Query:

```text
сенсорный экран для школы
```

Offering:

```text
Интерактивная образовательная панель
```

## Hard

Relevant concepts with low lexical overlap.

These are useful later for semantic retrieval.

Example query:

```text
оборудование для видеонаблюдения
```

Offering:

```text
IP-камера 4MP PoE
```

The keyword baseline should fail on some hard cases. That is desirable because it gives the semantic phase something measurable to improve.

---

# 24. Negative Examples

Every category should contain plausible but irrelevant distractors.

Example query:

```text
интерактивная панель 75 дюймов
```

Relevant:

```text
Interactive display 75"
Educational touch panel
```

Distractors:

```text
75-inch standard television
Projector screen
Interactive whiteboard accessories
Laptop
```

Without controlled negatives, benchmark metrics will be artificially easy.

---

# 25. Seed Data File Format

Use:

**JSON Lines (`.jsonl`)**

for supplier and offering seed files.

Why:

- readable,
- streamable,
- easy to validate,
- one record per line,
- easy to append,
- compatible with Python tooling.

Files:

```text
data/seed/suppliers.jsonl
data/seed/product_offerings.jsonl
data/seed/data_sources.jsonl
```

---

# 26. Benchmark Query Dataset

File:

```text
benchmark/queries.csv
```

Schema:

| Column | Required | Description |
|---|---|---|
| query_id | Yes | Stable query identifier |
| query_text | Yes | Procurement request |
| category | Yes | Benchmark category |
| difficulty | Yes | easy / medium / hard |
| cutoff_date | No | Required later for temporal holdout |
| notes | No | Human notes |

Example:

```csv
query_id,query_text,category,difficulty,cutoff_date,notes
Q001,"Интерактивная панель 75 дюймов для школы",interactive_displays,easy,,"Exact product-type benchmark"
Q002,"Сенсорный экран для образовательного класса",interactive_displays,medium,,"Partial lexical overlap"
Q003,"Компьютер для офисной работы 16 ГБ оперативной памяти",computers,medium,,"Attribute-focused query"
```

---

# 27. Qrels Dataset

File:

```text
benchmark/qrels.csv
```

`qrels` = query relevance judgments.

Schema:

| Column | Required | Description |
|---|---|---|
| query_id | Yes | Matches `queries.csv` |
| supplier_id | Yes | Canonical supplier UUID |
| relevance_grade | Yes | 0, 1, or 2 |
| judgment_source | Yes | seed_design / human / historical |
| notes | No | Rationale |

Relevance grades:

```text
0 = irrelevant
1 = plausible supplier
2 = strongly relevant supplier
```

Example:

```csv
query_id,supplier_id,relevance_grade,judgment_source,notes
Q001,24b5a0d2-9e46-46bb-8ba7-88a2ee246a8f,2,seed_design,"Offers exact 75-inch interactive panels"
Q001,543e118f-a20f-4d88-9d2e-d8b722c849ec,1,seed_design,"Offers interactive displays but not exact size"
Q001,ba83a2d7-b69f-44bd-97ac-b902602865c3,0,seed_design,"Standard TVs only"
```

---

# 28. Benchmark Seed Size

Initial P1-001:

**10 queries minimum**

Recommended composition:

```text
4 easy
4 medium
2 hard
```

Before Phase 2 completion:

**20–30 queries**

with a frozen holdout subset.

---

# 29. Benchmark Design Principles

## Principle 1 — Controlled Relevance

For seed data, we intentionally know which suppliers should be relevant.

## Principle 2 — Multiple Relevant Suppliers

Do not design each query with only one valid supplier.

Real procurement markets have multiple possible suppliers.

Recommended:

```text
3–8 plausible/relevant suppliers per query
```

## Principle 3 — Include Distractors

Each benchmark category must contain suppliers that look superficially similar but are not valid matches.

## Principle 4 — Preserve Hard Queries

Do not modify hard queries merely because the keyword baseline performs poorly.

The benchmark exists to expose weaknesses.

---

# 30. Benchmark Manifest

File:

```text
benchmark/benchmark_manifest.json
```

Example:

```json
{
  "name": "supplier-radar-seed-benchmark",
  "version": "0.1.0",
  "created_at": "2026-09-28T00:00:00Z",
  "query_count": 10,
  "supplier_count": 100,
  "offering_count": 200,
  "relevance_scale": {
    "0": "irrelevant",
    "1": "plausible",
    "2": "strongly_relevant"
  },
  "notes": "Controlled benchmark for lexical baseline development."
}
```

The benchmark version must change whenever judgments change.

---

# 31. Data Invariants

The validation scripts must enforce the following.

## Supplier Invariants

- Supplier ID is unique.
- INN is unique when present unless explicitly flagged as a source duplicate.
- Source identifiers are unique within the same source.
- `profile_completeness` is between 0 and 1.

## Product Offering Invariants

- Offering ID is unique.
- `supplier_id` references an existing supplier.
- Title is not empty.
- Source external ID is unique per source.

## Benchmark Invariants

- Every qrel references an existing query.
- Every qrel references an existing supplier.
- Relevance grade is only 0, 1, or 2.
- Every query has at least one grade-2 supplier.
- Every query should preferably have at least one grade-0 distractor.
- Query IDs are unique.

---

# 32. Validation Scripts

Three scripts are recommended.

## validate_contracts.py

Validates schema files themselves.

Expected output:

```text
Contracts valid: 4/4
```

## validate_seed.py

Checks:

- JSON parsing,
- contract validation,
- foreign keys,
- duplicate IDs,
- required fields,
- uniqueness rules.

Expected output:

```text
Suppliers: 100 valid
Offerings: 200 valid
Sources: 1 valid
Errors: 0
Warnings: 3
```

## validate_benchmark.py

Checks:

- query IDs,
- supplier references,
- relevance grades,
- coverage.

Expected output:

```text
Queries: 10
Qrels: 47
Queries with grade-2 suppliers: 10/10
Invalid references: 0
```

---

# 33. Schema Technology

Recommended contract format:

**JSON Schema Draft 2020-12**

Why:

- language-neutral,
- easy to inspect,
- usable by frontend/backend tooling,
- validates seed fixtures,
- can later generate typed models.

Application code can also define Pydantic models, but JSON Schema remains the portable contract artifact.

---

# 34. Contract Versioning

Every contract should contain a version.

Initial pre-organizer-data version:

`0.1.0`

Version rules:

### PATCH

Documentation or non-breaking clarification.

### MINOR

New optional field.

### MAJOR

Breaking required-field or semantic change.

---

# 35. Handling Unknown Organizer Data

When organizer data arrives, do not rewrite the canonical model immediately.

Instead:

```text
Organizer Dataset
        ↓
Organizer Adapter
        ↓
Canonical Supplier
Canonical ProductOffering
```

Example mapping:

```text
organizer.vendor_title
→ supplier.name

organizer.tax_id
→ supplier.inn

organizer.item_description
→ product_offering.description
```

If organizer data contains an important concept missing from our model:

1. Add it to the Assumption/Decision Log.
2. Determine whether it is source-specific, canonical, or search-only.
3. Extend the canonical model only if necessary.

---

# 36. Raw Data Preservation

Future ingestion must preserve raw source records.

Recommended future structure:

```text
raw_source_record
────────────────────────
id
source_name
external_id
payload JSONB
ingested_at
checksum
```

P1-001 does not need to implement the database table yet, but the architecture must preserve this principle.

---

# 37. Data Generation Policy

Synthetic seed data is acceptable for engineering validation.

However:

- do not present synthetic companies as real companies,
- do not present synthetic benchmark results as real market performance,
- use clearly fictional company names or mark generated records,
- keep real organizer data separate when it becomes available.

---

# 38. Recommended Seed Data Creation Method

Use a deterministic generator script.

Example:

```text
scripts/generate_seed.py
```

Inputs:

```text
random_seed = 42
supplier_count = 100
offering_count = 250
```

Output:

```text
suppliers.jsonl
product_offerings.jsonl
```

The generator should use deterministic UUIDs derived from stable keys and must include hand-crafted benchmark anchor records.

Recommended structure:

```text
70% generated background records
30% controlled benchmark anchor records
```

---

# 39. Benchmark Anchor Records

For each benchmark query, explicitly create:

- 2–4 strongly relevant suppliers,
- 1–3 plausible suppliers,
- 2–5 distractors.

This gives known expected behavior.

Example:

```text
Q001 Interactive panel 75"

Strong:
- Supplier A: exact 75" interactive panel
- Supplier B: 75" educational touch display

Plausible:
- Supplier C: interactive panels 65"/86"

Distractors:
- Supplier D: 75" television
- Supplier E: projector screen
```

---

# 40. Sample Query Set v0.1

Recommended first ten queries:

| ID | Query | Difficulty |
|---|---|---|
| Q001 | Interactive panel 75 inches for a school | Easy |
| Q002 | Touchscreen display for an educational classroom | Medium |
| Q003 | Office laptop with 16 GB RAM | Medium |
| Q004 | Black-and-white laser printer for an office | Easy |
| Q005 | Ergonomic office chairs for employees | Easy |
| Q006 | Disposable nitrile medical gloves | Easy |
| Q007 | Professional cleaning chemicals for public buildings | Medium |
| Q008 | Industrial water pump for a technical facility | Medium |
| Q009 | Energy-efficient LED lighting for corridors | Medium |
| Q010 | Video surveillance equipment for a public building | Hard |

The final seed files should store realistic Russian query text because the primary search corpus is expected to be Russian.

---

# 41. Russian Query Variants

Each query should have at least one realistic Russian formulation.

Examples:

```text
Интерактивная панель 75 дюймов для школы
```

```text
Ноутбук для офисной работы с 16 ГБ оперативной памяти
```

```text
Одноразовые нитриловые медицинские перчатки
```

The benchmark should test the expected operating language.

---

# 42. Search Corpus Language Policy

Primary:

**Russian**

Secondary support can later include English.

The seed data may contain English metadata fields, but searchable titles/descriptions should be predominantly Russian.

This matters because PostgreSQL FTS configuration, tokenization, stemming, and embedding evaluation depend on the target language.

---

# 43. Data Completeness Strategy

Do not make every seed supplier perfect.

The dataset should include realistic incompleteness.

Examples:

- missing INN,
- unknown supplier type,
- no website,
- missing category,
- sparse description.

Suggested distribution:

```text
80% complete profiles
20% incomplete profiles
```

This allows later confidence and data-quality logic to be tested.

---

# 44. Duplicate Test Cases

The seed dataset should include controlled duplicate-like records.

Example:

```text
ООО "ТехноПанель"
ООО ТЕХНОПАНЕЛЬ
TechnoPanel LLC
```

Only include them when clearly marked for entity-resolution tests.

P1-001 itself does not need to merge them yet.

The goal is to prepare future test fixtures.

---

# 45. Market Scope Test Cases

The seed benchmark must include:

- known supplier relevant to query,
- external supplier relevant to query,
- known supplier irrelevant to query,
- external supplier irrelevant to query.

This is necessary to verify future behavior for:

```text
market_scope = all
market_scope = known
market_scope = external
```

---

# 46. Search Contract Compatibility

P1-001 must not encode ranking implementation details into the public API.

Bad:

```json
{
  "bm25_score": 7.3411,
  "ts_rank": 0.0917
}
```

Better:

```json
{
  "score": 0.87,
  "reason_codes": ["LEXICAL_MATCH"]
}
```

Internal retrieval scores may change later without breaking the public contract.

---

# 47. P1-001 Decision Log

| ID | Decision | Reason |
|---|---|---|
| P1D-001 | Search unit is ProductOffering | Better product-level relevance |
| P1D-002 | Canonical IDs are stable UUIDs | Source-independent API identifiers |
| P1D-003 | Seed IDs use deterministic UUIDv5 | Regeneration preserves identifiers |
| P1D-004 | Seed files use JSONL | Simple, readable, streamable |
| P1D-005 | Benchmark uses CSV + qrels | Easy evaluation tooling |
| P1D-006 | Relevance scale is 0/1/2 | Supports nDCG later |
| P1D-007 | Query language is primarily Russian | Matches expected deployment context |
| P1D-008 | Seed contains controlled negatives | Prevent artificially easy benchmark |
| P1D-009 | Market expansion represented in seed | Tests known vs external suppliers early |
| P1D-010 | Contracts use JSON Schema | Language-neutral contract layer |
| P1D-011 | Organizer data enters through adapters | Avoid redesigning canonical model |

---

# 48. P1-001 Assumption Log

| ID | Assumption | Status |
|---|---|---|
| P1A-001 | Russian text will dominate search queries | Likely |
| P1A-002 | Suppliers can have multiple product offerings | Domain assumption accepted |
| P1A-003 | Organizer data can map into supplier/offering structure | Unverified |
| P1A-004 | INN will be present for many but not all suppliers | Likely |
| P1A-005 | Search quality should be measured primarily at supplier level | Strong assumption |
| P1A-006 | Product offering text will be available or derivable | Unverified |
| P1A-007 | External/new supplier distinction can be represented as a boolean initially | Accepted MVP simplification |
| P1A-008 | 10 seed benchmark queries are enough to build the first baseline | Accepted for P1-002 only |

---

# 49. P1-001 Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Seed data too artificial | Medium | Use controlled realistic Russian text |
| Benchmark too easy | High | Add distractors and hard queries |
| Canonical schema too rigid | High | Keep optional fields and JSON attributes |
| Organizer schema differs significantly | Medium | Use adapter layer |
| Supplier-level judgments hide offering relevance | Medium | Store matched offering in results |
| Random seed generator creates inconsistent relevance | High | Use hand-crafted anchor records |
| Regenerated IDs invalidate qrels | High | Use deterministic UUIDv5 identifiers |

---

# 50. Definition of Done

P1-001 is Done only if all of the following are true:

## Contracts

- [ ] `supplier.schema.json` exists.
- [ ] `product_offering.schema.json` exists.
- [ ] `search_query.schema.json` exists.
- [ ] `search_response.schema.json` exists.
- [ ] All schemas pass JSON Schema validation.

## Seed Data

- [ ] At least 100 suppliers exist.
- [ ] At least 200 offerings exist.
- [ ] Every offering references a valid supplier.
- [ ] Both known and external suppliers exist.
- [ ] Multiple supplier types exist.
- [ ] At least 8 procurement categories exist.
- [ ] Controlled distractor records exist.

## Benchmark

- [ ] `queries.csv` contains at least 10 queries.
- [ ] `qrels.csv` contains relevance judgments.
- [ ] Every query has at least one grade-2 supplier.
- [ ] Every query has negative/distractor cases.
- [ ] Benchmark manifest exists.
- [ ] Validation passes.

## Reproducibility

- [ ] Seed generation is deterministic.
- [ ] IDs remain stable between runs.
- [ ] No manual editing is required after generation.

## Documentation

- [ ] Contract README exists.
- [ ] Data README exists.
- [ ] Benchmark README exists.
- [ ] Assumptions and decisions are recorded.

---

# 51. Expected Deliverables

At completion, P1-001 should produce:

```text
contracts/
  supplier.schema.json
  product_offering.schema.json
  search_query.schema.json
  search_response.schema.json

data/seed/
  suppliers.jsonl
  product_offerings.jsonl
  data_sources.jsonl

benchmark/
  queries.csv
  qrels.csv
  benchmark_manifest.json

scripts/
  generate_seed.py
  validate_contracts.py
  validate_seed.py
  validate_benchmark.py
```

---

# 52. Handoff to P1-002

P1-002 must treat these artifacts as contracts.

The next implementation step becomes:

```text
Seed Data
    ↓
PostgreSQL
    ↓
Search Projection
    ↓
PostgreSQL Full-Text Search
    ↓
POST /api/v1/search
    ↓
Ranked Lexical Results
```

P1-002 should not redesign supplier or offering entities unless a concrete blocker is discovered.

If a schema change is necessary:

1. Update the Decision Log.
2. Version the affected contract.
3. Update seed data.
4. Re-run validation.
5. Re-run the benchmark.

---

# 53. Immediate Engineering Action

The first concrete coding sequence after this document is:

```text
1. Create repository structure.
2. Write the four JSON Schemas.
3. Implement deterministic seed generator.
4. Generate suppliers and product offerings.
5. Create ten benchmark queries.
6. Create qrels.
7. Implement validation scripts.
8. Freeze benchmark version 0.1.0.
```

Only after all eight steps pass validation should the team start:

**P1-002 — Keyword Baseline Vertical Slice.**

---

# 54. P1-001 Final Outcome

At the end of P1-001, the team should be able to answer:

### What is a supplier in our system?

Defined.

### What is searchable?

Product Offering.

### How do we represent a procurement search request?

Defined.

### How do we represent a search result?

Defined.

### What data do we build against before organizer data arrives?

Controlled seed data.

### How do we know whether search is improving?

Benchmark queries + qrels.

### What happens when organizer data arrives?

Map it through adapters into the canonical contracts.

---

# Status

**P1-001 Specification:** READY  
**Next Task:** P1-002 — Keyword Baseline Vertical Slice  
**Blocking Requirement Before P1-002:** Generate and validate the P1-001 artifacts defined above.
