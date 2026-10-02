"""P5-001A persistence of Supplier 360 enrichment (psycopg, plain SQL; tables from migration 0005)."""
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
                              WHERE inn = %s AND run_started_at = (SELECT max(run_started_at) FROM supplier_enrichment_attempt WHERE inn = %s)
                              ORDER BY source""", (inn, inn)).fetchall()


def mark_in_progress(conn: Connection, inn: str, now: datetime) -> None:
    """Only for a profile without usable data (new or FAILED); an existing COMPLETE/PARTIAL stays readable during a refresh."""
    conn.execute("""INSERT INTO supplier_enrichment_profile (inn, enrichment_status, pipeline_version, created_at, updated_at)
                    VALUES (%s, 'IN_PROGRESS', %s, %s, %s)
                    ON CONFLICT (inn) DO UPDATE SET enrichment_status = 'IN_PROGRESS', updated_at = EXCLUDED.updated_at
                    WHERE supplier_enrichment_profile.enrichment_status NOT IN ('COMPLETE', 'PARTIAL')""",
                 (inn, PIPELINE_VERSION, now, now))
    conn.commit()


def save_attempts(conn: Connection, res: EnrichmentResult) -> None:
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO supplier_enrichment_attempt (id, inn, run_started_at, source, outcome, detail, duration_ms)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        [(_id("attempt", res.inn, res.started_at.isoformat(), str(i), a.source), res.inn, res.started_at, a.source,
                          a.outcome.value, a.detail, a.duration_ms) for i, a in enumerate(res.attempts)])


def save(conn: Connection, res: EnrichmentResult, now: datetime, skip_contact_keys: set[tuple[str, str]] = frozenset(),
         historical: bool = True) -> str:
    """Persist one run. A FAILED refresh never overwrites a previously usable profile (only the attempt log is added).
    Contacts already present in the accepted P4-005C record (same type + normalized value) are not duplicated.
    Returns the stored enrichment_status."""
    existing = get_profile(conn, res.inn)
    save_attempts(conn, res)
    if res.status == EnrichmentStatus.FAILED and existing and existing["enrichment_status"] in ("COMPLETE", "PARTIAL"):
        conn.execute("UPDATE supplier_enrichment_profile SET status_reasons = %s, updated_at = %s WHERE inn = %s",
                     (sorted(set(existing["status_reasons"]) | {"LAST_REFRESH_FAILED"} | set(res.reasons)), now, res.inn))
        conn.commit()
        return existing["enrichment_status"]
    i, w = res.identity, res.website

    def v(x):
        return x.value if x else None

    ln = i.legal_name if i else None
    conn.execute("""
        INSERT INTO supplier_enrichment_profile (inn, supplier_id, entity_kind, legal_name, short_name, ogrn, kpp, legal_status,
            registration_date, registered_address, primary_okved, region, identity_source_url, identity_source_type,
            identity_checked_at, official_website, website_confidence, website_candidate, website_checked_at, content_currency,
            enrichment_status, status_reasons, retryable, pipeline_version, duration_ms, last_enriched_at, created_at, updated_at)
        VALUES (%(inn)s, %(sid)s, %(kind)s, %(ln)s, %(sn)s, %(ogrn)s, %(kpp)s, %(ls)s, %(rd)s, %(addr)s, %(okved)s, %(region)s,
            %(isrc)s, %(itype)s, %(ichk)s, %(site)s, %(wconf)s, %(wcand)s, %(wchk)s, %(cur)s, %(st)s, %(reasons)s, %(retry)s,
            %(pv)s, %(dur)s, %(last)s, %(now)s, %(now)s)
        ON CONFLICT (inn) DO UPDATE SET supplier_id = EXCLUDED.supplier_id, entity_kind = EXCLUDED.entity_kind,
            legal_name = EXCLUDED.legal_name, short_name = EXCLUDED.short_name, ogrn = EXCLUDED.ogrn, kpp = EXCLUDED.kpp,
            legal_status = EXCLUDED.legal_status, registration_date = EXCLUDED.registration_date,
            registered_address = EXCLUDED.registered_address, primary_okved = EXCLUDED.primary_okved, region = EXCLUDED.region,
            identity_source_url = EXCLUDED.identity_source_url, identity_source_type = EXCLUDED.identity_source_type,
            identity_checked_at = EXCLUDED.identity_checked_at, official_website = EXCLUDED.official_website,
            website_confidence = EXCLUDED.website_confidence, website_candidate = EXCLUDED.website_candidate,
            website_checked_at = EXCLUDED.website_checked_at, content_currency = EXCLUDED.content_currency,
            enrichment_status = EXCLUDED.enrichment_status, status_reasons = EXCLUDED.status_reasons,
            retryable = EXCLUDED.retryable, pipeline_version = EXCLUDED.pipeline_version, duration_ms = EXCLUDED.duration_ms,
            last_enriched_at = EXCLUDED.last_enriched_at, updated_at = EXCLUDED.updated_at""",
                 {"inn": res.inn, "sid": supplier_uuid(res.inn) if historical else None, "kind": i.entity_kind if i else None,
                  "ln": v(ln), "sn": v(i.short_name) if i else None, "ogrn": v(i.ogrn) if i else None,
                  "kpp": v(i.kpp) if i else None, "ls": v(i.legal_status) if i else None,
                  "rd": i.registration_date if i else None, "addr": v(i.registered_address) if i else None,
                  "okved": v(i.primary_okved) if i else None, "region": v(i.region) if i else None,
                  "isrc": ln.source_url if ln else None, "itype": ln.source_type.value if ln else None,
                  "ichk": ln.checked_at if ln else None, "site": w.official_url if w else None,
                  "wconf": w.confidence.value if w else "NONE", "wcand": w.candidate_url if w else None,
                  "wchk": w.checked_at if w else None, "cur": res.content_currency, "st": res.status.value,
                  "reasons": sorted(set(res.reasons)), "retry": res.retryable, "pv": PIPELINE_VERSION, "dur": res.duration_ms,
                  "last": res.finished_at if res.status != EnrichmentStatus.FAILED else None, "now": now})
    for table in ("supplier_contact", "supplier_enrichment_evidence", "supplier_role_evidence"):
        conn.execute(f"DELETE FROM {table} WHERE inn = %s", (res.inn,))   # one snapshot per INN; refresh replaces it
    with conn.cursor() as cur:
        rows, seen = [], set()
        for c in res.contacts:
            key = (c.type.value, c.normalized)
            if key in skip_contact_keys or key in seen:
                continue
            seen.add(key)
            rows.append((_id("contact", res.inn, *key), res.inn, c.type.value, c.value, c.normalized, c.label, c.source_url,
                         c.source_type.value, c.checked_at, c.content_currency, c.verified))
        cur.executemany("""INSERT INTO supplier_contact (id, inn, contact_type, value, normalized_value, label, source_url, source_type,
                               checked_at, content_currency, verified) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", rows)
        cur.executemany("""INSERT INTO supplier_enrichment_evidence (id, inn, evidence_type, claim, value, source_url, source_type,
                               checked_at, valid_until, strength) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(_id("evidence", res.inn, str(k), e.evidence_type, e.claim), res.inn, e.evidence_type, e.claim, e.value,
                          e.source_url, e.source_type.value, e.checked_at, e.valid_until, e.strength.value)
                         for k, e in enumerate(res.evidence)])
        cur.executemany("""INSERT INTO supplier_role_evidence (id, inn, role, status, basis, claim, source_url, source_type,
                               checked_at, strength) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(_id("role", res.inn, str(k), r.role.value, r.basis), res.inn, r.role.value, r.status.value, r.basis,
                          r.claim, r.source_url, r.source_type, r.checked_at, r.strength.value) for k, r in enumerate(res.roles)])
    conn.commit()
    return res.status.value
