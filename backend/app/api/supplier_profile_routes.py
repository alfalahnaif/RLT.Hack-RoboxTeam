"""P5-001A Supplier 360 routes. GET is read-only (stored profile, never live sources); POST runs bounded on-demand enrichment."""
from __future__ import annotations

import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.api import supplier_profile as SP
from app.api.supplier_profile_models import SupplierProfileResponse
from app.enrichment.catalog import EvidenceCatalogError
from app.enrichment.contacts import ContactEnrichmentError
from app.shared.config import database_url

router = APIRouter(prefix="/api/v1", tags=["supplier-360"])


def connect():
    return psycopg.connect(database_url())


def _guard(fn):
    try:
        with connect() as conn:
            return fn(conn)
    except SP.InvalidInn as e:
        raise HTTPException(422, detail={"code": "INVALID_INN", "message": str(e)}) from e
    except SP.SupplierNotFound as e:
        raise HTTPException(404, detail={"code": "SUPPLIER_NOT_FOUND", "message": str(e)}) from e
    except (EvidenceCatalogError, ContactEnrichmentError) as e:
        raise HTTPException(503, detail={"code": "CURATED_DATA_UNAVAILABLE", "message": str(e)}) from e
    except (psycopg.Error, RuntimeError) as e:
        raise HTTPException(503, detail={"code": "DATA_UNAVAILABLE", "message": str(e)}) from e


@router.get("/suppliers/{inn}/profile", response_model=SupplierProfileResponse,
            summary="Supplier 360 profile (stored enrichment + procurement history summary)",
            description="Read-only: returns the stored enrichment snapshot for the INN (status NOT_ENRICHED when none), the accepted "
                        "curated contacts/roles when they exist, and the organizer procurement history summary. Never queries "
                        "external sources.")
def get_profile(inn: str) -> SupplierProfileResponse:
    return _guard(lambda conn: SP.build_profile(conn, inn, SP.utcnow()))


@router.post("/suppliers/{inn}/enrich", response_model=SupplierProfileResponse,
             summary="Enrich one supplier by INN (cache-first; refresh=true forces re-query)",
             description="Identity-first pipeline: FNS EGRUL -> registry mirror -> candidate website verified by INN/OGRN on the site "
                         "-> first-party contacts -> role evidence -> freshness. Synchronous with per-request timeouts. A fresh "
                         "stored profile is returned without re-querying sources unless refresh=true.")
def enrich(inn: str, refresh: bool = Query(False)) -> SupplierProfileResponse:
    return _guard(lambda conn: SP.enrich_supplier(conn, inn, refresh=refresh))
