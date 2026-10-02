"""P4-005A free-text supplier discovery: an ad-hoc query equivalent to a one-item procurement query, plus deterministic OKPD2
classification signals from historical text evidence. Ranking itself is the accepted engine (prepare_query + rank_suppliers).

OKPD2 policy (no learned classifier):
  * history status of a code = observed lots / awards before as_of, with the accepted P3 pool thresholds (>= 20 lots and >= 20
    awards -> SUFFICIENT; >= 1 lot -> SPARSE; none -> NONE);
  * suggested codes = OKPD2 of historical items found by the TEXT / TECHNICAL / SEMANTIC branches (never the OKPD2 branch, so a
    supplied code cannot suggest itself), weighted by the engine's own item similarity;
  * alignment of a supplied code with the text = closest hierarchy relation to a supported suggestion
    (same group XX.XX -> ALIGNED, same class XX only -> UNCERTAIN, none -> MISMATCH; weak text evidence -> UNCERTAIN).
The supplied code is always preserved; it is never replaced by a suggestion.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.search.candidates import semantic_norm, text_similarity
from app.search.models import QueryItem, QueryLot, SearchConfig
from app.search.retrieval import LEX, Retrieval, okpd2_dict, tech_tokens
from app.search.stats import Idf
from app.shared import normalize as N

QUERY_MIN, QUERY_MAX = 3, 1000
HISTORY_MIN_LOTS = 20          # = accepted P3 POOL_THRESHOLDS (min_lots, min_awards)
HISTORY_MIN_AWARDS = 20
SUGGEST_MIN_SIMILARITY = 0.5   # an item supports a code only when it matches the text at least this well
SUGGEST_MAX = 3
SUGGEST_MIN_SHARE = 0.15       # a suggestion counts for alignment when it holds this share of the supporting evidence
WEAK_EVIDENCE_ITEMS = 3        # fewer supporting items -> alignment cannot be judged (UNCERTAIN)


class InvalidQuery(ValueError):
    pass


@dataclass
class CodeHistory:
    okpd2: str
    lots: int
    awards: int
    status: str                # SUFFICIENT | SPARSE | NONE


@dataclass
class Suggestion:
    okpd2: str
    share: float
    supporting_items: int
    supporting_lots: int
    example_products: list[str] = field(default_factory=list)


def data_as_of(conn) -> date:
    """Free-text searches look at all history: as_of = day after the latest procurement in the dataset (deterministic)."""
    latest = conn.execute("SELECT max(publish_date) FROM procurement_lot").fetchone()[0]
    return date.fromordinal(latest.toordinal() + 1)


def normalize_code(raw: str | None) -> N.Okpd2Norm | None:
    if raw is None or not raw.strip():
        return None
    o = N.normalize_okpd2(raw.strip())
    if o.flags or o.okpd2_code is None:
        raise InvalidQuery("OKPD2 must be a valid code (e.g. 10.51.11.141)")
    return o


def code_history(conn, code: str, as_of: date) -> CodeHistory:
    lots, awards = conn.execute("""
        WITH l AS (SELECT DISTINCT lot_id FROM procurement_item WHERE okpd2_code = %(c)s AND publish_date < %(a)s)
        SELECT (SELECT count(*) FROM l),
               (SELECT count(DISTINCT (h.lot_id, h.supplier_id)) FROM supplier_history h JOIN l ON l.lot_id = h.lot_id
                 WHERE h.is_winner AND h.publish_date < %(a)s)""", {"c": code, "a": as_of}).fetchone()
    status = "NONE" if lots == 0 else "SUFFICIENT" if lots >= HISTORY_MIN_LOTS and awards >= HISTORY_MIN_AWARDS else "SPARSE"
    return CodeHistory(code, lots, awards, status)


def build_text_query(conn, text: str, okpd2: N.Okpd2Norm | None, cfg: SearchConfig, as_of: date) -> tuple[QueryLot, Idf]:
    """One query item from the user's text (same normalization, lexemes and technical tokens as procurement items)."""
    raw = (text or "").strip()
    if not QUERY_MIN <= len(raw) <= QUERY_MAX:
        raise InvalidQuery(f"query must be {QUERY_MIN}-{QUERY_MAX} characters")
    name = N.normalize_product_name(raw).normalized or raw.lower()
    lexemes = list(conn.execute(f"SELECT {LEX.format(col='%s::text')}", (name,)).fetchone()[0])
    o = okpd2_dict(okpd2.okpd2_code, okpd2.okpd2_class, okpd2.okpd2_subclass, okpd2.okpd2_group, okpd2.okpd2_subgroup,
                   okpd2.okpd2_kind) if okpd2 else None
    qi = QueryItem(name, o, lexemes, tech_tokens(name, cfg.min_tech_token_len))
    idf = Idf(conn, lexemes)
    q = QueryLot(as_of=as_of, subject=raw, items=[qi], customer_inn=None, lot_id=None, total_items=1, subject_lexemes=lexemes)
    return q, idf


def suggest_codes(q: QueryLot, ret: Retrieval, idf: Idf, cfg: SearchConfig) -> tuple[list[Suggestion], int]:
    """OKPD2 codes of historical items that match the TEXT (text/technical/semantic branches). Returns (top suggestions, support)."""
    qi = q.items[0]
    ids = set(ret.text_ids) | {item_id for (_i, item_id) in ret.semantic}
    score: dict[str, float] = defaultdict(float)
    items: dict[str, int] = defaultdict(int)
    lots: dict[str, set] = defaultdict(set)
    examples: dict[str, list] = defaultdict(list)
    for item_id in sorted(ids):
        it = ret.items.get(item_id)
        if it is None or not it.okpd2:
            continue
        sem = ret.semantic.get((0, item_id))
        sim = max(text_similarity(qi, it, idf), cfg.semantic_weight * semantic_norm(sem[0], cfg) if sem else 0.0)
        if sim < SUGGEST_MIN_SIMILARITY:
            continue
        code = it.okpd2["code"]
        score[code] += sim
        items[code] += 1
        lots[code].add(it.lot_id)
        examples[code].append((-sim, it.name or "", item_id))
    total = sum(score.values())
    ranked = sorted(score, key=lambda c: (-score[c], c))[:SUGGEST_MAX]
    out = [Suggestion(c, round(score[c] / total, 4), items[c], len(lots[c]),
                      list(dict.fromkeys(n for _s, n, _i in sorted(examples[c]) if n))[:2]) for c in ranked]
    return out, sum(items.values())


def _relation(a: str, b: str) -> int:
    """3 exact, 2 same group (XX.XX), 1 same class (XX), 0 unrelated."""
    if a == b:
        return 3
    pa, pb = a.split("."), b.split(".")
    if pa[:2] == pb[:2] and len(pa) >= 2 and len(pb) >= 2:
        return 2
    return 1 if pa[0] == pb[0] else 0


def alignment(provided: str | None, suggestions: list[Suggestion], support: int) -> str | None:
    """ALIGNED / UNCERTAIN / MISMATCH for a supplied code; None when no code was supplied."""
    if provided is None:
        return None
    if support < WEAK_EVIDENCE_ITEMS or not suggestions:
        return "UNCERTAIN"
    strong = [s for s in suggestions if s.share >= SUGGEST_MIN_SHARE] or suggestions[:1]
    best = max(_relation(provided, s.okpd2) for s in strong)
    return "ALIGNED" if best >= 2 else "UNCERTAIN" if best == 1 else "MISMATCH"
