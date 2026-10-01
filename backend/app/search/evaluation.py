"""Replay-benchmark evaluation of the P1-002 baseline — WARM-UP and DEV only (holdout is sealed and refused).

Retrieval runs once per query (weights-independent); every configuration re-scores the cached evidence, so candidate generation
and ranking are measured separately: coverage = labelled suppliers present in the candidate pool; recall/MRR/nDCG = after ranking.
Unjudged suppliers are not proven irrelevant: precision-style numbers are not reported.
"""
from __future__ import annotations

import csv
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path

from app.search.candidates import Pool, build_pool, score_lots
from app.search.models import SearchConfig
from app.search.recommend import recommend
from app.search.retrieval import build_query, retrieve
from app.search.scoring import rank_suppliers

ALLOWED_SPLITS = {"warmup", "dev"}
KS = (1, 5, 10, 20)


def load_benchmark(root: Path, splits: set[str]):
    if not splits <= ALLOWED_SPLITS:
        raise PermissionError(f"refusing to evaluate {sorted(splits - ALLOWED_SPLITS)}: holdout is sealed until final evaluation")
    d = root / "benchmark" / "replay"
    with open(d / "queries.csv", encoding="utf-8", newline="") as f:
        queries = [q for q in csv.DictReader(f) if q["split"] in splits]
    keep = {q["query_id"] for q in queries}
    qrels = defaultdict(dict)
    with open(d / "qrels.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["query_id"] in keep:
                qrels[r["query_id"]][r["supplier_id"]] = int(r["relevance_grade"])
    with open(d / "query_metadata.csv", encoding="utf-8", newline="") as f:
        meta = {m["query_id"]: m for m in csv.DictReader(f) if m["query_id"] in keep}
    return queries, qrels, meta


def query_metrics(ranked: list[str], qrel: dict[str, int]) -> dict:
    winners = {s for s, g in qrel.items() if g == 2}
    observed = set(qrel)
    pos = {s: i for i, s in enumerate(ranked)}
    m = {}
    for k in KS:
        top = set(ranked[:k])
        m[f"winner_recall@{k}"] = len(winners & top) / len(winners)
        m[f"observed_recall@{k}"] = len(observed & top) / len(observed)
    first = min((pos[s] for s in winners if s in pos), default=None)
    m["winner_mrr"] = 0.0 if first is None else 1.0 / (first + 1)
    m["winner_rank"] = None if first is None else first + 1
    ideal = sorted(qrel.values(), reverse=True)
    for k in (10, 20):
        dcg = sum((2 ** qrel.get(s, 0) - 1) / math.log2(i + 2) for i, s in enumerate(ranked[:k]))
        idcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(ideal[:k]))
        m[f"ndcg@{k}"] = dcg / idcg if idcg else 0.0
    cand = set(ranked)
    m["candidate_winner_coverage"] = len(winners & cand) / len(winners)
    m["candidate_observed_coverage"] = len(observed & cand) / len(observed)
    m["candidates"] = len(ranked)
    return m


def aggregate(per_query: dict[str, dict], meta: dict, weighted: bool) -> dict:
    keys = [k for k in next(iter(per_query.values())) if k not in ("winner_rank",)]
    w = {q: (float(meta[q]["stratum_weight"]) if weighted else 1.0) for q in per_query}
    tw = sum(w.values())
    return {k: round(sum(w[q] * per_query[q][k] for q in per_query) / tw, 4) for k in keys}


def prepare_all(conn, queries, base: SearchConfig, log=None):
    cache = {}
    for i, q in enumerate(queries, 1):
        t0 = time.perf_counter()
        ql, idf = build_query(conn, q["lot_id"], base)
        ret = retrieve(conn, ql, base, idf)
        lots = score_lots(ql, ret, idf, base)
        pool = build_pool(conn, ql, lots, len(lots))        # relations for every retrieved lot (any limit is a prefix)
        cache[q["query_id"]] = (ql, ret, idf, pool, (time.perf_counter() - t0) * 1000)
        if log and i % 50 == 0:
            log(f"prepared {i}/{len(queries)}")
    return cache


def evaluate_config(cache, qrels, cfg: SearchConfig) -> dict[str, dict]:
    out = {}
    for qid, (ql, ret, idf, pool_all, _ms) in cache.items():
        lots = score_lots(ql, ret, idf, cfg)
        pool = Pool(lots=lots, relations=pool_all.relations, same_customer=pool_all.same_customer)
        recs, _ = rank_suppliers(ql, pool, cfg)
        out[qid] = query_metrics([r.supplier_id for r in recs], qrels[qid])
    return out


def breakdown(per_query: dict, meta: dict, field: str) -> dict:
    groups = defaultdict(dict)
    for q, m in per_query.items():
        groups[meta[q][field]][q] = m
    return {g: {"queries": len(v), **{k: x for k, x in aggregate(v, meta, False).items()
                                      if k in ("winner_recall@10", "winner_mrr", "ndcg@10", "candidate_winner_coverage")}}
            for g, v in sorted(groups.items())}


def latency(conn, queries, cfg: SearchConfig) -> dict:
    ms = []
    for q in queries:
        ms.append(recommend(conn, q["lot_id"], cfg)["timings_ms"]["total_ms"])
    ms.sort()
    return {"queries": len(ms), "p50_ms": round(statistics.median(ms), 1), "p95_ms": round(ms[int(0.95 * (len(ms) - 1))], 1),
            "max_ms": round(ms[-1], 1), "mean_ms": round(statistics.fmean(ms), 1)}
