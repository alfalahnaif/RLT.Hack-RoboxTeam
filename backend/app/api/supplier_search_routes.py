"""FastAPI routes for free-text supplier discovery and its stateless CRM/ERP/SRM export (P4-005A)."""
from __future__ import annotations

from typing import Literal

import psycopg
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from app.api import supplier_search as S
from app.api.supplier_search_models import SupplierSearchRequest, SupplierSearchResponse
from app.enrichment.catalog import EvidenceCatalogError
from app.search.text_query import InvalidQuery
from app.shared.config import database_url

router = APIRouter(prefix="/api/v1", tags=["supplier-search"])


def _run(req: SupplierSearchRequest) -> SupplierSearchResponse:
    try:
        with psycopg.connect(database_url()) as conn:
            return S.supplier_search(conn, req)
    except InvalidQuery as e:
        raise HTTPException(422, detail={"code": "INVALID_QUERY", "message": str(e)}) from e
    except EvidenceCatalogError as e:
        raise HTTPException(503, detail={"code": "EVIDENCE_CATALOG_UNAVAILABLE", "message": str(e)}) from e
    except (psycopg.Error, RuntimeError) as e:
        raise HTTPException(503, detail={"code": "HISTORICAL_DATA_UNAVAILABLE", "message": str(e)}) from e


@router.post("/supplier-search", response_model=SupplierSearchResponse,
             summary="Free-text supplier discovery (optional OKPD2 / registration region)",
             description="Builds a one-item query from the text and runs the accepted recommendation engine (DEFAULT_CONFIG). "
                         "A supplied OKPD2 is preserved and checked against historical text evidence (ALIGNED / UNCERTAIN / "
                         "MISMATCH) with suggested codes; codes without history fall back to text and semantic retrieval. "
                         "Pool health and curated external expansion are added per analyzed code. No price claims.")
def supplier_search(req: SupplierSearchRequest) -> SupplierSearchResponse:
    return _run(req)


@router.get("/supplier-search/{search_id}/export", summary="Export a supplier search for CRM / ERP / SRM (json or csv)",
            description="Stateless: the search_id encodes the request, so the export re-runs the same deterministic search. "
                        "Rows: ranked historical suppliers and curated external candidates with identity, score, role, "
                        "contact, freshness and an evidence summary.")
def export_search(search_id: str, format: Literal["json", "csv"] = Query("json")):
    try:
        req = S.decode_search_id(search_id)
    except S.InvalidSearchId as e:
        raise HTTPException(422, detail={"code": "INVALID_SEARCH_ID", "message": str(e)}) from e
    res = _run(req)
    name = f"supplier-search-{search_id[:12]}"
    if format == "csv":
        return Response(content=S.export_csv(res), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})
    return JSONResponse(content=S.export_json(res), headers={"Content-Disposition": f'attachment; filename="{name}.json"'})
