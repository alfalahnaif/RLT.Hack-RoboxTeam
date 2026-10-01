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


@dataclass(frozen=True)
class CandidateInput:
    supplier_inn: str | None
    company_name: str | None = None


@dataclass(frozen=True)
class SupplierEvidence:
    evidence_type: str
    source_url: str | None
    source_name: str | None
    product_scope: tuple[str, ...]
    evidence_date: date | None
    checked_at: datetime | None
    evidence_status: EvidenceStatus
    verification_strength: VerificationStrength
    notes: str | None = None


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
