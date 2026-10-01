# Supplier Radar (RLT.Hack 2026)

Evidence-based supplier discovery for public procurement. Project knowledge base: [`docs/README.md`](docs/README.md) ·
authoritative plan: [`docs/HACKATHON_EXECUTION_BASELINE.md`](docs/HACKATHON_EXECUTION_BASELINE.md).

## Run the product backend (existing database volume — short path)

```bash
docker compose up -d --build         # postgres (pgvector) + api: `alembic upgrade head` (no-op at head), then FastAPI
curl http://localhost:8000/api/v1/health      # api / postgres / semantic READY + pinned revision / curated catalog
```

- API base URL: `http://localhost:8000/api/v1` (port `API_PORT`, default 8000); OpenAPI docs at `http://localhost:8000/docs`.
- Routes: `GET /health`, `GET /recommendations/{lot_id}`, `GET /procurements/{lot_id}/analysis`,
  `GET /market-intelligence/{okpd2}`.
- Startup never builds embeddings. When the semantic index is READY the pinned model is loaded once at startup (~6 s);
  otherwise the API still starts and recommendations fall back to P2-003 with a `SEMANTIC_UNAVAILABLE` warning.
- Frontend: the Next.js client calls `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api/v1`) from the browser with
  `NEXT_PUBLIC_API_MODE=live`; CORS allows only `http://localhost:3000` and `http://127.0.0.1:3000` (override with `CORS_ORIGINS`;
  `*` is ignored), GET only.

## Fresh environment bootstrap (new machine / empty volume — one-off, hours)

Run the steps below once, in order: ingest (~15–20 min) → `search build-stats` (~1 min) → `semantic download-model` →
`semantic build` (~3.4 h on CPU, resumable) → `docker compose up -d api`. Until `semantic build` finishes, the API serves
P2-003 recommendations with a `SEMANTIC_UNAVAILABLE` warning.

## Database from scratch (Docker only — no local PostgreSQL needed)

Prerequisites: Docker Desktop (Compose v2) and the three organizer CSVs in `data/raw/`
(`Извещения_24-25.csv`, `Поставщики_24-25.csv`, `ТРУ_24-25.csv`; SHA-256 pinned in `reports/dataset_profile.json`).

```bash
cp .env.example .env                 # optional: override DB name/user/password/port (defaults work for local dev)
docker compose up -d postgres        # PostgreSQL 16 + named volume postgres_data
docker compose ps                    # wait for "(healthy)"
docker compose build backend         # Python 3.11 image: alembic, psycopg 3, pytest
docker compose run --rm backend alembic upgrade head                       # schema v0.2.0 + pg_trgm
docker compose run --rm backend pytest                                     # unit + DB integration tests (uses <db>_test)
docker compose run --rm backend python -m app.cli ingest organizer /data/raw   # full load (~15–20 min), writes reports/ingestion_report.*
docker compose run --rm backend python -m app.cli ingest-status            # read-only reconciliation
docker compose run --rm backend python -m app.cli search build-stats       # IDF snapshot (lots before 2024-07-01), ~1 min
docker compose run --rm backend python -m app.cli semantic download-model  # download EXACTLY the model@revision in backend/semantic_model.lock.json (never rewrites it)
docker compose run --rm backend python -m app.cli semantic build           # embed new texts, validate, HNSW + READY stamp (resumable; fails closed on revision mismatch -> --reembed)
docker compose run --rm backend python -m app.cli semantic status          # embedded / pending texts, index present
docker compose run --rm backend python -m app.cli recommend lot 5718896 --top-k 10 --explain   # recommendation (DEFAULT_CONFIG = P2-001)
docker compose run --rm backend python -m app.cli evaluate baseline          # DEV + warm-up replay evaluation (holdout sealed)
docker compose run --rm backend python -m app.cli evaluate semantic          # P2-001 DEV experiments (S0–S4), then semantic-latency, semantic-report
```

- `data/raw` is mounted **read-only** at `/data/raw`; the CSVs are never copied into the image. Ingestion stops with
  `reports/source_drift_report.json` if a file hash differs from the pinned P1-001A hash.
- Re-running the ingest command with the same files is a verify-only no-op; `--force` re-processes idempotently (0 new rows);
  `--reset-organizer-data` replaces organizer data only (enrichment tables untouched); `--dry-run` normalizes without writing.
- `docker compose down` keeps the database; **only `docker compose down -v` deletes the `postgres_data` volume.**
- Git Bash on Windows: prefix commands with `MSYS_NO_PATHCONV=1` so `/data/raw` is not rewritten to a Windows path.

Details: [`docs/domain/DATA_MAPPING.md`](docs/domain/DATA_MAPPING.md) §11 (ingestion), §10 (normalization).
