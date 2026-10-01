#!/usr/bin/env python3
"""P3-002A: reconcile manually supplied INNs with canonical procurement history.

This script reads canonical PostgreSQL tables only. Company names are supplied
inputs, not verified facts; no web evidence is fetched or written to the DB.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.enrichment.models import CandidateInput, ReconciliationStatus  # noqa: E402
from app.enrichment.reconciliation import RECONCILIATION_SQL, reconcile_candidates  # noqa: E402
from app.shared.config import database_url  # noqa: E402
from app.shared.normalize import normalize_inn  # noqa: E402


TARGET_OKPD2 = "10.51.11.141"
AS_OF = date(2026, 1, 1)
CANDIDATES = (
    CandidateInput("7622012124", "ООО «Переславский молочный комбинат»"),
    CandidateInput("0257011170", "ООО «Бирский комбинат молочных продуктов»"),
    CandidateInput("5320000979", "АО «Боровичский молочный завод»"),
    CandidateInput("5028002303", "ЗАО ЗСМ «Можайский»"),
    CandidateInput("5007126820", "ООО «ААП»"),
    CandidateInput("3128004452", "ЗАО МК «Авида»"),
)


def _index_names(plan: dict) -> list[str]:
    names = set()
    pending = [plan]
    while pending:
        node = pending.pop()
        if node.get("Index Name"):
            names.add(node["Index Name"])
        pending.extend(node.get("Plans", []))
    return sorted(names)


def _performance(conn: psycopg.Connection, target: str, as_of: date) -> dict:
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        reconcile_candidates(conn, CANDIDATES, target, as_of)
        samples.append(round((time.perf_counter() - start) * 1000, 3))
    inns = sorted({norm.inn for item in CANDIDATES if (norm := normalize_inn(item.supplier_inn)).inn
                   and not norm.flags})
    query = sql.SQL("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ") + sql.SQL(RECONCILIATION_SQL)
    explain = conn.execute(query, {"inns": inns, "target": target, "as_of": as_of}).fetchone()[0][0]
    return {"candidate_count": len(CANDIDATES), "samples_ms": samples,
            "median_ms": statistics.median(samples),
            "explain_execution_ms": round(explain["Execution Time"], 3),
            "explain_planning_ms": round(explain["Planning Time"], 3),
            "indexes_used": _index_names(explain["Plan"])}


def _report(conn: psycopg.Connection, target: str, as_of: date) -> dict:
    candidates = reconcile_candidates(conn, CANDIDATES, target, as_of)
    counts = Counter(c.reconciliation_status.value for c in candidates)
    findings = []
    if any(not c.inn_valid for c in candidates):
        findings.append("One or more supplied INNs failed existing validation rules.")
    return {
        "task": "P3-002A",
        "target_okpd2": target,
        "as_of": as_of,
        "source_tables": ["supplier", "supplier_history", "procurement_lot", "procurement_item"],
        "definitions": {
            "historical_universe": "Valid observed supplier_history relations with publish_date < as_of",
            "exact_category": "A historical relation to a lot containing the exact procurement_item.okpd2_code before as_of",
            "historical_lot_count": "Distinct historical lots for this supplier across all categories before as_of",
            "historical_win_count": "Distinct historical lots won by this supplier across all categories before as_of",
            "target_category_lot_count": "Distinct historical lots with this exact OKPD2 value and supplier relation before as_of",
            "target_category_win_count": "Distinct winning lots with this exact OKPD2 value before as_of",
        },
        "status_counts": {status.value: counts[status.value] for status in ReconciliationStatus},
        "candidates": [candidate.to_dict() for candidate in candidates],
        "data_quality_findings": findings,
        "performance": _performance(conn, target, as_of),
        "limitations": [
            "Supplied company names are manual input and have not been independently verified.",
            "INN validity establishes identifier format and checksum only, not business identity, activity, or product scope.",
            "EXTERNAL_NEW means absent from observed canonical procurement history before as_of, not verified or absent from the market.",
            "AIS_GZ provides observed winner rows only; EM includes observed winner and non-winner rows.",
            "No external evidence was fetched, and no canonical enrichment rows were inserted.",
        ],
    }


def _markdown(report: dict) -> str:
    lines = ["# P3-002A — External Candidate Reconciliation", "",
             f"Target exact observed OKPD2 value: `{report['target_okpd2']}`. History cutoff: `publish_date < {report['as_of']}`.",
             "Supplied names are unverified inputs; INN validity and historical reconciliation are separate from evidence verification.", "",
             "## Results", "",
             "| INN | Supplied name | INN valid | Global history | Exact category | First / last observed | Historical lots / wins | Exact lots / wins | Status | Verification |",
             "|---|---|---|---|---|---|---:|---:|---|---|"]
    for candidate in report["candidates"]:
        first = candidate["historical_first_seen"] or "—"
        last = candidate["historical_last_seen"] or "—"
        lines.append(
            f"| `{candidate['supplier_inn']}` | {candidate['company_name']} | {candidate['inn_valid']} | "
            f"{candidate['historically_known']} | {candidate['target_category_observed']} | {first} / {last} | "
            f"{candidate['historical_lot_count']} / {candidate['historical_win_count']} | "
            f"{candidate['target_category_lot_count']} / {candidate['target_category_win_count']} | "
            f"{candidate['reconciliation_status'].value} | {candidate['verification_status'].value} |"
        )
    lines += ["", "## Status counts", ""]
    for status, count in report["status_counts"].items():
        lines.append(f"- `{status}`: {count}")
    lines += ["", "## Definitions", ""]
    lines += [f"- **{name}:** {definition}." for name, definition in report["definitions"].items()]
    p = report["performance"]
    lines += ["", "## Performance", "",
              f"Six-candidate set-based reconciliation median: **{p['median_ms']:.3f} ms** over three runs; "
              f"EXPLAIN ANALYZE execution: **{p['explain_execution_ms']:.3f} ms**. "
              f"Indexes used: {', '.join(p['indexes_used']) or 'none reported'}.", "",
              "## Data quality findings", ""]
    lines += [f"- {finding}" for finding in report["data_quality_findings"]] or ["- None found in the six supplied INNs."]
    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in report["limitations"]]
    lines += ["", "## P3-002B handoff", "",
              "Curate source records per candidate and product scope, then review their status and strength before any database ingestion. Keep reconciliation and verification decisions independent.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=AS_OF)
    parser.add_argument("--target-okpd2", default=TARGET_OKPD2)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    with psycopg.connect(database_url()) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        report = _report(conn, args.target_okpd2, args.as_of)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "p3_002a_external_reconciliation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (args.output_dir / "p3_002a_external_reconciliation.md").write_text(_markdown(report), encoding="utf-8")
    print(f"Wrote P3-002A reconciliation for {len(report['candidates'])} candidates to {args.output_dir}")


if __name__ == "__main__":
    main()
