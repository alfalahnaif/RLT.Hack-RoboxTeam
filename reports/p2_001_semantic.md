# P2-001 — Semantic Retrieval Candidate Expansion (DEV only)

> Ranking frozen at P2_003_RANKING. **HOLDOUT: not evaluated (sealed).** Labels are weak (unjudged ≠ irrelevant). Model `intfloat/multilingual-e5-small` @ `614241f622f53c4eeff9890bdc4f31cfecc418b3` (384-d, MIT (intfloat/multilingual-e5-small)).

**Decision: `S3 semantic top-100`** — accepted by rules A–C: ['S1 semantic top-25', 'S2 semantic top-50', 'S3 semantic top-100']; latency gate passed: True.

## 1. Feasibility gate (run before any pgvector / full indexing)

- Rule: GO if plausibly recoverable retrieval failures >= 5 (estimated full-corpus rank <= 100 texts) → **GO** (9/31 retrieval failures plausibly recoverable; by difficulty {'EASY': {'failures': 3, 'plausibly_recoverable': 1}, 'HARD': {'failures': 19, 'plausibly_recoverable': 4}, 'MEDIUM': {'failures': 9, 'plausibly_recoverable': 4}}).
- Corpus sample: 100,000 distinct texts visible before 2025-01-01 (full visible ≈ 779,359); success sample: 28/30 winners also semantically reachable.
- Exact technical identifiers: on average 1.33 of the semantic top-10 neighbours contain the exact token → trigram/FTS stay responsible for model numbers.

## 2. Semantic storage

- Unit: one row per **distinct normalized product text** (`semantic_text`, md5 text hash, `first_seen_publish_date`, 384-d vector, model revision) mapped back to items through `md5(product_name_normalized)` (expression index with item date).
- Temporal rule: text eligible only if `first_seen_publish_date < as_of`; every evidence item must itself have `publish_date < as_of` (SQL).
- pgvector 0.8.6 in the `pgvector/pgvector:pg16` image; HNSW (cosine, m=16, ef_construction=64); query-time `hnsw.ef_search=200` with iterative scan (relaxed order).

| Item | Value |
|---|---:|
| texts | 993,289 |
| embedded | 993,289 |
| embedding_seconds | 11,777.2 |
| hnsw_build_seconds | 478.4 |
| semantic_text_total_bytes | 3,987 MiB |
| hnsw_index_bytes | 1,940 MiB |
| item_md5_index_bytes | 125 MiB |
| database_bytes_before | 6,718 MiB |
| database_bytes | 10,832 MiB |

> **Caveat.** Winner-pool movement vs S0: 5 recovered, 2 lost (semantic lots displace lexical lots inside the historical-lot limit) → net +3 queries. Population-weighted coverage 0.9041 → 0.9013 (the lost queries carry higher stratum weight). Rule A is defined on unweighted coverage / MEDIUM+HARD recovery and was applied as declared.

## 3. Acceptance rule (declared before the results)

- **A_coverage**: candidate winner coverage >= +2 percentage points overall, OR >= 3 additional MEDIUM+HARD winners recovered
- **B_quality**: population-weighted nDCG@10 delta >= -0.005
- **C_recall**: population-weighted winner Recall@10 delta >= -0.005
- **D_latency**: end-to-end p95 <= 5 s (hard limit 10 s), measured for the chosen configuration
- **E_explainable**: semantic evidence (text, cosine, lot, date, OKPD2) exposed for every semantic-based candidate (by construction)
- **choose**: largest overall coverage gain among accepted; tie -> smaller semantic_top_k; none accepted -> semantic stays OFF

## 4. Configurations (DEV, unweighted)

| Configuration | Winner cov. | Obs. cov. | Cands | W-R@1 | W-R@5 | W-R@10 | W-R@20 | MRR | nDCG@10 | nDCG@20 | w-nDCG@10 | w-R@10 | Recovered (MED+HARD) | Δ cov. pp | Pool growth % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S0 P2-003 (semantic off) | 0.8967 | 0.8932 | 125 | 0.28 | 0.5667 | 0.6633 | 0.75 | 0.4071 | 0.5247 | 0.5559 | 0.4794 | 0.617 | — (—) | — | — |
| S1 semantic top-25 | 0.9 | 0.8947 | 126 | 0.2833 | 0.5633 | 0.6667 | 0.7467 | 0.4073 | 0.5277 | 0.5577 | 0.4832 | 0.6214 | 3 (3) | 0.33 | 0.8 |
| S2 semantic top-50 | 0.9033 | 0.895 | 126 | 0.2767 | 0.56 | 0.6667 | 0.75 | 0.4048 | 0.5274 | 0.5572 | 0.4805 | 0.622 | 4 (4) | 0.66 | 1.0 |
| S3 semantic top-100 | 0.9067 | 0.8999 | 126 | 0.2867 | 0.56 | 0.6633 | 0.7533 | 0.411 | 0.5268 | 0.5596 | 0.4786 | 0.6135 | 5 (5) | 1.0 | 1.0 |
| S4 semantic top-50, λ=0.6 | 0.9 | 0.8943 | 125 | 0.2767 | 0.57 | 0.6733 | 0.7467 | 0.4086 | 0.5298 | 0.5586 | 0.4802 | 0.6242 | 2 (2) | 0.33 | 0.4 |

## 5. Weighted metrics (population-weighted by stratum_weight)

| Metric | S0 | Chosen |
|---|---:|---:|
| candidate_winner_coverage | 0.9041 | 0.9013 |
| candidate_observed_coverage | 0.9013 | 0.901 |
| winner_recall@1 | 0.2346 | 0.2372 |
| winner_recall@5 | 0.5059 | 0.4911 |
| winner_recall@10 | 0.617 | 0.6135 |
| winner_recall@20 | 0.7098 | 0.7107 |
| winner_mrr | 0.3528 | 0.354 |
| ndcg@10 | 0.4794 | 0.4786 |
| ndcg@20 | 0.5101 | 0.5103 |
| candidates | 143.9 | 143.3807 |

## 6. Difficulty breakdown (candidate coverage = retrieval; conditional recall in the configuration rows)

| Difficulty | S0 coverage | Chosen coverage | S0 W-R@10 | Chosen W-R@10 |
|---|---:|---:|---:|---:|
| EASY | 0.9881 | 0.9881 | 0.7708 | 0.7708 |
| MEDIUM | 0.5909 | 0.5909 | 0.1818 | 0.1818 |
| HARD | 0.24 | 0.36 | 0.0 | 0.0 |

## 7. The 31 baseline retrieval failures under the chosen configuration

| Query | Difficulty | Status | Detail |
|---|---|---|---|
| rpl-5503743 | EASY | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.8607) |
| rpl-5506524 | MEDIUM | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.9423) |
| rpl-5525329 | HARD | STILL_MISSING | genuinely unseen supplier (no visible history before the lot date) |
| rpl-5542519 | MEDIUM | RECOVERED | winner rank 115; «проведение технического осмотра автотранспортного средства ford transi» cos 0.9012 lot 5343005 2024-10-23 |
| rpl-5532791 | HARD | RECOVERED | winner rank 153; «выполнение работ по ремонту помещений шереметевского дворца помещение » cos 0.9224 lot 5230751 2024-07-11 |
| rpl-5555299 | HARD | RECOVERED | winner rank 47; «оказание услуг техническому обслуживанию и ремонту узлов учета теплово» cos 0.9308 lot 5483010 2024-12-24 |
| rpl-5559084 | HARD | STILL_MISSING | genuinely unseen supplier (no visible history before the lot date) |
| rpl-5563770 | HARD | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.863) |
| rpl-5548383 | HARD | STILL_MISSING | genuinely unseen supplier (no visible history before the lot date) |
| rpl-5581528 | MEDIUM | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.8684) |
| rpl-5583213 | HARD | RECOVERED | winner rank 15; «обслуживание системы контроля загазованности скз стг-3-и-ех» cos 0.8879 lot 5253057 2024-08-02 |
| rpl-5592531 | HARD | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.8621) |
| rpl-5612337 | MEDIUM | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.9063) |
| rpl-5558279 | MEDIUM | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.8706) |
| rpl-5626010 | MEDIUM | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8282) |
| rpl-5630655 | MEDIUM | RECOVERED | winner rank 43; «техническое обслуживание мфу kyocera» cos 0.9096 lot 5125302 2024-04-16 |
| rpl-5652935 | EASY | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.854) |
| rpl-5633525 | HARD | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8569) |
| rpl-5657798 | MEDIUM | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8498) |
| rpl-5660588 | HARD | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8384) |
| rpl-5677806 | HARD | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8111) |
| rpl-5679163 | HARD | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8085) |
| rpl-5688050 | HARD | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.8995) |
| rpl-5701460 | HARD | STILL_MISSING | genuinely unseen supplier (no visible history before the lot date) |
| rpl-5714306 | EASY | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.909) |
| rpl-5712129 | HARD | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.8653) |
| rpl-5725576 | MEDIUM | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.9104) |
| rpl-5733607 | HARD | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8165) |
| rpl-5739355 | HARD | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.8464) |
| rpl-5743395 | HARD | STILL_MISSING | related history exists but outside the semantic cap / lot limit (different terminology or broad category) (best history cos 0.8603) |
| rpl-5737759 | HARD | STILL_MISSING | no relevant historical procurement (winner's history is about other products) (best history cos 0.858) |

## 8. Latency (end-to-end, warm, DEV, chosen)

p50 711.2 ms · p95 3366.6 ms · max 5656.5 ms · mean 1079.9 ms; model load once per process: 6.31 s (cold start, not included in per-request numbers).

Per-stage breakdown (fresh process, 300 DEV queries; cold model load 6.31 s is paid by the first request of a process — first request total after load 570.9 ms):

| Stage | p50 ms | p95 ms | max ms | mean ms |
|---|---:|---:|---:|---:|
| candidates_ms | 10.8 | 22.1 | 144.9 | 12.9 |
| item_mapping_ms | 32.6 | 203.6 | 314.0 | 59.9 |
| lexical_okpd2_branches_ms | 515.3 | 2517.2 | 5139.2 | 814.3 |
| lot_aggregation_fusion_ms | 18.6 | 264.6 | 565.6 | 54.6 |
| query_embedding_ms | 32.2 | 177.4 | 597.9 | 55.7 |
| scoring_ms | 6.5 | 11.6 | 148.2 | 8.5 |
| total_ms | 711.4 | 3334.3 | 5848.4 | 1069.3 |
| vector_search_ms | 4.6 | 25.9 | 55.2 | 7.9 |

## 9. Golden cases (after the freeze; not tuned on)

| Lot | P2-003 rank | Now | Change |
|---|---:|---:|---|
| 5542696 | 11 | 16 | worse |
| 5545252 | 16 | 15 | better |
| 5612123 | 32 | 32 | same |
| 5718896 | 1 | 1 | same |
| 6022687 | 7 | 9 | worse |

## 10. Limitations

- CPU-only embedding is slow on the team machine (~80–100 texts/s); the one-off build takes hours (resumable).
- Cosine calibration (0.82 → 0, 0.95 → 1) is fixed from the feasibility study, not learned.
- Semantic neighbours of generic texts are generic; recovered candidates can still rank low.
- Failures caused by genuinely unseen suppliers cannot be fixed by any history-based retrieval (external expansion, P3).
- Weak labels: an unobserved supplier is not proven irrelevant.
