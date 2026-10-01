# P4-001 — Final Backend Integration

## Branch and commits

- Branch `integration/hackathon-final`, created from `f959d79` (P2-001 hardening).
- Merge `e552468` brings in `codex/independent-task` @ `b28e17e` (P3-001, P3-002A/B/C), with history preserved.
- Integration code: `43cd7c8`. This report is committed on top of it.

## Merge conflicts

No textual conflicts: P2 and P3 changed disjoint files. Three integration gaps were fixed in `43cd7c8`:

- The FastAPI stack was missing from `requirements.txt` (P3 had used a local venv only).
- `data/seed` was not mounted in Docker, which the curated evidence catalog needs.
- The new routers were added to the single existing FastAPI app rather than to a second app.

## Runtime dependencies

| Source | Packages |
|---|---|
| `requirements.txt` | alembic 1.14.0 · SQLAlchemy 2.0.36 · psycopg[binary] 3.2.3 · pytest 8.3.4 · **fastapi 0.115.6 · uvicorn 0.34.0 · pydantic 2.13.5 · httpx 0.28.1** (the versions the P3 work was validated with) |
| `requirements-semantic.txt` | sentence-transformers 3.3.1 · transformers 4.46.3 · huggingface_hub 0.26.5 · numpy 2.1.3 · pgvector 0.3.6 |
| Dockerfile | torch 2.5.1 CPU |

- `pip check` reports no broken requirements.
- The model lock is unchanged: `intfloat/multilingual-e5-small @ 614241f622f53c4eeff9890bdc4f31cfecc418b3`.

## API routes

All routes are served by one FastAPI app (`app.api.main:app`), base URL `http://localhost:8000/api/v1`.

| Route | Behaviour |
|---|---|
| `GET /health` | Reports api, postgres, semantic (READY, pinned and index revision, model loaded) and curated catalog. Uses catalog lookups only. |
| `GET /recommendations/{lot_id}` | Calls `recommend(conn, lot_id)`, so `DEFAULT_CONFIG = P2_001_SEMANTIC`. Returns typed JSON: query summary, config, warnings, candidate count, ranked suppliers with reasons and semantic provenance, and timings. |
| `GET /procurements/{lot_id}/analysis` | Returns procurement + recommendations + one market-intelligence entry per distinct exact OKPD2 (sorted), with `as_of` = the lot's publish date. Each section carries its own `OK`/`UNAVAILABLE` status, and the response is marked `COMPLETE` or `PARTIAL`. Items without an OKPD2 are listed and get no market intelligence. |
| `GET /market-intelligence/{okpd2}` | The P3-002C route, unchanged. |

- **Startup:** if semantic is READY, the pinned model is loaded once. Otherwise the API still starts, and recommendations fall back to P2-003 with a `SEMANTIC_UNAVAILABLE` warning.
- **CORS:** only `http://localhost:3000` and `http://127.0.0.1:3000`, GET only, and `*` is ignored. Frontend code is unchanged; its client already defaults to `http://localhost:8000/api/v1`.

## Docker

- Start: `docker compose up -d --build`.
  - `postgres` runs on the existing volume.
  - `api` runs `alembic upgrade head` (a no-op at head) and then uvicorn on port 8000, with a healthcheck.
- Restart to healthy: **12.1 s**. First recommendation after start: **0.33 s**.
- No embeddings were rebuilt.
- The one-off bootstrap for a fresh environment is documented in the README; the ~3.4 h semantic build was not run.

## Tests

`docker compose run --rm backend pytest -q` → **361 passed**, 0 failed:

| Group | Tests |
|---|---:|
| P2 and earlier | 295 |
| P3 | 57 |
| New P4-001 API tests | 9 |

The new tests cover:

- default engine and config
- 404 for an unknown lot
- semantic fallback (identical to P2-003, with warning)
- health
- the combined analysis response
- a failing category isolated from the rest
- a failing recommendation isolated, and items without OKPD2
- deterministic serialization
- restricted CORS

## Semantic readiness

- READY, with the HNSW index valid.
- Index revision equals the pinned revision `614241f6…`.
- 993,289 texts indexed.
- Model loaded at startup.
- Curated catalog ready (1 seed file).

## Smoke tests (no holdout data)

| Check | Result |
|---|---|
| A `GET /recommendations/5718896` | 200 · `P2_001_SEMANTIC` · semantic_top_k 100 · semantic ran, no warnings · 211 candidates · 20 results, all with reasons and semantic evidence |
| B `GET /market-intelligence/10.51.11.141` | 200 · VERY_HIGH (182 lots, top-1 0.9422) · EXPANSION_RECOMMENDED · 4 VERIFIED + 2 UNDER_REVIEW |
| C `GET /market-intelligence/10.20.25.111` | 200 · LOW (179 lots, top-1 0.1302) · NO_EXPANSION_SIGNAL · no curated external evidence |
| D `GET /procurements/6022687/analysis` | 200 · one response with procurement + recommendations (OK, 20) + market intelligence for 26.20.11.110 and 26.20.18.120 · COMPLETE |
| D `GET /procurements/5956101/analysis` | 200 · 20-item food lot, 18 distinct OKPD2, all 18 entries OK · recommendations OK · 10.51.11.141 = VERY_HIGH, EXPANSION_RECOMMENDED, 4 VERIFIED + 2 UNDER_REVIEW · COMPLETE |

- 6022687 is a golden backup case with no replay overlap.
- 5956101 is not in the replay benchmark.

## Endpoint latency

Five warm calls per route against the running container, after one discarded call each.

| Route | Median ms | Max ms |
|---|---:|---:|
| recommendations/5718896 | 284 | 296 |
| market-intelligence/10.51.11.141 | 67 | 71 |
| market-intelligence/10.20.25.111 | 64 | 86 |
| procurements/6022687/analysis (2 items) | 701 | 838 |
| procurements/5956101/analysis (20 items, 18 codes) | 3,695 | 4,206 |

## Blockers

None.
