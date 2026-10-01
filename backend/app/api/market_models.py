"""Public, explicit response contract for category market intelligence."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    okpd2: str
    as_of: date = Field(description="Exclusive historical publish_date cutoff; defaults to 2026-01-01.")


class PoolHealthResponse(BaseModel):
    status: Literal["INSUFFICIENT_DATA", "LOW", "MODERATE", "HIGH", "VERY_HIGH"] = Field(
        description="Concentration of observed procurement awards, not the entire current market.")
    lot_count: int
    procurement_count: int
    known_customer_count: int = Field(description="Distinct known, non-null customer INNs.")
    observed_supplier_count: int
    winning_supplier_count: int
    recent_winning_supplier_count: int
    award_count: int
    top1_share: float | None
    top3_share: float | None
    hhi: float | None
    alternative_supplier_count: int = Field(description="All observed alternatives excluding the dominant supplier; the response lists the first ten.")


class ConcentrationResponse(BaseModel):
    signal: Literal["EXPANSION_RECOMMENDED", "REVIEW_POOL", "NO_EXPANSION_SIGNAL", "INSUFFICIENT_DATA"]
    reason_codes: list[str]


class HistoricalAlternativeResponse(BaseModel):
    supplier_id: str
    supplier_inn: str | None
    historical_award_count: int
    observed_relation_count: int = Field(description="Observed supplier relations in this category, not a complete bidder count.")
    is_winner_in_category: bool


class EvidenceSummaryResponse(BaseModel):
    evidence_type: str
    source_name: str
    source_url: str | None
    source_record_id: str | None
    source_authority: str
    evidence_status: Literal["ACTIVE", "SUSPENDED", "TERMINATED", "UNKNOWN"]
    verification_strength: Literal["NONE", "WEAK", "MODERATE", "STRONG"]
    target_product_support: Literal["DIRECT", "RELATED", "NONE"]
    product_scope: list[str]
    evidence_date: date | None
    valid_until: date | None
    retrieved_at: datetime
    role_assertion: str


class ExternalCandidateResponse(BaseModel):
    supplier_inn: str
    company_name: str
    aliases: list[str]
    reconciliation_status: Literal["CATEGORY_HISTORICAL", "HISTORICAL_OTHER_CATEGORY", "EXTERNAL_NEW", "INVALID_INN"] = Field(
        description="Historical procurement reconciliation; EXTERNAL_NEW never implies VERIFIED.")
    market_role: str
    verification_status: Literal["UNVERIFIED", "UNDER_REVIEW", "VERIFIED"] = Field(
        description="Curated evidence decision. VERIFIED has current support; UNDER_REVIEW retains unresolved reasons.")
    verification_strength: Literal["NONE", "WEAK", "MODERATE", "STRONG"]
    target_product_match: str
    exact_okpd2_asserted_by_source: bool = Field(
        description="Direct product relevance does not prove that a source asserted this exact OKPD2 value.")
    why_candidate: str
    verification_reason_codes: list[str]
    review_reasons: list[str]
    evidence_count: int
    active_evidence_count: int
    evidence_summary: list[EvidenceSummaryResponse]


class ExternalExpansionResponse(BaseModel):
    available: bool = Field(description="False means no curated evidence is available in this catalog, not that no external suppliers exist.")
    evidence_checked_at: datetime | None
    verified_count: int
    under_review_count: int
    candidates: list[ExternalCandidateResponse]


class ProvenanceResponse(BaseModel):
    historical_source: Literal["canonical procurement database"]
    external_source: Literal["curated evidence seed", "none in current catalog"]
    history_cutoff_rule: Literal["publish_date < as_of"]
    verification_method: Literal["CURATED_EVIDENCE_POLICY", "NOT_AVAILABLE"]


class MarketIntelligenceResponse(BaseModel):
    category: CategoryResponse
    pool_health: PoolHealthResponse = Field(description="Historical supplier-pool measurements from observed procurement records.")
    concentration: ConcentrationResponse = Field(description="Deterministic product signal based on the historical pool label.")
    historical_alternatives: list[HistoricalAlternativeResponse] = Field(description="Observed historical suppliers other than the leading award winner; at most ten.")
    external_expansion: ExternalExpansionResponse = Field(description="Curated external evidence, evaluated separately from historical procurement status.")
    provenance: ProvenanceResponse
