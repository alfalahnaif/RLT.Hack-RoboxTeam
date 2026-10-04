# Supplier Radar intelligence stack: final integration

Validated on **2026-10-02**; report published on **2026-10-04**. Scope: Supplier 360 and P5-002A contact discovery, the full-taxonomy OKPD2 Resolver V4, and an optional closed-world Groq verifier. The integration is on `integration/okpd2-v4-llm-final`; it has **not** been merged into `main` or the final/demo branch.

## Source and integration commits

| Line | Branch | Commit |
| --- | --- | --- |
| Product base (Supplier 360 + P5-002A) | `feature/p5-002a-contact-discovery` | `300ac082210bb005a07339571a90dae0b4f3215f` |
| Resolver V4 | `feature/okpd2-resolver-v4` | `7a55e6d47fbcd6df8336e12884198caf3182c9e6` |
| Optional Groq verifier | `feature/llm-okpd2-verifier` | `8063d1c81d8aab5fdeacd205d53cc79f9a792163` |
| Merge of V4 into product base | `integration/okpd2-v4-llm-final` | `b3adad443cd907006ea364996288d05f7017bf39` |
| Verifier cherry-pick (same content as source line) | integration branch | `2a470dd0e0705ee14af273946574c46d9b2ad19b` |
| Exact-title, gate, and UI safety integration | integration branch | `14ea38e58594204e0b1ca138eb5f9ea749134818` |
| **Final tested implementation commit** | integration branch | **`719c05774b64721cdc3b8118bd064c96bdaa0641`** |

The V4 and verifier work was committed on its source branch before integration. The contact-discovery decision-log entries were retained when the branches were merged. Work outside this integration scope was excluded from the final implementation commit.

## Runtime path and safety

The API resolves a free-text query against the complete official OKPD2 taxonomy: exact title, Russian word forms (`pymorphy3`), term specificity and historical support, with semantic evidence as support. V4 produces the category state and official candidates. A confidence/ambiguity gate optionally sends **only those candidates** to Groq `qwen/qwen3.8-27b`; supplier retrieval and ranking then use a confirmed code or stay exploratory. The model cannot introduce a new code. Invalid output, provider failure, timeout, and HTTP 429 retain the deterministic result. An explicitly supplied code bypasses the verifier.

The API image `supplier-radar-integration-api:okpd2-v4-llm` was rebuilt for this branch, and `pymorphy3 2.0.6` imported successfully inside the running container. The live integration run enabled `OKPD2_LLM_VERIFIER_ENABLED=1` with an existing local credential. No key appears in Git or in these reports. The optional verifier remains disabled by default.

## Resolver V4 benchmark

Replayed from the integrated branch using the existing fixed dev/test split; the sealed supplier-ranking HOLDOUT was not run. The full output is [`okpd2_resolver_integrated.json`](okpd2_resolver_integrated.json). The established V4 reference is in [`okpd2_resolver_v4.json`](okpd2_resolver_v4.json). Thresholds were tuned only on dev.

| Test metric | Integrated | Reference V4 | Test cases |
| --- | ---: | ---: | ---: |
| Exact official titles | 100.00% | 100.00% | 68 |
| Morphological variants | 100.00% | 100.00% | 123 |
| Distinctive single words | 98.31% | 98.31% | 59 |
| Ambiguity detection | 93.44% | 93.44% | 61 |
| Wrong high-confidence resolution | 0.96% | 0.96% | 416 |
| Resolved-case precision | 98.46% | 98.46% | 259 |
| Correct code in top three | 83.23% | 83.84% | 328 |

The 0.61 percentage-point top-three decline is caused by reordering weak **suggestions** when an official parent category provides context. It does not change the resolved/ambiguous/uncertain decision for the benchmark cases. This tradeoff is recorded rather than tuning on the test set. The dev objective was 357; the configured acceptance and margin thresholds remain 0.36 and 0.18.

## Live API acceptance and Groq

The 11 requested queries were sent to the running integrated FastAPI service and checked in [`final_intelligence_acceptance.json`](final_intelligence_acceptance.json). One deterministic warm-up request was excluded from measurement. The browser also exercised the search and result views.

| Case | Query | Result |
| --- | --- | --- |
| A | `Асфальтиты` | `RESOLVED` → `08.99.10.120`; no LLM |
| B | `Асфальтит` | `RESOLVED` → `08.99.10.120`; no LLM |
| C | `Вина столовые прочие` | `RESOLVED` → `11.02.12.159`, `OFFICIAL_EXACT_TITLE`; no LLM; code has no observed history, so supplier ranking remains text-only |
| D | `Битум природный` | `CATEGORY_AMBIGUOUS`; `08.99.10.110` remains the leading official candidate; Groq did not force resolution |
| E | `Стол` | `CATEGORY_AMBIGUOUS`; official alternatives require user selection |
| F | `Стол для медицинских процедур с регулируемой высотой` | `CATEGORY_UNCERTAIN`; official medical-table options `32.50.30.112` and `32.50.30.111` surfaced through parent-category context; Groq returned `AMBIGUOUS` |
| G | `Трубы` | `CATEGORY_AMBIGUOUS`; the exact-title musical-instrument code `32.20.13.161` remains first, but **is not** used for ranking; Groq returned `AMBIGUOUS` |
| H | `Флюрбикс заквант` | `CATEGORY_UNCERTAIN`; no candidate or invented code |
| I | Acer laptop query | `CATEGORY_UNCERTAIN`; `26.20.11.110` leads, no forced code |
| J | Nitrile gloves | `RESOLVED` → `22.19.60.119` |
| K | Ultra-pasteurized milk | `RESOLVED` → `10.51.11.121` |

For `Трубы`, the general one-token exact-title guard detects low specificity plus strong competing official evidence. It preserved deterministic resolution of distinctive one-word examples such as `Принтеры` and `Песчаник` in dev validation. The leading musical code is still a limitation of candidate ordering; ambiguity and text-only ranking prevent a false confirmed category.

| Live metric | Result | Scope |
| --- | ---: | --- |
| Verifier invocation | 4/11 = 36.4% | Requested acceptance queries only |
| Deterministic **total API** latency | p50 1,105.5 ms; p95 2,748.7 ms | 7 queries |
| LLM-query **total API** latency | p50 2,250.9 ms; p95 2,471.5 ms | 4 queries |
| Groq verification component | p50 1,333.2 ms; p95 1,427.1 ms | 4 calls |
| HTTP 429 | 0/4 = 0% | Final integrated run |
| Timeout | 0/4 = 0% | Final integrated run |
| Deterministic fallback | 0 | Final integrated run |

An earlier live verifier fixture run saw **one HTTP 429 in four calls**, with deterministic fallback, as recorded in [`../benchmark/okpd2_llm_verifier/live_groq_report.json`](../benchmark/okpd2_llm_verifier/live_groq_report.json). The older supplier-search latency baseline (p50 375 ms, p95 555 ms) came from a different run and must not be presented as the LLM path's latency. These small samples are acceptance checks, not a production latency distribution.

## Browser, Supplier 360, and contact regression

In the production Next.js build, `RESOLVED`, `CATEGORY_AMBIGUOUS`, and `CATEGORY_UNCERTAIN` display distinct labels. Ambiguous categories show official selectable codes; uncertain categories now show relevant official candidates when available. The UI no longer presents resolver scores or unlabeled history shares as probability percentages. The medical-table browser result displayed the two medical codes, and a user selection leads to a new search with the chosen code. Browser console errors were empty in the Supplier 360 flow.

The live browser path `search → supplier result → Supplier 360` was checked with RSVO (`9719079775`). The profile API returned HTTP 200 and showed its legal identity, OGRN/KPP, EGRUL source, OKVED, 1,408 historical lots, eight contact entries, website checks, and source/freshness information. The profile endpoint and P5-002A contact logic were retained.

The existing 18-supplier contact golden run recorded **zero wrong-company matches and zero invented contacts**, including six adversarial website checks rejected or left unknown. The contact code was not changed in this integration, and the backend/frontend regressions passed. This is preservation of the documented golden result, not a claim that a new live enrichment crawl was performed; see [`p5_002a_contact_discovery.md`](p5_002a_contact_discovery.md) and its JSON evidence.

## Regression gates and limitations

- Backend: **528 passed**, one existing `anyio` deprecation warning. Resolver and verifier targeted tests: **47 passed**.
- Frontend: **18 passed**, typecheck, ESLint, and production build passed.
- Real browser: ambiguous selection, uncertain medical options, exact-title resolution, and Supplier 360 profile checked.
- The medically qualified table query remains uncertain because the official candidates distinguish operating tables from examination/therapy tables but the query does not identify which procedure is intended. Text-only exploratory suppliers can include school or office tables; they are labeled preliminary.
- The exact wine category is absent from observed procurement history, so its correctly resolved code does not create an exact-code supplier pool.
- Contact discovery prioritizes precision over coverage. The prior golden set found three of 11 eligible official websites; several legitimate sites were missed without an external search lead.
- Live timings and Groq error rates are based on only 11 queries (four provider calls) on a local integration stack.

Integration validation is complete. No RFQ, Risk Score, additional feature, or merge into the final/demo branch is part of this integration.
