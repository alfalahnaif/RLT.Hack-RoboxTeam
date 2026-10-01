# Requirements Quality Review (gaps, ambiguities, missing pieces)

> ### Hackathon Day-1 amendment (2026-10-01)
> Written before the dataset and briefing. Gaps resolved by real data / ADR-H1: G-16 (valid time → `publish_date`), G-18 (history fixtures → real history),
> G-22 (buyer → `customer_inn`), G-23 (categories → OKPD2), unknown-dataset items. The blocking set in §4 is replaced by organizer questions OQ-33…OQ-44
> and the [Execution Baseline](../HACKATHON_EXECUTION_BASELINE.md).

> Contradictions are in [CONFLICTS.md](CONFLICTS.md); unanswerable items are in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
> This file lists **quality findings `G-xx`** with the recommended handling. Severity: **H** blocks a phase ·
> **M** causes rework if ignored · **L** cosmetic/clarity.

## 1. Overall assessment

The source documents are **unusually strong** for a pre-hackathon plan: clear problem, explicit scope
cuts, a defensible architecture, an evaluation-first mindset, and logged assumptions/decisions. The main
weaknesses are (a) **missing operational definitions** (formulas, thresholds, "known", "suitable query"),
(b) **session/state gaps** between search and profile/compare/feedback, (c) **temporal-holdout
prerequisites** not reflected in the data model, and (d) **external constraints** (pre-event coding
rules, source legality, organizer data) that can invalidate the timeline.

## 2. Findings

### Ambiguous requirements
| ID | Sev | Finding | Handling |
|---|---|---|---|
| G-01 | H | "Relevant supplier" not operationally defined (acknowledged as OQ in sources) | Seed: designed qrels; real: weak labels + human grading; confirm with organizers (OQ-02) |
| G-02 | H | "Known supplier" (`is_known_supplier`) definition: known to whom, active when? Category-relative novelty also used (C-04) | OQ-17; ED-14 |
| G-03 | M | Filter `region` semantics: supplier location? delivery region? hard filter? (Location is soft per P0 §36, but a UI filter is inherently hard) | OQ-19; proposed: UI region filter = hard filter on supplier region; parsed region = soft feature |
| G-04 | M | "Relevant Experience" filter (STR §11) has no definition (threshold of similar contracts?) | Proposed: `experience ≥ 1 similar record`; confirm in P6 |
| G-05 | H | Query max 1000 chars; real procurement descriptions/ТЗ are often much longer (users "paste a procurement request") | OQ-20; MVP: `QUERY_TOO_LONG` with guidance; Could: accept long text + extract key lines |
| G-06 | L | Quantity is extracted (STR §11) but not in canonical intent (P0 §17) and unused in ranking | Add optional `quantity` to intent for display only |
| G-24 | M | Success targets ambiguous: recall "5%" relative or absolute; "suitable queries" for discovery target | Proposed definitions in [EVALUATION §6](../architecture/EVALUATION.md#6-success-targets-phase-0-71) |
| G-25 | M | "Evidence" for Top 5 — what counts (organizer record itself? category code?) | Proposed: any Evidence row with source + observed_at; organizer procurement record counts as `PROCUREMENT_HISTORY` evidence |

### Missing definitions / formulas
| ID | Sev | Finding | Handling |
|---|---|---|---|
| G-20 | M | "Not applicable" vs "missing data" for features not distinguished | BR-05 clarification (N/A per query; missing per supplier = 0) |
| G-21 | M | No formulas for: 8 ranking features, 5 confidence components, `profile_completeness`, evidence-level `confidence`, risk-flag thresholds | v1 proposals in SEARCH_AND_RANKING §3–5; finalize in P3-009/P5-005/P5-006 with unit tests |
| G-26 | M | Offering→supplier aggregation function unspecified ("best offering" only for display) | ED-09 (max) |
| G-27 | M | Lexical score normalization to 0–1 unspecified; per-query min-max is misleading | ED-10 |
| G-28 | L | Tie-breaking unspecified (needed for determinism) | ED-09 |
| G-29 | M | Semantic retrieval has no minimum similarity → always returns 200 "candidates" | ED-13 floor |

### Missing user flows / states
| ID | Sev | Finding | Handling |
|---|---|---|---|
| G-07 | H | Profile/compare need **query context** ("why matched", Match/Confidence for this query), but `GET /suppliers/{id}` is query-agnostic; feedback references `request_id` but nothing stores runs | ED-02 SearchRun persistence + `?request_id=` |
| G-08 | M | Pagination is a stated API principle but `/search` has only `limit`; profile offerings/history/evidence unbounded | Add `offset` (Could) — limit ≤ 100 is sufficient for MVP; paginate profile sub-lists |
| G-09 | L | `supplier_type` filter single-valued while UI implies multi-select | Accept array (MINOR) in P6 |
| G-11 | M | Missing UI states in sources: zero results, partial/degraded, low confidence, not found, merged supplier | Defined in [SCREENS](../product/SCREENS.md) |
| G-12 | M | Market-expansion summary (counts known/external/types/new) is central to the demo but not an FR nor in the response contract | FR-17 [ER]; `market_summary` in response |
| G-13 | M | Multi-item/multi-lot requests not addressed | OQ-21; MVP warning |
| G-14 | L | Search history, CSV export listed as Should with no API/flow | Deferred; S-05 depends on ED-02 |

### Missing data / model elements
| ID | Sev | Finding | Handling |
|---|---|---|---|
| G-10 | M | DeliveryFit (0.03) and "delivery evidence for Saint Petersburg" have no data model or source | `DELIVERY_REGION` evidence type [ER]; feature N/A when no delivery data exists |
| G-16 | **H** | Temporal holdout requires **valid time** for every fact (offerings, evidence, supplier first-seen), but entities only have ingestion `created_at` | ED-04; `as_of` across repositories; valid-time fields in DOMAIN_MODEL |
| G-17 | M | After entity resolution, how `is_known_supplier` combines across sources is undefined | BR-19a |
| G-18 | M | Seed dataset contains **no procurement records and no evidence** → Experience, Confidence, Evidence coverage untestable until organizer data | P3-008 seed extension [ER] |
| G-19 | L | "Description may be empty only if title is sufficiently descriptive" — not testable | BR-39 operationalization |
| G-22 | L | `buyer` in data strategy (P0 §18) missing from `procurement_record` | Add optional `buyer_name/buyer_inn` |
| G-23 | M | Category taxonomy: "canonical_category" mentioned, no taxonomy source defined (organizer likely uses ОКПД2/КТРУ) | OQ-29; P4-006 |
| G-30 | M | Merge of suppliers invalidates IDs referenced by qrels and search runs | `SupplierRedirect` [ER], EC-22 |
| G-31 | L | `trust_level` and DataSource `status` enums undefined | Proposed values in DOMAIN_MODEL §2.5 |

### Missing permission / security / validation rules
| ID | Sev | Finding | Handling |
|---|---|---|---|
| G-15 | M | "No auth" + public deployment + optional paid LLM ⇒ abuse/cost exposure; feedback spam | ED-15 |
| G-32 | M | Personal data of individual entrepreneurs (152-ФЗ) not considered | NFR-PRIV-01, OQ-24, R-17 |
| G-33 | M | Scraping/ToS constraints named as risk but no source-approval procedure | P0-002 + allowlist in adapters (NFR-SEC-04) |
| G-34 | L | Ingestion validation behavior on bad records undefined (fail whole batch vs skip) | Per-record error report; quarantine |

### Redundancies
| ID | Finding | Handling |
|---|---|---|
| G-35 | Quality flags vs risk flags (C-09) | Mapping |
| G-36 | Embedding field duplicated (C-14) | ED-06 |
| G-37 | Execution order given 3 times (P0 §89, §91–96, §107) with slight differences | Single roadmap in implementation/ |

## 3. Feature dependencies (functional)
- Ranking features **Experience**, **historical branch**, **known/new**, **temporal holdout** ⇒ require procurement data (organizer).
- **Confidence**, **evidence coverage**, **risk flags**, **manufacturer verification** ⇒ require Evidence + ≥1 external source.
- **Profile query context, compare, feedback, history, analytics** ⇒ require SearchRun persistence.
- **CategoryMatch / category branch** ⇒ require intent category + canonical category mapping.
- **Editable intent (UC-08)** ⇒ requires `intent_overrides`.
- **All UI screens** ⇒ require Design System integration (P0-005) and UI-locale decision (OQ-22).

## 4. Decisions required before implementation (blocking set)
| Blocks | Item |
|---|---|
| Everything | OQ-01 pre-event coding rules (A-12) |
| P1 contracts | C-03 source reference, C-05 score scale, C-18 data_source schema, ED-11 repo layout |
| P2 API | C-06 error codes, ED-07 envelope |
| P3 ranking | C-01 weights, ED-09 aggregation/tie-break, ED-10 normalization, ED-13 semantic floor |
| P4 data | OQ-17 known definition, ED-04 valid-time, OQ-29 taxonomy |
| P5 sources | OQ-08 allowed external sources, legal clearance |
| P6 UI | P0-005 Design System mapping, OQ-22 UI language, ED-19 overrides/filters, C-08 compare priority |
