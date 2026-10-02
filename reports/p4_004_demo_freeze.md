# P4-004 — Final Demo Freeze

## Branch, commit and tag

- **Branch:** `integration/hackathon-final`. It contains the backend integration (P4-001), the frontend integration (P4-002) and the evaluation reports (P4-003).
- **Evaluated system:** tag `hackathon-final-evaluated` → `417eff2`.
- **Demo-freeze commit:** on top of `417eff2`, tagged `hackathon-demo-freeze`. It contains operational changes only:
  - `docker-compose.yml`: `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` for the `api` service
  - `docs/DEMO_RUNBOOK.md`
  - this report
- **Unchanged:** retrieval, ranking, the S3 semantic configuration, pool-health formulas, verification decisions, the holdout script and its results, and the frontend.

## Startup commands

```bash
docker compose up -d --build          # postgres (pgvector) + api: migrations no-op, FastAPI :8000, model loaded at startup
cd frontend && npm run dev            # Supplier Radar on :3000 (live API mode via the committed .env.development)
```

| What | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend health | http://localhost:8000/api/v1/health |

Recreating the API with `docker compose up -d --build` took 20 s until healthy.

## Health result

`GET /api/v1/health`:

- `status: ok`, `api: ready`, `postgres: reachable`
- semantic `ready`, `hnsw_ready: true`, `model_loaded: true`, index revision = pinned revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 993,289 texts
- curated evidence catalog `ready` (1 seed file)

## Primary demo — 5956101: ready

Browser run of the live flow (headless Chrome, shortcut button → rendered page in **4.4 s**). All expected elements present:

- procurement summary
- **33 candidates**
- OKPD2 **10.51.11.141**
- **VERY_HIGH** ("Supplier pool is highly concentrated")
- top supplier share **95%**
- HHI **0.90**
- **Market expansion recommended**
- **4 Verified + 2 Under review** badges
- historical alternatives and the external market expansion section
- source links in the external evidence
- separate labels for the two dates: "Historical procurement evidence as of 2025/11/24" and "External evidence checked 2026/10/01"
- the disclaimer that candidates are not approved for award

"Why this supplier" opens. Semantic evidence is collapsed by default and absent from the headline reasons.

No research terms are visible: DEV, HOLDOUT, S3, MRR and nDCG do not appear.

Problems found: none. That means no exceptions, no `console.error`, no failed requests, no HTTP ≥ 400 and no requests outside localhost. Styles loaded (Inter, card styling). No horizontal overflow at 1440 px, or at 390 px in Russian.

## Fallback demo — 5718896: ready

- Rendered in **0.9 s**; recommendations and pool health shown; analysis COMPLETE (no partial warning).
- No errors, no failed requests, no overflow.
- API: HTTP 200, COMPLETE.

## Local semantic and model readiness

| Item | Status |
|---|---|
| Docker volumes | `supplier-radar_postgres_data` and `supplier-radar_models` exist |
| Embeddings | `semantic_text`: 993,289 rows, 993,289 embeddings, 1 model revision; HNSW READY (no rebuild) |
| Model cache | pinned `intfloat/multilingual-e5-small` in the `models` volume (`/models/hf`, 2.2 GB) |
| Offline load test | a container with `--network none` loaded the model and encoded text in 7.2 s (DNS to huggingface.co failed, confirming no network) |
| API offline mode | runs with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`; no Hugging Face or download lines in the API logs |
| Curated seed | `data/seed/p3_002b_evidence_seed.json` mounted at `/srv/data/seed` |
| Frontend | `NEXT_PUBLIC_API_MODE=live`, base URL `http://localhost:8000/api/v1`; Inter font files cached locally in `frontend/.next/dev` |

## Blockers

None.

**DEMO READY**
