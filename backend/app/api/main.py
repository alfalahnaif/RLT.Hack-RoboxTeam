"""FastAPI application using the project's documented /api/v1 route prefix."""
from fastapi import FastAPI

from app.api.market_intelligence import router as market_intelligence_router


app = FastAPI(title="Supplier Radar API", version="0.1.0")
app.include_router(market_intelligence_router)
