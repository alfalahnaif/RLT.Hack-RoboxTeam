"""FastAPI route for category market intelligence."""
from __future__ import annotations

from datetime import date

import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.api.market_models import MarketIntelligenceResponse
from app.api.market_service import (DEFAULT_AS_OF, DEFAULT_RECENT_DAYS, InvalidCategory,
                                    UnknownCategory, build_market_intelligence)
from app.enrichment.catalog import CuratedEvidenceCatalog, EvidenceCatalogError
from app.shared.config import database_url


router = APIRouter(prefix="/api/v1", tags=["market-intelligence"])


@router.get(
    "/market-intelligence/{okpd2}", response_model=MarketIntelligenceResponse,
    summary="Historical pool health and curated external supplier evidence",
    description=("Analyzes observed procurement history before as_of, then independently reconciles "
                 "and verifies any curated external candidates. A category without curated evidence "
                 "still returns its historical analysis. Concentration is a historical procurement signal."),
)
def market_intelligence(
    okpd2: str,
    as_of: date = Query(DEFAULT_AS_OF, description="Exclusive historical cutoff; never inferred from today's date."),
    recent_days: int = Query(DEFAULT_RECENT_DAYS, ge=1, le=36500,
                             description="Lookback window for recent winning suppliers."),
) -> MarketIntelligenceResponse:
    try:
        with psycopg.connect(database_url()) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            return build_market_intelligence(conn, CuratedEvidenceCatalog(), okpd2, as_of, recent_days)
    except InvalidCategory as error:
        raise HTTPException(422, detail={"code": "INVALID_OKPD2", "message": str(error)}) from error
    except UnknownCategory as error:
        raise HTTPException(404, detail={"code": "CATEGORY_NOT_OBSERVED", "message": str(error)}) from error
    except EvidenceCatalogError as error:
        raise HTTPException(503, detail={"code": "EVIDENCE_CATALOG_UNAVAILABLE", "message": str(error)}) from error
    except (ValueError, OverflowError) as error:
        raise HTTPException(422, detail={"code": "INVALID_ANALYSIS_PARAMETERS", "message": str(error)}) from error
    except (psycopg.Error, RuntimeError) as error:
        raise HTTPException(503, detail={"code": "HISTORICAL_DATA_UNAVAILABLE", "message": str(error)}) from error
