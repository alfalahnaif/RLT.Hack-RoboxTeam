"""P5-001A Supplier 360 response contract (GET /api/v1/suppliers/{inn}/profile, POST …/enrich)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

FreshnessStatus = Literal["FRESH", "STALE", "UNKNOWN"]


class SupplierIdentity(BaseModel):
    inn: str
    entity_kind: str | None = None
    display_name: str | None = Field(None, description="Registry legal name; else the accepted curated name; else null")
    legal_name: str | None = None
    short_name: str | None = None
    legal_status: str | None = Field(None, description="ACTIVE / CEASED as published by the registry; null when not enriched")
    ogrn: str | None = None
    kpp: str | None = None
    region: str | None = None
    registered_address: str | None = None
    registration_date: date | None = None
    primary_okved: str | None = None
    identity_source_url: str | None = None
    identity_source_type: str | None = None
    historically_known: bool = Field(description="INN appears in the organizer procurement data")


class WebsiteVerificationOut(BaseModel):
    """P5-002A: how the official website (or the best rejected candidate) was checked against the EGRUL identity."""
    status: Literal["VERIFIED_STRONG", "VERIFIED_COMPOSITE", "REJECTED", "UNKNOWN"]
    signals: list[str] = Field([], description="e.g. INN_ON_SITE, OGRN_ON_SITE, KPP_ON_SITE, EXACT_LEGAL_NAME, REGISTERED_STREET_ADDRESS")
    discovered_via: str | None = Field(None, description="Discovery provider, e.g. EGRUL_EMAIL_DOMAIN, BRAVE_SEARCH_API, LEGAL_NAME_DOMAIN")
    checked_at: datetime | None = None


class WebsiteCheckOut(BaseModel):
    """One candidate website checked in an enrichment run (append-only history)."""
    candidate_url: str
    official_url: str | None = None
    status: Literal["VERIFIED_STRONG", "VERIFIED_COMPOSITE", "REJECTED", "UNKNOWN"]
    signals: list[str] = []
    discovered_via: str | None = None
    reason: str | None = None
    checked_at: datetime


class EnrichmentState(BaseModel):
    status: Literal["NOT_ENRICHED", "IN_PROGRESS", "COMPLETE", "PARTIAL", "FAILED"]
    reasons: list[str] = []
    retryable: bool = False
    last_enriched_at: datetime | None = None
    official_website: str | None = None
    website_confidence: Literal["HIGH", "MEDIUM", "LOW", "NONE"] = "NONE"
    website_candidate: str | None = Field(None, description="Website considered but not proven official (MEDIUM/LOW)")
    website_verification: WebsiteVerificationOut | None = Field(None, description="P5-002A; null before any website check")
    pipeline_version: str | None = None
    cache: Literal["HIT", "MISS", "REFRESHED", "NONE"] = "NONE"


class ContactItem(BaseModel):
    type: Literal["PHONE", "EMAIL", "WEBSITE", "ADDRESS"]
    value: str
    label: str | None = None
    source_url: str
    source_type: str
    checked_at: datetime
    freshness_status: FreshnessStatus
    verified: bool
    origin: Literal["ENRICHMENT_PIPELINE", "CURATED_P4_005C"]
    verification_basis: str | None = Field(None, description="P5-002A why the value is trusted, e.g. "
                                                              "OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE, FNS_EGRUL_EXTRACT")


class RoleItem(BaseModel):
    role: Literal["MANUFACTURER", "OFFICIAL_DISTRIBUTOR", "DISTRIBUTOR", "SUPPLIER", "UNKNOWN"]
    status: Literal["VERIFIED", "INFERRED", "UNDER_REVIEW", "UNKNOWN"]
    basis: str
    claim: str
    strength: str
    source_url: str | None = None
    source_type: str
    checked_at: datetime | None = None
    origin: Literal["ENRICHMENT_PIPELINE", "CURATED_P3_002B", "PROCUREMENT_HISTORY"]


class EvidenceItemOut(BaseModel):
    evidence_type: str
    claim: str
    value: str | None = None
    source_url: str
    source_type: str
    checked_at: datetime
    valid_until: date | None = None
    strength: str


class FreshnessBlock(BaseModel):
    policy_version: str
    identity: FreshnessStatus
    identity_checked_at: datetime | None = None
    contacts: FreshnessStatus
    contacts_last_checked_at: datetime | None = None
    content_currency: str | None = Field(None, description="CURRENT / UNDATED / OUTDATED of the contact source page")
    profile_cache_valid_until: datetime | None = None
    note: str = "Retrieved recently is not the same as fresh: an outdated source page stays STALE; undated pages are UNKNOWN."


class OkpdCount(BaseModel):
    okpd2: str
    awarded_lots: int


class HistorySummary(BaseModel):
    observed_relations: int
    relevant_awards: int = Field(description="Relations with is_winner = true (all АИС ГЗ rows are winner rows)")
    distinct_lots: int
    first_observed_activity: date | None = None
    last_observed_activity: date | None = None
    platforms: dict[str, int] = {}
    top_okpd2: list[OkpdCount] = []
    note: str = "Organizer procurement data (2024–2025). No cross-platform win rate is computed (АИС ГЗ rows are winner-only)."


class SourceRef(BaseModel):
    source_url: str
    source_type: str
    last_checked_at: datetime | None = None
    used_for: list[str]


class AttemptOut(BaseModel):
    source: str
    outcome: str
    detail: str | None = None
    duration_ms: int


class SupplierProfileResponse(BaseModel):
    supplier: SupplierIdentity
    enrichment: EnrichmentState
    contacts: list[ContactItem]
    roles: list[RoleItem]
    evidence: list[EvidenceItemOut]
    freshness: FreshnessBlock
    procurement_history_summary: HistorySummary | None
    sources: list[SourceRef]
    last_run_attempts: list[AttemptOut] = []
    website_checks: list[WebsiteCheckOut] = Field([], description="P5-002A latest website identity checks (accepted and rejected)")
