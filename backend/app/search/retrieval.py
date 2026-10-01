"""Query construction and historical item retrieval (P1-002). Every SQL statement enforces publish_date < as_of in PostgreSQL
through app.benchmark.temporal.visible(); nothing dated on/after as_of is ever fetched.

Branches (per query item, each capped):
  T  text      — russian-config FTS (GIN ix_item_name_fts_russian) on an OR of the item's rarest lexemes (df ≤ max_df_ratio);
                 if all lexemes are frequent: AND of all lexemes. Ranked by ts_rank_cd.
  X  technical — exact substring of letter+digit tokens (a515-57-50r7, 4103dw, cf280x) via the pg_trgm GIN index.
  O  OKPD2     — lots with the exact code, and lots sharing the query's most specific indexed level (kind > group > class),
                 newest first, one representative item per lot.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date

from app.benchmark.temporal import visible
from app.search.models import QueryItem, QueryLot, SearchConfig
from app.search.stats import Idf

LEX = "tsvector_to_array(to_tsvector('russian'::regconfig, coalesce({col}, '')))"
ITEM_SELECT = f"""SELECT i.item_id::text, i.lot_id, i.product_name_normalized, i.okpd2_code, i.okpd2_class, i.okpd2_subclass,
       i.okpd2_group, i.okpd2_subgroup, i.okpd2_kind, {LEX.format(col='i.product_name_normalized')}, l.publish_date
FROM procurement_item i JOIN procurement_lot l ON l.lot_id = i.lot_id"""
FTS_DOC = "to_tsvector('russian'::regconfig, coalesce(i.product_name_normalized, ''))"

TEXT_SQL = f"""{ITEM_SELECT}
WHERE {FTS_DOC} @@ %(tq)s::tsquery AND {visible('l')}
ORDER BY ts_rank_cd({FTS_DOC}, %(tq)s::tsquery) DESC, i.item_id LIMIT %(lim)s"""
TECH_SQL = f"""{ITEM_SELECT}
WHERE i.product_name_normalized LIKE %(pat)s AND {visible('l')}
ORDER BY l.publish_date DESC, i.item_id LIMIT %(lim)s"""
OKPD_SQL = """WITH top AS (
  SELECT DISTINCT ON (i.publish_date, i.lot_id) i.item_id, i.lot_id, i.publish_date
  FROM procurement_item i
  WHERE {cond} AND {vis}
  ORDER BY i.publish_date DESC, i.lot_id, i.line_no
  LIMIT %(lim)s)
SELECT i.item_id::text, i.lot_id, i.product_name_normalized, i.okpd2_code, i.okpd2_class, i.okpd2_subclass, i.okpd2_group,
       i.okpd2_subgroup, i.okpd2_kind, {lex}, i.publish_date
FROM top JOIN procurement_item i ON i.item_id = top.item_id
ORDER BY top.publish_date DESC, top.lot_id"""

_TECH = re.compile(r"(?=.*[^\W\d_])(?=.*\d)")


@dataclass(frozen=True)
class HistItem:
    item_id: str
    lot_id: str
    name: str | None
    okpd2: dict | None
    lexemes: frozenset
    publish_date: date


@dataclass
class Retrieval:
    items: dict[str, HistItem] = field(default_factory=dict)          # item_id -> item
    branch_hits: dict[str, int] = field(default_factory=dict)          # branch -> rows fetched
    branch_ms: dict[str, float] = field(default_factory=dict)          # branch -> SQL time
    lot_subject_lexemes: dict[str, frozenset] = field(default_factory=dict)
    lot_customer: dict[str, str | None] = field(default_factory=dict)


def okpd2_dict(code, cls, subclass, group, subgroup, kind) -> dict | None:
    if code is None:
        return None
    return {"code": code, "class": cls, "subclass": subclass, "group": group, "subgroup": subgroup, "kind": kind}


def tech_tokens(name: str | None, min_len: int) -> list[str]:
    if not name:
        return []
    out = []
    for tok in name.split(" "):
        tok = tok.strip('"%')
        if len(tok) >= min_len and _TECH.match(tok) and tok not in out:
            out.append(tok)
    return out


def build_query(conn, lot_id: str, cfg: SearchConfig, as_of: date | None = None) -> tuple[QueryLot, Idf]:
    """Query from the target lot's own procurement-time information only (subject, items, OKPD2, customer). Never its suppliers."""
    row = conn.execute("SELECT publish_date, subject, customer_inn FROM procurement_lot WHERE lot_id = %s", (lot_id,)).fetchone()
    if row is None:
        raise ValueError(f"lot {lot_id} not found")
    rows = conn.execute(f"""SELECT product_name_normalized, okpd2_code, okpd2_class, okpd2_subclass, okpd2_group, okpd2_subgroup,
                                   okpd2_kind, {LEX.format(col='product_name_normalized')}, line_no
                            FROM procurement_item WHERE lot_id = %s ORDER BY line_no""", (lot_id,)).fetchall()
    subj_lex = conn.execute(f"SELECT {LEX.format(col='%s::text')}", (row[1],)).fetchone()[0]
    distinct, seen = [], set()
    for name, code, cls, sc, grp, sg, kind, lex, line in rows:
        key = (name, code)
        if key in seen or (name is None and code is None):
            continue
        seen.add(key)
        distinct.append((QueryItem(name or "", okpd2_dict(code, cls, sc, grp, sg, kind), list(lex),
                                   tech_tokens(name, cfg.min_tech_token_len)), line))
    idf = Idf(conn, [lx for qi, _ in distinct for lx in qi.lexemes] + list(subj_lex))

    def info(qi: QueryItem) -> float:
        return sum(idf.weight(lx) for lx in set(qi.lexemes)) + idf.max_weight * len(qi.tech_tokens) + (1.0 if qi.okpd2 else 0.0)

    keep = sorted(distinct, key=lambda x: (-info(x[0]), x[1]))[:cfg.max_query_items]
    keep.sort(key=lambda x: x[1])
    q = QueryLot(as_of=as_of or row[0], subject=row[1], items=[qi for qi, _ in keep], customer_inn=row[2], lot_id=lot_id,
                 total_items=len(rows), subject_lexemes=list(subj_lex))
    return q, idf


def _tsquery(lexemes: list[str], op: str) -> str:
    return f" {op} ".join("'" + lx.replace("\\", "\\\\").replace("'", "''") + "'" for lx in lexemes)


def _like(token: str) -> str:
    return "%" + token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _run(conn, ret: Retrieval, branch: str, sql: str, params: dict) -> None:
    t = time.perf_counter()
    rows = conn.execute(sql, params).fetchall()
    ret.branch_ms[branch] = round(ret.branch_ms.get(branch, 0.0) + (time.perf_counter() - t) * 1000, 1)
    _add(ret, rows, branch)


def _add(ret: Retrieval, rows, branch: str) -> None:
    ret.branch_hits[branch] = ret.branch_hits.get(branch, 0) + len(rows)
    for item_id, lot_id, name, code, cls, sc, grp, sg, kind, lex, pdate in rows:
        if item_id not in ret.items:
            ret.items[item_id] = HistItem(item_id, lot_id, name, okpd2_dict(code, cls, sc, grp, sg, kind), frozenset(lex), pdate)


def retrieve(conn, q: QueryLot, cfg: SearchConfig, idf: Idf) -> Retrieval:
    ret = Retrieval()
    p = {"as_of": q.as_of}
    done_codes: set[str] = set()
    for qi in q.items:
        lexes = sorted(set(qi.lexemes), key=lambda lx: (-idf.weight(lx), lx))
        rare = [lx for lx in lexes if not idf.frequent(lx, cfg.max_df_ratio)][:cfg.max_or_lexemes]
        if rare:
            _run(conn, ret, "text", TEXT_SQL, {**p, "tq": _tsquery(rare, "|"), "lim": cfg.text_items_limit})
        elif len(lexes) >= 1:
            _run(conn, ret, "text_and", TEXT_SQL, {**p, "tq": _tsquery(lexes, "&"), "lim": cfg.text_items_limit})
        for tok in qi.tech_tokens:
            _run(conn, ret, "technical", TECH_SQL, {**p, "pat": _like(tok), "lim": cfg.tech_items_limit})
        if qi.okpd2 and qi.okpd2["code"] not in done_codes:   # identical OKPD2 queries run once per distinct code
            done_codes.add(qi.okpd2["code"])
            o = qi.okpd2
            sql = OKPD_SQL.format(lex=LEX.format(col="i.product_name_normalized"), cond="i.okpd2_code = %(v)s", vis=visible("i"))
            _run(conn, ret, "okpd2_exact", sql, {**p, "v": o["code"], "lim": cfg.okpd2_exact_lots_limit})
            level = "kind" if o["kind"] else ("group" if o["group"] else "class")
            sql = OKPD_SQL.format(lex=LEX.format(col="i.product_name_normalized"),
                                  cond=f"i.okpd2_{level} = %(v)s AND i.okpd2_code <> %(code)s", vis=visible("i"))
            _run(conn, ret, f"okpd2_{level}", sql, {**p, "v": o[level], "code": o["code"], "lim": cfg.okpd2_broad_lots_limit})
    lots = sorted({it.lot_id for it in ret.items.values()})
    for lot_id, lex, cust in conn.execute(
            f"SELECT l.lot_id, {LEX.format(col='l.subject')}, l.customer_inn FROM procurement_lot l "
            f"WHERE l.lot_id = ANY(%(lots)s) AND {visible('l')}", {**p, "lots": lots}).fetchall():
        ret.lot_subject_lexemes[lot_id] = frozenset(lex)
        ret.lot_customer[lot_id] = cust
    return ret
