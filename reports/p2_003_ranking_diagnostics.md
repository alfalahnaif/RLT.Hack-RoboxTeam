# P2-003 — Ranking Error Diagnosis (DEV, frozen P1-002 baseline)

> ranking failure = winner in candidate pool and best winner rank > 10. Candidate pool fixed. HOLDOUT not used. Baseline reproduced: {'candidate_winner_coverage': {'now': 0.8967, 'p1_002': 0.8967}, 'ndcg@10': {'now': 0.5056, 'p1_002': 0.5056}, 'winner_mrr': {'now': 0.3885, 'p1_002': 0.3885}, 'winner_recall@10': {'now': 0.6533, 'p1_002': 0.6533}}.

Query groups: {'ranked_top10': 196, 'ranking_failure (in pool, rank > 10)': 73, 'retrieval_failure (winner not in pool)': 31}

Conditional baseline (winner already in the pool, 269 queries): R@1 0.2937, R@5 0.6171, R@10 0.7286, R@20 0.8327, MRR 0.4332.

## Why winners lose rank

| Component | Dominant cause (failures) | Mean contribution deficit vs suppliers above | Share of suppliers above with a higher value |
|---|---:|---:|---:|
| em_participation | 0 | 0.0123 | 0.734 |
| evidence_quality | 0 | 0.0 | 0.743 |
| historical_relevance | 29 | 0.0466 | 0.814 |
| item_coverage | 0 | 0.0 | 0.52 |
| okpd2 | 18 | 0.0333 | 0.305 |
| product_text | 14 | 0.0277 | 0.405 |
| recency | 0 | 0.0039 | 0.52 |
| relevant_awards | 12 | 0.0413 | 0.714 |
| same_customer | 0 | 0.0039 | 0.078 |

## Evidence shape of failed winners (median) vs the top-10 suppliers

| Measure | Winner | Top-10 mean |
|---|---:|---:|
| days_since_latest | 30 | 19.8 |
| distinct_products | 2 | 17.8 |
| relevance_sum | 1.25 | 13.257 |
| relevant_awards | 1 | 10.9 |
| relevant_em_participations | 2 | 25.6 |
| relevant_lots | 2 | 27.9 |
| top_lot_share | 0.5 | 0.082 |

## Query/winner flags: ranking failures vs top-10 successes

| Flag | Failures | Successes |
|---|---:|---:|
| difficulty_EASY | 59 | 191 |
| difficulty_HARD | 6 | 0 |
| difficulty_MEDIUM | 8 | 5 |
| multi_item_query | 28 | 76 |
| queries | 73 | 196 |
| text_redundant_query | 14 | 57 |
| winner_same_customer | 36 | 136 |
| winner_single_relevant_lot | 20 | 4 |

## Reading

- Volume components (historical relevance + relevant awards) are the dominant cause in most failures: failed winners have thin relevant history (median 2 lots) while the suppliers above them are large incumbents.
- Text redundancy and multi-item queries are not over-represented among failures; same-customer history is more common among successes.

## Pairwise examples (top-1 vs immediately above vs winner; contributions)

**rpl-5511078** (EASY, 1 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.768 | 0.031 | 0.098 | 0.200 | 0.250 | 0.048 | 0.090 | 0.050 | 8 | 4 | 7 | yes |
| immediately_above | 10 | 0.663 | 0.011 | 0.061 | 0.200 | 0.250 | 0.050 | 0.091 | 0.000 | 7 | 7 | 4 |  |
| winner | 11 | 0.663 | 0.015 | 0.039 | 0.200 | 0.250 | 0.048 | 0.061 | 0.050 | 4 | 4 | 4 | yes |

**rpl-5512483** (EASY, 2 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 1.000 | 0.050 | 0.200 | 0.200 | 0.250 | 0.050 | 0.200 | 0.050 | 117 | 51 | 98 | yes |
| immediately_above | 12 | 0.769 | 0.017 | 0.120 | 0.200 | 0.250 | 0.048 | 0.135 | 0.000 | 11 | 8 | 3 |  |
| winner | 13 | 0.754 | 0.049 | 0.186 | 0.200 | 0.250 | 0.048 | 0.020 | 0.000 | 32 | 1 | 32 |  |

**rpl-5524182** (EASY, 8 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.911 | 0.048 | 0.182 | 0.200 | 0.223 | 0.049 | 0.158 | 0.050 | 44 | 17 | 33 | yes |
| immediately_above | 16 | 0.654 | 0.040 | 0.125 | 0.200 | 0.206 | 0.050 | 0.034 | 0.000 | 19 | 2 | 19 |  |
| winner | 17 | 0.631 | 0.017 | 0.052 | 0.160 | 0.223 | 0.049 | 0.080 | 0.050 | 5 | 5 | 4 | yes |

**rpl-5524232** (EASY, 2 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.843 | 0.050 | 0.200 | 0.155 | 0.192 | 0.047 | 0.200 | 0.000 | 145 | 143 | 143 |  |
| immediately_above | 14 | 0.524 | 0.013 | 0.032 | 0.155 | 0.228 | 0.047 | 0.050 | 0.000 | 2 | 2 | 2 |  |
| winner | 15 | 0.514 | 0.030 | 0.083 | 0.155 | 0.165 | 0.050 | 0.031 | 0.000 | 10 | 2 | 10 |  |

**rpl-5528109** (EASY, 1 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.929 | 0.048 | 0.192 | 0.200 | 0.250 | 0.050 | 0.190 | 0.000 | 62 | 33 | 39 |  |
| immediately_above | 24 | 0.472 | 0.011 | 0.029 | 0.200 | 0.189 | 0.043 | 0.000 | 0.000 | 3 | 0 | 3 |  |
| winner | 25 | 0.465 | 0.011 | 0.027 | 0.200 | 0.091 | 0.043 | 0.043 | 0.050 | 3 | 3 | 3 | yes |

**rpl-5530573** (EASY, 1 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.584 | 0.013 | 0.109 | 0.200 | 0.070 | 0.046 | 0.146 | 0.000 | 21 | 21 | 5 |  |
| immediately_above | 135 | 0.232 | 0.006 | 0.016 | 0.000 | 0.160 | 0.050 | 0.000 | 0.000 | 2 | 0 | 2 |  |
| winner | 136 | 0.232 | 0.006 | 0.015 | 0.000 | 0.160 | 0.050 | 0.000 | 0.000 | 2 | 0 | 2 |  |

**rpl-5531133** (EASY, 1 item(s), text redundant: True)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.793 | 0.050 | 0.191 | 0.200 | 0.205 | 0.050 | 0.097 | 0.000 | 58 | 8 | 58 |  |
| immediately_above | 15 | 0.588 | 0.000 | 0.053 | 0.200 | 0.210 | 0.045 | 0.080 | 0.000 | 5 | 5 | 0 |  |
| winner | 16 | 0.581 | 0.017 | 0.063 | 0.200 | 0.188 | 0.050 | 0.063 | 0.000 | 6 | 4 | 4 |  |

**rpl-5531373** (EASY, 1 item(s), text redundant: True)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.929 | 0.046 | 0.162 | 0.200 | 0.250 | 0.050 | 0.172 | 0.050 | 31 | 22 | 29 | yes |
| immediately_above | 20 | 0.444 | 0.013 | 0.032 | 0.200 | 0.166 | 0.033 | 0.000 | 0.000 | 3 | 0 | 3 |  |
| winner | 21 | 0.443 | 0.022 | 0.059 | 0.200 | 0.104 | 0.047 | 0.012 | 0.000 | 7 | 1 | 7 |  |

**rpl-5531678** (EASY, 8 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.821 | 0.050 | 0.188 | 0.160 | 0.183 | 0.050 | 0.141 | 0.050 | 55 | 15 | 55 | yes |
| immediately_above | 17 | 0.508 | 0.028 | 0.078 | 0.150 | 0.153 | 0.049 | 0.000 | 0.050 | 10 | 0 | 10 | yes |
| winner | 18 | 0.504 | 0.030 | 0.085 | 0.142 | 0.134 | 0.050 | 0.013 | 0.050 | 12 | 1 | 12 | yes |

**rpl-5532243** (EASY, 8 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.838 | 0.050 | 0.200 | 0.200 | 0.140 | 0.050 | 0.198 | 0.000 | 168 | 58 | 147 |  |
| immediately_above | 24 | 0.361 | 0.004 | 0.011 | 0.200 | 0.082 | 0.047 | 0.017 | 0.000 | 1 | 1 | 1 |  |
| winner | 25 | 0.354 | 0.007 | 0.025 | 0.200 | 0.063 | 0.046 | 0.015 | 0.000 | 3 | 1 | 2 |  |

**rpl-5534810** (MEDIUM, 1 item(s), text redundant: True)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.855 | 0.044 | 0.145 | 0.200 | 0.250 | 0.050 | 0.116 | 0.050 | 27 | 12 | 26 | yes |
| immediately_above | 152 | 0.269 | 0.004 | 0.009 | 0.000 | 0.164 | 0.028 | 0.015 | 0.050 | 1 | 1 | 1 | yes |
| winner | 153 | 0.266 | 0.003 | 0.007 | 0.140 | 0.058 | 0.046 | 0.012 | 0.000 | 1 | 1 | 1 |  |

**rpl-5537058** (EASY, 1 item(s), text redundant: False)

| Supplier | Rank | Score | em_participation | historical_relevance | okpd2 | product_text | recency | relevant_awards | same_customer | Lots | Awards | ЭМ part. | Same cust. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| top1 | 1 | 0.950 | 0.050 | 0.200 | 0.200 | 0.250 | 0.050 | 0.200 | 0.000 | 118 | 77 | 72 |  |
| immediately_above | 34 | 0.472 | 0.018 | 0.047 | 0.200 | 0.141 | 0.045 | 0.021 | 0.000 | 4 | 1 | 4 |  |
| winner | 35 | 0.472 | 0.010 | 0.025 | 0.200 | 0.141 | 0.046 | 0.000 | 0.050 | 2 | 0 | 2 | yes |
