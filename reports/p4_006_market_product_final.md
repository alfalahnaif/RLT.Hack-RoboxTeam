# P4-006 — Final Market Product Integration

## Branch and commits

| Item | Value |
|---|---|
| Final branch | `feature/market-product-final`, created from `feature/market-product-backend` @ `dd9861f` |
| Backend commit used | `dd9861f` (P4-005A free-text search + P4-005C sourced contacts) |
| Frontend commit used | `f5b85d6` (`feature/market-product-frontend`) |
| Merge commit | `cfd2c2c`. History preserved; **no textual conflicts** (the frontend branch changed only `frontend/`). |
| Integration fixes | One commit on top of the merge (see below). Tag `hackathon-market-product-final` is on that commit. |
| Untouched tags | `hackathon-demo-freeze`, `hackathon-final-evaluated` |

## Integration fixes (contract, presentation and wording only — no algorithm changes)

1. **Types accept the real P4-005C contract.** `SupplierContact` now includes `sources` (per-field value, `source_url`, `source_authority`, `checked_at`, `address_type`), `identity_basis` and contact `freshness`. All are optional, so older responses still type-check.
2. **Contact presentation.**
   - New compact "Контакты (с источниками)" block. It shows only sourced values (phone, e-mail, website, address); missing fields are simply absent.
   - Each value carries its source label and check date:
     - first-party pages: "Официальный сайт компании" / "Official company website"
     - checko.ru data: "Данные из реестровых сведений о компании" / "Registry-derived company data" (never "official tax registry")
     - a registered legal address is labelled "Юр. адрес"
   - Contact freshness has its own badge (current / may be outdated / unknown), separate from the evidence-check line, which now reads "Evidence checked …". So Можайский shows STALE and Авида UNKNOWN even though the evidence was checked recently.
3. **Why each historical supplier was recommended** is now shown in the UI language. The lines are built from structured evidence: closest supplied product, OKPD2, relevant awards, similar procurements. "Exact OKPD2" appears only when the supplier's code equals the code used for ranking; otherwise it reads "related". The engine's original English reason strings remain under "Evidence details".
4. **Query interpretation** shows all suggested OKPD2 codes with their shares, the OKPD2-vs-text alignment, and whether ranking used a code or text/semantic only.
5. **Pool health** adds the status badge (e.g. "Очень высокая концентрация"), the analyzed OKPD2, the top-supplier share and HHI. These are API values; the formulas are unchanged.
6. **Wording.**
   - Added "«Проверен» означает подтверждённые источники, а не одобрение поставщика и не гарантию пригодности для контракта" / "Verified ≠ vendor approval".
   - The role `MANUFACTURER_ASSERTED_BY_DECLARATION` is labelled "Производитель (по декларации)".
   - The English sample query is now the Russian product text, because the procurement data is Russian.

## Tests

| Suite | Result |
|---|---|
| Backend (`docker compose run --rm backend pytest -q`) | **382 passed** |
| Frontend `npm run typecheck` | pass |
| Frontend `npm run lint` | pass, 0 problems |
| Frontend `npm run build` | pass |

Holdout not run.

## Real browser scenarios

Run against the live stack: `docker compose up -d --build`, frontend `npm run dev`, headless Chrome, real API responses only.

| Scenario | Result |
|---|---|
| A. «Молоко ультрапастеризованное 3.2%» typed into the real form (ru default) | `/ru/results?q=…`; "Как понят запрос"; suggestions 10.51.11.121 59% · 10.51.11.111 13% · 10.51.11 10%; 20 historical supplier cards; price message shown |
| B. Same + OKPD2 10.51.11.141 | Alignment "соответствует" (ALIGNED); pool "Очень высокая концентрация", top supplier 94%, HHI 0.89, "Рекомендуется расширить рынок"; external candidates: **4 "Проверен" + 2 "На проверке"**; Verified ≠ approval note visible |
| C. Same text + 26.20.11.110 (laptops) | Mismatch warning shown; supplied 26.20.11.110 kept and shown; suggestions 10.51.11.* visible; "Ранжирование по тексту и семантике"; first supplier is a milk supplier |
| D. «Молоко питьевое» + 10.51.11.999 | "История категории отсутствует"; 20 suppliers from text search; the page works |
| E. «Ноутбук Acer Aspire 5 A515-57-50R7» | Suggested 26.20.11.110; first supplier card's product is the exact model `a515-57-50r7` |
| English route `/en/results?…` | Renders; "Official company website", "Registry-derived company data" and "Contact data may be outdated" shown |
| Mobile (390 px), results and search pages | No horizontal overflow |

**Quality checks across all scenarios:**
- no failed requests and no HTTP ≥ 400
- no exceptions or `console.error`
- no requests outside localhost
- loading state shown; null contacts render as absent
- no "best price", "cheapest" or price ranking. Only the message "Сопоставимых цен по отдельным поставщикам пока нет." (backend `price_intelligence.available = false`).

## Contacts verified in the UI (milk + 10.51.11.141)

| Candidate | Rendered | Contact freshness |
|---|---|---|
| Переславский МК (7622012124) | https://pervozdannoe.ru/, sales@pervozdannoe.ru, +7-960-530-91-00, legal address д. Лунино (registry-derived label) | Контакты актуальны (FRESH) |
| Бирский КМП (0257011170) | https://molloko.ru/, hello@molloko.ru, +7 (34784) 3-37-78, ул. Интернациональная | FRESH |
| Боровичский МЗ (5320000979) | http://bormoloko.ru/, bormoloko@mail.ru, 8-816-642-8088, ул. Ленинградская, 65 | FRESH |
| ЗСМ «Можайский» (5028002303) | http://mozhayskiy.ru/, sales@mozhayskiy.ru, +7-49638-21052, ул. Мира, д.106 | **Контакты могут быть устаревшими (STALE)** |
| ООО «ААП» (5007126820) | Legal address only, Горки Сухаревские (registry-derived); no phone, e-mail or website shown | address only |
| ЗАО МК «Авида» (3128004452) | info@mk-avida.ru, (4725)42-93-28, Старый Оскол | **Актуальность контактов неизвестна (UNKNOWN)** |

Verification statuses are unchanged: 4 VERIFIED, 2 UNDER_REVIEW.

Historical suppliers and external candidates are shown in separate sections with separate headings.

## Export verified

- The UI section "Экспорт для CRM / ERP / SRM" has JSON and CSV links built from the API's `export_url`. Both were fetched from the page.
- CSV: 26 rows (20 historical + 6 external). Columns include `inn`, `score`, `role`, `role_evidence_status`, `phone`, `email`, `website`, `address`, freshness, `reasons`, `evidence_summary`, `contact_checked_at`, `contact_freshness_status`, `contact_sources`. Бирский's e-mail and Можайский's STALE are present.
- JSON: 26 records.
- No native SAP / Salesforce / 1C integration is claimed. The REST API and OpenAPI (`http://localhost:8000/openapi.json`, `/docs`) remain available (HTTP 200).

## Lot-ID regression

| Lot | Result |
|---|---|
| 5956101 | COMPLETE ("Пул поставщиков сильно сконцентрирован"), 5.3 s |
| 5718896 | COMPLETE ("Лучшая рекомендация"), 1.0–1.1 s |

No errors or partial warnings. "Анализ закупки" stays in the top navigation as the secondary workflow.

## User-visible latency (warm, from action to rendered results)

| Search | Time |
|---|---|
| Milk, text-only (typed + submit) | 0.8–1.7 s |
| Milk + 10.51.11.141 | 1.5–1.7 s |
| Acer technical query | 1.2–1.3 s |

## Blockers

None.
