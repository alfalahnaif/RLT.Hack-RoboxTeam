# Temporal replay benchmark v1.0.0 (P1-001E)

Question: *had Supplier Radar existed before lot L was published (date T), could it have surfaced the suppliers later observed on L?*

| File | Content |
|---|---|
| `queries.csv` | `query_id, lot_id, publish_date, split, platform` — 50 warm-up (2024-H2), **300 dev (2025-H1)**, **300 holdout (2025-H2, sealed)** |
| `qrels.csv` | `query_id, supplier_id, relevance_grade, is_winner` — supplier UUIDs only (no INNs) |
| `query_metadata.csv` | stratum, `stratum_weight` (eligible ÷ selected), items/codes/relations counts, generic title, winner-history flags, difficulty |
| `manifest.json` | versions, ingestion delivery, source hashes, schema revision, seed, eligibility, temporal rule, splits, counts, label semantics, limitations, file sha256 |

**Rules.** ЭМ lots with items, ≥ 1 winner and ≥ 2 observed relations; golden demo lots excluded. A system answering a query may use
only facts with `publish_date < T` (strict; `app.benchmark.temporal.VISIBLE_HISTORY_SQL` / `visible_history()`).

**Labels are weak.** 2 = observed winner · 1 = observed non-winner · anything else is **unjudged**, not irrelevant (the supplier
simply did not appear in the delivered ЭМ rows). Prefer recall/hit-rate/MRR/nDCG on judged suppliers; never present precision as truth.

**Never tune on `holdout`.** Use `dev` for development; report `holdout` once at the end (P5).

Regenerate / validate (byte-identical, ~1 min):
```bash
docker compose run --rm backend python -m app.cli benchmark generate
docker compose run --rm backend python -m app.cli benchmark validate
```
Report: `reports/benchmark_seed_report.{json,md}`.
