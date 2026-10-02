"""P4-005C source-backed contact enrichment: record validation, freshness semantics, serialization in supplier-search and
export, verification statuses untouched, lot-ID flow and P3 contract unchanged. Deterministic (fixed `today`)."""
from __future__ import annotations

import copy
import csv
import io
import json
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api import supplier_search as S
from app.api.main import app
from app.api.supplier_search_models import SupplierSearchRequest
from app.enrichment import contacts as CE
from app.shared.config import database_url, repo_root

MILK_CODE = "10.51.11.141"
SIX = {"7622012124", "0257011170", "5320000979", "5028002303", "5007126820", "3128004452"}
FILE = repo_root() / "data" / "seed" / "p4_005c_contact_enrichment.json"
DOC = json.loads(FILE.read_text(encoding="utf-8"))
TODAY = date(2026, 10, 2)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def milk():
    with psycopg.connect(database_url()) as conn:
        res = S.supplier_search(conn, SupplierSearchRequest(query="Молоко ультрапастеризованное 3.2%", okpd2=MILK_CODE), today=TODAY)
    return {x.supplier_inn: x for e in res.external_expansion if e.okpd2 == MILK_CODE for x in e.candidates}, res


# ---------------------------------------------------------------------------------------------------- record / validation
def test_record_covers_exactly_the_six_candidates():
    recs = CE.load()
    assert set(recs) == SIX
    for r in recs.values():
        for f in r.fields.values():
            if f:
                assert f.source_url.startswith("http") and f.checked_at.tzinfo and f.source_authority in CE.AUTHORITIES


def test_validation_rejects_unsourced_or_unknown_fields():
    bad = copy.deepcopy(DOC)
    del bad["contacts"][0]["fields"]["phone"]["source_url"]
    with pytest.raises(CE.ContactEnrichmentError, match="provenance"):
        CE.parse(bad)
    bad = copy.deepcopy(DOC)
    bad["contacts"][0]["fields"]["fax"] = None
    with pytest.raises(CE.ContactEnrichmentError, match="unsupported"):
        CE.parse(bad)
    bad = copy.deepcopy(DOC)
    bad["contacts"][0]["fields"]["email"]["source_authority"] = "RANDOM_DIRECTORY"
    with pytest.raises(CE.ContactEnrichmentError, match="source_authority"):
        CE.parse(bad)


def test_freshness_semantics():
    recs = CE.load()
    assert recs["0257011170"].freshness(TODAY)[2] == "FRESH"
    assert recs["0257011170"].freshness(date(2027, 10, 2))[2] == "STALE"        # check older than 180 days
    assert recs["5028002303"].freshness(TODAY)[2] == "STALE"                     # page itself outdated (2011/2012)
    assert recs["3128004452"].freshness(TODAY)[2] == "UNKNOWN"                   # undated page
    empty = CE.parse({"contacts": [{**DOC["contacts"][0], "fields": {"website": None, "email": None, "phone": None, "address": None}}]})
    assert empty["7622012124"].freshness(TODAY) == (None, None, "UNKNOWN")


# ---------------------------------------------------------------------------------------------------- serialization
def test_sourced_fields_serialize_with_provenance(milk):
    by_inn, _ = milk
    b = by_inn["0257011170"].contact
    assert (b.website, b.email, b.phone) == ("https://molloko.ru/", "hello@molloko.ru", "+7 (34784) 3-37-78")
    assert b.address.startswith("Россия, Республика Башкортостан, г. Бирск")
    assert set(b.sources) == {"website", "email", "phone", "address"}
    assert b.sources["email"].source_url == "https://molloko.ru/contacts/" and b.sources["email"].source_authority == "FIRST_PARTY"
    assert b.sources["address"].address_type == "PUBLISHED_COMPANY_ADDRESS"
    assert all(s.checked_at.isoformat() == "2026-10-02T03:55:00+03:00" for s in b.sources.values())
    assert b.freshness.status == "FRESH" and b.freshness.source_url == "https://molloko.ru/contacts/" and b.identity_basis
    assert by_inn["5028002303"].contact.freshness.status == "STALE"
    assert by_inn["3128004452"].contact.freshness.status == "UNKNOWN"


def test_missing_fields_remain_null(milk):
    by_inn, _ = milk
    a = by_inn["5007126820"].contact
    assert (a.phone, a.email, a.website) == (None, None, None) and set(a.sources) == {"address"}
    assert a.sources["address"].source_authority == "FNS_EGRUL_DERIVED_REGISTRY"
    assert a.sources["address"].address_type == "REGISTERED_LEGAL_ADDRESS"


def test_contact_enrichment_does_not_change_verification(client, milk):
    by_inn, _ = milk
    p3 = client.get(f"/api/v1/market-intelligence/{MILK_CODE}").json()["external_expansion"]["candidates"]
    assert {c["supplier_inn"]: c["verification_status"] for c in p3} == {i: x.verification_status for i, x in by_inn.items()}
    assert sorted(x.verification_status for x in by_inn.values()) == ["UNDER_REVIEW"] * 2 + ["VERIFIED"] * 4
    for c in p3:                                                       # the P3 candidate payload is identical apart from additions
        mine = by_inn[c["supplier_inn"]].model_dump(mode="json")
        assert {k: mine[k] for k in c} == c and "contact" not in c


def test_supplier_search_response_and_export_include_contacts(client):
    d = client.post("/api/v1/supplier-search", json={"query": "Молоко ультрапастеризованное 3.2%", "okpd2": MILK_CODE}).json()
    cands = {x["supplier_inn"]: x for e in d["external_expansion"] for x in e["candidates"]}
    assert set(cands) == SIX
    assert cands["7622012124"]["contact"]["email"] == "sales@pervozdannoe.ru"
    assert cands["7622012124"]["contact"]["sources"]["email"]["source_url"] == "https://pervozdannoe.ru/contact/"
    r = client.get(f"/api/v1/supplier-search/{d['search_id']}/export", params={"format": "csv"})
    rows = {x["inn"]: x for x in csv.DictReader(io.StringIO(r.text)) if x["record_type"] == "EXTERNAL_CANDIDATE"}
    assert rows["0257011170"]["email"] == "hello@molloko.ru" and rows["0257011170"]["phone"] == "+7 (34784) 3-37-78"
    assert rows["0257011170"]["contact_checked_at"] == "2026-10-02T03:55:00+03:00"
    assert "email=https://molloko.ru/contacts/ (FIRST_PARTY, 2026-10-02)" in rows["0257011170"]["contact_sources"]
    assert rows["5007126820"]["phone"] == "" and rows["5007126820"]["email"] == ""
    assert rows["5028002303"]["contact_freshness_status"] == "STALE"


def test_lot_flow_unchanged(client):
    a = client.get("/api/v1/procurements/5956101/analysis").json()
    assert a["availability"] == "COMPLETE" and a["recommendations"]["data"]["config_name"] == "P2_001_SEMANTIC"
    milk = next(e for e in a["market_intelligence"] if e["okpd2"] == MILK_CODE)["data"]["external_expansion"]
    assert (milk["verified_count"], milk["under_review_count"]) == (4, 2) and all("contact" not in c for c in milk["candidates"])
