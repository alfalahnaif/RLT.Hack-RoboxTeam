"""P1-002 baseline evaluation driver: DEV config comparison -> freeze -> warm-up check -> latency -> golden inspection -> reports.

Pre-declared selection rule (set before any result was seen): highest DEV unweighted nDCG@10; a challenger must beat the
default configuration by more than SELECTION_TOLERANCE, otherwise the simpler default is kept. HOLDOUT is never loaded.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from app.search import evaluation as E
from app.search.models import BASELINE_VERSION, SearchConfig
from app.search.recommend import recommend
from app.shared.config import repo_root

SELECTION_TOLERANCE = 0.005
GOLDEN = ["5718896", "5545252", "5542696", "6022687", "5612123"]
NAIVE_RANKS = {"5718896": "2", "5545252": "70–83", "5542696": "155–290", "6022687": "27–29", "5612123": "9–10"}

BASE = SearchConfig()
CONFIGS = {
    "default (limit 300, lot fusion 0.6/0.3/0.1)": BASE,
    "historical_lot_limit=100": BASE.with_(historical_lot_limit=100),
    "historical_lot_limit=500": BASE.with_(historical_lot_limit=500),
    "lot fusion text-heavy 0.75/0.2/0.05": BASE.with_(w_lot_text=0.75, w_lot_okpd2=0.2, w_lot_subject=0.05),
    "lot fusion balanced 0.45/0.45/0.1": BASE.with_(w_lot_text=0.45, w_lot_okpd2=0.45, w_lot_subject=0.1),
    "wider saturation (evidence 10, awards 6, participation 6)": BASE.with_(evidence_saturation=10.0, awards_saturation=6.0,
                                                                            participation_saturation=6.0),
}


def revision(root: Path) -> dict:
    files = sorted((root / "backend" / "app" / "search").glob("*.py")) + [root / "backend" / "app" / "benchmark" / "temporal.py",
                                                                            root / "backend" / "app" / "shared" / "normalize.py"]
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return {"source_sha256": h.hexdigest(), "files": [str(f.relative_to(root)).replace("\\", "/") for f in files],
            "benchmark_manifest_sha256": hashlib.sha256((root / "benchmark" / "replay" / "manifest.json").read_bytes()).hexdigest(),
            "baseline_version": BASELINE_VERSION}


def golden_inspection(conn, cfg: SearchConfig) -> dict:
    out = {}
    for lot in GOLDEN:
        res = recommend(conn, lot, cfg.with_(top_k=10_000))
        winners = {r[0] for r in conn.execute("SELECT supplier_id::text FROM supplier_history WHERE lot_id = %s AND is_winner",
                                              (lot,)).fetchall()}   # evaluation display only — never a query input
        observed = {r[0] for r in conn.execute("SELECT supplier_id::text FROM supplier_history WHERE lot_id = %s", (lot,)).fetchall()}
        ranks = [r["rank"] for r in res["results"] if r["supplier_id"] in winners]
        out[lot] = {
            "winner_rank": ranks[0] if ranks else None, "naive_award_count_rank_p1_001a": NAIVE_RANKS[lot],
            "candidates": res["candidates"], "observed_suppliers_in_top10": sum(1 for r in res["results"][:10] if r["supplier_id"] in observed),
            "timings_ms": res["timings_ms"], "query": res["query"],
            "top10": [{k: r[k] for k in ("rank", "score", "components", "relevant_lots", "relevant_awards", "relevant_em_participations",
                                         "best_products", "best_okpd2", "most_recent_relevant", "same_customer_history", "reasons")}
                      | {"is_actual_winner": r["supplier_id"] in winners, "observed_on_lot": r["supplier_id"] in observed}
                      for r in res["results"][:10]],
        }
    return out


def run(conn, log=print) -> dict:
    root = repo_root()
    t0 = time.perf_counter()
    dev_q, qrels, meta = E.load_benchmark(root, {"dev"})
    log(f"DEV queries: {len(dev_q)}")
    cache = E.prepare_all(conn, dev_q, BASE, log)
    compared = {}
    per_query_by_name = {}
    for name, cfg in CONFIGS.items():
        pq = E.evaluate_config(cache, qrels, cfg)
        per_query_by_name[name] = pq
        compared[name] = {"config_delta": {k: v for k, v in cfg.to_dict().items() if v != BASE.to_dict()[k]},
                          "unweighted": E.aggregate(pq, meta, False), "weighted": E.aggregate(pq, meta, True)}
        log(f"{name}: nDCG@10={compared[name]['unweighted']['ndcg@10']} MRR={compared[name]['unweighted']['winner_mrr']}")
    default = next(iter(CONFIGS))
    best = max(CONFIGS, key=lambda n: (compared[n]["unweighted"]["ndcg@10"], n == default))
    chosen = best if compared[best]["unweighted"]["ndcg@10"] > compared[default]["unweighted"]["ndcg@10"] + SELECTION_TOLERANCE else default
    cfg = CONFIGS[chosen]
    log(f"chosen: {chosen}")
    pq = per_query_by_name[chosen]
    dev = {"queries": len(pq), "unweighted": compared[chosen]["unweighted"], "weighted": compared[chosen]["weighted"],
           "by_difficulty": E.breakdown(pq, meta, "difficulty"), "by_okpd2_stratum": E.breakdown(pq, meta, "stratum"),
           "queries_without_candidates": sum(1 for m in pq.values() if m["candidates"] == 0),
           "winner_not_in_candidates": sum(1 for m in pq.values() if m["candidate_winner_coverage"] < 1),
           "winner_rank_distribution": _rank_hist(pq)}
    wq, wqrels, wmeta = E.load_benchmark(root, {"warmup"})
    wcache = E.prepare_all(conn, wq, cfg)
    wpq = E.evaluate_config(wcache, wqrels, cfg)
    warmup = {"queries": len(wpq), "unweighted": E.aggregate(wpq, wmeta, False), "weighted": E.aggregate(wpq, wmeta, True)}
    log("latency (end-to-end, fresh) on DEV …")
    lat = E.latency(conn, dev_q, cfg)
    log("golden inspection (after freeze) …")
    golden = golden_inspection(conn, cfg)
    stats_meta = conn.execute("SELECT snapshot_before, documents, ts_config FROM lexeme_stats_meta").fetchone()
    return {
        "baseline_version": BASELINE_VERSION, "revision": revision(root),
        "lexeme_stats": {"snapshot_before": stats_meta[0].isoformat(), "documents": stats_meta[1], "ts_config": stats_meta[2]},
        "selection_rule": f"highest DEV unweighted nDCG@10; challenger must beat default by > {SELECTION_TOLERANCE}",
        "chosen_configuration": {"name": chosen, "config": cfg.to_dict()},
        "configurations_evaluated_on_dev": compared, "dev": dev, "warmup": warmup, "latency_dev_end_to_end": lat,
        "golden_cases": golden, "holdout": "NOT EVALUATED (sealed)", "runtime_seconds": round(time.perf_counter() - t0, 1),
    }


def _rank_hist(pq: dict) -> dict:
    buckets = {"1": 0, "2-5": 0, "6-10": 0, "11-20": 0, "21-50": 0, "51+": 0, "not candidate": 0}
    for m in pq.values():
        r = m["winner_rank"]
        key = ("not candidate" if r is None else "1" if r == 1 else "2-5" if r <= 5 else "6-10" if r <= 10 else
               "11-20" if r <= 20 else "21-50" if r <= 50 else "51+")
        buckets[key] += 1
    return buckets
