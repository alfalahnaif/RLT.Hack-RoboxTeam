"""P4-003 — one-time final HOLDOUT evaluation of the frozen system (evaluation record; no tuning).

Usage (backend container, PYTHONPATH=/srv/backend):
  python /srv/scripts/p4_003_final_holdout.py --split dev                          # dry run: must reproduce published DEV numbers
  python /srv/scripts/p4_003_final_holdout.py --split holdout --confirm-final-holdout

Pipeline per query = the DEV semantic experiment (app.search.semantic_experiments.run): one retrieval with the frozen final
configuration (semantic_top_k = 100), then each frozen configuration is scored on its own view (restrict_semantic to its own
semantic_top_k; 0 = lexical/OKPD2 only). Metrics, aggregation, conditional recall, paired bootstrap and the failure taxonomy are
the existing functions/definitions, imported unchanged. Only three already-frozen configurations are scored; nothing is selected.
The holdout loader mirrors app.search.evaluation.load_benchmark (whose guard is left in place for every other caller).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import psycopg

from app.search import evaluation as E
from app.search import semantic
from app.search.candidates import Pool, build_pool, score_lots
from app.search.models import DEFAULT_CONFIG, P1_002_BASELINE, P2_001_SEMANTIC, P2_003_RANKING
from app.search.ranking_study import conditional, paired_bootstrap
from app.search.retrieval import build_query, restrict_semantic, retrieve
from app.search.scoring import rank_suppliers
from app.shared.config import database_url, repo_root

CONFIGS = {"A P1-002 baseline": P1_002_BASELINE, "B P2-003 ranking": P2_003_RANKING, "C P2-001 S3 (final)": P2_001_SEMANTIC}
FINAL, PREV = "C P2-001 S3 (final)", "B P2-003 ranking"


def load_split(root: Path, split: str):
    d = root / "benchmark" / "replay"
    with open(d / "queries.csv", encoding="utf-8", newline="") as f:
        queries = [q for q in csv.DictReader(f) if q["split"] == split]
    keep = {q["query_id"] for q in queries}
    qrels = defaultdict(dict)
    with open(d / "qrels.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["query_id"] in keep:
                qrels[r["query_id"]][r["supplier_id"]] = int(r["relevance_grade"])
    with open(d / "query_metadata.csv", encoding="utf-8", newline="") as f:
        meta = {m["query_id"]: m for m in csv.DictReader(f) if m["query_id"] in keep}
    return queries, qrels, meta


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def failure_row(conn, q, ql, meta, qrels, per_final, ranked_final) -> dict:
    """Same taxonomy and thresholds as the DEV analysis (semantic_experiments.run)."""
    winners = sorted(s for s, g in qrels[q].items() if g == 2)
    hist = conn.execute("SELECT count(*) FROM supplier_history WHERE supplier_id = ANY(%s::uuid[]) AND publish_date < %s",
                        (winners, ql.as_of)).fetchone()[0]
    status = "RECOVERED" if per_final[q]["candidate_winner_coverage"] > 0 else "STILL_MISSING"
    row = {"query_id": q, "difficulty": meta[q]["difficulty"], "status": status, "winner_visible_relations": hist}
    if status == "RECOVERED":
        row["winner_rank"] = per_final[q]["winner_rank"]
        row["category"] = "recovered by semantic retrieval"
        ev = [e for r in ranked_final[q] if r.supplier_id in set(winners) for e in r.semantic_evidence]
        row["has_semantic_evidence"] = bool(ev)
        return row
    if hist == 0:
        row["category"] = "unseen supplier before cutoff"
        return row
    texts = [r[0] for r in conn.execute("""SELECT DISTINCT i.product_name_normalized FROM supplier_history h
        JOIN procurement_item i ON i.lot_id = h.lot_id WHERE h.supplier_id = ANY(%s::uuid[]) AND h.publish_date < %s
        AND i.publish_date < %s AND i.product_name_normalized IS NOT NULL ORDER BY 1 LIMIT 1000""",
                                                 (winners, ql.as_of, ql.as_of)).fetchall()]
    qtexts = [qi.product_name for qi in ql.items if qi.product_name]
    best = float((semantic.encode(qtexts, "query") @ semantic.encode(texts, "document").T).max()) if texts and qtexts else None
    row["winner_best_history_cosine"] = None if best is None else round(best, 4)
    row["category"] = ("no relevant historical procurement" if best is not None and best < 0.86
                       else "related history outside cap/lot limit")
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "holdout"], required=True)
    ap.add_argument("--confirm-final-holdout", action="store_true")
    args = ap.parse_args()
    root = repo_root()
    out_path = root / "reports" / ("p4_003_final_holdout.json" if args.split == "holdout" else "p4_003_dev_reproduction.json")
    if args.split == "holdout":
        if not args.confirm_final_holdout:
            print("refusing: the holdout is evaluated once, with --confirm-final-holdout", file=sys.stderr)
            return 2
        if out_path.exists():
            print(f"refusing: {out_path.name} already exists — the holdout has been evaluated", file=sys.stderr)
            return 2
    assert DEFAULT_CONFIG == P2_001_SEMANTIC and P2_001_SEMANTIC.semantic_top_k == 100
    assert P2_001_SEMANTIC.with_(semantic_top_k=0) == P2_003_RANKING

    t0 = time.perf_counter()
    queries, qrels, meta = load_split(root, args.split)
    log = lambda m: print(f"[p4-003 {args.split}] {m}", file=sys.stderr, flush=True)  # noqa: E731
    log(f"{len(queries)} queries")
    per = {n: {} for n in CONFIGS}
    ranked_final = {}
    with psycopg.connect(database_url()) as conn:
        cache = {}
        for i, q in enumerate(queries, 1):
            ql, idf = build_query(conn, q["lot_id"], P2_001_SEMANTIC)
            ret = retrieve(conn, ql, P2_001_SEMANTIC, idf)
            lots_all = score_lots(ql, ret, idf, P2_001_SEMANTIC)
            pool_all = build_pool(conn, ql, lots_all, len(lots_all))
            conn.rollback()
            cache[q["query_id"]] = ql
            for name, cfg in CONFIGS.items():
                view = restrict_semantic(ret, cfg.semantic_top_k)
                lots = score_lots(ql, view, idf, cfg)
                recs, _ = rank_suppliers(ql, Pool(lots=lots, relations=pool_all.relations, same_customer=pool_all.same_customer), cfg)
                per[name][q["query_id"]] = E.query_metrics([r.supplier_id for r in recs], qrels[q["query_id"]])
                if name == FINAL:
                    ranked_final[q["query_id"]] = recs
            if i % 50 == 0:
                log(f"scored {i}/{len(queries)}")
        configs = {}
        for name, cfg in CONFIGS.items():
            pq = per[name]
            configs[name] = {
                "config_delta_vs_default": {k: v for k, v in cfg.to_dict().items() if v != DEFAULT_CONFIG.to_dict()[k]},
                "unweighted": E.aggregate(pq, meta, False), "weighted": E.aggregate(pq, meta, True),
                "conditional_unweighted": conditional(pq, meta, False), "conditional_weighted": conditional(pq, meta, True),
                "by_difficulty": {d: {"queries": sum(1 for q in pq if meta[q]["difficulty"] == d),
                                      **E.aggregate({q: m for q, m in pq.items() if meta[q]["difficulty"] == d}, meta, False)}
                                  for d in ("EASY", "MEDIUM", "HARD")},
            }
        a, b, c = per["A P1-002 baseline"], per[PREV], per[FINAL]
        comparisons = {
            "C_vs_B_weighted_ndcg10": paired_bootstrap(b, c, meta, "ndcg@10"),
            "C_vs_B_weighted_winner_recall10": paired_bootstrap(b, c, meta, "winner_recall@10"),
            "C_vs_B_weighted_coverage": paired_bootstrap(b, c, meta, "candidate_winner_coverage"),
            "B_vs_A_weighted_ndcg10": paired_bootstrap(a, b, meta, "ndcg@10"),
            "B_vs_A_weighted_winner_recall10": paired_bootstrap(a, b, meta, "winner_recall@10"),
            "C_vs_A_weighted_ndcg10": paired_bootstrap(a, c, meta, "ndcg@10"),
        }
        cls = {"present_before": 0, "newly_recovered": 0, "still_absent": 0, "lost": 0}
        for q in c:
            was, now = b[q]["candidate_winner_coverage"] > 0, c[q]["candidate_winner_coverage"] > 0
            cls["present_before" if was and now else "newly_recovered" if now else "lost" if was else "still_absent"] += 1
        log("failure analysis (P2-003 retrieval failures, status under S3)")
        failures = [failure_row(conn, q, cache[q], meta, qrels, c, ranked_final) for q in sorted(b) if b[q]["candidate_winner_coverage"] == 0]
        conn.rollback()
    summary = defaultdict(int)
    for f in failures:
        summary[f["category"]] += 1
    by_diff = defaultdict(lambda: defaultdict(int))
    for f in failures:
        by_diff[f["difficulty"]][f["category"]] += 1
    result = {
        "task": "P4-003", "split": args.split, "queries": len(queries),
        "difficulty_counts": {d: sum(1 for q in meta.values() if q["difficulty"] == d) for d in ("EASY", "MEDIUM", "HARD")},
        "benchmark_files_sha256": {n: sha256(root / "benchmark" / "replay" / n) for n in ("queries.csv", "qrels.csv", "query_metadata.csv")},
        "frozen_final_config": DEFAULT_CONFIG.to_dict(), "semantic_model": semantic.lock(),
        "configurations": configs, "paired_bootstrap_90ci": comparisons,
        "final_vs_p2003_winner_pool": cls,
        "retrieval_failure_analysis": {"baseline_failures": len(failures), "summary": dict(summary),
                                       "by_difficulty": {d: dict(v) for d, v in by_diff.items()},
                                       "final_system_failures": sum(1 for q in c if c[q]["candidate_winner_coverage"] == 0),
                                       "rows": failures},
        "runtime_seconds": round(time.perf_counter() - t0, 1),
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    for n, r in configs.items():
        log(f"{n}: cov={r['unweighted']['candidate_winner_coverage']} R@10={r['unweighted']['winner_recall@10']} "
            f"nDCG@10={r['unweighted']['ndcg@10']} w-nDCG@10={r['weighted']['ndcg@10']}")
    log(f"wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
