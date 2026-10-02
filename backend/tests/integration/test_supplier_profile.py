"""P5-001A Supplier 360 persistence + API on the throwaway test database (migrated to head, incl. 0005).
Fake providers (no network), fixed clock. Covers persistence, cache reuse, explicit refresh, unknown suppliers, null contacts,
and that the accepted P4-005C contacts / P3-002B decisions are reused unchanged and never duplicated."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api import supplier_profile as SP
from app.api import supplier_profile_routes as routes
from app.api.main import app
from app.enrichment import contacts as CE
from app.enrichment import pipeline as P
from app.enrichment.providers import HtmlContactExtractor, RegistryWebsiteDiscovery, SiteAndOkvedRoleEvidence
from app.shared.ids import history_uuid, item_uuid, lot_uuid, supplier_uuid
from tests.enrichment.fakes import NOW, FakeRegistry, FakeVerifier, identity, site_pages

HIST = "7701234567"         # synthetic historical supplier (test DB only)
NO_SITE = "7701234568"
MOZH = "5028002303"         # curated P4-005C record with an OUTDATED page -> STALE
SIX = {"7622012124", "0257011170", "5320000979", "5028002303", "5007126820", "3128004452"}
SHA = "0" * 64


@pytest.fixture(scope="module")
def db(test_db_url):
    with psycopg.connect(test_db_url) as conn:
        for k, (inn, okpd2, d) in enumerate([(HIST, "10.51.11.141", date(2025, 3, 1)), (HIST, "10.51.11.141", date(2025, 6, 1)),
                                             (HIST, "10.51.52.110", date(2025, 9, 1)), (NO_SITE, "26.20.11.110", date(2024, 5, 5))]):
            lot = f"p5test{k}"
            conn.execute("""INSERT INTO procurement_lot (lot_id, id, procedure_id, publish_date, platform, is_smp, customer_inn,
                            start_price, has_supplier_history, source_sha256, source_row_no)
                            VALUES (%s, %s, %s, %s, 'AIS_GZ', false, '7800000000', 100, true, %s, %s) ON CONFLICT DO NOTHING""",
                         (lot, lot_uuid(lot), lot, d, SHA, 900000 + k))
            conn.execute("""INSERT INTO supplier (supplier_id, inn, entity_type, origin, first_seen_publish_date)
                            VALUES (%s, %s, 'legal_entity', 'ORGANIZER_DATA', %s) ON CONFLICT DO NOTHING""",
                         (supplier_uuid(inn), inn, d))
            conn.execute("""INSERT INTO supplier_history (id, lot_id, supplier_id, supplier_inn, is_winner, platform, publish_date,
                            coverage_semantics, source_sha256, source_row_nos)
                            VALUES (%s, %s, %s, %s, true, 'AIS_GZ', %s, 'WINNER_ROWS_ONLY_OBSERVED', %s, ARRAY[%s]) ON CONFLICT DO NOTHING""",
                         (history_uuid(lot, inn), lot, supplier_uuid(inn), inn, d, SHA, 900000 + k))
            parts = okpd2.split(".")
            conn.execute("""INSERT INTO procurement_item (item_id, lot_id, line_no, content_hash, product_name_raw, is_generic_type_name,
                            okpd2_code_raw, okpd2_code, okpd2_depth, okpd2_section, okpd2_class, source_sha256, source_row_no)
                            VALUES (%s, %s, 1, %s, 'Молоко', false, %s, %s, 4, 'C', %s, %s, %s) ON CONFLICT DO NOTHING""",
                         (item_uuid(lot, 1), lot, SHA, okpd2, okpd2, parts[0], SHA, 900000 + k))
        conn.commit()
    yield test_db_url


class Clock:
    def __init__(self):
        self.t = NOW

    def __call__(self):
        return self.t


def factory(registry_result, pages=None, calls=None):
    def make(now):
        if calls is not None:
            calls.append(1)
        return P.Providers(registries=[FakeRegistry("FNS_EGRUL", registry_result)], discovery=RegistryWebsiteDiscovery(),
                           verifier=FakeVerifier(pages or {}), extractor=HtmlContactExtractor(),
                           roles=SiteAndOkvedRoleEvidence()), (lambda: None)
    return make


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setattr(routes, "connect", lambda: psycopg.connect(db))
    monkeypatch.setattr(SP, "default_providers", factory(identity(HIST), site_pages(HIST)))
    with TestClient(app) as c:
        yield c


def test_inn_only_historical_supplier_is_enriched_and_persisted(db):
    calls, clk = [], Clock()
    with psycopg.connect(db) as conn:
        prof = SP.enrich_supplier(conn, HIST, clk, refresh=True, factory=factory(identity(HIST), site_pages(HIST), calls))
        assert prof.enrichment.status == "COMPLETE" and prof.enrichment.official_website == "https://moloko-test.ru/"
        assert prof.supplier.legal_name and prof.supplier.ogrn and prof.supplier.historically_known
        stored = conn.execute("SELECT enrichment_status, supplier_id FROM supplier_enrichment_profile WHERE inn = %s", (HIST,)).fetchone()
        assert stored == ("COMPLETE", supplier_uuid(HIST))
        assert conn.execute("SELECT count(*) FROM supplier_contact WHERE inn = %s", (HIST,)).fetchone()[0] == 4
    for c in prof.contacts:
        assert c.source_url.startswith("http") and c.source_type and c.checked_at and c.freshness_status in ("FRESH", "STALE", "UNKNOWN")
    assert {c.type for c in prof.contacts} == {"PHONE", "EMAIL", "WEBSITE", "ADDRESS"}
    h = prof.procurement_history_summary
    assert (h.observed_relations, h.relevant_awards, h.last_observed_activity) == (3, 3, date(2025, 9, 1))
    assert h.top_okpd2[0].okpd2 == "10.51.11.141" and h.top_okpd2[0].awarded_lots == 2
    roles = {(r.role, r.status, r.origin) for r in prof.roles}
    assert ("SUPPLIER", "VERIFIED", "PROCUREMENT_HISTORY") in roles
    assert ("MANUFACTURER", "INFERRED", "ENRICHMENT_PIPELINE") in roles
    assert not any(r.status == "VERIFIED" and r.origin == "ENRICHMENT_PIPELINE" for r in prof.roles)
    assert prof.freshness.identity == "FRESH" and prof.freshness.contacts == "FRESH"
    assert {s.source_type for s in prof.sources} >= {"FNS_EGRUL", "FIRST_PARTY", "FNS_EGRUL_DERIVED_REGISTRY"}


def test_cache_reuse_and_explicit_refresh(db):
    calls, clk = [], Clock()
    f = factory(identity(HIST), site_pages(HIST), calls)
    with psycopg.connect(db) as conn:
        SP.enrich_supplier(conn, HIST, clk, refresh=True, factory=f)
        assert len(calls) == 1
        clk.t = NOW + timedelta(days=5)
        assert SP.enrich_supplier(conn, HIST, clk, factory=f).enrichment.cache == "HIT" and len(calls) == 1
        assert SP.enrich_supplier(conn, HIST, clk, refresh=True, factory=f).enrichment.cache == "REFRESHED" and len(calls) == 2
        clk.t = NOW + timedelta(days=45)        # past the profile TTL -> re-queried without refresh
        SP.enrich_supplier(conn, HIST, clk, factory=f)
        assert len(calls) == 3
        # refresh contacts are a replacement snapshot, not appended duplicates
        assert conn.execute("SELECT count(*) FROM supplier_contact WHERE inn = %s", (HIST,)).fetchone()[0] == 4


def test_failed_refresh_keeps_previous_profile(db):
    with psycopg.connect(db) as conn:
        SP.enrich_supplier(conn, HIST, Clock(), refresh=True, factory=factory(identity(HIST), site_pages(HIST)))

        def down(now):
            return P.Providers([FakeRegistry("FNS_EGRUL", error=True)], RegistryWebsiteDiscovery(), FakeVerifier({}),
                               HtmlContactExtractor(), SiteAndOkvedRoleEvidence()), (lambda: None)
        prof = SP.enrich_supplier(conn, HIST, Clock(), refresh=True, factory=down)
        assert prof.enrichment.status == "COMPLETE" and "LAST_REFRESH_FAILED" in prof.enrichment.reasons
        assert any(a.outcome == "UNAVAILABLE" for a in prof.last_run_attempts)


def test_legal_identity_only_partial_and_missing_contacts_stay_absent(db):
    with psycopg.connect(db) as conn:
        prof = SP.enrich_supplier(conn, NO_SITE, Clock(), refresh=True, factory=factory(identity(NO_SITE, site=None)))
    assert prof.enrichment.status == "PARTIAL" and prof.enrichment.official_website is None
    assert [c.type for c in prof.contacts] == ["ADDRESS"]
    assert prof.enrichment.website_confidence == "NONE"


def test_rejected_website_is_not_official(db):
    other = site_pages("7709999999", "1027709999999")
    with psycopg.connect(db) as conn:
        prof = SP.enrich_supplier(conn, NO_SITE, Clock(), refresh=True, factory=factory(identity(NO_SITE), other))
    assert prof.enrichment.status == "PARTIAL" and prof.enrichment.official_website is None
    assert prof.enrichment.website_candidate == "https://moloko-test.ru" and prof.enrichment.website_confidence == "LOW"
    assert not any(c.type in ("PHONE", "EMAIL", "WEBSITE") for c in prof.contacts)


def test_api_get_and_post(client):
    r = client.post(f"/api/v1/suppliers/{HIST}/enrich", params={"refresh": "true"})
    assert r.status_code == 200 and r.json()["enrichment"]["status"] == "COMPLETE"
    g = client.get(f"/api/v1/suppliers/{HIST}/profile").json()
    assert set(g) >= {"supplier", "enrichment", "contacts", "roles", "freshness", "procurement_history_summary", "sources"}
    assert g["supplier"]["inn"] == HIST and g["enrichment"]["last_enriched_at"]
    assert client.get("/api/v1/suppliers/12345/profile").status_code == 422
    assert client.get("/api/v1/suppliers/7700000009/profile").json()["detail"]["code"] == "SUPPLIER_NOT_FOUND"
    assert client.post("/api/v1/suppliers/7700000009/enrich").status_code == 404


def test_get_never_triggers_enrichment(db, client, monkeypatch):
    def boom(now):
        raise AssertionError("GET must not call providers")
    monkeypatch.setattr(SP, "default_providers", boom)
    with psycopg.connect(db) as conn:
        conn.execute("DELETE FROM supplier_enrichment_profile WHERE inn = %s", (NO_SITE,))
        conn.commit()
    g = client.get(f"/api/v1/suppliers/{NO_SITE}/profile").json()
    assert g["enrichment"]["status"] == "NOT_ENRICHED" and g["contacts"] == [] and g["procurement_history_summary"]


# ------------------------------------------------------------------------------------------------------------ P4-005C / P3-002B
def test_curated_six_keep_contacts_and_decisions(db):
    records = CE.load()
    statuses = Counter()
    with psycopg.connect(db) as conn:
        for inn in sorted(SIX):
            prof = SP.build_profile(conn, inn, NOW)
            cur = [c for c in prof.contacts if c.origin == "CURATED_P4_005C"]
            fields = {k: f for k, f in records[inn].fields.items() if f}
            assert {c.value for c in cur} == {f.value for f in fields.values()}
            assert all(c.source_url == f.source_url for c in cur for f in fields.values() if f.value == c.value)
            statuses.update(r.status for r in prof.roles if r.origin == "CURATED_P3_002B")
    assert statuses == Counter({"VERIFIED": 4, "UNDER_REVIEW": 2})


def test_curated_stale_contacts_not_duplicated_by_pipeline(db):
    rec = CE.load()[MOZH]
    pages = {"http://mozhayskiy.ru/": f"<p>© 2011</p><a href='/Contact.html'>Контакты</a><p>ИНН {MOZH}</p>",
             "http://mozhayskiy.ru/Contact.html": "<p>Отдел продаж: <a href='tel:+74963821052'>+7-49638-21052</a> "
                                                 "<a href='mailto:sales@mozhayskiy.ru'>sales@mozhayskiy.ru</a></p>"}
    ident = identity(MOZH, site="http://mozhayskiy.ru/")
    with psycopg.connect(db) as conn:
        prof = SP.enrich_supplier(conn, MOZH, Clock(), refresh=True, factory=factory(ident, pages))
        stored = {r[0] for r in conn.execute("SELECT normalized_value FROM supplier_contact WHERE inn = %s", (MOZH,)).fetchall()}
    assert "sales@mozhayskiy.ru" not in stored and "74963821052" not in stored and "mozhayskiy.ru" not in stored
    cur = [c for c in prof.contacts if c.origin == "CURATED_P4_005C"]
    assert len(cur) == sum(1 for f in rec.fields.values() if f) and {c.freshness_status for c in cur} == {"STALE"}
    emails = [c.value for c in prof.contacts if c.type == "EMAIL"]
    assert emails.count("sales@mozhayskiy.ru") == 1
    assert prof.freshness.contacts == "STALE"
    assert Counter(r.status for r in prof.roles if r.origin == "CURATED_P3_002B") in (Counter({"VERIFIED": 1}),
                                                                                       Counter({"UNDER_REVIEW": 1}))
