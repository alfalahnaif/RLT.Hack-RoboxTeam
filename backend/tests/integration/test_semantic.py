"""P2-001 semantic branch tests on a small synthetic database with a real (pinned) e5 encoder. Masked identifiers."""
from datetime import date

import numpy as np
import psycopg
import pytest

from app.ingestion.organizer import reset_organizer_data
from app.search import evaluation as E
from app.search import semantic, semantic_index, stats
from app.search.candidates import score_lots
from app.search.models import P2_003_RANKING
from app.search.recommend import recommend
from app.search.retrieval import build_query, restrict_semantic, retrieve
from app.shared import ids
from app.shared import normalize as N

pytestmark = pytest.mark.skipif(not semantic.LOCK.exists(), reason="semantic model not downloaded")

SHA = "0" * 64
INN = {"LAPTOP": "7800000010", "LOSE": "4715000038", "TECH": "7800000027", "FUTURE": "7800000098", "SAMEDAY": "780000000177",
       "TEXTFUT": "470000000239"}
SID = {k: str(ids.supplier_uuid(v)) for k, v in INN.items()}
# lot_id, date, subject, [(product_name, okpd2)], [(supplier, is_winner)]
LOTS = [
    ("Q", "2025-06-01", "Поставка оборудования", [("Персональный компьютер портативный", "26.20.11.110")], [("LAPTOP", True), ("LOSE", False)]),
    ("Q2", "2025-06-02", "Поставка оборудования", [("Персональный компьютер портативный", "26.20.11.110"),
                                                  ("Ноутбук Acer Aspire 5 A515-57-50R7", "26.20.11.110")], [("TECH", True), ("LOSE", False)]),
    ("H1", "2025-01-10", "Поставка", [("Ноутбук для учебного класса", "31.01.11.150")], [("LAPTOP", True), ("LOSE", False)]),
    ("H2", "2025-02-10", "Поставка", [("Ноутбук Acer Aspire 5 A515-57-50R7", "58.29.50.000")], [("TECH", True), ("LOSE", False)]),
    ("SAME", "2025-06-01", "Поставка", [("Переносной компьютер Lenovo", "31.01.11.150")], [("SAMEDAY", True), ("LOSE", False)]),
    ("FUT", "2025-09-01", "Поставка", [("Ноутбук для учебного класса", "31.01.11.150")], [("FUTURE", True), ("LOSE", False)]),
    ("TFUT", "2025-08-01", "Поставка", [("Мобильный компьютер HP", "31.01.11.150")], [("TEXTFUT", True), ("LOSE", False)]),
]
CFG = P2_003_RANKING.with_(semantic_top_k=10, top_k=100)


@pytest.fixture(scope="module")
def db(test_db_url):
    with psycopg.connect(test_db_url) as c:
        reset_organizer_data(c)
        first = {}
        for _lot, d, _s, _items, rels in LOTS:
            for s_, _w in rels:
                first[s_] = min(first.get(s_, d), d)
        for s_, inn in INN.items():
            n = N.normalize_inn(inn)
            c.execute("INSERT INTO supplier VALUES (%s, %s, %s, %s, 'ORGANIZER_DATA', %s, %s)",
                      (SID[s_], inn, n.entity_type, n.inn_region_code, first[s_], list(n.flags)))
        for k, (lot, d, subj, items, rels) in enumerate(LOTS, 1):
            c.execute("""INSERT INTO procurement_lot (lot_id, id, procedure_id, publish_date, platform, subject, start_price, is_smp,
                         customer_inn, has_supplier_history, data_quality_flags, source_sha256, source_row_no)
                         VALUES (%s, %s, %s, %s, 'EM', %s, 1000, false, '7800000300', true, '{MISSING_KPP}', %s, %s)""",
                      (lot, ids.lot_uuid(lot), f"p{k}", d, subj, SHA, k))
            for ln, (name, code) in enumerate(items, 1):
                o, pn = N.normalize_okpd2(code), N.normalize_product_name(name)
                c.execute("""INSERT INTO procurement_item VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '{}', %s, %s, %s)""",
                          (ids.item_uuid(lot, ln), lot, ln, SHA, name, pn.normalized, pn.has_generic_type_marker, code, o.okpd2_code,
                           o.okpd2_depth, o.okpd2_section, o.okpd2_class, o.okpd2_subclass, o.okpd2_group, o.okpd2_subgroup, o.okpd2_kind,
                           SHA, k * 1000 + ln, d))
            for j, (s_, win) in enumerate(rels):
                c.execute("INSERT INTO supplier_history VALUES (%s, %s, %s, %s, NULL, %s, 'EM', %s, %s, '{MISSING_KPP}', %s, %s)",
                          (ids.history_uuid(lot, INN[s_]), lot, SID[s_], INN[s_], win, d, "MIXED_WINNER_NONWINNER_ROWS_OBSERVED",
                           SHA, [k * 100 + j]))
        c.commit()
        stats.build(c, snapshot_before=date(2030, 1, 1))
        semantic_index.build(c, log=lambda m: None)
    with psycopg.connect(test_db_url) as conn:
        yield conn


def ranks(out):
    return {r["supplier_id"]: r["rank"] for r in out["results"]}


def test_embedding_deterministic():
    a = semantic.encode(["ноутбук acer", "перчатки нитриловые"], "document")
    b = semantic.encode(["ноутбук acer", "перчатки нитриловые"], "document")
    assert np.array_equal(a, b) and a.shape == (2, semantic.DIM)


def test_semantic_recovers_vocabulary_mismatch(db):
    off = ranks(recommend(db, "Q", P2_003_RANKING.with_(top_k=100)))
    db.rollback()
    on = recommend(db, "Q", CFG)
    db.rollback()
    assert SID["LAPTOP"] not in off                       # "персональный компьютер портативный" shares no lexeme/code with H1
    assert SID["LAPTOP"] in ranks(on)                     # H1 "ноутбук для учебного класса" found semantically
    laptop = next(r for r in on["results"] if r["supplier_id"] == SID["LAPTOP"])
    ev = laptop["semantic_evidence"][0]
    assert ev["lot_id"] == "H1" and ev["publish_date"] == "2025-01-10" and 0 < ev["cosine"] <= 1
    assert any(x.startswith("semantically similar historical product: «ноутбук для учебного класса»") for x in laptop["reasons"])


def test_future_same_day_and_future_text_excluded(db):
    q, idf = build_query(db, "Q", CFG)
    ret = retrieve(db, q, CFG, idf)
    db.rollback()
    lots = {it.lot_id for it in ret.items.values()}
    assert not {"SAME", "FUT", "TFUT", "Q", "Q2"} & lots          # same-day lot, future lot of a past text, future-only text
    assert all(it.publish_date < date(2025, 6, 1) for it in ret.items.values())
    out = ranks(recommend(db, "Q", CFG))
    db.rollback()
    assert not {SID["SAMEDAY"], SID["FUTURE"], SID["TEXTFUT"]} & set(out)


def test_exact_technical_identifier_still_lexical(db):
    q, idf = build_query(db, "Q2", CFG)
    ret = retrieve(db, q, CFG, idf)
    db.rollback()
    h2 = [it for it in ret.items.values() if it.lot_id == "H2"]
    assert h2 and h2[0].item_id in ret.lexical_ids              # found by the technical/FTS branches, not only semantically
    assert ret.branch_hits.get("technical", 0) > 0


def test_semantic_dedup_and_bounded_multi_item_aggregation(db):
    q, idf = build_query(db, "Q2", CFG)
    ret = retrieve(db, q, CFG, idf)
    db.rollback()
    assert len(ret.items) == len({it.item_id for it in ret.items.values()})
    assert {i for (i, _item) in ret.semantic} <= set(range(len(q.items)))
    for e in score_lots(q, ret, idf, CFG):
        assert 0.0 <= e.relevance <= 1.0 and all(0.0 <= m <= 1.0 for m in e.item_match)


def test_disabled_semantic_is_identical_to_p2_003(db):
    off = recommend(db, "Q2", P2_003_RANKING.with_(top_k=100))
    db.rollback()
    q, idf = build_query(db, "Q2", CFG)
    ret_on = retrieve(db, q, CFG, idf)
    db.rollback()
    q0, idf0 = build_query(db, "Q2", P2_003_RANKING)
    ret_off = retrieve(db, q0, P2_003_RANKING, idf0)
    view = restrict_semantic(ret_on, 0)
    assert set(view.items) == set(ret_off.items) and not view.semantic
    assert [r["supplier_id"] for r in off["results"]] == [r["supplier_id"] for r in recommend(db, "Q2", P2_003_RANKING.with_(top_k=100))["results"]]
    db.rollback()


def test_semantic_degrades_with_warning_when_model_missing(db, monkeypatch, tmp_path):
    monkeypatch.setattr(semantic, "LOCK", tmp_path / "missing.lock.json")
    out = recommend(db, "Q2", CFG)
    db.rollback()
    base = recommend(db, "Q2", P2_003_RANKING.with_(top_k=100))
    db.rollback()
    assert out["warnings"] and out["warnings"][0].startswith("SEMANTIC_UNAVAILABLE")
    assert [r["supplier_id"] for r in out["results"]] == [r["supplier_id"] for r in base["results"]]


def test_default_config_is_p2_001_semantic():
    from app.search.models import DEFAULT_CONFIG, P2_001_SEMANTIC
    assert DEFAULT_CONFIG == P2_001_SEMANTIC and P2_001_SEMANTIC.semantic_top_k == 100
    assert P2_001_SEMANTIC.with_(semantic_top_k=0) == P2_003_RANKING      # ranking weights frozen at P2-003


def test_holdout_still_refused(tmp_path):
    with pytest.raises(PermissionError):
        E.load_benchmark(tmp_path, {"holdout"})
