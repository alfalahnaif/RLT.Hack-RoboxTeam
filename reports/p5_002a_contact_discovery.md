# P5-002A — Automated official website & contact discovery

Historical suppliers now get candidate websites without Checko. Each candidate is checked against the official EGRUL identity on
the site itself, and public business phones and e-mails are taken only from verified sites. Sources and freshness are kept for
every value. Supplier 360 shows the results with no new profile contract.

**Branch:** `feature/p5-002a-contact-discovery`, built from `integration/supplier-360`. The P5-001A backend reference is
`5127995` and the P5-001C reference is `03b2346`.

**Untouched:** recommendation ranking, semantic retrieval, S3, HOLDOUT (not re-run), pool health, curated external
verification decisions, and the main `supplier_radar` database (still at migration 0004). Migration 0006 is applied only to the
enrichment database `supplier_radar_p5`.

Raw results: `reports/p5_002a_contact_discovery.json` (golden set, pilot and browser runs) and `reports/p5_002a_pilot.json`.

## 1. Headline

| Safety target | Golden result |
|---|---|
| Wrong-company website matches | **0** (11 eligible suppliers, 18 in total) |
| Invented contacts | **0**. Every returned site phone or e-mail was re-fetched from its `source_url` and found there (10/10). |
| Adversarial forced candidates verified | **0 / 6**. These are similar names, a fraud-warning page and a group brand site. |

| Golden, corrected truth | Coverage | Precision |
|---|---|---|
| Official website | 3 / 11 (27.3 %) | 3 / 3 (100 %) |
| Phone | 3 / 10 suppliers (30 %) | 7 / 7 values (100 %) |
| E-mail | 4 / 10 suppliers (40 %) | 7 / 7 values (100 %) |
| Legal identity (EGRUL) | 18 / 18 | — |

Coverage is low, and the cause is known. The search-engine provider was built but not active, because no search API key is
configured (section 3). Precision was never traded for coverage.

## 2. Pipeline

1. **EGRUL identity.** This is the ground truth: INN, OGRN, KPP, legal name, registered address, region, OKVED and **the
   registered e-mail**. The e-mail is new in P5-002A and is parsed from the official extract.
2. **`WebsiteSearchProvider`s.** They are replaceable and each sits behind its own circuit breaker:
   - **EGRUL e-mail domain.** The domain of the registered e-mail, for example `INFO@BSSPHARM.RU` → `bsspharm.ru`. Free-mail
     domains are skipped.
   - **Brave Search API / Yandex Search API.** These run high-precision queries such as `"<name>" "<INN>"`,
     `"<name>" "<OGRN>"`, `"<name>" "<region>"`, `"<INN>"` and `"<OGRN>"`, with at most 3 queries. They are **active only
     with a key** (`BRAVE_SEARCH_API_KEY`, or `YANDEX_SEARCH_API_KEY` + `YANDEX_SEARCH_FOLDER_ID`).
   - **Wikidata.** Looks up the item with this OGRN (P7011) and reads its official website (P856).
   - **Legal-name domains.** Transliterated names plus `.рф`, at most 6, kept only if the domain resolves in DNS.
   - **Checko website hint.** This is `OPTIONAL_SECONDARY_HINT` and never required. It was **disabled** in every run reported
     here.
3. **Candidate filter.** Directories, registry mirrors, marketplaces, social networks, aggregators, news sites and procurement
   portals are dropped and logged as rejected hints. Candidates are de-duplicated by registrable domain, ranked, and capped at 4.
4. **Identity verification** on the site root plus at most 6 same-host high-value pages: requisites, contacts, about, policy,
   documents and catalog. robots.txt is respected, with an 8 s timeout, a 1.5 MB cap, a per-host delay and a descriptive
   User-Agent.
   - `VERIFIED_STRONG`: this company's INN or OGRN is published on the site as self-identification.
   - `VERIFIED_COMPOSITE`: the exact legal-name core (word-bounded) plus the registered street and house, or plus the KPP.
   - `REJECTED`: the name alone, the KPP alone, an INN quoted only inside an impostor warning, or a directory-like page with
     three or more other companies' INNs. These never verify.
5. **Business contacts, only from verified domains.**
   - Fax-only numbers are dropped. A combined «тел./факс» line counts as a phone.
   - Person-associated numbers are dropped: a patronymic or role word next to the number.
   - Person-like mailboxes are dropped: `a.bondar@`, `kamenev.m@`, `name.surname@`, bare surnames.
   - Third-party domains are rejected. Accepted are the company domain, the EGRUL e-mail domain, or a role mailbox on public
     mail.
   - Values are de-duplicated with normalized phones and lower-cased e-mails, and nothing is inferred.
   - Every value carries `verification_basis`, for example `OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE+OGRN_ON_SITE` or
     `FNS_EGRUL_EXTRACT`.
6. **Freshness.** FRESH, STALE or UNKNOWN comes from the copyright year, page metadata (`article:modified_time`,
   `dateModified`) and `<time datetime>`. The retrieval date is never used. A page with no date stays UNKNOWN.
7. **Website change protection.** The stored official site is re-verified first:
   - Still verified: it is kept, and new candidates are not considered.
   - Unreachable: it is kept, with its verified phones and e-mails.
   - Rechecked and failing: it is replaced.

   Every check is appended to `supplier_website_check`, which is the evidence history.

The API is still `GET /api/v1/suppliers/{inn}/profile`, now with additive fields: `enrichment.website_verification`
`{status, signals, discovered_via, checked_at}`, `contacts[].verification_basis` and `website_checks[]` (the latest 6 checks).
Supplier 360 shows how the website was verified and how it was found, a basis line for each value, and a "Websites checked"
list that includes rejected similar-name sites.

## 3. Source availability

| Source | Status on 2026-10-02 |
|---|---|
| Web-search HTML pages (Brave, Bing, Mojeek, DuckDuckGo) | **Not used.** robots.txt `Disallow: /search`; DuckDuckGo html serves a bot challenge. Bypassing either would be evasion (ED-29, owner decision). |
| Brave Search API, Yandex Search API | Implemented and unit-tested on documented response shapes. **Not exercised live: no key configured.** |
| EGRUL e-mail domain | Works. A lead for 4 of 18 golden suppliers (final run) and 3 of 22 pilot suppliers that reached discovery. Most companies register no e-mail or a free-mail address. |
| Wikidata (OGRN → P856) | Works. 0 hits in golden and pilot; about 2,000 Russian organisations carry an OGRN there, mostly large companies. |
| Legal-name domains (DNS-checked) | Works, but no correct site among the candidates checked: 11 in the golden final run (5 suppliers) and 16 in the pilot (9 suppliers). **All were rejected by identity verification**, among them `altair.ru`, `altair.com`, `альтаир.рф`, `kardan.ru` and `кардан.рф`. |
| egrul.nalog.ru | Refuses bursts with HTTP 400. Golden first pass: 6/18 refused; re-run with a 20 s pause: 0/18. Pilot with a 15 s pause: 13/40 refused (7 kept their previous profile, 6 FAILED). |
| Checko (optional hint) | Disabled in all P5-002A runs, and still HTTP 429 on a single probe. |

## 4. Golden acceptance set

`benchmark/enrichment/p5_002a_contact_golden.json` has 18 historical suppliers.

**How the truth was built.** It was established by hand before the discovery code existed. Directory pages were used only as
leads. The company pages were fetched raw and inspected for the INN or OGRN and the printed contacts.

**Cases covered:**
- Obvious official site (Артис, RSVO)
- INN on site (most)
- OGRN on site (BSS, RSVO, Тензор, …)
- Similar names (Артис / artis21, Альтаир, Эдельвейс, БСС / bssys)
- No discoverable site (Эдельвейс, КП Кировский, КСП Колпино, ТД Ленинградский)
- Individual entrepreneur
- Phone and e-mail present (most)
- No business contacts (Альтаир: its only number is printed under the director's name)
- Fax lines (Первый Спецтранс, Охрана Телеком)
- Personal e-mails (BSS regional managers)
- An adversarial wrong-company trap: СЗУОМТ's INN appears on another group company's site only inside a fraud warning

### Corrections made after the first run (disclosed)

All three were accepted only after re-inspecting the pages or the EGRUL extract by hand. They are listed with their evidence in
the golden file under `corrections`.

| Supplier | Change | Why |
|---|---|---|
| Прометей 4719016624 | expected website: none → `prometeyspb.com` | The page `/ooo_prometei/` publishes the INN, KPP, OGRN and registered address. The first manual check read only the home page. |
| БСС 7810687137 | `bsspharm.ru` added, plus three branch phones | The non-www `bsspharm.ru/contacts/` shows «БСС», the registered street address and the central-office phone. The first check read the `www.` host, which serves different content. |
| Охрана Телеком 7813474659 | `in@rosohrana.ru` added | It is the e-mail registered in EGRUL (official extract). |

**Against the original, uncorrected truth**, scoring the same final output:
- Website: 2 correct of 3 found. `bsspharm.ru` counts as a same-company domain, not a wrong company.
- Wrong-company discovery matches: still **0**.
- 1 adversarial candidate (`prometeyspb.com`) would count as "verified". The pipeline was right there; the truth was wrong.

### Bug found by the golden run and fixed

On the first run, `tsmb.ru/contacts/` became **VERIFIED_COMPOSITE for СЗУОМТ**. The INN guard worked, but that company's name,
KPP and registered address quoted inside the same fraud warning satisfied the composite rule. Now, when the company's INN or
OGRN appears only inside a warning, the whole page is rejected (regression test
`test_warning_page_never_becomes_a_composite_match`). On the re-run, all 6 adversarial checks were REJECTED or UNKNOWN.

### Per-supplier results (final run)

| Supplier | Expected | Result |
|---|---|---|
| RSVO 9719079775 | rsvo.ru | ✓ STRONG (INN+OGRN), found via EGRUL e-mail domain; 3 phones and 3 e-mails, all correct |
| Вижен-Софт 7802433724 | pitaniesoft.ru | ✓ STRONG (INN+OGRN+KPP), via EGRUL e-mail domain; 1 phone and 2 e-mails, correct |
| БСС 7810687137 | bsscosmetics.ru / bsspharm.ru | ✓ COMPOSITE `bsspharm.ru`, via EGRUL e-mail domain; 3 phones correct; registered e-mail; 0 of the dozens of personal manager e-mails |
| Охрана Телеком 7813474659 | ohranatelecom.ru | missed: the EGRUL domain `rosohrana.ru` was correctly REJECTED; the EGRUL e-mail is shown |
| Артис, Тензор, ЦКР, Первый Спецтранс, Кардан, Альтаир, Прометей | have sites | missed: no lead without a search API (name guesses rejected) |
| ЦМБ, СЗУОМТ, Эдельвейс, КП Кировский, КСП Колпино, ТД Ленинградский, individual entrepreneur | none | ✓ no website, no contacts invented |

**Timing.** The pipeline time per supplier, from EGRUL identity and extract to discovery and verification, was a **median of
30.7 s, p95 65.1 s and max 69.2 s**. Most of it is the EGRUL extract polling, polite per-host delays and slow or unreachable
candidate hosts with an 8 s timeout and one retry.

**Provider failures in the final golden run:** `FIRST_PARTY_WEBSITE` 5 (unreachable or timed-out candidates). EGRUL: 0.

## 5. Pilot: 40 historical suppliers (coverage only, no truth labels)

**Selection:** the top suppliers of OKPD2 prefixes 10.51 and 26.20, filled up with the most active suppliers, with HOLDOUT
suppliers excluded. Checko was off, refresh was on, and the pause was 15 s.

The deterministic selection overlaps the golden set by **17 of 40** suppliers, so only 23 suppliers are new to this task.

| Measure | Value |
|---|---|
| EGRUL legal identity | 34 / 40 (6 FAILED: EGRUL HTTP 400 with no stored profile) |
| EGRUL address / OKVED | 29 / 34 |
| Official website | 3 / 40 (7.5 %). All 3 are golden suppliers' stored sites (2 re-verified in this run, 1 kept from its previous verified state); **no site found among the 23 non-golden suppliers** |
| Phone / e-mail | 3 / 40 · 4 / 40 |
| Website checks in the pilot | 16 legal-name candidates (9 suppliers) and 1 EGRUL-domain candidate **REJECTED**; 2 stored sites re-verified; 0 wrong verified |
| Pipeline time | median 19.1 s, p90 53.9 s |
| Source failures | `FNS_EGRUL` 13, `FIRST_PARTY_WEBSITE` 7, `WIKIDATA_OGRN` 1 |

Coverage without a search API is limited by leads, not by verification. Configuring a Brave or Yandex Search API key enables
the `"<name>" "<INN>"` queries with no code change.

## 6. Real Supplier 360 test (browser)

**Setup.** Production frontend build on `:3107`; the search API on `:8002` (main DB) and the Supplier 360 API on `:8001`
(`supplier_radar_p5`, now with 0006); headless Chrome with CORS enforced.

**Checked in every case:**
- no failed requests;
- no HTTP ≥ 400;
- no console errors;
- no external requests;
- no horizontal overflow at 1366 px and 390 px.

| Case | Supplier | Result |
|---|---|---|
| Flow: historical search → Supplier 360 | «Услуги связи проводного радиовещания» → RSVO is card #1 | Profile shows legal identity (OGRN), official website «подтверждён реквизитами» and found via, phones, `info@rsvo.ru`, a basis line, source classes, checked date and freshness. Results 1.0 s, profile 0.23 s. |
| A. Website + phone + e-mail | Вижен-Софт | ✓ |
| B. Website + phone only | **synthetic mock fixture** (no real example in golden or pilot) | ✓ |
| C. Verified website, no contacts | **synthetic mock fixture** (no real example in golden or pilot) | ✓ shows "Verified contact information has not yet been discovered" and UNKNOWN freshness. This found and fixed a UI bug: a website alone counted as a reachable contact. |
| D. No official website | КП «Кировский» | ✓ |
| E. Individual supplier | the 12-digit pilot INN | ✓ no collection, explained |
| F. Stale freshness | ЗАО «Можайский» (curated, outdated page) | ✓ «Данные могут быть устаревшими» |
| G. Wrong similar-name website rejected | Альтаир | ✓ "Websites checked": `altair.ru`, `altair.com`, `альтаир.рф` — «Отклонён — принадлежность не подтверждена» |
| Composite + personal-mail exclusion | БСС | ✓ «подтверждён наименованием и адресом»; no manager e-mails |
| EGRUL e-mail + rejected EGRUL domain | Охрана Телеком | ✓ |
| English route | Вижен-Софт `/en` | ✓ |

Screenshots: `reports/p5_002a_screenshots/` (the individual entrepreneur's page is not stored, because it shows a personal
name).

## 7. Regression

| Check | Result |
|---|---|
| Backend `pytest` | **475 passed** (439 before + 36 P5-002A unit and integration tests) |
| Frontend `npm test` | 18 passed |
| typecheck / lint / production build | pass |
| Browser: free-text search, explicit OKPD2 10.51.11.141, mismatch 26.20.11.110, unknown OKPD2 10.51.11.999, Acer query, English results, Lot-ID 5956101 / 5718896, CSV / JSON export | all pass, no 390 px overflow |
| HOLDOUT | not re-run |

**Verification scope.** During this task the shared working tree also held another session's uncommitted OKPD2 work:
`app/search/category_*`, `supplier_search*.py`, `market-product/results-screen.tsx` and marketProduct copy. None of it is in
the P5-002A commits.

The browser regression and the main-tree builds ran with those changes present. On a clean checkout of the P5-002A commit
`5b1de53`:
- backend: **475 passed** (same count, so none of it came from the other work);
- frontend: tests (18), typecheck and lint pass;
- production build: could not run there (Turbopack rejects a symlinked `node_modules`).

P5-002A does not change any search code; it is identical to the P5-001C baseline.

## 8. Known limitations

- **No search-engine provider active.** Without a Brave or Yandex Search API key, discovery relies on the EGRUL e-mail domain,
  Wikidata and name guesses. Golden website coverage is 27 % and pilot coverage of new suppliers is 0. The provider code and
  ranking are in place, but untested against the live APIs.
- **egrul.nalog.ru throttles bursts** with HTTP 400, so batches need pauses of 20 s or more. With a 15 s pause, 13/40 pilot
  suppliers were still refused. This is the main limit on scale before the 44,196-supplier universe.
- **Per-supplier time** is a median of about 20–30 s and p95 about 65 s. On-demand enrichment in the UI is synchronous; batch
  pre-enrichment is the intended path (HD-07).
- **JavaScript-rendered sites** expose no requisites in their HTML: `tensor.ru` publishes them only on `/doc`. No headless
  rendering is done.
- **The golden set is small (18)** and its truth was corrected 3 times after the first run, with the corrections disclosed in
  section 4.
- **Case B and C UI states** have no real example yet and were verified on synthetic fixtures only.
- **The person-like mailbox rule is heuristic.** It rejects some legitimate role mailboxes (coverage loss) and cannot detect
  every personal mailbox.
- **Evidence claim texts** are produced in English by the backend.
- **Two databases.** Migration 0006 is on `supplier_radar_p5` only. A single-API deployment still needs migrations 0005 and
  0006 on the main database, which is an owner decision.
