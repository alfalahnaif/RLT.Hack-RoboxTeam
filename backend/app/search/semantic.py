"""Local sentence-embedding encoder for P2-001 (CPU, offline at recommendation time).

Model: intfloat/multilingual-e5-small (MIT) — 384-d, e5 prefixes "query: " / "passage: ", L2-normalized (cosine = dot product).
The exact Hugging Face revision is pinned in backend/semantic_model.lock.json by `python -m app.cli semantic download-model`;
afterwards the model is loaded offline from HF_HOME (the `models` Docker volume). No external API is ever called at query time.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

MODEL_ID = "intfloat/multilingual-e5-small"
LOCK = Path(__file__).resolve().parents[2] / "semantic_model.lock.json"
DIM = 384
BATCH = 64
MAX_SEQ_LEN = 128   # feasibility: 512 vs 128 tokens -> mean cosine 1.000, min 0.936 (only >400-char texts change)

_encoder = None


def download_model(update_lock: bool = False) -> dict:
    """Normal setup: download EXACTLY lock["model"] @ lock["revision"]; the committed lock is never rewritten.
    update_lock=True is the explicit maintenance action: resolve the current Hugging Face revision and rewrite the lock
    (stored embeddings then no longer match -> `semantic build --reembed`)."""
    from huggingface_hub import HfApi, snapshot_download
    if not update_lock:
        lk = lock()
        path = snapshot_download(lk["model"], revision=lk["revision"])
        return {**lk, "path": path, "lock_rewritten": False}
    info = HfApi().model_info(MODEL_ID)
    path = snapshot_download(MODEL_ID, revision=info.sha)
    lk = {"model": MODEL_ID, "revision": info.sha, "dimension": DIM, "license": "MIT (intfloat/multilingual-e5-small)",
          "prefixes": {"query": "query: ", "document": "passage: "}, "normalized": True, "source": "huggingface.co"}
    LOCK.write_text(json.dumps(lk, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {**lk, "path": path, "lock_rewritten": True}


def lock() -> dict:
    if not LOCK.exists():
        raise RuntimeError("semantic model lock missing — restore backend/semantic_model.lock.json from the repository "
                           "(maintenance only: `python -m app.cli semantic download-model --update-lock`)")
    return json.loads(LOCK.read_text(encoding="utf-8"))


def encoder():
    """Lazily load the pinned model offline (once per process)."""
    global _encoder
    if _encoder is None:
        os.environ["HF_HUB_OFFLINE"] = "1"
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(os.cpu_count() or 1)
        _encoder = SentenceTransformer(lock()["model"], revision=lock()["revision"], device="cpu")
        _encoder.max_seq_length = MAX_SEQ_LEN   # same truncation for queries and documents
    return _encoder


def encode(texts: list[str], kind: str) -> np.ndarray:
    """kind: 'query' | 'document'. Returns float32 [n, 384], L2-normalized. Batches are formed in input order (deterministic)."""
    prefix = lock()["prefixes"][kind]
    if not texts:
        return np.zeros((0, DIM), dtype=np.float32)
    v = encoder().encode([prefix + t for t in texts], batch_size=BATCH, normalize_embeddings=True,
                         convert_to_numpy=True, show_progress_bar=False)
    return v.astype(np.float32)
