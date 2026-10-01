# API Contracts (analysis level)

> ### Hackathon Day-1 amendment (2026-10-01, ADR-H1)
> The v2 endpoint set is defined at analysis level in [Baseline §12](../HACKATHON_EXECUTION_BASELINE.md#12-updated-architecture): `POST /api/v1/recommendations`
> (`{lot_id}` or `{text}`, optional `as_of`, `limit`) returning suppliers with `components`, `reason_codes`, `evidence_lots`, `pool_health`,
> `external_candidates`; plus `GET /lots/{lot_id}`, `GET /categories/{okpd2}/pool-health`, `GET /meta`. Existing `POST /search` (below) is kept
> as the free-text entry and maps to `/recommendations {text}`; the frontend typed client keeps its mock mode until the live API exists (ED-27).
> Field-level contracts are produced in v2 P1-001B / P1-002. Score scale stays 0–1 in the API, 0–100 in the UI (ED-01).

> Sources: Phase 0 §56–63; P1-001 §13–17, §46. **Not implemented.** The executable contract will be
> `/contracts/search_query.schema.json` + `search_response.schema.json` (P1-008) and the FastAPI OpenAPI
> document. Fields marked **[ER]** are proposed additions (MINOR, optional → non-breaking per BR-25).

## Principles (Phase 0 §63)
Versioned (`/api/v1`) · Pydantic validation · typed error codes · correlation/request IDs · pagination ·
ISO-8601 timestamps · no DB entities in responses · DTOs separate from ORM · no internal retrieval scores
in public payloads (P1-001 §46).

## Endpoint inventory

| Method & path | Priority | Purpose | Errors |
|---|---|---|---|
| `POST /api/v1/search` | P0 | Search pipeline (SF-01) | 422 `QUERY_TOO_SHORT` (status: C-06), `QUERY_TOO_LONG` [ER], `INVALID_FILTER`, `VALIDATION_ERROR`; 503 `SEARCH_UNAVAILABLE` |
| `GET /api/v1/suppliers/{supplier_id}` | P0 | Supplier profile; optional `?request_id=` for query context [ER ED-02] | 404 `SUPPLIER_NOT_FOUND`; 301/200-with-`redirected_from` for merged IDs [ER] |
| `GET /api/v1/suppliers/{supplier_id}/evidence` | P1 | Evidence list (paginated [ER]) | 404 |
| `GET /api/v1/meta/filters` | P1 | Regions, supplier types, source types, categories | — |
| `POST /api/v1/feedback` | P2 (Should) | Relevance feedback | 422; 404 `REQUEST_NOT_FOUND` [ER] |
| `GET /api/v1/health` | P0 (stub) → P1 full | API, DB, search index (+ model) | 503 when degraded [ER] |
| `GET /api/v1/searches/{request_id}` [ER] | P1 | Re-open a search run (US-08, S-05) | 404 `REQUEST_NOT_FOUND` |
| `POST /api/v1/debug/rank` | Debug only | Experiments; registered only when `DEBUG=true` | — |

## POST /search

### Request
```json
{
  "query": "Интерактивная панель 75 дюймов для школы",
  "filters": {
    "region": null,
    "supplier_type": null,
    "market_scope": "all"
  },
  "intent_overrides": null,
  "limit": 20
}
```
| Field | Rule | Source |
|---|---|---|
| query | required, 3–1000 chars (trimmed) | P1-001 §14 |
| filters.region | null or string (code vs name vs delivery region: OQ-19) | P1-001 |
| filters.supplier_type | null or enum (multi-select? G-09) | P1-001 |
| filters.market_scope | `all` \| `known` \| `external`, default `all` | P1-001 |
| intent_overrides **[ER]** | partial SearchIntent; user-edited fields (UC-08, C-07) | ED-19 |
| limit | int 1–100, default 20 | P1-001 |
| offset / cursor | **missing** — pagination principle unmet (G-08) | — |

### Response
```json
{
  "request_id": "uuid",
  "query": "Интерактивная панель 75 дюймов для школы",
  "parsed_query": {
    "product": "интерактивная панель",
    "category_terms": ["интерактивные панели", "образовательное оборудование"],
    "attributes": {"screen_size_inches": 75},
    "region": null,
    "supplier_types": [],
    "mandatory_constraints": [],
    "field_origin": {"attributes": "extracted"}
  },
  "total_candidates": 318,
  "market_summary": {"known": 12, "external": 25, "by_type": {"distributor": 6, "manufacturer": 3}, "new_to_category": null},
  "results": [
    {
      "rank": 1,
      "supplier_id": "uuid",
      "supplier_name": "ООО ТехноПанель",
      "supplier_type": "manufacturer",
      "region_name": "Санкт-Петербург",
      "is_known_supplier": true,
      "matched_offering": {"offering_id": "uuid", "title": "Интерактивная панель 75 дюймов", "category_name": "Интерактивные панели"},
      "score": 0.87,
      "match_score": 0.87,
      "confidence_score": 0.91,
      "contributions": [{"feature": "semantic", "points": 27.0, "applicable": true}],
      "reason_codes": ["CATEGORY_MATCH", "ATTRIBUTE_MATCH", "KNOWN_SUPPLIER"],
      "explanation": "…templated text…",
      "risk_flags": [],
      "top_evidence": [{"evidence_type": "PRODUCT_CATALOG", "claim": "…", "source_name": "…", "source_url": "…", "observed_at": "…"}]
    }
  ],
  "versions": {"parser": "rules-0.1.0", "ranking": "1.0.0", "index": "…", "embedding": "e5-base@…"},
  "timings": {"parse_ms": 5, "retrieval_ms": 180, "ranking_ms": 35, "total_ms": 240},
  "warnings": []
}
```
Evolution by phase (all additive):
- **P2 (baseline slice):** `request_id, query, parsed_query=null, total_candidates, results[{supplier_id, supplier_name, supplier_type, region_name, is_known_supplier, matched_offering, score, reason_codes}], timings{retrieval_ms,total_ms}, warnings` — exactly P1-001 §15.
- **P3:** `parsed_query`, `contributions`, `match_score` (`score` kept as alias until contract 1.0 — C-05), `versions`, `ranking_ms`.
- **P5:** `confidence_score`, `risk_flags`, `top_evidence`, `explanation`, `market_summary`.

### Result rules (P1-001 §16)
Valid supplier/offering IDs · score ∈ [0,1] · non-empty reason codes · sorted desc · one result per supplier (best offering).

## GET /suppliers/{supplier_id}
Returns: identity (name, INN/OGRN/KPP, legal status, region, city, website, OKVED) · supplier type + basis ·
known/external · offerings (paginated; query-relevant first when `request_id` given) · procurement history ·
evidence (or summary + link to `/evidence`) · source metadata · confidence (+ breakdown) · risk flags ·
**[ER]** `query_context {request_id, rank, match_score, contributions, reason_codes, matched_offerings}` when `request_id` known.

## GET /meta/filters
`{ regions: [{code, name, count}], supplier_types: [...], source_types: [...], categories: [{code, name, count}] }` — counts [ER].

## POST /feedback (Should)
Request `{request_id, supplier_id, relevance: relevant|not_relevant|unsure}` → `201 {feedback_id}`; upsert on (request_id, supplier_id) [ER].

## GET /health
`{status: ok|degraded|down, components: {api, db, search_index {documents, embedded_ratio}, embedding_model, llm?}, versions}`.

## Error envelope (ED-07)
```json
{ "error": { "code": "INVALID_FILTER", "message": "supplier_type must be one of …", "details": {"field": "filters.supplier_type"}, "request_id": "uuid" } }
```

## Warning codes (non-fatal)
`SEMANTIC_UNAVAILABLE · LLM_UNAVAILABLE · PARSER_FALLBACK · HISTORY_UNAVAILABLE · STALE_EXTERNAL_DATA · MULTI_ITEM_QUERY_DETECTED · LOW_INFORMATION_QUERY · FILTER_REGION_OVERRIDES_QUERY · NO_RESULTS`
