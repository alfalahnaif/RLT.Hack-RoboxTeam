"""P2-003 ranking unit tests on constructed evidence (no database): quality vs volume, saturation, multi-item coverage,
text redundancy, customer signal, fixed candidate pool, no win rate."""
from datetime import date, timedelta

import pytest

from app.search.candidates import LotEvidence, Pool, Relation
from app.search.models import P1_002_BASELINE, QueryItem, QueryLot
from app.search.scoring import COMPONENTS, rank_suppliers, text_redundancy

AS_OF = date(2025, 6, 1)


def q(n_items=1, subject="Поставка ноутбуков", names=None, customer="7800000300"):
    names = names or [f"ноутбук модель {i}" for i in range(n_items)]
    return QueryLot(as_of=AS_OF, subject=subject, customer_inn=customer,
                    items=[QueryItem(n, {"code": "26.20.11.110", "class": "26", "subclass": "26.2", "group": "26.20",
                                         "subgroup": "26.20.1", "kind": "26.20.11"}, ["ноутбук"]) for n in names])


def lot(i, rel, days_ago=30, item_match=(), text=None, okpd=None):
    return LotEvidence(f"L{i}", AS_OF - timedelta(days=days_ago), rel, rel if text is None else text, rel if okpd is None else okpd,
                       0.0, "ноутбук", "26.20.11.110", None, tuple(item_match) or (rel,))


def pool(spec, same_customer=()):
    """spec: {supplier: [(LotEvidence, is_winner, platform)]}"""
    lots, rels = {}, {}
    for s, rows in spec.items():
        for e, win, plat in rows:
            lots[e.lot_id] = e
            rels.setdefault(e.lot_id, []).append(Relation(e.lot_id, s, "7800000010", win, plat, e.publish_date))
    ordered = sorted(lots.values(), key=lambda e: (-e.relevance, e.lot_id))
    return Pool(lots=ordered, relations=rels, same_customer=set(same_customer))


def ranks(recs):
    return {r.supplier_id: r.rank for r in recs}


def strong_vs_volume():
    strong = [(lot(i, 0.95), True, "EM") for i in range(2)]
    weak = [(lot(100 + i, 0.25, text=0.25, okpd=0.4), i % 2 == 0, "EM") for i in range(60)]
    return pool({"strong": strong, "volume": weak})


def test_quality_component_beats_weak_volume():
    cfg = P1_002_BASELINE.with_(w_historical_relevance=0.0, w_evidence_quality=0.20)
    r = ranks(rank_suppliers(q(), strong_vs_volume(), cfg)[0])
    assert r["strong"] < r["volume"]


def test_saturation_is_bounded_and_quality_ignores_weak_volume():
    recs = {x.supplier_id: x for x in rank_suppliers(q(), strong_vs_volume(), P1_002_BASELINE)[0]}
    assert all(0.0 <= v <= 1.0 for x in recs.values() for v in x.components.values())
    assert recs["volume"].components["historical_relevance"] < 1.0
    assert recs["strong"].components["evidence_quality"] == pytest.approx((0.95 + 0.95 + 0.0) / 3, abs=1e-4)
    assert recs["volume"].components["evidence_quality"] == pytest.approx(0.25, abs=1e-4)   # 60 weak lots never exceed their own level


def test_multi_item_coverage_is_bounded_and_multi_item_only():
    two = q(n_items=2)
    p = pool({"both": [(lot(1, 0.8, item_match=(0.8, 0.0)), True, "EM"), (lot(2, 0.8, item_match=(0.0, 0.8)), False, "EM")],
              "one": [(lot(3, 0.8, item_match=(0.8, 0.0)), True, "EM"), (lot(4, 0.8, item_match=(0.8, 0.0)), False, "EM")]})
    cfg = P1_002_BASELINE.with_(w_item_coverage=0.15)
    recs = {x.supplier_id: x for x in rank_suppliers(two, p, cfg)[0]}
    assert recs["both"].components["item_coverage"] == pytest.approx(0.8) and recs["one"].components["item_coverage"] == pytest.approx(0.4)
    assert recs["both"].rank < recs["one"].rank
    single = {x.supplier_id: x for x in rank_suppliers(q(1), pool({"a": [(lot(5, 0.8), True, "EM")]}), cfg)[0]}
    assert "item_coverage" not in single["a"].contributions          # not applicable to single-item queries


def test_text_redundancy_detection_and_rule():
    assert text_redundancy(q(names=["поставка интерактивной панели"], subject="Поставка интерактивной панели"), 0.8) == 1.0
    assert text_redundancy(q(names=["ноутбук acer aspire 5 a515-57-50r7"], subject="Поставка компьютерного оборудования"), 0.8) == 0.0
    redundant = q(names=["поставка интерактивной панели"], subject="Поставка интерактивной панели")
    p = pool({"a": [(lot(1, 0.6), True, "EM")]})
    base = rank_suppliers(redundant, p, P1_002_BASELINE)[0][0]
    down = rank_suppliers(redundant, p, P1_002_BASELINE.with_(redundant_text_factor=0.5))[0][0]
    assert down.contributions["product_text"] < base.contributions["product_text"]
    assert base.diagnostics["query_text_redundant"] is True


def test_customer_signal_is_optional_and_supporting():
    p = pool({"inc": [(lot(1, 0.5), True, "EM")], "new": [(lot(2, 0.9), True, "EM")]}, same_customer={"inc"})
    recs = {x.supplier_id: x for x in rank_suppliers(q(), p, P1_002_BASELINE)[0]}
    assert recs["new"].rank < recs["inc"].rank                            # much stronger relevance beats incumbency
    assert recs["inc"].contributions["same_customer"] <= P1_002_BASELINE.w_same_customer
    off = rank_suppliers(q(), p, P1_002_BASELINE.with_(w_same_customer=0.0))[0]
    assert all("same_customer" not in x.contributions for x in off)
    nocust = rank_suppliers(q(customer=None), p, P1_002_BASELINE)[0]
    assert all("same_customer" not in x.contributions for x in nocust)    # not applicable without a known customer


def test_candidate_pool_identical_across_scoring_configs():
    p = strong_vs_volume()
    cfgs = [P1_002_BASELINE, P1_002_BASELINE.with_(w_evidence_quality=0.2, w_historical_relevance=0.0),
            P1_002_BASELINE.with_(w_recency=0.0), P1_002_BASELINE.with_(redundant_text_factor=0.5, w_item_coverage=0.15)]
    pools = [sorted(r.supplier_id for r in rank_suppliers(q(), p, c)[0]) for c in cfgs]
    assert all(x == pools[0] for x in pools)


def test_no_win_rate_and_contributions_sum_to_score():
    assert not any("rate" in c for c in COMPONENTS)
    for cfg in (P1_002_BASELINE, P1_002_BASELINE.with_(w_evidence_quality=0.2, w_item_coverage=0.15)):
        for r in rank_suppliers(q(2), strong_vs_volume(), cfg)[0]:
            assert abs(sum(r.contributions.values()) - r.score) < 1e-3
            assert r.diagnostics["distinct_products"] >= 1 and 0 < r.diagnostics["top_lot_share"] <= 1


def test_ais_wins_are_awards_not_participation():
    p = pool({"ais": [(lot(1, 0.9), True, "AIS_GZ")]})
    r = rank_suppliers(q(), p, P1_002_BASELINE)[0][0]
    assert r.relevant_awards == 1 and r.relevant_em_participations == 0 and r.components["em_participation"] == 0.0
