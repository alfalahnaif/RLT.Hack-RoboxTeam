"""P2-003 controlled ranking-only experiments on DEV (defined after the diagnosis, before any result was computed).

Pre-declared selection rule (SELECTION_RULE) — a challenger replaces the frozen P1-002 baseline only if it clears every check.
The candidate pool is identical across configurations (asserted); only supplier scoring changes. Holdout is never loaded.
"""
from __future__ import annotations

import statistics
import time

from app.search import evaluation as E
from app.search.diagnostics import diagnose, rank_all
from app.search.models import P1_002_BASELINE
from app.search.ranking_study import conditional, load_dev, metrics_from_ranked, paired_bootstrap

B = P1_002_BASELINE
BASE = "B0 baseline (P1-002)"
EXPERIMENTS = {
    BASE: (B, "frozen reference"),
    "C1 quality over volume": (B.with_(w_historical_relevance=0.0, w_evidence_quality=0.20),
                               "volume (historical_relevance) is the dominant cause in 29/73 failures: top-3 mean relevance replaces the saturated sum"),
    "C2 relevance-dominant": (B.with_(w_product_text=0.35, w_okpd2=0.30, w_historical_relevance=0.10, w_relevant_awards=0.10),
                              "volume components (relevance sum + awards) dominant in 41/73 failures: shift weight to query relevance"),
    "C3 no customer signal": (B.with_(w_same_customer=0.0), "required comparison: incumbent effect of same-customer history"),
    "C4 no recency": (B.with_(w_recency=0.0), "recency comparison: 1-year half-life vs none"),
    "C5 recency 2-year half-life": (B.with_(recency_half_life_days=730), "recency comparison: 1-year vs 2-year half-life"),
    "C6 multi-item coverage": (B.with_(w_item_coverage=0.15), "bounded query-item coverage for multi-item queries (28/73 failures multi-item)"),
    "C7 redundant-text down-weight": (B.with_(redundant_text_factor=0.5),
                                      "generic rule: halve the product_text weight when every item text ~ the subject (5612123 class)"),
    "C8 quality + coverage": (B.with_(w_historical_relevance=0.0, w_evidence_quality=0.20, w_item_coverage=0.15),
                              "combined query-relative variant (C1 + C6)"),
}
SELECTION_RULE = {
    "primary": "population-weighted nDCG@10",
    "accept_if": ["delta weighted nDCG@10 >= +0.01 vs B0 AND paired-bootstrap 90% CI lower bound > 0",
                  "delta weighted winner Recall@10 >= -0.005",
                  "identical candidate pools (asserted)",
                  "no OKPD2 stratum with >= 10 DEV queries loses more than 0.05 unweighted nDCG@10"],
    "choose": "highest weighted nDCG@10 among accepted challengers; if none is accepted keep B0",
}
MIN_DELTA, MIN_RECALL_DELTA, STRATUM_MIN_Q, STRATUM_MAX_LOSS = 0.01, -0.005, 10, 0.05


def _strata_delta(pq_a: dict, pq_b: dict, meta: dict) -> dict:
    groups: dict[str, list] = {}
    for q in pq_a:
        groups.setdefault(meta[q]["stratum"], []).append(q)
    return {s: round(statistics.fmean(pq_b[q]["ndcg@10"] for q in qs) - statistics.fmean(pq_a[q]["ndcg@10"] for q in qs), 4)
            for s, qs in sorted(groups.items()) if len(qs) >= STRATUM_MIN_Q}


def _by_difficulty(pq: dict, meta: dict) -> dict:
    out = {}
    for d in ("EASY", "MEDIUM", "HARD"):
        sub = {q: m for q, m in pq.items() if meta[q]["difficulty"] == d}
        agg = E.aggregate(sub, meta, False)
        out[d] = {"queries": len(sub), "winner_in_pool": sum(1 for m in sub.values() if m["candidate_winner_coverage"] > 0),
                  "retrieval_failures": sum(1 for m in sub.values() if m["candidate_winner_coverage"] == 0),
                  "candidate_winner_coverage": agg["candidate_winner_coverage"], "winner_recall@10": agg["winner_recall@10"],
                  "conditional_recall@10": conditional(sub, meta, False)["winner_recall@10"], "winner_mrr": agg["winner_mrr"],
                  "ndcg@10": agg["ndcg@10"]}
    return out


def run(conn, log=print) -> dict:
    from app.search.report import golden_inspection
    t0 = time.perf_counter()
    queries, qrels, meta, cache = load_dev(conn, log)
    ranked_by, pq_by, results = {}, {}, {}
    base_pools = None
    for name, (cfg, why) in EXPERIMENTS.items():
        t = time.perf_counter()
        ranked = rank_all(cache, cfg)
        scoring_ms = (time.perf_counter() - t) * 1000 / len(ranked)
        pools = {q: sorted(r.supplier_id for r in recs) for q, (_ql, recs) in ranked.items()}
        base_pools = base_pools or pools
        assert pools == base_pools, f"{name}: candidate pool changed"
        pq = metrics_from_ranked(ranked, qrels)
        ranked_by[name], pq_by[name] = ranked, pq
        results[name] = {"rationale": why, "config_delta": {k: v for k, v in cfg.to_dict().items() if v != B.to_dict()[k]},
                         "unweighted": E.aggregate(pq, meta, False), "weighted": E.aggregate(pq, meta, True),
                         "conditional_unweighted": conditional(pq, meta, False), "conditional_weighted": conditional(pq, meta, True),
                         "scoring_and_lot_aggregation_ms_per_query": round(scoring_ms, 2)}
        log(f"{name}: w-nDCG@10={results[name]['weighted']['ndcg@10']} nDCG@10={results[name]['unweighted']['ndcg@10']}")
    accepted = []
    for name in EXPERIMENTS:
        if name == BASE:
            continue
        boot = paired_bootstrap(pq_by[BASE], pq_by[name], meta, "ndcg@10")
        rboot = paired_bootstrap(pq_by[BASE], pq_by[name], meta, "winner_recall@10")
        strata = _strata_delta(pq_by[BASE], pq_by[name], meta)
        checks = {"weighted_ndcg10_gain": boot["delta"] >= MIN_DELTA and boot["ci90"][0] > 0,
                  "weighted_recall10_guard": rboot["delta"] >= MIN_RECALL_DELTA,
                  "strata_guard": all(v >= -STRATUM_MAX_LOSS for v in strata.values())}
        results[name].update({"vs_baseline": {"weighted_ndcg10": boot, "weighted_winner_recall10": rboot, "stratum_ndcg10_delta": strata},
                              "acceptance_checks": checks, "accepted": all(checks.values())})
        if all(checks.values()):
            accepted.append(name)
    chosen = max(accepted, key=lambda n: (results[n]["weighted"]["ndcg@10"], n)) if accepted else BASE
    cfg = EXPERIMENTS[chosen][0]
    log(f"chosen: {chosen}")
    incumbent = {}
    for name in (BASE, "C3 no customer signal"):
        top = [r for _q, (_ql, recs) in ranked_by[name].items() for r in recs[:10]]
        incumbent[name] = {"top10_suppliers_with_same_customer_history": round(sum(r.same_customer_history for r in top) / max(1, len(top)), 3),
                           "weighted_ndcg@10": results[name]["weighted"]["ndcg@10"], "ndcg@10": results[name]["unweighted"]["ndcg@10"]}
    failures = diagnose(ranked_by[chosen], qrels, meta, max_examples=8)
    log("latency (end-to-end) on DEV …")
    lat = E.latency(conn, queries, cfg)
    log("golden cases (after freeze) …")
    golden = golden_inspection(conn, cfg)
    return {
        "candidate_pool": "frozen (P1-002 retrieval, lot fusion, historical_lot_limit); identical across all configurations (asserted)",
        "selection_rule": SELECTION_RULE, "configurations": results, "accepted_challengers": accepted,
        "chosen": {"name": chosen, "config": cfg.to_dict()},
        "customer_signal_incumbent_analysis": incumbent,
        "difficulty_breakdown": {BASE: _by_difficulty(pq_by[BASE], meta), chosen: _by_difficulty(pq_by[chosen], meta)},
        "stratum_breakdown": {BASE: E.breakdown(pq_by[BASE], meta, "stratum"), chosen: E.breakdown(pq_by[chosen], meta, "stratum")},
        "remaining_failures_chosen": {k: failures[k] for k in ("query_groups", "dominant_cause_counts", "pairwise_examples")},
        "latency_dev_end_to_end_chosen": lat, "golden_cases": golden,
        "golden_p1_002_ranks": {"5718896": 1, "5545252": 17, "5542696": 19, "6022687": 7, "5612123": 27},
        "holdout": "NOT EVALUATED (sealed)", "runtime_seconds": round(time.perf_counter() - t0, 1),
    }
