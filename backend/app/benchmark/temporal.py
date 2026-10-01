"""P1-001E — temporal replay benchmark (generation + validation) from the ingested organizer data.

Question answered by the benchmark: "had Supplier Radar existed before lot L was published (date T), could it have surfaced
the suppliers later observed on L?"  Absolute rule: only facts with publish_date < T are visible (VISIBLE_HISTORY_SQL).

Labels (weak): 2 = observed winner on L · 1 = observed non-winning relation on L · unjudged = not observed on L
(NOT "irrelevant"). ЭМ only (both winner and non-winner rows observed; participant-list completeness not claimed — A4).
Selection never looks at difficulty; difficulty is computed afterwards for analysis only.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from psycopg.rows import dict_row

GENERATOR_VERSION = "1.0.0"
BENCHMARK_VERSION = "1.0.0"
DEFAULT_SEED = 20261001
GOLDEN_LOTS = ["5542696", "5545252", "5612123", "5659204", "5718896"]


@dataclass(frozen=True)
class Split:
    name: str
    start: date
    end: date      # inclusive
    size: int


DEFAULT_SPLITS = [
    Split("warmup", date(2024, 7, 1), date(2024, 12, 31), 50),     # debugging only (2024 ЭМ)
    Split("dev", date(2025, 1, 1), date(2025, 6, 30), 300),
    Split("holdout", date(2025, 7, 1), date(2025, 12, 31), 300),   # sealed: never tune on it
]

# Same generic-title heuristic as P1-001A (metadata only).
GENERIC_SUBJECT = re.compile(r"^(поставка|закупка|приобретение)\s+(товар|компьютерн|оргтехник|оборудован|мебел|расходн|хозяйств|канцеляр|медицинск)", re.I)

# ---------------------------------------------------------------------------- temporal visibility (single definition)
# Every historical query in the benchmark (and later P1-002) uses this predicate. Strict "<": same-day and future lots are invisible.
VISIBLE = "h.publish_date < {as_of}"


def visible(alias: str, as_of_sql: str = "%(as_of)s") -> str:
    """The one temporal predicate for any table alias carrying publish_date (supplier_history h, procurement_lot l)."""
    return f"{alias}.publish_date < {as_of_sql}"
VISIBLE_HISTORY_SQL = "SELECT h.* FROM supplier_history h WHERE " + VISIBLE.format(as_of="%(as_of)s")


def visible_history(conn, as_of: date, supplier_ids=None) -> list[dict]:
    """Supplier relations visible at as_of (publish_date < as_of), optionally for given suppliers. Filtering happens in SQL."""
    sql = VISIBLE_HISTORY_SQL + ("" if supplier_ids is None else " AND h.supplier_id = ANY(%(sids)s)")
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(sql, {"as_of": as_of, "sids": list(supplier_ids or [])}).fetchall()


ELIGIBLE_SQL = """
WITH cand AS (
    SELECT lot_id, publish_date, subject FROM procurement_lot
    WHERE platform = 'EM' AND publish_date BETWEEN %(start)s AND %(end)s AND NOT (lot_id = ANY(%(golden)s))
), rel AS (
    SELECT h.lot_id, count(*) AS n_rel, count(*) FILTER (WHERE h.is_winner) AS n_win
    FROM supplier_history h JOIN cand USING (lot_id) GROUP BY h.lot_id
), it AS (
    SELECT i.lot_id, count(*) AS n_items, count(DISTINCT i.okpd2_code) AS n_codes,
           array_agg(DISTINCT i.okpd2_section) FILTER (WHERE i.okpd2_section IS NOT NULL) AS sections
    FROM procurement_item i JOIN cand USING (lot_id) GROUP BY i.lot_id
)
SELECT c.lot_id, c.publish_date, c.subject, r.n_rel, r.n_win, it.n_items, it.n_codes, coalesce(it.sections, '{}') AS sections
FROM cand c JOIN rel r USING (lot_id) JOIN it USING (lot_id)
WHERE r.n_win >= 1 AND r.n_rel >= 2
ORDER BY c.lot_id
"""

# Difficulty metadata for selected lots; every history probe is constrained by VISIBLE in SQL (as_of = target date).
METADATA_SQL = f"""
WITH t AS (
    SELECT l.lot_id, l.publish_date AS as_of, l.customer_inn FROM procurement_lot l WHERE l.lot_id = ANY(%(lots)s)
), w AS (
    SELECT t.lot_id, t.as_of, t.customer_inn, h.supplier_id FROM t JOIN supplier_history h ON h.lot_id = t.lot_id AND h.is_winner
), tc AS (
    SELECT DISTINCT i.lot_id, i.okpd2_code, i.okpd2_group FROM procurement_item i
    WHERE i.lot_id = ANY(%(lots)s) AND i.okpd2_code IS NOT NULL
)
SELECT w.lot_id,
  bool_or(EXISTS (SELECT 1 FROM supplier_history h WHERE h.supplier_id = w.supplier_id AND {VISIBLE.format(as_of='w.as_of')})) AS seen_any,
  bool_or(EXISTS (SELECT 1 FROM supplier_history h JOIN procurement_item i ON i.lot_id = h.lot_id
                  WHERE h.supplier_id = w.supplier_id AND {VISIBLE.format(as_of='w.as_of')}
                    AND i.okpd2_code IN (SELECT tc.okpd2_code FROM tc WHERE tc.lot_id = w.lot_id))) AS seen_same_okpd2,
  bool_or(EXISTS (SELECT 1 FROM supplier_history h JOIN procurement_item i ON i.lot_id = h.lot_id
                  WHERE h.supplier_id = w.supplier_id AND {VISIBLE.format(as_of='w.as_of')}
                    AND i.okpd2_group IN (SELECT tc.okpd2_group FROM tc WHERE tc.lot_id = w.lot_id))) AS seen_same_group,
  bool_or(w.customer_inn IS NOT NULL AND EXISTS (SELECT 1 FROM supplier_history h JOIN procurement_lot pl ON pl.lot_id = h.lot_id
                  WHERE h.supplier_id = w.supplier_id AND {VISIBLE.format(as_of='w.as_of')} AND pl.customer_inn = w.customer_inn)) AS seen_same_customer
FROM w GROUP BY w.lot_id
"""

QRELS_SQL = """
SELECT h.lot_id, h.supplier_id::text, h.is_winner FROM supplier_history h WHERE h.lot_id = ANY(%(lots)s)
"""


def _rank(seed: int, lot_id: str) -> str:
    return hashlib.sha256(f"{seed}:{lot_id}".encode()).hexdigest()


def stratum(sections: list[str]) -> str:
    return sections[0] if len(sections) == 1 else ("NONE" if not sections else "MULTI")


def allocate(sizes: dict[str, int], total: int) -> dict[str, int]:
    """sqrt-proportional allocation (largest remainder), capped by stratum size; damps the dominance of big sections."""
    total = min(total, sum(sizes.values()))
    alloc = {k: 0 for k in sizes}
    remaining = total
    active = {k for k, n in sizes.items() if n > 0}
    while remaining > 0 and active:
        w = {k: math.sqrt(sizes[k]) for k in active}
        sw = sum(w.values())
        quota = {k: remaining * w[k] / sw for k in active}
        base = {k: min(int(quota[k]), sizes[k] - alloc[k]) for k in active}
        for k, v in base.items():
            alloc[k] += v
        remaining -= sum(base.values())
        rema = sorted(active, key=lambda k: (-(quota[k] - int(quota[k])), k))
        for k in rema:
            if remaining == 0:
                break
            if alloc[k] < sizes[k]:
                alloc[k] += 1
                remaining -= 1
        active = {k for k in active if alloc[k] < sizes[k]}
    return alloc


def bucket_participants(n: int) -> str:
    return "2" if n == 2 else ("3-4" if n <= 4 else ("5-9" if n <= 9 else "10+"))


def difficulty(m: dict) -> str:
    if m["winner_seen_same_okpd2"]:
        return "EASY"
    if m["winner_seen_same_okpd2_group"]:
        return "MEDIUM"
    return "HARD"


@dataclass
class Benchmark:
    queries: list = field(default_factory=list)       # dicts
    qrels: list = field(default_factory=list)
    metadata: list = field(default_factory=list)
    population: dict = field(default_factory=dict)


def build(conn, splits=DEFAULT_SPLITS, seed: int = DEFAULT_SEED, golden=GOLDEN_LOTS) -> Benchmark:
    b = Benchmark()
    selected = []
    for sp in splits:
        rows = conn.execute(ELIGIBLE_SQL, {"start": sp.start, "end": sp.end, "golden": list(golden)}).fetchall()
        by_stratum = defaultdict(list)
        for r in rows:
            by_stratum[stratum(sorted(r[7]))].append(r)
        alloc = allocate({k: len(v) for k, v in by_stratum.items()}, sp.size)
        pick = []
        for k in sorted(by_stratum):
            pick += sorted(by_stratum[k], key=lambda r: _rank(seed, r[0]))[:alloc[k]]
        b.population[sp.name] = {
            "eligible": len(rows),
            "strata": {k: len(v) for k, v in sorted(by_stratum.items())},
            "allocation": {k: v for k, v in sorted(alloc.items()) if v},
            "participants": dict(sorted(Counter(bucket_participants(r[3]) for r in rows).items())),
            "multi_item_pct": round(100 * sum(r[5] > 1 for r in rows) / max(1, len(rows)), 1),
            "multi_okpd2_pct": round(100 * sum(r[6] > 1 for r in rows) / max(1, len(rows)), 1),
        }
        weight = {k: round(len(by_stratum[k]) / alloc[k], 4) for k in alloc if alloc[k]}
        selected += [(sp.name, r, weight[stratum(sorted(r[7]))]) for r in pick]
    lots = [r[0] for _, r, _w in selected]
    meta = {r[0]: r[1:] for r in conn.execute(METADATA_SQL, {"lots": lots}).fetchall()}
    rels = defaultdict(list)
    for lot_id, sid, win in conn.execute(QRELS_SQL, {"lots": lots}).fetchall():
        rels[lot_id].append((sid, win))
    order = {s.name: i for i, s in enumerate(splits)}
    selected.sort(key=lambda x: (order[x[0]], x[1][1], x[1][0]))
    for split, (lot_id, pdate, subject, n_rel, n_win, n_items, n_codes, sections), weight in selected:
        qid = f"rpl-{lot_id}"
        b.queries.append({"query_id": qid, "lot_id": lot_id, "publish_date": pdate.isoformat(), "split": split, "platform": "EM"})
        any_, same_code, same_group, same_cust = meta[lot_id]
        m = {"query_id": qid, "stratum": stratum(sorted(sections)), "stratum_weight": weight, "okpd2_sections": "|".join(sorted(sections)),
             "n_items": n_items, "n_okpd2_codes": n_codes, "n_relations": n_rel, "n_winners": n_win,
             "generic_title": bool(subject and GENERIC_SUBJECT.search(subject)),
             "winner_seen_before_anywhere": bool(any_), "winner_seen_same_okpd2": bool(same_code),
             "winner_seen_same_okpd2_group": bool(same_group), "winner_seen_same_customer": bool(same_cust)}
        m["difficulty"] = difficulty(m)
        b.metadata.append(m)
        for sid, win in sorted(rels[lot_id], key=lambda x: (not x[1], x[0])):
            b.qrels.append({"query_id": qid, "supplier_id": sid, "relevance_grade": 2 if win else 1, "is_winner": win})
    return b


# ---------------------------------------------------------------------------- files
QUERY_FIELDS = ["query_id", "lot_id", "publish_date", "split", "platform"]
QREL_FIELDS = ["query_id", "supplier_id", "relevance_grade", "is_winner"]
META_FIELDS = ["query_id", "stratum", "stratum_weight", "okpd2_sections", "n_items", "n_okpd2_codes", "n_relations", "n_winners", "generic_title",
               "winner_seen_before_anywhere", "winner_seen_same_okpd2", "winner_seen_same_okpd2_group",
               "winner_seen_same_customer", "difficulty"]


def _csv_bytes(fields, rows) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: (str(v).lower() if isinstance(v, bool) else v) for k, v in r.items()})
    return buf.getvalue().encode("utf-8")


def render_files(b: Benchmark, conn, seed: int, splits, golden) -> dict[str, bytes]:
    files = {"queries.csv": _csv_bytes(QUERY_FIELDS, b.queries), "qrels.csv": _csv_bytes(QREL_FIELDS, b.qrels),
             "query_metadata.csv": _csv_bytes(META_FIELDS, b.metadata)}
    delivery = conn.execute("SELECT delivery_id::text, normalization_version FROM ingestion_delivery").fetchall()
    sources = {ds: {"file": f, "sha256": s} for ds, f, s in
               conn.execute("SELECT dataset, file_name, sha256 FROM source_file ORDER BY dataset").fetchall()}
    rev = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    split_counts = Counter(q["split"] for q in b.queries)
    qsplit = {q["query_id"]: q["split"] for q in b.queries}
    grade_counts = Counter(f"{qsplit[r['query_id']]}|grade_{r['relevance_grade']}" for r in b.qrels)
    manifest = {
        "benchmark_name": "supplier-radar-temporal-replay", "benchmark_version": BENCHMARK_VERSION,
        "generator": "backend/app/benchmark/temporal.py", "generator_version": GENERATOR_VERSION,
        "created_from_ingestion_delivery": [{"delivery_id": d, "normalization_version": v} for d, v in delivery],
        "source_files": sources, "schema_revision": rev, "sampling_seed": seed,
        "eligibility": {"platform": "EM", "has_items": True, "min_winner_relations": 1, "min_observed_relations": 2,
                        "publish_date": "valid DATE (all are)", "golden_lots_excluded": sorted(golden)},
        "temporal_rule": "For a query lot with publish_date T only supplier_history / lots / items with publish_date < T (strict) are "
                         "visible; same-day and later facts are invisible (VISIBLE_HISTORY_SQL).",
        "splits": [{"name": s.name, "from": s.start.isoformat(), "to": s.end.isoformat(), "target_size": s.size,
                    "role": {"warmup": "debugging only", "dev": "development + tuning", "holdout": "SEALED final evaluation — never tune"}[s.name]}
                   for s in splits],
        "sampling": "per split: strata = OKPD2 section of the lot's items (single section letter, MULTI, NONE); allocation "
                    "proportional to sqrt(stratum size) (largest remainder, capped); within a stratum lots ordered by "
                    "sha256(f'{seed}:{lot_id}') and the first k taken. Difficulty is NOT used for selection. query_metadata.stratum_weight = eligible/selected in the stratum (inverse inclusion probability) — report population-weighted metrics alongside unweighted ones.",
        "query_counts": dict(sorted(split_counts.items())), "qrel_counts": dict(sorted(grade_counts.items())),
        "label_semantics": {"2": "observed winner relation on the target lot", "1": "observed non-winning relation on the target lot",
                            "unjudged": "supplier not observed on the target lot — NOT evidence of irrelevance; it did not appear "
                                        "in the delivered ЭМ rows (it may not have bid, or may be relevant but absent)"},
        "difficulty": {"EASY": "a winner had a relation (any role) before T on a lot with the same full OKPD2 code",
                       "MEDIUM": "otherwise, a winner had a relation before T in the same OKPD2 group (XX.XX)",
                       "HARD": "otherwise (seen only in other categories, or never)",
                       "note": "metadata for analysis only; computed after selection; text similarity not used"},
        "known_limitations": [
            "Weak labels: unjudged suppliers are not proven irrelevant; precision-style metrics underestimate quality.",
            "ЭМ participant-list completeness is not officially confirmed (coverage MIXED_WINNER_NONWINNER_ROWS_OBSERVED).",
            "АИС ГЗ is excluded from the primary benchmark (only winner rows observed; OQ-33).",
            "History window starts 2024-01-08: early-2024 targets have little history (warm-up split only).",
            "Lot-level labels: a supplier is relevant to the lot, not to a specific item of a multi-item lot.",
            "~40% of eligible ЭМ lots have exactly 2 observed relations; small label sets make per-query metrics noisy.",
        ],
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n").encode("utf-8")
    return files


def write_files(files: dict[str, bytes], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out_dir / name).write_bytes(data)


def generate(conn, out_dir: Path, seed: int = DEFAULT_SEED, splits=DEFAULT_SPLITS, golden=GOLDEN_LOTS) -> tuple[Benchmark, dict]:
    b = build(conn, splits, seed, golden)
    files = render_files(b, conn, seed, splits, golden)
    write_files(files, out_dir)
    return b, files


# ---------------------------------------------------------------------------- validation
def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def validate(conn, out_dir: Path, *, splits=DEFAULT_SPLITS, golden=GOLDEN_LOTS, regenerate: bool = True) -> dict:
    queries = _read_csv(out_dir / "queries.csv")
    qrels = _read_csv(out_dir / "qrels.csv")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    lots = [q["lot_id"] for q in queries]
    db = {r[0]: r[1:] for r in conn.execute(
        """SELECT l.lot_id, l.platform, l.publish_date,
                  (SELECT count(*) FROM supplier_history h WHERE h.lot_id = l.lot_id),
                  (SELECT count(*) FROM supplier_history h WHERE h.lot_id = l.lot_id AND h.is_winner),
                  (SELECT count(*) FROM procurement_item i WHERE i.lot_id = l.lot_id)
           FROM procurement_lot l WHERE l.lot_id = ANY(%s)""", (lots,)).fetchall()}
    truth = defaultdict(set)
    for lot_id, sid, win in conn.execute(QRELS_SQL, {"lots": lots}).fetchall():
        truth[lot_id].add((sid, 2 if win else 1, win))
    split_by = {s.name: s for s in splits}
    qlot = {q["query_id"]: q["lot_id"] for q in queries}
    got = defaultdict(set)
    for r in qrels:
        got[qlot.get(r["query_id"])].add((r["supplier_id"], int(r["relevance_grade"]), r["is_winner"] == "true"))
    checks = {}
    checks["01 every query lot exists"] = all(l in db for l in lots)
    checks["02 every query is EM"] = all(db[l][0] == "EM" for l in lots if l in db)
    checks["03 every query has >= 2 observed relations"] = all(db[l][2] >= 2 for l in lots if l in db)
    checks["04 every query has >= 1 winner"] = all(db[l][3] >= 1 for l in lots if l in db)
    checks["04b every query has items"] = all(db[l][4] >= 1 for l in lots if l in db)
    checks["05 qrels = exactly the target lot's relations"] = all(got[l] == truth[l] for l in lots) and \
        all(r["query_id"] in qlot for r in qrels)
    checks["06 winners graded 2"] = all(int(r["relevance_grade"]) == 2 for r in qrels if r["is_winner"] == "true")
    checks["07 non-winners graded 1"] = all(int(r["relevance_grade"]) == 1 for r in qrels if r["is_winner"] == "false")
    checks["08 no golden lot"] = not (set(lots) & set(golden))
    checks["09 split dates obey the split"] = all(
        split_by[q["split"]].start <= date.fromisoformat(q["publish_date"]) <= split_by[q["split"]].end
        and db[q["lot_id"]][1].isoformat() == q["publish_date"] for q in queries)
    checks["10 query ids unique"] = len({q["query_id"] for q in queries}) == len(queries)
    checks["10b no duplicate qrels"] = len({(r["query_id"], r["supplier_id"]) for r in qrels}) == len(qrels)
    checks["10c file checksums match manifest"] = all(
        hashlib.sha256((out_dir / n).read_bytes()).hexdigest() == h for n, h in manifest["files"].items())
    if regenerate:
        b = build(conn, splits, manifest["sampling_seed"], golden)
        fresh = render_files(b, conn, manifest["sampling_seed"], splits, golden)
        checks["11 regeneration byte-identical"] = all(fresh[n] == (out_dir / n).read_bytes() for n in fresh)
    leak = leakage_probe(conn, lots)
    checks["12 temporal rule: no visible fact with publish_date >= T"] = leak["violations"] == 0
    return {"checks": checks, "passed": all(checks.values()), "leakage_probe": leak}


def leakage_probe(conn, lots: list[str]) -> dict:
    """For every query: run the visibility predicate for the target's own suppliers at as_of = T and assert that nothing
    dated >= T comes back, while counting how many same-day / future relations exist for those suppliers (proof that the
    rule is exercised, not vacuous)."""
    row = conn.execute(f"""
        WITH t AS (SELECT lot_id, publish_date AS as_of FROM procurement_lot WHERE lot_id = ANY(%(lots)s)),
        s AS (SELECT DISTINCT t.lot_id, t.as_of, h.supplier_id FROM t JOIN supplier_history h ON h.lot_id = t.lot_id),
        vis AS (SELECT s.lot_id, s.as_of, h.publish_date FROM s JOIN supplier_history h
                ON h.supplier_id = s.supplier_id AND {VISIBLE.format(as_of='s.as_of')})
        SELECT (SELECT count(*) FROM vis WHERE publish_date >= as_of),
               (SELECT count(*) FROM vis),
               (SELECT count(*) FROM s JOIN supplier_history h ON h.supplier_id = s.supplier_id AND h.publish_date = s.as_of),
               (SELECT count(*) FROM s JOIN supplier_history h ON h.supplier_id = s.supplier_id AND h.publish_date > s.as_of)
    """, {"lots": lots}).fetchone()
    return {"violations": row[0], "visible_relations_checked": row[1], "same_day_relations_excluded": row[2],
            "future_relations_excluded": row[3]}


# ---------------------------------------------------------------------------- statistics
def statistics(b: Benchmark) -> dict:
    out = {"population": b.population, "splits": {}}
    qsplit = {q["query_id"]: q["split"] for q in b.queries}
    nq = Counter(qsplit[r["query_id"]] for r in b.qrels)
    for sp in sorted(set(qsplit.values())):
        ms = [m for m in b.metadata if qsplit[m["query_id"]] == sp]
        n = len(ms)
        pct = lambda f: round(100 * sum(1 for m in ms if f(m)) / max(1, n), 1)  # noqa: E731
        out["splits"][sp] = {
            "queries": n, "qrels": nq[sp], "qrels_per_query": round(nq[sp] / max(1, n), 2),
            "grade_2": sum(1 for r in b.qrels if qsplit[r["query_id"]] == sp and r["relevance_grade"] == 2),
            "grade_1": sum(1 for r in b.qrels if qsplit[r["query_id"]] == sp and r["relevance_grade"] == 1),
            "participants": dict(sorted(Counter(bucket_participants(m["n_relations"]) for m in ms).items())),
            "multi_winner_queries": sum(1 for m in ms if m["n_winners"] > 1),
            "difficulty": dict(sorted(Counter(m["difficulty"] for m in ms).items())),
            "winner_seen_before_anywhere_pct": pct(lambda m: m["winner_seen_before_anywhere"]),
            "winner_seen_same_okpd2_pct": pct(lambda m: m["winner_seen_same_okpd2"]),
            "winner_seen_same_okpd2_group_pct": pct(lambda m: m["winner_seen_same_okpd2_group"]),
            "winner_seen_same_customer_pct": pct(lambda m: m["winner_seen_same_customer"]),
            "okpd2_strata": dict(sorted(Counter(m["stratum"] for m in ms).items())),
            "multi_item_pct": pct(lambda m: m["n_items"] > 1),
            "multi_okpd2_pct": pct(lambda m: m["n_okpd2_codes"] > 1),
            "generic_title_pct": pct(lambda m: m["generic_title"]),
        }
    return out
