"""P1-001D — organizer CSV ingestion: raw staging + canonical tables in one transaction, idempotent.

Flow (single CSV parse per file, no three-way raw join, items streamed):
  verify files + SHA-256 pin + headers -> schema version -> delivery manifest check
  -> [one transaction] suppliers (raw COPY; group for dedup) -> notices (raw COPY, then procurement_lot)
     -> supplier (distinct INN) -> supplier_history (dedup) -> items (raw COPY, then procurement_item, streamed)
     (each file is parsed twice — raw pass + canonical pass — because one connection runs one COPY at a time)
     -> quarantine -> source_file row counts -> secondary indexes (rebuilt after a fresh load) -> delivery manifest
  -> ANALYZE -> reconciliation -> reports.
Idempotency: deterministic primary keys (UUIDv5 / (sha256,row_no)) + delivery manifest keyed by the three file hashes and
the normalization version. Same delivery again -> verify-only (no reload); --force -> re-process through
INSERT … ON CONFLICT DO NOTHING (inserts 0 rows). Normalization: only app.shared.normalize (via app.ingestion.mapping).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import resource
import sys
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from app.db.schema import ALL_SECONDARY_INDEXES, ORGANIZER_TABLES
from app.ingestion import mapping as M
from app.shared import ids
from app.shared import normalize as N
from app.shared.config import repo_root

SCHEMA_REVISION = "0003_item_publish_date"  # current head required for ingestion
DATASETS = {"notices_24_25": "Извещения_24-25.csv", "suppliers_24_25": "Поставщики_24-25.csv", "items_24_25": "ТРУ_24-25.csv"}
PROFILE_KEY = {"notices_24_25": "notices", "suppliers_24_25": "suppliers", "items_24_25": "items"}
RAW_TABLES = {"notices_24_25": "raw_notice", "suppliers_24_25": "raw_supplier_relation", "items_24_25": "raw_procurement_item"}

csv.field_size_limit(10 ** 9)


class IngestionError(RuntimeError):
    pass


class SourceDriftError(IngestionError):
    pass


def log(msg: str) -> None:
    print(f"[ingest] {msg}", file=sys.stderr, flush=True)


# ============================================================================ source files
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def pinned_sources(root: Path | None = None) -> dict:
    """Expected file names/hashes/columns from the P1-001A profile (reports/dataset_profile.json)."""
    prof = json.loads(((root or repo_root()) / "reports" / "dataset_profile.json").read_text(encoding="utf-8"))
    return {ds: {"file": prof["files"][pk]["name"], "sha256": prof["files"][pk]["sha256"],
                 "size_bytes": prof["files"][pk]["size_bytes"], "columns": prof["files"][pk]["columns"]}
            for ds, pk in PROFILE_KEY.items()}


def csv_rows(path: Path):
    """Yield (row_no, fields) — row_no is the 1-based data-row number in immutable file order (header excluded)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f, delimiter=";", quotechar='"')
        next(r)
        for row_no, row in enumerate(r, 1):
            yield row_no, row


def read_header(path: Path) -> list[str]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f, delimiter=";", quotechar='"'))


def verify_sources(raw_dir: Path, expected: dict | None, reports_dir: Path | None) -> dict:
    """Existence, SHA-256 pin, header. On drift: write source_drift_report.json and stop (never re-key silently)."""
    facts, drift = {}, {}
    for ds, name in DATASETS.items():
        p = raw_dir / name
        if not p.is_file():
            raise IngestionError(f"missing source file: {p}")
        sha = sha256_file(p)
        header = read_header(p)
        facts[ds] = {"file": name, "path": p, "sha256": sha, "size_bytes": p.stat().st_size, "header": header}
        if header != M.SOURCE_COLUMNS[ds]:
            drift[ds] = {"problem": "header mismatch", "expected": M.SOURCE_COLUMNS[ds], "actual": header}
        if expected is not None and sha != expected[ds]["sha256"]:
            drift[ds] = {"problem": "sha256 mismatch", "expected": expected[ds]["sha256"], "actual": sha,
                         "expected_size": expected[ds]["size_bytes"], "actual_size": facts[ds]["size_bytes"]}
    if drift:
        if reports_dir is not None:
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "source_drift_report.json").write_text(
                json.dumps({"drift": drift, "action": "ingestion stopped; item line_no identity is pinned to these hashes"},
                           ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        raise SourceDriftError(f"source drift detected: {sorted(drift)}")
    return facts


# ============================================================================ writers
class Writer:
    """COPY rows into `table`. direct=True: straight into the (empty) target. Otherwise into a temp table, then
    INSERT … ON CONFLICT DO NOTHING (idempotent re-processing). dry_run=True: count only."""

    def __init__(self, conn, table: str, cols: list[str], direct: bool, dry_run: bool):
        self.conn, self.table, self.cols, self.direct, self.dry_run = conn, table, cols, direct, dry_run
        self.written = 0
        self.inserted = 0
        self._copy_cm = None
        self._copy = None

    def __enter__(self):
        if not self.dry_run:
            target = self.table if self.direct else f"tmp_{self.table}"
            cur = self.conn.cursor()
            if not self.direct:
                cur.execute(f"CREATE TEMP TABLE {target} (LIKE {self.table} INCLUDING DEFAULTS) ON COMMIT DROP")
            self._copy_cm = cur.copy(f"COPY {target} ({', '.join(self.cols)}) FROM STDIN")
            self._copy = self._copy_cm.__enter__()
        return self

    def write(self, row: tuple) -> None:
        self.written += 1
        if self._copy is not None:
            self._copy.write_row(row)

    def __exit__(self, exc_type, exc, tb):
        if self._copy_cm is not None:
            self._copy_cm.__exit__(exc_type, exc, tb)
        if exc_type is None and not self.dry_run:
            if self.direct:
                self.inserted = self.written
            else:
                cols = ", ".join(self.cols)
                cur = self.conn.execute(
                    f"INSERT INTO {self.table} ({cols}) SELECT {cols} FROM tmp_{self.table} ON CONFLICT DO NOTHING")
                self.inserted = cur.rowcount
                self.conn.execute(f"DROP TABLE tmp_{self.table}")
        return False


@dataclass
class Run:
    timings: dict = field(default_factory=dict)
    written: dict = field(default_factory=dict)
    inserted: dict = field(default_factory=dict)
    quarantine: list = field(default_factory=list)
    source_rows: dict = field(default_factory=dict)

    @contextmanager
    def phase(self, name: str):
        t = time.perf_counter()
        log(f"{name} …")
        yield
        self.timings[name] = round(time.perf_counter() - t, 1)
        log(f"{name} done in {self.timings[name]}s")

    def record(self, w: Writer) -> None:
        self.written[w.table] = self.written.get(w.table, 0) + w.written
        self.inserted[w.table] = self.inserted.get(w.table, 0) + w.inserted


# ============================================================================ load
def _load(conn, facts: dict, run: Run, direct: bool, dry_run: bool) -> None:
    sha = {ds: f["sha256"] for ds, f in facts.items()}

    # ---- suppliers: raw + group for dedup (lots for has_supplier_history)
    groups: dict[tuple[str, str], list[tuple[int, str, bool]]] = defaultdict(list)
    with run.phase("suppliers_raw_and_parse"):
        s = sha["suppliers_24_25"]
        with Writer(conn, "raw_supplier_relation", ["source_sha256", "source_row_no", *M.SUPPLIER_COLUMNS], direct, dry_run) as raw:
            n = 0
            for row_no, row in csv_rows(facts["suppliers_24_25"]["path"]):
                n = row_no
                raw.write((s, row_no, *row))
                try:
                    lot_id, inn, kpp_raw, win = M.parse_supplier_row(row)
                    groups[(lot_id, inn)].append((row_no, kpp_raw, win))
                except (N.NormalizationError, ValueError) as e:
                    run.quarantine.append((s, row_no, "suppliers_24_25", str(e)))
        run.record(raw)
        run.source_rows["suppliers_24_25"] = n
    lots_with_history = {lot for lot, _ in groups}

    # ---- notices: raw (pass 1) + procurement_lot (pass 2) — one COPY at a time per connection
    lots: dict[str, tuple[str, object]] = {}
    with run.phase("notices_raw"):
        s = sha["notices_24_25"]
        with Writer(conn, "raw_notice", ["source_sha256", "source_row_no", *M.NOTICE_COLUMNS], direct, dry_run) as raw:
            n = 0
            for row_no, row in csv_rows(facts["notices_24_25"]["path"]):
                n = row_no
                raw.write((s, row_no, *row))
        run.record(raw)
        run.source_rows["notices_24_25"] = n
    with run.phase("notices_canonical"):
        with Writer(conn, "procurement_lot", M.LOT_COLS, direct, dry_run) as lw:
            for row_no, row in csv_rows(facts["notices_24_25"]["path"]):
                try:
                    t = M.map_notice(row, row_no, s, lots_with_history)
                except (N.NormalizationError, ValueError) as e:
                    run.quarantine.append((s, row_no, "notices_24_25", str(e)))
                    continue
                if t[0] in lots:
                    run.quarantine.append((s, row_no, "notices_24_25", f"duplicate lot_id {t[0]}"))
                    continue
                lots[t[0]] = (t[4], t[3])
                lw.write(t)
        run.record(lw)

    # ---- supplier + supplier_history (dedup)
    with run.phase("suppliers_and_history"):
        s = sha["suppliers_24_25"]
        first_seen: dict[str, object] = {}
        valid = []
        for (lot_id, inn), rows in groups.items():
            meta = lots.get(lot_id)
            if meta is None:
                run.quarantine.extend((s, r[0], "suppliers_24_25", f"unknown lot_id {lot_id}") for r in rows)
                continue
            valid.append((lot_id, inn, rows, meta))
            d = meta[1]
            if inn not in first_seen or d < first_seen[inn]:
                first_seen[inn] = d
        with Writer(conn, "supplier", M.SUPPLIER_COLS, direct, dry_run) as sw:
            for inn in sorted(first_seen):
                sw.write(M.supplier_row(inn, first_seen[inn]))
        run.record(sw)
        with Writer(conn, "supplier_history", M.HISTORY_COLS, direct, dry_run) as hw:
            for lot_id, inn, rows, (platform, date) in valid:
                hw.write(M.history_row(lot_id, inn, rows, platform, date, s))
        run.record(hw)
    del groups, valid

    # ---- items: raw (pass 1) + procurement_item (pass 2), streamed
    with run.phase("items_raw"):
        s = sha["items_24_25"]
        with Writer(conn, "raw_procurement_item", ["source_sha256", "source_row_no", *M.ITEM_COLUMNS], direct, dry_run) as raw:
            n = 0
            for row_no, row in csv_rows(facts["items_24_25"]["path"]):
                n = row_no
                raw.write((s, row_no, *row))
        run.record(raw)
        run.source_rows["items_24_25"] = n
    with run.phase("items_canonical"):
        line: Counter = Counter()
        with Writer(conn, "procurement_item", M.ITEM_COLS, direct, dry_run) as iw:
            for row_no, row in csv_rows(facts["items_24_25"]["path"]):
                lot_id = row[0].strip()
                if lot_id not in lots:
                    run.quarantine.append((s, row_no, "items_24_25", f"unknown lot_id {lot_id}"))
                    continue
                line[lot_id] += 1
                iw.write(M.item_row(lot_id, line[lot_id], row[1], row[2], s, row_no, lots[lot_id][1]))
        run.record(iw)

    if not dry_run:
        with run.phase("quarantine_and_manifest_rows"):
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO ingestion_quarantine VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING", run.quarantine)
                for ds, f in facts.items():
                    cur.execute("UPDATE source_file SET data_rows = %s WHERE sha256 = %s", (run.source_rows[ds], f["sha256"]))


# ============================================================================ reconciliation
FLAG_QUERY = "SELECT f, count(*) FROM {t}, unnest(data_quality_flags) f GROUP BY f"


def _scalar(conn, sql: str, *args):
    return conn.execute(sql, args).fetchone()[0]


def reconcile(conn, root: Path | None = None) -> dict:
    root = root or repo_root()
    prof = json.loads((root / "reports" / "dataset_profile.json").read_text(encoding="utf-8"))
    nv_path = root / "reports" / "normalization_verification.json"
    nv = json.loads(nv_path.read_text(encoding="utf-8")) if nv_path.exists() else None
    counts = {t: _scalar(conn, f"SELECT count(*) FROM {t}") for t in
              ["raw_notice", "raw_supplier_relation", "raw_procurement_item", "procurement_lot", "procurement_item",
               "supplier_history", "supplier", "supplier_profile", "supplier_evidence", "ingestion_quarantine", "source_file",
               "ingestion_delivery"]}
    flags = {t: dict(sorted(conn.execute(FLAG_QUERY.format(t=t)).fetchall()))
             for t in ["procurement_lot", "procurement_item", "supplier_history", "supplier"]}
    by_platform = dict(conn.execute("SELECT platform, count(*) FROM procurement_lot GROUP BY 1 ORDER BY 1").fetchall())
    history_by_platform = {f"{p}|{c}|{w}": n for p, c, w, n in conn.execute(
        "SELECT platform, coverage_semantics, is_winner, count(*) FROM supplier_history GROUP BY 1, 2, 3 ORDER BY 1, 2, 3")}
    entity = dict(conn.execute("SELECT entity_type, count(*) FROM supplier GROUP BY 1 ORDER BY 1").fetchall())
    no_history_lots = _scalar(conn, "SELECT count(*) FROM procurement_lot WHERE NOT has_supplier_history")
    dup = conn.execute("""SELECT count(*), coalesce(sum(cardinality(source_row_nos)), 0) FROM supplier_history
                          WHERE cardinality(source_row_nos) > 1""").fetchone()
    line_gaps = _scalar(conn, """SELECT count(*) FROM (SELECT lot_id, count(*) c, max(line_no) m, min(line_no) mn
                                 FROM procurement_item GROUP BY lot_id) t WHERE c <> m OR mn <> 1""")
    prov = {
        "lot_without_raw": _scalar(conn, """SELECT count(*) FROM procurement_lot l LEFT JOIN raw_notice r
            ON r.source_sha256 = l.source_sha256 AND r.source_row_no = l.source_row_no WHERE r.source_row_no IS NULL"""),
        "item_without_raw": _scalar(conn, """SELECT count(*) FROM procurement_item i LEFT JOIN raw_procurement_item r
            ON r.source_sha256 = i.source_sha256 AND r.source_row_no = i.source_row_no WHERE r.source_row_no IS NULL"""),
        "item_raw_text_mismatch": _scalar(conn, """SELECT count(*) FROM procurement_item i JOIN raw_procurement_item r
            ON r.source_sha256 = i.source_sha256 AND r.source_row_no = i.source_row_no
            WHERE r.product_name <> i.product_name_raw OR r.okpd2_code <> i.okpd2_code_raw"""),
        "history_rows_vs_raw": _scalar(conn, "SELECT coalesce(sum(cardinality(source_row_nos)), 0) FROM supplier_history"),
    }
    null_names = conn.execute("""SELECT product_name_raw, count(*) FROM procurement_item
        WHERE product_name_normalized IS NULL AND btrim(product_name_raw) <> '' GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 5""").fetchall()
    null_names_total = _scalar(conn, """SELECT count(*) FROM procurement_item
        WHERE product_name_normalized IS NULL AND btrim(product_name_raw) <> ''""")
    generic = _scalar(conn, "SELECT count(*) FROM procurement_item WHERE is_generic_type_name")

    P, S, I = prof["notices"], prof["suppliers"], prof["items"]
    expect = {
        "raw_notice = source rows": (counts["raw_notice"], P["rows"]),
        "raw_supplier_relation = source rows": (counts["raw_supplier_relation"], S["rows"]),
        "raw_procurement_item = source rows": (counts["raw_procurement_item"], I["rows"]),
        "procurement_lot = unique lots": (counts["procurement_lot"], P["unique_lots"]),
        "procurement_item = item rows": (counts["procurement_item"], I["rows"]),
        "supplier_history = rows - duplicate pairs": (counts["supplier_history"], S["rows"] - S["duplicate_lot_inn_pairs"]),
        "supplier = distinct INNs": (counts["supplier"], S["unique_inns"]),
        "quarantine": (counts["ingestion_quarantine"], 0),
        "lots by platform AIS_GZ": (by_platform.get("AIS_GZ"), P["by_platform"]["АИС ГЗ"]),
        "lots by platform EM": (by_platform.get("EM"), P["by_platform"]["ЭМ"]),
        "lots without supplier history": (no_history_lots, prof["coverage"]["by_platform"].get("АИС ГЗ|no_supplier", 0)
                                          + prof["coverage"]["by_platform"].get("ЭМ|no_supplier", 0)),
        "duplicate relations (canonical)": (dup[0], S["duplicate_lot_inn_pairs"]),
        "duplicate relations source rows": (dup[1], 2 * S["duplicate_lot_inn_pairs"]),
        "history source rows = raw rows": (prov["history_rows_vs_raw"], S["rows"]),
        "AIS_GZ non-winner relations": (sum(v for k, v in history_by_platform.items() if k.startswith("AIS_GZ") and k.endswith("False")), 0),
        "lot MISSING_INN": (flags["procurement_lot"].get("MISSING_INN", 0), 8449),
        "lot MISSING_START_PRICE": (flags["procurement_lot"].get("MISSING_START_PRICE", 0), P["start_price_empty_or_unparsable"]),
        "lot ZERO_START_PRICE": (flags["procurement_lot"].get("ZERO_START_PRICE", 0), P["start_price_zero"]),
        "lot MISSING_SUBJECT": (flags["procurement_lot"].get("MISSING_SUBJECT", 0), P["subject_empty"]),
        "item MISSING_OKPD2": (flags["procurement_item"].get("MISSING_OKPD2", 0), I["okpd2"]["empty_rows"]),
        "item INVALID_OKPD2": (flags["procurement_item"].get("INVALID_OKPD2", 0), I["okpd2"]["bad_format_rows"]),
        "item MISSING_PRODUCT_NAME": (flags["procurement_item"].get("MISSING_PRODUCT_NAME", 0), I["product_name_empty_rows"]),
        "supplier INVALID_INN_FORMAT (distinct)": (flags["supplier"].get("INVALID_INN_FORMAT", 0), S["inn_kind_unique"]["invalid"]),
        "supplier INVALID_INN_CHECKSUM (distinct)": (flags["supplier"].get("INVALID_INN_CHECKSUM", 0), S["inn_checksum_invalid_unique"]),
        "supplier legal_entity": (entity.get("legal_entity"), S["inn_kind_unique"]["legal_entity"]),
        "supplier individual_entrepreneur": (entity.get("individual_entrepreneur"), S["inn_kind_unique"]["individual_entrepreneur"]),
        "item line_no gaps": (line_gaps, 0),
        "lot without raw provenance": (prov["lot_without_raw"], 0),
        "item without raw provenance": (prov["item_without_raw"], 0),
        "item raw text differs from raw table": (prov["item_raw_text_mismatch"], 0),
        "history MISSING_KPP (DATA_MAPPING §9)": (flags["supplier_history"].get("MISSING_KPP", 0), 191359),
    }
    if nv is not None:
        expect["history INVALID_INN_CHECKSUM rows"] = (flags["supplier_history"].get("INVALID_INN_CHECKSUM", 0),
                                                       nv["suppliers"]["inn_flags_rows"].get("INVALID_INN_CHECKSUM", 0))
        expect["history INVALID_INN_FORMAT rows"] = (flags["supplier_history"].get("INVALID_INN_FORMAT", 0),
                                                     nv["suppliers"]["inn_flags_rows"].get("INVALID_INN_FORMAT", 0))
        expect["nonempty names normalized to null"] = (null_names_total, nv["items"]["nonempty_names_normalized_to_null_rows"])
        expect["generic type marker items"] = (generic, nv["items"]["generic_type_marker_rows"])
    checks = {k: {"db": a, "expected": b, "ok": a == b} for k, (a, b) in expect.items()}
    return {
        "counts": counts, "flags": flags, "lots_by_platform": by_platform, "history_by_platform_coverage_winner": history_by_platform,
        "supplier_entity_types": entity,
        "nonempty_product_name_raw_but_normalized_null": {"count": null_names_total,
                                                          "examples": [[r[0][:40], r[1]] for r in null_names]},
        "checks": checks, "reconciliation": "PASS" if all(c["ok"] for c in checks.values()) else "FAIL",
    }


def fingerprints(conn) -> dict:
    """md5 over every canonical row (ordered by PK) — proves identical content across runs."""
    q = "SELECT md5(string_agg(md5(t::text), '' ORDER BY {pk})) FROM {table} t"
    return {t: _scalar(conn, q.format(table=t, pk=pk)) for t, pk in [
        ("procurement_lot", "lot_id"), ("procurement_item", "item_id"), ("supplier_history", "id"), ("supplier", "supplier_id")]}


def db_size(conn) -> dict:
    out = {"database_bytes": _scalar(conn, "SELECT pg_database_size(current_database())")}
    for t in ["raw_notice", "raw_supplier_relation", "raw_procurement_item", "procurement_lot", "procurement_item",
              "supplier_history", "supplier"]:
        out[t] = _scalar(conn, "SELECT pg_total_relation_size(%s::regclass)", t)
    return out


# ============================================================================ orchestration
def _schema_revision(conn) -> str | None:
    try:
        return _scalar(conn, "SELECT version_num FROM alembic_version")
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return None


def reset_organizer_data(conn) -> None:
    """Delete organizer-derived data only (raw, canonical organizer rows, manifests). Enrichment rows are kept;
    suppliers referenced by enrichment are kept."""
    conn.execute(f"TRUNCATE {', '.join(ORGANIZER_TABLES)}")
    conn.execute("DELETE FROM ingestion_delivery")
    conn.execute("""DELETE FROM supplier s WHERE origin = 'ORGANIZER_DATA'
                    AND NOT EXISTS (SELECT 1 FROM supplier_profile p WHERE p.supplier_id = s.supplier_id)
                    AND NOT EXISTS (SELECT 1 FROM supplier_evidence e WHERE e.supplier_id = s.supplier_id)""")
    conn.execute("DELETE FROM source_file")


def ingest_organizer(database_url: str, raw_dir: Path, *, expected: dict | None = None, use_pinned: bool = True,
                     dry_run: bool = False, force: bool = False, reset: bool = False, reports_dir: Path | None = None,
                     root: Path | None = None) -> dict:
    root = root or repo_root()
    t0 = time.perf_counter()
    run = Run()
    if use_pinned and expected is None:
        expected = pinned_sources(root)
    with run.phase("verify_sources"):
        facts = verify_sources(raw_dir, expected, reports_dir)
    delivery = ids.delivery_uuid(facts["notices_24_25"]["sha256"], facts["suppliers_24_25"]["sha256"],
                                 facts["items_24_25"]["sha256"], N.NORMALIZATION_VERSION)
    mode = "dry-run" if dry_run else "load"

    with psycopg.connect(database_url) as conn:
        rev = _schema_revision(conn)
        if rev != SCHEMA_REVISION:
            raise IngestionError(f"database schema revision is {rev!r}, expected {SCHEMA_REVISION!r} — run `alembic upgrade head`")
        existing = conn.execute("SELECT delivery_id, normalization_version FROM ingestion_delivery").fetchall()
        if reset and not dry_run:
            log("--reset-organizer-data: deleting organizer-derived rows only")
            reset_organizer_data(conn)
            conn.commit()
            existing = []
        if existing and not dry_run:
            if [r[0] for r in existing] != [delivery]:
                raise IngestionError("a different organizer delivery (file hashes or normalization version) is already "
                                     "loaded — rerun with --reset-organizer-data to replace it")
            if not force:
                mode = "verify-existing"
        if mode in ("load", "dry-run"):
            if not dry_run:
                for ds, f in facts.items():
                    conn.execute("""INSERT INTO source_file (sha256, dataset, file_name, size_bytes, header)
                                    VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                                 (f["sha256"], ds, f["file"], f["size_bytes"], f["header"]))
            fresh = not dry_run and all(not _scalar(conn, f"SELECT EXISTS (SELECT 1 FROM {t})") for t in ORGANIZER_TABLES)
            if fresh:
                with run.phase("drop_secondary_indexes"):
                    for name, _t, _ddl in ALL_SECONDARY_INDEXES:
                        conn.execute(f"DROP INDEX IF EXISTS {name}")
            _load(conn, facts, run, direct=fresh, dry_run=dry_run)
            if not dry_run:
                if fresh:
                    with run.phase("build_secondary_indexes"):
                        for _name, _t, ddl in ALL_SECONDARY_INDEXES:
                            conn.execute(ddl)
                conn.execute("""INSERT INTO ingestion_delivery (delivery_id, notices_sha256, suppliers_sha256, items_sha256,
                                    normalization_version, status, counts)
                                VALUES (%s, %s, %s, %s, %s, 'complete', %s) ON CONFLICT (delivery_id) DO NOTHING""",
                             (delivery, facts["notices_24_25"]["sha256"], facts["suppliers_24_25"]["sha256"],
                              facts["items_24_25"]["sha256"], N.NORMALIZATION_VERSION,
                              json.dumps(run.source_rows, sort_keys=True)))
                with run.phase("commit"):
                    conn.commit()
                with run.phase("analyze"):
                    conn.autocommit = True
                    conn.execute("ANALYZE")
                    conn.autocommit = False
        if dry_run:
            report = {"mode": mode, "delivery_id": str(delivery), "written": run.written,
                      "quarantine": len(run.quarantine), "source_rows": run.source_rows}
        else:
            with run.phase("reconcile"):
                rec = reconcile(conn, root)
                fp = fingerprints(conn)
                size = db_size(conn)
            report = {
                "delivery_id": str(delivery), "normalization_version": N.NORMALIZATION_VERSION, "schema_revision": SCHEMA_REVISION,
                "sources": {ds: {"file": f["file"], "sha256": f["sha256"], "size_bytes": f["size_bytes"]} for ds, f in facts.items()},
                **rec, "fingerprints": fp,
            }
            meta = {"mode": mode, "phase_seconds": run.timings, "total_seconds": round(time.perf_counter() - t0, 1),
                    "rows_written": run.written, "rows_inserted": run.inserted, "quarantined_this_run": len(run.quarantine),
                    "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
                    "database_size": size, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            if reports_dir is not None:
                write_reports(reports_dir, report, meta)
            report = {**report, "meta": meta}
    return report


def write_reports(reports_dir: Path, report: dict, meta: dict) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "ingestion_report.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=1, sort_keys=True, default=str)
        f.write("\n")
    with open(reports_dir / "ingestion_report.meta.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, sort_keys=True, default=str)
        f.write("\n")
    (reports_dir / "ingestion_report.md").write_text(render_md(report, meta), encoding="utf-8")


def render_md(r: dict, m: dict) -> str:
    out = io.StringIO()
    w = out.write
    w("# Organizer Ingestion Report (P1-001D)\n\n")
    w(f"> Generated by `python -m app.cli ingest organizer`. Delivery `{r['delivery_id']}` · normalization "
      f"`{r['normalization_version']}` · schema `{r['schema_revision']}` · mode `{m['mode']}` · finished {m['finished_utc']}.\n")
    w("> Deterministic content: `ingestion_report.json`; volatile run data: `ingestion_report.meta.json`.\n\n")
    w(f"**Reconciliation: {r['reconciliation']}**\n\n## Sources\n| Dataset | File | SHA-256 | Bytes |\n|---|---|---|---:|\n")
    for ds, s in r["sources"].items():
        w(f"| {ds} | `{s['file']}` | `{s['sha256'][:16]}…` | {s['size_bytes']:,} |\n")
    w("\n## Table counts\n| Table | Rows |\n|---|---:|\n")
    for t, n in r["counts"].items():
        w(f"| {t} | {n:,} |\n")
    w("\n## Reconciliation checks\n| Check | DB | Expected | OK |\n|---|---:|---:|:-:|\n")
    for k, c in r["checks"].items():
        w(f"| {k} | {c['db']} | {c['expected']} | {'✅' if c['ok'] else '❌'} |\n")
    w("\n## Quality flags\n")
    for t, f in r["flags"].items():
        w(f"- **{t}**: " + (", ".join(f"`{k}` {v:,}" for k, v in f.items()) or "none") + "\n")
    w(f"\n- Supplier relations by platform | coverage | is_winner: {r['history_by_platform_coverage_winner']}\n")
    w(f"- Supplier entity types: {r['supplier_entity_types']}\n")
    nn = r["nonempty_product_name_raw_but_normalized_null"]
    w(f"- Non-empty product names that normalize to null (no flag; raw kept): {nn['count']} — examples {nn['examples']}\n")
    w("\n## Content fingerprints (md5 over all rows, ordered by PK)\n")
    for t, h in r["fingerprints"].items():
        w(f"- {t}: `{h}`\n")
    w("\n## Run (volatile)\n")
    w(f"- Phases (s): {m['phase_seconds']}\n- Total: {m['total_seconds']} s · peak RSS ≈ {m['peak_rss_mb']} MB\n")
    w(f"- Rows written: {m['rows_written']}\n- Rows inserted: {m['rows_inserted']}\n")
    sz = m["database_size"]
    w(f"- Database size: {sz['database_bytes'] / 2**30:.2f} GiB; " +
      ", ".join(f"{k} {v / 2**20:.0f} MiB" for k, v in sz.items() if k != "database_bytes") + "\n")
    return out.getvalue()
