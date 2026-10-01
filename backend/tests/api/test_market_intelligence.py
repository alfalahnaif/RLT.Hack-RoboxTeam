"""Read-only market-intelligence API and temporal integration tests."""
from __future__ import annotations

import json
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.market_service import build_market_intelligence
from app.enrichment.catalog import CuratedEvidenceCatalog
from app.shared.config import database_url, repo_root


MILK = "10.51.11.141"
CONTRAST = "10.20.25.111"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_primary_category_returns_distinct_historical_and_external_sections(client):
    response = client.get(f"/api/v1/market-intelligence/{MILK}")
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == {"okpd2": MILK, "as_of": "2026-01-01"}
    pool = data["pool_health"]
    assert pool["status"] == "VERY_HIGH"
    assert pool["lot_count"] == 182
    assert pool["known_customer_count"] == 39
    assert pool["top1_share"] == pytest.approx(0.9422, abs=0.0001)
    assert data["concentration"]["signal"] == "EXPANSION_RECOMMENDED"
    assert len(data["historical_alternatives"]) == pool["alternative_supplier_count"] == 5
    external = data["external_expansion"]
    assert external["available"] is True
    assert (external["verified_count"], external["under_review_count"]) == (4, 2)
    assert [c["verification_status"] for c in external["candidates"]] == ["VERIFIED"] * 4 + ["UNDER_REVIEW"] * 2
    assert all(c["reconciliation_status"] == "EXTERNAL_NEW" for c in external["candidates"])
    assert all(c["exact_okpd2_asserted_by_source"] is False for c in external["candidates"])
    assert all(c["evidence_count"] == len(c["evidence_summary"]) for c in external["candidates"])
    assert data["provenance"]["historical_source"] == "canonical procurement database"
    assert data["provenance"]["external_source"] == "curated evidence seed"


def test_contrast_category_has_pool_without_curated_external_evidence(client):
    response = client.get(f"/api/v1/market-intelligence/{CONTRAST}")
    assert response.status_code == 200
    data = response.json()
    assert data["pool_health"]["status"] == "LOW"
    assert data["pool_health"]["lot_count"] == 179
    assert data["pool_health"]["known_customer_count"] == 74
    assert data["pool_health"]["observed_supplier_count"] == 45
    assert data["pool_health"]["top1_share"] == pytest.approx(.13, abs=.01)
    assert data["concentration"]["signal"] == "NO_EXPANSION_SIGNAL"
    assert data["external_expansion"] == {"available": False, "evidence_checked_at": None,
                                          "verified_count": 0, "under_review_count": 0, "candidates": []}
    assert data["provenance"]["external_source"] == "none in current catalog"


def test_valid_category_with_no_history_at_cutoff_is_insufficient_data(client):
    response = client.get(f"/api/v1/market-intelligence/{MILK}", params={"as_of": "2020-01-01"})
    assert response.status_code == 200
    data = response.json()
    assert data["pool_health"]["lot_count"] == 0
    assert data["pool_health"]["status"] == "INSUFFICIENT_DATA"
    assert data["concentration"] == {"signal": "INSUFFICIENT_DATA", "reason_codes": ["INSUFFICIENT_HISTORY"]}


@pytest.mark.parametrize("path,params,status,code", [
    ("not-an-okpd2", {}, 422, "INVALID_OKPD2"),
    ("99.99.99.999", {}, 404, "CATEGORY_NOT_OBSERVED"),
    (MILK, {"as_of": "tomorrow"}, 422, None),
    (MILK, {"recent_days": 0}, 422, None),
])
def test_input_and_unknown_category_errors(client, path, params, status, code):
    response = client.get(f"/api/v1/market-intelligence/{path}", params=params)
    assert response.status_code == status
    if code:
        assert response.json()["detail"]["code"] == code


def test_malformed_catalog_is_a_service_error(client, tmp_path, monkeypatch):
    (tmp_path / "bad_evidence_seed.json").write_text("{invalid", encoding="utf-8")
    monkeypatch.setattr("app.api.market_intelligence.CuratedEvidenceCatalog",
                        lambda: CuratedEvidenceCatalog(tmp_path))
    response = client.get(f"/api/v1/market-intelligence/{MILK}")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "EVIDENCE_CATALOG_UNAVAILABLE"


def test_missing_catalog_is_a_service_error(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.market_intelligence.CuratedEvidenceCatalog",
                        lambda: CuratedEvidenceCatalog(tmp_path / "missing"))
    response = client.get(f"/api/v1/market-intelligence/{MILK}")
    assert response.status_code == 503


def test_external_order_and_json_serialization_are_deterministic(client):
    first = client.get(f"/api/v1/market-intelligence/{MILK}")
    second = client.get(f"/api/v1/market-intelligence/{MILK}")
    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    data = first.json()
    json.dumps(data)
    candidates = data["external_expansion"]["candidates"]
    priority = {"VERIFIED": 0, "UNDER_REVIEW": 1, "UNVERIFIED": 2}
    strength = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "NONE": 3}
    assert candidates == sorted(candidates, key=lambda c: (
        priority[c["verification_status"]], strength[c["verification_strength"]],
        c["company_name"].casefold(), c["supplier_inn"]))
    assert isinstance(candidates[0]["evidence_summary"][0]["retrieved_at"], str)
    assert "supplier_id" in data["historical_alternatives"][0]


def test_temporal_reconciliation_changes_without_changing_verification():
    """Temporary shadow tables model a future observation without canonical writes."""
    with psycopg.connect(database_url()) as conn:
        conn.execute("CREATE TEMP TABLE procurement_lot (lot_id text, procedure_id text, customer_inn text, publish_date date, platform text)")
        conn.execute("CREATE TEMP TABLE procurement_item (lot_id text, publish_date date, okpd2_code text)")
        conn.execute("CREATE TEMP TABLE supplier_history (lot_id text, supplier_id text, is_winner boolean, platform text, publish_date date, coverage_semantics text)")
        conn.execute("CREATE TEMP TABLE supplier (supplier_id text, inn text)")
        conn.execute("INSERT INTO supplier VALUES ('other', '7806410527'), ('future', '7622012124')")
        conn.execute("INSERT INTO procurement_lot VALUES ('old', 'p-old', '123', '2025-01-01', 'EM'), ('future', 'p-future', '123', '2026-02-01', 'EM')")
        conn.execute("INSERT INTO procurement_item VALUES ('old', '2025-01-01', %s), ('future', '2026-02-01', %s)", (MILK, MILK))
        conn.execute("INSERT INTO supplier_history VALUES ('old', 'other', true, 'EM', '2025-01-01', 'MIXED_WINNER_NONWINNER_ROWS_OBSERVED'), ('future', 'future', true, 'EM', '2026-02-01', 'MIXED_WINNER_NONWINNER_ROWS_OBSERVED')")
        catalog = CuratedEvidenceCatalog(repo_root() / "data" / "seed")
        earlier = build_market_intelligence(conn, catalog, MILK, date(2026, 1, 1))
        later = build_market_intelligence(conn, catalog, MILK, date(2026, 3, 1))
        early = {c.supplier_inn: c for c in earlier.external_expansion.candidates}
        late = {c.supplier_inn: c for c in later.external_expansion.candidates}
        assert earlier.pool_health.lot_count == 1
        assert later.pool_health.lot_count == 2
        assert early["7622012124"].reconciliation_status == "EXTERNAL_NEW"
        assert late["7622012124"].reconciliation_status == "CATEGORY_HISTORICAL"
        assert early["7622012124"].verification_status == late["7622012124"].verification_status == "VERIFIED"
        conn.rollback()


def test_api_does_not_write_canonical_procurement_tables(client):
    with psycopg.connect(database_url()) as conn:
        before = conn.execute("SELECT count(*) FROM procurement_lot").fetchone()[0]
    assert client.get(f"/api/v1/market-intelligence/{MILK}").status_code == 200
    with psycopg.connect(database_url()) as conn:
        after = conn.execute("SELECT count(*) FROM procurement_lot").fetchone()[0]
    assert before == after


def test_openapi_describes_provenance_and_independent_statuses(client):
    schema = client.get("/openapi.json").json()
    path = schema["paths"][f"/api/v1/market-intelligence/{{okpd2}}"]
    assert "historical" in path["get"]["description"].lower()
    models = schema["components"]["schemas"]
    assert "EXTERNAL_NEW never implies VERIFIED" in models["ExternalCandidateResponse"]["properties"]["reconciliation_status"]["description"]
