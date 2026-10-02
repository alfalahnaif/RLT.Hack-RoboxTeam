"""P5-002A persistence on the throwaway test database (migrated to head, incl. 0006): website verification status / signals,
contact verification basis, append-only website-check history, website change protection, and the profile API fields.
Fake providers (no network); synthetic INN used only by this module."""
from __future__ import annotations

from datetime import date, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api import supplier_profile as SP
from app.api import supplier_profile_routes as routes
from app.api.main import app
from app.enrichment import pipeline as P
from app.enrichment.providers import HtmlContactExtractor, RegistryWebsiteDiscovery, SiteAndOkvedRoleEvidence
from app.shared.ids import history_uuid, lot_uuid, supplier_uuid
from tests.enrichment.fakes import NOW, FakeRegistry, FakeVerifier, identity, site_pages

INN = "7701234599"
SHA = "0" * 64


@pytest.fixture(scope="module")
def db(test_db_url):
    with psycopg.connect(test_db_url) as conn:
        lot, d = "p5002a-lot", date(2025, 4, 1)
        conn.execute("""INSERT INTO procurement_lot (lot_id, id, procedure_id, publish_date, platform, is_smp, customer_inn,
                        start_price, has_supplier_history, source_sha256, source_row_no)
                        VALUES (%s, %s, %s, %s, 'AIS_GZ', false, '7800000000', 100, true, %s, 990001) ON CONFLICT DO NOTHING""",
                     (lot, lot_uuid(lot), lot, d, SHA))
        conn.execute("""INSERT INTO supplier (supplier_id, inn, entity_type, origin, first_seen_publish_date)
                        VALUES (%s, %s, 'legal_entity', 'ORGANIZER_DATA', %s) ON CONFLICT DO NOTHING""", (supplier_uuid(INN), INN, d))
        conn.execute("""INSERT INTO supplier_history (id, lot_id, supplier_id, supplier_inn, is_winner, platform, publish_date,
                        coverage_semantics, source_sha256, source_row_nos)
                        VALUES (%s, %s, %s, %s, true, 'AIS_GZ', %s, 'WINNER_ROWS_ONLY_OBSERVED', %s, ARRAY[990001]) ON CONFLICT DO NOTHING""",
                     (history_uuid(lot, INN), lot, supplier_uuid(INN), INN, d, SHA))
        conn.commit()
    yield test_db_url


class Clock:
    def __init__(self):
        self.t = NOW

    def __call__(self):
        return self.t


def make_factory(pages=None, site_error=False):
    def make(now):
        return P.Providers(registries=[FakeRegistry("FNS_EGRUL", identity(INN))], discovery=RegistryWebsiteDiscovery(),
                           verifier=FakeVerifier(pages or {}, site_error), extractor=HtmlContactExtractor(),
                           roles=SiteAndOkvedRoleEvidence()), (lambda: None)
    return make


def checks(conn):
    return conn.execute("SELECT verification_status, candidate_url FROM supplier_website_check WHERE inn = %s ORDER BY seq",
                        (INN,)).fetchall()


def test_discovery_columns_basis_history_and_protection(db):
    clk = Clock()
    with psycopg.connect(db) as conn:
        # 1. first run: the site is verified by INN on the site
        out = SP.enrich_supplier(conn, INN, clk, factory=make_factory(site_pages(INN)))
        assert out.enrichment.official_website == "https://moloko-test.ru/"
        wv = out.enrichment.website_verification
        assert wv.status == "VERIFIED_STRONG" and "INN_ON_SITE" in wv.signals
        bases = {c.type: c.verification_basis for c in out.contacts}
        assert bases["ADDRESS"] == "FNS_EGRUL_EXTRACT" and bases["PHONE"].startswith("OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE")
        assert [r[0] for r in checks(conn)] == ["VERIFIED_STRONG"]
        assert out.website_checks[0].status == "VERIFIED_STRONG"

        # 2. refresh while the stored site is unreachable: kept (protection), nothing else replaces it
        clk.t = NOW + timedelta(days=40)
        out = SP.enrich_supplier(conn, INN, clk, refresh=True, factory=make_factory(site_pages(INN), site_error=True))
        assert out.enrichment.official_website == "https://moloko-test.ru/"
        assert "WEBSITE_KEPT_FROM_PREVIOUS_RUN" in out.enrichment.reasons
        assert any(c.type == "PHONE" for c in out.contacts)                  # verified phone not lowered either
        assert len(checks(conn)) == 1                                         # nothing was checked -> no history row

        # 3. refresh where the stored site is re-checked and no longer shows the identity: replaced (cleared)
        clk.t = NOW + timedelta(days=80)
        out = SP.enrich_supplier(conn, INN, clk, refresh=True, factory=make_factory(site_pages(INN, with_requisites=False)))
        assert out.enrichment.official_website is None
        assert "STORED_WEBSITE_FAILED_RECHECK" in out.enrichment.reasons
        assert not any(c.type in ("PHONE", "WEBSITE") for c in out.contacts)
        assert [r[0] for r in checks(conn)] == ["VERIFIED_STRONG", "REJECTED"]  # append-only evidence history


def test_profile_api_exposes_new_fields(db, monkeypatch):
    monkeypatch.setattr(routes, "connect", lambda: psycopg.connect(db))
    with TestClient(app) as c:
        body = c.get(f"/api/v1/suppliers/{INN}/profile").json()
    assert "website_checks" in body and body["website_checks"][0]["status"] in ("VERIFIED_STRONG", "REJECTED")
    assert all("verification_basis" in x for x in body["contacts"])
    assert "website_verification" in body["enrichment"]
