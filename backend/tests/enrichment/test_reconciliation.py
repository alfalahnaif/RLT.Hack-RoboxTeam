"""Temporal candidate reconciliation against canonical history only."""
from dataclasses import replace
from datetime import date

import psycopg
import pytest

from app.enrichment.models import (CandidateInput, EvidenceStatus, ReconciliationStatus,
                                   SupplierEvidence, VerificationStatus, VerificationStrength)
from app.enrichment.reconciliation import reconcile_candidates
from app.shared.config import database_url


TARGET = "10.51.11.141"
INNS = {"category": "7622012124", "other": "0257011170", "new": "5320000979",
        "future": "5028002303"}


@pytest.fixture
def canonical_db():
    """Temporary canonical-shaped tables leave organizer data unchanged."""
    with psycopg.connect(database_url()) as conn:
        conn.execute("CREATE TEMP TABLE supplier (supplier_id text, inn text)")
        conn.execute("CREATE TEMP TABLE procurement_lot (lot_id text, publish_date date)")
        conn.execute("CREATE TEMP TABLE procurement_item (lot_id text, publish_date date, okpd2_code text, okpd2_group text)")
        conn.execute("CREATE TEMP TABLE supplier_history (lot_id text, supplier_id text, publish_date date, is_winner boolean, platform text, coverage_semantics text)")
        for key in ("category", "other", "future"):
            conn.execute("INSERT INTO supplier VALUES (%s, %s)", (key, INNS[key]))
        yield conn
        conn.rollback()


def add_lot(conn, lot_id, day, code):
    conn.execute("INSERT INTO procurement_lot VALUES (%s, %s)", (lot_id, day))
    conn.execute("INSERT INTO procurement_item VALUES (%s, %s, %s, '10.51')", (lot_id, day, code))


def add_history(conn, lot_id, day, supplier, winner=True, platform="EM"):
    coverage = ("WINNER_ROWS_ONLY_OBSERVED" if platform == "AIS_GZ"
                else "MIXED_WINNER_NONWINNER_ROWS_OBSERVED")
    conn.execute("INSERT INTO supplier_history VALUES (%s, %s, %s, %s, %s, %s)",
                 (lot_id, supplier, day, winner, platform, coverage))


def test_exact_category_other_category_new_invalid_and_future_only(canonical_db):
    add_lot(canonical_db, "exact", "2025-02-01", TARGET)
    add_history(canonical_db, "exact", "2025-02-01", "category")
    add_lot(canonical_db, "group-only", "2025-03-01", "10.51.11.142")
    add_history(canonical_db, "group-only", "2025-03-01", "other", winner=False)
    add_lot(canonical_db, "cutoff", "2026-01-01", TARGET)
    add_history(canonical_db, "cutoff", "2026-01-01", "future")
    inputs = [CandidateInput(INNS[key], key) for key in ("category", "other", "new", "future")]
    inputs += [CandidateInput("123", "malformed")]

    results = reconcile_candidates(canonical_db, inputs, TARGET, date(2026, 1, 1))

    assert [r.reconciliation_status for r in results] == [
        ReconciliationStatus.CATEGORY_HISTORICAL,
        ReconciliationStatus.HISTORICAL_OTHER_CATEGORY,
        ReconciliationStatus.EXTERNAL_NEW,
        ReconciliationStatus.EXTERNAL_NEW,
        ReconciliationStatus.INVALID_INN,
    ]
    assert results[0].historically_known and results[0].target_category_observed
    assert results[0].historical_first_seen == date(2025, 2, 1)
    assert results[0].historical_last_seen == date(2025, 2, 1)
    assert results[0].historical_lot_count == results[0].historical_win_count == 1
    assert results[1].historically_known and not results[1].target_category_observed
    assert results[1].historical_lot_count == 1 and results[1].historical_win_count == 0
    assert results[1].target_category_lot_count == 0
    assert not results[3].historically_known  # Canonical supplier row exists, but only future history.
    assert results[4].inn_valid is False
    assert all(r.verification_status == VerificationStatus.UNVERIFIED for r in results)


def test_duplicate_items_and_relations_do_not_inflate_lots_or_wins(canonical_db):
    add_lot(canonical_db, "dup", "2025-05-01", TARGET)
    canonical_db.execute("INSERT INTO procurement_item VALUES ('dup', '2025-05-01', %s, '10.51')", (TARGET,))
    add_history(canonical_db, "dup", "2025-05-01", "category")
    add_history(canonical_db, "dup", "2025-05-01", "category")

    result = reconcile_candidates(canonical_db, [CandidateInput(INNS["category"], "category")],
                                  TARGET, date(2026, 1, 1))[0]

    assert result.reconciliation_status == ReconciliationStatus.CATEGORY_HISTORICAL
    assert result.historical_lot_count == result.historical_win_count == 1
    assert result.target_category_lot_count == result.target_category_win_count == 1


def test_checksum_failure_is_invalid_and_verification_is_independent(canonical_db):
    invalid = reconcile_candidates(canonical_db, [CandidateInput("7622012125", "bad checksum")],
                                   TARGET, date(2026, 1, 1))[0]
    assert invalid.reconciliation_status == ReconciliationStatus.INVALID_INN
    assert "INVALID_INN_CHECKSUM" in invalid.inn_validation_flags

    external = reconcile_candidates(canonical_db, [CandidateInput(INNS["new"], "new")],
                                    TARGET, date(2026, 1, 1))[0]
    evidence = SupplierEvidence("registry", "https://example.test/record", "Example Registry", (TARGET,),
                                date(2025, 12, 1), None, EvidenceStatus.UNKNOWN,
                                VerificationStrength.NONE, "Illustrative test record")
    enriched = replace(external, evidence_records=(evidence,), verification_status=VerificationStatus.VERIFIED)
    assert external.reconciliation_status == enriched.reconciliation_status == ReconciliationStatus.EXTERNAL_NEW
    assert external.verification_status == VerificationStatus.UNVERIFIED
    assert enriched.verification_status == VerificationStatus.VERIFIED


def test_reconciliation_requires_an_explicit_date_cutoff(canonical_db):
    with pytest.raises(ValueError, match="as_of"):
        reconcile_candidates(canonical_db, [CandidateInput(INNS["new"], "new")], TARGET, None)
