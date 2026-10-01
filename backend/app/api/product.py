"""FastAPI routes for recommendations, the integrated procurement analysis and health/readiness (P4-001)."""
from __future__ import annotations

import psycopg
from fastapi import APIRouter, HTTPException, Request

from app.api import product_service as S
from app.api.recommendation_models import AnalysisResponse, RecommendationResponse
from app.api.readiness import HealthResponse, health
from app.shared.config import database_url

router = APIRouter(prefix="/api/v1", tags=["supplier-radar"])


@router.get("/recommendations/{lot_id}", response_model=RecommendationResponse,
            summary="Ranked, explainable historical suppliers for a procurement lot",
            description="Calls the accepted recommendation engine with DEFAULT_CONFIG (P2-001 S3: lexical + OKPD2 + semantic retrieval, "
                        "P2-003 ranking). History strictly before the lot's publish_date. If the semantic index is not READY the "
                        "response equals P2-003 and carries a SEMANTIC_UNAVAILABLE warning.")
def recommendations(lot_id: str) -> RecommendationResponse:
    try:
        with psycopg.connect(database_url()) as conn:
            return S.recommendation(conn, lot_id)
    except S.LotNotFound as e:
        raise HTTPException(404, detail={"code": "LOT_NOT_FOUND", "message": str(e)}) from e
    except (psycopg.Error, RuntimeError) as e:
        raise HTTPException(503, detail={"code": "HISTORICAL_DATA_UNAVAILABLE", "message": str(e)}) from e


@router.get("/procurements/{lot_id}/analysis", response_model=AnalysisResponse,
            summary="Integrated Supplier Radar analysis of one procurement",
            description="Procurement facts + recommendations + market intelligence for each distinct exact OKPD2 on the items "
                        "(history before the lot's publish_date). Each section reports its own availability; one failing "
                        "category does not remove the others.")
def procurement_analysis(lot_id: str) -> AnalysisResponse:
    try:
        with psycopg.connect(database_url()) as conn:
            return S.analysis(conn, lot_id)
    except S.LotNotFound as e:
        raise HTTPException(404, detail={"code": "LOT_NOT_FOUND", "message": str(e)}) from e
    except psycopg.Error as e:
        raise HTTPException(503, detail={"code": "HISTORICAL_DATA_UNAVAILABLE", "message": str(e)}) from e


@router.get("/health", response_model=HealthResponse, summary="Cheap liveness/readiness (catalog lookups only, no table scans)")
def health_route(request: Request) -> HealthResponse:
    return health(getattr(request.app.state, "semantic_model_loaded", False))
