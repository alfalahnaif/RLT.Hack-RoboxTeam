"""P1-002 baseline retrieval/ranking tests on a small synthetic database (masked identifiers)."""
from datetime import date

import psycopg
import pytest

from app.ingestion.organizer import reset_organizer_data
from app.search import evaluation as E
from app.search import stats
from app.search.candidates import okpd2_similarity, score_lots
from app.search.models import SearchConfig
from app.search.recommend import recommend
from app.search.retrieval import build_query, retrieve
from app.shared import ids
from app.shared import normalize as N

SHA = "0" * 64
ACER = 'Ноутбук Acer Aspire 5 A515-57-50R7 15.6"'
MFU = "МФУ HP LaserJet Pro 4103dw"
INN = {k: v for k, v in {"EXACT": "7800000010", "LOSE": "4715000038", "PARENT": "7800000027", "SUBJ": "7800000098",
                         "SAMEDAY": "780000000177", "FUTURE": "470000000239", "BIG": "7800000213", "AIS": "7800000220",
                         "MFU": "7800000237"}.items()}
SID = {k: str(ids.supplier_uuid(v)) for k, v in INN.items()}

# lot_id, date, platform, subject, customer, [(product_name, okpd2)], [(supplier, is_winner)]
LOTS = [
    ("T", "2025-06-01", "EM", "Поставка компьютерного оборудования", "7800000300", [(ACER, "26.20.11.110")], [("EXACT", True), ("LOSE", False)]),
    ("T2", "2025-06-02", "EM", "Поставка компьютерной техники", "7800000300", [(ACER, "26.20.11.110"), (MFU, "26.20.18.120")], [("EXACT", True), ("MFU", False)]),
    ("L1", "2025-01-10", "EM", "Поставка ноутбука", "7800000300", [("Ноутбук Acer Aspire 5 A515-57-50R7", "26.20.11.110")], [("EXACT", True), ("LOSE", False)]),
    ("L2", "2025-02-10", "EM", "Поставка моноблока", "7800000400", [("Моноблок Lenovo IdeaCentre", "26.20.15.000")], [("PARENT", True), ("LOSE", False)]),
    ("L3", "2025-03-10", "EM", "Поставка компьютерного оборудования", "7800000400", [("Кресло офисное", "31.01.11.150")], [("SUBJ", True), ("LOSE", False)]),
    ("L4", "2025-03-01", "AIS_GZ", "Ноутбук", "7800000400", [("Ноутбук Acer Aspire 5 A515-57-50R7", "26.20.11.110")], [("AIS", True)]),
    ("L5", "2025-05-01", "EM", "Поставка МФУ", "7800000400", [(MFU, "26.20.18.120")], [("MFU", True), ("LOSE", False)]),
    ("BIG", "2025-04-01", "EM", "Поставка", "7800000400", [("Ноутбук Acer Aspire 5 A515-57-50R7", "26.20.11.110")] * 50, [("BIG", True), ("LOSE", False)]),
    ("SAME", "2025-06-01", "EM", "Поставка ноутбука", "7800000300", [(ACER, "26.20.11.110")], [("SAMEDAY", True), ("LOSE", False)]),
    ("FUT", "2025-09-01", "EM", "Поставка ноутбука", "7800000300", [(ACER, "26.20.11.110")], [("FUTURE", True), ("LOSE", False)]),
]


@pytest.fixture(scope="module")
def db(test_db_url):
    with psycopg.connect(test_db_url) as c:
        reset_organizer_data(c)
        first = {}
        for lot, d, plat, subj, cust, items, rels in LOTS:
            for s, _ in rels:
                first[s] = min(first.get(s, d), d)
        for s, inn in INN.items():
            n = N.normalize_inn(inn)
            c.execute("INSERT INTO supplier VALUES (%s, %s, %s, %s, 'ORGANIZER_DATA', %s, %s)",
                      (SID[s], inn, n.entity_type, n.inn_region_code, first[s], list(n.flags)))
        for k, (lot, d, plat, subj, cust, items, rels) in enumerate(LOTS, 1):
            c.execute("""INSERT INTO procurement_lot (lot_id, id, procedure_id, publish_date, platform, subject, start_price, is_smp,
                         customer_inn, has_supplier_history, data_quality_flags, source_sha256, source_row_no)
                         VALUES (%s, %s, %s, %s, %s, %s, 1000, false, %s, true, '{MISSING_KPP}', %s, %s)""",
                      (lot, ids.lot_uuid(lot), f"p{k}", d, plat, subj, cust, SHA, k))
            for ln, (name, code) in enumerate(items, 1):
                o, pn = N.normalize_okpd2(code), N.normalize_product_name(name)
                c.execute("""INSERT INTO procurement_item VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '{}', %s, %s, %s)""",
                          (ids.item_uuid(lot, ln), lot, ln, SHA, name, pn.normalized, pn.has_generic_type_marker, code, o.okpd2_code,
                           o.okpd2_depth, o.okpd2_section, o.okpd2_class, o.okpd2_subclass, o.okpd2_group, o.okpd2_subgroup, o.okpd2_kind,
                           SHA, k * 1000 + ln, d))
            for j, (s, win) in enumerate(rels):
                cov = N.coverage_semantics(plat)
                c.execute("INSERT INTO supplier_history VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, '{MISSING_KPP}', %s, %s)",
                          (ids.history_uuid(lot, INN[s]), lot, SID[s], INN[s], win, plat, d, cov, SHA, [k * 100 + j]))
        c.commit()
        stats.build(c, snapshot_before=date(2030, 1, 1))
    with psycopg.connect(test_db_url) as conn:
        yield conn


def ranks(out):
    return {r["supplier_id"]: r["rank"] for r in out["results"]}


CFG = SearchConfig().with_(top_k=100)


def test_strict_temporal_cutoff_same_day_and_future_excluded(db):
    out = recommend(db, "T", CFG)
    r = ranks(out)
    assert SID["SAMEDAY"] not in r and SID["FUTURE"] not in r
    q, idf = build_query(db, "T", CFG)
    ret = retrieve(db, q, CFG, idf)
    assert ret.items and all(it.publish_date < date(2025, 6, 1) for it in ret.items.values())
    assert not {"SAME", "FUT", "T", "T2"} & {it.lot_id for it in ret.items.values()}


def test_exact_okpd2_and_text_above_parent_only(db):
    r = ranks(recommend(db, "T", CFG))
    # PARENT only shares the OKPD2 group (26.20) with no text overlap: for a kind-level query the broad branch searches the
    # kind (26.20.11), so it is not even a candidate; if it ever is, it must rank below the exact match.
    assert r[SID["EXACT"]] == 1
    assert SID["PARENT"] not in r or r[SID["PARENT"]] > r[SID["EXACT"]]


def test_technical_token_retrieval(db):
    q, idf = build_query(db, "T2", CFG)
    assert "a515-57-50r7" in q.items[0].tech_tokens and "4103dw" in q.items[1].tech_tokens
    ret = retrieve(db, q, CFG, idf)
    assert ret.branch_hits.get("technical", 0) > 0
    assert {"L1", "L5"} <= {it.lot_id for it in ret.items.values()}


def test_generic_subject_does_not_override_item_evidence(db):
    out = recommend(db, "T", CFG)
    r = ranks(out)
    assert SID["SUBJ"] not in r or r[SID["SUBJ"]] > r[SID["EXACT"]]


def test_multi_item_multi_okpd2_query(db):
    out = recommend(db, "T2", CFG)
    assert [i["okpd2"] for i in out["query"]["items"]] == ["26.20.11.110", "26.20.18.120"]
    r = ranks(out)
    assert SID["MFU"] in r and SID["EXACT"] in r


def test_large_lot_evidence_is_capped(db):
    q, idf = build_query(db, "T", CFG)
    lots = {e.lot_id: e for e in score_lots(q, retrieve(db, q, CFG, idf), idf, CFG)}
    assert lots["BIG"].relevance == pytest.approx(lots["L1"].relevance)


def test_supplier_dedup_and_no_win_rate(db):
    out = recommend(db, "T", CFG)
    ids_ = [r["supplier_id"] for r in out["results"]]
    assert len(ids_) == len(set(ids_))
    for r in out["results"]:
        assert not any("rate" in k for k in r["components"]) and not any("rate" in k for k in r)


def test_ais_awards_are_not_participation(db):
    ais = next(r for r in recommend(db, "T", CFG)["results"] if r["supplier_id"] == SID["AIS"])
    assert ais["relevant_awards"] == 1 and ais["relevant_ais_awards"] == 1 and ais["relevant_em_participations"] == 0
    assert ais["components"]["em_participation"] == 0.0


def test_deterministic_output(db):
    a, b = recommend(db, "T2", CFG), recommend(db, "T2", CFG)
    for x in (a, b):
        x.pop("timings_ms")
        x["retrieval"].pop("branch_ms")   # wall-clock SQL timings legitimately differ
    assert a == b


def test_explanations_match_evidence(db):
    out = recommend(db, "T", CFG)
    rels = {(r[0], r[1]) for r in db.execute("SELECT lot_id, supplier_id::text FROM supplier_history").fetchall()}
    for r in out["results"]:
        assert r["reasons"][0].startswith(f"matched {r['relevant_lots']} ")
        assert any(x.startswith(f"{r['relevant_awards']} relevant historical award") for x in r["reasons"])
        assert all((lot, r["supplier_id"]) in rels for lot in r["evidence_lot_ids"])
        assert abs(sum(r["contributions"].values()) - r["score"]) < 1e-3


@pytest.mark.parametrize("q,h,expected", [
    ("26.20.11.110", "26.20.11.110", 1.0), ("21.20", "21.20.23.110", 0.8), ("26.20.11.110", "26.20.11.120", 0.7),
    ("26.20.11.110", "26.20.15.000", 0.55), ("26.20.11.110", "26.20.20.000", 0.4), ("26.20.11.110", "26.21.11.000", 0.25),
    ("26.20.11.110", "26.30.11.110", 0.1), ("26.20.11.110", "27.20.11.110", 0.0), ("33.12.1", "33.12.19.000", 0.8),
    ("33.12.19.000", "33.12.1", 0.8), ("33.12.1", "33.12.29.000", 0.4), ("21.20", "21.20", 1.0),
])
def test_okpd2_similarity_mixed_depth(q, h, expected):
    def d(c):
        o = N.normalize_okpd2(c)
        return {"code": o.okpd2_code, "class": o.okpd2_class, "subclass": o.okpd2_subclass, "group": o.okpd2_group,
                "subgroup": o.okpd2_subgroup, "kind": o.okpd2_kind}
    assert okpd2_similarity(d(q), d(h)) == expected


def test_metrics_separate_coverage_from_ranking():
    ranked = [f"s{i}" for i in range(40)]
    m = E.query_metrics(ranked, {"s29": 2, "s1": 1})
    assert m["candidate_winner_coverage"] == 1.0 and m["winner_recall@10"] == 0.0 and m["winner_rank"] == 30
    assert m["observed_recall@10"] == 0.5 and m["winner_mrr"] == pytest.approx(1 / 30)
    m2 = E.query_metrics(ranked, {"zz": 2})
    assert m2["candidate_winner_coverage"] == 0.0 and m2["winner_mrr"] == 0.0


def test_holdout_is_refused(tmp_path):
    with pytest.raises(PermissionError):
        E.load_benchmark(tmp_path, {"dev", "holdout"})
