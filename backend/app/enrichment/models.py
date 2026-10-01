"""Separate historical reconciliation from future evidence verification."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum


class ReconciliationStatus(str, Enum):
    CATEGORY_HISTORICAL = "CATEGORY_HISTORICAL"
    HISTORICAL_OTHER_CATEGORY = "HISTORICAL_OTHER_CATEGORY"
    EXTERNAL_NEW = "EXTERNAL_NEW"
    INVALID_INN = "INVALID_INN"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"


class EvidenceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    UNKNOWN = "UNKNOWN"


class VerificationStrength(str, Enum):
    NONE = "NONE"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class MarketRole(str, Enum):
    MANUFACTURER = "MANUFACTURER"
    MANUFACTURER_ASSERTED_BY_DECLARATION = "MANUFACTURER_ASSERTED_BY_DECLARATION"
    UNKNOWN = "UNKNOWN"


class TargetProductMatch(str, Enum):
    DIRECT_PRODUCT_TEXT = "DIRECT_PRODUCT_TEXT"
    HISTORICAL_DIRECT_PRODUCT_TEXT = "HISTORICAL_DIRECT_PRODUCT_TEXT"
    UNKNOWN = "UNKNOWN"


class EvidenceType(str, Enum):
    CONFORMITY_DECLARATION = "CONFORMITY_DECLARATION"
    LEGAL_IDENTITY = "LEGAL_IDENTITY"
    FIRST_PARTY_WEBSITE = "FIRST_PARTY_WEBSITE"
    CURRENT_PRODUCT_LISTING = "CURRENT_PRODUCT_LISTING"
    BUSINESS_PROFILE = "BUSINESS_PROFILE"


class SourceAuthority(str, Enum):
    REGULATORY_REGISTRY_MIRROR_WITH_FGIS_ROSACCREDITATION_SOURCE = "REGULATORY_REGISTRY_MIRROR_WITH_FGIS_ROSACCREDITATION_SOURCE"
    FNS_EGRUL_DERIVED = "FNS_EGRUL_DERIVED"
    FIRST_PARTY = "FIRST_PARTY"
    RETAIL_SECONDARY = "RETAIL_SECONDARY"
    SECONDARY_BUSINESS_PROFILE = "SECONDARY_BUSINESS_PROFILE"


class RoleAssertion(str, Enum):
    MANUFACTURER_AND_APPLICANT = "MANUFACTURER_AND_APPLICANT"
    ACTIVE_LEGAL_ENTITY = "ACTIVE_LEGAL_ENTITY"
    DAIRY_PRODUCER = "DAIRY_PRODUCER"
    ACTIVE_DAIRY_MANUFACTURER = "ACTIVE_DAIRY_MANUFACTURER"
    MANUFACTURER_NAMED_ON_PRODUCT_LISTING = "MANUFACTURER_NAMED_ON_PRODUCT_LISTING"
    MAIN_OKVED_56_10 = "MAIN_OKVED_56_10"
    DAIRY_MANUFACTURER = "DAIRY_MANUFACTURER"


@dataclass(frozen=True)
class CandidateInput:
    supplier_inn: str | None
    company_name: str | None = None


@dataclass(frozen=True)
class SupplierEvidence:
    evidence_type: EvidenceType | str
    source_url: str | None
    source_name: str | None
    product_scope: tuple[str, ...]
    evidence_date: date | None
    checked_at: datetime | None
    evidence_status: EvidenceStatus
    verification_strength: VerificationStrength
    notes: str | None = None
    source_record_id: str | None = None
    source_authority: SourceAuthority | None = None
    valid_until: date | None = None
    retrieved_at: datetime | None = None
    role_assertion: RoleAssertion | None = None
    asserted_okpd2_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalCandidate:
    supplier_inn: str | None
    company_name: str | None
    target_okpd2: str
    as_of: date
    inn_valid: bool
    inn_validation_flags: tuple[str, ...]
    reconciliation_status: ReconciliationStatus
    historically_known: bool
    target_category_observed: bool
    historical_first_seen: date | None
    historical_last_seen: date | None
    historical_lot_count: int
    historical_win_count: int
    target_category_lot_count: int
    target_category_win_count: int
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    evidence_records: tuple[SupplierEvidence, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CuratedCandidate:
    supplier_inn: str
    canonical_name: str
    aliases: tuple[str, ...]
    reconciliation_status: ReconciliationStatus
    market_role: MarketRole
    verification_status: VerificationStatus
    overall_strength: VerificationStrength
    target_product_match: TargetProductMatch
    exact_okpd2_asserted_by_source: bool
    verification_reason_codes: tuple[str, ...]
    review_reasons: tuple[str, ...]
    notes: str | None
    evidence_records: tuple[SupplierEvidence, ...]


@dataclass(frozen=True)
class EvidenceSeed:
    target_okpd2: str
    target_label: str
    checked_at: datetime
    candidates: tuple[CuratedCandidate, ...]
    recommended_demo_subset: tuple[str, ...]
    recommended_review_queue: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedExternalCandidate:
    supplier_inn: str
    company_name: str
    aliases: tuple[str, ...]
    reconciliation_status: ReconciliationStatus
    market_role: MarketRole
    verification_status: VerificationStatus
    verification_strength: VerificationStrength
    target_product_match: TargetProductMatch
    exact_okpd2_asserted_by_source: bool
    verification_reason_codes: tuple[str, ...]
    review_reasons: tuple[str, ...]
    why_candidate: str
    evidence_summary: tuple[dict, ...]
    evidence_count: int
    active_evidence_count: int

    def to_dict(self) -> dict:
        return asdict(self)
