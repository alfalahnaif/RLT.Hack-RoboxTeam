"""Health/readiness and semantic warm-up (P4-001). Only catalog lookups and tiny files — never a table scan."""
from __future__ import annotations

import logging
from typing import Literal

import psycopg
from pydantic import BaseModel

from app.enrichment.catalog import CuratedEvidenceCatalog, EvidenceCatalogError
from app.search import semantic, semantic_index
from app.search.retrieval import semantic_unavailable
from app.shared.config import database_url

log = logging.getLogger("supplier_radar.api")


class SemanticHealth(BaseModel):
    status: Literal["ready", "unavailable"]
    reason: str | None
    pinned_revision: str | None
    hnsw_ready: bool
    index_revision: str | None
    index_texts: int | None
    model_loaded: bool


class CatalogHealth(BaseModel):
    status: Literal["ready", "unavailable"]
    seed_files: int
    reason: str | None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    api: Literal["ready"]
    postgres: Literal["reachable", "unreachable"]
    semantic: SemanticHealth
    curated_evidence_catalog: CatalogHealth


def _catalog() -> CatalogHealth:
    cat = CuratedEvidenceCatalog()
    try:
        cat.get("__readiness_probe__")                     # loads + validates every seed file (small JSON)
        return CatalogHealth(status="ready", seed_files=len(list(cat.directory.glob("*_evidence_seed.json"))), reason=None)
    except EvidenceCatalogError as e:
        return CatalogHealth(status="unavailable", seed_files=0, reason=str(e))


def semantic_ready(conn) -> tuple[str | None, dict | None]:
    reason = semantic_unavailable(conn)
    state = semantic_index.index_state(conn)
    conn.rollback()
    return reason, state


def health(model_loaded: bool) -> HealthResponse:
    pinned = semantic.lock()["revision"] if semantic.LOCK.exists() else None
    try:
        with psycopg.connect(database_url(), connect_timeout=3) as conn:
            conn.execute("SELECT 1")
            reason, state = semantic_ready(conn)
        pg = "reachable"
    except (psycopg.Error, RuntimeError) as e:
        pg, reason, state = "unreachable", f"postgres unreachable: {e.__class__.__name__}", None
    sem = SemanticHealth(status="ready" if reason is None else "unavailable", reason=reason, pinned_revision=pinned,
                         hnsw_ready=bool(state and state.get("state") == "READY"), index_revision=(state or {}).get("revision"),
                         index_texts=(state or {}).get("texts"), model_loaded=model_loaded)
    cat = _catalog()
    status = "unavailable" if pg == "unreachable" else "ok" if sem.status == "ready" and cat.status == "ready" else "degraded"
    return HealthResponse(status=status, api="ready", postgres=pg, semantic=sem, curated_evidence_catalog=cat)


def warm_semantic_model() -> bool:
    """Load the pinned encoder once at startup when the semantic index is READY (no fake recommendation). Never raises."""
    try:
        with psycopg.connect(database_url(), connect_timeout=3) as conn:
            reason, _state = semantic_ready(conn)
        if reason is not None:
            log.warning("semantic unavailable at startup (%s); recommendations use the P2-003 fallback", reason)
            return False
        semantic.encoder()
        log.info("semantic model %s@%s loaded", semantic.lock()["model"], semantic.lock()["revision"])
        return True
    except Exception as e:                                  # startup must succeed without semantic
        log.warning("semantic warm-up skipped: %s", e)
        return False
