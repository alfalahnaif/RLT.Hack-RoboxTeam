"""Markdown rendering of reports/p1_002_baseline.json (the JSON is the source of truth)."""
from __future__ import annotations


def render_md(r: dict) -> str:
    u, w = r["dev"]["unweighted"], r["dev"]["weighted"]
    L = ["# P1-002 — Historical Keyword + OKPD2 Retrieval Baseline", "",
         f"> Baseline {r['baseline_version']} · source sha256 `{r['revision']['source_sha256'][:16]}…` · benchmark manifest "
         f"`{r['revision']['benchmark_manifest_sha256'][:16]}…` · lexeme snapshot < {r['lexeme_stats']['snapshot_before']} "
         f"({r['lexeme_stats']['documents']:,} items). **HOLDOUT: not evaluated (sealed).** Labels are weak: unjudged ≠ irrelevant.", "",
         f"**Chosen configuration:** `{r['chosen_configuration']['name']}` — rule: {r['selection_rule']}.", "",
         "## DEV configurations compared (unweighted; population-weighted nDCG@10 in the last column)", "",
         "| Configuration | Winner cov. | Observed cov. | Cands | W-R@1 | W-R@5 | W-R@10 | W-R@20 | MRR | nDCG@10 | nDCG@20 | Obs-R@10 | Obs-R@20 | wnDCG@10 |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n, c in r["configurations_evaluated_on_dev"].items():
        x = c["unweighted"]
        L.append(f"| {n} | {x['candidate_winner_coverage']} | {x['candidate_observed_coverage']} | {x['candidates']:.0f} | "
                 f"{x['winner_recall@1']} | {x['winner_recall@5']} | {x['winner_recall@10']} | {x['winner_recall@20']} | {x['winner_mrr']} | "
                 f"{x['ndcg@10']} | {x['ndcg@20']} | {x['observed_recall@10']} | {x['observed_recall@20']} | {c['weighted']['ndcg@10']} |")
    L += ["", "## Chosen configuration on DEV — candidate generation vs ranking", "",
          f"- Candidate generation: winner present in the candidate pool for **{u['candidate_winner_coverage']:.1%}** of queries "
          f"(observed suppliers {u['candidate_observed_coverage']:.1%}); mean pool {u['candidates']:.0f} suppliers; "
          f"winner not a candidate in {r['dev']['winner_not_in_candidates']} / {r['dev']['queries']} queries.",
          f"- Ranking: winner in top-1 {u['winner_recall@1']:.1%}, top-5 {u['winner_recall@5']:.1%}, top-10 {u['winner_recall@10']:.1%}, "
          f"top-20 {u['winner_recall@20']:.1%}; MRR {u['winner_mrr']}; nDCG@10 {u['ndcg@10']}.",
          f"- Gap: of winners that ARE candidates, {u['winner_recall@10'] / u['candidate_winner_coverage']:.1%} reach the top 10. "
          "The remaining loss is a ranking problem; the coverage loss is a retrieval problem.",
          f"- Winner rank distribution: {r['dev']['winner_rank_distribution']}", "",
          "| Metric | Unweighted | Population-weighted (stratum_weight) |", "|---|---:|---:|"]
    for k in ["candidate_winner_coverage", "candidate_observed_coverage", "winner_recall@1", "winner_recall@5", "winner_recall@10",
              "winner_recall@20", "observed_recall@10", "observed_recall@20", "winner_mrr", "ndcg@10", "ndcg@20"]:
        L.append(f"| {k} | {u[k]} | {w[k]} |")
    L += ["", "### By difficulty (natural benchmark mix — HARD/MEDIUM are small and noisy)", "",
          "| Difficulty | Queries | Winner coverage | W-R@10 | MRR | nDCG@10 |", "|---|---:|---:|---:|---:|---:|"]
    for d, x in r["dev"]["by_difficulty"].items():
        L.append(f"| {d} | {x['queries']} | {x['candidate_winner_coverage']} | {x['winner_recall@10']} | {x['winner_mrr']} | {x['ndcg@10']} |")
    L += ["", "### By OKPD2 stratum", "", "| Stratum | Queries | Winner coverage | W-R@10 | MRR | nDCG@10 |", "|---|---:|---:|---:|---:|---:|"]
    for d, x in r["dev"]["by_okpd2_stratum"].items():
        L.append(f"| {d} | {x['queries']} | {x['candidate_winner_coverage']} | {x['winner_recall@10']} | {x['winner_mrr']} | {x['ndcg@10']} |")
    wu = r["warmup"]["unweighted"]
    lat = r["latency_dev_end_to_end"]
    L += ["", f"## WARM-UP (debugging only, {r['warmup']['queries']} queries)", "",
          f"winner coverage {wu['candidate_winner_coverage']} · W-R@10 {wu['winner_recall@10']} · MRR {wu['winner_mrr']} · nDCG@10 {wu['ndcg@10']}", "",
          "## Latency (end-to-end: query build + retrieval + lot aggregation + candidates + scoring; fresh, DEV)", "",
          f"p50 {lat['p50_ms']} ms · p95 {lat['p95_ms']} ms · max {lat['max_ms']} ms · mean {lat['mean_ms']} ms ({lat['queries']} queries)", "",
          "## Golden cases (qualitative, inspected after the configuration freeze — not tuned on)", "",
          "| Lot | Winner rank (new) | Naive award-count rank (P1-001A) | Candidates | Observed suppliers in top 10 | Latency ms |",
          "|---|---:|---|---:|---:|---:|"]
    for lot, g in r["golden_cases"].items():
        L.append(f"| {lot} | {g['winner_rank'] if g['winner_rank'] else 'not a candidate'} | {g['naive_award_count_rank_p1_001a']} | "
                 f"{g['candidates']} | {g['observed_suppliers_in_top10']} | {g['timings_ms']['total_ms']} |")
    for lot, g in r["golden_cases"].items():
        L += ["", f"### {lot} — top 10", "",
              "| # | Score | text | okpd2 | hist. rel. | awards | ЭМ part. | recency | same cust. | Lots | Awards | Winner | Observed | Best product |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|:-:|---|"]
        for t in g["top10"]:
            c = t["components"]
            L.append(f"| {t['rank']} | {t['score']:.3f} | {c['product_text']:.2f} | {c['okpd2']:.2f} | {c['historical_relevance']:.2f} | "
                     f"{c['relevant_awards']:.2f} | {c['em_participation']:.2f} | {c['recency']:.2f} | {c['same_customer']:.0f} | "
                     f"{t['relevant_lots']} | {t['relevant_awards']} | {'yes' if t['is_actual_winner'] else ''} | "
                     f"{'yes' if t['observed_on_lot'] else ''} | {(t['best_products'] or [''])[0][:60]} |")
    L += ["", "## Known limitations", "",
          "- Weak labels: unjudged suppliers are not proven irrelevant; recall/MRR/nDCG are computed on observed suppliers only.",
          "- Retrieval is lexical + OKPD2 only (no semantic matching): vocabulary mismatch (synonyms, abbreviations) is missed, "
          "which is why HARD/MEDIUM cases have low candidate coverage.",
          "- The broad OKPD2 branch searches the query kind when the code has one; group-level siblings are found only through text.",
          "- Multi-item lots use at most `max_query_items` most informative distinct items (bounded latency).",
          "- Evidence is lot-level: a supplier is relevant to a lot, not to a specific item of a multi-item lot.",
          "- History-based features favour incumbents; suppliers without history cannot be recommended by this baseline "
          "(by design: external expansion is P3).",
          "- Configuration chosen on 300 DEV queries among 6 explicit variants; HOLDOUT untouched."]
    return "\n".join(L) + "\n"
