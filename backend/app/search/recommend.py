"""End-to-end baseline recommendation: query -> retrieval -> lot aggregation -> candidates -> scoring (timed)."""
from __future__ import annotations

import time
from dataclasses import asdict
from datetime import date

from app.search.candidates import build_pool, score_lots
from app.search.models import BASELINE_VERSION, DEFAULT_CONFIG, SearchConfig
from app.search.retrieval import build_query, retrieve
from app.search.scoring import rank_suppliers


def prepare(conn, lot_id: str, cfg: SearchConfig, as_of: date | None = None, pool_lots: int | None = None):
    """Everything up to the supplier pool (weights-independent); reused by evaluation across configurations."""
    t0 = time.perf_counter()
    q, idf = build_query(conn, lot_id, cfg, as_of)
    query_ms = (time.perf_counter() - t0) * 1000
    ret, pool, t = prepare_query(conn, q, idf, cfg, pool_lots)
    return q, ret, pool, {"query_ms": query_ms, **t}


def prepare_query(conn, q, idf, cfg: SearchConfig, pool_lots: int | None = None):
    """The shared pipeline after query construction (lot query or free-text query): retrieval -> lot aggregation -> pool."""
    t = {}
    t1 = time.perf_counter()
    ret = retrieve(conn, q, cfg, idf)
    t["retrieval_ms"] = (time.perf_counter() - t1) * 1000
    t2 = time.perf_counter()
    lots = score_lots(q, ret, idf, cfg)
    t["lot_aggregation_ms"] = (time.perf_counter() - t2) * 1000
    t3 = time.perf_counter()
    pool = build_pool(conn, q, lots, pool_lots or cfg.historical_lot_limit)
    t["candidates_ms"] = (time.perf_counter() - t3) * 1000
    return ret, pool, t


def recommend(conn, lot_id: str, cfg: SearchConfig | None = None, as_of: date | None = None) -> dict:
    """cfg omitted -> DEFAULT_CONFIG (the accepted P2-001 configuration)."""
    cfg = cfg or DEFAULT_CONFIG
    t0 = time.perf_counter()
    q, ret, pool, t = prepare(conn, lot_id, cfg, as_of)
    t4 = time.perf_counter()
    recs, _ = rank_suppliers(q, pool, cfg)
    t["scoring_ms"] = (time.perf_counter() - t4) * 1000
    t["total_ms"] = (time.perf_counter() - t0) * 1000
    return {
        "baseline_version": BASELINE_VERSION, "lot_id": lot_id, "as_of": q.as_of.isoformat(),
        "query": {"subject": q.subject, "items_used": len(q.items), "items_total": q.total_items,
                  "items": [{"product_name": qi.product_name[:200], "okpd2": qi.okpd2["code"] if qi.okpd2 else None,
                             "technical_tokens": qi.tech_tokens} for qi in q.items],
                  "customer_known": q.customer_inn is not None},
        "retrieval": {"branch_rows": ret.branch_hits, "branch_ms": ret.branch_ms, "historical_items": len(ret.items), "historical_lots": len(pool.lots)},
        "warnings": ret.warnings,
        "candidates": len(recs), "results": [asdict(r) for r in recs[:cfg.top_k]],
        "timings_ms": {k: round(v, 1) for k, v in t.items()}, "config": cfg.to_dict(),
    }
