# Screen Inventory

> ### Hackathon Day-1 amendment (2026-10-01)
> The built screens (S-00…S-05 on the mock API) are **kept** — no redesign. Integration task v2 **P4** adds, within the existing screens:
> lot-id entry on S-01; lot items + OKPD2 context on S-02; counts ("how many suppliers / pool size"); a **pool-health panel** with verdict and
> "Expand the pool" action (manager level); role badges with source (S-02/S-03); an analyst **methodology/evidence** view. One interface, three levels
> of detail (organizer §10). UI = 10 points → wiring and clarity over polish. See [Baseline §12](../HACKATHON_EXECUTION_BASELINE.md#12-updated-architecture).

> Sources: Strategy §10–11 (four screens, demo flow), Phase 0 §85 (UI epic priorities), US-01…08.
> Sections S-00…S-05 define *what each screen must do* (no visual design). The mapping onto the Design System
> (P0-005) is in [§ Design System mapping](#design-system-mapping-p0-005) at the end of this file.

Principle: **four excellent screens, not a large dashboard** (Strategy §11, §16).

| ID | Screen | Priority | Primary flows |
|---|---|---|---|
| S-01 | Search | P0 (Must) | UF-01, UF-02 |
| S-02 | Search Results | P0 (Must) | UF-01, UF-03, UF-04, UF-05, UF-06 |
| S-03 | Supplier Profile | P0 (Must) | UF-01, UF-05, UF-08 |
| S-04 | Compare Suppliers | P1 (Should) — see C-08 | UF-06 |
| S-05 | Search History | P2 (Should/Could) | — deferred |
| S-00 | Global shell (header, system status, demo-data notice) | P0 | all |

Language of UI labels: **Russian (default) + English, LTR** — ED-25 (OQ-22 answered 2026-09-29).

---

## S-01 Search

**Responsibility:** capture the procurement requirement, show how the system interpreted it, let the user correct the interpretation, start the search.

**Data displayed**
- Query input (prompt text from source: *"Что необходимо закупить?"*).
- Example / demo queries (frozen demo set, P8-004).
- Parsed intent (after parse or with results): category, product, characteristics/attributes, quantity, region, required supplier type, mandatory constraints. Each field marked *extracted* vs *user-edited*.
- Parser mode indicator: rule-based / LLM / LLM-unavailable fallback (from `warnings`).

**Actions**
| Action | Result |
|---|---|
| Type / paste requirement | Client-side length validation (3–1000) |
| Submit | `POST /search` → S-02 |
| Edit an extracted field | Marks field as override; re-submit sends override (FR-18, C-07) |
| Clear an extracted field | Field removed from intent (feature becomes N/A → renormalization, BR-05) |
| Choose example query | Fills input |
| Set market scope before search (all/known/external) | Included in request filters |

**States**
| State | Trigger |
|---|---|
| Empty | Initial |
| Typing / invalid | Length < 3 or > 1000 → inline error `QUERY_TOO_SHORT` / `QUERY_TOO_LONG` |
| Submitting | Request in flight (target ≤ 5 s P95; show progress for >1 s) |
| Parsed (intent visible) | Response returned `parsed_query` |
| Parser degraded | `warnings` contains `LLM_UNAVAILABLE` / `PARSER_FALLBACK` — search still works (BR-10) |
| Service unavailable | `503 SEARCH_UNAVAILABLE` → retry action |

---

## S-02 Search Results

**Responsibility:** present the ranked market map; make market expansion obvious; enable filtering, explanation, comparison and drill-down **without losing results** (US-08).

**Data displayed**
- Summary: total candidates; count of known vs external suppliers; breakdown by supplier type; number of *new-to-AIS* (and, if defined, *new-to-category*) suppliers (FR-17, OQ-17).
- Result card per supplier (Top 20 default): name, supplier type (+ verified/unverified), region, known/external badge, Match (0–100), Confidence (0–100), top reason codes rendered as short checklist (e.g. "✓ 14 similar contracts", "✓ official product evidence", "✓ verified manufacturer"), best matched offering (title, category), risk flags.
- Active filters and parsed intent summary (link back to S-01 to edit).
- Timing / warnings (non-intrusive; e.g. "semantic search unavailable — keyword results only").

**Actions**
| Action | Result |
|---|---|
| Filter: supplier type, region, market scope (known/external), relevant experience, min confidence | Re-query or client-side filter — decision ED-19 |
| Sort (default: Match) | Optional: Confidence (Could) |
| "Why matched" on a card | Expands contribution breakdown + reason codes + evidence snippets (UF-05) |
| Select for compare (max 5) | Adds to compare tray → S-04 |
| Open supplier | S-03 with `request_id` context |
| Feedback (relevant / not relevant / unsure) | `POST /feedback` (Should) |
| Load more / page | Up to `limit` 100 (G-08 pagination) |
| Export CSV | Should — deferred unless time |

**States**
| State | Trigger |
|---|---|
| Loading | Awaiting `/search` |
| Results | ≥1 result |
| Zero results | 0 candidates → show parsed intent, suggest broadening (remove constraints/filters) |
| Filtered-empty | Filters exclude all → offer "clear filters" |
| Partial / degraded | `warnings[]` non-empty (semantic branch down, external data stale, LLM fallback) |
| Low-confidence set | All top results Confidence < threshold → show notice (threshold: OQ-26) |
| Error | 4xx validation / 503 |
| Stale context | Results belong to an older index version (EC-40) — Could |

---

## S-03 Supplier Profile

**Responsibility:** full evidence-backed view of one supplier; when opened from a search, show *why it matched this query*.

**Data displayed**
- Identity: legal name (original), INN, OGRN, KPP, legal status, region/city, website, OKVED codes.
- Role: supplier type + how it was determined (e.g. ГИСП registry match) + `UNVERIFIED_MANUFACTURER` if not.
- Known / external status (and first-seen date if available).
- **Query context** (only when `request_id` provided): Match, Confidence, contribution breakdown, reason codes, matched offerings for this query.
- Relevant products / offerings (query-matched first, then others; paginated).
- Procurement history: records (title, date, role winner/participant, amount, region) — relevant ones first.
- Evidence list: type, claim, source name, link, observed_at, evidence confidence.
- Confidence breakdown (5 components) and risk flags with human-readable meaning.
- Data sources & freshness; data-quality flags (optional, analyst view).

**Actions**: back to results (restores state, no re-run), add to compare, open source link (external, new tab), feedback.

**States**: loading · loaded · partial sections (no evidence / no history / no offerings — each with explicit empty text, never blank) · not found (`404 SUPPLIER_NOT_FOUND`) · supplier merged/redirected (EC-22) · context expired (request_id unknown → show profile without query context).

---

## S-04 Compare Suppliers

**Responsibility:** side-by-side comparison of 2–5 suppliers from the same search; answer "why A above B" (US-07).

**Fields (Strategy §11):** Match score · Confidence · Manufacturer/Distributor · relevant contracts count · region · product evidence · company status · new/existing. Plus **[ER]** contribution breakdown per feature with the largest differences highlighted (derived from ranking engine, BR-12).

**Actions**: remove supplier, open profile, reorder (Could).
**States**: fewer than 2 selected (prompt) · 2–5 · limit reached (6th rejected with message) · suppliers from different searches (EC-43: disallow or show without query context) · missing values ("—" with reason, never 0).

---

## S-05 Search History (UI built on mock data at the owner's request, 2026-10-01; backend list endpoint still deferred)

List of previous searches in this browser/session (request_id, query, time, result count); re-open results.
Depends on ED-02 persistence. Not in MVP build plan unless time allows.

## S-06 Procurement analysis (P4-002, live backend — main demo screen)

Lot ID input + Analyze + demo shortcuts (primary 5956101, fallback 5718896; they only fill the ID — data always comes from the API).
One request `GET /procurements/{lot_id}/analysis` renders: procurement summary · overview tiles (suppliers / concentrated
categories / external candidates) · two separately labelled dates (historical procurement cutoff vs. external evidence checked) ·
ranked suppliers (reasons built from structured fields; semantic provenance only in a collapsed "Additional semantic evidence") ·
per-OKPD2 accordion: pool health (headline, top-1 share bar, lots/awards/suppliers/top-3/HHI), historical alternatives,
external market expansion (Verified / Under review badges, evidence basis, review points, source links,
`exact_okpd2_asserted_by_source` wording). States: initial, staged loading, not found, PARTIAL, semantic unavailable,
section unavailable, items without OKPD2.

## S-07 Supplier 360 profile (P5-001B, UI for the P5-001A contract)

Drill-down from every supplier card (live market-product historical + external cards, S-06 ranked suppliers, historical
alternatives and external candidates) via "View supplier profile"; the back button returns to the originating list (`?back=`,
relative paths only). One screen for historical suppliers and curated external candidates, keyed by INN.
`GET /suppliers/{inn}/profile` renders: header (name — or the INN when unknown, never an invented name; INN copy; OGRN/KPP;
region; legal status; role badges; history vs. external badge; actions area Contact · Export JSON — a future "Request
quotation" is one more entry in `ProfileActions`, no placeholder button) · contacts (only returned values; per-value source,
check date, freshness and verified badges; call / copy phone / email / open website / copy address; "Contact data not available
from current verified sources" when empty; unconfirmed website candidate labelled separately) · company role (grouped per role,
strongest API status shown; VERIFIED solid green, UNDER_REVIEW amber, INFERRED dashed gray; every evidence item inspectable) ·
data freshness (last profile update, identity, contacts incl. source-page currency, last evidence check date; STALE/UNKNOWN never
hidden) · legal identity (registry fields + source) · observed procurement history (relations, awards, lots, last activity,
top OKPD2; worded as observed organizer data, not total market activity) · collapsed "Sources & evidence" (source type, URL,
check date, claims supported; evidence items with strength / valid-until; no raw payloads).
Enrichment states: NOT_ENRICHED (notice + "Enrich supplier profile" → `POST /suppliers/{inn}/enrich`), IN_PROGRESS (no second
trigger), PARTIAL (available data + reasons; retry when `retryable`), FAILED (reasons; retry with `refresh=true` when
`retryable`), call error (stored data kept, error + retry). `NEXT_PUBLIC_SUPPLIER_ENRICH=off` hides the trigger.
P5-001C (integration with the real P5-001A API): PARTIAL is presented as a valid result (info tone, "Refresh profile" is
cache-first); after a successful POST the screen re-reads `GET …/profile`. Contact absence reads "Verified contact information
has not yet been discovered." (EGRUL legal address still shown). Every source carries a provenance class: official FNS registry ·
company website · optional secondary provider (checko.ru — never labelled official) · historical procurement evidence · curated
regulatory evidence; the last enrichment run's per-source outcomes are listed. "Supplier" backed only by procurement awards is
shown as "Supplier — from procurement history", and a missing manufacturer/distributor role is stated explicitly.
`NEXT_PUBLIC_SUPPLIER_PROFILE_API_BASE_URL` (optional, defaults to `NEXT_PUBLIC_API_BASE_URL`) points the profile calls at the
API serving the enrichment database while it is separate from the search database (`supplier_radar_p5`).
Mock mode: synthetic fixtures (`src/mocks/supplier-360-fixtures.ts`, INNs `0000…`) listed at `/[locale]/supplier-360`;
view-model tests `npm test` (`frontend/tests/supplier-360.test.mjs`).

---

## S-00 Global shell

- Product name, navigation between Search / Results / Compare (tray count).
- **Demo-data notice** when synthetic seed data is active (BR-20: synthetic companies must never be presented as real).
- System status on degradation (from `/health`, optional).

## Cross-screen requirements

| Requirement | Source |
|---|---|
| Results and compare selection survive navigation to profile and back (no re-run) | US-08 |
| Every score shown has an explanation reachable in ≤1 interaction | NFR-EXP-01 |
| Unknown / missing values are shown explicitly as unknown, never as zero or blank | EC-30 |
| Scores displayed 0–100 integers; API provides 0–1 floats | ED-01 |
| All external links open with `rel="noopener noreferrer"`; untrusted text rendered as text, never HTML | NFR-SEC-01 |
| Accessibility: keyboard navigable, labeled controls, status by text not color alone | DoD |

---

## Design System mapping (P0-005)

> Decided with the owner on 2026-10-01 (ED-27, ED-28). Implemented in `/frontend` on the mock API; the live
> API is wired through the same client once P2-006/P6-001/P6-003 exist. Visual reference: `/ru/design-system`.

### Stack (confirmed, no new dependencies)
Next.js 16 App Router · React 19 · Tailwind CSS v4 (DS tokens only) · Radix (`radix-ui`) · next-intl (`ru` default, `en`; both LTR).
State: server data through `src/lib/api/client.ts` (`useAsync`); cross-screen state (compare tray, last run) in a
sessionStorage-backed context (`features/shell/session-store.tsx`); filters/overrides travel with the persisted
search run (`request_id` in the URL). No TanStack Query / Zustand (owner decision — revisit only if live API caching needs it).

### Data modes
| Mode | Switch | Behaviour |
|---|---|---|
| Mock (default) | `NEXT_PUBLIC_API_MODE` unset | In-browser stand-in for the backend (`src/mocks/server.ts`) over a synthetic corpus (`src/mocks/fixtures.ts`). Demo-data notice always visible (BR-20). "Demo scenario" panel on S-01 forces 503 / LLM fallback / semantic-down / slow. |
| Live | `NEXT_PUBLIC_API_MODE=live`, `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api/v1`); committed in `frontend/.env.development` / `.env.production` since P4-002 | Same `api.*` functions call FastAPI; error envelope (ED-07, or FastAPI `detail`) mapped to `ApiError`. Scenario panel hidden. Navigation shows only S-06 (the mock-only screens have no live endpoints); `/` opens S-06. |

Demo queries that reach every state: panels (normal, region, attributes) · laptops (quantity, RAM) · "только от производителя" (mandatory constraint) · desks (low-confidence set + `STALE_EXTERNAL_DATA`) · "Ледокол…" (zero results).

### Route map
| Screen | Route | Feature module |
|---|---|---|
| S-00 shell | `app/[locale]/(app)/layout.tsx` | `features/shell/*` |
| S-01 | `/[locale]/search` · refine: `/search?from=<request_id>` | `features/search/*` |
| S-02 | `/[locale]/results/<request_id>` (`/results` reopens the last run) | `features/results/*` |
| S-03 | `/[locale]/suppliers/<supplier_id>?request_id=<id>` | `features/supplier/*` |
| S-04 | `/[locale]/compare` | `features/compare/*` |
| S-05 | `/[locale]/history` | `features/history/*` |
| S-06 | `/[locale]/analysis?lot=<lot_id>` | `features/analysis/*` |
| S-07 | `/[locale]/supplier-360/<inn>?back=<path>` (mock-only fixture index: `/supplier-360`) | `features/supplier-360/*` |
Copy: `messages/{ru,en}/{shell,vocab,feedback,search,results,supplier,compare,history,analysis,marketProduct,supplier360}.json` (Russian first, keys in sync).

### S-00 Global shell
| Region / state | DS pattern |
|---|---|
| Navigation (Search · Results · Compare + count · History) | **TopBar** (DS extension; top header chosen instead of the sidebar `AppShell`) · `CountBadge` on Compare |
| Mobile < 960 px | TopBar dark 72 px header + start `Drawer` with the same nav |
| System status | Pill with status dot + text, `Tooltip` lists components (`/health`, polled 30 s) |
| Language | `LocaleSwitch` |
| Demo-data notice | Warning strip under the header (icon + text), always on in mock mode |
| Toasts | `ToastProvider` / `useToast` |
| Skip link | sr-only "skip to content" → `#main` |

### S-01 Search
| Region / state | DS pattern |
|---|---|
| Header | `PageHeader` (refine mode: back button to the run) |
| Query input | `Card` › `Field` (required, hint, error) › `Textarea` with counter (max 1000) |
| Market scope | `RadioCards` (3 options with hints) |
| Example queries | Pill chips (secondary-button style) |
| Submit | `Button` lg primary with `loading`; Ctrl+Enter |
| Parsed intent (refine) | `Card` + `FieldGrid`: `Input` (product, quantity), `TagInput` (categories, constraints), attribute rows (`Input` + ghost delete), `Combobox` (region), `MultiSelect` (supplier types); per-field origin `Badge` (Recognised / Edited / Not set); clear = ghost icon button |
| Parser mode indicator | `Badge` (rules · LLM · fallback) |
| Empty | Focused textarea + examples |
| Typing / invalid | `Field` error (`QUERY_TOO_SHORT` / `QUERY_TOO_LONG`) |
| Submitting > 1 s | `Spinner` + text in the form footer (`aria-live`) |
| Parser degraded | Fallback badge on the intent card + warning `Alert` on S-02 |
| Service unavailable | `Alert` danger with "Retry" |
| Explainer | `Card` + `IconChip` list (Match / Confidence / New suppliers) |

### S-02 Search Results
| Region / state | DS pattern |
|---|---|
| Header | `PageHeader` + secondary "Refine" + outline "New search" |
| Summary | 3 × `MetricCard` (found · new to AIS · known) + `Card panel` with `StackedBar` by type |
| Intent + filters summary | Outlined `Card` with `Badge` chips (edited = warning tone + sr text) + link "Edit" |
| Filters | Desktop: sticky side `Card` (280 px) — `RadioGroup` scope/type, `Combobox` region, `SwitchLabel` experience, `RadioGroup` min confidence, Reset/Apply. Mobile: same form in `Drawer` |
| Result card | `Card`: rank tile, name link, `MarketBadge` / `TypeBadge` (verified icon) / region, best offering, **CheckList** reasons, `RiskBadges` (`Badge` warning + `Tooltip` meaning), **ScoreStat** Match + Confidence side panel |
| Why matched (≤ 1 interaction) | Inline expansion: **ContributionList** (sums to Match) + **CheckList** + **EvidenceItem** list |
| Compare selection | `CheckboxLabel` on the card + **ActionBar** tray; limit → toast; other-search conflict → `ConfirmDialog` |
| Feedback | 3 icon toggle buttons (aria-pressed) + toast |
| Loading | `ResultCardSkeleton` × n |
| Zero results | `EmptyState` (summary and filters hidden, intent chips kept) + "Refine request" |
| Filtered-empty | `EmptyState` + "Reset filters" |
| Partial / degraded | Inline warning `Alert` listing `warnings[]` |
| Low-confidence set | Warning `Alert` (all top-5 < 0.4, OQ-26) |
| Error | `ErrorPanel` (`Alert` danger + retry); unknown run → `EmptyState` |
| Load more | Secondary button → new run with `limit + 20` (≤ 100) |

### S-03 Supplier Profile
| Region / state | DS pattern |
|---|---|
| Header | `PageHeader` (back → results without re-run) + compare toggle + "Back to results"; status badges row |
| Query context | `Card` (primary border): **ScoreStat** × 2, **CheckList**, **ContributionList**, feedback |
| Offerings / History / Evidence | `Card` › `TabsHeader` › segmented `Tabs` with `TabsCount`; offerings list + `Pagination`; history `Table` (cards < 1150 px) + `Pagination`; **EvidenceItem** list |
| Identity | `Card` + `DescriptionList` (2 cols, `--` for missing, LTR codes) |
| Role / basis | `TypeBadge` + basis with **ExternalLink**, or unverified text |
| Confidence breakdown | **ScoreStat** + 5 rows (`Progress` + value or "no data" + weight) |
| Risks | **CheckList** risk tone with meanings / positive "none" |
| Sources & data quality | List with observed date + "Demo" `Badge`; quality flags as gray `Badge`s |
| Loading / not found / redirected / context expired | `PageSkeleton` / `EmptyState` / info `Alert` / warning `Alert` |
| Empty sections | `EmptyState size="small"` with explicit text (never blank) |

### S-04 Compare Suppliers
| Region / state | DS pattern |
|---|---|
| Table | **CompareTable** (sticky label column, sections, horizontal scroll on mobile) |
| Scores / attributes | **ScoreStat** sm, `TypeBadge`, `MarketBadge`, `RiskBadges`, **ExternalLink** |
| Contribution rows | Points per feature; top-2 spread rows highlighted (fill + text label) |
| "Why A above B" | Info `Alert` naming the leading features (from returned contributions) |
| Missing values | "—" with `Tooltip` reason + sr-only text, never 0 |
| < 2 selected / empty | `EmptyState` + link back to results |
| 6th selection | Toast (blocked in the tray) |
| Different searches | Tray is scoped to one `request_id`; conflict → `ConfirmDialog` "start new" |
| No run context | Warning `Alert`, scores shown as "—" |

### S-05 Search History
List-page recipe: `PageHeader` + primary "New search" → `TableCard` › `TableToolbar` (title + filter `Input`) › `Table`
(query link, date, result count, scope `Badge`, open action) › `TableFooter` with `Pagination`. Empty → `Card` + `EmptyState`;
no filter match → `TableEmpty` + `EmptyState`. Reopening uses the persisted run (no re-run).

### DS gaps → library extensions (tokens only, shown in the gallery section "Supplier Radar extensions")
| Gap | Component | File |
|---|---|---|
| Top navigation shell | `TopBar` | `components/layout/top-bar.tsx` |
| Score display 0–100 with explicit unknown | `ScoreStat`, `ScorePill` | `components/ui/score.tsx` |
| Contribution bar breakdown | `ContributionList` | `components/ui/contribution-list.tsx` |
| Reason / risk checklist (icon + text) | `CheckList` | `components/ui/check-list.tsx` |
| Evidence row with source + date | `EvidenceItem` | `components/ui/evidence-item.tsx` |
| Safe external link | `ExternalLink` | `components/ui/external-link.tsx` |
| Transposed comparison table | `CompareTable` (+ Head/Row/Cell/Section) | `components/ui/compare-table.tsx` |
| Floating tray | `ActionBar` | `components/ui/action-bar.tsx` |
| Fix | `DescriptionList` wide items no longer force 3 columns when `columns={2}` | `components/ui/description-list.tsx` |

### Contract notes for P1-008 / P6 (additive, [ER])
The UI types in `src/lib/api/types.ts` mirror API_CONTRACTS plus these proposed optional fields — confirm when the contracts are written:
`SearchResult.supplier_type_verified`, `SearchResult.reason_params` (template parameters, e.g. contract count),
`SearchResponse.created_at / filters / intent_overrides / limit / synthetic_data`, `SearchIntent.quantity` (G-06),
`filters.has_experience / min_confidence`, `SupplierProfile.context_status / redirected_from`,
`GET /api/v1/searches` (list for S-05; not in the endpoint inventory yet).
