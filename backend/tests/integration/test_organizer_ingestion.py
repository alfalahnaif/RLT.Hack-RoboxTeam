"""DB integration tests for the organizer ingestion (fixture slice; masked identifiers)."""
import json
import sys
from decimal import Decimal

import psycopg
import pytest

from app.ingestion import organizer
from app.shared import ids
from app.shared.config import repo_root


@pytest.fixture(scope="module")
def loaded(test_db_url, slice_dir):
    report = organizer.ingest_organizer(test_db_url, slice_dir, use_pinned=False, reset=True)
    return report


def q(url, sql, *args):
    with psycopg.connect(url) as c:
        return c.execute(sql, args).fetchall()


def test_fresh_ingestion_counts(loaded):
    c = loaded["counts"]
    assert (c["raw_notice"], c["raw_supplier_relation"], c["raw_procurement_item"]) == (6, 9, 12)
    assert (c["procurement_lot"], c["procurement_item"], c["supplier_history"], c["supplier"]) == (6, 12, 8, 7)
    assert c["ingestion_quarantine"] == 0 and c["ingestion_delivery"] == 1
    assert loaded["meta"]["mode"] == "load"


def test_second_run_is_verify_only_and_force_inserts_nothing(test_db_url, slice_dir, loaded):
    again = organizer.ingest_organizer(test_db_url, slice_dir, use_pinned=False)
    assert again["meta"]["mode"] == "verify-existing"
    assert again["counts"] == loaded["counts"] and again["fingerprints"] == loaded["fingerprints"]
    forced = organizer.ingest_organizer(test_db_url, slice_dir, use_pinned=False, force=True)
    assert forced["meta"]["mode"] == "load"
    assert set(forced["meta"]["rows_inserted"].values()) == {0}
    assert forced["counts"] == loaded["counts"] and forced["fingerprints"] == loaded["fingerprints"]


def test_foreign_keys_enforced(test_db_url, loaded):
    with psycopg.connect(test_db_url) as c, pytest.raises(psycopg.errors.ForeignKeyViolation):
        c.execute("""INSERT INTO procurement_item (item_id, lot_id, line_no, content_hash, product_name_raw, is_generic_type_name,
                     okpd2_code_raw, source_sha256, source_row_no, publish_date)
                     VALUES (gen_random_uuid(), 'no-such-lot', 1, repeat('0', 64), 'x', false, '', repeat('0', 64), 1, '2025-01-01')""")


def test_duplicate_relation_merged_with_provenance(test_db_url, loaded):
    (row,) = q(test_db_url, """SELECT is_winner, supplier_kpp, data_quality_flags, source_row_nos FROM supplier_history
                               WHERE lot_id = '9900001' AND supplier_inn = '470000000239'""")
    assert row == (True, "470101001", ["DUPLICATE_SUPPLIER_RELATION"], [4, 5])
    assert q(test_db_url, "SELECT count(*) FROM raw_supplier_relation WHERE lot_id = '9900001' AND supplier_inn = '470000000239'")[0][0] == 2


def test_malformed_inn_preserved(test_db_url, loaded):
    rows = {r[0]: r[1:] for r in q(test_db_url, """SELECT inn, entity_type, inn_region_code, data_quality_flags FROM supplier
                                                   WHERE inn IN ('78О0000010', '123456789', '7800000042')""")}
    assert rows["78О0000010"] == ("unknown", None, ["INVALID_INN_FORMAT"])
    assert rows["123456789"] == ("unknown", None, ["INVALID_INN_FORMAT"])
    assert rows["7800000042"] == ("legal_entity", "78", ["INVALID_INN_CHECKSUM"])


def test_missing_customer_inn_is_null_with_flag(test_db_url, loaded):
    (row,) = q(test_db_url, "SELECT customer_inn, customer_kpp, data_quality_flags FROM procurement_lot WHERE lot_id = '9900001'")
    assert row == (None, None, ["MISSING_INN", "MISSING_KPP", "ZERO_START_PRICE"])


def test_invalid_okpd2_preserved(test_db_url, loaded):
    rows = q(test_db_url, """SELECT okpd2_code_raw, okpd2_code, data_quality_flags FROM procurement_item
                             WHERE lot_id = '9900002' ORDER BY line_no""")
    assert ("22.19.6O.119", None, ["INVALID_OKPD2"]) in rows and ("04.11", None, ["INVALID_OKPD2"]) in rows
    assert ("33.12.1", "33.12.1", []) in rows


def test_decimal_prices(test_db_url, loaded):
    prices = dict(q(test_db_url, "SELECT lot_id, start_price FROM procurement_lot"))
    assert prices["5718896"] == Decimal("71985.00") and isinstance(prices["5718896"], Decimal)
    assert prices["4900162"] == Decimal("250000.50")
    assert prices["9900001"] == Decimal("0.00") and prices["9900002"] is None


def test_platform_and_coverage(test_db_url, loaded):
    rows = set(q(test_db_url, "SELECT platform, coverage_semantics FROM supplier_history"))
    assert rows == {("AIS_GZ", "WINNER_ROWS_ONLY_OBSERVED"), ("EM", "MIXED_WINNER_NONWINNER_ROWS_OBSERVED")}
    with psycopg.connect(test_db_url) as c, pytest.raises(psycopg.errors.CheckViolation):
        c.execute("UPDATE supplier_history SET coverage_semantics = 'MIXED_WINNER_NONWINNER_ROWS_OBSERVED' WHERE platform = 'AIS_GZ'")


def test_item_identity_and_line_order(test_db_url, loaded):
    rows = q(test_db_url, "SELECT item_id, lot_id, line_no, source_row_no FROM procurement_item ORDER BY source_row_no")
    for item_id, lot_id, line_no, _ in rows:
        assert item_id == ids.item_uuid(lot_id, line_no)
    lot2 = [(ln, rn) for _, lot, ln, rn in rows if lot == "9900002"]
    assert lot2 == [(1, 8), (2, 9), (3, 10), (4, 11), (5, 12)]  # file order within the lot


def test_hash_drift_stops_before_writing(test_db_url, slice_dir, tmp_path, loaded):
    before = q(test_db_url, "SELECT count(*) FROM raw_procurement_item")[0][0]
    wrong = {ds: {"sha256": "0" * 64, "size_bytes": 0} for ds in organizer.DATASETS}
    with pytest.raises(organizer.SourceDriftError):
        organizer.ingest_organizer(test_db_url, slice_dir, expected=wrong, reports_dir=tmp_path)
    assert json.loads((tmp_path / "source_drift_report.json").read_text(encoding="utf-8"))["drift"]
    assert q(test_db_url, "SELECT count(*) FROM raw_procurement_item")[0][0] == before


def test_canonical_rows_validate_against_contracts(test_db_url, loaded):
    """Read every canonical row back from PostgreSQL and validate it with the v0.2.0 JSON Schemas."""
    sys.path.insert(0, str(repo_root() / "scripts"))
    import validate_contracts as vc
    schemas = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (repo_root() / "contracts").glob("*.schema.json")}
    V = vc.Validator(schemas)

    def plain(v):
        if isinstance(v, Decimal):
            return format(v, "f")
        if hasattr(v, "isoformat"):
            return v.isoformat()
        if hasattr(v, "hex") and hasattr(v, "version"):
            return str(v)
        return v

    with psycopg.connect(test_db_url) as c:
        c.row_factory = psycopg.rows.dict_row
        tables = {
            "procurement_lot": "SELECT * FROM procurement_lot",
            "procurement_item": "SELECT * FROM procurement_item",
            "supplier_history": "SELECT * FROM supplier_history",
            "supplier": "SELECT * FROM supplier",
        }
        errors = []
        for ent, sql in tables.items():
            for row in c.execute(sql).fetchall():
                rec = {k: plain(v) for k, v in row.items()}
                sha = rec.pop("source_sha256", None)
                if ent == "procurement_item":
                    rec.pop("publish_date")  # physical index helper (migration 0003), not a contract field
                    rec["id"] = rec.pop("item_id")
                    rec["source_ref"] = {"dataset": "items_24_25", "row_number": rec.pop("source_row_no")}
                elif ent == "procurement_lot":
                    rec["source_ref"] = {"dataset": "notices_24_25", "row_number": rec.pop("source_row_no")}
                elif ent == "supplier_history":
                    rec["source_refs"] = [{"dataset": "suppliers_24_25", "row_number": n} for n in rec.pop("source_row_nos")]
                assert sha is None or len(sha) == 64
                errors += [f"{ent}: {e}" for e in V.validate(schemas[vc.ENTITY_SCHEMAS[ent]], rec, vc.ENTITY_SCHEMAS[ent])]
    assert errors == []


def test_reset_is_scoped_to_organizer_data(test_db_url, slice_dir):
    with psycopg.connect(test_db_url) as c:
        c.execute("""INSERT INTO supplier (supplier_id, inn, entity_type, inn_region_code, origin, first_seen_publish_date)
                     VALUES (%s, '4700000017', 'legal_entity', '47', 'EXTERNAL_ENRICHMENT', NULL) ON CONFLICT DO NOTHING""",
                  (ids.supplier_uuid("4700000017"),))
    organizer.ingest_organizer(test_db_url, slice_dir, use_pinned=False, reset=True)
    assert q(test_db_url, "SELECT count(*) FROM supplier WHERE origin = 'EXTERNAL_ENRICHMENT'")[0][0] == 1
    assert q(test_db_url, "SELECT count(*) FROM procurement_item")[0][0] == 12
