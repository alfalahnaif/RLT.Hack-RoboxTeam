"""Curated seed validation and deterministic evidence verification."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import psycopg
import pytest

from app.enrichment.models import CandidateInput, ExternalCandidate, ReconciliationStatus, VerificationStatus
from app.enrichment.reconciliation import reconcile_candidates
from app.enrichment.verification import evaluate_seed, load_evidence_seed, parse_evidence_seed
from app.shared.config import database_url


SEED_PATH = Path(__file__).resolve().parents[3] / "data" / "seed" / "p3_002b_evidence_seed.json"
HISTORY_AS_OF = date(2026, 1, 1)


def seed_dict() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def historical_results(seed) -> list[ExternalCandidate]:
    return [ExternalCandidate(
        supplier_inn=c.supplier_inn, company_name=c.canonical_name,
        target_okpd2=seed.target_okpd2, as_of=HISTORY_AS_OF,
        inn_valid=True, inn_validation_flags=(), reconciliation_status=ReconciliationStatus.EXTERNAL_NEW,
        historically_known=False, target_category_observed=False,
        historical_first_seen=None, historical_last_seen=None,
        historical_lot_count=0, historical_win_count=0,
        target_category_lot_count=0, target_category_win_count=0,
    ) for c in seed.candidates]


def test_seed_yields_four_verified_two_under_review_and_preserves_identity():
    seed = load_evidence_seed(SEED_PATH)
    results = evaluate_seed(seed, historical_results(seed))
    by_inn = {r.supplier_inn: r for r in results}

    assert len(results) == len(by_inn) == 6
    assert [r.verification_status for r in results] == [
        VerificationStatus.VERIFIED, VerificationStatus.VERIFIED,
        VerificationStatus.VERIFIED, VerificationStatus.VERIFIED,
        VerificationStatus.UNDER_REVIEW, VerificationStatus.UNDER_REVIEW,
    ]
    assert all(r.reconciliation_status == ReconciliationStatus.EXTERNAL_NEW for r in results)
    assert by_inn["7622012124"].aliases == ("ООО «Эдельвейс»",)
    assert by_inn["7622012124"].company_name == "ООО «Переславский молочный комбинат»"
    assert all(not r.exact_okpd2_asserted_by_source for r in results)
    assert all(r.evidence_count == len(r.evidence_summary) for r in results)
    assert by_inn["7622012124"].evidence_summary[0]["target_product_support"] == "DIRECT"
    assert by_inn["5007126820"].active_evidence_count == 2
    assert by_inn["3128004452"].active_evidence_count == 1
    assert by_inn["5007126820"].review_reasons
    assert by_inn["5007126820"].verification_status == VerificationStatus.UNDER_REVIEW
    assert results == evaluate_seed(seed, historical_results(seed))
    assert [r.to_dict() for r in results] == [r.to_dict() for r in evaluate_seed(seed, historical_results(seed))]


@pytest.mark.parametrize("mutate,expected", [
    (lambda p: p["candidates"][0].update(supplier_inn="123"), "INN"),
    (lambda p: p["candidates"][0].update(market_role="MYSTERY"), "market_role"),
    (lambda p: p["candidates"][0]["evidence_records"][0].update(evidence_status="LIVE"), "evidence_status"),
    (lambda p: p["candidates"][0]["evidence_records"][0].update(evidence_date="2026-99-99"), "evidence_date"),
    (lambda p: p["candidates"][0]["evidence_records"][0].update(valid_until="2026-09-30"), "valid_until"),
    (lambda p: p["candidates"][0]["evidence_records"][0].update(valid_until="2026-02-30"), "valid_until"),
    (lambda p: p["candidates"][0]["evidence_records"][0].update(retrieved_at="2026-10-02T20:45:00+03:00"), "retrieved_at"),
    (lambda p: p["candidates"][0]["evidence_records"][0].update(source_authority="UNKNOWN_SOURCE"), "source_authority"),
    (lambda p: p["candidates"][0]["evidence_records"][0].update(target_product_support="MAYBE"), "target_product_support"),
    (lambda p: p["candidates"][0].update(exact_okpd2_asserted_by_source=True), "exact_okpd2"),
    (lambda p: p["candidates"][0].update(verification_status="MAYBE"), "verification_status"),
])
def test_malformed_seed_is_rejected(mutate, expected):
    payload = seed_dict()
    mutate(payload)
    with pytest.raises(ValueError, match=expected):
        parse_evidence_seed(payload)


def test_terminated_declaration_cannot_alone_support_verified_status():
    payload = seed_dict()
    av = payload["candidates"][5]
    av["verification_status"] = "VERIFIED"
    av["review_reasons"] = []
    av["evidence_records"] = [av["evidence_records"][1]]  # terminated declaration only
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="supporting evidence"):
        evaluate_seed(seed, historical_results(seed))


def test_suspended_declaration_cannot_alone_support_verified_status():
    payload = seed_dict()
    candidate = payload["candidates"][2]
    candidate["evidence_records"][0]["evidence_status"] = "SUSPENDED"
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="supporting evidence"):
        evaluate_seed(seed, historical_results(seed))


def test_active_evidence_valid_until_on_check_date_is_accepted():
    payload = seed_dict()
    payload["candidates"][0]["evidence_records"][0]["valid_until"] = "2026-10-01"
    seed = parse_evidence_seed(payload)
    assert evaluate_seed(seed, historical_results(seed))[0].verification_status == VerificationStatus.VERIFIED


@pytest.mark.parametrize("change,expected", [
    ({"evidence_date": "2026-10-02"}, "evidence_date is after checked_at"),
    ({"valid_until": "2026-06-29"}, "valid_until is before evidence_date"),
    ({"retrieved_at": "2026-10-01T20:45:01+03:00"}, "retrieved_at is after checked_at"),
])
def test_temporal_inconsistency_is_rejected(change, expected):
    payload = seed_dict()
    payload["candidates"][0]["evidence_records"][0].update(change)
    with pytest.raises(ValueError, match=expected):
        parse_evidence_seed(payload)


def test_direct_support_is_structured_and_independent_of_product_wording():
    payload = seed_dict()
    record = payload["candidates"][2]["evidence_records"][0]
    record["product_scope"] = ["A different category's target product"]
    seed = parse_evidence_seed(payload)
    assert evaluate_seed(seed, historical_results(seed))[2].verification_status == VerificationStatus.VERIFIED
    record["target_product_support"] = "RELATED"
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="supporting evidence"):
        evaluate_seed(seed, historical_results(seed))


def test_candidate_direct_product_match_is_required_for_verification():
    payload = seed_dict()
    payload["candidates"][2]["target_product_match"] = "HISTORICAL_DIRECT_PRODUCT_TEXT"
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="supporting evidence"):
        evaluate_seed(seed, historical_results(seed))


@pytest.mark.parametrize("url", [None, "ftp://example.org/declaration"])
def test_declaration_without_auditable_url_cannot_verify(url):
    payload = seed_dict()
    payload["candidates"][2]["evidence_records"][0]["source_url"] = url
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="supporting evidence"):
        evaluate_seed(seed, historical_results(seed))


@pytest.mark.parametrize("record_index", [0, 1])
def test_corroborated_path_requires_urls_for_both_sources(record_index):
    payload = seed_dict()
    payload["candidates"][3]["evidence_records"][record_index]["source_url"] = None
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="supporting evidence"):
        evaluate_seed(seed, historical_results(seed))


def test_https_url_supports_verification_without_fetching():
    payload = seed_dict()
    payload["candidates"][2]["evidence_records"][0]["source_url"] = "https://example.org/declaration"
    seed = parse_evidence_seed(payload)
    assert evaluate_seed(seed, historical_results(seed))[2].verification_status == VerificationStatus.VERIFIED


def test_incomplete_url_is_retained_for_review_without_verifying():
    payload = seed_dict()
    payload["candidates"][4]["evidence_records"][0]["source_url"] = None
    seed = parse_evidence_seed(payload)
    assert evaluate_seed(seed, historical_results(seed))[4].verification_status == VerificationStatus.UNDER_REVIEW


def test_weak_product_listing_does_not_support_verified_status():
    payload = seed_dict()
    payload["candidates"][3]["evidence_records"][1]["verification_strength"] = "WEAK"
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="supporting evidence"):
        evaluate_seed(seed, historical_results(seed))


def test_duplicate_inn_cannot_split_alias_into_second_supplier():
    payload = seed_dict()
    payload["candidates"][1]["supplier_inn"] = "7622012124"
    with pytest.raises(ValueError, match="Duplicate candidate INN"):
        parse_evidence_seed(payload)


def test_review_reason_cannot_be_silently_overridden_by_active_declaration():
    payload = seed_dict()
    payload["candidates"][4]["verification_status"] = "VERIFIED"
    seed = parse_evidence_seed(payload)
    with pytest.raises(ValueError, match="review"):
        evaluate_seed(seed, historical_results(seed))


def test_explicit_exact_code_requires_structured_source_assertion():
    payload = seed_dict()
    payload["candidates"][0]["evidence_records"][0]["asserted_okpd2_codes"] = ["10.51.11"]
    payload["candidates"][0]["exact_okpd2_asserted_by_source"] = True
    with pytest.raises(ValueError, match="exact_okpd2"):
        parse_evidence_seed(payload)


def test_canonical_procurement_tables_remain_read_only():
    seed = load_evidence_seed(SEED_PATH)
    with psycopg.connect(database_url()) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        before = conn.execute("SELECT count(*) FROM procurement_lot").fetchone()[0]
        reconciled = reconcile_candidates(conn, [CandidateInput(c.supplier_inn, c.canonical_name)
                                                 for c in seed.candidates], seed.target_okpd2, HISTORY_AS_OF)
        results = evaluate_seed(seed, reconciled)
        after = conn.execute("SELECT count(*) FROM procurement_lot").fetchone()[0]
    assert before == after
    assert all(r.reconciliation_status == ReconciliationStatus.EXTERNAL_NEW for r in results)
