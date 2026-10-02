"""P5-001A/P5-002A persistence of Supplier 360 enrichment (psycopg, plain SQL; tables from migrations 0005 + 0006)."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from psycopg import Connection
from psycopg.rows import dict_row

from app.enrichment.pipeline import PIPELINE_VERSION
from app.enrichment.profile_models import EnrichmentResult, EnrichmentStatus
from app.shared.ids import NAMESPACE, supplier_uuid


def _id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, "enrichment:" + hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest())


def get_profile(conn: Connection, inn: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute("SELECT * FROM supplier_enrichment_profile WHERE inn = %s", (inn,)).fetchone()


def children(conn: Connection, inn: str) -> dict[str, list[dict]]:
    with conn.cursor(row_factory=dict_row) as cur:
        return {
            "contacts": cur.execute("""SELECT * FROM supplier_contact WHERE inn = %s
                                       ORDER BY array_position(ARRAY['WEBSITE','PHONE','EMAIL','ADDRESS'], contact_type), checked_at, value""",
                                    (inn,)).fetchall(),
            "evidence": cur.execute("SELECT * FROM supplier_enrichment_evidence WHERE inn = %s ORDER BY evidence_type, claim",
                                    (inn,)).fetchall(),
            "roles": cur.execute("SELECT * FROM supplier_role_evidence WHERE inn = %s ORDER BY role, status, basis", (inn,)).fetchall(),
        }


def last_attempts(conn: Connection, inn: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute("""SELECT source, outcome, detail, duration_ms, run_started_at FROM supplier_enrichment_attempt
                              WHERE run_id = (SELECT run_id FROM supplier_enrichment_attempt WHERE inn = %s ORDER BY seq DESC LIMIT 1)
                              ORDER BY source, seq""", (inn,)).fetchall()


def mark_in_progress(conn: Connection, inn: str, now: datetime) -> None:
    """Only for a profile without usable data (new or FAILED); an existing COMPLETE/PARTIAL stays readable during a refresh."""
    conn.execute("""INSERT INTO supplier_enrichment_profile (inn, enrichment_status, pipeline_version, created_at, updated_at)
                    VALUES (%s, 'IN_PROGRESS', %s, %s, %s)
                    ON CONFLICT (inn) DO UPDATE SET enrichment_status = 'IN_PROGRESS', updated_at = EXCLUDED.updated_at
                    WHERE supplier_enrichment_profile.enrichment_status NOT IN ('COMPLETE', 'PARTIAL')""",
                 (inn, PIPELINE_VERSION, now, now))
    conn.commit()


def save_attempts(conn: Connection, res: EnrichmentResult) -> None:
    """Append the run's attempts. Log rows are events, not entities: random ids, one run_id per run (two runs may share a
    start timestamp, e.g. under a fixed clock or a fast refresh)."""
    run_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO supplier_enrichment_attempt (id, run_id, inn, run_started_at, source, outcome, detail, duration_ms)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(uuid.uuid4(), run_id, res.inn, res.started_at, a.source, a.outcome.value, a.detail, a.duration_ms)
                         for a in res.attempts])


IDENTITY_COLUMNS = ("entity_kind", "legal_name", "short_name", "ogrn", "kpp", "legal_status", "registration_date",
                    "registered_address", "primary_okved", "region", "identity_source_url", "identity_source_type",
                    "identity_checked_at")
WEBSITE_COLUMNS = ("official_website", "website_confidence", "website_candidate", "website_checked_at", "content_currency",
                   "website_verification_status", "website_signals", "website_discovered_via")
_WEBSITE_GAP_REASONS = {"NO_WEBSITE_CANDIDATE", "WEBSITE_UNAVAILABLE", "NO_PUBLIC_PHONE_OR_EMAIL_ON_OFFICIAL_SITE"}
FIRST_PARTY = "FIRST_PARTY"


def _profile_values(res: EnrichmentResult, historical: bool) -> dict:
    i, w = res.identity, res.website

    def v(x):
        return x.value if x else None

    ln = i.legal_name if i else None
    return {"entity_kind": i.entity_kind if i else None, "legal_name": v(ln), "short_name": v(i.short_name) if i else None,
            "ogrn": v(i.ogrn) if i else None, "kpp": v(i.kpp) if i else None, "legal_status": v(i.legal_status) if i else None,
            "registration_date": i.registration_date if i else None, "registered_address": v(i.registered_address) if i else None,
            "primary_okved": v(i.primary_okved) if i else None, "region": v(i.region) if i else None,
            "identity_source_url": ln.source_url if ln else None, "identity_source_type": ln.source_type.value if ln else None,
            "identity_checked_at": ln.checked_at if ln else None,
            "official_website": w.official_url if w else None, "website_confidence": w.confidence.value if w else "NONE",
            "website_candidate": w.candidate_url if w else None, "website_checked_at": w.checked_at if w else None,
            "content_currency": res.content_currency, "supplier_id": supplier_uuid(res.inn) if historical else None,
            "website_verification_status": w.verification_status.value if w else None,
            "website_signals": list(w.signals) if w else [], "website_discovered_via": w.provider if w else None}


def last_website_checks(conn: Connection, inn: str, limit: int = 10) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute("""SELECT checked_at, candidate_url, official_url, discovered_via, verification_status, signals, reason
                              FROM supplier_website_check WHERE inn = %s ORDER BY seq DESC LIMIT %s""", (inn, limit)).fetchall()


def save_website_checks(conn: Connection, res: EnrichmentResult) -> None:
    """Append every candidate checked in this run (evidence history; never updated, never deleted by a refresh)."""
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO supplier_website_check (id, inn, checked_at, candidate_url, official_url, discovered_via,
                               verification_status, signals, reason, pipeline_version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(uuid.uuid4(), res.inn, v.checked_at or res.started_at, v.candidate_url, v.official_url, v.provider,
                          v.verification_status.value, list(v.signals), v.reason, PIPELINE_VERSION) for v in res.website_checks])


def save(conn: Connection, res: EnrichmentResult, now: datetime, skip_contact_keys: set[tuple[str, str]] = frozenset(),
         historical: bool = True) -> str:
    """Persist one run with weak-refresh protection: a refresh never lowers the stored verified information.

    - FAILED refresh over a usable profile: nothing but the attempt log and a LAST_REFRESH_FAILED reason is written.
    - Legal identity: a new non-empty value updates the field; an empty one never erases a stored value.
    - Official website + every first-party row (contacts, evidence, roles): kept when this run did not check a website
      (mirror outage, site unreachable, no candidate); replaced when it did (a re-check that no longer confirms the site is
      genuinely newer evidence).
    - Registry rows (address contact, OKVED evidence / role): replaced per kind only when this run produced that kind.
    Anything kept is reported as LAST_REFRESH_DEGRADED. Status is recomputed from the merged snapshot.
    Contacts already present in the accepted P4-005C record (same type + normalized value) are not duplicated.
    Returns the stored enrichment_status."""
    existing = get_profile(conn, res.inn)
    save_attempts(conn, res)
    save_website_checks(conn, res)
    usable = existing is not None and existing["enrichment_status"] in ("COMPLETE", "PARTIAL")
    if res.status == EnrichmentStatus.FAILED and usable:
        conn.execute("UPDATE supplier_enrichment_profile SET status_reasons = %s, updated_at = %s WHERE inn = %s",
                     (sorted(set(existing["status_reasons"]) | {"LAST_REFRESH_FAILED"} | set(res.reasons)), now, res.inn))
        conn.commit()
        return existing["enrichment_status"]

    vals = _profile_values(res, historical)
    reasons, degraded = set(res.reasons), False
    old = children(conn, res.inn) if usable else {"contacts": [], "evidence": [], "roles": []}
    if usable:
        for col in IDENTITY_COLUMNS:
            if vals[col] is None and existing[col] is not None:
                vals[col], degraded = existing[col], True
    # P5-002A website change protection: a verified official site is replaced only when it was re-checked this run and failed
    # (or re-verified, which refreshes it); a run that did not re-check it never lowers it.
    keep_site = bool(usable and existing["official_website"]
                     and (res.website is None or (res.website.official_url is None and not res.prior_site_rechecked)))
    if keep_site:
        vals.update({col: existing[col] for col in WEBSITE_COLUMNS})
        reasons = (reasons - _WEBSITE_GAP_REASONS) | {"WEBSITE_KEPT_FROM_PREVIOUS_RUN"}
        degraded = True

    contacts, seen = [], set()
    for c in res.contacts:
        key = (c.type.value, c.normalized)
        if key in skip_contact_keys or key in seen:
            continue
        seen.add(key)
        contacts.append(c)
    new_registry_contact_types = {c.type.value for c in contacts if c.source_type.value != FIRST_PARTY}
    new_registry_evidence_types = {e.evidence_type for e in res.evidence if e.source_type.value != FIRST_PARTY}
    has_okved = vals["primary_okved"] is not None and res.identity is not None and res.identity.primary_okved is not None

    def kept(row: dict, kind: str) -> bool:
        if row["source_type"] == FIRST_PARTY:
            return keep_site
        if kind == "contacts":
            return row["contact_type"] not in new_registry_contact_types
        if kind == "evidence":
            return row["evidence_type"] not in new_registry_evidence_types
        return row["basis"] == "OKVED_PRIMARY" and not has_okved          # roles

    keep_ids = {kind: [r["id"] for r in rows if kept(r, kind)] for kind, rows in old.items()}
    if any(keep_ids.values()):
        degraded = True
    for kind, table in (("contacts", "supplier_contact"), ("evidence", "supplier_enrichment_evidence"),
                        ("roles", "supplier_role_evidence")):
        conn.execute(f"DELETE FROM {table} WHERE inn = %s AND NOT (id = ANY(%s))", (res.inn, keep_ids[kind]))
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO supplier_contact (id, inn, contact_type, value, normalized_value, label, source_url, source_type,
                               checked_at, content_currency, verified, verification_basis)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""",
                        [(_id("contact", res.inn, c.type.value, c.normalized), res.inn, c.type.value, c.value, c.normalized, c.label,
                          c.source_url, c.source_type.value, c.checked_at, c.content_currency, c.verified, c.verification_basis)
                         for c in contacts])
        cur.executemany("""INSERT INTO supplier_enrichment_evidence (id, inn, evidence_type, claim, value, source_url, source_type,
                               checked_at, valid_until, strength) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""",
                        [(_id("evidence", res.inn, str(k), e.evidence_type, e.claim), res.inn, e.evidence_type, e.claim, e.value,
                          e.source_url, e.source_type.value, e.checked_at, e.valid_until, e.strength.value)
                         for k, e in enumerate(res.evidence)])
        cur.executemany("""INSERT INTO supplier_role_evidence (id, inn, role, status, basis, claim, source_url, source_type,
                               checked_at, strength) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""",
                        [(_id("role", res.inn, str(k), r.role.value, r.basis), res.inn, r.role.value, r.status.value, r.basis,
                          r.claim, r.source_url, r.source_type, r.checked_at, r.strength.value) for k, r in enumerate(res.roles)])

    status = res.status.value
    if res.status != EnrichmentStatus.FAILED:
        # reach counts this run's contacts (incl. those not stored because the curated record already has them) + kept ones
        kept_ids = set(keep_ids["contacts"])
        reach = any(c.type.value in ("PHONE", "EMAIL") for c in res.contacts) or any(
            r["contact_type"] in ("PHONE", "EMAIL") for r in old["contacts"] if r["id"] in kept_ids)
        status = "COMPLETE" if vals["official_website"] and reach else "PARTIAL"
        if vals["official_website"] and not reach:
            reasons.add("NO_PUBLIC_PHONE_OR_EMAIL_ON_OFFICIAL_SITE")
    if degraded:
        reasons.add("LAST_REFRESH_DEGRADED")
    vals.update({"inn": res.inn, "enrichment_status": status, "status_reasons": sorted(reasons), "retryable": res.retryable,
                 "pipeline_version": PIPELINE_VERSION, "duration_ms": res.duration_ms,
                 "last_enriched_at": res.finished_at if res.status != EnrichmentStatus.FAILED else None,
                 "created_at": now, "updated_at": now})
    cols = list(vals)
    conn.execute(f"""INSERT INTO supplier_enrichment_profile ({", ".join(cols)}) VALUES ({", ".join(f"%({c})s" for c in cols)})
                     ON CONFLICT (inn) DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c not in ("inn", "created_at"))}""",
                 vals)
    conn.commit()
    return status
