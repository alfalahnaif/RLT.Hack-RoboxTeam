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
    lexical_ids: set = field(default_factory=set)                      # items found by text / technical / OKPD2 branches
    semantic: dict = field(default_factory=dict)                       # (query item index, item_id) -> (cosine, text rank)
    warnings: list = field(default_factory=list)                       # degraded branches (BR-11)


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
        if not branch.startswith("semantic"):
            ret.lexical_ids.add(item_id)
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
    if cfg.semantic_top_k > 0:
        missing = semantic_unavailable(conn)
        if missing:
            ret.warnings.append(f"SEMANTIC_UNAVAILABLE: {missing}; lexical/OKPD2 retrieval only")
        else:
            semantic_retrieve(conn, q, cfg, ret)
    lots = sorted({it.lot_id for it in ret.items.values()})
    for lot_id, lex, cust in conn.execute(
            f"SELECT l.lot_id, {LEX.format(col='l.subject')}, l.customer_inn FROM procurement_lot l "
            f"WHERE l.lot_id = ANY(%(lots)s) AND {visible('l')}", {**p, "lots": lots}).fetchall():
        ret.lot_subject_lexemes[lot_id] = frozenset(lex)
        ret.lot_customer[lot_id] = cust
    return ret


# ---------------------------------------------------------------------------- P2-001 semantic branch
SEMANTIC_SQL = f"""WITH nn AS (
  SELECT s.text_hash, s.normalized_text, s.embedding <=> %(qv)s AS dist
  FROM semantic_text s
  WHERE s.first_seen_publish_date < %(as_of)s AND s.embedding IS NOT NULL
  ORDER BY s.embedding <=> %(qv)s LIMIT %(k)s)
SELECT 1 - nn.dist, it.* FROM nn CROSS JOIN LATERAL (
  SELECT i.item_id::text, i.lot_id, i.product_name_normalized, i.okpd2_code, i.okpd2_class, i.okpd2_subclass, i.okpd2_group,
         i.okpd2_subgroup, i.okpd2_kind, {LEX.format(col='i.product_name_normalized')}, i.publish_date
  FROM procurement_item i
  WHERE md5(i.product_name_normalized) = nn.text_hash::text AND i.product_name_normalized IS NOT NULL AND {visible('i')}
    AND (i.product_name_normalized || '') = nn.normalized_text   -- collision guard (non-indexable on purpose: keeps the planner on ix_item_name_md5_date, not the trigram GIN)
  ORDER BY i.publish_date DESC, i.item_id LIMIT %(per_text)s) it
ORDER BY nn.dist, nn.text_hash, it.publish_date DESC, it.item_id"""


def semantic_unavailable(conn) -> str | None:
    """Reason the semantic branch must not run, or None. Cheap (lock file + two catalog lookups, no table scan): READY means the HNSW
    index exists, is valid, and carries the build's READY stamp for the currently pinned model revision (semantic_index.mark_ready).
    Otherwise search degrades to lexical/OKPD2 (identical to P2-003) with a warning — never a sequential vector scan."""
    from app.search import semantic, semantic_index
    if not semantic.LOCK.exists():
        return "model lock missing (backend/semantic_model.lock.json)"
    if conn.execute("SELECT to_regclass('semantic_text')").fetchone()[0] is None:
        return "semantic_text table missing (migration 0004)"
    state = semantic_index.index_state(conn)
    if state is None or state.get("state") != "READY":
        return "semantic index not READY (missing/invalid HNSW index or interrupted build; run `semantic build`)"
    pinned = semantic.lock()["revision"]
    if state.get("revision") != pinned:
        return f"semantic index built with model revision {state.get('revision')}, pinned revision is {pinned}"
    return None


def semantic_retrieve(conn, q: QueryLot, cfg: SearchConfig, ret: Retrieval) -> None:
    """Nearest distinct historical texts per query item (first_seen < as_of), mapped to their newest visible items
    (item publish_date < as_of, enforced in SQL). Results are evidence rows like every other branch."""
    from pgvector.psycopg import register_vector
    from app.search import semantic
    register_vector(conn)
    idx_texts = [(i, qi.product_name) for i, qi in enumerate(q.items) if qi.product_name]
    if not idx_texts:
        return
    t = time.perf_counter()
    vecs = semantic.encode([x for _, x in idx_texts], "query")
    ret.branch_ms["semantic_embed"] = round(ret.branch_ms.get("semantic_embed", 0.0) + (time.perf_counter() - t) * 1000, 1)
    conn.execute(f"SET LOCAL hnsw.ef_search = {int(cfg.semantic_ef_search)}")
    conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
    for (i, _text), v in zip(idx_texts, vecs):
        t = time.perf_counter()
        rows = conn.execute(SEMANTIC_SQL, {"qv": v, "as_of": q.as_of, "k": cfg.semantic_top_k,
                                           "per_text": cfg.semantic_items_per_text}).fetchall()
        ret.branch_ms["semantic"] = round(ret.branch_ms.get("semantic", 0.0) + (time.perf_counter() - t) * 1000, 1)
        rank, last = 0, None
        for row in rows:
            cos, item = float(row[0]), row[1:]
            if item[2] != last:
                rank, last = rank + 1, item[2]
            key = (i, item[0])
            if key not in ret.semantic or cos > ret.semantic[key][0]:
                ret.semantic[key] = (cos, rank)
        _add(ret, [r[1:] for r in rows], "semantic")


def restrict_semantic(ret: Retrieval, k: int) -> Retrieval:
    """View of a retrieval run at a smaller semantic cap (texts ranked <= k); k = 0 -> lexical/OKPD2 branches only."""
    sem = {key: v for key, v in ret.semantic.items() if v[1] <= k}
    keep = ret.lexical_ids | {item_id for (_i, item_id) in sem}
    items = {i: it for i, it in ret.items.items() if i in keep}
    lots = {it.lot_id for it in items.values()}
    return Retrieval(items=items, branch_hits=ret.branch_hits, branch_ms=ret.branch_ms,
                     lot_subject_lexemes={l: v for l, v in ret.lot_subject_lexemes.items() if l in lots},
                     lot_customer={l: v for l, v in ret.lot_customer.items() if l in lots},
                     lexical_ids=ret.lexical_ids, semantic=sem, warnings=ret.warnings)
