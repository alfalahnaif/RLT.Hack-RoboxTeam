# P4-002 — Demo-Ready Frontend Integration

## Primary demo lot: 5956101

- Every non-holdout lot that contains OKPD2 10.51.11.141 has at least 11 items, so no 1–5 item case exists. I checked the 20 smallest such lots through the live `/analysis` API; all 20 return COMPLETE with VERY_HIGH, EXPANSION_RECOMMENDED and 4 VERIFIED + 2 UNDER_REVIEW.
- No candidate was clearly simpler or faster. The smallest ones (5381843 with 11 items, 5372920 with 12) still took 2.9–4.1 s and use older history (2024-11).
- **5956101** is kept as the primary case:
  - AIS GZ, 2025-11-24, 20 items, 18 OKPD2 codes
  - latest history cutoff, 33 candidate suppliers
  - not in the replay benchmark
  - COMPLETE analysis in ~3.7 s at the API, ~4.7 s until the page has rendered

## Fallback lot: 5718896

The golden recommendation case: laptops, one item, OKPD2 26.20.11.110. Page renders in ~0.8 s.

## Frontend files changed

New:
- `frontend/src/app/[locale]/(app)/analysis/page.tsx`
- `frontend/src/features/analysis/analysis-screen.tsx`
- `frontend/src/features/analysis/overview.tsx`
- `frontend/src/features/analysis/procurement-summary.tsx`
- `frontend/src/features/analysis/supplier-list.tsx`
- `frontend/src/features/analysis/market-section.tsx`
- `frontend/messages/{ru,en}/analysis.json`
- `frontend/.env.development` and `frontend/.env.production` (`NEXT_PUBLIC_API_MODE=live`, base URL `http://localhost:8000/api/v1`; no secrets)

Modified:
- `frontend/src/lib/api/types.ts`: analysis DTOs and two error codes
- `frontend/src/lib/api/client.ts`:
  - adds `api.analysis` (one shared request per lot while in flight)
  - maps FastAPI `detail` errors to `ApiError`
  - adapts `/health` for the status pill
- `frontend/src/features/shell/app-frame.tsx`: Analysis nav item; live mode shows only screens backed by the live API
- `frontend/src/app/[locale]/page.tsx`: `/` opens Analysis in live mode
- `frontend/src/config/ui.ts`: `DEMO_LOTS`
- `frontend/src/i18n/request.ts`: `analysis` namespace
- `frontend/messages/{ru,en}/{shell,vocab}.json`
- `frontend/.gitignore`: allows the two env files
- `docs/product/SCREENS.md`: S-06

The backend is unchanged: the integrated response already carries `market_intelligence_as_of` and `external_expansion.evidence_checked_at`.

## Final demo flow

1. `docker compose up -d --build` (backend), then `npm run dev` in `frontend/`.
2. Open `http://localhost:3000` (redirects to `/ru/analysis`; `/en/analysis` for English).
3. Click **Primary demo · lot 5956101**, or type a lot ID and press **Analyze**. A staged loading card shows: items → suppliers → pool → external.
4. The page then shows, top to bottom:
   - the procurement summary
   - three overview tiles: 33 recommended suppliers, 1 concentrated category (10.51.11.141), 4 verified external candidates
   - **"Historical procurement evidence as of 2025/11/24"**, shown separately from **"External evidence checked 2026/10/01"**
   - recommended suppliers (top 5, expandable to 20; top recommendation highlighted). Each has a score and human-readable reasons. "Why this supplier" opens counts, the score breakdown, evidence lots, and a collapsed **"Additional semantic evidence"** section.
   - supplier pool health, one accordion per OKPD2 with priority categories first. For 10.51.11.141: "Supplier pool is highly concentrated", top supplier share 95%, HHI 0.90, "Market expansion recommended".
   - historical alternatives and external market expansion, side by side. The external section shows 4 **Verified** + 2 **Under review** candidates, each with role, evidence strength, evidence basis, review points and source links, plus the line "Sources support the product type; they do not assert this exact OKPD2 code".

## API used

`GET /api/v1/procurements/{lot_id}/analysis` is the only request for page data, made once per page load. `GET /api/v1/health` feeds the status pill.

## Pages and screenshots

- Pages:
  - `/ru/analysis` and `/en/analysis` (initial state)
  - `/{locale}/analysis?lot=5956101` (primary)
  - `?lot=5718896` (fallback)
  - `?lot=99999999` (not found)
- Screenshots checked at 1440 px and 390 px:
  - primary top
  - pool health
  - "Why this supplier" with semantic evidence expanded
  - external candidates
  - not found
  - Russian
  - fallback
  - mobile
- The screenshots are not committed because they contain supplier INNs.

## Tests and build

Commands (all pass):

- `npm run typecheck`
- `npm run lint`: 0 errors; 1 warning that predates this task (unused `DemoNotice`)
- `npm run build`

Browser checks against the real stack, in headless Chrome:

| Check | Result |
|---|---|
| Shortcut fires the real API call | URL becomes `?lot=5956101`; loading state seen |
| Primary page content | All sections render; 4 "Verified" + 2 "Under review" badges; VERY_HIGH and expansion recommended; both date labels present |
| Semantic evidence placement | Not in the headline reasons; present and expandable under "Why this supplier" (shows similarity, lot, date, OKPD2) |
| External evidence | Source links render |
| Not found | Not-found state, no crash |
| Russian | Renders |
| Fallback | Renders |
| Mobile, 390 px | No horizontal overflow |

Warm time until the page has rendered:

| Lot | Times (s) |
|---|---|
| 5956101 | 5.01, 4.72, 4.80, 4.64 |
| 5718896 | 0.80, 0.76, 0.97, 0.75 |

No holdout data was used.

## Actual blockers

None.
