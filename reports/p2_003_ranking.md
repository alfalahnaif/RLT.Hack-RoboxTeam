# P2-003 — Explainable Supplier Ranking Improvement (DEV only)

> Candidate pool: frozen (P1-002 retrieval, lot fusion, historical_lot_limit); identical across all configurations (asserted). **HOLDOUT: not evaluated (sealed).** Labels are weak (unjudged ≠ irrelevant).

**Chosen: `C2 relevance-dominant`** — accepted challengers: ['C2 relevance-dominant'].

## Selection rule (declared before the results)

- delta weighted nDCG@10 >= +0.01 vs B0 AND paired-bootstrap 90% CI lower bound > 0
- delta weighted winner Recall@10 >= -0.005
- identical candidate pools (asserted)
- no OKPD2 stratum with >= 10 DEV queries loses more than 0.05 unweighted nDCG@10
- Primary metric: population-weighted nDCG@10; choose: highest weighted nDCG@10 among accepted challengers; if none is accepted keep B0

## Configurations tested

| Configuration | Rationale | w-nDCG@10 | Δ (90% CI) | nDCG@10 | W-R@10 | Cond. R@10 | MRR | Accepted | Scoring ms/query |
|---|---|---:|---|---:|---:|---:|---:|:-:|---:|
| B0 baseline (P1-002) | frozen reference | 0.4638 | — | 0.5056 | 0.6533 | 0.7286 | 0.3885 | — | 49.44 |
| C1 quality over volume | volume (historical_relevance) is the dominant cause in 29/73 failures: top-3 mean relevance replaces the saturated sum | 0.4695 | +0.0057 [-0.0053, +0.0165] | 0.5139 | 0.66 | 0.7361 | 0.408 | no | 48.8 |
| C2 relevance-dominant | volume components (relevance sum + awards) dominant in 41/73 failures: shift weight to query relevance | 0.4794 | +0.0156 [+0.0054, +0.0266] | 0.5247 | 0.6633 | 0.7398 | 0.4071 | yes | 51.16 |
| C3 no customer signal | required comparison: incumbent effect of same-customer history | 0.4447 | -0.0191 [-0.0294, -0.0091] | 0.491 | 0.6333 | 0.7063 | 0.3708 | no | 62.58 |
| C4 no recency | recency comparison: 1-year half-life vs none | 0.4616 | -0.0022 [-0.0052, +0.0005] | 0.5055 | 0.6533 | 0.7286 | 0.3916 | no | 55.25 |
| C5 recency 2-year half-life | recency comparison: 1-year vs 2-year half-life | 0.4615 | -0.0023 [-0.0052, +0.0001] | 0.5051 | 0.6533 | 0.7286 | 0.3885 | no | 48.55 |
| C6 multi-item coverage | bounded query-item coverage for multi-item queries (28/73 failures multi-item) | 0.4662 | +0.0024 [-0.0011, +0.0056] | 0.5077 | 0.65 | 0.7249 | 0.3896 | no | 51.39 |
| C7 redundant-text down-weight | generic rule: halve the product_text weight when every item text ~ the subject (5612123 class) | 0.4618 | -0.0020 [-0.0039, -0.0004] | 0.502 | 0.6467 | 0.7212 | 0.3834 | no | 59.87 |
| C8 quality + coverage | combined query-relative variant (C1 + C6) | 0.4701 | +0.0062 [-0.0052, +0.0182] | 0.5143 | 0.6533 | 0.7286 | 0.4089 | no | 54.42 |

## Baseline vs chosen

| Metric | Baseline unweighted | Chosen unweighted | Baseline weighted | Chosen weighted |
|---|---:|---:|---:|---:|
| winner_recall@1 | 0.2633 | 0.28 | 0.2208 | 0.2346 |
| winner_recall@5 | 0.5533 | 0.5667 | 0.4827 | 0.5059 |
| winner_recall@10 | 0.6533 | 0.6633 | 0.6098 | 0.617 |
| winner_recall@20 | 0.7467 | 0.75 | 0.7004 | 0.7098 |
| winner_mrr | 0.3885 | 0.4071 | 0.3387 | 0.3528 |
| ndcg@10 | 0.5056 | 0.5247 | 0.4638 | 0.4794 |
| ndcg@20 | 0.5389 | 0.5559 | 0.4962 | 0.5101 |
| candidate_winner_coverage | 0.8967 | 0.8967 | 0.9041 | 0.9041 |

## Conditional ranking metrics (winner already in the candidate pool)

| Metric | Baseline | Chosen | Baseline weighted | Chosen weighted |
|---|---:|---:|---:|---:|
| winner_recall@1 | 0.2937 | 0.3123 | 0.2442 | 0.2595 |
| winner_recall@5 | 0.6171 | 0.632 | 0.5339 | 0.5596 |
| winner_recall@10 | 0.7286 | 0.7398 | 0.6744 | 0.6824 |
| winner_recall@20 | 0.8327 | 0.8364 | 0.7747 | 0.785 |
| winner_mrr | 0.4332 | 0.4541 | 0.3746 | 0.3902 |
| ndcg@10 | 0.5497 | 0.57 | 0.4958 | 0.5125 |
| queries with winner in pool | 269 | 269 | | |

## Difficulty — retrieval failure vs ranking

| Difficulty | Queries | Retrieval failures | Winner in pool | Cond. R@10 baseline | Cond. R@10 chosen | nDCG@10 baseline | nDCG@10 chosen |
|---|---:|---:|---:|---:|---:|---:|---:|
| EASY | 253 | 3 | 250 | 0.764 | 0.78 | 0.5633 | 0.5856 |
| MEDIUM | 22 | 9 | 13 | 0.3846 | 0.3077 | 0.2547 | 0.2455 |
| HARD | 25 | 19 | 6 | 0.0 | 0.0 | 0.1431 | 0.1548 |

## OKPD2 strata (nDCG@10)

| Stratum | Queries | Baseline | Chosen |
|---|---:|---:|---:|
| A | 5 | 0.4048 | 0.4622 |
| B | 9 | 0.7842 | 0.7835 |
| C | 71 | 0.4084 | 0.4214 |
| D | 2 | 0.5413 | 0.5413 |
| E | 11 | 0.6246 | 0.6461 |
| F | 16 | 0.3879 | 0.4304 |
| G | 10 | 0.524 | 0.5657 |
| H | 7 | 0.3246 | 0.3646 |
| I | 2 | 0.2606 | 0.4131 |
| J | 14 | 0.5243 | 0.5315 |
| K | 14 | 0.8037 | 0.8084 |
| L | 4 | 0.4207 | 0.4625 |
| M | 25 | 0.4902 | 0.5311 |
| MULTI | 10 | 0.5088 | 0.5441 |
| N | 23 | 0.5058 | 0.5128 |
| O | 10 | 0.6717 | 0.6751 |
| P | 27 | 0.5554 | 0.5695 |
| Q | 18 | 0.5134 | 0.5082 |
| R | 5 | 0.3239 | 0.3521 |
| S | 16 | 0.5991 | 0.6164 |
| U | 1 | 0.0 | 0.0 |

## Customer signal (with vs without)

- With: weighted nDCG@10 0.4638, top-10 suppliers with same-customer history 36.8%.
- Without (C3): weighted nDCG@10 0.4447, top-10 with same-customer history 31.4%.
- Removing it lowers quality significantly (CI excludes 0), so it stays a supporting signal (weight 0.05). It does raise the share of incumbents in the top 10 by about 5 points — a known, visible trade-off, not lock-in.

## Golden cases (inspected after the freeze; not tuned on)

| Lot | P1-002 winner rank | P2-003 winner rank | Change |
|---|---:|---:|---|
| 5542696 | 19 | 11 | better |
| 5545252 | 17 | 16 | better |
| 5612123 | 27 | 32 | worse |
| 5718896 | 1 | 1 | same |
| 6022687 | 7 | 7 | same |

## Latency (end-to-end, DEV, chosen)

p50 666.8 ms · p95 3495.9 ms · max 6199.8 ms · mean 1039.4 ms. Retrieval is unchanged; scoring + lot aggregation cost per query is in the table above.

## Remaining failures (chosen)

Query groups: {'ranked_top10': 199, 'ranking_failure (in pool, rank > 10)': 70, 'retrieval_failure (winner not in pool)': 31}

Dominant causes: {'historical_relevance': 13, 'okpd2': 23, 'product_text': 27, 'relevant_awards': 6, 'same_customer': 1} — after the change, failures are mostly driven by weaker product-text and OKPD2 matches of the winner (relevance), no longer by incumbent volume.

### Pairwise examples

**rpl-5512483** (EASY, 2 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 1.000 | 0.050 | 0.100 | 0.300 | 0.350 | 0.050 | 0.100 | 0.050 | 117 | 51 | 98 | yes |
| immediately_above | 11 | 0.864 | 0.000 | 0.076 | 0.300 | 0.350 | 0.048 | 0.091 | 0.000 | 18 | 18 | 0 |  |
| winner | 12 | 0.850 | 0.049 | 0.093 | 0.300 | 0.350 | 0.048 | 0.010 | 0.000 | 32 | 1 | 32 |  |

**rpl-5524182** (EASY, 8 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.930 | 0.048 | 0.091 | 0.300 | 0.312 | 0.049 | 0.079 | 0.050 | 44 | 17 | 33 | yes |
| immediately_above | 15 | 0.756 | 0.025 | 0.068 | 0.300 | 0.237 | 0.049 | 0.077 | 0.000 | 21 | 16 | 8 |  |
| winner | 16 | 0.735 | 0.017 | 0.026 | 0.240 | 0.312 | 0.049 | 0.040 | 0.050 | 5 | 5 | 4 | yes |

**rpl-5524232** (EASY, 2 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.797 | 0.050 | 0.100 | 0.233 | 0.268 | 0.047 | 0.100 | 0.000 | 145 | 143 | 143 |  |
| immediately_above | 15 | 0.615 | 0.022 | 0.030 | 0.233 | 0.268 | 0.047 | 0.016 | 0.000 | 6 | 2 | 6 |  |
| winner | 16 | 0.600 | 0.030 | 0.042 | 0.233 | 0.231 | 0.050 | 0.016 | 0.000 | 10 | 2 | 10 |  |

**rpl-5528109** (EASY, 1 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.938 | 0.048 | 0.096 | 0.300 | 0.350 | 0.050 | 0.095 | 0.000 | 62 | 33 | 39 |  |
| immediately_above | 26 | 0.593 | 0.018 | 0.023 | 0.300 | 0.222 | 0.030 | 0.000 | 0.000 | 5 | 0 | 5 |  |
| winner | 27 | 0.567 | 0.011 | 0.013 | 0.300 | 0.128 | 0.043 | 0.021 | 0.050 | 3 | 3 | 3 | yes |

**rpl-5530573** (EASY, 1 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.689 | 0.025 | 0.034 | 0.300 | 0.224 | 0.044 | 0.011 | 0.050 | 11 | 2 | 11 | yes |
| immediately_above | 132 | 0.288 | 0.006 | 0.008 | 0.000 | 0.224 | 0.050 | 0.000 | 0.000 | 2 | 0 | 2 |  |
| winner | 133 | 0.288 | 0.006 | 0.008 | 0.000 | 0.224 | 0.050 | 0.000 | 0.000 | 2 | 0 | 2 |  |

**rpl-5531133** (EASY, 1 item(s), text redundant: True)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.831 | 0.050 | 0.096 | 0.300 | 0.288 | 0.050 | 0.049 | 0.000 | 58 | 8 | 58 |  |
| immediately_above | 16 | 0.697 | 0.013 | 0.016 | 0.300 | 0.294 | 0.048 | 0.026 | 0.000 | 2 | 2 | 2 |  |
| winner | 17 | 0.694 | 0.017 | 0.031 | 0.300 | 0.264 | 0.050 | 0.032 | 0.000 | 6 | 4 | 4 |  |

**rpl-5531373** (EASY, 1 item(s), text redundant: True)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.963 | 0.046 | 0.081 | 0.300 | 0.350 | 0.050 | 0.086 | 0.050 | 31 | 22 | 29 | yes |
| immediately_above | 35 | 0.550 | 0.005 | 0.007 | 0.300 | 0.195 | 0.033 | 0.011 | 0.000 | 1 | 1 | 1 |  |
| winner | 36 | 0.549 | 0.022 | 0.029 | 0.300 | 0.145 | 0.047 | 0.006 | 0.000 | 7 | 1 | 7 |  |

**rpl-5531678** (EASY, 8 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.810 | 0.050 | 0.094 | 0.240 | 0.256 | 0.050 | 0.071 | 0.050 | 55 | 15 | 55 | yes |
| immediately_above | 16 | 0.592 | 0.023 | 0.031 | 0.225 | 0.246 | 0.049 | 0.018 | 0.000 | 7 | 2 | 7 |  |
| winner | 17 | 0.580 | 0.030 | 0.043 | 0.214 | 0.187 | 0.050 | 0.006 | 0.050 | 12 | 1 | 12 | yes |

## Limitations

- Gains are modest (one accepted challenger, Δ weighted nDCG@10 ≈ +0.016); ranking signals of this lexical/history feature family are close to saturation.
- 31/300 DEV queries are retrieval failures (winner absent from the pool): no ranking change can fix them (HARD: 19/25).
- MEDIUM conditional R@10 moved 0.385 → 0.308 on 13 queries (one query) — noise-level, reported for transparency.
- The generic text-redundancy rule hurt on DEV and was not adopted; golden case 5612123 (item text = subject) remains a known regression.
- Weak labels: unjudged suppliers are not proven irrelevant.
