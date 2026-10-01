"""P1-001E temporal benchmark tests on a small synthetic database (masked identifiers)."""
from datetime import date

import psycopg
import pytest

from app.benchmark import temporal as T
from app.ingestion.organizer import reset_organizer_data
from app.shared import ids

SPLITS = [T.Split("warmup", date(2024, 7, 1), date(2024, 12, 31), 100),
          T.Split("dev", date(2025, 1, 1), date(2025, 6, 30), 100),
          T.Split("holdout", date(2025, 7, 1), date(2025, 12, 31), 100)]
INN = {"A": "7800000010", "B": "4715000038", "C": "7800000027", "D": "7800000098", "E": "780000000177"}
SID = {k: str(ids.supplier_uuid(v)) for k, v in INN.items()}
SHA = "0" * 64

# lot_id, date, platform, okpd2 codes, relations [(supplier, is_winner)]
LOTS = [
    ("H1", "2024-08-01", "EM", ["26.20.11.110"], [("A", True), ("B", False)]),          # warm-up + history for A
    ("W_DEC31", "2024-12-31", "EM", ["31.01.11.150"], [("B", True), ("C", False)]),     # warm-up boundary
    ("D_JAN01", "2025-01-01", "EM", ["31.01.11.150"], [("B", True), ("E", False)]),     # dev boundary
    ("D_EASY", "2025-03-10", "EM", ["26.20.11.110"], [("A", True), ("C", False)]),      # A seen same code before -> EASY
    ("SAMEDAY", "2025-05-05", "EM", ["22.19.60.119"], [("D", False), ("E", False), ("C", True)]),  # same day as D_HARD
    ("D_HARD", "2025-05-05", "EM", ["22.19.60.119"], [("D", True), ("E", False)]),      # D only seen same day / later -> HARD
    ("D_MEDIUM", "2025-06-01", "EM", ["26.20.13.000"], [("A", True), ("B", False)]),    # A seen in group 26.20 only -> MEDIUM
    ("D_JUN30", "2025-06-30", "EM", ["31.01.11.150"], [("B", True), ("A", True), ("C", False)]),  # dev boundary + 2 winners
    ("H_JUL01", "2025-07-01", "EM", ["22.19.60.119"], [("D", True), ("B", False)]),     # holdout boundary (D now seen)
    ("H_DEC31", "2025-12-31", "EM", ["26.20.11.110"], [("A", True), ("E", False)]),     # holdout boundary
    ("X_NOWIN", "2025-02-02", "EM", ["26.20.11.110"], [("A", False), ("B", False)]),    # excluded: no winner
    ("X_SINGLE", "2025-02-03", "EM", ["26.20.11.110"], [("A", True)]),                  # excluded: single relation
    ("X_AIS", "2025-02-04", "AIS_GZ", ["26.20.11.110"], [("A", True), ("B", True)]),    # excluded: not EM
    ("X_NOITEMS", "2025-02-05", "EM", [], [("A", True), ("B", False)]),                 # excluded: no items
    ("5718896", "2025-06-16", "EM", ["26.20.11.110"], [("C", True), ("A", False)]),     # excluded: golden
    ("FUTURE", "2026-01-15", "EM", ["22.19.60.119"], [("D", True), ("A", False)]),      # outside splits; future for D
]
EXPECTED = {"warmup": {"H1", "W_DEC31"}, "dev": {"D_JAN01", "D_EASY", "SAMEDAY", "D_HARD", "D_MEDIUM", "D_JUN30"},
            "holdout": {"H_JUL01", "H_DEC31"}}


@pytest.fixture(scope="module")
def db(test_db_url):
    with psycopg.connect(test_db_url) as c:
        reset_organizer_data(c)
        first_seen = {}
        for lot, d, plat, codes, rels in LOTS:
            for s, _ in rels:
                first_seen[s] = min(first_seen.get(s, d), d)
        for s, inn in INN.items():
            c.execute("INSERT INTO supplier VALUES (%s, %s, %s, %s, 'ORGANIZER_DATA', %s, '{}')",
                      (SID[s], inn, "legal_entity" if len(inn) == 10 else "individual_entrepreneur", inn[:2], first_seen[s]))
        for n, (lot, d, plat, codes, rels) in enumerate(LOTS, 1):
            c.execute("""INSERT INTO procurement_lot (lot_id, id, procedure_id, publish_date, platform, subject, start_price, is_smp,
                         customer_inn, customer_kpp, has_supplier_history, data_quality_flags, source_sha256, source_row_no)
                         VALUES (%s, %s, %s, %s, %s, 'Поставка товара', 1000, false, '7800000010', '780101001', true, '{}', %s, %s)""",
                      (lot, ids.lot_uuid(lot), f"p{n}", d, plat, SHA, n))
            for ln, code in enumerate(codes, 1):
                grp = code[:5]
                c.execute("""INSERT INTO procurement_item (item_id, lot_id, line_no, content_hash, product_name_raw, product_name_normalized,
                             is_generic_type_name, okpd2_code_raw, okpd2_code, okpd2_depth, okpd2_section, okpd2_class, okpd2_subclass,
                             okpd2_group, okpd2_subgroup, okpd2_kind, data_quality_flags, source_sha256, source_row_no, publish_date)
                             VALUES (%s, %s, %s, %s, 'товар', 'товар', false, %s, %s, 4, 'C', %s, %s, %s, %s, %s, '{}', %s, %s, %s)""",
                          (ids.item_uuid(lot, ln), lot, ln, SHA, code, code, code[:2], code[:4], grp, code[:7], code[:8], SHA, n * 10 + ln, d))
            for k, (s, win) in enumerate(rels):
                cov = "WINNER_ROWS_ONLY_OBSERVED" if plat == "AIS_GZ" else "MIXED_WINNER_NONWINNER_ROWS_OBSERVED"
                c.execute("""INSERT INTO supplier_history VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, '{MISSING_KPP}', %s, %s)""",
                          (ids.history_uuid(lot, INN[s]), lot, SID[s], INN[s], win, plat, d, cov, SHA, [n * 100 + k]))
    with psycopg.connect(test_db_url) as conn:
        yield conn


def test_selection_respects_eligibility_splits_and_golden(db):
    b = T.build(db, SPLITS, seed=1)
    got = {sp: {q["lot_id"] for q in b.queries if q["split"] == sp} for sp in EXPECTED}
    assert got == EXPECTED
    assert all(q["platform"] == "EM" for q in b.queries)


def test_labels_and_multiple_winners(db):
    b = T.build(db, SPLITS, seed=1)
    q = {(r["supplier_id"], r["relevance_grade"], r["is_winner"]) for r in b.qrels if r["query_id"] == "rpl-D_JUN30"}
    assert q == {(SID["B"], 2, True), (SID["A"], 2, True), (SID["C"], 1, False)}
    assert len({(r["query_id"], r["supplier_id"]) for r in b.qrels}) == len(b.qrels)


def test_difficulty_uses_strictly_earlier_history_only(db):
    meta = {m["query_id"]: m for m in T.build(db, SPLITS, seed=1).metadata}
    assert meta["rpl-D_EASY"]["difficulty"] == "EASY"
    assert meta["rpl-D_MEDIUM"]["difficulty"] == "MEDIUM"
    hard = meta["rpl-D_HARD"]     # D's other relations are same-day (SAMEDAY) and later (H_JUL01, FUTURE)
    assert hard["difficulty"] == "HARD" and hard["winner_seen_before_anywhere"] is False
    assert meta["rpl-H_JUL01"]["difficulty"] == "EASY"     # by July, D_HARD (May) is visible history
    assert meta["rpl-D_JAN01"]["winner_seen_same_okpd2"] is True  # W_DEC31 (2024-12-31) is visible for 2025-01-01


def test_visible_history_excludes_same_day_and_future(db):
    rows = T.visible_history(db, date(2025, 5, 5), [SID["D"]])
    assert rows == []                                   # D: only 2025-05-05 (same day), 2025-07-01, 2026-01-15
    rows = T.visible_history(db, date(2025, 7, 2), [SID["D"]])
    assert {r["lot_id"] for r in rows} == {"SAMEDAY", "D_HARD", "H_JUL01"}
    assert all(r["publish_date"] < date(2025, 7, 2) for r in T.visible_history(db, date(2025, 7, 2)))


def test_leakage_probe_is_exercised_and_clean(db):
    probe = T.leakage_probe(db, [lot for lot, *_ in LOTS])
    assert probe["violations"] == 0
    assert probe["same_day_relations_excluded"] > 0 and probe["future_relations_excluded"] > 0


def test_generation_is_deterministic_and_validates(db, tmp_path):
    a, fa = T.generate(db, tmp_path / "a", seed=7, splits=SPLITS)
    b, fb = T.generate(db, tmp_path / "b", seed=7, splits=SPLITS)
    assert fa == fb
    result = T.validate(db, tmp_path / "a", splits=SPLITS)
    assert result["passed"], result["checks"]


def test_validator_detects_tampering(db, tmp_path):
    T.generate(db, tmp_path, seed=7, splits=SPLITS)
    qrels = (tmp_path / "qrels.csv").read_text(encoding="utf-8").replace(",2,true", ",1,true", 1)
    (tmp_path / "qrels.csv").write_text(qrels, encoding="utf-8")
    checks = T.validate(db, tmp_path, splits=SPLITS)["checks"]
    assert not checks["06 winners graded 2"] and not checks["10c file checksums match manifest"]


@pytest.mark.parametrize("sizes,total,expected_total", [({"C": 900, "G": 100, "Q": 1}, 100, 100), ({"C": 5, "G": 3}, 50, 8), ({}, 10, 0)])
def test_allocation(sizes, total, expected_total):
    alloc = T.allocate(sizes, total)
    assert sum(alloc.values()) == expected_total and all(alloc[k] <= sizes[k] for k in alloc)
    if sizes == {"C": 900, "G": 100, "Q": 1}:
        assert alloc["Q"] == 1 and alloc["C"] < 90     # sqrt damping vs proportional 89.9


# ---------------------------------------------------------------------------- P1-001F golden cards
def test_golden_card_uses_strict_history_and_matches_db(db, tmp_path):
    from app.benchmark import golden as G
    card = G.build_card(db, "D_HARD")
    assert card["temporal_history"]["winner_seen_before_anywhere"] is False   # same-day / future relations invisible
    assert card["descriptive_difficulty"]["winner_prior_same_okpd2_awards"] == [0]
    easy = G.build_card(db, "D_EASY")
    assert easy["temporal_history"]["winner_seen_same_okpd2"] is True
    # A's earlier same-code wins: H1 (2024-08-01), X_SINGLE (2025-02-03), X_AIS (2025-02-04) — benchmark-excluded lots are still history;
    # D_JUN30 / H_DEC31 (later) must not count
    assert easy["descriptive_difficulty"]["winner_prior_same_okpd2_awards"] == [3]
    assert easy["observed_supplier_relations"] == 2 and easy["winner_count"] == 1 and easy["okpd2_codes"] == ["26.20.11.110"]


def csv_text(*rows):
    return "".join(line + "\n" for line in ["query_id,lot_id,publish_date,split,platform", *rows])


def test_golden_validation_overlap_and_tamper(db, tmp_path, monkeypatch):
    from app.benchmark import golden as G
    sel = [{"lot_id": l, "role": r, "capabilities": [], "why": "t", "story": {"input": "i", "evidence": "e", "expected_capability": "c"} if r == "primary" else None}
           for l, r in [("D_EASY", "primary"), ("D_HARD", "primary"), ("D_MEDIUM", "primary"), ("H_JUL01", "backup"), ("H_DEC31", "backup")]]
    monkeypatch.setattr(G, "SELECTION", sel)
    G.write(G.build(db), tmp_path)
    q = tmp_path / "queries.csv"
    q.write_text(csv_text('rpl-X,OTHER,2025-01-01,dev,EM'), encoding="utf-8")
    assert G.validate(db, tmp_path, q)["passed"]
    q.write_text(csv_text('rpl-D_HARD,D_HARD,2025-05-05,dev,EM'), encoding="utf-8")
    assert not G.validate(db, tmp_path, q)["checks"]["no overlap with benchmark/replay/queries.csv"]
    doc = (tmp_path / "golden_cases.json").read_text(encoding="utf-8").replace('"winner_count": 1', '"winner_count": 9', 1)
    (tmp_path / "golden_cases.json").write_text(doc, encoding="utf-8")
    q.write_text(csv_text(), encoding="utf-8")
    assert not G.validate(db, tmp_path, q)["checks"]["stored facts match PostgreSQL"]
