"""FastAPI application using the project's documented /api/v1 route prefix."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.market_intelligence import router as market_intelligence_router
from app.api.product import router as product_router
from app.api.readiness import warm_semantic_model
from app.api.supplier_search_routes import router as supplier_search_router

# Local frontend origins only (Next.js dev server); never "*". Override with a comma-separated CORS_ORIGINS.
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.semantic_model_loaded = warm_semantic_model() if os.environ.get("SEMANTIC_WARMUP", "1") == "1" else False
    yield


app = FastAPI(title="Supplier Radar API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
                                                  if o.strip() and o.strip() != "*"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(market_intelligence_router)
app.include_router(product_router)
app.include_router(supplier_search_router)
