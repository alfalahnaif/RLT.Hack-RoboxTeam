"""Historical lot aggregation and supplier candidate generation (P1-002).

Lot relevance (bounded, large lots cannot dominate):
  for every query item take the BEST matching retrieved item of the historical lot (text and OKPD2 separately);
  lot_text = mean over query items of best text similarity; lot_okpd2 = mean over query items with OKPD2 of best OKPD2 score;
  lot_subject = IDF-weighted overlap of the subjects; relevance = normalized weighted fusion of the applicable components.
  A lot with 3,000 matching items scores exactly like a lot with one equally good item.
Candidates: suppliers related (any role) to the top `historical_lot_limit` lots, all relations with publish_date < as_of (SQL).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.benchmark.temporal import visible
from app.search.models import QueryItem, QueryLot, SearchConfig
from app.search.retrieval import HistItem, Retrieval
from app.search.stats import Idf

OKPD_LEVEL_SCORES = {"kind": 0.7, "subgroup": 0.55, "group": 0.4, "subclass": 0.25, "class": 0.1}
_DEPTH_ORDER = ["class", "subclass", "group", "subgroup", "kind"]


def _deepest(o: dict) -> str | None:
    """Deepest hierarchy level the code itself denotes (None for a full 4-segment code, whose detail is only in `code`)."""
    if o["code"].count(".") == 3:
        return None
    for level in reversed(_DEPTH_ORDER):
        if o.get(level):
            return level
    return None


def okpd2_similarity(q: dict | None, h: dict | None) -> float:
    """exact code 1.0 > query fully contained in a deeper/shallower code of the same branch 0.8 > shared kind 0.7 > subgroup 0.55 >
    group 0.4 > subclass 0.25 > class 0.1 > 0. Mixed depths supported; codes are never padded."""
    if not q or not h:
        return 0.0
    if q["code"] == h["code"]:
        return 1.0
    lq, lh = _deepest(q), _deepest(h)
    if (lq and h.get(lq) == q[lq]) or (lh and q.get(lh) == h[lh]):   # one code lies inside the other's branch (mixed depth)
        return 0.8
    for level in reversed(_DEPTH_ORDER):
        if q.get(level) and q.get(level) == h.get(level):
            return OKPD_LEVEL_SCORES[level]
    return 0.0


def semantic_norm(cosine: float, cfg: SearchConfig) -> float:
    """Fixed calibration of e5 cosine to [0, 1] (floor/ceiling from the feasibility study; not tuned on DEV)."""
    return min(1.0, max(0.0, (cosine - cfg.semantic_floor) / (cfg.semantic_ceiling - cfg.semantic_floor)))


def text_similarity(qi: QueryItem, h: HistItem, idf: Idf) -> float:
    """IDF-weighted share of the query item's features present in the historical item; technical tokens count as exact
    substrings with maximum weight. Bounded in [0, 1]."""
    feats = {lx: idf.weight(lx) for lx in set(qi.lexemes)}
    tech = {t: idf.max_weight for t in qi.tech_tokens}
    total = sum(feats.values()) + sum(tech.values())
    if total == 0:
        return 0.0
    got = sum(w for lx, w in feats.items() if lx in h.lexemes)
    got += sum(w for t, w in tech.items() if h.name and t in h.name)
    return got / total


@dataclass
class LotEvidence:
    lot_id: str
    publish_date: object
    relevance: float
    text: float
    okpd2: float
    subject: float
    best_item_name: str | None
    best_item_okpd2: str | None
    customer_inn: str | None = None
    item_match: tuple = ()   # per query item (q.items order): best combined text/OKPD2 match in this lot, in [0, 1]
    semantic_cosine: float | None = None   # P2-001: raw cosine of the best item when its text evidence came from the semantic branch
    # P2-001 provenance (not scored): the semantically retrieved item of this lot with the highest raw cosine, kept even when lexical
    # similarity is the larger text component. None when the semantic branch retrieved no item of this lot.
    semantic_discovery: dict | None = None


def score_lots(q: QueryLot, ret: Retrieval, idf: Idf, cfg: SearchConfig) -> list[LotEvidence]:
    by_lot: dict[str, list[HistItem]] = defaultdict(list)
    for it in ret.items.values():
        by_lot[it.lot_id].append(it)
    q_index = {id(qi): i for i, qi in enumerate(q.items)}
    qtext = [qi for qi in q.items if qi.lexemes or qi.tech_tokens or any(k[0] == q_index[id(qi)] for k in ret.semantic)]
    qokpd = [qi for qi in q.items if qi.okpd2]
    subj_w = {lx: idf.weight(lx) for lx in set(q.subject_lexemes)}
    subj_total = sum(subj_w.values())
    weights = {"text": cfg.w_lot_text if qtext else 0.0, "okpd2": cfg.w_lot_okpd2 if qokpd else 0.0,
               "subject": cfg.w_lot_subject if subj_total else 0.0}
    wsum = sum(weights.values()) or 1.0
    out = []
    for lot_id in sorted(by_lot):
        items = sorted(by_lot[lot_id], key=lambda it: it.item_id)
        best_t, best_o, best_item, best_item_score, best_sem = [], [], None, -1.0, None
        for qi in qtext:
            qidx = q_index[id(qi)]
            sims = []
            for it in items:
                lex = text_similarity(qi, it, idf)
                sem = ret.semantic.get((qidx, it.item_id))
                sem_eff = cfg.semantic_weight * semantic_norm(sem[0], cfg) if sem else 0.0
                sims.append((max(lex, sem_eff), it, sem[0] if sem and sem_eff > lex else None))
            s, it, cos = max(sims, key=lambda x: (x[0], x[1].item_id))
            best_t.append(s)
            if s > best_item_score:
                best_item_score, best_item, best_sem = s, it, cos
        for qi in qokpd:
            best_o.append(max(okpd2_similarity(qi.okpd2, it.okpd2) for it in items))
        t_by, o_by = dict(zip(map(id, qtext), best_t)), dict(zip(map(id, qokpd), best_o))
        item_match = []
        for qi in q.items:   # per requested item: text + OKPD2 with the lot-fusion weights (subject excluded), bounded
            parts = [(cfg.w_lot_text, t_by[id(qi)])] if id(qi) in t_by else []
            parts += [(cfg.w_lot_okpd2, o_by[id(qi)])] if id(qi) in o_by else []
            wt = sum(p_[0] for p_ in parts)
            item_match.append(sum(w_ * v for w_, v in parts) / wt if wt else 0.0)
        text = sum(best_t) / len(best_t) if best_t else 0.0
        okpd = sum(best_o) / len(best_o) if best_o else 0.0
        subj_lex = ret.lot_subject_lexemes.get(lot_id, frozenset())
        subj = sum(w for lx, w in subj_w.items() if lx in subj_lex) / subj_total if subj_total else 0.0
        rel = (weights["text"] * text + weights["okpd2"] * okpd + weights["subject"] * subj) / wsum
        if best_item is None:
            best_item = max(items, key=lambda it: (okpd2_similarity(qokpd[0].okpd2, it.okpd2) if qokpd else 0, it.item_id))
        discovery = _semantic_discovery(items, ret, len(q.items))
        out.append(LotEvidence(lot_id, items[0].publish_date, rel, text, okpd, subj, best_item.name,
                               best_item.okpd2["code"] if best_item.okpd2 else None, ret.lot_customer.get(lot_id),
                               tuple(item_match), best_sem, discovery))
    out.sort(key=lambda e: (-e.relevance, -e.publish_date.toordinal(), e.lot_id))
    return out


def _semantic_discovery(items: list[HistItem], ret: Retrieval, n_query_items: int) -> dict | None:
    """Deterministic provenance of the semantic branch for one lot: highest raw cosine (ties -> smaller item_id)."""
    found = []
    for it in items:
        cos = [ret.semantic[(i, it.item_id)][0] for i in range(n_query_items) if (i, it.item_id) in ret.semantic]
        if cos:
            found.append((max(cos), it))
    if not found:
        return None
    cos, it = min(found, key=lambda x: (-x[0], x[1].item_id))
    return {"item_id": it.item_id, "product": it.name, "okpd2": it.okpd2["code"] if it.okpd2 else None, "cosine": cos,
            "semantic_only": not any(i.item_id in ret.lexical_ids for i in items)}


@dataclass
class Relation:
    lot_id: str
    supplier_id: str
    inn: str
    is_winner: bool
    platform: str
    publish_date: object


@dataclass
class Pool:
    lots: list[LotEvidence]                                    # all scored retrieved lots (sorted)
    relations: dict[str, list[Relation]] = field(default_factory=dict)  # lot_id -> relations (publish_date < as_of)
    same_customer: set = field(default_factory=set)            # supplier_ids with any earlier relation to the query customer


RELATIONS_SQL = f"""SELECT h.lot_id, h.supplier_id::text, h.supplier_inn, h.is_winner, h.platform, h.publish_date
FROM supplier_history h WHERE h.lot_id = ANY(%(lots)s) AND {visible('h')}"""
SAME_CUSTOMER_SQL = f"""SELECT DISTINCT h.supplier_id::text FROM supplier_history h JOIN procurement_lot l ON l.lot_id = h.lot_id
WHERE h.supplier_id = ANY(%(sids)s::uuid[]) AND l.customer_inn = %(cust)s AND {visible('h')}"""


def build_pool(conn, q: QueryLot, lots: list[LotEvidence], max_lots: int) -> Pool:
    """Relations for the top `max_lots` relevant lots (fetched once; any smaller historical_lot_limit is a prefix)."""
    top = [e for e in lots][:max_lots]
    pool = Pool(lots=lots)
    rels: dict[str, list[Relation]] = defaultdict(list)
    for row in conn.execute(RELATIONS_SQL, {"lots": [e.lot_id for e in top], "as_of": q.as_of}).fetchall():
        rels[row[0]].append(Relation(*row))
    pool.relations = dict(rels)
    sids = sorted({r.supplier_id for rs in rels.values() for r in rs})
    if q.customer_inn and sids:
        pool.same_customer = {r[0] for r in conn.execute(SAME_CUSTOMER_SQL, {"sids": sids, "cust": q.customer_inn,
                                                                             "as_of": q.as_of}).fetchall()}
    return pool
