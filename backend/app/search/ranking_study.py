"""P2-003 ranking study on DEV only (holdout sealed): diagnosis, controlled ranking-only experiments, freeze, golden + latency.

The candidate pool is frozen (same retrieval, same lot fusion, same historical_lot_limit); experiments only change supplier scoring,
so every configuration ranks the identical candidate set (asserted).
"""
from __future__ import annotations

import random
import statistics
import time

from app.search import evaluation as E
from app.search.diagnostics import diagnose, rank_all
from app.search.models import P1_002_BASELINE
from app.shared.config import repo_root

P1_002_REPORTED = {"ndcg@10": 0.5056, "candidate_winner_coverage": 0.8967, "winner_recall@10": 0.6533, "winner_mrr": 0.3885}


def metrics_from_ranked(ranked: dict, qrels: dict) -> dict:
    return {qid: E.query_metrics([r.supplier_id for r in recs], qrels[qid]) for qid, (_q, recs) in ranked.items()}


def conditional(per_query: dict, meta: dict, weighted: bool) -> dict:
    inpool = {q: m for q, m in per_query.items() if m["candidate_winner_coverage"] > 0}
    agg = E.aggregate(inpool, meta, weighted)
    return {"queries_with_winner_in_pool": len(inpool),
            **{k: agg[k] for k in ("winner_recall@1", "winner_recall@5", "winner_recall@10", "winner_recall@20", "winner_mrr", "ndcg@10")}}


def load_dev(conn, log):
    queries, qrels, meta = E.load_benchmark(repo_root(), {"dev"})
    cache = E.prepare_all(conn, queries, P1_002_BASELINE, log)
    return queries, qrels, meta, cache


def run_diagnostics(conn, log=print) -> dict:
    t0 = time.perf_counter()
    queries, qrels, meta, cache = load_dev(conn, log)
    ranked = rank_all(cache, P1_002_BASELINE)
    pq = metrics_from_ranked(ranked, qrels)
    base = E.aggregate(pq, meta, False)
    reproduced = {k: (base[k], v, abs(base[k] - v) < 1e-4) for k, v in P1_002_REPORTED.items()}
    if not all(x[2] for x in reproduced.values()):
        raise RuntimeError(f"frozen baseline does not reproduce P1-002 DEV metrics: {reproduced}")
    return {"baseline_reproduced": {k: {"now": a, "p1_002": b} for k, (a, b, _) in reproduced.items()},
            "conditional_baseline": conditional(pq, meta, False),
            **diagnose(ranked, qrels, meta), "runtime_seconds": round(time.perf_counter() - t0, 1)}


def paired_bootstrap(a: dict, b: dict, meta: dict, key: str, n: int = 2000, seed: int = 20261001) -> dict:
    """Weighted mean difference (b - a) with a 90% percentile CI from a deterministic paired bootstrap over queries."""
    qids = sorted(a)
    w = [float(meta[q]["stratum_weight"]) for q in qids]
    d = [b[q][key] - a[q][key] for q in qids]

    def wmean(idx):
        tw = sum(w[i] for i in idx)
        return sum(w[i] * d[i] for i in idx) / tw
    rng = random.Random(seed)
    stats = sorted(wmean([rng.randrange(len(qids)) for _ in qids]) for _ in range(n))
    return {"delta": round(wmean(range(len(qids))), 4), "ci90": [round(stats[int(0.05 * n)], 4), round(stats[int(0.95 * n)], 4)]}
