# OKPD2 resolver V4: Russian morphology and ambiguity handling

V4 changes how free text is turned into an OKPD2 category, before the accepted supplier ranking runs. The frozen supplier
scorer and its weights, S3 and the sealed HOLDOUT are unchanged and were not re-run.
Machine-readable results: [`okpd2_resolver_v4.json`](okpd2_resolver_v4.json). Benchmark: [`benchmark/okpd2_resolver/`](../benchmark/okpd2_resolver/README.md).

## Problem

V3 matched PostgreSQL snowball stems against the titles of the **8,452 OKPD2 codes observed** in procurement. Three things went wrong:

- A word form could miss: `Асфальтиты` resolved but `Асфальтит` did not.
- Official categories never seen in the data were invisible: `Вина столовые прочие` (11.02.12.159) has no procurement history.
- A broad word could only end up "uncertain". There was no way to say that several categories legitimately match.

## What changed

**Morphology.** [`morphology.py`](../backend/app/search/morphology.py) uses **pymorphy3 2.0.6** with **pymorphy3-dicts-ru 2.4.417150.4580142**.

- Both packages are MIT-licensed, work offline and are pinned in `requirements.txt` (proposed decision ED-29).
- Each word keeps the lemmas of all its noun/adjective readings, e.g. `вина` → {вино, вина}.
- Verb readings are dropped when a noun reading exists, so `стали` → сталь.
- Participles keep their adjective form (`моющие` → моющий).
- Latin model strings are matched literally.

**Index.** [`okpd2_category_index.json`](../data/seed/okpd2_category_index.json) is schema v2.

- It covers all **21,024 official codes** plus 75 observed codes that have no official name: **21,099 rows**, 22.5 MB.
- Each official code stores:
  - its title, normalized title, content tokens, per-token lemma lists and phrase lemmas
  - its parent and depth. Subcategories such as 10.51.11.121 are placed under their zero-ending category 10.51.11.120, which the source data flattens.
- The observed-procurement part (phrases, item and lot counts) is byte-identical to V3.
- Lemmas are precomputed, so a query lemmatizes only its own words.
- The builder records the morphology version, and a test checks that the runtime matches it.

**Resolution order** ([`category_resolver.py`](../backend/app/search/category_resolver.py)):

1. **Exact normalized official title.**
2. **Morphology-aware title:** the query's lemma sequence equals the title's.
   - Stages 1 and 2 resolve when all matches lie on one ancestor line.
   - The same title on unrelated lines is `CATEGORY_AMBIGUOUS`.
3. **Weighted official terms.** Each query word is weighted by `IDF = log(N / df)`, where N is the number of official titles and df is the number of titles containing any of the word's lemmas. The score combines:
   - coverage of the query's term weight
   - title focus: how much of the title the query explains
   - specificity of the rarest matched term
   - historical support (≤ 0.10)
   - semantic support (≤ 0.03)

   Official evidence carries 0.87 of the 0–1 scale, so semantic similarity cannot override it (tested).
   A result is `RESOLVED` only if **score ≥ ACCEPT and score − best rival ≥ MARGIN**:
   - Ancestors of the leader are not rivals; they are the same answer, only broader.
   - The leader's own subcategories are rivals.
4. **Dominant historical phrase** (the V3 rule) applies in two situations:
   - Official evidence is weak, e.g. `Перчатки нитриловые` → 22.19.60.119.
   - Official evidence is ambiguous, and exactly one dominant historical code lies on an official contender's line, e.g. `Молоко ультрапастеризованное 3.2%` → 10.51.11.121. History can choose among official candidates but never introduce a new one.
5. **Fuzzy and semantic neighbours** produce suggestions only, under `CATEGORY_UNCERTAIN`.

**Thresholds.** ACCEPT = **0.36** and MARGIN = **0.18**, tuned on the **dev split only**:

- Grid: ACCEPT 0.30–0.70, MARGIN 0.00–0.40.
- Objective: correct decisions − 2 × wrong confident resolutions.
- The optimum is a plateau (MARGIN 0.15–0.21, ACCEPT 0.35–0.37), so its centre was taken rather than an edge.
- The score weights are design choices, set by inspecting the acceptance examples before the benchmark existed. They were not tuned.

## Results (test split, never tuned on)

The benchmark has 843 cases (dev 427 / test 416): taxonomy-generated cases, 150 procurement item names published before 2025-07-01, and 33 hand-curated cases.

| Metric | V3 | **V4** | V4 dev | n (test) |
|---|---:|---:|---:|---:|
| Exact-title accuracy | 16.2% | **100%** | 100% | 68 |
| Morphological-variant accuracy | 14.6% | **100%** | 99.2% | 123 |
| — number (singular/plural) | 11.1% | **100%** | 100% | 63 |
| — grammatical case | 18.3% | **100%** | 98.4% | 60 |
| — with adjective inflection | 14.3% | **100%** | 98.5% | 77 |
| One-word distinctive term | 44.1% | **98.3%** | 92.3% | 59 |
| Top-1 accuracy (cases with a gold code) | 22.3% | **81.4%** | 79.7% | 328 |
| Top-3 accuracy | 27.4% | **83.8%** | 82.5% | 328 |
| Ambiguity-detection accuracy | 0% | **93.4%** | 97.2% | 61 |
| False ambiguity (gold code exists) | 0% | 0.9% | 2.2% | 328 |
| Correct abstention (ambiguous + unknown) | 90.9% | **96.6%** | 98.1% | 88 |
| Unknown queries → `CATEGORY_UNCERTAIN` | 100% | 100% | 100% | 27 |
| **Wrong high-confidence rate** (all cases) | 5.8% | **1.0%** | 0.5% | 416 |
| Precision of `RESOLVED` | 71.1% | **98.5%** | 99.2% | 259 |
| Procurement descriptions resolved correctly | 5.2% | 7.8% | 16.4% | 77 |
| Procurement descriptions resolved wrongly | 1.3% | 1.3% | 0% | 77 |

On the test split, V3 misses 195 generated title, variant and one-word cases. For 139 of them (71%) the gold code is absent from V3's observed-only index, so the V3 column measures coverage as much as morphology.
Mean resolver time is **132 ms per query**, mostly the fuzzy fallback on unknown words. The 22.5 MB index takes about 4 s to load, once per API process.

## Acceptance cases

| Case | Query | Expected | V4 result |
|---|---|---|---|
| A | Асфальтиты | 08.99.10.120 | ✅ `RESOLVED` 08.99.10.120 (`OFFICIAL_TERMS`) |
| B | Асфальтит | 08.99.10.120 | ✅ `RESOLVED` 08.99.10.120 (V3: uncertain) |
| C | Вина столовые прочие | 11.02.12.159, exact title | ✅ `RESOLVED` 11.02.12.159 (`OFFICIAL_EXACT_TITLE`) |
| D | Стол | `CATEGORY_AMBIGUOUS` | ✅ ambiguous: кухонные / тепловые / чертежные / поворотные … (margin 0.001) |
| E | Битум природный | distinct from Асфальтиты | ✅ distinct: leader 08.99.10.110 «Битумы и асфальты природные»; reported **ambiguous** with 23.99.13 (bituminous mixtures), margin 0.099 < 0.18 — see limitations |
| F | Флюрбикс заквант | `CATEGORY_UNCERTAIN` | ✅ uncertain |
| G | Ноутбук Acer Aspire 5 A515-57-50R7 | regression | ✅ uncertain category; top suggestion 26.20.11.110; model token kept |
| H | Перчатки нитриловые | regression | ✅ `RESOLVED` 22.19.60.119 (`HISTORICAL_DOMINANT`), as in V3 |

Of the 33 curated cases, 31 pass; the two misses are listed under limitations.

## API and UI contract

`classification.category_state` is now one of `RESOLVED`, `CATEGORY_AMBIGUOUS` or `CATEGORY_UNCERTAIN`.
`classification.top_candidates` is a list of `{code, official_name, score, basis}`.

- **Ambiguous query:** no code is used for ranking, no pool-health claim is made, and the warning `CATEGORY_AMBIGUOUS` is returned.
  - The results page shows "Several procurement categories match your request. Please select the intended category" with the candidates.
  - Selecting a candidate re-runs the search with that `okpd2`; it counts as aligned and is then ranked as usual.
  - Until a category is confirmed, suppliers are labelled **Exploratory**.
- **Resolved code with no procurement history** (e.g. 11.02.12.159): the result is `RESOLVED_CATEGORY_NOT_OBSERVED`. Ranking falls back to text evidence, labelled exploratory, instead of returning an empty exact-code pool.
- New `basis` values: `OFFICIAL_EXACT_TITLE`, `OFFICIAL_MORPH_TITLE` and `OFFICIAL_TERMS`. These replace `EXACT_TERM`.

## Limitations

- **Single-word homonym titles.** `Трубы` exactly matches 32.20.13.161 (brass instruments) and resolves there, although procurement users usually mean pipes.
  - I tried a rule that makes one-word exact titles ambiguous when the word names strong candidates elsewhere. It was **net harmful on dev** (utility 354 → 347): it also blocked «Принтеры», «Песчаник», «Громкоговоритель». So it was reverted.
  - Better handling needs procurement-usage evidence for single words. That is an open item, not done here.
- **`Битум природный`** is ambiguous rather than resolved at the dev-tuned margin. Bituminous mixtures (23.99.13) also name natural bitumen. The thresholds were not adjusted for this one case.
- **Long procurement descriptions** mostly abstain: words absent from official titles dilute coverage. The API then falls back to the existing historical/text suggestions, as before.
- **History tie-break trade-off.** It fixes the milk regression but resolves one dev case labelled ambiguous (`ботик` → footwear 15.20.11.111).
- **Benchmark caveats** (see its README): the inflected cases are generated with the same morphology library, description labels are customer-assigned, and the historical phrase channel is in-sample for descriptions.

## Verification

- `tests/search/test_category_resolver.py` (22 tests) and `tests/api/test_supplier_search.py` (27 tests) pass.
- The full backend suite passes when run with the `docker-compose.yml` mounts.
- Frontend: ESLint is clean, and `tsc` reports no errors in the changed files.

## Deployment note

The API image needs to be rebuilt to pick up pymorphy3 (`requirements.txt`). Images built before this change will fail to import the resolver.
