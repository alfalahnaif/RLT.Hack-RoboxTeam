"""P4-005A free-text supplier discovery: classification cases, contact/freshness contract, export, determinism, old endpoints.
Read-only against the canonical database (like the P3-002C / P4-001 API tests)."""
from __future__ import annotations

import csv
import io
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api import supplier_search as S
from app.api.main import app
from app.api.supplier_search_models import SupplierSearchRequest
from app.search.models import DEFAULT_CONFIG
from app.shared.config import database_url

MILK_TEXT = "Молоко ультрапастеризованное 3.2%"
MILK_CODE = "10.51.11.141"
LAPTOP_CODE = "26.20.11.110"
UNSEEN_CODE = "10.51.11.999"
PRICE_REASON = "Comparable supplier-level pricing is not available in the current dataset."


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def post(client, **body):
    r = client.post("/api/v1/supplier-search", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _strip(d):
    if isinstance(d, dict):
        return {k: _strip(v) for k, v in d.items() if k != "timings_ms"}
    if isinstance(d, list):
        return [_strip(x) for x in d]
    return d


def test_text_only_search(client):
    d = post(client, query=MILK_TEXT)
    c = d["classification"]
    assert c["provided_okpd2"] is None and c["text_okpd2_alignment"] is None
    assert c["suggested_okpd2"] and c["suggested_okpd2"][0]["okpd2"].startswith("10.51.11")
    assert c["history_status"] in ("SUFFICIENT", "SPARSE", "NONE") and c["history"]["okpd2"] == c["suggested_okpd2"][0]["okpd2"]
    assert d["query"]["as_of"] == "2026-01-01" and d["query"]["okpd2"] is None
    assert [s["rank"] for s in d["suppliers"]] == list(range(1, len(d["suppliers"]) + 1)) and len(d["suppliers"]) <= 20
    assert all(s["reasons"] and not any(r.startswith("semantically similar") for r in s["reasons"]) for s in d["suppliers"])
    assert d["price_intelligence"] == {"available": False, "reason": PRICE_REASON}
    assert d["integration"]["export_available"] and d["integration"]["export_url"].endswith(f"/{d['search_id']}/export")
    assert [p["source"] for p in d["pool_health"]] == ["SUGGESTED"]


def test_rare_official_term_resolves_to_exact_observed_code_and_suppliers(client):
    d = post(client, query="Асфальтиты")
    c = d["classification"]
    assert c["category_state"] == "RESOLVED"
    assert c["suggested_okpd2"][0]["okpd2"] == "08.99.10.120"
    assert c["suggested_okpd2"][0]["basis"] == "EXACT_TERM"
    assert c["suggested_okpd2"][0]["confidence"] >= 0.9
    assert c["ranking_okpd2"] == "08.99.10.120"
    with psycopg.connect(database_url()) as conn:
        actual = {str(row[0]) for row in conn.execute("""
            SELECT DISTINCT h.supplier_id FROM supplier_history h
            JOIN procurement_item i ON i.lot_id = h.lot_id
            WHERE i.okpd2_code = '08.99.10.120'""")}
    assert actual and {s["supplier_id"] for s in d["suppliers"]} == actual
    assert all(s["historical_evidence"]["best_okpd2"] == "08.99.10.120" for s in d["suppliers"])


def test_generic_term_keeps_category_uncertain(client):
    d = post(client, query="Асфальт")
    assert d["classification"]["category_state"] == "CATEGORY_UNCERTAIN"
    assert d["classification"]["ranking_okpd2"] is None
    assert any(w.startswith("CATEGORY_UNCERTAIN") for w in d["classification"]["warnings"])
    assert not d["pool_health"]  # no concentration claim for an unconfirmed category


def test_text_with_aligned_okpd2_uses_code_and_returns_external_candidates(client):
    d = post(client, query=MILK_TEXT, okpd2=MILK_CODE)
    c = d["classification"]
    assert c["provided_okpd2"] == MILK_CODE and c["ranking_okpd2"] == MILK_CODE
    assert c["text_okpd2_alignment"] == "ALIGNED" and c["history_status"] == "SUFFICIENT"
    pool = {p["okpd2"]: p for p in d["pool_health"]}
    assert pool[MILK_CODE]["source"] == "PROVIDED" and pool[MILK_CODE]["pool_health"]["status"] == "VERY_HIGH"
    assert pool[MILK_CODE]["concentration"]["signal"] == "EXPANSION_RECOMMENDED"
    ext = next(x for x in d["external_expansion"] if x["okpd2"] == MILK_CODE)
    assert ext["available"] and (ext["verified_count"], ext["under_review_count"]) == (4, 2)
    assert all(x["reconciliation_status"] == "EXTERNAL_NEW" and x["exact_okpd2_asserted_by_source"] is False for x in ext["candidates"])


def test_sparse_okpd2_is_reported(client):
    with psycopg.connect(database_url()) as conn:
        code, name = conn.execute("""SELECT okpd2_code, min(product_name_normalized) FROM procurement_item
            WHERE okpd2_code IS NOT NULL AND product_name_normalized IS NOT NULL AND length(product_name_normalized) > 5
            GROUP BY okpd2_code HAVING count(DISTINCT lot_id) BETWEEN 2 AND 5 ORDER BY okpd2_code LIMIT 1""").fetchone()
    d = post(client, query=name, okpd2=code)
    c = d["classification"]
    assert c["provided_okpd2"] == code and c["history"]["okpd2"] == code and c["history_status"] == "SPARSE"
    assert any(w.startswith("OKPD2_HISTORY_SPARSE") for w in c["warnings"])
    assert d["suppliers"]                                              # text / semantic evidence still ranks suppliers


def test_unseen_okpd2_preserved_with_text_ranking(client):
    d = post(client, query="Молоко питьевое", okpd2=UNSEEN_CODE)
    c = d["classification"]
    assert c["provided_okpd2"] == UNSEEN_CODE and c["history_status"] == "NONE" and c["ranking_okpd2"] is None
    assert any(w.startswith("OKPD2_NOT_OBSERVED") for w in c["warnings"])
    provided = next(p for p in d["pool_health"] if p["source"] == "PROVIDED")
    assert provided["okpd2"] == UNSEEN_CODE and provided["status"] == "UNAVAILABLE" and provided["error"]["code"] == "CATEGORY_NOT_OBSERVED"
    assert c["category_state"] == "CATEGORY_UNCERTAIN"
    assert any(w.startswith("CATEGORY_UNCERTAIN") for w in c["warnings"])
    assert d["suppliers"] and any(x["okpd2"] == UNSEEN_CODE for x in d["external_expansion"])


def test_mismatch_keeps_supplied_code_but_ranks_by_resolved_text_category(client):
    d = post(client, query=MILK_TEXT, okpd2=LAPTOP_CODE)
    c = d["classification"]
    assert c["provided_okpd2"] == LAPTOP_CODE and c["text_okpd2_alignment"] == "MISMATCH"
    assert c["ranking_okpd2"] == "10.51.11.121" and c["suggested_okpd2"][0]["okpd2"].startswith("10.51")
    assert any(w.startswith("OKPD2_TEXT_MISMATCH") for w in c["warnings"])
    assert any(p["okpd2"] == LAPTOP_CODE and p["source"] == "PROVIDED" for p in d["pool_health"])
    text_only = post(client, query=MILK_TEXT)
    assert [s["supplier_id"] for s in d["suppliers"]] == [s["supplier_id"] for s in text_only["suppliers"]]


def test_technical_tokens_are_kept(client):
    d = post(client, query="Ноутбук Acer Aspire 5 A515-57-50R7")
    assert "a515-57-50r7" in d["query"]["technical_tokens"]
    assert d["classification"]["suggested_okpd2"][0]["okpd2"] == LAPTOP_CODE
    assert any("a515-57-50r7" in (p or "") for p in d["suppliers"][0]["historical_evidence"]["best_products"])


def test_no_contact_is_never_invented(client):
    d = post(client, query=MILK_TEXT, okpd2=MILK_CODE)
    for s_ in d["suppliers"]:                                          # historical suppliers: no curated profile / contact record
        assert s_["company_name"] is None and s_["role"] is None and s_["role_evidence_status"] == "NO_EVIDENCE"
        assert s_["contact"] is None and s_["freshness"] is None
    cands = [x for e in d["external_expansion"] for x in e["candidates"]]
    for x in cands:                                                    # every populated contact field has its own source
        populated = {k for k in ("phone", "email", "website", "address") if x["contact"][k] is not None}
        assert populated == set(x["contact"]["sources"])
    aap = next(x for x in cands if x["supplier_inn"] == "5007126820")  # no company website exists: nothing invented
    assert (aap["contact"]["phone"], aap["contact"]["email"], aap["contact"]["website"]) == (None, None, None)


def test_supplier_with_contact_and_freshness():
    req = SupplierSearchRequest(query=MILK_TEXT, okpd2=MILK_CODE)
    with psycopg.connect(database_url()) as conn:
        fresh = S.supplier_search(conn, req, today=date(2026, 10, 2))
    with psycopg.connect(database_url()) as conn:
        stale = S.supplier_search(conn, req, today=date(2027, 10, 2))

    def birsk(res):
        return next(x for e in res.external_expansion for x in e.candidates if x.supplier_inn == "0257011170")
    b = birsk(fresh)
    assert b.contact.website == "https://molloko.ru/"                  # first-party website (P4-005C record)
    assert b.freshness.status == "FRESH" and b.freshness.last_checked_at.date() == date(2026, 10, 1)
    assert b.freshness.source_url and b.freshness.source_url.startswith("https://")
    assert birsk(stale).freshness.status == "STALE"


def test_region_filter_uses_registration_region(client):
    d = post(client, query="Молоко", okpd2=MILK_CODE, region="78", limit=5)
    assert d["suppliers"] and len(d["suppliers"]) <= 5 and all(s["registration_region"] == "78" for s in d["suppliers"])
    assert any(w.startswith("REGION_IS_REGISTRATION_REGION") for w in d["classification"]["warnings"])


def test_deterministic_response(client):
    a = post(client, query=MILK_TEXT, okpd2=MILK_CODE)
    b = post(client, query=MILK_TEXT, okpd2=MILK_CODE)
    assert _strip(a) == _strip(b)
    assert a["search_id"] == S.encode_search_id(SupplierSearchRequest(query=MILK_TEXT, okpd2=MILK_CODE))


def test_export_csv_and_json(client):
    d = post(client, query=MILK_TEXT, okpd2=MILK_CODE, limit=10)
    r = client.get(f"/api/v1/supplier-search/{d['search_id']}/export", params={"format": "csv"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert list(rows[0].keys()) == S.EXPORT_COLUMNS
    hist = [x for x in rows if x["record_type"] == "HISTORICAL_SUPPLIER"]
    ext = [x for x in rows if x["record_type"] == "EXTERNAL_CANDIDATE"]
    assert [x["supplier_id"] for x in hist] == [s["supplier_id"] for s in d["suppliers"]]
    assert len(ext) == sum(len(e["candidates"]) for e in d["external_expansion"]) == 6
    j = client.get(f"/api/v1/supplier-search/{d['search_id']}/export", params={"format": "json"}).json()
    assert j["search_id"] == d["search_id"] and j["columns"] == S.EXPORT_COLUMNS and len(j["records"]) == len(rows)
    assert j["price_intelligence"]["available"] is False
    assert client.get("/api/v1/supplier-search/not-a-valid-id/export").status_code == 422


def test_validation_errors(client):
    assert client.post("/api/v1/supplier-search", json={"query": "ab"}).status_code == 422
    r = client.post("/api/v1/supplier-search", json={"query": "молоко", "okpd2": "abc"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "INVALID_QUERY"
    assert client.post("/api/v1/supplier-search", json={"query": "молоко", "region": "7"}).status_code == 422
    assert client.post("/api/v1/supplier-search", json={"query": "молоко", "limit": 0}).status_code == 422


def test_lot_endpoints_unchanged(client):
    r = client.get("/api/v1/recommendations/5718896").json()
    assert r["config_name"] == "P2_001_SEMANTIC" and r["config"] == DEFAULT_CONFIG.to_dict()
    assert list(r["timings_ms"]) == ["query_ms", "retrieval_ms", "lot_aggregation_ms", "candidates_ms", "scoring_ms", "total_ms"]
    a = client.get("/api/v1/procurements/6022687/analysis").json()
    assert a["availability"] == "COMPLETE" and a["recommendations"]["status"] == "OK"
    m = client.get(f"/api/v1/market-intelligence/{MILK_CODE}").json()
    assert m["pool_health"]["status"] == "VERY_HIGH" and (m["external_expansion"]["verified_count"], m["external_expansion"]["under_review_count"]) == (4, 2)
