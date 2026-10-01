# P3-002C — Market Intelligence API Integration

Route: `GET /api/v1/market-intelligence/{okpd2}`; defaults: `as_of=2026-01-01`, `recent_days=365`.

## Response contract

Typed sections: `category`, `pool_health`, `concentration`, `historical_alternatives`, `external_expansion`, `provenance`.
Historical procurement, external reconciliation and curated verification remain separate.

## Real canonical-database responses

| OKPD2 | Pool status | Lots | Known customers | Observed / winning suppliers | Awards | Top 1 | Top 3 | HHI | Signal | Alternatives | Curated external | Verified / review |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|
| `10.51.11.141` | VERY_HIGH | 182 | 39 | 6 / 5 | 173 | 0.9422 | 0.9884 | 0.8895 | EXPANSION_RECOMMENDED | 5 | true | 4 / 2 |
| `10.20.25.111` | LOW | 179 | 74 | 45 / 42 | 169 | 0.1302 | 0.2899 | 0.0493 | NO_EXPANSION_SIGNAL | 10 | false | 0 / 0 |

### Curated candidate states

| INN | Reconciliation | Verification | Exact OKPD2 source assertion |
|---|---|---|---|
| `5320000979` | EXTERNAL_NEW | VERIFIED | false |
| `0257011170` | EXTERNAL_NEW | VERIFIED | false |
| `7622012124` | EXTERNAL_NEW | VERIFIED | false |
| `5028002303` | EXTERNAL_NEW | VERIFIED | false |
| `3128004452` | EXTERNAL_NEW | UNDER_REVIEW | false |
| `5007126820` | EXTERNAL_NEW | UNDER_REVIEW | false |

## Performance

Five local calls: [117.521, 111.886, 115.771, 108.177, 102.282] ms; median **111.886 ms**, p95 **117.171 ms**, max **117.521 ms**; response **13308 bytes**.
Local FastAPI TestClient against canonical PostgreSQL; includes HTTP adapter and database work.

## Tests and integration

- 286 safe unit/API tests passed; integration tests that use shared test state were not run.
- No existing FastAPI app/router existed; created backend/app/api/main.py and registered one router there.
- Search, semantic, ranking, benchmark, Docker, requirements, migrations, CLI and frontend files untouched.

## Limitations

- Historical concentration describes observed procurement awards, not the entire current supplier market.
- No curated external evidence in the catalog does not mean no external suppliers exist.
- Source URLs are validated syntactically and are not fetched during API requests.
- FastAPI, Pydantic, HTTPX and Uvicorn were installed in the local worktree virtual environment only; deployment dependency files remain unchanged under this task's constraints.
- Historical alternatives expose observed_relation_count because the accepted pool service does not expose a distinct per-supplier lot count.

## Next step

After semantic retrieval work is accepted, integrate this endpoint with the frontend and historical recommendation flow; add runtime dependencies when the requirements-file constraint is lifted.
