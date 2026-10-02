"""P5-001A Supplier 360 enrichment domain: values exchanged between providers, pipeline and repository.

External enrichment evidence is kept apart from historical procurement evidence (which is never copied here; the API reads it
from the canonical tables at response time). Every populated external value carries source_url + source_type + checked_at.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class EnrichmentStatus(str, Enum):
    NOT_ENRICHED = "NOT_ENRICHED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ContactType(str, Enum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    WEBSITE = "WEBSITE"
    ADDRESS = "ADDRESS"


class SourceType(str, Enum):
    FNS_EGRUL = "FNS_EGRUL"                                  # egrul.nalog.ru (official FNS service)
    FNS_EGRUL_DERIVED_REGISTRY = "FNS_EGRUL_DERIVED_REGISTRY"  # registry mirror built from FNS data (checko.ru)
    FIRST_PARTY = "FIRST_PARTY"                              # identity-verified company website
    CURATED_P4_005C = "CURATED_P4_005C"                      # accepted P4-005C contact record (read-only)


class WebsiteConfidence(str, Enum):
    HIGH = "HIGH"      # INN/OGRN on the site, or exact legal name + registered street address -> official
    MEDIUM = "MEDIUM"  # exact legal name + registered locality on the site, no requisites -> NOT marked official
    LOW = "LOW"        # reachable, no identity match -> rejected
    NONE = "NONE"      # no candidate / unreachable


class Role(str, Enum):
    MANUFACTURER = "MANUFACTURER"
    OFFICIAL_DISTRIBUTOR = "OFFICIAL_DISTRIBUTOR"
    DISTRIBUTOR = "DISTRIBUTOR"
    SUPPLIER = "SUPPLIER"
    UNKNOWN = "UNKNOWN"


class RoleStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNDER_REVIEW = "UNDER_REVIEW"
    UNKNOWN = "UNKNOWN"


class Strength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class SourceOutcome(str, Enum):
    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class SourceUnavailable(RuntimeError):
    """A source could not be queried (network, HTTP error, captcha, timeout) — retryable."""


@dataclass(frozen=True)
class Sourced:
    value: str
    source_url: str
    source_type: SourceType
    checked_at: datetime


@dataclass(frozen=True)
class RegistryIdentity:
    inn: str
    entity_kind: str                 # LEGAL_ENTITY | INDIVIDUAL_ENTREPRENEUR
    legal_name: Sourced
    short_name: Sourced | None = None
    ogrn: Sourced | None = None
    kpp: Sourced | None = None
    legal_status: Sourced | None = None   # ACTIVE | CEASED (as published by the registry)
    region: Sourced | None = None
    registration_date: date | None = None
    registered_address: Sourced | None = None
    primary_okved: Sourced | None = None  # "10.51.9 Производство прочей молочной продукции"
    website_hints: tuple[Sourced, ...] = ()  # website claimed by a registry mirror — a candidate, never official by itself


@dataclass(frozen=True)
class WebsiteCandidate:
    url: str
    discovered_via: Sourced


@dataclass(frozen=True)
class Page:
    url: str
    html: str
    text: str


@dataclass(frozen=True)
class WebsiteVerification:
    candidate_url: str
    confidence: WebsiteConfidence
    signals: tuple[str, ...]          # e.g. INN_ON_SITE, OGRN_ON_SITE, EXACT_LEGAL_NAME, REGISTERED_LOCALITY
    official_url: str | None          # set only for HIGH
    pages: tuple[Page, ...] = ()       # pages that were fetched (contacts are extracted only when official)
    latest_year: int | None = None    # latest copyright / dated-content year seen on the pages
    checked_at: datetime | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ContactValue:
    type: ContactType
    value: str
    normalized: str
    label: str | None
    source_url: str
    source_type: SourceType
    checked_at: datetime
    content_currency: str | None      # CURRENT | UNDATED | OUTDATED of the source page (None for registry values)
    verified: bool                    # True = from the registry or an identity-verified first-party page


@dataclass(frozen=True)
class EvidenceItem:
    evidence_type: str                # LEGAL_IDENTITY | WEBSITE_IDENTITY | WEBSITE_CANDIDATE | OKVED_PRIMARY | ...
    claim: str
    value: str | None
    source_url: str
    source_type: SourceType
    checked_at: datetime
    strength: Strength
    valid_until: date | None = None


@dataclass(frozen=True)
class RoleEvidenceItem:
    role: Role
    status: RoleStatus
    basis: str                        # OKVED_PRIMARY | FIRST_PARTY_PRODUCTION_CLAIM | FIRST_PARTY_DISTRIBUTION_CLAIM | ...
    claim: str
    source_url: str | None
    source_type: str
    checked_at: datetime | None
    strength: Strength


@dataclass(frozen=True)
class SourceAttempt:
    source: str
    outcome: SourceOutcome
    detail: str | None = None
    duration_ms: int = 0


@dataclass
class EnrichmentResult:
    inn: str
    status: EnrichmentStatus
    reasons: list[str] = field(default_factory=list)
    retryable: bool = False
    identity: RegistryIdentity | None = None
    website: WebsiteVerification | None = None
    contacts: list[ContactValue] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    roles: list[RoleEvidenceItem] = field(default_factory=list)
    attempts: list[SourceAttempt] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    content_currency: str | None = None

    @property
    def duration_ms(self) -> int:
        if not self.started_at or not self.finished_at:
            return 0
        return int((self.finished_at - self.started_at).total_seconds() * 1000)
