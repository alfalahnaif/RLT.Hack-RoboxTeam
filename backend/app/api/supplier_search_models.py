"""P4-005A free-text supplier discovery contract (`POST /api/v1/supplier-search`)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.market_models import (ConcentrationResponse, ExternalCandidateResponse, HistoricalAlternativeResponse,
                                   PoolHealthResponse)
from app.api.recommendation_models import SemanticEvidenceResponse, SectionError


class SupplierSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000, description="Free-text product / service description.")
    okpd2: str | None = Field(None, description="Optional OKPD2; preserved as supplied, never replaced by a suggestion.")
    region: str | None = Field(None, pattern=r"^\d{2}$",
                               description="Optional 2-digit registration region (from the supplier INN); not delivery capability.")
    limit: int = Field(20, ge=1, le=100)


class QueryEcho(BaseModel):
    text: str
    normalized_text: str
    technical_tokens: list[str]
    okpd2: str | None
    region: str | None
    limit: int
    as_of: date = Field(description="Exclusive history cutoff: the day after the latest procurement in the dataset.")


class SuggestedOkpd2(BaseModel):
    okpd2: str
    share: float = Field(description="Share of text-matching historical evidence; 0 when suggestion comes only from category terminology.")
    supporting_items: int
    supporting_lots: int
    example_products: list[str]
    confidence: float = Field(description="Evidence strength in [0,1], not a calibrated probability.")
    basis: Literal["OFFICIAL_EXACT_TITLE", "OFFICIAL_MORPH_TITLE", "OFFICIAL_TERMS", "HISTORICAL_DOMINANT",
                   "FUZZY", "SEMANTIC", "UNCERTAIN"]
    evidence: list[str]


class CategoryCandidate(BaseModel):
    code: str
    official_name: str | None
    score: float = Field(description="Category evidence score in [0,1], not a calibrated probability.")
    basis: Literal["OFFICIAL_EXACT_TITLE", "OFFICIAL_MORPH_TITLE", "OFFICIAL_TERMS", "HISTORICAL_DOMINANT",
                   "FUZZY", "SEMANTIC"]


class CodeHistoryResponse(BaseModel):
    okpd2: str
    lots: int
    awards: int
    status: Literal["SUFFICIENT", "SPARSE", "NONE"]


class Classification(BaseModel):
    provided_okpd2: str | None
    category_state: Literal["RESOLVED", "CATEGORY_AMBIGUOUS", "CATEGORY_UNCERTAIN"] = Field(
        description="CATEGORY_AMBIGUOUS: several official categories match with similar strong evidence; "
                    "the user selects one (re-search with okpd2) before suppliers are ranked as exact matches.")
    top_candidates: list[CategoryCandidate] = Field(
        description="Official OKPD2 candidates from the category resolver, best first (alternatives for confirmation).")
    suggested_okpd2: list[SuggestedOkpd2]
    history_status: Literal["SUFFICIENT", "SPARSE", "NONE"] = Field(
        description="Procurement history of the analyzed code (the supplied code, else the top suggestion).")
    history: CodeHistoryResponse | None
    text_okpd2_alignment: Literal["ALIGNED", "UNCERTAIN", "MISMATCH"] | None = Field(
        description="Only when an OKPD2 was supplied; null otherwise.")
    ranking_okpd2: str | None = Field(description="OKPD2 actually used by the ranking (null = text/semantic only).")
    warnings: list[str]


class Freshness(BaseModel):
    last_checked_at: datetime | None
    source_url: str | None
    status: Literal["FRESH", "STALE", "UNKNOWN"]


class ContactSource(BaseModel):
    value: str
    source_url: str
    source_authority: Literal["FIRST_PARTY", "FNS_EGRUL_DERIVED_REGISTRY", "REGULATORY_REGISTRY"]
    checked_at: datetime
    address_type: Literal["PUBLISHED_COMPANY_ADDRESS", "REGISTERED_LEGAL_ADDRESS"] | None = None


class Contact(BaseModel):
    phone: str | None
    email: str | None
    website: str | None = Field(description="Only a source-backed website; never inferred.")
    address: str | None
    sources: dict[str, ContactSource] = Field(default_factory=dict,
                                              description="Provenance of every populated field (value, source_url, authority, checked_at).")
    identity_basis: str | None = Field(None, description="Why the contact source belongs to this INN.")
    freshness: Freshness | None = Field(None, description="Freshness of the contact information itself (an outdated page is STALE).")


class HistoricalEvidence(BaseModel):
    relevant_lots: int
    relevant_awards: int
    relevant_ais_awards: int
    relevant_em_participations: int
    most_recent_relevant: date
    best_products: list[str]
    best_okpd2: str | None
    evidence_lot_ids: list[str]
    components: dict[str, float]
    contributions: dict[str, float]


class SupplierResult(BaseModel):
    rank: int
    supplier_id: str
    inn: str
    company_name: str | None = Field(description="Known only from curated evidence; procurement data has no supplier names.")
    registration_region: str | None
    score: float
    role: str | None = Field(description="Market role from curated evidence; null when no source establishes it.")
    role_evidence_status: Literal["VERIFIED", "UNDER_REVIEW", "UNVERIFIED", "NO_EVIDENCE"]
    reasons: list[str] = Field(description="Deterministic template explanations from historical evidence (no semantic lines).")
    historical_evidence: HistoricalEvidence
    semantic_evidence: list[SemanticEvidenceResponse] = Field(description="Secondary provenance of the semantic branch.")
    contact: Contact | None
    freshness: Freshness | None


class PoolHealthEntry(BaseModel):
    okpd2: str
    source: Literal["PROVIDED", "SUGGESTED"]
    status: Literal["OK", "UNAVAILABLE"]
    error: SectionError | None
    pool_health: PoolHealthResponse | None
    concentration: ConcentrationResponse | None
    historical_alternatives: list[HistoricalAlternativeResponse]


class ExternalCandidateResult(ExternalCandidateResponse):
    contact: Contact
    freshness: Freshness


class ExternalExpansionEntry(BaseModel):
    okpd2: str
    source: Literal["PROVIDED", "SUGGESTED"]
    available: bool = Field(description="False = no curated evidence for this code, not 'no external suppliers exist'.")
    evidence_checked_at: datetime | None
    verified_count: int
    under_review_count: int
    candidates: list[ExternalCandidateResult]


class PriceIntelligence(BaseModel):
    available: bool
    reason: str


class Integration(BaseModel):
    export_available: bool
    export_formats: list[Literal["json", "csv"]]
    export_url: str


class SupplierSearchResponse(BaseModel):
    search_id: str = Field(description="Stateless, deterministic id (encodes the request) used by the export endpoint.")
    query: QueryEcho
    classification: Classification
    candidate_count: int
    suppliers: list[SupplierResult]
    pool_health: list[PoolHealthEntry]
    external_expansion: list[ExternalExpansionEntry]
    price_intelligence: PriceIntelligence
    integration: Integration
    semantic_enabled: bool
    warnings: list[str]
    timings_ms: dict[str, float]
