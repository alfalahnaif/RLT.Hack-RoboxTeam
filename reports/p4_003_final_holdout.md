# P4-003 — Final HOLDOUT Evaluation & Model Freeze

## 1. Frozen state (recorded before the holdout was opened)

| Item | Value |
|---|---|
| Branch / commit evaluated | `integration/hackathon-final` @ `31517a9e716d79046dcc92164b4bc829ff3ce05f` |
| Final configuration | `DEFAULT_CONFIG = P2_001_SEMANTIC` (S3) |
| Retrieval | lexical + technical + OKPD2 + semantic, `semantic_top_k = 100` |
| Ranking weights | P2-003, unchanged: `w_product_text 0.35`, `w_okpd2 0.30`, `w_historical_relevance 0.10`, `w_relevant_awards 0.10` |
| Model | `intfloat/multilingual-e5-small @ 614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| Semantic index | HNSW READY, 993,289 texts |
| Benchmark | `supplier-radar-temporal-replay 1.0.0` (EM lots only). File SHA-256 values equal `manifest.json`: queries `31fcf0f5…`, qrels `c5eb5b84…`, metadata `4821f998…` |
| DEV / HOLDOUT size | 300 / 300 queries |
| HOLDOUT difficulty (pre-assigned) | EASY 267 · MEDIUM 16 · HARD 17 |
| DEV difficulty (pre-assigned) | EASY 253 · MEDIUM 22 · HARD 25 |

### How the holdout was evaluated

- **Script:** `scripts/p4_003_final_holdout.py`, a one-off evaluation record.
  - It runs the same per-query pipeline as the DEV semantic experiment.
  - It calls the existing functions unchanged: `query_metrics`, `aggregate`, `conditional`, `paired_bootstrap`.
  - It uses the same failure taxonomy as DEV.
  - It refuses to write a second holdout result.
- **Dry run on DEV first:** before the holdout was opened, the script was run on DEV ([p4_003_dev_reproduction.json](p4_003_dev_reproduction.json)). It reproduced **every** published DEV metric of all three frozen configurations exactly: unweighted, weighted, conditional, by difficulty, and the failure taxonomy 4 / 10 / 12 / 5.
- **The holdout run:** done once, completed without error, runtime 567 s.

## 2. Final system (P2-001 S3) — DEV vs HOLDOUT

| Metric | DEV unweighted | **HOLDOUT unweighted** | DEV weighted | **HOLDOUT weighted** |
|---|---:|---:|---:|---:|
| Candidate winner coverage | 0.9067 | **0.9200** | 0.9013 | **0.8886** |
| Candidate observed-supplier coverage | 0.8999 | **0.9061** | 0.9010 | **0.8812** |
| Winner Recall@1 | 0.2867 | **0.3433** | 0.2372 | **0.2658** |
| Winner Recall@5 | 0.5600 | **0.6433** | 0.4911 | **0.5493** |
| Winner Recall@10 | 0.6633 | **0.7333** | 0.6135 | **0.6346** |
| Winner Recall@20 | 0.7533 | **0.8233** | 0.7107 | **0.7505** |
| MRR | 0.4110 | **0.4713** | 0.3540 | **0.3924** |
| nDCG@10 | 0.5268 | **0.5608** | 0.4786 | **0.4951** |
| nDCG@20 | 0.5596 | **0.5932** | 0.5103 | **0.5312** |
| Candidates per query | 125.9 | **123.2** | 143.4 | **149.5** |

- **Conditional on the winner being in the candidate pool (HOLDOUT, 276 queries):**
  - unweighted: R@10 0.7971, nDCG@10 0.6003
  - weighted: R@10 0.7141, nDCG@10 0.5383
- **Weighted** = population-weighted by the benchmark's pre-assigned `stratum_weight`.
- **Weak labels:** a supplier not observed on a lot is not proven irrelevant.

## 3. Frozen baselines on HOLDOUT (interpretation only — no selection)

| Configuration | Coverage | R@1 | R@5 | R@10 | R@20 | MRR | nDCG@10 | nDCG@20 | w-nDCG@10 | w-R@10 | w-coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A P1-002 baseline | 0.9133 | 0.3300 | 0.6233 | 0.7133 | 0.8100 | 0.4589 | 0.5469 | 0.5795 | 0.4847 | 0.6295 | 0.8883 |
| B P2-003 ranking | 0.9133 | 0.3300 | 0.6233 | 0.7267 | 0.8133 | 0.4656 | 0.5590 | 0.5882 | 0.4874 | 0.6259 | 0.8883 |
| **C P2-001 S3 (final)** | **0.9200** | **0.3433** | **0.6433** | **0.7333** | **0.8233** | **0.4713** | **0.5608** | **0.5932** | **0.4951** | **0.6346** | **0.8886** |

Same configurations on DEV, for reference (published values, reproduced exactly):

| Configuration | Coverage | R@10 | MRR | nDCG@10 | w-nDCG@10 |
|---|---:|---:|---:|---:|---:|
| A P1-002 | 0.8967 | 0.6533 | 0.3885 | 0.5056 | 0.4638 |
| B P2-003 | 0.8967 | 0.6633 | 0.4071 | 0.5247 | 0.4794 |
| C S3 | 0.9067 | 0.6633 | 0.4110 | 0.5268 | 0.4786 |

Paired bootstrap (existing method: weighted, 2,000 resamples, 90% percentile CI):

| Comparison | DEV Δ [CI90] | HOLDOUT Δ [CI90] |
|---|---|---|
| C vs B, weighted nDCG@10 | −0.0008 [−0.0104, +0.0089] | **+0.0078 [−0.0015, +0.0164]** |
| C vs B, weighted R@10 | −0.0035 [−0.0216, +0.0129] | +0.0087 [−0.0196, +0.0369] |
| C vs B, weighted coverage | −0.0029 [−0.0193, +0.0098] | +0.0003 [−0.0247, +0.0252] |
| B vs A, weighted nDCG@10 | +0.0156 [+0.0054, +0.0266] | +0.0027 [−0.0087, +0.0133] |
| B vs A, weighted R@10 | +0.0073 [−0.0020, +0.0177] | −0.0036 [−0.0279, +0.0187] |
| C vs A, weighted nDCG@10 | +0.0147 [+0.0035, +0.0263] | +0.0105 [−0.0027, +0.0225] |

What this shows:

- **Final vs P2-003 (C vs B):** on HOLDOUT the final system is at least as good as P2-003 on every unconditional metric, unweighted and weighted. The exception is conditional unweighted nDCG@10 (0.6003 vs 0.6024). Every CI includes 0.
- **P2-003 vs P1-002 (B vs A):** the DEV ranking gain (+0.016 weighted nDCG@10, CI above 0) did **not** clearly replicate on HOLDOUT (+0.003, CI includes 0).
- **Final vs P1-002 (C vs A):** +0.011 weighted nDCG@10 on HOLDOUT, but the CI includes 0.
- These are measurements only. No configuration was selected or changed because of them.

## 4. Difficulty breakdown (pre-assigned labels, unweighted)

| Difficulty | Queries (H) | Coverage A / B / **C** (HOLDOUT) | R@10 A / B / **C** (HOLDOUT) | Coverage C (DEV) | R@10 C (DEV) |
|---|---:|---|---|---:|---:|
| EASY | 267 | 0.9700 / 0.9700 / **0.9775** | 0.7865 / 0.8015 / **0.8090** | 0.9881 | 0.7708 |
| MEDIUM | 16 | 0.5625 / 0.5625 / **0.5625** | 0.1875 / 0.1875 / **0.1875** | 0.5909 | 0.1818 |
| HARD | 17 | 0.3529 / 0.3529 / **0.3529** | 0.0588 / 0.0588 / **0.0588** | 0.3600 | 0.0000 |

MEDIUM and HARD are small groups (16 and 17 holdout queries), so their rates move in steps of about 6 percentage points.

## 5. Retrieval-failure analysis (final S3 only, same taxonomy as DEV)

The analysis covers queries where P2-003 (the lexical/OKPD2 pool) misses every winner; the status column is under S3.

| Category | DEV (31 failures) | **HOLDOUT (26 failures)** |
|---|---:|---:|
| Recovered by semantic retrieval | 5 | **5** (EASY 3, MEDIUM 1, HARD 1) |
| Unseen supplier before cutoff | 4 | **5** |
| No relevant historical procurement (best history cosine < 0.86) | 10 | **7** |
| Related history outside cap / lot limit | 12 | **9** |

Winner-pool movement, S3 vs P2-003, on HOLDOUT:

- 5 queries recovered, 3 lost (lost = semantic lots displaced lexical lots inside the historical-lot limit); net +2.
- Queries with no winner in the S3 pool: **24 / 300**.
- Recovered winners' ranks: 12, 42, 55, 71 and 123.
- All 5 recovered winners carry semantic evidence.

## 6. Demo cases (runtime sanity only; neither lot is in the benchmark)

| Lot | Result |
|---|---|
| 5956101 | HTTP 200 · COMPLETE · `P2_001_SEMANTIC` · semantic on, no warnings · 20 results · 10.51.11.141 = VERY_HIGH / EXPANSION_RECOMMENDED / 4 VERIFIED + 2 UNDER_REVIEW |
| 5718896 | HTTP 200 · COMPLETE · `P2_001_SEMANTIC` · semantic on · 20 results |

## 7. Governance

- **Prior state:** HOLDOUT was sealed. Every earlier report records it as `NOT EVALUATED (sealed)`: P1-002, P2-003, P2-001.
- **This evaluation:** the first and only one, run exactly once with the frozen final system.
- **Configurations scored:** only three configurations already frozen in code (`P1_002_BASELINE`, `P2_003_RANKING`, `P2_001_SEMANTIC`). No challenger was created, and nothing was selected using HOLDOUT.
- **No changes after the holdout:** no ranking weights, `semantic_top_k`, thresholds, cosine calibration, candidate limits, HNSW parameters, OKPD2 logic or scoring logic were changed after (or for) the holdout.
- **Files committed:** this report, `p4_003_final_holdout.json`, `p4_003_dev_reproduction.json` and the evaluation script. No product code changed.
