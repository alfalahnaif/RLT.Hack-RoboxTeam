"""P5-001A Supplier 360 service: compose the stored enrichment profile, accepted curated data and procurement history.

  build_profile(conn, inn, now)                       read-only; never calls external sources (search latency unaffected)
  enrich_supplier(conn, inn, now, refresh, factory)   cache-first; runs the identity-first pipeline only when needed

Curated P3-002B role decisions (4 VERIFIED / 2 UNDER_REVIEW) and P4-005C contact records are read from their accepted seed
files at response time and never rewritten; pipeline contacts that duplicate a curated value are not stored.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from psycopg import Connection

from app.api.market_service import build_external_expansion
from app.api.supplier_profile_models import (AttemptOut, ContactItem, EnrichmentState, EvidenceItemOut, FreshnessBlock,
                                             HistorySummary, OkpdCount, RoleItem, SourceRef, SupplierIdentity,
                                             SupplierProfileResponse)
from app.enrichment import contacts as CE
from app.enrichment import freshness as F
from app.enrichment import pipeline as P
from app.enrichment import repository as R
from app.enrichment.catalog import CuratedEvidenceCatalog
from app.enrichment.providers import (CheckoRegistryMirror, FnsEgrulRegistry, HtmlContactExtractor, HttpFetcher,
                                      HttpWebsiteVerifier, RegistryWebsiteDiscovery, SiteAndOkvedRoleEvidence, _fold,
                                      host_of, normalize_phone)
from app.shared.ids import supplier_uuid

ProvidersFactory = Callable[[Callable[[], datetime]], tuple[P.Providers, Callable[[], None]]]
_CURATED_TYPES = {"website": "WEBSITE", "email": "EMAIL", "phone": "PHONE", "address": "ADDRESS"}
_ROLE_OF_MARKET_ROLE = {"MANUFACTURER": "MANUFACTURER", "MANUFACTURER_ASSERTED_BY_DECLARATION": "MANUFACTURER"}


class InvalidInn(ValueError):
    pass


class SupplierNotFound(LookupError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def default_providers(now: Callable[[], datetime]) -> tuple[P.Providers, Callable[[], None]]:
    fetcher = HttpFetcher()
    return P.Providers(registries=[FnsEgrulRegistry(fetcher, now), CheckoRegistryMirror(fetcher, now)],
                       discovery=RegistryWebsiteDiscovery(), verifier=HttpWebsiteVerifier(fetcher, now),
                       extractor=HtmlContactExtractor(), roles=SiteAndOkvedRoleEvidence()), fetcher.close


def validate_inn(inn: str) -> str:
    if not (inn.isdigit() and len(inn) in (10, 12)):
        raise InvalidInn("INN must be 10 (legal entity) or 12 (individual entrepreneur) digits")
    return inn


def normalized_key(ctype: str, value: str) -> tuple[str, str]:
    if ctype == "PHONE":
        return ctype, normalize_phone(value) or value
    if ctype == "EMAIL":
        return ctype, value.strip().lower()
    if ctype == "WEBSITE":
        return ctype, host_of(value)
    return ctype, _fold(value)


def curated_contact_keys(record: CE.ContactRecord | None) -> set[tuple[str, str]]:
    if record is None:
        return set()
    return {normalized_key(_CURATED_TYPES[k], f.value) for k, f in record.fields.items() if f}


def is_historical(conn: Connection, inn: str) -> bool:
    return conn.execute("SELECT 1 FROM supplier WHERE inn = %s", (inn,)).fetchone() is not None


def history_summary(conn: Connection, inn: str) -> HistorySummary | None:
    sid = supplier_uuid(inn)
    row = conn.execute("""SELECT count(*), count(*) FILTER (WHERE is_winner), count(DISTINCT lot_id), min(publish_date), max(publish_date)
                          FROM supplier_history WHERE supplier_id = %s""", (sid,)).fetchone()
    if not row or not row[0]:
        return None
    platforms = dict(conn.execute("SELECT platform, count(*) FROM supplier_history WHERE supplier_id = %s GROUP BY 1 ORDER BY 1",
                                  (sid,)).fetchall())
    top = conn.execute("""SELECT i.okpd2_code, count(DISTINCT i.lot_id) n FROM supplier_history h
                          JOIN procurement_item i ON i.lot_id = h.lot_id
                          WHERE h.supplier_id = %s AND h.is_winner AND i.okpd2_code IS NOT NULL
                          GROUP BY 1 ORDER BY n DESC, 1 LIMIT 5""", (sid,)).fetchall()
    return HistorySummary(observed_relations=row[0], relevant_awards=row[1], distinct_lots=row[2], first_observed_activity=row[3],
                          last_observed_activity=row[4], platforms=platforms,
                          top_okpd2=[OkpdCount(okpd2=c, awarded_lots=n) for c, n in top])


def curated_roles(conn: Connection, inn: str) -> list[RoleItem]:
    """Accepted P3-002B decisions, evaluated exactly as the market-intelligence endpoint does (unchanged)."""
    catalog = CuratedEvidenceCatalog()
    out = []
    for code, seed in sorted(catalog.all().items()):
        if not any(c.supplier_inn == inn for c in seed.candidates):
            continue
        for c in build_external_expansion(conn, catalog, code).candidates:
            if c.supplier_inn != inn:
                continue
            role = _ROLE_OF_MARKET_ROLE.get(c.market_role, "UNKNOWN")
            status = c.verification_status if c.verification_status in ("VERIFIED", "UNDER_REVIEW") else "UNKNOWN"
            src = next((e for e in c.evidence_summary if e.source_url), None)
            out.append(RoleItem(role=role, status=status, basis=f"CURATED_EVIDENCE_POLICY:{code}",
                                claim=f"{c.why_candidate} (strength {c.verification_strength}; reasons "
                                      f"{', '.join(c.verification_reason_codes or c.review_reasons) or '—'})",
                                strength=c.verification_strength if c.verification_strength in ("STRONG", "MODERATE", "WEAK") else "WEAK",
                                source_url=src.source_url if src else None,
                                source_type=src.source_authority if src else "CURATED_EVIDENCE_SEED",
                                checked_at=src.retrieved_at if src else None, origin="CURATED_P3_002B"))
    return out


def build_profile(conn: Connection, inn: str, now: datetime, cache: str = "NONE") -> SupplierProfileResponse:
    validate_inn(inn)
    today = now.date()
    prof = R.get_profile(conn, inn)
    record = CE.load().get(inn)
    historical = is_historical(conn, inn)
    roles_cur = curated_roles(conn, inn)
    if prof is None and record is None and not historical and not roles_cur:
        raise SupplierNotFound(f"INN {inn} is neither a historical supplier nor a curated candidate")
    kids = R.children(conn, inn) if prof else {"contacts": [], "evidence": [], "roles": []}
    hist = history_summary(conn, inn) if historical else None

    # contacts: accepted P4-005C record first (its own freshness), then pipeline values not duplicating it
    contacts: list[ContactItem] = []
    cur_last, _, cur_status = record.freshness(today) if record else (None, None, None)
    if record:
        for k in ("website", "phone", "email", "address"):
            f = record.fields.get(k)
            if f:
                contacts.append(ContactItem(type=_CURATED_TYPES[k], value=f.value,
                                            label=(f.address_type or "").replace("_", " ").lower() or None,
                                            source_url=f.source_url, source_type=f.source_authority, checked_at=f.checked_at,
                                            freshness_status=cur_status, verified=True, origin="CURATED_P4_005C"))
    seen = curated_contact_keys(record)
    for c in kids["contacts"]:
        if (c["contact_type"], c["normalized_value"]) in seen:
            continue
        contacts.append(ContactItem(type=c["contact_type"], value=c["value"], label=c["label"], source_url=c["source_url"],
                                    source_type=c["source_type"], checked_at=c["checked_at"],
                                    freshness_status=F.contact_freshness(c["checked_at"], c["content_currency"], today),
                                    verified=c["verified"], origin="ENRICHMENT_PIPELINE"))

    roles = roles_cur + [RoleItem(role=r["role"], status=r["status"], basis=r["basis"], claim=r["claim"], strength=r["strength"],
                                  source_url=r["source_url"], source_type=r["source_type"], checked_at=r["checked_at"],
                                  origin="ENRICHMENT_PIPELINE") for r in kids["roles"]]
    if hist and hist.relevant_awards:
        roles.append(RoleItem(role="SUPPLIER", status="VERIFIED", basis="PROCUREMENT_HISTORY_AWARDS",
                              claim=f"{hist.relevant_awards} awarded supply relations in the organizer procurement data "
                                    f"({hist.first_observed_activity} – {hist.last_observed_activity}).",
                              strength="STRONG", source_type="ORGANIZER_PROCUREMENT_DATA", origin="PROCUREMENT_HISTORY"))

    p = prof or {}
    status = p.get("enrichment_status", "NOT_ENRICHED")
    ident_checked = p.get("identity_checked_at")
    # contact freshness: curated record status when present; otherwise the first-party page currency / registry recency
    pipe = [c for c in contacts if c.origin == "ENRICHMENT_PIPELINE"]
    if record and any(record.fields.values()):
        c_status, c_last, c_cur = cur_status, cur_last, record.content_currency
    elif any(c.type in ("PHONE", "EMAIL", "WEBSITE") for c in pipe):
        c_last = max(c.checked_at for c in pipe)
        c_status, c_cur = F.contact_freshness(c_last, p.get("content_currency"), today), p.get("content_currency")
    elif pipe:
        c_last = max(c.checked_at for c in pipe)
        c_status, c_cur = F.contact_freshness(c_last, F.CURRENT, today), F.CURRENT
    else:
        c_status, c_last, c_cur = "UNKNOWN", None, None
    last = p.get("last_enriched_at")

    sources: dict[tuple[str, str], SourceRef] = {}

    def add_src(url, stype, checked, use):
        if not url:
            return
        s = sources.setdefault((url, stype), SourceRef(source_url=url, source_type=stype, last_checked_at=checked, used_for=[]))
        if checked and (s.last_checked_at is None or checked > s.last_checked_at):
            s.last_checked_at = checked
        if use not in s.used_for:
            s.used_for.append(use)

    for e in kids["evidence"]:
        add_src(e["source_url"], e["source_type"], e["checked_at"], e["evidence_type"])
    for c in contacts:
        add_src(c.source_url, c.source_type, c.checked_at, f"CONTACT_{c.type}")
    for r in roles:
        add_src(r.source_url, r.source_type, r.checked_at, f"ROLE_{r.role}")
    if record:
        add_src(record.identity_source_url, "FNS_EGRUL_DERIVED_REGISTRY", cur_last, "CURATED_IDENTITY_BASIS")

    return SupplierProfileResponse(
        supplier=SupplierIdentity(inn=inn, entity_kind=p.get("entity_kind"),
                                  display_name=p.get("legal_name") or (record.company_name if record else None),
                                  legal_name=p.get("legal_name"), short_name=p.get("short_name"), legal_status=p.get("legal_status"),
                                  ogrn=p.get("ogrn"), kpp=p.get("kpp"), region=p.get("region"),
                                  registered_address=p.get("registered_address"), registration_date=p.get("registration_date"),
                                  primary_okved=p.get("primary_okved"), identity_source_url=p.get("identity_source_url"),
                                  identity_source_type=p.get("identity_source_type"), historically_known=historical),
        enrichment=EnrichmentState(status=status, reasons=list(p.get("status_reasons") or []), retryable=bool(p.get("retryable")),
                                   last_enriched_at=last, official_website=p.get("official_website"),
                                   website_confidence=p.get("website_confidence") or "NONE",
                                   website_candidate=p.get("website_candidate") if not p.get("official_website") else None,
                                   pipeline_version=p.get("pipeline_version"), cache=cache),
        contacts=contacts, roles=roles,
        evidence=[EvidenceItemOut(**{k: e[k] for k in ("evidence_type", "claim", "value", "source_url", "source_type", "checked_at",
                                                         "valid_until", "strength")}) for e in kids["evidence"]],
        freshness=FreshnessBlock(policy_version=F.POLICY.version, identity=F.identity_freshness(ident_checked, today),
                                 identity_checked_at=ident_checked, contacts=c_status, contacts_last_checked_at=c_last,
                                 content_currency=c_cur,
                                 profile_cache_valid_until=last + timedelta(days=F.POLICY.profile_ttl_days) if last else None),
        procurement_history_summary=hist, sources=sorted(sources.values(), key=lambda s: (s.source_type, s.source_url)),
        last_run_attempts=[AttemptOut(source=a["source"], outcome=a["outcome"], detail=a["detail"], duration_ms=a["duration_ms"])
                           for a in (R.last_attempts(conn, inn) if prof else [])])


def enrich_supplier(conn: Connection, inn: str, now: Callable[[], datetime] = utcnow, refresh: bool = False,
                    factory: ProvidersFactory | None = None) -> SupplierProfileResponse:
    """Cache-first, bounded, synchronous enrichment of one INN (per-request timeouts in HttpFetcher)."""
    validate_inn(inn)
    t = now()
    prof = R.get_profile(conn, inn)
    record = CE.load().get(inn)
    historical = is_historical(conn, inn)
    if prof is None and record is None and not historical:
        if not any(c.supplier_inn == inn for s in CuratedEvidenceCatalog().all().values() for c in s.candidates):
            raise SupplierNotFound(f"INN {inn} is neither a historical supplier nor a curated candidate")
    if prof is not None:
        reusable = F.cache_reusable(prof["enrichment_status"], prof["retryable"], prof["last_enriched_at"], prof["updated_at"], t)
        if prof["enrichment_status"] == "IN_PROGRESS" and reusable:
            return build_profile(conn, inn, t, cache="HIT")      # another run is active; never start a second one
        if reusable and not refresh:
            return build_profile(conn, inn, t, cache="HIT")
    R.mark_in_progress(conn, inn, t)
    providers, close = (factory or default_providers)(now)
    try:
        res = P.enrich(inn, providers, now)
    except Exception as e:  # a parser/provider bug must not leave the profile IN_PROGRESS
        res = P.EnrichmentResult(inn=inn, status=P.EnrichmentStatus.FAILED, reasons=["PIPELINE_ERROR"], retryable=True,
                                 started_at=t, finished_at=now(),
                                 attempts=[P.SourceAttempt("PIPELINE", P.SourceOutcome.UNAVAILABLE, f"{type(e).__name__}: {e}"[:200])])
    finally:
        close()
    R.save(conn, res, now(), skip_contact_keys=curated_contact_keys(record), historical=historical)
    return build_profile(conn, inn, now(), cache="REFRESHED" if prof is not None else "MISS")
