# P4-005A — Market Product Backend (free-text supplier discovery)

- **Branch:** `feature/market-product-backend`, based on `hackathon-demo-freeze`.
- **Unchanged:** the frozen engine (`DEFAULT_CONFIG = P2_001_SEMANTIC`, ranking weights, semantic model), the holdout reports, and the lot-ID endpoints. The frozen demo and evaluation tags are untouched.

## Endpoints

| Route | Purpose |
|---|---|
| `POST /api/v1/supplier-search` | Free-text supplier discovery. Body: `{query (3–1000 chars), okpd2?, region? (2-digit INN registration region), limit 1–100 = 20}` |
| `GET /api/v1/supplier-search/{search_id}/export?format=json\|csv` | Stateless CRM / ERP / SRM export. `search_id` encodes the request, so the export re-runs the same deterministic search. |

The existing routes are unchanged: `/health`, `/recommendations/{lot_id}`, `/procurements/{lot_id}/analysis`, `/market-intelligence/{okpd2}`. CORS now allows `POST` from the local frontend origins only.

## How it works (no second engine)

1. **Query object.** The text becomes a one-item query of the same type as a procurement query (`QueryLot` / `QueryItem`) by `app/search/text_query.py`:
   - same product-name normalization, Russian lexemes and technical tokens (e.g. `a515-57-50r7`)
   - `as_of` = the day after the latest procurement (2026-01-01), so history is strictly before it
2. **Ranking.** The query runs through the shared pipeline: `recommend.prepare_query` (extracted from the lot path without changing it) → `scoring.rank_suppliers` with `DEFAULT_CONFIG`. That means lexical + trigram + OKPD2 + semantic retrieval with the same explanations.
3. **OKPD2 classification** (deterministic, built from existing signals):
   - **History status** of the analyzed code, using the accepted P3 thresholds:
     - SUFFICIENT: at least 20 lots and 20 awards
     - SPARSE: at least 1 lot
     - NONE: no lots
   - **Suggested codes:** the OKPD2 of historical items matched by the text, technical or semantic branches (never by the OKPD2 branch), weighted by the engine's own item similarity (≥ 0.5). Top 3 are returned, each with its share, supporting items and lots, and example products.
   - **Alignment** of a supplied code with the text evidence:
     - ALIGNED: same group (XX.XX) as a supported suggestion
     - UNCERTAIN: same class (XX) only, or weak text evidence
     - MISMATCH: no relation
   - **What the ranking uses:**
     - The supplied code is used only when it has history and is not MISMATCH.
     - With no history, or on MISMATCH, ranking uses text and semantic evidence only, and a warning says so.
     - The supplied code is always kept in `provided_okpd2` and analyzed in pool health. It is never replaced by a suggestion.
4. **Pool health and external expansion:** run for the supplied code (`PROVIDED`) and the top suggestion (`SUGGESTED`), using the accepted P3 services.
   - P3 is refactored without behaviour change so that external expansion also works for a code with no procurement history.
   - An unseen code gives `UNAVAILABLE / CATEGORY_NOT_OBSERVED` for pool health. The rest of the response is still returned.
5. **Contact:** taken only from sources. `website` comes from FIRST_PARTY_WEBSITE evidence. Phone, e-mail and address are always `null`: neither the procurement data nor the curated seed contains them.
6. **Freshness:** `last_checked_at` is the latest evidence check, and `source_url` points to the strongest active evidence. `FRESH` means checked within 180 days, otherwise `STALE`; `UNKNOWN` when there is no evidence.
   - Historical suppliers get `contact`, `freshness`, `company_name` and `role` only when their INN appears in curated evidence. Otherwise these are `null` / `NO_EVIDENCE`.
7. **Price:** `price_intelligence.available = false`, reason "Comparable supplier-level pricing is not available in the current dataset." The canonical data has no supplier-level awarded or bid prices, only the lot `start_price`, which is never used for price claims.
8. **Semantics preserved:**
   - VERIFIED and UNDER_REVIEW are copied as-is from the P3 verification.
   - `EXTERNAL_NEW` means new to the procurement data; it says nothing about the company's age.
   - `exact_okpd2_asserted_by_source` is kept.
   - Semantic evidence appears only as secondary provenance; it is filtered out of `reasons`.

## Verified behaviour (real canonical data)

| Request | Result |
|---|---|
| "Молоко ультрапастеризованное 3.2%" | Text-only. Suggestions: 10.51.11.121 (59%), 10.51.11.111, 10.51.11. 92 candidates. Pool health for the suggested code. |
| same text + 10.51.11.141 | ALIGNED. Ranked with the code (33 candidates). Pool VERY_HIGH / EXPANSION_RECOMMENDED. External 4 VERIFIED + 2 UNDER_REVIEW with contact and freshness (e.g. website https://molloko.ru/, FRESH, checked 2026-10-01). |
| same text + 26.20.11.110 (laptops) | MISMATCH. Code kept and analyzed (LOW). Ranking identical to the text-only search. Suggestions point to 10.51.11.*. |
| "Молоко питьевое" + 10.51.11.999 | NONE. Ranking is text-only. The supplied code's pool is `CATEGORY_NOT_OBSERVED`; the suggested code's pool is OK. |
| sparse code (1–5 lots) | SPARSE plus a warning; suppliers still ranked from text evidence. |
| "Ноутбук Acer Aspire 5 A515-57-50R7" | Technical token `a515-57-50r7` kept; suggestion 26.20.11.110 (100%); top supplier's best product matches the exact model. |

Warm latency (3 HTTP calls each):

| Request | Latency |
|---|---|
| Milk + code | 0.84–1.04 s |
| Text-only | 0.77–1.70 s |
| Laptop | 0.40–1.13 s |
| CSV export | 0.41 s |

## Tests

**374 passed** (361 before + 13 new in `tests/api/test_supplier_search.py`). The new tests cover:

- text-only search
- text + explicit OKPD2
- sparse OKPD2
- unseen OKPD2
- mismatch
- technical tokens
- no invented contact data
- contact and freshness (FRESH / STALE with an injected date)
- registration-region filter
- deterministic response and `search_id`
- CSV / JSON export and an invalid id
- validation errors
- lot endpoints unchanged (recommendation config and timing keys, analysis, market intelligence 4/2)

Holdout not run.

## Notes for frontend integration

- Response keys: `search_id`, `query`, `classification`, `candidate_count`, `suppliers`, `pool_health`, `external_expansion`, `price_intelligence`, `integration`, `semantic_enabled`, `warnings`, `timings_ms`. Pydantic models are in `backend/app/api/supplier_search_models.py`; OpenAPI is at `/docs`.
- Warning strings start with a stable code before the colon: `OKPD2_TEXT_MISMATCH`, `OKPD2_ALIGNMENT_UNCERTAIN`, `OKPD2_HISTORY_SPARSE`, `OKPD2_NOT_OBSERVED`, `WEAK_TEXT_EVIDENCE`, `REGION_IS_REGISTRATION_REGION`, `SEMANTIC_UNAVAILABLE`, `EXTERNAL_EVIDENCE_UNAVAILABLE`.
- `text_okpd2_alignment` is `null` when no OKPD2 was supplied.
