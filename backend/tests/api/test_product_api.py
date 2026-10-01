"""P4-001 product API: recommendations, integrated procurement analysis, health, semantic fallback, deterministic serialization.
Read-only against the canonical database (like the P3-002C API tests). Lots used are golden demo lots (no replay overlap)."""
from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api import product_service as S
from app.api.main import app
from app.api.market_service import UnknownCategory
from app.search import semantic
from app.search.models import DEFAULT_CONFIG, P2_001_SEMANTIC, P2_003_RANKING
from app.search.recommend import recommend
from app.shared.config import database_url

LOT = "5718896"          # golden primary (laptops, one OKPD2)
MULTI = "6022687"        # golden backup (two distinct OKPD2 codes)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _semantic_ready(client) -> bool:
    return client.get("/api/v1/health").json()["semantic"]["status"] == "ready"


def _strip_timings(d):
    if isinstance(d, dict):
        return {k: _strip_timings(v) for k, v in d.items() if k not in ("timings_ms", "branch_ms")}
    if isinstance(d, list):
        return [_strip_timings(x) for x in d]
    return d


def test_recommendation_endpoint_uses_default_engine(client):
    r = client.get(f"/api/v1/recommendations/{LOT}")
    assert r.status_code == 200
    d = r.json()
    assert d["config_name"] == "P2_001_SEMANTIC" and d["config"] == P2_001_SEMANTIC.to_dict() == DEFAULT_CONFIG.to_dict()
    assert d["config"]["semantic_top_k"] == 100 and d["config"]["w_product_text"] == 0.35 and d["config"]["w_okpd2"] == 0.30
    assert d["lot_id"] == LOT and d["as_of"] == "2025-06-16" and d["candidate_count"] >= len(d["results"]) > 0
    assert all(x["reasons"] for x in d["results"]) and [x["rank"] for x in d["results"]] == list(range(1, len(d["results"]) + 1))
    with psycopg.connect(database_url()) as conn:
        direct = recommend(conn, LOT)                     # the API adds no ranking logic
    assert [x["supplier_id"] for x in d["results"]] == [x["supplier_id"] for x in direct["results"]]
    if _semantic_ready(client):
        assert d["semantic_enabled"] and d["warnings"] == []
        assert any(x["semantic_evidence"] for x in d["results"])
        ev = next(x["semantic_evidence"][0] for x in d["results"] if x["semantic_evidence"])
        assert ev["product"] and ev["lot_id"] and ev["publish_date"] < d["as_of"] and 0 < ev["cosine"] <= 1


def test_recommendation_unknown_lot_is_404(client):
    r = client.get("/api/v1/recommendations/does-not-exist")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "LOT_NOT_FOUND"
    assert client.get("/api/v1/procurements/does-not-exist/analysis").status_code == 404


def test_semantic_fallback_through_api(client, monkeypatch, tmp_path):
    monkeypatch.setattr(semantic, "LOCK", tmp_path / "missing.lock.json")
    d = client.get(f"/api/v1/recommendations/{LOT}").json()
    assert d["warnings"] and d["warnings"][0].startswith("SEMANTIC_UNAVAILABLE") and d["semantic_enabled"] is False
    assert d["config_name"] == "P2_001_SEMANTIC"
    with psycopg.connect(database_url()) as conn:
        p2003 = recommend(conn, LOT, P2_003_RANKING.with_(top_k=DEFAULT_CONFIG.top_k))
    assert [x["supplier_id"] for x in d["results"]] == [x["supplier_id"] for x in p2003["results"]]
    assert [x["score"] for x in d["results"]] == [x["score"] for x in p2003["results"]]
    h = client.get("/api/v1/health").json()
    assert h["status"] == "degraded" and h["semantic"]["status"] == "unavailable" and h["postgres"] == "reachable"


def test_health_reports_components(client):
    h = client.get("/api/v1/health")
    assert h.status_code == 200
    d = h.json()
    assert d["api"] == "ready" and d["postgres"] == "reachable"
    assert d["semantic"]["pinned_revision"] == semantic.lock()["revision"]
    if d["semantic"]["status"] == "ready":
        assert d["semantic"]["hnsw_ready"] and d["semantic"]["index_revision"] == d["semantic"]["pinned_revision"]
    assert d["curated_evidence_catalog"]["status"] == "ready" and d["curated_evidence_catalog"]["seed_files"] >= 1


def test_analysis_combines_all_sections(client):
    r = client.get(f"/api/v1/procurements/{MULTI}/analysis")
    assert r.status_code == 200
    d = r.json()
    assert set(d) >= {"procurement", "recommendations", "market_intelligence"}
    p = d["procurement"]
    assert p["lot_id"] == MULTI and p["items_total"] == len(p["items"]) == 2 and p["publish_date"] == "2025-12-17"
    codes = sorted({i["okpd2_code"] for i in p["items"] if i["okpd2_code"]})
    assert [e["okpd2"] for e in d["market_intelligence"]] == codes        # each distinct exact code once, sorted
    assert all(e["status"] == "OK" and e["data"]["category"]["as_of"] == p["publish_date"] for e in d["market_intelligence"])
    assert d["recommendations"]["status"] == "OK" and d["recommendations"]["data"]["config_name"] == "P2_001_SEMANTIC"
    assert d["recommendations"]["data"]["results"] and d["availability"] == "COMPLETE" and d["items_without_okpd2"] == []


def test_analysis_isolates_a_failing_category(client, monkeypatch):
    real = S.build_market_intelligence

    def flaky(conn, catalog, code, as_of):
        if code == "26.20.18.120":
            raise UnknownCategory("simulated")
        return real(conn, catalog, code, as_of)
    monkeypatch.setattr(S, "build_market_intelligence", flaky)
    d = client.get(f"/api/v1/procurements/{MULTI}/analysis").json()
    by = {e["okpd2"]: e for e in d["market_intelligence"]}
    assert by["26.20.18.120"]["status"] == "UNAVAILABLE" and by["26.20.18.120"]["error"]["code"] == "CATEGORY_NOT_OBSERVED"
    assert by["26.20.11.110"]["status"] == "OK" and d["recommendations"]["status"] == "OK" and d["availability"] == "PARTIAL"


def test_analysis_isolates_recommendation_failure_and_skips_items_without_okpd2(client, monkeypatch):
    real_proc = S.procurement

    def proc_with_blank(conn, lot_id):
        p = real_proc(conn, lot_id)
        p.items[0] = p.items[0].model_copy(update={"okpd2_code": None})
        return p

    def broken(conn, lot_id):
        raise RuntimeError("simulated engine failure")
    monkeypatch.setattr(S, "procurement", proc_with_blank)
    monkeypatch.setattr(S, "recommendation", broken)
    d = client.get(f"/api/v1/procurements/{MULTI}/analysis").json()
    assert d["recommendations"]["status"] == "UNAVAILABLE" and d["recommendations"]["error"]["code"] == "RECOMMENDATION_UNAVAILABLE"
    blank = d["procurement"]["items"][0]["line_no"]
    assert d["items_without_okpd2"] == [blank]
    assert all(blank not in e["item_lines"] for e in d["market_intelligence"]) and len(d["market_intelligence"]) == 1
    assert d["market_intelligence"][0]["status"] == "OK" and d["availability"] == "PARTIAL"


def test_serialization_is_deterministic(client):
    a = client.get(f"/api/v1/procurements/{MULTI}/analysis").json()
    b = client.get(f"/api/v1/procurements/{MULTI}/analysis").json()
    assert _strip_timings(a) == _strip_timings(b)
    r1, r2 = (client.get(f"/api/v1/recommendations/{LOT}").json() for _ in range(2))
    assert _strip_timings(r1) == _strip_timings(r2)


def test_cors_is_restricted_to_local_frontend(client):
    ok = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
