# Assumptions

> Source assumptions keep their IDs (`A-01…A-12` from P0 §75; `P1A-001…008` from P1S §48).
> New assumptions from this analysis use `A-101+`. Status: *Unverified · Likely · Accepted · Must verify · Confirmed · Invalidated*.
> When an assumption is invalidated, log the impact in DECISION_LOG and update affected tasks.

## From sources

| ID | Assumption | Status | Verified by | Linked |
|---|---|---|---|---|
| A-01 | Organizer data contains identifiable suppliers | **Confirmed 2026-10-01** — supplier INN on every row (44,196 INNs; 8 malformed) | P4-001 | OQ-07 |
| A-02 | Product/procurement description text exists | **Confirmed with correction** — ТРУ `product_name` (2.97M items) + lot subject; no separate description field | P4-001 | OQ-07 |
| A-03 | Russian is the dominant query language | **Confirmed** (all data Russian) | P4-001 | NFR-LANG-01 |
| A-04 | Historical procurements exist | **Confirmed** — 2024-01-08 → 2025-12-31 | P4-001 | Temporal holdout |
| A-05 | External company data can legally be accessed | Must verify | P0-002 | OQ-08, R-06 |
| A-06 | Discovering new suppliers is valuable to the organizer | **Confirmed** (briefing §2, §8) | P0-003 | OQ-03 |
| A-07 | Manufacturer status can be determined from available sources | Partial | P5-003 | OQ-06 |
| A-08 | Price data is incomplete/non-comparable | **Confirmed** — only lot-level `start_price`; no item/contract price | P4-001 | BR-07 |
| A-09 | Main search corpus fits PostgreSQL MVP architecture | **Confirmed (size)** — 0.6M lots / 3M items; load time to measure in P1-001D | P4-008 | OQ-11 |
| A-10 | Stable internet is not guaranteed | **Confirmed as requirement** (briefing §9: no live-internet dependency) | — | NFR-REL-05 |
| A-11 | Historical participation can be used as a weak relevance signal | **Likely** — organizer lists it as useful; ЭМ only (HD-05); validate on replay benchmark | P4-009 | OQ-05 |
| A-12 | Pre-event coding rules permit planned preparation | **Moot** — event started; only UI was pre-built | P0-002 | OQ-01, R-01 |
| P1A-001 | Russian text will dominate search queries | Likely | P4-001 | A-03 |
| P1A-002 | Suppliers can have multiple product offerings | Accepted | — | BR-01 |
| P1A-003 | Organizer data can map into supplier/offering structure | **Invalidated** — no supplier offerings/catalog; maps into Lot/Item/SupplierHistory (HD-02/03) | P4-001 | R-03 |
| P1A-004 | INN present for many but not all suppliers | **Invalidated (better)** — INN present for all supplier rows | P4-001 | BR-36 |
| P1A-005 | Search quality measured primarily at supplier level | Strong assumption | — | EVALUATION |
| P1A-006 | Product offering text available or derivable | **Confirmed with correction** — item text from procurements, not supplier offerings | P4-001 | OQ-28 |
| P1A-007 | Known/external can be a boolean initially | Accepted (MVP) | — | C-04 |
| P1A-008 | 10 seed queries enough for first baseline | **Superseded** — replay benchmark (HD-06) | — | EVALUATION |

## New (this analysis)

| ID | Assumption | Status | Verified by | Linked |
|---|---|---|---|---|
| A-101 | Hackathon event days are 2026-10-01 → 2026-10-02 (STR §14 plan); organizer dataset arrives on 10-01 | **Confirmed** (dataset + briefing on 10-01) | P0-002 | R-02 |
| A-102 | Team = 4 people with roles per STR §13 (Lead, Data/ML, Backend/Data, Frontend/Product) | Likely | P0-007 | Roadmap tracks |
| A-103 | The standalone web app + REST API is an acceptable deliverable (no AIS ГЗ integration needed) | Likely | OQ-12 | ARCHITECTURE §2 |
| A-104 | Inactive (liquidated) companies are excluded by default; `unknown` status kept with flag | Working | OQ-25 | BR-04 |
| A-105 | UI language is Russian (LTR); Design System is applied via tokens/components with a `ru` locale | Confirmed (ED-25) | OQ-22, P0-005 | C-19 |
| A-106 | multilingual-e5-base runs acceptably on CPU for query-time embedding (≈ tens of ms) and batch indexing of the corpus within the event window | Likely | P3-001/002 | R-12 |
| A-107 | LLM is optional; the product meets all Must requirements without it | Working | P5-008 | ED-03 |
| A-108 | Region filter in UI filters supplier registration region (hard); parsed region is soft | Working | OQ-19 | BR-03 |
| A-109 | Demo corpus size is ≤ ~1M offerings (single-node PostgreSQL + HNSW is sufficient) | **Revised** — 2.97M items (fewer distinct names); embed distinct normalized names only | P4-001 | A-09 |
| A-110 | Seed benchmark metrics are for engineering only; pitch metrics come from the real benchmark | Accepted — real = replay benchmark (HD-06) | — | R-09, BR-20 |
| A-111 | The provided Design System's Next.js/Tailwind/next-intl conventions are compatible with the planned frontend stack | Confirmed — `/frontend` builds and lints (ED-26) | P0-005 | ARCHITECTURE §3 |
| A-112 | The Design System is design guidance only — its SafarFlow domain screens (travel, payments) are not product scope | Working | P0-005 | BR-27 |


## New (hackathon day 1, 2026-10-01)

| ID | Assumption | Status | Verified by | Linked |
|---|---|---|---|---|
| A-113 | АИС ГЗ supplier rows are award records only (no participant lists) | **Working interpretation** — confirmed fact is only that all provided АИС ГЗ rows have `is_winner=true`; semantics pending | OQ-33 | HD-05 |
| A-114 | ЭМ supplier rows are complete participant lists for the lot | **Unconfirmed — not assumed by the contracts** (A4: only mixed winner/non-winner rows are observed) | OQ-33/34 | HD-05, HD-06 |
| A-115 | INN prefix (first 2 digits) = tax-registration region of the supplier | Likely (standard INN structure) | OQ-39 | Regional signal |
| A-116 | Historical ТРУ items represent what a supplier can supply (relevance evidence, not quality) | Working | Replay benchmark | HD-03, BR-08 |
| A-117 | ~10 verified external suppliers per demo category are enough to show enrichment value | Organizer-stated | Briefing §11 | HD-07 |
| A-118 | Concentration in food categories reflects dependency risk, not misconduct | Working (presentation framing) | — | HD-08 |
