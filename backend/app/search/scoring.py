"""Supplier scoring and deterministic explanations (P1-002 baseline).

Per candidate supplier, over its relevant historical lots R (top `historical_lot_limit` lots with relevance >= min_lot_relevance),
each lot weighted by its relevance r in [0, 1]:
  product_text          = max text similarity of its lots                     (query/product relevance)
  okpd2                 = max OKPD2 similarity of its lots
  historical_relevance  = 1 - exp(-sum(r) / evidence_saturation)              (bounded volume of relevant evidence)
  relevant_awards       = 1 - exp(-sum(r over won lots) / awards_saturation)  (is_winner evidence, both platforms)
  em_participation      = 1 - exp(-sum(r over EM relations) / participation_saturation)   (EM only: observed participation)
  recency               = 0.5 ** (days since latest relevant relation / recency_half_life_days)
  same_customer         = 1 if any earlier relation with the query customer (applicable only when the customer is known)
score = sum(w_i * f_i) / sum(w_i over applicable components); contributions are reported per component.
There is no win-rate anywhere (АИС ГЗ has no observed non-winner rows — HD-05).
Tie-break: score desc, weighted awards desc, supplier_id asc (deterministic).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from app.search.candidates import Pool
from app.search.models import QueryLot, SearchConfig
from app.shared.normalize import comparison_key


def text_redundancy(q: QueryLot, threshold: float) -> float:
    """Share of query items whose product text adds (almost) nothing beyond the lot subject (comparison-key token Jaccard)."""
    subj = set(comparison_key(q.subject).split())
    if not q.items or not subj:
        return 0.0
    red = 0
    for qi in q.items:
        toks = set(comparison_key(qi.product_name).split())
        if toks and len(toks & subj) / len(toks | subj) >= threshold:
            red += 1
    return red / len(q.items)

COMPONENTS = ["product_text", "okpd2", "historical_relevance", "relevant_awards", "em_participation", "recency", "same_customer",
              "evidence_quality", "item_coverage"]


@dataclass
class Recommendation:
    rank: int
    supplier_id: str
    supplier_inn: str
    score: float
    components: dict
    contributions: dict
    relevant_lots: int
    relevant_awards: int
    relevant_em_participations: int
    relevant_ais_awards: int
    best_products: list
    best_okpd2: str | None
    most_recent_relevant: str
    same_customer_history: bool
    evidence_lot_ids: list
    reasons: list = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)   # raw evidence shape (not scored unless a weight uses it)
    semantic_evidence: list = field(default_factory=list)  # P2-001: lots whose best text evidence is a semantic match


def _sat(x: float, s: float) -> float:
    return 1.0 - math.exp(-x / s) if s > 0 else 0.0


def rank_suppliers(q: QueryLot, pool: Pool, cfg: SearchConfig) -> tuple[list[Recommendation], list[str]]:
    """Returns (ranked recommendations [all candidates], candidate supplier_ids)."""
    top = [e for e in pool.lots[:cfg.historical_lot_limit] if e.relevance >= cfg.min_lot_relevance]
    lot_by_id = {e.lot_id: e for e in top}
    per: dict[str, list] = defaultdict(list)
    for e in top:
        for r in pool.relations.get(e.lot_id, []):
            per[r.supplier_id].append((e, r))
    redundant = text_redundancy(q, cfg.redundancy_jaccard) >= 1.0
    weights = {"product_text": cfg.w_product_text * (cfg.redundant_text_factor if redundant else 1.0),
               "okpd2": cfg.w_okpd2 if any(qi.okpd2 for qi in q.items) else 0.0,
               "historical_relevance": cfg.w_historical_relevance, "relevant_awards": cfg.w_relevant_awards,
               "em_participation": cfg.w_em_participation, "recency": cfg.w_recency,
               "same_customer": cfg.w_same_customer if q.customer_inn else 0.0,
               "evidence_quality": cfg.w_evidence_quality,
               "item_coverage": cfg.w_item_coverage if len(q.items) >= 2 else 0.0}
    wsum = sum(weights.values()) or 1.0
    recs = []
    for sid, rows in per.items():
        lots = {e.lot_id: e for e, _ in rows}
        won = {r.lot_id for _, r in rows if r.is_winner}
        em = {r.lot_id for _, r in rows if r.platform == "EM"}
        ais_won = {r.lot_id for _, r in rows if r.is_winner and r.platform == "AIS_GZ"}
        latest = max(e.publish_date for e in lots.values())
        f = {
            "product_text": max(e.text for e in lots.values()),
            "okpd2": max(e.okpd2 for e in lots.values()),
            "historical_relevance": _sat(sum(e.relevance for e in lots.values()), cfg.evidence_saturation),
            "relevant_awards": _sat(sum(lot_by_id[l].relevance for l in won), cfg.awards_saturation),
            "em_participation": _sat(sum(lot_by_id[l].relevance for l in em), cfg.participation_saturation),
            "recency": 0.5 ** ((q.as_of - latest).days / cfg.recency_half_life_days),
            "same_customer": 1.0 if sid in pool.same_customer else 0.0,
        }
        rels = sorted((e.relevance for e in lots.values()), reverse=True)
        f["evidence_quality"] = sum(rels[:cfg.quality_top_k]) / cfg.quality_top_k
        n_items = len(q.items)
        f["item_coverage"] = (sum(max((e.item_match[i] for e in lots.values() if len(e.item_match) > i), default=0.0)
                                  for i in range(n_items)) / n_items) if n_items else 0.0
        diag = {"relevance_sum": round(sum(rels), 4), "top_lot_share": round(rels[0] / sum(rels), 4) if sum(rels) else 0.0,
                "distinct_products": len({e.best_item_name for e in lots.values() if e.best_item_name}),
                "days_since_latest": (q.as_of - latest).days, "query_text_redundant": redundant, "query_items": n_items}
        contrib = {k: weights[k] * f[k] / wsum for k in COMPONENTS}
        ordered = sorted(lots.values(), key=lambda e: (-e.relevance, -e.publish_date.toordinal(), e.lot_id))
        best = ordered[0]
        recs.append(Recommendation(
            rank=0, supplier_id=sid, supplier_inn=rows[0][1].inn, score=round(sum(contrib.values()), 6),
            components={k: round(v, 4) for k, v in f.items()},
            contributions={k: round(v, 4) for k, v in contrib.items() if weights[k] > 0},
            relevant_lots=len(lots), relevant_awards=len(won), relevant_em_participations=len(em), relevant_ais_awards=len(ais_won),
            best_products=[n for n in dict.fromkeys(e.best_item_name for e in ordered[:5]) if n][:3],
            best_okpd2=best.best_item_okpd2, most_recent_relevant=latest.isoformat(),
            same_customer_history=sid in pool.same_customer, evidence_lot_ids=[e.lot_id for e in ordered[:5]], diagnostics=diag,
            semantic_evidence=[{"lot_id": e.lot_id, "publish_date": e.publish_date.isoformat(), "product": e.best_item_name,
                                "okpd2": e.best_item_okpd2, "cosine": round(e.semantic_cosine, 4)}
                               for e in ordered if e.semantic_cosine is not None][:2]))
    recs.sort(key=lambda r: (-r.score, -r.components["relevant_awards"], r.supplier_id))
    for i, r in enumerate(recs, 1):
        r.rank = i
        r.reasons = explain(r)
    return recs, [r.supplier_id for r in recs]


def explain(r: Recommendation) -> list[str]:
    """Template facts generated from the evidence only (no LLM, no invented attributes)."""
    out = [f"matched {r.relevant_lots} historically similar procurement(s) published before the target date"]
    if r.components["okpd2"] >= 1.0:
        out.append(f"exact OKPD2 match ({r.best_okpd2})")
    elif r.components["okpd2"] > 0:
        out.append(f"related OKPD2 match ({r.best_okpd2}, similarity {r.components['okpd2']:.2f})")
    if r.best_products:
        out.append(f"strongest matched product: «{r.best_products[0][:120]}» (text similarity {r.components['product_text']:.2f})")
    out.append(f"{r.relevant_awards} relevant historical award(s)" + (f", {r.relevant_ais_awards} on АИС ГЗ" if r.relevant_ais_awards else ""))
    if r.relevant_em_participations:
        out.append(f"{r.relevant_em_participations} relevant observed ЭМ participation(s) (winner or not)")
    out.append(f"most recent relevant activity: {r.most_recent_relevant}")
    if r.same_customer_history:
        out.append("has earlier procurement history with the same customer")
    for ev in r.semantic_evidence:
        out.append(f"semantically similar historical product: «{(ev['product'] or '')[:120]}» (cosine {ev['cosine']:.2f}, lot {ev['lot_id']}, "
                   f"{ev['publish_date']}" + (f", OKPD2 {ev['okpd2']})" if ev["okpd2"] else ")"))
    return out
