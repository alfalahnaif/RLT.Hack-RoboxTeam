# P4-005C — Source-Backed Contact Enrichment (six curated candidates, OKPD2 10.51.11.141)

## Scope and data

- **Branch:** `feature/market-product-backend`. Only the six curated external candidates are in scope.
- **Record:** `data/seed/p4_005c_contact_enrichment.json`, validated by `backend/app/enrichment/contacts.py`.
  - It sits next to the curated evidence seed and is not used by verification.
  - Each populated field stores `value`, `source_url`, `source_authority` and `checked_at`. Addresses also store `address_type`.
- **Check date:** all pages were checked on 2026-10-02 (`checked_at` 2026-10-02T03:55:00+03:00). Every stored value was re-checked to appear verbatim on its cited page.

## Sourcing rules applied

- **Sources:**
  - Contact values come from the company's own website.
  - A current FNS/EGRUL-derived registry record (checko.ru) was used only for two things: to confirm that a website belongs to the INN, and for the registered legal address when the company publishes no postal address.
  - No directory listings were used as contact sources.
- **What was not recorded:**
  - No e-mail patterns were inferred and no phone numbers were composed.
  - Named employees' personal e-mails and mobile numbers were skipped; only general or department contacts were kept.
- **Freshness of contact data:** it describes the page itself.
  - An outdated page is **STALE** even though it was checked today.
  - An undated page is **UNKNOWN**.
  - Otherwise **FRESH** if checked within 180 days.
- **Verification statuses are unchanged:** 4 VERIFIED, 2 UNDER_REVIEW. Contact evidence and product/role evidence are separate.

## Results by candidate

| Company / INN | Verification (unchanged) | Fields found | Fields not found | Source type | Identity basis | Contact freshness |
|---|---|---|---|---|---|---|
| ООО «Переславский молочный комбинат» / 7622012124 | VERIFIED | website https://pervozdannoe.ru/, e-mail sales@pervozdannoe.ru, phone +7-960-530-91-00, address 152020, Ярославская область, Переславский район, д. Лунино, ул. Центральная, д. 13 | — | website, e-mail, phone: first-party (pervozdannoe.ru/contact/). Address: FNS-derived registry, registered legal address (the website gives no postal address) | Registry record for this INN lists the same phone and the pervozdannoe.ru e-mail domain | FRESH (site © 2026) |
| ООО «Бирский комбинат молочных продуктов» / 0257011170 | VERIFIED | website https://molloko.ru/, e-mail hello@molloko.ru, phone +7 (34784) 3-37-78, address Россия, Республика Башкортостан, г. Бирск, ул. Интернациональная, д .163 | — | First-party (molloko.ru/contacts/) | Site address = registered legal address of the INN | FRESH (© 2016-2026, 2025 news) |
| АО «Боровичский молочный завод» / 5320000979 | VERIFIED | website http://bormoloko.ru/, e-mail bormoloko@mail.ru, phone 8-816-642-8088, address Россия, 174411 Новгородская обл, г. Боровичи, ул. Ленинградская, 65 | — | First-party (bormoloko.ru) | Site address = registered legal address of the INN | FRESH (shareholder-meeting notice for 10 April 2026) |
| ЗАО ЗСМ «Можайский» / 5028002303 | VERIFIED | website http://mozhayskiy.ru/, e-mail sales@mozhayskiy.ru, phone +7-49638-21052, address РФ, Московская область Можайск, ул. Мира, д.106 | — | First-party (mozhayskiy.ru/Contact.html) | Site address = registered legal address of the INN | **STALE** — page © 2011, latest news dated 2 April 2012 |
| ООО «ААП» / 5007126820 | UNDER_REVIEW | address 141865, Московская область, м. о. Дмитровский, д. Горки Сухаревские, д. 67, стр. 5 | website, e-mail, phone (no company website found; registry-aggregator phones/e-mails not used) | FNS-derived registry, registered legal address | Registry record for this INN (active company) | FRESH (current registry record; address only) |
| ЗАО МК «Авида» / 3128004452 | UNDER_REVIEW | website https://xn----8sbahkxkp.xn--p1ai/ (мк-авида.рф), e-mail info@mk-avida.ru, phone (4725)42-93-28, address Россия, 309504, Белгородская обл. г. Старый Оскол, Промкомзона (район авторынка) | — | First-party (мк-авида.рф/kontakty/) | The contacts page prints ИНН 3128004452 in its requisites | **UNKNOWN** — page © 2012, news items without a year |

## API integration

- **Contact contract:** extended additively. `phone`, `email`, `website` and `address` stay as before, and three fields are new:
  - `sources` — per-field provenance
  - `identity_basis`
  - `freshness` — contact freshness, separate from the evidence `freshness`
- **Where it appears:** in `POST /api/v1/supplier-search` (external candidates, and any historical supplier whose INN has a record), and in the JSON/CSV export. The CSV adds three columns: `contact_checked_at`, `contact_freshness_status`, `contact_sources`.
- **Unchanged:** the P3 `/market-intelligence` and lot-ID `/procurements/{lot_id}/analysis` contracts. Retrieval, ranking, pool-health formulas and verification are also unchanged.

## Tests

**382 passed** (374 before + 8 in `tests/api/test_contact_enrichment.py`; 2 P4-005A contact tests updated to the enriched contract). The new tests cover:

- the record covers exactly the six INNs
- unsourced or unknown fields and authorities are rejected
- freshness semantics: FRESH; STALE when the check is old; STALE when the page is outdated; UNKNOWN when undated
- sourced fields serialize with source URL, authority and `checked_at`
- missing fields remain null (ООО «ААП»)
- verification statuses and the P3 candidate payload are unchanged
- supplier-search response and CSV export include the contacts
- lot-ID analysis unchanged (4/2, no contact in the P3 contract)

Holdout not run.
