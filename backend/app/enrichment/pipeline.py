"""P5-001A identity-first enrichment of ONE supplier INN (pure orchestration over injected providers; no DB, no globals).

INN -> legal identity -> candidate website -> website identity verification -> contacts -> role evidence -> freshness.
Contacts are never collected before the company identity is established and the site is proven to be the company's own.

Status: identity + official website + phone or e-mail -> COMPLETE; identity with gaps -> PARTIAL;
registry unreachable -> FAILED (retryable); INN unknown to the registry -> FAILED (not retryable).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.enrichment import freshness as F
from app.enrichment.profile_models import (ContactType, EnrichmentResult, EnrichmentStatus, EvidenceItem, RegistryIdentity,
                                           SourceAttempt, SourceOutcome, SourceType, SourceUnavailable, Strength,
                                           WebsiteConfidence, WebsiteVerification)
from app.enrichment.providers import (CompanyRegistryProvider, ContactExtractor, RoleEvidenceProvider, WebsiteDiscoveryProvider,
                                      WebsiteVerifier, merge_identities, registry_contacts)

PIPELINE_VERSION = "p5-001a-v1"
MAX_WEBSITE_CANDIDATES = 2


@dataclass
class Providers:
    registries: list[CompanyRegistryProvider]   # ordered by authority: official first, mirrors after
    discovery: WebsiteDiscoveryProvider
    verifier: WebsiteVerifier
    extractor: ContactExtractor
    roles: RoleEvidenceProvider


def _timed(fn):
    t0 = time.perf_counter()
    try:
        return fn(), None, int((time.perf_counter() - t0) * 1000)
    except SourceUnavailable as e:
        return None, e, int((time.perf_counter() - t0) * 1000)


def _identity_evidence(identity: RegistryIdentity) -> list[EvidenceItem]:
    out = []
    ln = identity.legal_name
    strength = Strength.STRONG if ln.source_type == SourceType.FNS_EGRUL else Strength.MODERATE
    reqs = ", ".join(f"{k} {getattr(identity, k).value}" for k in ("ogrn", "kpp") if getattr(identity, k))
    out.append(EvidenceItem("LEGAL_IDENTITY", f"INN {identity.inn} is registered as «{ln.value}»" + (f" ({reqs})" if reqs else ""),
                            ln.value, ln.source_url, ln.source_type, ln.checked_at, strength))
    if identity.legal_status:
        s = identity.legal_status
        out.append(EvidenceItem("LEGAL_STATUS", f"Registry status: {s.value}", s.value, s.source_url, s.source_type, s.checked_at, strength))
    if identity.primary_okved:
        o = identity.primary_okved
        out.append(EvidenceItem("OKVED_PRIMARY", f"Primary OKVED: {o.value}", o.value, o.source_url, o.source_type, o.checked_at,
                                Strength.MODERATE))
    return out


def _website_evidence(v: WebsiteVerification, discovered_via) -> EvidenceItem:
    if v.confidence == WebsiteConfidence.HIGH:
        return EvidenceItem("WEBSITE_IDENTITY", f"Official website: the company's requisites are published on the site "
                            f"({', '.join(v.signals)})", v.official_url, v.official_url, SourceType.FIRST_PARTY, v.checked_at,
                            Strength.STRONG)
    return EvidenceItem("WEBSITE_CANDIDATE", f"Candidate website {v.candidate_url} (found via {discovered_via.source_type.value}) "
                        f"NOT marked official: confidence {v.confidence.value}, signals {list(v.signals) or 'none'}",
                        v.candidate_url, v.pages[0].url if v.pages else v.candidate_url, SourceType.FIRST_PARTY, v.checked_at,
                        Strength.WEAK)


def enrich(inn: str, providers: Providers, now: Callable[[], datetime]) -> EnrichmentResult:
    res = EnrichmentResult(inn=inn, status=EnrichmentStatus.IN_PROGRESS, started_at=now())

    # 1. legal identity (official registry first; mirrors fill gaps only when their OGRN agrees)
    found, answered = [], 0
    for reg in providers.registries:
        ident, err, ms = _timed(lambda r=reg: r.lookup_by_inn(inn))
        if err:
            res.attempts.append(SourceAttempt(reg.name, SourceOutcome.UNAVAILABLE, str(err)[:200], ms))
            found.append(None)
            continue
        answered += 1
        res.attempts.append(SourceAttempt(reg.name, SourceOutcome.OK if ident else SourceOutcome.NOT_FOUND, None, ms))
        found.append(ident)
    primary_answered = bool(res.attempts) and res.attempts[0].outcome != SourceOutcome.UNAVAILABLE
    identity = found[0] if found else None
    for extra in found[1:]:
        identity, conflict = merge_identities(identity, extra)
        if conflict:
            res.reasons.append(conflict)
    if identity is None or identity.legal_name is None:
        res.finished_at = now()
        if answered == 0:
            res.status, res.retryable = EnrichmentStatus.FAILED, True
            res.reasons.append("SOURCE_UNAVAILABLE")
        elif primary_answered and res.attempts[0].outcome == SourceOutcome.NOT_FOUND:
            res.status = EnrichmentStatus.FAILED
            res.reasons.append("REGISTRY_NOT_FOUND")
        else:
            res.status, res.retryable = EnrichmentStatus.FAILED, True
            res.reasons.append("PRIMARY_REGISTRY_UNAVAILABLE")
        return res
    if not primary_answered:
        res.reasons.append("PRIMARY_REGISTRY_UNAVAILABLE_MIRROR_USED")
    res.identity = identity
    res.evidence += _identity_evidence(identity)
    if identity.legal_status and identity.legal_status.value == "CEASED":
        res.reasons.append("LEGAL_ENTITY_CEASED")

    # 2. website (identity-verified) — not for individual entrepreneurs (their contacts are personal data)
    verification: WebsiteVerification | None = None
    if identity.entity_kind == "INDIVIDUAL_ENTREPRENEUR":
        res.reasons.append("INDIVIDUAL_ENTREPRENEUR_CONTACTS_NOT_COLLECTED")
        res.attempts.append(SourceAttempt(providers.verifier.name, SourceOutcome.SKIPPED, "individual entrepreneur"))
    else:
        candidates = providers.discovery.discover(identity)[:MAX_WEBSITE_CANDIDATES]
        if not candidates:
            res.reasons.append("NO_WEBSITE_CANDIDATE")
        for cand in candidates:
            v, err, ms = _timed(lambda c=cand: providers.verifier.verify_company_site(identity, c))
            if err:
                res.attempts.append(SourceAttempt(providers.verifier.name, SourceOutcome.UNAVAILABLE, f"{cand.url}: {err}"[:200], ms))
                continue
            res.attempts.append(SourceAttempt(providers.verifier.name,
                                              SourceOutcome.OK if v.confidence == WebsiteConfidence.HIGH else SourceOutcome.REJECTED,
                                              f"{cand.url}: {v.confidence.value} {list(v.signals)}"[:200], ms))
            res.evidence.append(_website_evidence(v, cand.discovered_via))
            if verification is None or v.confidence == WebsiteConfidence.HIGH:
                verification = v
            if v.confidence == WebsiteConfidence.HIGH:
                break
        if candidates and verification is None:
            res.reasons.append("WEBSITE_UNAVAILABLE")
        elif verification is not None and verification.confidence != WebsiteConfidence.HIGH:
            res.reasons.append("WEBSITE_IDENTITY_NOT_CONFIRMED")
    res.website = verification

    # 3. contacts (registry address + first-party contacts from the verified site only)
    res.contacts = registry_contacts(identity)
    if verification is not None and verification.confidence == WebsiteConfidence.HIGH:
        res.contacts += providers.extractor.extract(identity, verification)
        res.content_currency = F.content_currency(verification.latest_year, (verification.checked_at or now()).date())

    # 4. role / product evidence (never VERIFIED automatically)
    res.roles = providers.roles.collect(identity, verification)

    # 5. status
    has_site = any(c.type == ContactType.WEBSITE for c in res.contacts)
    has_reach = any(c.type in (ContactType.PHONE, ContactType.EMAIL) for c in res.contacts)
    if has_site and not has_reach:
        res.reasons.append("NO_PUBLIC_PHONE_OR_EMAIL_ON_OFFICIAL_SITE")
    res.status = EnrichmentStatus.COMPLETE if has_site and has_reach else EnrichmentStatus.PARTIAL
    res.finished_at = now()
    return res
