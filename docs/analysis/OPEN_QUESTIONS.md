# Open Questions

> **Hackathon day 1 (2026-10-01):** the new organizer questions OQ-33…OQ-44 are at the end ([Organizer question pack](#organizer-question-pack--hackathon-day-1)). Ask **OQ-33** first.

> Consolidates STR §15 (10 questions), P0 §77 (16 questions) — de-duplicated — plus new questions from this analysis (**[NEW]**).
> **Ask:** O = organizers/mentors · T = team decision · D = discover from dataset.
> **Blocks:** earliest task that cannot be finalized without an answer. Record answers inline (date + source) and update ASSUMPTIONS.

**Most important question (STR §15, P0 §77):**
> *«Если мы решим только одну проблему идеально, какая проблема даст вам наибольший бизнес-эффект?»*
> If we solve only one problem perfectly, which problem would create the greatest business impact for you?

| ID | Question | Ask | Blocks | Current working assumption | Answer |
|---|---|:-:|---|---|---|
| OQ-01 **[NEW, from A-12]** | Do event rules allow code prepared **before** the event (repo skeleton, seed data, pipeline)? Must code be written during the event only? | O | **All implementation phases (timeline)** | Unknown — plan works either way but timing differs (R-01) || **Moot 2026-10-01:** the event has started; only the UI layer was prepared before the event. |
| OQ-02 | What exactly defines a **relevant supplier**? | O | P4-009 real qrels | Offers the requested product/service and could plausibly participate | |
| OQ-03 | Is discovering companies **outside AIS ГЗ** part of the desired result? | O | P5 emphasis, pitch | Yes (A-06) || **Answered 2026-10-01 (organizer briefing §8):** yes — validate existing suppliers, identify roles, expand the pool via open sources. |
| OQ-04 | What **ground truth** / fields will be used during evaluation by the jury? | O | P7 | Unknown; we bring our own benchmark | |
| OQ-05 | Is historical procurement experience an important ranking signal? Is participation = relevance? | O | P3-009 weights | Weak signal (A-11) || **Answered 2026-10-01 (briefing §11):** yes — similar procurement experience, customer experience, participation, wins are useful signals (not the only criterion). |
| OQ-06 | How should **manufacturer vs distributor** be determined (registry, OKVED, self-declared)? | O | P5-003 | Registry (ГИСП) → catalog → declared || **Partly answered (briefing §3):** roles manufacturer/distributor/supplier/dealer/reseller/other intermediary; must be explainable with evidence. Acceptable evidence → OQ-38. |
| OQ-07 | Which **datasets** will be provided, what identifiers (INN/OGRN), what size? | O/D | P4-001 | A-01, A-02, A-04, A-09 || **Answered 2026-10-01 (data):** 3 CSVs — lots 604,452, supplier rows 1,010,138, ТРУ 2,971,651; identifiers: lot_id, supplier/customer INN (+KPP); no OGRN/names. See dataset analysis. |
| OQ-08 | Which **external/open sources** are explicitly acceptable (ГИСП, ФНС, EIS, company sites, Контур.Фокус…)? Scraping allowed? | O | P5-002…004 | Only public registries with permitted access | |
| OQ-09 | Precision or recall — which matters more? Categories where false positives are especially costly? | O | P3 tuning | Balanced; nDCG primary | |
| OQ-10 | Is geography a hard restriction or a preference? Does delivery capability matter? | O | P3-007, DeliveryFit | Soft unless explicitly required || **Partly answered (briefing §1):** "regional" suppliers are the goal; hard vs soft → OQ-39. |
| OQ-11 | Expected **production data volume**? | O | P4-008, scale story | Fits single PostgreSQL (A-09) || **Answered (data):** ~0.6M lots / 3M items / 44k suppliers for 2 years — single PostgreSQL is sufficient. |
| OQ-12 | Integration model: **embedded in AIS ГЗ** vs standalone app? API-first? | O | Pitch, P8 | Standalone web app + REST API | |
| OQ-13 | Acceptable **latency** and concurrency? | O | P7-003 | P95 ≤ 2.5 s / 5 s; ≤5 concurrent || **Answered 2026-10-01 (briefing §12):** ~5–10 s per recommendation acceptable; 1 min not. |
| OQ-14 | What is the biggest real-world pain point for procurement employees today? Can we observe an existing workflow? | O | Pitch, UX priorities | Discovery + manual verification | |
| OQ-15 | Is the **submission** a live demo, a repository, a deployed URL, a video? Any required tech stack or hosting? | O | P8 | Live demo + repo | |
| OQ-16 | Can organizer data be used offline / stored locally / shown in a public demo? | O | P8-002/003 | Local use allowed; public display unknown | |
| OQ-17 **[NEW]** | Definition of **known vs new** supplier: present anywhere in AIS/organizer data? winner only? within last N years? also "new to category"? | O | P4-005, FR-08 metric | Present as winner/participant anywhere in provided procurement data (ED-14) || **Working answer (ADR-H1):** known = appears in Поставщики on a lot published before `as_of`; external = verified company not in the data. |
| OQ-18 **[NEW]** | Should the product show company **contacts** (phone/email) for outreach? | O | P6-008 | No (out of scope; privacy) | |
| OQ-19 **[NEW]** | UI **region filter** meaning: supplier registration region, delivery region? Hard filter? | T | P6-006 | Supplier region, hard filter; parsed region soft | |
| OQ-20 **[NEW]** | Must we accept **long procurement specs** (> 1000 chars, full ТЗ) as input? | O | P2-006 | No for MVP (reject with guidance) | |
| OQ-21 **[NEW]** | Must we support **multi-item/multi-lot** requests (one search per lot)? | O | P3-005 | No for MVP (warn) | |
| OQ-22 **[NEW]** | **UI language**: Russian? English? Arabic (Design System default)? Jury language? | T/O | P0-005, P6 | Russian UI + Russian data (C-19) | **Answered 2026-09-29 (owner):** Russian default + English, LTR — ED-25 |
| OQ-23 **[NEW]** | Demo **hosting**: team laptop, VPS, organizer infrastructure? Internet at venue? | O/T | P8-003 | Laptop primary + optional VPS || **Answered (briefing §9):** do not depend on internet during the defense → offline demo. |
| OQ-24 **[NEW]** | Constraints on **personal data** (individual entrepreneurs) in storage/display? | O | P4-002 | Minimize; show only public registry data | |
| OQ-25 **[NEW]** | Should **inactive/liquidated** companies be excluded always, or shown flagged? | O/T | P3-007 | Excluded by default (A-104) | |
| OQ-26 **[NEW]** | Thresholds: staleness (days), "low confidence" level for notices, evidence confidence tiers | T | P5-005/006 | 90/730 days; low < 0.4 | |
| OQ-27 **[NEW]** | May Confidence influence ordering (tie-break only, or a "sort by confidence" option)? | T | P3-010 | Tie-break + optional sort; never mixed into Match | |
| OQ-28 **[NEW]** | Suppliers with procurement history but **no offerings**: derive pseudo-offerings from contract titles? | T/D | P4-007 | Yes, as `source_type=procurement_history` offerings flagged derived || **Resolved by HD-03:** no pseudo-offerings — historical ТРУ items are the search unit for known suppliers. |
| OQ-29 **[NEW]** | Which **classification** does organizer data use (ОКПД2, КТРУ, own categories)? Should canonical categories follow it? | D/O | P4-006 | Use organizer classification as canonical if present || **Answered (data):** OKPD2 (8,453 codes, mixed depth); no КТРУ column. OKPD2 is canonical; not sole criterion (HD-04). |
| OQ-30 **[NEW]** | For temporal holdout: use publication date or contract date as cutoff? | D/T | P7-002 | Publication date || **Answered (data):** only `publish_date` exists → cutoff = publish_date (strictly earlier lots visible). |
| OQ-31 **[NEW]** | LLM availability: which provider/model is allowed (data residency, cost), or none? | T/O | P5-008 | Optional; rule-based default | |
| OQ-32 **[NEW]** | Must the product work for **services** (not only goods)? `service_provider` exists but all examples are goods | O | Seed categories | Goods first; services supported by model || **Answered (data):** dataset contains goods, works and services (e.g. OKPD2 86 health services, 33 repair). Demo focuses on goods; services supported by the same pipeline. |


---

## Organizer question pack — Hackathon Day 1

> Created 2026-10-01 from the [organizer briefing](../sources/HACKATHON_DAY1_ORGANIZER_BRIEFING.md) and the
> [real dataset analysis](REAL_DATASET_ANALYSIS_2024_2025.md). Ask in this order. Record answers here **and** in briefing §13.

| ID | Priority | Question (EN) | Вопрос (RU) | Why it matters / blocks | Working assumption until answered | Answer |
|---|:-:|---|---|---|---|---|
| **OQ-33** | **CRITICAL** | In АИС ГЗ supplier data we observe **only** `is_winner=true` (279,031 of 279,031 rows), while ЭМ contains winners and non-winners. Does АИС ГЗ contain only awarded suppliers rather than the full participant list? | В данных АИС ГЗ все записи поставщиков имеют `is_winner=true`, а в ЭМ есть и победители, и участники. Верно ли, что по АИС ГЗ выгружены только победители (с кем заключён контракт), а не полный список участников? | Participation and win-rate modelling; benchmark labels; HD-05 | АИС ГЗ = award records only; participation/win metrics only on ЭМ; no global win rate | |
| OQ-34 | High | Exact meaning of `is_eshop_or_aisgz` (is "ЭМ" = Электронный магазин Санкт-Петербурга?). Why do 54,279 АИС ГЗ lots have no supplier rows (not concluded, cancelled, single-supplier procurement, filtered)? | Что точно означает поле `is_eshop_or_aisgz` («ЭМ» = электронный магазин СПб?). Почему у 54 279 лотов АИС ГЗ нет записей о поставщиках? | Treatment of lots without suppliers; platform semantics | ЭМ = SPb e-shop; supplier-less lots are kept as targets, never as ground truth | |
| OQ-35 | Medium | What does `is_smp` mean, and why is it never `true` on ЭМ (only on АИС ГЗ, 45% of lots)? | Что означает `is_smp` и почему он никогда не равен `true` для ЭМ? | SME filter/feature; avoid a misleading platform bias | Lot-level SME restriction (44-ФЗ ст. 30), only populated for АИС ГЗ; not used in ranking | |
| OQ-36 | Low | What is `reqnum` (filled for 38% of lots)? | Что означает поле `reqnum`? | Possible extra grouping key | Ignored | |
| OQ-37 | Medium | Can we use the official OKPD2 dictionary (titles, hierarchy) and КТРУ as external reference data? Any preferred version? | Можно ли использовать официальный справочник ОКПД2 (и КТРУ) как справочные данные? Какая версия предпочтительна? | Display names, hierarchy features | Yes — public classifier (ОК 034-2014) | |
| OQ-38 | High | What role classification do you expect (manufacturer / distributor / dealer / reseller …)? Which evidence is acceptable (ГИСП, ЕГРЮЛ OKVED, company website, dealer certificates)? Is an inferred role from procurement patterns acceptable if labelled? | Какую классификацию ролей вы ожидаете и какие подтверждения допустимы (ГИСП, ОКВЭД, сайт, дилерские сертификаты)? Допустима ли выведенная роль с пометкой «по косвенным признакам»? | P3-002 role enrichment | Registry/website evidence = verified; procurement pattern = *inferred* label | |
| OQ-39 | High | Does "regional" mean St Petersburg + Leningrad oblast only? Hard filter or preference? Is supplier registration region (INN prefix) acceptable as the region signal? | «Региональные поставщики» — это только СПб и Ленобласть? Это жёсткий фильтр или предпочтение? Допустимо ли определять регион по коду региона в ИНН? | Filters, ranking feature, external search scope | Preference, not filter; region from INN prefix labelled "регион регистрации" | |
| OQ-40 | High | How will matching quality be judged — on your own test lots, on our replay metrics, or by expert review of the shortlist? | Как будет оцениваться качество рекомендаций — на ваших тестовых лотах, по нашим ретро-метрикам или экспертно? | Benchmark design, demo emphasis | Our replay metrics + live golden lots | |
| OQ-41 | Medium | Points for "supplier pool enrichment" and "explainability" (we noted 30 / 25 / 10 for integrity / matching / UI)? Any criteria not mentioned? | Сколько баллов за «расширение пула поставщиков» и «объяснимость»? Есть ли ещё критерии? | Time allocation | Remaining ~35 pts split between enrichment and explainability | |
| OQ-42 | Medium | Which external sources are allowed for enrichment (ГИСП, ЕГРЮЛ/«Прозрачный бизнес», Контур.Фокус, company sites, marketplaces)? Any restrictions on storing/displaying them? | Какие внешние источники допустимы для обогащения и есть ли ограничения на их хранение/показ? | P3-002/P3-003 legality (BR-38) | Public registries + company websites; no paid services | |
| OQ-43 | Medium | 53% of supplier INNs are individuals/IEs. Any restrictions on displaying them? | 53% поставщиков — ИП/физлица. Есть ли ограничения на их отображение? | Privacy (NFR-PRIV-01, OQ-24) | Show INN + entity type only; no personal contacts | |
| OQ-44 | Low | Should the product start from an existing lot (lot_id) or from a free-text need — or both? Is integration into the procurement workflow (e.g. "who to invite" before publication) the intended use? | Продукт должен стартовать от существующего лота или от текстового описания потребности — или и то, и другое? | Entry point emphasis in UI | Both; lot-based is the primary demo path | |
