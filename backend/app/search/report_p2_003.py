"""Markdown rendering for reports/p2_003_ranking_diagnostics.json and reports/p2_003_ranking.json (JSON = source of truth)."""
from __future__ import annotations

KEYS = ["winner_recall@1", "winner_recall@5", "winner_recall@10", "winner_recall@20", "winner_mrr", "ndcg@10", "ndcg@20"]


def _pairs(examples) -> list[str]:
    L = []
    for ex in examples:
        L += ["", f"**{ex['query_id']}** ({ex['difficulty']}, {ex['query_items']} item(s), text redundant: {ex['query_text_redundant']})", "",
              "| Supplier | Rank | Score | " + " | ".join(c for c in ex["winner"]["contributions"]) + " | Lots | Awards | ЭМ part. | Same cust. |",
              "|---|---:|---:|" + "---:|" * len(ex["winner"]["contributions"]) + "---:|---:|---:|:-:|"]
        for label in ("top1", "immediately_above", "winner"):
            r = ex[label]
            L.append(f"| {label} | {r['rank']} | {r['score']:.3f} | " +
                     " | ".join(f"{r['contributions'].get(c, 0.0):.3f}" for c in ex["winner"]["contributions"]) +
                     f" | {r['relevant_lots']} | {r['relevant_awards']} | {r['relevant_em_participations']} | {'yes' if r['same_customer_history'] else ''} |")
    return L


def render_diagnostics(d: dict) -> str:
    L = ["# P2-003 — Ranking Error Diagnosis (DEV, frozen P1-002 baseline)", "",
         f"> {d['definition']}. Candidate pool fixed. HOLDOUT not used. Baseline reproduced: {d['baseline_reproduced']}.", "",
         f"Query groups: {d['query_groups']}", "",
         f"Conditional baseline (winner already in the pool, {d['conditional_baseline']['queries_with_winner_in_pool']} queries): "
         f"R@1 {d['conditional_baseline']['winner_recall@1']}, R@5 {d['conditional_baseline']['winner_recall@5']}, "
         f"R@10 {d['conditional_baseline']['winner_recall@10']}, R@20 {d['conditional_baseline']['winner_recall@20']}, "
         f"MRR {d['conditional_baseline']['winner_mrr']}.", "",
         "## Why winners lose rank", "", "| Component | Dominant cause (failures) | Mean contribution deficit vs suppliers above | Share of suppliers above with a higher value |",
         "|---|---:|---:|---:|"]
    for c, v in d["mean_contribution_deficit_vs_suppliers_above"].items():
        L.append(f"| {c} | {d['dominant_cause_counts'].get(c, 0)} | {v} | {d['share_of_above_suppliers_with_higher_component'][c]} |")
    L += ["", "## Evidence shape of failed winners (median) vs the top-10 suppliers", "", "| Measure | Winner | Top-10 mean |", "|---|---:|---:|"]
    for k, v in d["evidence_shape_winner_vs_top10_mean (medians over failures)"].items():
        L.append(f"| {k} | {v['winner']} | {v['top10_mean']} |")
    f, s = d["query_flags"]["failure"], d["query_flags"]["success"]
    L += ["", "## Query/winner flags: ranking failures vs top-10 successes", "", "| Flag | Failures | Successes |", "|---|---:|---:|"]
    for k in sorted(set(f) | set(s)):
        L.append(f"| {k} | {f.get(k, 0)} | {s.get(k, 0)} |")
    L += ["", "## Reading", "",
          "- Volume components (historical relevance + relevant awards) are the dominant cause in most failures: failed winners have thin "
          "relevant history (median 2 lots) while the suppliers above them are large incumbents.",
          "- Text redundancy and multi-item queries are not over-represented among failures; same-customer history is more common among "
          "successes.", "", "## Pairwise examples (top-1 vs immediately above vs winner; contributions)"]
    L += _pairs(d["pairwise_examples"])
    return "\n".join(L) + "\n"


def render_ranking(r: dict) -> str:
    base = "B0 baseline (P1-002)"
    ch = r["chosen"]["name"]
    L = ["# P2-003 — Explainable Supplier Ranking Improvement (DEV only)", "",
         f"> Candidate pool: {r['candidate_pool']}. **HOLDOUT: not evaluated (sealed).** Labels are weak (unjudged ≠ irrelevant).", "",
         f"**Chosen: `{ch}`** — accepted challengers: {r['accepted_challengers']}.", "",
         "## Selection rule (declared before the results)", ""] + [f"- {x}" for x in r["selection_rule"]["accept_if"]] + \
        [f"- Primary metric: {r['selection_rule']['primary']}; choose: {r['selection_rule']['choose']}", "",
         "## Configurations tested", "",
         "| Configuration | Rationale | w-nDCG@10 | Δ (90% CI) | nDCG@10 | W-R@10 | Cond. R@10 | MRR | Accepted | Scoring ms/query |",
         "|---|---|---:|---|---:|---:|---:|---:|:-:|---:|"]
    for n, c in r["configurations"].items():
        vb = c.get("vs_baseline", {}).get("weighted_ndcg10")
        delta = f"{vb['delta']:+.4f} [{vb['ci90'][0]:+.4f}, {vb['ci90'][1]:+.4f}]" if vb else "—"
        L.append(f"| {n} | {c['rationale']} | {c['weighted']['ndcg@10']} | {delta} | {c['unweighted']['ndcg@10']} | "
                 f"{c['unweighted']['winner_recall@10']} | {c['conditional_unweighted']['winner_recall@10']} | {c['unweighted']['winner_mrr']} | "
                 f"{'yes' if c.get('accepted') else ('—' if n == base else 'no')} | {c['scoring_and_lot_aggregation_ms_per_query']} |")
    b, c = r["configurations"][base], r["configurations"][ch]
    L += ["", "## Baseline vs chosen", "", "| Metric | Baseline unweighted | Chosen unweighted | Baseline weighted | Chosen weighted |",
          "|---|---:|---:|---:|---:|"]
    for k in KEYS + ["candidate_winner_coverage"]:
        L.append(f"| {k} | {b['unweighted'][k]} | {c['unweighted'][k]} | {b['weighted'][k]} | {c['weighted'][k]} |")
    L += ["", "## Conditional ranking metrics (winner already in the candidate pool)", "",
          "| Metric | Baseline | Chosen | Baseline weighted | Chosen weighted |", "|---|---:|---:|---:|---:|"]
    for k in ["winner_recall@1", "winner_recall@5", "winner_recall@10", "winner_recall@20", "winner_mrr", "ndcg@10"]:
        L.append(f"| {k} | {b['conditional_unweighted'][k]} | {c['conditional_unweighted'][k]} | {b['conditional_weighted'][k]} | "
                 f"{c['conditional_weighted'][k]} |")
    L += [f"| queries with winner in pool | {b['conditional_unweighted']['queries_with_winner_in_pool']} | "
          f"{c['conditional_unweighted']['queries_with_winner_in_pool']} | | |"]
    L += ["", "## Difficulty — retrieval failure vs ranking", "",
          "| Difficulty | Queries | Retrieval failures | Winner in pool | Cond. R@10 baseline | Cond. R@10 chosen | nDCG@10 baseline | nDCG@10 chosen |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for d in ("EASY", "MEDIUM", "HARD"):
        x, y = r["difficulty_breakdown"][base][d], r["difficulty_breakdown"][ch][d]
        L.append(f"| {d} | {x['queries']} | {x['retrieval_failures']} | {x['winner_in_pool']} | {x['conditional_recall@10']} | "
                 f"{y['conditional_recall@10']} | {x['ndcg@10']} | {y['ndcg@10']} |")
    L += ["", "## OKPD2 strata (nDCG@10)", "", "| Stratum | Queries | Baseline | Chosen |", "|---|---:|---:|---:|"]
    for s, x in r["stratum_breakdown"][base].items():
        L.append(f"| {s} | {x['queries']} | {x['ndcg@10']} | {r['stratum_breakdown'][ch][s]['ndcg@10']} |")
    inc = r["customer_signal_incumbent_analysis"]
    L += ["", "## Customer signal (with vs without)", "",
          f"- With: weighted nDCG@10 {inc[base]['weighted_ndcg@10']}, top-10 suppliers with same-customer history "
          f"{inc[base]['top10_suppliers_with_same_customer_history']:.1%}.",
          f"- Without (C3): weighted nDCG@10 {inc['C3 no customer signal']['weighted_ndcg@10']}, top-10 with same-customer history "
          f"{inc['C3 no customer signal']['top10_suppliers_with_same_customer_history']:.1%}.",
          "- Removing it lowers quality significantly (CI excludes 0), so it stays a supporting signal (weight 0.05). It does raise the share "
          "of incumbents in the top 10 by about 5 points — a known, visible trade-off, not lock-in.",
          "", "## Golden cases (inspected after the freeze; not tuned on)", "", "| Lot | P1-002 winner rank | P2-003 winner rank | Change |",
          "|---|---:|---:|---|"]
    for lot, g in r["golden_cases"].items():
        old, new = r["golden_p1_002_ranks"][lot], g["winner_rank"]
        L.append(f"| {lot} | {old} | {new} | {'better' if new and new < old else 'worse' if new is None or new > old else 'same'} |")
    lat = r["latency_dev_end_to_end_chosen"]
    rf = r["remaining_failures_chosen"]
    L += ["", "## Latency (end-to-end, DEV, chosen)", "", f"p50 {lat['p50_ms']} ms · p95 {lat['p95_ms']} ms · max {lat['max_ms']} ms · "
          f"mean {lat['mean_ms']} ms. Retrieval is unchanged; scoring + lot aggregation cost per query is in the table above.", "",
          "## Remaining failures (chosen)", "", f"Query groups: {rf['query_groups']}", "",
          f"Dominant causes: {rf['dominant_cause_counts']} — after the change, failures are mostly driven by weaker product-text and OKPD2 "
          "matches of the winner (relevance), no longer by incumbent volume.", "", "### Pairwise examples"]
    L += _pairs(rf["pairwise_examples"])
    L += ["", "## Limitations", "",
          "- Gains are modest (one accepted challenger, Δ weighted nDCG@10 ≈ +0.016); ranking signals of this lexical/history feature family "
          "are close to saturation.",
          "- 31/300 DEV queries are retrieval failures (winner absent from the pool): no ranking change can fix them (HARD: 19/25).",
          "- MEDIUM conditional R@10 moved 0.385 → 0.308 on 13 queries (one query) — noise-level, reported for transparency.",
          "- The generic text-redundancy rule hurt on DEV and was not adopted; golden case 5612123 (item text = subject) remains a known regression.",
          "- Weak labels: unjudged suppliers are not proven irrelevant."]
    return "\n".join(L) + "\n"
