"""Semantic index build/status (P2-001). Resumable, batched, multi-process, deterministic.

0. fail closed if stored embeddings come from a model revision other than the pinned lock (explicit `--reembed` clears them all);
1. register distinct normalized product texts with first_seen_publish_date = min(item date); an existing text's first_seen only
   moves EARLIER (LEAST) when older items are ingested later — its embedding is kept (the text did not change);
2. embed rows whose embedding IS NULL, in text_hash order, in chunks; each chunk is committed (resumable after interruption);
   the HNSW index is dropped first, so an interrupted build is never READY;
3. validate invariants (every text embedded, single pinned revision), build the HNSW cosine index if missing/invalid, and stamp it
   READY with a JSON comment on the index (model, revision, texts) in the same transaction. The readiness state lives on the index
   itself, so dropping the index also removes it. Search checks it with one catalog query (retrieval.semantic_unavailable()).
Recomputation never happens on container start: only rows without an embedding are processed.
"""
from __future__ import annotations

import json
import os
import time
from multiprocessing import get_context

import numpy as np

from app.search import semantic

HNSW_INDEX = "ix_semantic_text_hnsw"
SEMANTIC_HNSW_DDL = ("CREATE INDEX IF NOT EXISTS ix_semantic_text_hnsw ON semantic_text "
                     "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")
CHUNK = 4000
# Measured on the team machine (8 vCPU, Docker Desktop): 1 process x 8 threads ~95-99 texts/s; 6 processes x 1 thread 57/s;
# ONNX fp32 83/s; ONNX int8 82/s with only 0.83 top-10 neighbour overlap -> one in-process torch encoder is used (WORKERS = 1).
WORKERS = 1


def _init_worker():
    import torch
    torch.set_num_threads(1)
    semantic.encoder()


def _encode(texts: list[str]) -> np.ndarray:
    return semantic.encode(texts, "document")


class RevisionMismatch(RuntimeError):
    pass


def register_texts(conn) -> dict:
    """Insert new distinct texts; move an existing text's first_seen EARLIER only (never later); embeddings are untouched."""
    rows = conn.execute("""INSERT INTO semantic_text AS s (text_hash, normalized_text, first_seen_publish_date)
        SELECT md5(product_name_normalized), min(product_name_normalized), min(publish_date)
        FROM procurement_item WHERE product_name_normalized IS NOT NULL
        GROUP BY md5(product_name_normalized)
        ON CONFLICT (text_hash) DO UPDATE
          SET first_seen_publish_date = LEAST(s.first_seen_publish_date, EXCLUDED.first_seen_publish_date)
          WHERE EXCLUDED.first_seen_publish_date < s.first_seen_publish_date
        RETURNING (xmax = 0)""").fetchall()
    conn.commit()
    inserted = sum(1 for (new,) in rows if new)
    return {"inserted": inserted, "first_seen_moved_earlier": len(rows) - inserted}


def check_revision(conn, rev: str) -> None:
    """Fail closed when stored embeddings were produced by a different model revision than the pinned lock."""
    other = conn.execute("""SELECT array_agg(DISTINCT coalesce(model_revision, '<null>')) FROM semantic_text
                            WHERE embedding IS NOT NULL AND model_revision IS DISTINCT FROM %s""", (rev,)).fetchone()[0]
    if other:
        raise RevisionMismatch(f"semantic_text holds embeddings from model revision(s) {sorted(other)} but the pinned lock is {rev}; "
                               "refusing to mix revisions. Run `python -m app.cli semantic build --reembed` to re-embed every text with "
                               "the pinned model (hours on CPU), or restore the matching backend/semantic_model.lock.json.")


def build(conn, log=print, workers: int = WORKERS, reembed: bool = False) -> dict:
    from pgvector.psycopg import register_vector
    register_vector(conn)
    t0 = time.perf_counter()
    lk = semantic.lock()
    rev = lk["revision"]
    if reembed:
        conn.execute(f"DROP INDEX IF EXISTS {HNSW_INDEX}")
        n = conn.execute("UPDATE semantic_text SET embedding = NULL, model_revision = NULL WHERE embedding IS NOT NULL").rowcount
        conn.commit()
        log(f"--reembed: cleared {n} embeddings")
    check_revision(conn, rev)
    reg = register_texts(conn)
    log(f"registered {reg['inserted']} new texts; first_seen moved earlier for {reg['first_seen_moved_earlier']}")
    todo = conn.execute("SELECT count(*) FROM semantic_text WHERE embedding IS NULL").fetchone()[0]
    done, t_emb = 0, time.perf_counter()
    if todo:
        conn.execute(f"DROP INDEX IF EXISTS {HNSW_INDEX}")   # never READY while embedding; HNSW built once at the end
        conn.commit()
        pool = get_context("spawn").Pool(workers, initializer=_init_worker) if workers > 1 else None
        try:
            last = ""
            while True:
                rows = conn.execute("""SELECT text_hash, normalized_text FROM semantic_text WHERE embedding IS NULL AND text_hash > %s
                                       ORDER BY text_hash LIMIT %s""", (last, CHUNK)).fetchall()
                if not rows:
                    break
                texts = [r[1] for r in rows]
                if pool is None:
                    out = _encode(texts)
                else:
                    parts = [texts[i::workers] for i in range(workers)]      # deterministic split
                    vecs = pool.map(_encode, parts)
                    out = np.zeros((len(texts), semantic.DIM), dtype=np.float32)
                    for i, v in enumerate(vecs):
                        out[i::workers] = v
                with conn.cursor() as cur:
                    cur.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_emb (text_hash text, embedding vector(384)) ON COMMIT DELETE ROWS")
                    with cur.copy("COPY tmp_emb (text_hash, embedding) FROM STDIN WITH (FORMAT BINARY)") as cp:
                        cp.set_types(["text", "vector"])
                        for (h, _t), v in zip(rows, out):
                            cp.write_row((h, v))
                    cur.execute("""UPDATE semantic_text s SET embedding = t.embedding, model_revision = %s
                                   FROM tmp_emb t WHERE t.text_hash = s.text_hash""", (rev,))
                conn.commit()
                done += len(rows)
                last = rows[-1][0]
                rate = done / (time.perf_counter() - t_emb)
                log(f"embedded {done}/{todo} ({rate:.0f}/s, eta {(todo - done) / rate / 60:.0f} min)")
        finally:
            if pool is not None:
                pool.close()
    emb_s = time.perf_counter() - t_emb
    t_idx = time.perf_counter()
    texts = mark_ready(conn, lk)
    idx_s = time.perf_counter() - t_idx
    log(f"HNSW index READY ({texts} texts, revision {rev})")
    return {**status(conn), "registered": reg, "embedded_this_run": done, "embedding_seconds": round(emb_s, 1),
            "hnsw_build_seconds": round(idx_s, 1), "total_seconds": round(time.perf_counter() - t0, 1), "workers": workers}


def mark_ready(conn, lk: dict) -> int:
    """Validate build invariants, (re)build the HNSW index if missing/invalid, and stamp the READY state — one transaction."""
    rev = lk["revision"]
    n, missing, wrong = conn.execute("""SELECT count(*), count(*) FILTER (WHERE embedding IS NULL),
        count(*) FILTER (WHERE embedding IS NOT NULL AND model_revision IS DISTINCT FROM %s) FROM semantic_text""", (rev,)).fetchone()
    if missing or wrong or n == 0:
        conn.rollback()
        raise RuntimeError(f"semantic index invariants violated (texts {n}, unembedded {missing}, other revision {wrong}); not READY")
    valid = conn.execute("SELECT indisvalid AND indisready FROM pg_index WHERE indexrelid = to_regclass(%s)", (HNSW_INDEX,)).fetchone()
    if valid is not None and not valid[0]:
        conn.execute(f"DROP INDEX {HNSW_INDEX}")
    conn.execute("SET LOCAL maintenance_work_mem = '2GB'")
    conn.execute(SEMANTIC_HNSW_DDL)
    state = {"state": "READY", "model": lk["model"], "revision": rev, "dimension": lk["dimension"], "texts": n}
    conn.execute(f"COMMENT ON INDEX {HNSW_INDEX} IS " + "'" + json.dumps(state, sort_keys=True).replace("'", "''") + "'")
    conn.commit()
    return n


def index_state(conn) -> dict | None:
    """READY stamp of the HNSW index; None if the index is missing, invalid, not HNSW or unstamped. One catalog query."""
    row = conn.execute("""SELECT x.indisvalid AND x.indisready, a.amname, obj_description(c.oid, 'pg_class')
        FROM pg_class c JOIN pg_index x ON x.indexrelid = c.oid JOIN pg_am a ON a.oid = c.relam
        WHERE c.oid = to_regclass(%s)""", (HNSW_INDEX,)).fetchone()
    if row is None or not row[0] or row[1] != "hnsw" or not row[2]:
        return None
    try:
        return json.loads(row[2])
    except ValueError:
        return None


def status(conn) -> dict:
    n, emb, revs = conn.execute("""SELECT count(*), count(embedding), array_agg(DISTINCT model_revision)
                                   FROM semantic_text""").fetchone()
    size = lambda rel: conn.execute("SELECT coalesce(pg_total_relation_size(to_regclass(%s)), 0)", (rel,)).fetchone()[0]  # noqa: E731
    return {"texts": n, "embedded": emb, "model_revisions": [r for r in (revs or []) if r],
            "semantic_text_table_bytes": conn.execute("SELECT pg_relation_size('semantic_text') + coalesce(pg_relation_size(reltoastrelid), 0) "
                                                       "FROM pg_class WHERE relname = 'semantic_text'").fetchone()[0],
            "semantic_text_total_bytes": size("semantic_text"), "hnsw_index_bytes": size("ix_semantic_text_hnsw"),
            "item_md5_index_bytes": size("ix_item_name_md5_date"),
            "database_bytes": conn.execute("SELECT pg_database_size(current_database())").fetchone()[0],
            "hnsw_index_present": conn.execute("SELECT to_regclass('ix_semantic_text_hnsw') IS NOT NULL").fetchone()[0],
            "index_state": index_state(conn), "pinned_revision": semantic.lock()["revision"] if semantic.LOCK.exists() else None}
