"""P5-001A identity-first enrichment of ONE supplier INN (pure orchestration over injected providers; no DB, no globals).

INN -> official EGRUL (identity, status, OGRN/KPP, address, primary OKVED) -> optional secondary registries (corroboration,
website hints) -> candidate website -> website identity verification -> contacts -> role evidence -> freshness.
Contacts are never collected before the company identity is established and the site is proven to be the company's own.

P5-002A: candidate websites come from WebsiteDiscovery (EGRUL e-mail domain, search APIs when configured, Wikidata, legal-name
domains; checko only as an optional hint). A stored official website is re-verified FIRST: still verified -> kept (new
candidates are not considered); unreachable -> kept, nothing else is tried; rechecked and rejected -> the other candidates are
checked. Every checked candidate is returned in `website_checks` (persisted as history).

Status: identity + official website + phone or e-mail -> COMPLETE; identity with gaps -> PARTIAL;
official registry unreachable and no mirror answer -> FAILED (retryable); INN unknown to the registry -> FAILED (not retryable).
A secondary registry (checko.ru) is OPTIONAL: its rate limiting / outage / open circuit never fails a supplier; it only adds a
reason and makes the profile retryable (the website hint it would have given is missing). Same for an unreachable website or a
failed official extract: PARTIAL, retryable=True (re-attempted after the retry delay, not kept for the TTL).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.enrichment import freshness as F
from app.enrichment.profile_models import (ContactType, EnrichmentResult, EnrichmentStatus, EvidenceItem, RegistryIdentity,
                                           SourceAttempt, SourceOutcome, SourceType, SourceUnavailable, Sourced, Strength,
                                           WebsiteCandidate, WebsiteConfidence, WebsiteVerification, outcome_of)
from app.enrichment.providers import (CompanyRegistryProvider, ContactExtractor, RoleEvidenceProvider, WebsiteDiscoveryProvider,
                                      WebsiteVerifier, host_of, merge_identities, registry_contacts)

PIPELINE_VERSION = "p5-002a-v1"   # p5-001a-v2 + P5-002A website discovery / verification statuses / verification basis
MAX_WEBSITE_CANDIDATES = 4
STORED_SITE = "STORED_OFFICIAL_SITE"


@dataclass
class Providers:
    registries: list[CompanyRegistryProvider]   # [0] = official (required); [1:] = optional secondary mirrors
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


def _website_evidence(v: WebsiteVerification, discovered_via, provider: str | None = None) -> EvidenceItem:
    via = provider or discovered_via.source_type.value
    if v.confidence == WebsiteConfidence.HIGH:
        return EvidenceItem("WEBSITE_IDENTITY", f"Official website ({v.verification_status.value}, found via {via}): identity "
                            f"confirmed on the site ({', '.join(v.signals)})", v.official_url, v.official_url,
                            SourceType.FIRST_PARTY, v.checked_at,
                            Strength.STRONG if v.verification_status.value == "VERIFIED_STRONG" else Strength.MODERATE)
    return EvidenceItem("WEBSITE_CANDIDATE", f"Candidate website {v.candidate_url} (found via {via}) "
                        f"NOT marked official: {v.verification_status.value}, signals {list(v.signals) or 'none'}",
                        v.candidate_url, v.pages[0].url if v.pages else v.candidate_url, SourceType.FIRST_PARTY, v.checked_at,
                        Strength.WEAK)


def enrich(inn: str, providers: Providers, now: Callable[[], datetime], prior_website: str | None = None) -> EnrichmentResult:
    res = EnrichmentResult(inn=inn, status=EnrichmentStatus.IN_PROGRESS, started_at=now())

    # 1. legal identity: the official registry first; optional mirrors only corroborate / fill gaps when their OGRN agrees
    ANSWERED = (SourceOutcome.OK, SourceOutcome.NOT_FOUND)
    found, outcomes = [], []
    for reg in providers.registries:
        ident, err, ms = _timed(lambda r=reg: r.lookup_by_inn(inn))
        if err:
            outcome = outcome_of(err)
            res.attempts.append(SourceAttempt(reg.name, outcome, str(err)[:200], ms))
        else:
            outcome = SourceOutcome.OK if ident else SourceOutcome.NOT_FOUND
            res.attempts.append(SourceAttempt(reg.name, outcome, None, ms))
            res.attempts.extend(ident.sub_attempts if ident else ())
        found.append(ident)
        outcomes.append(outcome)
    primary = outcomes[0] if outcomes else None
    identity = found[0] if found else None
    for extra in found[1:]:
        identity, conflict = merge_identities(identity, extra)
        if conflict:
            res.reasons.append(conflict)
    if identity is None or identity.legal_name is None:
        res.finished_at = now()
        if not any(o in ANSWERED for o in outcomes):
            res.status, res.retryable = EnrichmentStatus.FAILED, True
            res.reasons.append("SOURCE_UNAVAILABLE")
        elif primary == SourceOutcome.NOT_FOUND:
            res.status = EnrichmentStatus.FAILED
            res.reasons.append("REGISTRY_NOT_FOUND")
        else:
            res.status, res.retryable = EnrichmentStatus.FAILED, True
            res.reasons.append("PRIMARY_REGISTRY_UNAVAILABLE")
        return res
    if primary not in ANSWERED:
        res.reasons.append("PRIMARY_REGISTRY_UNAVAILABLE_MIRROR_USED")
        res.retryable = True
    for o in outcomes[1:]:      # optional secondary registries: never a failure, only a (retryable) gap
        if o not in ANSWERED:
            res.reasons.append(f"REGISTRY_MIRROR_{'SKIPPED' if o == SourceOutcome.SKIPPED else o.value}")
            res.retryable = True
    for a in (found[0].sub_attempts if found and found[0] else ()):
        if a.outcome in (SourceOutcome.UNAVAILABLE, SourceOutcome.RATE_LIMITED):
            res.reasons.append("EGRUL_EXTRACT_UNAVAILABLE")
            res.retryable = True
        elif a.outcome == SourceOutcome.REJECTED:
            res.reasons.append("EGRUL_EXTRACT_REJECTED")
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
        candidates = list(providers.discovery.discover(identity))
        log = getattr(providers.discovery, "last_log", None)
        if log is not None:
            res.attempts.extend(log.attempts)
            if log.rejected:
                res.attempts.append(SourceAttempt("DISCOVERY_FILTER", SourceOutcome.REJECTED,
                                                  "; ".join(f"{host_of(u)}={c}" for u, c, _ in log.rejected[:8])[:200]))
        if prior_website:
            stored = WebsiteCandidate(prior_website, Sourced(prior_website, prior_website, SourceType.FIRST_PARTY, now()),
                                      provider=STORED_SITE)
            candidates = [stored] + [c for c in candidates if host_of(c.url) != host_of(prior_website)]
        candidates = candidates[:MAX_WEBSITE_CANDIDATES]
        if not candidates:
            res.reasons.append("NO_WEBSITE_CANDIDATE")
        for cand in candidates:
            is_stored = cand.provider == STORED_SITE
            v, err, ms = _timed(lambda c=cand: providers.verifier.verify_company_site(identity, c))
            if err:
                res.attempts.append(SourceAttempt(providers.verifier.name, outcome_of(err), f"{cand.url}: {err}"[:200], ms))
                if is_stored:          # the stored official site could not be re-checked: keep it, do not replace it
                    res.reasons.append("STORED_WEBSITE_NOT_RECHECKED")
                    res.retryable = True
                    break
                continue
            res.website_checks.append(v)
            if is_stored:
                res.prior_site_rechecked = True
            res.attempts.append(SourceAttempt(providers.verifier.name,
                                              SourceOutcome.OK if v.confidence == WebsiteConfidence.HIGH else SourceOutcome.REJECTED,
                                              f"{cand.url}: {v.verification_status.value} {list(v.signals)}"[:200], ms))
            res.evidence.append(_website_evidence(v, cand.discovered_via, cand.provider))
            if verification is None or v.confidence == WebsiteConfidence.HIGH:
                verification = v
            if v.confidence == WebsiteConfidence.HIGH:
                break
            if is_stored:
                res.reasons.append("STORED_WEBSITE_FAILED_RECHECK")
        if candidates and not res.website_checks and "STORED_WEBSITE_NOT_RECHECKED" not in res.reasons:
            res.reasons.append("WEBSITE_UNAVAILABLE")
            res.retryable = True
        elif verification is not None and verification.confidence != WebsiteConfidence.HIGH:
            res.reasons.append("WEBSITE_IDENTITY_NOT_CONFIRMED")
        if "STORED_WEBSITE_NOT_RECHECKED" in res.reasons:
            verification = None        # nothing checked this run may replace the stored site
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
