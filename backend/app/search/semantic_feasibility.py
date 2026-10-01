"""P2-001 feasibility gate — run BEFORE any pgvector / full-corpus indexing. DEV only; holdout never loaded.

Corpus: a deterministic random sample of distinct normalized product texts from items of lots published before CORPUS_BEFORE
(2025-01-01, earlier than every DEV query → visible to all of them).
Recoverability (diagnostic, uses labels ONLY to measure, never to retrieve): for each DEV retrieval failure, the winner's own
visible historical item texts are embedded; the best winner text's rank among the sample corpus (cosine to any selected query item)
is scaled to the full visible corpus size. A failure is "plausibly recoverable" when that estimated rank <= RECOVERY_TOP_K texts
(the largest per-item cap that would be tested).
GATE (declared before running): GO if plausibly_recoverable_failures >= GATE_MIN_RECOVERABLE, else STOP (P2-001 not justified).
"""
from __future__ import annotations

import time
from datetime import date

import numpy as np

from app.search import evaluation as E
from app.search import semantic
from app.search.models import P2_003_RANKING
from app.search.scoring import rank_suppliers
from app.search.candidates import Pool, score_lots
from app.shared.config import repo_root

CORPUS_BEFORE = date(2025, 1, 1)
SAMPLE_SIZE = 100_000
SAMPLE_SEED = "p2-001-feasibility"
RECOVERY_TOP_K = 100
GATE_MIN_RECOVERABLE = 5
SUCCESS_SAMPLE = 30


def _corpus(conn) -> tuple[list[str], int]:
    n_full = conn.execute("""SELECT count(DISTINCT product_name_normalized) FROM procurement_item
                             WHERE publish_date < '2025-07-01' AND product_name_normalized IS NOT NULL""").fetchone()[0]
    rows = conn.execute("""SELECT t FROM (SELECT DISTINCT product_name_normalized AS t FROM procurement_item
                           WHERE publish_date < %s AND product_name_normalized IS NOT NULL) d
                           ORDER BY md5(%s || t) LIMIT %s""", (CORPUS_BEFORE, SAMPLE_SEED, SAMPLE_SIZE)).fetchall()
    return [r[0] for r in rows], n_full


def _winner_texts(conn, winner: str, as_of) -> list[str]:
    return [r[0] for r in conn.execute("""SELECT DISTINCT i.product_name_normalized FROM supplier_history h
        JOIN procurement_item i ON i.lot_id = h.lot_id
        WHERE h.supplier_id = %s::uuid AND h.publish_date < %s AND i.publish_date < %s AND i.product_name_normalized IS NOT NULL
        ORDER BY 1 LIMIT 2000""", (winner, as_of, as_of)).fetchall()]


def run(conn, log=print) -> dict:
    t0 = time.perf_counter()
    queries, qrels, meta = E.load_benchmark(repo_root(), {"dev"})
    cache = E.prepare_all(conn, queries, P2_003_RANKING, log)
    failures, successes = [], []
    for q in queries:
        qid = q["query_id"]
        ql, ret, idf, pool_all, _ms = cache[qid]
        lots = score_lots(ql, ret, idf, P2_003_RANKING)
        recs, _ = rank_suppliers(ql, Pool(lots=lots, relations=pool_all.relations, same_customer=pool_all.same_customer), P2_003_RANKING)
        cands = {r.supplier_id for r in recs}
        winners = sorted(s for s, g in qrels[qid].items() if g == 2)
        (failures if not (set(winners) & cands) else successes).append((qid, ql, winners))
    successes = sorted(successes, key=lambda x: x[0])[:: max(1, len(successes) // SUCCESS_SAMPLE)][:SUCCESS_SAMPLE]
    log(f"retrieval failures: {len(failures)}, success sample: {len(successes)}")

    corpus, n_full = _corpus(conn)
    t = time.perf_counter()
    cvec = semantic.encode(corpus, "document")
    corpus_s = time.perf_counter() - t
    log(f"corpus {len(corpus)} texts embedded in {corpus_s:.0f}s ({len(corpus) / corpus_s:.0f}/s)")
    scale = n_full / len(corpus)

    def analyse(qid, ql, winners, keep_neighbours: bool):
        texts = [qi.product_name for qi in ql.items if qi.product_name]
        if not texts:
            return {"query_id": qid, "status": "no query text"}
        qv = semantic.encode(texts, "query")
        sims = qv @ cvec.T                                   # [items, corpus]
        best_w, best_text, best_item = -1.0, None, None
        for w in winners:
            wt = _winner_texts(conn, w, ql.as_of)
            if not wt:
                continue
            ws = qv @ semantic.encode(wt, "document").T
            i, j = np.unravel_index(int(np.argmax(ws)), ws.shape)
            if ws[i, j] > best_w:
                best_w, best_text, best_item = float(ws[i, j]), wt[j], i
        out = {"query_id": qid, "difficulty": meta[qid]["difficulty"], "query_items": texts[:3]}
        if best_text is None:
            out.update({"status": "winner has no visible historical item text (unseen / no history)"})
        else:
            rank_sample = int((sims[best_item] > best_w).sum())
            est = int(round(rank_sample * scale)) + 1
            out.update({"status": "plausibly recoverable" if est <= RECOVERY_TOP_K else "not recoverable at cap",
                        "winner_best_similarity": round(best_w, 4), "winner_best_text": best_text[:160],
                        "matched_query_item": texts[best_item][:160], "estimated_full_corpus_rank": est})
        if keep_neighbours:
            top = np.argsort(-sims[0])[:5]
            out["top5_neighbours_item1"] = [[corpus[k][:120], round(float(sims[0][k]), 4)] for k in top]
        return out

    fail_rows = [analyse(qid, ql, w, True) for qid, ql, w in failures]
    succ_rows = [analyse(qid, ql, w, False) for qid, ql, w in successes]
    # technical identifiers: does semantic search reproduce exact-token matches?
    tech = []
    for qid, ql, _w in successes + failures:
        for qi in ql.items:
            for tok in qi.tech_tokens[:1]:
                qv = semantic.encode([qi.product_name], "query")
                top = np.argsort(-(qv @ cvec.T)[0])[:10]
                exact_in_corpus = sum(1 for c in corpus if tok in c)
                tech.append({"token": tok, "semantic_top10_with_token": sum(1 for k in top if tok in corpus[k]),
                             "corpus_texts_with_token": exact_in_corpus})
    rec = sum(1 for r in fail_rows if r["status"] == "plausibly recoverable")
    by_diff = {}
    for r in fail_rows:
        d = r.get("difficulty", "?")
        by_diff.setdefault(d, {"failures": 0, "plausibly_recoverable": 0})
        by_diff[d]["failures"] += 1
        by_diff[d]["plausibly_recoverable"] += r["status"] == "plausibly recoverable"
    tech_ok = [t for t in tech if t["corpus_texts_with_token"] > 0]
    return {
        "model": semantic.lock(), "corpus": {"visible_before": CORPUS_BEFORE.isoformat(), "sample_size": len(corpus),
                                            "full_visible_distinct_texts_estimate": n_full, "seed": SAMPLE_SEED,
                                            "embedding_seconds": round(corpus_s, 1), "texts_per_second": round(len(corpus) / corpus_s, 1)},
        "gate": {"rule": f"GO if plausibly recoverable retrieval failures >= {GATE_MIN_RECOVERABLE} (estimated full-corpus rank <= "
                         f"{RECOVERY_TOP_K} texts)", "plausibly_recoverable": rec, "retrieval_failures": len(fail_rows),
                 "decision": "GO" if rec >= GATE_MIN_RECOVERABLE else "STOP"},
        "failures_by_difficulty": by_diff,
        "success_sample_plausibly_recoverable": sum(1 for r in succ_rows if r["status"] == "plausibly recoverable"),
        "success_sample_size": len(succ_rows),
        "technical_tokens": {"queries_checked": len(tech_ok),
                             "mean_semantic_top10_containing_exact_token": round(float(np.mean([t["semantic_top10_with_token"] for t in tech_ok])), 2)
                             if tech_ok else None, "examples": tech_ok[:10]},
        "failures": fail_rows, "success_sample": succ_rows, "runtime_seconds": round(time.perf_counter() - t0, 1),
    }
