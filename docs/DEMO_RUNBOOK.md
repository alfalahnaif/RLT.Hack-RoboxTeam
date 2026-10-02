# Supplier Radar — Demo Runbook

Frozen build: branch `integration/hackathon-final`, tag `hackathon-final-evaluated`, plus the demo-freeze commit (see `reports/p4_004_demo_freeze.md`).
No Internet is needed during the demo: the database, the 993,289 embeddings, the e5-small model (Docker volume `models`) and the frontend fonts (`frontend/.next`) are all local.
Do not run `docker compose down -v`, and do not delete `frontend/.next`.

| What | URL |
|---|---|
| Supplier Radar (frontend) | http://localhost:3000 |
| Backend health | http://localhost:8000/api/v1/health |

## A. Before the presentation (about 5 minutes)

1. Start Docker Desktop. Then, from the repository root:
   ```bash
   docker compose up -d --build
   ```
2. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open http://localhost:8000/api/v1/health. Expect:
   - `"status": "ok"`
   - `semantic.status = "ready"`
   - `hnsw_ready: true`
   - `model_loaded: true`
   - `curated_evidence_catalog.status = "ready"`
4. Open http://localhost:3000/en/analysis?lot=5956101 once and wait for the page (~5 s). This warms the browser and the app.
5. Click **Analysis** in the top bar to return to the empty input screen. For a Russian demo, use `/ru/analysis`.

## B. Live demo flow (lot 5956101)

1. Open Supplier Radar: http://localhost:3000.
2. Click **Primary demo · food supply, lot 5956101** (or type `5956101` and press **Analyze**). The staged loading takes about 4–5 s.
3. **Procurement summary:** food supply for a social canteen, 20 items, 18 OKPD2 categories. Point to the two dates: *historical procurement evidence as of 2025/11/24* versus *external evidence checked 2026/10/01*.
4. **Recommended suppliers:** 33 candidates from historical procurement data. The top recommendation is highlighted.
5. Open **Why this supplier** on #1. Show the matching products, OKPD2, relevant awards, prior work for this customer and the score breakdown. Semantic evidence sits in a collapsed secondary section.
6. **Supplier pool health:** the milk category, 10.51.11.141, is listed first.
7. Point out the VERY_HIGH concentration: "Supplier pool is highly concentrated". The top supplier holds about 95% of observed awards, HHI is 0.90, and the signal is **Market expansion recommended**.
8. **Historical alternatives:** other suppliers already seen in this category in procurement history.
9. **External market expansion:** new suppliers found outside the procurement data.
10. Show the **4 Verified + 2 Under review** candidates, with their roles, evidence basis and open review points.
11. Open **Evidence** on a candidate to show the source link and the check date. Point out the wording "Sources support the product type; they do not assert this exact OKPD2 code" and "Candidates are leads for market research, not suppliers approved for award".

## C. Fallback

If the large case is slow, click **Recommendation example · laptops, lot 5718896** (renders in about 1 s).

## D. Recovery

```bash
curl http://localhost:8000/api/v1/health      # backend health
docker compose restart api                    # restart the API (~20 s until healthy)
docker compose up -d                          # start anything that stopped (postgres + api)
```

Frontend: stop it with Ctrl+C in its terminal, then run `npm run dev` in `frontend/` again.
