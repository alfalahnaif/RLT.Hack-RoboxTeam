"""Pool-health calculations and canonical-table semantics."""
from datetime import date

import psycopg
import pytest

from app.analytics.models import PoolScope, PoolThresholds
from app.analytics.distribution import full_code_distribution
from app.analytics.pool_health import analyze_pool, classify, concentration_shares
from app.shared.config import database_url


def test_concentration_math_for_dominant_equal_and_single_supplier():
    assert concentration_shares([94, 4, 2]) == pytest.approx((.94, 1.0, .8856))
    assert concentration_shares([1, 1, 1, 1]) == pytest.approx((.25, .75, .25))
    assert concentration_shares([7]) == pytest.approx((1.0, 1.0, 1.0))
    assert concentration_shares([]) == (None, None, None)


@pytest.fixture
def pool_db():
    """Temporary canonical-shaped tables; no persistent test or organizer rows are changed."""
    with psycopg.connect(database_url()) as conn:
        conn.execute("CREATE TEMP TABLE procurement_lot (lot_id text, procedure_id text, publish_date date, platform text, customer_inn text)")
        conn.execute("CREATE TEMP TABLE procurement_item (lot_id text, publish_date date, okpd2_code text, okpd2_group text, okpd2_class text, product_name_raw text)")
        conn.execute("CREATE TEMP TABLE supplier_history (lot_id text, supplier_id text, is_winner boolean, platform text, publish_date date, coverage_semantics text)")
        conn.execute("CREATE TEMP TABLE supplier (supplier_id text, inn text)")
        for supplier in ("A", "B", "C", "D"):
            conn.execute("INSERT INTO supplier VALUES (%s, %s)", (supplier, supplier))
        yield conn
        conn.rollback()


def add_lot(conn, lot_id, day, winner, observed=(), platform="EM", repeat_item=False):
    conn.execute("INSERT INTO procurement_lot VALUES (%s, %s, %s, %s, %s)",
                 (lot_id, f"procedure-{lot_id}", day, platform, f"customer-{lot_id}"))
    for _ in range(2 if repeat_item else 1):
        conn.execute("INSERT INTO procurement_item VALUES (%s, %s, '10.51.11.141', '10.51', '10', 'Milk')",
                     (lot_id, day))
    semantics = "WINNER_ROWS_ONLY_OBSERVED" if platform == "AIS_GZ" else "MIXED_WINNER_NONWINNER_ROWS_OBSERVED"
    for supplier, is_winner in [(winner, True), *((s, False) for s in observed)]:
        # Duplicate source-like relations deliberately; service must deduplicate.
        for _ in range(2 if repeat_item else 1):
            conn.execute("INSERT INTO supplier_history VALUES (%s, %s, %s, %s, %s, %s)",
                         (lot_id, supplier, is_winner, platform, day, semantics))


def test_temporal_recent_dedup_and_platform_semantics(pool_db):
    add_lot(pool_db, "old", "2024-01-01", "A", ("B",), repeat_item=True)
    add_lot(pool_db, "recent", "2025-06-01", "A", ("C",), platform="AIS_GZ")
    add_lot(pool_db, "future", "2025-07-01", "D")
    result = analyze_pool(pool_db, PoolScope("okpd2_code", "10.51.11.141", date(2025, 7, 1), 365),
                          PoolThresholds(min_lots=1, min_awards=1))
    assert result.support.lots == 2
    assert result.support.procurements == 2
    assert result.support.awards == 2
    assert result.suppliers.winning == 1
    assert result.suppliers.observed == 2  # AIS_GZ non-winner relation is not participant evidence.
    assert result.suppliers.recent_winning == 1
    assert result.suppliers.em_observed == 2
    assert result.suppliers.ais_gz_winning == 1
    assert result.concentration.hhi == 1
    assert result.alternatives.observed_only_count == 1
    assert result.alternatives.winning_count == 0
    assert result.alternatives.total_count == 1
    assert result.support.customers == 2
    assert result.reasons == analyze_pool(pool_db, result.scope, PoolThresholds(1, 1)).reasons
    earlier = analyze_pool(pool_db, PoolScope("okpd2_code", "10.51.11.141", date(2025, 1, 1), 90),
                           PoolThresholds(1, 1))
    assert earlier.support.lots == 1
    assert earlier.suppliers.recent_winning == 0


def test_equal_awards_group_scope_and_insufficient_data(pool_db):
    for n, supplier in enumerate(("A", "B", "C", "D"), 1):
        add_lot(pool_db, f"L{n}", f"2025-01-{n:02d}", supplier)
    full = analyze_pool(pool_db, PoolScope("okpd2_code", "10.51.11.141"), PoolThresholds(4, 4))
    assert full.concentration.top1_share == pytest.approx(.25)
    assert full.concentration.top3_share == pytest.approx(.75)
    assert full.concentration.hhi == pytest.approx(.25)
    assert full.concentration.label == "MODERATE"
    assert full.alternatives.winning_count == 3
    assert full.alternatives.total_count == 3
    assert analyze_pool(pool_db, PoolScope("okpd2_group", "10.51"), PoolThresholds(5, 5)).concentration.label == "INSUFFICIENT_DATA"
    assert analyze_pool(pool_db, PoolScope("okpd2_class", "10"), PoolThresholds(4, 4)).support.lots == 4


def test_configurable_thresholds_and_no_awards(pool_db):
    add_lot(pool_db, "one", "2025-01-01", "A")
    scope = PoolScope("okpd2_code", "10.51.11.141")
    assert analyze_pool(pool_db, scope, PoolThresholds(2, 2)).concentration.label == "INSUFFICIENT_DATA"
    assert analyze_pool(pool_db, scope, PoolThresholds(1, 1)).concentration.label == "VERY_HIGH"
    pool_db.execute("INSERT INTO procurement_lot VALUES ('empty', 'procedure-empty', '2025-01-02', 'EM', 'customer-empty')")
    pool_db.execute("INSERT INTO procurement_item VALUES ('empty', '2025-01-02', '10.51.11.142', '10.51', '10', 'Milk')")
    empty = analyze_pool(pool_db, PoolScope("okpd2_code", "10.51.11.142"), PoolThresholds(1, 1))
    assert empty.support.lots == 1 and empty.support.awards == 0
    assert empty.concentration.label == "INSUFFICIENT_DATA"
    assert empty.concentration.hhi is None


def test_analytical_threshold_boundaries_are_configurable():
    config = PoolThresholds(10, 10, moderate_top1=.45, high_top1=.65, very_high_top1=.85,
                            moderate_hhi=.31, high_hhi=.41, very_high_hhi=.61)
    assert classify(9, 100, .99, .99, config) == "INSUFFICIENT_DATA"
    assert classify(100, 9, .99, .99, config) == "INSUFFICIENT_DATA"
    assert classify(10, 10, .84, .60, config) == "HIGH"
    assert classify(10, 10, .85, .20, config) == "VERY_HIGH"
    assert classify(10, 10, .30, .42, config) == "HIGH"
    assert classify(10, 10, .20, .20, config) == "LOW"


def test_full_distribution_agrees_with_single_pool_and_deduplicates_lots(pool_db):
    add_lot(pool_db, "A1", "2025-01-01", "A", ("B",), repeat_item=True)
    add_lot(pool_db, "B1", "2025-01-02", "B", ("C",))
    pool_db.execute("UPDATE procurement_lot SET procedure_id = 'procedure-A1' WHERE lot_id = 'B1'")
    add_lot(pool_db, "future", "2025-04-01", "C")
    cutoff = date(2025, 3, 1)
    _, rows = full_code_distribution(pool_db, cutoff)
    row = next(r for r in rows if r["code"] == "10.51.11.141")
    pool = analyze_pool(pool_db, PoolScope("okpd2_code", row["code"], cutoff), PoolThresholds(1, 1))
    assert row["lot_count"] == pool.support.lots == 2
    assert row["procurement_count"] == pool.support.procurements == 1
    assert row["award_count"] == pool.support.awards == 2
    assert row["observed_supplier_count"] == pool.suppliers.observed == 3
    assert row["winning_supplier_count"] == pool.suppliers.winning == 2
    assert row["top1_share"] == pool.concentration.top1_share == .5
    assert row["hhi"] == pool.concentration.hhi == .5


@pytest.mark.parametrize("kind,value", [("okpd2_group", "10.51"), ("okpd2_class", "10")])
def test_group_and_class_deduplicate_different_exact_codes_in_one_lot(pool_db, kind, value):
    add_lot(pool_db, "multi-code", "2025-02-01", "A", ("B",))
    pool_db.execute("""INSERT INTO procurement_item VALUES
                    ('multi-code', '2025-02-01', '10.51.11.142', '10.51', '10', 'Milk variant')""")

    result = analyze_pool(pool_db, PoolScope(kind, value), PoolThresholds(1, 1))

    assert result.support.lots == 1
    assert result.support.procurements == 1
    assert result.support.awards == 1
    assert result.suppliers.winning == 1
    assert result.suppliers.observed == 2


def test_unknown_customer_lot_counts_but_not_as_distinct_customer(pool_db):
    add_lot(pool_db, "known", "2025-02-01", "A")
    add_lot(pool_db, "unknown", "2025-02-02", "B")
    pool_db.execute("UPDATE procurement_lot SET customer_inn = NULL WHERE lot_id = 'unknown'")

    result = analyze_pool(pool_db, PoolScope("okpd2_code", "10.51.11.141"), PoolThresholds(1, 1))
    _, rows = full_code_distribution(pool_db)
    distribution_row = next(r for r in rows if r["code"] == "10.51.11.141")

    assert result.support.lots == distribution_row["lot_count"] == 2
    assert result.support.customers == distribution_row["customer_count"] == 1
