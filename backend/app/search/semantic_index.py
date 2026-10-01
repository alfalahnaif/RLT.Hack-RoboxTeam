"""Semantic index build/status (P2-001). Resumable, batched, multi-process, deterministic.

1. register distinct normalized product texts (INSERT ... ON CONFLICT DO NOTHING) with first_seen_publish_date = min(item date);
2. embed rows whose embedding IS NULL, in text_hash order, in chunks; each chunk is committed (resumable after interruption);
   texts are encoded by N single-thread worker processes (CPU threading scales poorly for this model; processes scale ~linearly);
3. build the HNSW cosine index once all rows are embedded (if missing).
Recomputation never happens on container start: only rows without an embedding are processed.
"""
from __future__ import annotations

import os
import time
from multiprocessing import get_context

import numpy as np

from app.search import semantic

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


def register_texts(conn) -> int:
    cur = conn.execute("""INSERT INTO semantic_text (text_hash, normalized_text, first_seen_publish_date)
        SELECT md5(product_name_normalized), min(product_name_normalized), min(publish_date)
        FROM procurement_item WHERE product_name_normalized IS NOT NULL
        GROUP BY md5(product_name_normalized)
        ON CONFLICT (text_hash) DO NOTHING""")
    conn.commit()
    return cur.rowcount


def build(conn, log=print, workers: int = WORKERS) -> dict:
    from pgvector.psycopg import register_vector
    register_vector(conn)
    t0 = time.perf_counter()
    rev = semantic.lock()["revision"]
    added = register_texts(conn)
    log(f"registered {added} new texts")
    todo = conn.execute("SELECT count(*) FROM semantic_text WHERE embedding IS NULL").fetchone()[0]
    done, t_emb = 0, time.perf_counter()
    if todo:
        conn.execute("DROP INDEX IF EXISTS ix_semantic_text_hnsw")   # bulk updates first, HNSW built once at the end
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
    conn.execute("SET maintenance_work_mem = '2GB'")
    conn.execute(SEMANTIC_HNSW_DDL)
    conn.commit()
    idx_s = time.perf_counter() - t_idx
    return {**status(conn), "embedded_this_run": done, "embedding_seconds": round(emb_s, 1),
            "hnsw_build_seconds": round(idx_s, 1), "total_seconds": round(time.perf_counter() - t0, 1), "workers": workers}


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
            "hnsw_index_present": conn.execute("SELECT to_regclass('ix_semantic_text_hnsw') IS NOT NULL").fetchone()[0]}
