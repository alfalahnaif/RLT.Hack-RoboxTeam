# Edge Cases

> ### Hackathon Day-1 amendment (2026-10-01) — data-driven edge cases
> | ID | Case | Expected behavior |
> |---|---|---|
> | EC-60 | Target lot has no supplier history (54,279 АИС ГЗ lots) | Still recommend; never used as ground truth |
> | EC-61 | Lot with many items (≥ 11 items: 9.2% of lots) / several OKPD2 codes (17.1%) | Match per item, aggregate per supplier (best item + coverage); show which item matched |
> | EC-62 | Generic "тип N" item name (`Пюре томатное тип 1`) | Low text weight; rely on OKPD2 + context; flag as generic |
> | EC-63 | Noisy OKPD2 (e.g. drills coded `32.99.59.000`) | Text relevance can outweigh OKPD2; explanation shows both |
> | EC-64 | АИС ГЗ lot with several "winners" (services) | Count each as an award; do not infer participation |
> | EC-65 | ЭМ lot with no winner (~2.6%) | Participation counts only; excluded from benchmark winner labels |
> | EC-66 | Malformed INN (8 values) / duplicate (lot, INN) rows (31) | Keep raw; flag; dedupe in canonical layer |
> | EC-67 | Supplier is an individual/IE (12-digit INN) | Show INN + entity type only; no personal enrichment |
> | EC-68 | Replay `as_of` on the first days of 2024 | Little history → warning `LIMITED_HISTORY`, no failure |

> Expected behavior is either sourced from the documents or marked **[ER]** (recommended).
> Items marked **OQ** need an answer before the related task is finalized.
> Each edge case should become at least one test in the task that owns it (column *Owner task*).

## Query input

| ID | Case | Expected behavior | Owner task |
|---|---|---|---|
| EC-01 | Empty / whitespace-only query | 422 `QUERY_TOO_SHORT` (status code: C-06) | P2-006 |
| EC-02 | Query < 3 chars after trimming (e.g. "TV") | `QUERY_TOO_SHORT` | P2-006 |
| EC-03 | Query > 1000 chars — **real procurement specs (ТЗ) are often longer** | [ER] `QUERY_TOO_LONG`; OQ-20 whether to accept long specs (truncate/summarize) | P2-006 |
| EC-04 | Query only numbers/units ("75", "16 ГБ") | Search runs; lexical may return noise → low confidence; warning `LOW_INFORMATION_QUERY` [ER] | P3-005 |
| EC-05 | Mixed RU/EN, Latin brand names ("Samsung 75 панель") | Both preserved; FTS `russian` + `simple` config for Latin tokens [ER] | P2-003 |
| EC-06 | Typos ("интерактивая панел") | pg_trgm and semantic recover (E3-T2 "typo cases improve") | P3-004 |
| EC-07 | Unit variants: `75"`, `75 дюймов`, `75 in`, `190 см` | Rule parser normalizes to `screen_size_inches=75`; cm→inch conversion [ER] | P3-005 |
| EC-08 | `ё` vs `е` ("жёсткий" vs "жесткий") | Equal in search aliases (BR-33) | P1-010 |
| EC-09 | **Multi-item request** (several products/lots in one text) | Not specified — OQ-21. [ER] MVP: treat as one query, warn `MULTI_ITEM_QUERY_DETECTED` | P3-005 |
| EC-10 | Negations ("не б/у", "кроме китайских") | Not supported in MVP; must not invert meaning silently → treated as plain text [ER] | P3-005 |
| EC-11 | Prompt-injection text in the query ("ignore instructions…") | LLM output validated against intent schema; cannot change ranking (BR-09) | P5-008 |
| EC-12 | Unknown / invalid filter values | 422 `INVALID_FILTER` | P2-006 |
| EC-13 | `limit` = 0 / 101 / non-integer | 422 validation | P2-006 |
| EC-14 | Explicit hard constraint in text ("только производители", "с местным присутствием в СПб") | Becomes mandatory constraint → hard filter (BR-04); parser confidence must be high, else soft [ER] | P3-005/P3-007 |
| EC-15 | Parsed region conflicts with filter region | Explicit filter wins; warning [ER] | P3-007 |

## Data & identity

| ID | Case | Expected behavior | Owner task |
|---|---|---|---|
| EC-20 | Supplier without INN | Allowed (BR-36); `MISSING_INN` data-quality flag; lower LegalIdentityVerification | P4-004 |
| EC-21 | Same INN, different names (rename / branding) | Auto-merge (L1); keep all names as aliases; preserve source records | P4-004 |
| EC-22 | Supplier merged after qrels/search runs referenced its old ID | [ER] Keep a `supplier_redirect(old_id → canonical_id)`; profile API follows redirect; qrels remapped with a benchmark version bump | P4-004 |
| EC-23 | Same INN, different KPP (branches) | One legal entity; KPP list stored; not separate suppliers [ER] | P4-004 |
| EC-24 | Individual entrepreneur (12-digit INN) | Valid supplier; personal-data minimization (NFR-PRIV-01, OQ-24) | P4-002 |
| EC-25 | Conflicting regions across sources | `CONFLICTING_REGION` flag; region from highest trust source [ER] | P4-004 |
| EC-26 | Supplier with zero offerings | Not searchable via offering branches; may appear via historical branch only if an offering-like text can be derived from procurement records (OQ-28) | P4-007 |
| EC-27 | Huge supplier with thousands of offerings (marketplace/wholesaler) | Aggregation must not reward breadth: MVP aggregation = max offering relevance (ED-09); consider `GENERALIST` signal later | P2-005 |
| EC-28 | Duplicate offerings (same title, same supplier, several sources) | Dedupe at projection by (supplier, normalized_title, model) [ER] | P2-003 |
| EC-29 | Offering with empty description and short title | Invalid unless title descriptive (BR-39) → rejected with warning in validation | P1-013 |
| EC-30 | Missing value shown in UI (unknown type, no region) | Displayed as "unknown", never as 0/blank; feature scoring per BR-05 | P6-* |
| EC-31 | Stale data (`observed_at` old) | `STALE_INFORMATION` flag; SourceRecency lower. Staleness threshold: OQ-26 | P5-006 |
| EC-32 | Evidence without URL (registry record) | Allowed if `source_record_id` present (reference) [ER] | P5-001 |
| EC-33 | Organizer dataset re-ingested | Idempotent: same canonical IDs, no duplicates (checksums) | P4-002 |
| EC-34 | Category missing / unmapped | `MISSING_CATEGORY` flag; CategoryMatch = 0 for that supplier; semantic fallback (R: unknown categories) | P4-006 |

## Retrieval & ranking

| ID | Case | Expected behavior | Owner task |
|---|---|---|---|
| EC-35 | Zero candidates | 200 with empty results, `total_candidates=0`, warning `NO_RESULTS` (not 404) [ER] | P2-006 |
| EC-36 | Lexical returns nothing, semantic returns weakly related items | Semantic similarity floor (ED-13); below floor → dropped | P3-003 |
| EC-37 | Single candidate / all equal raw scores | Normalization must not force 1.0 via per-query min-max (ED-10) | P2-004 |
| EC-38 | All ranking features N/A except semantic+lexical | Renormalize; still valid score (BR-05) | P3-010 |
| EC-39 | Exact score ties | Deterministic tie-break (BR-14) | P3-010 |
| EC-40 | Index rebuilt between search and profile open | Search-run snapshot is authoritative for query context (ED-02); profile shows current data + notice [Could] | P6-003 |
| EC-41 | All top results are external with no evidence | Still shown (discovery), but Confidence low + `LOW_EVIDENCE`; counts toward evidence-coverage metric | P5-005 |
| EC-42 | Search latency exceeds budget (e.g. LLM slow) | LLM call timeout → fallback parser + warning (budget: OQ-13, default 1.5 s [ER]) | P5-008 |

## UI / session

| ID | Case | Expected behavior | Owner task |
|---|---|---|---|
| EC-43 | Compare suppliers selected from different searches | [ER] Compare tray scoped to one `request_id`; new search clears or asks | P6-009 |
| EC-44 | Selecting a 6th supplier for compare | Rejected with message (max 5) | P6-009 |
| EC-45 | Browser back from profile to results | Results restored without new request (US-08) | P6-006 |
| EC-46 | Deep link to profile with unknown/expired `request_id` | Profile without query context + notice | P6-008 |
| EC-47 | Double submit / rapid re-search | Last request wins; earlier responses discarded [ER] | P6-005 |

## Evaluation

| ID | Case | Expected behavior | Owner task |
|---|---|---|---|
| EC-50 | Query with no relevant supplier in the corpus | Excluded from nDCG/recall averages but counted in coverage; flagged in report [ER] | P2-009 |
| EC-51 | Retrieved supplier not in qrels (unjudged) | Treated as non-relevant for metrics; listed for human judging [ER] | P2-009 |
| EC-52 | Temporal holdout: supplier existed before cutoff but its offering evidence was observed after | Must be excluded (BR-29) — requires valid-time fields (ED-04) | P7-002 |
| EC-53 | Benchmark run while index is partially built | Runner refuses unless index/embedding versions match manifest [ER] | P2-009 |
