"""P2-001 semantic candidate-expansion experiments — DEV only (holdout sealed), ranking frozen at P2_003_RANKING.

Retrieval runs once per query with the largest semantic cap; each configuration is a view with a smaller cap (restrict_semantic), so
lexical/OKPD2 evidence is identical across configurations and S0 reproduces P2-003 exactly.
ACCEPTANCE (declared before results): see ACCEPTANCE. Labels are used only to measure, never to retrieve.
"""
from __future__ import annotations

import statistics
import time

from app.search import evaluation as E
from app.search import semantic
from app.search.candidates import Pool, build_pool, score_lots
from app.search.models import P2_003_RANKING
from app.search.ranking_study import conditional, paired_bootstrap
from app.search.retrieval import build_query, restrict_semantic, retrieve
from app.search.scoring import rank_suppliers
from app.shared.config import repo_root

R = P2_003_RANKING
MAX_K = 100
S0 = "S0 P2-003 (semantic off)"
CONFIGS = {
    S0: R,
    "S1 semantic top-25": R.with_(semantic_top_k=25),
    "S2 semantic top-50": R.with_(semantic_top_k=50),
    "S3 semantic top-100": R.with_(semantic_top_k=100),
    "S4 semantic top-50, λ=0.6": R.with_(semantic_top_k=50, semantic_weight=0.6),
}
ACCEPTANCE = {
    "A_coverage": "candidate winner coverage >= +2 percentage points overall, OR >= 3 additional MEDIUM+HARD winners recovered",
    "B_quality": "population-weighted nDCG@10 delta >= -0.005",
    "C_recall": "population-weighted winner Recall@10 delta >= -0.005",
    "D_latency": "end-to-end p95 <= 5 s (hard limit 10 s), measured for the chosen configuration",
    "E_explainable": "semantic evidence (text, cosine, lot, date, OKPD2) exposed for every semantic-based candidate (by construction)",
    "choose": "largest overall coverage gain among accepted; tie -> smaller semantic_top_k; none accepted -> semantic stays OFF",
}


def _winner_semantic_evidence(recs, winners) -> list:
    out = []
    for r in recs:
        if r.supplier_id in winners:
            out += [{"rank": r.rank, **ev} for ev in r.semantic_evidence]
    return out[:3]


def run(conn, log=print) -> dict:
    from app.search.report import golden_inspection
    t0 = time.perf_counter()
    semantic.encoder()                       # cold model load, once per process (reported separately by `evaluate semantic-latency`)
    cold_model_load_s = round(time.perf_counter() - t0, 2)
    queries, qrels, meta = E.load_benchmark(repo_root(), {"dev"})
    full = R.with_(semantic_top_k=MAX_K)
    cache = {}
    for i, q in enumerate(queries, 1):
        ql, idf = build_query(conn, q["lot_id"], full)
        ret = retrieve(conn, ql, full, idf)
        lots_all = score_lots(ql, ret, idf, full)
        pool_all = build_pool(conn, ql, lots_all, len(lots_all))
        conn.rollback()                      # end the read transaction (SET LOCAL hnsw settings)
        cache[q["query_id"]] = (ql, ret, idf, pool_all)
        if i % 50 == 0:
            log(f"prepared {i}/{len(queries)}")
    per, ranked_by, results = {}, {}, {}
    for name, cfg in CONFIGS.items():
        pq, rk = {}, {}
        for qid, (ql, ret, idf, pool_all) in cache.items():
            view = restrict_semantic(ret, cfg.semantic_top_k)
            lots = score_lots(ql, view, idf, cfg)
            recs, _ = rank_suppliers(ql, Pool(lots=lots, relations=pool_all.relations, same_customer=pool_all.same_customer), cfg)
            rk[qid] = recs
            pq[qid] = E.query_metrics([r.supplier_id for r in recs], qrels[qid])
        per[name], ranked_by[name] = pq, rk
        results[name] = {"config_delta": {k: v for k, v in cfg.to_dict().items() if v != R.to_dict()[k]},
                         "unweighted": E.aggregate(pq, meta, False), "weighted": E.aggregate(pq, meta, True),
                         "conditional_unweighted": conditional(pq, meta, False), "conditional_weighted": conditional(pq, meta, True),
                         "by_difficulty": {d: E.aggregate({q: m for q, m in pq.items() if meta[q]["difficulty"] == d}, meta, False)
                                           for d in ("EASY", "MEDIUM", "HARD")}}
        log(f"{name}: coverage={results[name]['unweighted']['candidate_winner_coverage']} w-nDCG@10={results[name]['weighted']['ndcg@10']}")
    base = per[S0]
    for name in CONFIGS:
        if name == S0:
            continue
        pq = per[name]
        cls = {"present_before": 0, "newly_recovered": 0, "still_absent": 0, "lost": 0}
        recovered_mh, recovered = 0, []
        for q in pq:
            b, a = base[q]["candidate_winner_coverage"] > 0, pq[q]["candidate_winner_coverage"] > 0
            key = "present_before" if b and a else "newly_recovered" if a else "lost" if b else "still_absent"
            cls[key] += 1
            if key == "newly_recovered":
                winners = {s for s, g in qrels[q].items() if g == 2}
                recovered.append({"query_id": q, "difficulty": meta[q]["difficulty"], "winner_rank": pq[q]["winner_rank"],
                                  "query_items": [qi.product_name[:120] for qi in cache[q][0].items[:2]],
                                  "winner_semantic_evidence": _winner_semantic_evidence(ranked_by[name][q], winners)})
                recovered_mh += meta[q]["difficulty"] in ("MEDIUM", "HARD")
        pool_growth = [pq[q]["candidates"] - base[q]["candidates"] for q in pq]
        cov_gain = results[name]["unweighted"]["candidate_winner_coverage"] - results[S0]["unweighted"]["candidate_winner_coverage"]
        boot = paired_bootstrap(base, pq, meta, "ndcg@10")
        rboot = paired_bootstrap(base, pq, meta, "winner_recall@10")
        checks = {"A_coverage": cov_gain >= 0.02 or recovered_mh >= 3, "B_quality": boot["delta"] >= -0.005, "C_recall": rboot["delta"] >= -0.005}
        results[name].update({"winner_pool_classification": cls, "recovered_medium_hard": recovered_mh,
                              "coverage_gain_pp": round(100 * cov_gain, 2), "new_candidates_per_query_mean": round(statistics.fmean(pool_growth), 1),
                              "candidate_pool_growth_pct": round(100 * statistics.fmean(pool_growth) /
                                                                 max(1e-9, results[S0]["unweighted"]["candidates"]), 1),
                              "vs_s0": {"weighted_ndcg10": boot, "weighted_winner_recall10": rboot}, "acceptance_checks_abc": checks,
                              "recovered_queries": recovered})
    accepted = [n for n in CONFIGS if n != S0 and all(results[n]["acceptance_checks_abc"].values())]
    chosen = max(accepted, key=lambda n: (results[n]["coverage_gain_pp"], -CONFIGS[n].semantic_top_k, n)) if accepted else S0
    cfg = CONFIGS[chosen]
    log(f"chosen (before latency check): {chosen}")
    # 31-failure analysis under the chosen configuration
    failures = []
    for q, m in base.items():
        if m["candidate_winner_coverage"] > 0:
            continue
        ql = cache[q][0]
        winners = sorted(s for s, g in qrels[q].items() if g == 2)
        hist = conn.execute("SELECT count(*) FROM supplier_history WHERE supplier_id = ANY(%s::uuid[]) AND publish_date < %s",
                            (winners, ql.as_of)).fetchone()[0]
        status = "RECOVERED" if per[chosen][q]["candidate_winner_coverage"] > 0 else "STILL_MISSING"
        row = {"query_id": q, "difficulty": meta[q]["difficulty"], "status": status,
               "query_items": [qi.product_name[:120] for qi in ql.items[:2]], "winner_visible_relations": hist}
        if status == "RECOVERED":
            row["winner_rank"] = per[chosen][q]["winner_rank"]
            row["semantic_evidence"] = _winner_semantic_evidence(ranked_by[chosen][q], set(winners))
        else:
            if hist == 0:
                row["likely_reason"] = "genuinely unseen supplier (no visible history before the lot date)"
            else:
                texts = [r[0] for r in conn.execute("""SELECT DISTINCT i.product_name_normalized FROM supplier_history h
                    JOIN procurement_item i ON i.lot_id = h.lot_id WHERE h.supplier_id = ANY(%s::uuid[]) AND h.publish_date < %s
                    AND i.publish_date < %s AND i.product_name_normalized IS NOT NULL ORDER BY 1 LIMIT 1000""",
                    (winners, ql.as_of, ql.as_of)).fetchall()]
                qtexts = [qi.product_name for qi in ql.items if qi.product_name]
                best = float((semantic.encode(qtexts, "query") @ semantic.encode(texts, "document").T).max()) if texts and qtexts else None
                row["winner_best_history_cosine"] = None if best is None else round(best, 4)
                row["likely_reason"] = ("no relevant historical procurement (winner's history is about other products)" if best is not None and best < 0.86
                                        else "related history exists but outside the semantic cap / lot limit (different terminology or broad category)")
        failures.append(row)
    log("latency (end-to-end, warm) on DEV …")
    lat = E.latency(conn, queries, cfg)
    results_lat = {"chosen": lat, "model_load_seconds_once_per_process": cold_model_load_s}
    accept_d = lat["p95_ms"] <= 5000
    if chosen != S0 and not accept_d:
        log("chosen config fails the latency gate -> semantic stays OFF")
        chosen, cfg = S0, CONFIGS[S0]
    log("golden cases (after freeze) …")
    golden = golden_inspection(conn, cfg)
    return {
        "acceptance_rule": ACCEPTANCE, "configurations": results, "accepted_abc": accepted, "latency_gate_passed": accept_d,
        "chosen": {"name": chosen, "config": cfg.to_dict()}, "retrieval_failure_analysis": failures,
        "latency": results_lat, "golden_cases": golden,
        "golden_p2_003_ranks": {"5718896": 1, "5545252": 16, "5542696": 11, "6022687": 7, "5612123": 32},
        "holdout": "NOT EVALUATED (sealed)", "runtime_seconds": round(time.perf_counter() - t0, 1),
    }


VECTOR_ONLY_SQL = """SELECT s.text_hash FROM semantic_text s WHERE s.first_seen_publish_date < %(as_of)s AND s.embedding IS NOT NULL
ORDER BY s.embedding <=> %(qv)s LIMIT %(k)s"""


def latency_breakdown(conn, cfg) -> dict:
    """Per-stage latency on DEV (fresh process): cold model load, query embedding, vector search alone, vector search + item mapping,
    lexical/OKPD2 branches, lot aggregation + fusion, candidates, scoring, total. Mapping = semantic SQL minus vector-only SQL."""
    from pgvector.psycopg import register_vector
    from app.search.recommend import recommend
    t = time.perf_counter()
    semantic.encoder()
    cold = round(time.perf_counter() - t, 2)
    queries, _qrels, _meta = E.load_benchmark(repo_root(), {"dev"})
    register_vector(conn)
    stages: dict[str, list[float]] = {}
    first_total = None
    for q in queries:
        out = recommend(conn, q["lot_id"], cfg)
        conn.rollback()
        tm, br = out["timings_ms"], out["retrieval"]["branch_ms"]
        if first_total is None:
            first_total = tm["total_ms"]
        ql, _idf = build_query(conn, q["lot_id"], cfg)
        texts = [qi.product_name for qi in ql.items if qi.product_name]
        vec_ms = 0.0
        if texts:
            conn.execute(f"SET LOCAL hnsw.ef_search = {int(cfg.semantic_ef_search)}")
            conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
            for v in semantic.encode(texts, "query"):
                t = time.perf_counter()
                conn.execute(VECTOR_ONLY_SQL, {"qv": v, "as_of": ql.as_of, "k": cfg.semantic_top_k}).fetchall()
                vec_ms += (time.perf_counter() - t) * 1000
        conn.rollback()
        sem = br.get("semantic", 0.0)
        row = {"query_embedding_ms": br.get("semantic_embed", 0.0), "vector_search_ms": vec_ms, "item_mapping_ms": max(0.0, sem - vec_ms),
               "lexical_okpd2_branches_ms": sum(v for k, v in br.items() if not k.startswith("semantic")),
               "lot_aggregation_fusion_ms": tm["lot_aggregation_ms"], "candidates_ms": tm["candidates_ms"], "scoring_ms": tm["scoring_ms"],
               "total_ms": tm["total_ms"]}
        for k, v in row.items():
            stages.setdefault(k, []).append(v)

    def summ(xs):
        xs = sorted(xs)
        return {"p50": round(statistics.median(xs), 1), "p95": round(xs[int(0.95 * (len(xs) - 1))], 1), "max": round(xs[-1], 1),
                "mean": round(statistics.fmean(xs), 1)}
    return {"queries": len(queries), "cold_model_load_seconds": cold, "first_request_total_ms_after_model_load": first_total,
            "stages_warm": {k: summ(v) for k, v in stages.items()}}
