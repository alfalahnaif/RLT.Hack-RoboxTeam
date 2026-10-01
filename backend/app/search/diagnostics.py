"""P2-003 ranking-error diagnosis on DEV (frozen P1-002 baseline; candidate pool fixed).

A ranking failure = the actual winner IS in the candidate pool but ranks below `FAIL_RANK`. For each failure the winner is compared with
every supplier ranked above it: per score component, the mean contribution deficit (above - winner, positive part) and how often the
component is the single largest deficit (the "dominant cause"). Retrieval failures (winner absent from the pool) are counted separately.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from app.search import evaluation as E
from app.search.candidates import Pool, score_lots
from app.search.models import SearchConfig
from app.search.scoring import COMPONENTS, rank_suppliers

FAIL_RANK = 10
SHAPE_KEYS = ["relevance_sum", "top_lot_share", "distinct_products", "days_since_latest"]


def rank_all(cache, cfg: SearchConfig) -> dict:
    out = {}
    for qid, (ql, ret, idf, pool_all, _ms) in cache.items():
        lots = score_lots(ql, ret, idf, cfg)
        recs, _ = rank_suppliers(ql, Pool(lots=lots, relations=pool_all.relations, same_customer=pool_all.same_customer), cfg)
        out[qid] = (ql, recs)
    return out


def _row(r) -> dict:
    return {"rank": r.rank, "score": r.score, "contributions": r.contributions, "components": r.components,
            "relevant_lots": r.relevant_lots, "relevant_awards": r.relevant_awards,
            "relevant_em_participations": r.relevant_em_participations, "same_customer_history": r.same_customer_history,
            "diagnostics": r.diagnostics, "best_products": r.best_products[:1]}


def diagnose(ranked: dict, qrels: dict, meta: dict, max_examples: int = 12) -> dict:
    cause, deficit = Counter(), defaultdict(list)
    lower_than_above = defaultdict(list)
    shape_w, shape_top = defaultdict(list), defaultdict(list)
    flags = {"failure": Counter(), "success": Counter()}
    groups = Counter()
    examples = []
    for qid in sorted(ranked):
        ql, recs = ranked[qid]
        winners = {s for s, g in qrels[qid].items() if g == 2}
        wr = [r for r in recs if r.supplier_id in winners]
        if not wr:
            groups["retrieval_failure (winner not in pool)"] += 1
            continue
        w = min(wr, key=lambda r: r.rank)
        kind = "failure" if w.rank > FAIL_RANK else "success"
        groups["ranking_failure (in pool, rank > 10)" if kind == "failure" else "ranked_top10"] += 1
        flags[kind]["queries"] += 1
        flags[kind]["text_redundant_query"] += w.diagnostics["query_text_redundant"]
        flags[kind]["multi_item_query"] += w.diagnostics["query_items"] > 1
        flags[kind]["winner_same_customer"] += w.same_customer_history
        flags[kind]["winner_single_relevant_lot"] += w.relevant_lots == 1
        flags[kind]["difficulty_" + meta[qid]["difficulty"]] += 1
        if kind == "success":
            continue
        above = recs[:w.rank - 1]
        avg_def = {}
        for c in COMPONENTS:
            d = [max(0.0, a.contributions.get(c, 0.0) - w.contributions.get(c, 0.0)) for a in above]
            avg_def[c] = statistics.fmean(d)
            deficit[c].append(avg_def[c])
            lower_than_above[c].append(statistics.fmean([1.0 if a.components[c] > w.components[c] else 0.0 for a in above]))
        cause[max(avg_def, key=lambda c: (avg_def[c], c))] += 1
        top10 = recs[:10]
        for k in SHAPE_KEYS:
            shape_w[k].append(w.diagnostics[k])
            shape_top[k].append(statistics.fmean([a.diagnostics[k] for a in top10]))
        for k, getter in (("relevant_lots", lambda r: r.relevant_lots), ("relevant_awards", lambda r: r.relevant_awards),
                          ("relevant_em_participations", lambda r: r.relevant_em_participations)):
            shape_w[k].append(getter(w))
            shape_top[k].append(statistics.fmean([getter(a) for a in top10]))
        if len(examples) < max_examples:
            examples.append({"query_id": qid, "difficulty": meta[qid]["difficulty"], "query_items": w.diagnostics["query_items"],
                             "query_text_redundant": w.diagnostics["query_text_redundant"],
                             "winner": _row(w), "immediately_above": _row(recs[w.rank - 2]), "top1": _row(recs[0])})
    n_fail = groups["ranking_failure (in pool, rank > 10)"]
    return {
        "definition": f"ranking failure = winner in candidate pool and best winner rank > {FAIL_RANK}",
        "query_groups": dict(groups),
        "dominant_cause_counts": dict(cause.most_common()),
        "mean_contribution_deficit_vs_suppliers_above": {c: round(statistics.fmean(v), 4) for c, v in deficit.items()},
        "share_of_above_suppliers_with_higher_component": {c: round(statistics.fmean(v), 3) for c, v in lower_than_above.items()},
        "evidence_shape_winner_vs_top10_mean (medians over failures)": {
            k: {"winner": round(statistics.median(shape_w[k]), 3), "top10_mean": round(statistics.median(shape_top[k]), 3)}
            for k in shape_w},
        "query_flags": {k: dict(v) for k, v in flags.items()},
        "ranking_failures": n_fail,
        "pairwise_examples": examples,
    }
