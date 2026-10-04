"""Typed response contract for historical supplier recommendations and the integrated procurement analysis (P4-001).

The models describe what app.search.recommend.recommend() already returns; they add no ranking logic.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.market_models import MarketIntelligenceResponse


class SemanticEvidenceResponse(BaseModel):
    lot_id: str
    publish_date: date
    product: str | None = Field(description="Historical product text retrieved by the semantic branch.")
    okpd2: str | None
    cosine: float = Field(description="Raw cosine similarity between the query item and the historical text.")
    discovered_only_by_semantic: bool = Field(description="The lot was found only by the semantic branch (not text / technical / OKPD2).")
    semantic_score_won: bool = Field(description="The calibrated semantic similarity was also the winning text-similarity component.")


class RankedSupplierResponse(BaseModel):
    rank: int
    supplier_id: str
    supplier_inn: str
    score: float
    components: dict[str, float] = Field(description="Match components in [0, 1] (Match only; not Confidence or Risk).")
    contributions: dict[str, float] = Field(description="Weighted contribution of each component to the score.")
    relevant_lots: int
    relevant_awards: int
    relevant_em_participations: int
    relevant_ais_awards: int
    best_products: list[str]
    best_okpd2: str | None
    most_recent_relevant: date
    same_customer_history: bool
    evidence_lot_ids: list[str]
    reasons: list[str] = Field(description="Deterministic template explanations generated from the evidence only.")
    diagnostics: dict[str, Any]
    semantic_evidence: list[SemanticEvidenceResponse] = Field(description="Semantic retrieval provenance (empty when not semantic).")


class QueryItemResponse(BaseModel):
    product_name: str | None
    okpd2: str | None
    technical_tokens: list[str]


class QuerySummaryResponse(BaseModel):
    subject: str | None
    items_used: int
    items_total: int
    items: list[QueryItemResponse]
    customer_known: bool


class RetrievalSummaryResponse(BaseModel):
    branch_rows: dict[str, int]
    branch_ms: dict[str, float]
    historical_items: int
    historical_lots: int


class RecommendationResponse(BaseModel):
    lot_id: str
    as_of: date = Field(description="Exclusive history cutoff: the procurement's own publish_date.")
    recommendation_version: str
    config_name: str
    config: dict[str, Any]
    semantic_enabled: bool = Field(description="True when the semantic branch actually ran for this request.")
    warnings: list[str] = Field(description="Degraded branches, e.g. SEMANTIC_UNAVAILABLE (results then equal P2-003).")
    candidate_count: int
    query: QuerySummaryResponse
    retrieval: RetrievalSummaryResponse
    results: list[RankedSupplierResponse]
    timings_ms: dict[str, float]


class ProcurementItemResponse(BaseModel):
    line_no: int
    product_name: str
    okpd2_code: str | None = Field(description="Normalized OKPD2; null when the source code is missing or invalid.")
    okpd2_code_raw: str
    okpd2_status: str | None = Field(None, description="Pre-defense files only: SUPPLIED_ALIGNED | RESOLVED_FROM_TEXT | "
                                                       "SUPPLIED_UNVERIFIED | UNRESOLVED (supplied code vs product text).")
    okpd2_evidence: str | None = None


class ProcurementResponse(BaseModel):
    lot_id: str
    subject: str | None
    publish_date: date
    platform: Literal["AIS_GZ", "EM"]
    start_price: float | None
    customer_inn: str | None
    items_total: int
    items: list[ProcurementItemResponse]
    source: Literal["HISTORICAL_DB", "PREDEFENSE_FILE"] = Field(
        "HISTORICAL_DB", description="PREDEFENSE_FILE = item-level data from the organizer procurement file (query input only).")


class SectionError(BaseModel):
    code: str
    message: str


class RecommendationSection(BaseModel):
    status: Literal["OK", "UNAVAILABLE"]
    data: RecommendationResponse | None
    error: SectionError | None


class MarketIntelligenceEntry(BaseModel):
    okpd2: str
    item_lines: list[int] = Field(description="Procurement line numbers carrying this exact OKPD2.")
    status: Literal["OK", "UNAVAILABLE"]
    data: MarketIntelligenceResponse | None
    error: SectionError | None


class AnalysisResponse(BaseModel):
    procurement: ProcurementResponse
    recommendations: RecommendationSection
    market_intelligence: list[MarketIntelligenceEntry] = Field(
        description="One entry per distinct exact OKPD2 observed on the procurement items, ordered by code.")
    market_intelligence_as_of: date = Field(description="History cutoff used for market intelligence (= the procurement's publish_date).")
    items_without_okpd2: list[int] = Field(description="Line numbers with no usable OKPD2; no market intelligence is invented for them.")
    availability: Literal["COMPLETE", "PARTIAL"]
    timings_ms: dict[str, float]
