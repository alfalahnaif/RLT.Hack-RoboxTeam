# Evaluation & Benchmark Methodology

> ### Hackathon Day-1 amendment (2026-10-01, ADR-H1 / HD-06)
> **Primary evaluation = temporal historical replay on real data** ([Baseline §8, §13–14](../HACKATHON_EXECUTION_BASELINE.md), [dataset analysis §8](../analysis/REAL_DATASET_ANALYSIS_2024_2025.md#8-temporal-replay-feasibility-)):
> - Cases: ЭМ lots (2025 primary: 79,047 lots with winner + ≥ 2 participants + items); `as_of = publish_date` (strictly earlier lots only).
> - Weak labels: **2 = actual winner · 1 = actual participant · 0/unjudged = not observed** (not proven irrelevant — BR-22). АИС ГЗ lots give winner-only labels.
> - Split by time: dev = 2025-01…06, holdout = 2025-07…12 (+ ЭМ 2024 warm-up); golden demo lots excluded from tuning.
> - Metrics: hit@5/10/20 of winner and participants, MRR, nDCG@10 (2/1 gains), latency; reason-code/evidence coverage.
> - Baseline: historical keyword + OKPD2 lookup (naive award count) — a strong baseline (92.5% of winners have prior same-class history).
> - **§2 seed benchmark (v0.1.0 / v0.2.0) is superseded** as the first benchmark (HD-01); it may only serve as unit-test fixtures.
> - **Realized (P1-001E, 2026-10-01):** `benchmark/replay/` v1.0.0 — 300 dev / 300 holdout / 50 warm-up ЭМ queries from 35,829 / 43,211 / 40,558
>   eligible lots; sqrt-proportional OKPD2-section stratification with `stratum_weight` for population-weighted metrics; difficulty (natural, not
>   selected): dev 253 EASY / 22 MEDIUM / 25 HARD, holdout 267 / 16 / 17; leakage probe 0 violations. Generator/validator: `python -m app.cli benchmark generate|validate`.
> - §6 targets: kept as aspirations; latency acceptance bound ≤ 10 s (C-27); discovery target is measured on curated external candidates, not on replay.

> Sources: Strategy §8–9; Phase 0 §64–71, §90; P1-001 §18–45.
> The benchmark is a first-class product artifact: **"No accuracy claim without a metric"** (BR-23).

## 1. What we compare
- **Baseline:** PostgreSQL keyword/FTS only (`mode=baseline`).
- **Challenger:** Hybrid Supplier Radar (`mode=hybrid`).
Same `SearchService` code path, same corpus, same aggregation → differences are attributable to retrieval + ranking.

## 2. Benchmark datasets

| Dataset | Version | Content | Purpose | Credibility |
|---|---|---|---|---|
| **Seed benchmark** | 0.1.0 (P1) → 0.2.0 (P3) | Synthetic corpus (≥100 suppliers / ≥200 offerings; preferred 200/500), 10 → 20–30 Russian queries, designed qrels | Engineering development & regression | **Low for external claims** — designed by the team (R-09). Never presented as market performance (BR-20). |
| **Real benchmark** [ER] | 1.0.0 (P4) | Organizer data; queries from real procurement titles/descriptions; weak labels (winners/participants) + human grading; cutoff dates | Pitch metrics, temporal holdout | High — required for jury claims |

### Files (P1-001 §26–30)
- `benchmark/queries.csv`: `query_id, query_text, category, difficulty(easy|medium|hard), cutoff_date?, notes` (+ `split` dev|holdout [ER]).
- `benchmark/qrels.csv`: `query_id, supplier_id, relevance_grade(0|1|2), judgment_source(seed_design|human|historical), notes`.
- `benchmark/benchmark_manifest.json`: name, version, created_at, counts, relevance scale, notes (+ corpus/index/embedding versions [ER]).

### Seed benchmark design rules
- 10 initial queries: **4 easy / 4 medium / 2 hard** (P1-001 §28); 10 categories: interactive displays, laptops/computers, office printers, office furniture, medical gloves, cleaning products, industrial pumps, LED lighting, security cameras, network equipment.
- Per query anchors: 2–4 strong (grade 2), 1–3 plausible (grade 1), 2–5 distractors (grade 0); 3–8 relevant overall.
- Known/external mix ~60–70% / 30–40%; type mix ~30/30/30/5/5; ~20% incomplete profiles; marked duplicate fixtures.
- Market-scope coverage: known-relevant, external-relevant, known-irrelevant, external-irrelevant per benchmark.
- Hard queries are preserved even if baseline fails (BR-21). Generator: deterministic, `random_seed=42`, UUIDv5, 70% background / 30% anchors.

### Splits
Target 30 queries = **20 dev + 10 frozen holdout**; minimum 20 meaningful queries (MVP gate). Holdout never used for tuning.

## 3. Relevance grades
`0 irrelevant · 1 plausible supplier · 2 strongly relevant supplier` → enables nDCG.
Ground truth = weak labels (winner, participants, previous similar procurements) + human review of a subset. **Winner ≠ only relevant supplier** (BR-22).

## 4. Metrics

| Metric | Definition (supplier level) | Role |
|---|---|---|
| **nDCG@10** | graded gain `2^rel − 1`, log2 discount [ER: formula choice] | **Primary** ranking metric |
| Precision@5 | share of Top 5 with grade ≥ 1 [ER: threshold] | Top quality |
| Recall@20 | relevant (grade ≥ 1) retrieved in Top 20 / all judged relevant | Coverage |
| MRR | 1 / rank of first relevant | First-hit quality |
| Coverage | share of queries returning ≥ N results [ER: N = 5] | Robustness |
| Evidence coverage | share of Top 5 results with ≥ 1 source evidence | Explainability |
| Reason-code coverage | share of Top 5 with non-empty reason codes (target 100%) | Explainability |
| New suppliers discovered | per query: # external suppliers with grade ≥ 1 in Top 20 **and evidence** | Market expansion |
| Latency P50 / P95 | per stage and total | Usability |
Unjudged results count as non-relevant and are listed for judging (EC-51). Queries without relevant suppliers are reported separately (EC-50).

## 5. Temporal holdout (strongest experiment)
1. Select historical procurements (organizer data) with known winners/participants.
2. `cutoff = procurement_date` (minus publication lag if known — OQ-30).
3. Build query from procurement title/description.
4. Run `SearchService.search(query, as_of=cutoff)` — **every** branch, feature, flag and evidence item filtered to valid-time ≤ cutoff (ED-04).
5. Measure: hit rate of eventual winner/participants in Top 5/10/20; MRR.
6. Report leakage safeguards used. Question answered: *"Could our system have discovered this supplier before the procurement happened?"*

## 6. Success targets (Phase 0 §71)

| Target | Value | Notes |
|---|---|---|
| Ranking | nDCG@10 **≥ +10% relative** vs baseline | On holdout |
| Recall guard | Recall@20 not reduced by more than **5%** | Relative vs absolute unspecified — G-24 (proposed: relative) |
| Discovery | For ≥ **70% of suitable queries**, ≥ **2 evidence-backed external/new suppliers** | "Suitable" undefined — G-24 (proposed: queries whose qrels contain ≥ 2 external grade ≥ 1 suppliers) |
| Explainability | **100%** of Top 5 have reason codes | |
| Evidence | **≥ 90%** of Top 5 have source evidence | vs NFR "every" — C-12 |
| Latency | indexed P95 ≤ 2.5 s; full P95 ≤ 5 s | |

## 7. Outputs
- `evaluation_report.json` per run: versions (benchmark, corpus, index, embedding, parser, ranking), per-query metrics, aggregates per split and difficulty, baseline vs hybrid deltas, latency percentiles.
- Human-readable summary (markdown) + error-analysis table (failure categories: vocabulary gap, attribute miss, category miss, aggregation error, data gap).
- **Claims register** (P7-007): each pitch claim ↔ report + metric + dataset version.

## 8. Discipline
Baseline first (D-10, BR-42) · benchmark starts early (Phase 1) · tune on dev only · bump version on any judgment change · rerun both modes after any contract, corpus, or ranking change · no manual edits to generated seed.
