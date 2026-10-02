# P5-001C — Supplier 360 final integration

End-to-end Supplier 360: the P5-001B frontend now runs against the real P5-001A API. A user can search for a supplier, open its
profile, and see legal identity, market-role evidence, observed procurement history, contacts, freshness and source provenance.
On-demand enrichment of a not-yet-enriched supplier works from the profile.

## Commits

| Component | Branch | Commit |
|---|---|---|
| Backend (P5-001A final) | `feature/supplier-enrichment-backend` | `5127995` |
| Frontend (P5-001B) | `feature/supplier-360-frontend` | `8a6838c` |
| Merge | `integration/supplier-360` | `4c3845c` |
| Integration changes | `integration/supplier-360` | `aea3a4a` |

No backend code was changed. Untouched: recommendation ranking, semantic retrieval, the final HOLDOUT (not re-run), migration 0004,
the main `supplier_radar` database (still at 0004), and every existing tag.

## Real API contract

The real responses of `GET /api/v1/suppliers/{inn}/profile` and `POST /api/v1/suppliers/{inn}/enrich` were captured from
`supplier_radar_p5` and compared with the P5-001B TypeScript types. The fields and enums match exactly (P5-001B was built from
`backend/app/api/supplier_profile_models.py`), so no type change was needed. Four real legal-entity responses are now contract
fixtures (`frontend/tests/fixtures/p5_profile_*.json`). The tests check their top-level keys and how the UI reads them.

Changes made because of real data:

| Real data | Frontend change |
|---|---|
| All 30 pilot profiles are `PARTIAL` + `retryable` (checko.ru rate-limited; website discovery has no hint) | PARTIAL is shown as a valid result (info tone, "this is an expected result, not an error"). The action is a cache-first "Refresh profile". Only `FAILED` + retryable forces `refresh=true`. |
| No phone, e-mail or website for historical suppliers; EGRUL legal address only | "Verified contact information has not yet been discovered.", with an explanation. The EGRUL address is still shown. No placeholders. |
| Individual entrepreneurs: no address, no contacts | "Not published for individual entrepreneurs"; "Contacts of individual entrepreneurs are not collected (personal data)". |
| `platforms` keys are `AIS_GZ` / `EM` | Labels "АИС ГЗ" / "ЭМ" ("AIS GZ" / "e-shop (EM)"). |
| `SUPPLIER/VERIFIED` comes from procurement awards; most suppliers have no manufacturer/distributor evidence | Shown as "Supplier — from procurement history", separate from market-role evidence. An explicit "Manufacturer / distributor role unknown" appears when there is none. |
| `last_run_attempts` shows checko RATE_LIMITED / SKIPPED next to EGRUL OK | "Last enrichment run" list, with a note that the secondary provider is optional. |
| Enrichment tables exist only in `supplier_radar_p5`, which has no search indexes | Optional `NEXT_PUBLIC_SUPPLIER_PROFILE_API_BASE_URL` (defaults to the main API). See the limitations section. |

After a successful `POST …/enrich`, the screen re-reads `GET …/profile`, as required. It falls back to the POST body only if that
read fails.

**Source transparency.** Every source, contact and identity line carries a provenance class:

- **Official FNS registry:** `FNS_EGRUL`, `FNS_EGRUL_EXTRACT`.
- **Company website:** `FIRST_PARTY`.
- **Optional secondary provider — not an official registry:** checko.ru / `FNS_EGRUL_DERIVED_REGISTRY`.
- **Historical procurement evidence:** organizer data.
- **Curated regulatory evidence:** the declaration registry mirror.

## Tests

| Check | Result |
|---|---|
| Backend `pytest` (tools image, integration code, throwaway `supplier_radar_test` DB) | **439 passed** |
| Frontend `npm test` (view model + real-contract snapshots) | **16 passed** |
| Frontend `npm run typecheck` | pass |
| Frontend `npm run lint` | pass |
| Frontend `npm run build` (production) | pass |

The first backend run showed 12 errors and 1 failure. They came from the test container: `reports/` was not mounted
(`FileNotFoundError: /srv/reports/dataset_profile.json`). Re-run with the same mounts as `docker-compose.yml` (a scratch copy of
`reports/`): 439 passed.

## Real browser acceptance

**Setup.** Integration code, production frontend build on `:3107`, headless Chrome (CORS enforced) over DevTools; 390 px checks
use device-metrics emulation (headless `--window-size` cannot go below 504 px).

- **Search API:** `:8002`, main `supplier_radar` (semantic READY). Started with `uvicorn` only, never `alembic upgrade`.
- **Supplier 360 API:** `:8001`, `supplier_radar_p5`.
- **Owner's servers:** the demo API `:8000` and the dev server `:3000` were not touched.

Every case was checked for:

- failed requests;
- HTTP ≥ 400, other than the expected 422/404 in F/G;
- `console.error` and exceptions;
- requests outside localhost;
- horizontal overflow at 1366 px and 390 px.

All 19 cases pass. Raw results: `reports/p5_001c_acceptance.json`.

### Main flow

| Step | Result | User-visible latency (warm) |
|---|---|---|
| Free-text search «Молоко ультрапастеризованное 3.2%» | 20 historical cards, each with "Профиль поставщика" (real INN) | 0.83–0.96 s |
| Open Supplier 360 from the first card | Legal identity, official address + OKVED, role section, observed history, sources (expanded): all visible | 0.34 s |
| Back button | Returns to the same results (`?q=` kept) | 0.44 s |

### Supplier 360 cases

| Case | Supplier | Verified on screen | Load |
|---|---|---|---|
| A. Enriched legal entity, address + OKVED | 7804054351 АО «Артис-Детское питание» | <ul><li>Full and short name, INN, OGRN, KPP, "Действующая", registration date, region, EGRUL address, OKVED 56.29.2</li><li>PARTIAL shown as expected</li><li>Contact-absence message</li><li>History «Наблюдаемая…», АИС ГЗ / ЭМ</li><li>checko labelled optional</li><li>No placeholders</li></ul> | 0.37 s |
| B. Individual entrepreneur, address intentionally absent | 12-digit INN (pilot) | "Индивидуальный предприниматель"; "Не публикуется для индивидуальных предпринимателей"; IP-contacts note; OKVED shown | 0.24 s |
| C. Role evidence | 7810687137 ООО «БСС» | "Дистрибьютор — Предположение" (inferred from OKVED, dashed, weaker than verified); "Поставщик — по истории закупок"; no manufacturer | 0.46 s |
| D. No market-role evidence | 7804054351 | "Роль производителя или дистрибьютора не установлена" in the header and the role section; no manufacturer or distributor | 0.36 s |
| E. NOT_ENRICHED → POST → refresh | 7814580307 (not in benchmark/holdout) | <ul><li>Before: INN shown as the title, "ещё не обогащён"</li><li>Click «Обогатить профиль»: loading state</li><li>Requests: `GET /profile` → `POST /enrich` → `GET /profile`</li><li>After: ООО «КАРДАН», PARTIAL, EGRUL identity + address + OKVED</li><li>checko RATE_LIMITED (optional), EGRUL OK</li></ul> | load 0.24 s; **enrichment 16.1 s** |
| F. Invalid INN | 12345 | "Поставщик не найден" + 10/12-digit explanation (API 422 `INVALID_INN`) | 0.25 s |
| G. Not found | 1234567890 | "Поставщик не найден" + INN message (API 404 `SUPPLIER_NOT_FOUND`) | 0.24 s |
| H. Curated external candidate | 7622012124 ООО «Переславский молочный комбинат» | <ul><li>Same profile screen</li><li>"Внешний кандидат", "Производитель — Подтверждено" (curated P3-002B)</li><li>Curated phone / e-mail / website</li><li>Address marked "Дополнительный провайдер — не официальный реестр"</li><li>"Not in procurement data" history text</li></ul> | 0.23 s |
| English route | `/en/supplier-360/7810687137` | "Supplier profile", "Legal identity", "Distributor — Inferred", "Verified contact information has not yet been discovered.", "Official FNS registry" | 0.46 s |

Enrichment (E) is synchronous and makes live calls to egrul.nalog.ru. That includes downloading the official extract and one
bounded backoff after checko answered 429. Before the run, checko was probed once (429). It was called for this one supplier
only, behind the circuit breaker.

### Regression (main search API, `supplier_radar`)

| Case | Result | Load |
|---|---|---|
| Free-text search (ru) | Interpretation + historical suppliers | 0.56 s |
| Explicit OKPD2 10.51.11.141 | "соответствует"; external candidates "Проверен" | 0.78 s |
| Mismatch 26.20.11.110 | Mismatch warning | 0.67 s |
| Unknown OKPD2 10.51.11.999 | "История категории отсутствует"; page works | 0.70 s |
| Acer «Ноутбук Acer Aspire 5 A515-57-50R7» | 26.20.11.110 suggested; exact model `a515-57-50r7` on a card | 0.68 s |
| English results route | Renders; "View supplier profile" on cards | 0.56 s |
| Lot-ID 5956101 | Recommended suppliers + profile links | 4.7 s |
| Lot-ID 5718896 | Recommended suppliers | 0.68 s |
| CSV / JSON export | Both links on the page return 200 with content | — |
| Mobile 390 px | No horizontal overflow on any page above (after the fix below) | — |

**Regression found and fixed.** At 390 px, the explicit-OKPD2 results page overflowed by 212 px. The cause was in the P4-006
external-candidate cards: the API's `why_candidate` text contains long unbroken codes (`MAIN_OKVED_IS_RESTAURANT_OR_FO…`), which
forced a ~550 px minimum width. These texts, and evidence claims in `EvidenceItem`, now wrap (`overflow-wrap: anywhere`). After the
fix, no page overflows.

### Screenshots

Saved in `reports/p5_001c_screenshots/`:

- `flow-profile-1366.png`, `flow-profile-390.png` — profile opened from search
- `case-A-1366.png`, `case-C-1366.png`, `case-D-390.png`, `case-H-390.png`, `case-EN-1366.png`
- `case-E-before-390.png`, `case-E-after-1366.png`
- `case-F-390.png`, `case-G-390.png`
- `reg-R2-390.png` (after the overflow fix), `reg-R7-1366.png`

Case B screenshots are not stored, because they show an individual entrepreneur's name.

## Known limitations

- **Automated official website/email/phone discovery for historical suppliers is not yet generalized. The current legal enrichment remains useful without it.** In the EGRUL-first pilot, website, phone and e-mail are unavailable for the historical suppliers. The UI states this as an intentional absence. Website discovery still depends on the optional checko.ru hint, which is rate-limited (HTTP 429).
- **Two databases.** The enrichment tables (migration 0005) exist only in `supplier_radar_p5`, which has no search indexes (`lexeme_stats`, `semantic_text` empty). The main `supplier_radar` stays at 0004 by design. The demo therefore runs two API instances of the same code, and the frontend sends profile calls to the P5 instance via `NEXT_PUBLIC_SUPPLIER_PROFILE_API_BASE_URL`. A single deployment needs migration 0005 on the main database, which is an owner decision. After that, the variable is simply left unset.
- **Enrichment latency.** On-demand enrichment is synchronous: about 16 s in the real run, including the official extract and one backoff after checko's 429. The UI shows a progress state, and no second run is started while one is in progress.
- **English evidence text.** Evidence and role `claim` texts are produced in English by the backend. Labels around them are localized, but the claim text itself is shown as returned.
- **Enrichment pilot scope.** Only 30 pilot suppliers, plus the supplier enriched in case E, are enriched in `supplier_radar_p5`. Every other historical supplier opens as NOT_ENRICHED, with the enrich action.
- **Curated candidates keep their curated data.** The six curated external candidates show their P4-005C contacts and P3-002B roles. Their legal identity block stays empty until they are enriched; the enrich action is available.
- **Committed config.** `frontend/.env.*` still point at `:8000` without a profile base URL. The integration build used environment overrides only.

## How to reproduce

```sh
# APIs (no alembic; integration code mounted read-only)
docker run -d --name sr-int-api-p5   --network supplier-radar_default -p 8001:8000 -e DATABASE_URL=postgresql://supplier_radar:supplier_radar_dev@postgres:5432/supplier_radar_p5 -e REPO_ROOT=/srv -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e CORS_ORIGINS=http://localhost:3107 -v <repo>/backend:/srv/backend:ro -v <repo>/data/seed:/srv/data/seed:ro -v supplier-radar_models:/models -w /srv/backend supplier-radar-backend uvicorn app.api.main:app --host 0.0.0.0 --port 8000
docker run -d --name sr-int-api-main --network supplier-radar_default -p 8002:8000 -e DATABASE_URL=postgresql://supplier_radar:supplier_radar_dev@postgres:5432/supplier_radar    -e REPO_ROOT=/srv -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e CORS_ORIGINS=http://localhost:3107 -v <repo>/backend:/srv/backend:ro -v <repo>/data/seed:/srv/data/seed:ro -v supplier-radar_models:/models -w /srv/backend supplier-radar-backend uvicorn app.api.main:app --host 0.0.0.0 --port 8000
# frontend
cd frontend
NEXT_PUBLIC_API_MODE=live NEXT_PUBLIC_API_BASE_URL=http://localhost:8002/api/v1 NEXT_PUBLIC_SUPPLIER_PROFILE_API_BASE_URL=http://localhost:8001/api/v1 npm run build
npx next start -p 3107
```
