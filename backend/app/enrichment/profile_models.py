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


class WebsiteVerificationStatus(str, Enum):
    """P5-002A outcome of checking one candidate site against the official EGRUL identity."""
    VERIFIED_STRONG = "VERIFIED_STRONG"        # this company's INN or OGRN published on the site (self-identification)
    VERIFIED_COMPOSITE = "VERIFIED_COMPOSITE"  # exact legal-name core + (registered street & house, or KPP) on the site
    REJECTED = "REJECTED"                      # reachable, identity not proven / another company's site / directory-like
    UNKNOWN = "UNKNOWN"                        # not checked (unreachable, robots.txt disallow, not attempted)


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
    RATE_LIMITED = "RATE_LIMITED"   # HTTP 429 / 503 still refused after the single bounded backoff
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class SourceUnavailable(RuntimeError):
    """A source could not be queried (network, HTTP error, captcha, timeout) — retryable."""


class SourceRateLimited(SourceUnavailable):
    """The source refuses because of request volume (HTTP 429 / 503) — retryable, and a signal for the circuit breaker."""


class SourceSkipped(SourceUnavailable):
    """The source was deliberately not called (e.g. its circuit breaker is open after repeated rate limiting)."""


def outcome_of(err: SourceUnavailable) -> "SourceOutcome":
    if isinstance(err, SourceSkipped):
        return SourceOutcome.SKIPPED
    return SourceOutcome.RATE_LIMITED if isinstance(err, SourceRateLimited) else SourceOutcome.UNAVAILABLE


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
    registered_email: Sourced | None = None  # e-mail registered in EGRUL (official extract) — discovery hint + business contact
    sub_attempts: tuple = ()                 # SourceAttempt of sub-steps (e.g. the official EGRUL extract) for the attempt log


@dataclass(frozen=True)
class WebsiteCandidate:
    url: str
    discovered_via: Sourced
    provider: str | None = None       # P5-002A WebsiteSearchProvider that proposed it (EGRUL_EMAIL_DOMAIN, BRAVE_SEARCH_API, ...)
    rank: int = 0                     # bounded ranked list position (0 = best)
    hint: str | None = None           # query / snippet that produced the candidate (provenance only, never a fact)


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
    status: WebsiteVerificationStatus | None = None   # P5-002A; derived from confidence when not set
    provider: str | None = None                       # discovery provider of the candidate

    @property
    def verification_status(self) -> WebsiteVerificationStatus:
        if self.status is not None:
            return self.status
        if self.confidence == WebsiteConfidence.HIGH:
            return (WebsiteVerificationStatus.VERIFIED_STRONG if {"INN_ON_SITE", "OGRN_ON_SITE"} & set(self.signals)
                    else WebsiteVerificationStatus.VERIFIED_COMPOSITE)
        return WebsiteVerificationStatus.UNKNOWN if self.confidence == WebsiteConfidence.NONE else WebsiteVerificationStatus.REJECTED


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
    verification_basis: str | None = None   # P5-002A why this value is trusted, e.g. OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE


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
    website_checks: list[WebsiteVerification] = field(default_factory=list)   # P5-002A every candidate checked this run
    prior_site_rechecked: bool = False   # the stored official site was re-verified this run (protection rule)

    @property
    def duration_ms(self) -> int:
        if not self.started_at or not self.finished_at:
            return 0
        return int((self.finished_at - self.started_at).total_seconds() * 1000)
