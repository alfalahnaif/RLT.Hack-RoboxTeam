#!/usr/bin/env python3
"""Read-only P3-001 supplier-pool report from canonical PostgreSQL tables.

Usage:
  DATABASE_URL=... python scripts/analyze_pool_health.py
  DATABASE_URL=... python scripts/analyze_pool_health.py --scope-type okpd2_group --scope-value 10.51
  DATABASE_URL=... python scripts/analyze_pool_health.py --as-of 2025-01-01 --recent-days 180
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.analytics.distribution import full_code_distribution  # noqa: E402
from app.analytics.models import PoolScope, PoolThresholds  # noqa: E402
from app.analytics.pool_health import analyze_pool, classify, explain_pool  # noqa: E402
from app.shared.config import database_url  # noqa: E402


# Calibrated from the 2026-01-01 full-code distribution; overridable in the service.
THRESHOLDS = PoolThresholds(20, 20, moderate_top1=.25, high_top1=.50, very_high_top1=.80,
                            moderate_hhi=.125, high_hhi=.32, very_high_hhi=.60)
DEMO_CODES = {
    "primary": "10.51.11.141",       # sterilized milk
    "contrast": "10.20.25.111",      # natural canned fish, similar lot count and dispersed awards
    "backup": "01.25.19.150",        # cranberry, concentrated backup
    "reconciliation": "10.39.17.111", # tomato puree, previously reported approximate values
    "rice_flour": "10.61.22.130",
}
PERCENTILES = (.25, .50, .75, .90, .95)


def percentiles(values: list[float]) -> dict[str, float | None]:
    numbers = sorted(float(value) for value in values if value is not None)
    if not numbers:
        return {f"p{int(p * 100)}": None for p in PERCENTILES}
    result = {}
    for p in PERCENTILES:
        position = (len(numbers) - 1) * p
        lower = int(position)
        upper = min(lower + 1, len(numbers) - 1)
        result[f"p{int(p * 100)}"] = round(numbers[lower] +
                                               (numbers[upper] - numbers[lower]) * (position - lower), 4)
    return result


def describe_distribution(rows: list[dict]) -> dict:
    awarded = [r for r in rows if r["award_count"] > 0]
    eligible = [r for r in rows if r["lot_count"] >= THRESHOLDS.min_lots and
                r["award_count"] >= THRESHOLDS.min_awards]
    fields = ("lot_count", "award_count", "observed_supplier_count", "winning_supplier_count",
              "top1_share", "top3_share", "hhi")
    return {
        "all_codes": len(rows),
        "codes_with_awards": len(awarded),
        "eligible_codes": len(eligible),
        "all_awarded_percentiles": {f: percentiles([r[f] for r in awarded]) for f in fields},
        "eligible_percentiles": {f: percentiles([r[f] for r in eligible]) for f in fields},
    }


def product_names(conn: psycopg.Connection, code: str, cutoff: date) -> list[str]:
    rows = conn.execute("""SELECT product_name_raw, count(*) AS occurrences
                           FROM procurement_item WHERE okpd2_code = %s AND publish_date < %s
                           GROUP BY product_name_raw ORDER BY occurrences DESC, product_name_raw LIMIT 3""",
                        (code, cutoff)).fetchall()
    return [name.strip() for name, _ in rows]


def category_card(conn: psycopg.Connection, code: str, cutoff: date, recent_days: int) -> dict:
    pool = analyze_pool(conn, PoolScope("okpd2_code", code, cutoff, recent_days), THRESHOLDS)
    card = pool.to_dict()
    card["representative_product_names"] = product_names(conn, code, cutoff)
    return card


def timed_pool(conn: psycopg.Connection, scope: PoolScope) -> dict:
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        analyze_pool(conn, scope, THRESHOLDS)
        samples.append(round((time.perf_counter() - start) * 1000, 2))
    explain = explain_pool(conn, scope)
    return {"samples_ms": samples, "median_ms": statistics.median(samples),
            "explain_execution_ms": round(explain["execution_ms"], 2),
            "explain_planning_ms": round(explain["planning_ms"], 2),
            "plan_root": explain["plan"]["Node Type"]}


def fmt_share(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def fmt_hhi(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def fmt_number(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def markdown(report: dict) -> str:
    d = report["distribution"]
    t = report["thresholds"]
    all_p = d["all_awarded_percentiles"]
    eligible_p = d["eligible_percentiles"]
    lines = ["# P3-001 Supplier Pool Health — real-data analysis", "",
             f"As of **{report['as_of']}** (strictly earlier publish dates); recent window **{report['recent_days']} days**.",
             "Source: canonical `procurement_lot`, `procurement_item`, `supplier_history`, `supplier` only.", "",
             "## Metric definitions", "",
             "- A category lot counts once even when it has repeated matching items; procurements are distinct procedure IDs and customers are distinct non-null customer INNs.",
             "- An observed supplier has a valid historical relation. AIS_GZ supplies observed winner rows only; EM supplies observed winner and non-winner rows. AIS_GZ is never treated as a complete participant list.",
             "- A winning supplier has at least one `is_winner=true` relation. An award is one distinct `(lot_id, supplier_id)` winning relation; it is not a monetary share.",
             "- A recent winning supplier has at least one winning relation with publish date in `[as_of - recent_days, as_of)`.",
             "- Top-one and top-three shares use award counts. HHI = Σ(awards for supplier / total awards)², on a 0–1 scale.",
             "- Winning alternatives are other historical winners; observed-only alternatives have EM non-winning evidence but no award in this scope. No recommendation score is used.", "",
             "## Dataset distribution", "",
             f"**{d['all_codes']:,}** full OKPD2 codes; **{d['codes_with_awards']:,}** with awards; **{d['eligible_codes']:,}** pass the support rule.", "",
             "| Metric | Population | p25 | p50 | p75 | p90 | p95 |", "|---|---|---:|---:|---:|---:|---:|"]
    for population, key in (("All with awards", "all_awarded_percentiles"), ("Eligible", "eligible_percentiles")):
        for field, values in d[key].items():
            lines.append("| " + field + " | " + population + " | " + " | ".join(str(values[f"p{p}"]) for p in (25, 50, 75, 90, 95)) + " |")
    lines += ["", "## Analytical thresholds", "",
              f"Minimum support: **{t['min_lots']} lots and {t['min_awards']} observed awards**; otherwise `INSUFFICIENT_DATA`.",
              f"The all-awarded median is {fmt_number(all_p['lot_count']['p50'], 0)} lots and {fmt_number(all_p['award_count']['p50'], 0)} awards; 20/20 avoids confident labels for the small-category majority while retaining {d['eligible_codes']:,} categories.",
              f"Among eligible categories, p75 top-one = {fmt_share(eligible_p['top1_share']['p75'])} and p75 HHI = {fmt_number(eligible_p['hhi']['p75'], 4)}; p95 top-one = {fmt_share(eligible_p['top1_share']['p95'])} and p95 HHI = {fmt_number(eligible_p['hhi']['p95'], 4)}.",
              "Thresholds are product analytics, not legal or competition-law thresholds. The label is the highest tier met by **either** indicator:", "",
              "| Label | Top-one share | HHI |", "|---|---:|---:|",
              "| MODERATE | ≥ 25% | ≥ 0.125 |", "| HIGH | ≥ 50% | ≥ 0.320 |",
              "| VERY_HIGH | ≥ 80% | ≥ 0.600 |", "| LOW | below both MODERATE boundaries | |", "",
              "## Category counts", "", "| Label | Full-code categories |", "|---|---:|"]
    for label in ("INSUFFICIENT_DATA", "LOW", "MODERATE", "HIGH", "VERY_HIGH"):
        lines.append(f"| {label} | {report['category_counts'][label]:,} |")
    primary_lots = report["demo_categories"]["primary"]["support"]["lots"]
    contrast_lots = report["demo_categories"]["contrast"]["support"]["lots"]
    backup_lots = report["demo_categories"]["backup"]["support"]["lots"]
    lines += ["", "## Demo category cards", "",
              f"Selection: sterilized milk and natural canned fish have comparable activity ({primary_lots} vs {contrast_lots} lots), familiar source product descriptions, and sharply different award concentration. Cranberry is a second high-concentration example with {backup_lots} lots. Selection does not use recommendation performance.", ""]
    for role in ("primary", "contrast", "backup"):
        card = report["demo_categories"][role]
        c = card["concentration"]
        s = card["support"]
        suppliers = card["suppliers"]
        alt = card["alternatives"]
        dominant = card["dominant_supplier"] or {}
        lines += [f"### {role.title()}: `{card['scope']['value']}` — {c['label']}", "",
                  f"Representative source product: {card['representative_product_names'][0] if card['representative_product_names'] else 'unavailable'}.",
                  f"{s['lots']} lots · {s['procurements']} procurements · {s['customers']} customers · {s['awards']} observed awards · {suppliers['winning']} winning suppliers · {suppliers['observed']} observed suppliers.",
                  f"Top one {fmt_share(c['top1_share'])} · top three {fmt_share(c['top3_share'])} · HHI {fmt_hhi(c['hhi'])}.",
                  f"Dominant supplier `{dominant.get('inn', 'unavailable')}`: {dominant.get('awards', 0)} observed awards. Historical alternatives: {alt['total_count']} total ({alt['winning_count']} winners, {alt['observed_only_count']} observed-only).", ""]
    lines += ["## Reconciliation of known categories", "", "| Code | Lots | Winners | Top one | Top three | HHI | Label |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for role in ("primary", "backup", "rice_flour", "reconciliation"):
        card = report["demo_categories"][role]
        c, s = card["concentration"], card["support"]
        lines.append(f"| {card['scope']['value']} | {s['lots']} | {card['suppliers']['winning']} | {fmt_share(c['top1_share'])} | {fmt_share(c['top3_share'])} | {fmt_hhi(c['hhi'])} | {c['label']} |")
    lines += ["", "## Other supported categories", "",
              "Top historical concentration among categories with at least 100 lots and 100 awards:", "",
              "| Code | Lots | Winners | Top one | HHI |", "|---|---:|---:|---:|---:|"]
    for row in report["top_concentrated_with_100_lots_and_awards"]:
        lines.append(f"| {row['code']} | {row['lot_count']} | {row['winning_supplier_count']} | {fmt_share(row['top1_share'])} | {fmt_hhi(row['hhi'])} |")
    lines += ["", "Lower concentration comparisons with 100–1,000 lots and at least 20 winning suppliers:", "",
              "| Code | Lots | Winners | Top one | HHI |", "|---|---:|---:|---:|---:|"]
    for row in report["lower_concentration_comparisons"]:
        lines.append(f"| {row['code']} | {row['lot_count']} | {row['winning_supplier_count']} | {fmt_share(row['top1_share'])} | {fmt_hhi(row['hhi'])} |")
    lines += ["", "## Performance", "",
              f"Full distribution query: **{report['performance']['distribution_seconds']:.2f} s** for {d['all_codes']:,} codes."]
    for kind in ("single_code", "group"):
        p = report["performance"][kind]
        lines.append(f"- {kind}: median service latency **{p['median_ms']:.2f} ms** (three runs); EXPLAIN ANALYZE execution **{p['explain_execution_ms']:.2f} ms**, plan root `{p['plan_root']}`.")
    lines.append("Existing indexes supported interactive single-code and group analysis in this run; the full distribution is a batch report. No new index or migration was added.")
    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in report["limitations"]]
    lines += ["", "## Integration note", "",
              "Call `app.analytics.pool_health.analyze_pool(connection, PoolScope(...), PoolThresholds(...))` from a later CLI/API change after parallel search work is merged. The current script is read-only and independent.", ""]
    return "\n".join(lines)


def report_run(conn: psycopg.Connection, as_of: date | None, recent_days: int) -> dict:
    start = time.perf_counter()
    cutoff, rows = full_code_distribution(conn, as_of)
    distribution_seconds = time.perf_counter() - start
    counts = Counter(classify(r["lot_count"], r["award_count"], r["top1_share"], r["hhi"], THRESHOLDS)
                     for r in rows)
    cards = {role: category_card(conn, code, cutoff, recent_days) for role, code in DEMO_CODES.items()}
    eligible = [r for r in rows if r["lot_count"] >= 100 and r["award_count"] >= 100]
    concentrated = sorted(eligible, key=lambda r: (-r["hhi"], -r["lot_count"], r["code"]))[:10]
    healthier = sorted((r for r in rows if 100 <= r["lot_count"] <= 1000 and r["winning_supplier_count"] >= 20),
                       key=lambda r: (r["hhi"], -r["lot_count"], r["code"]))[:10]
    return {
        "as_of": cutoff,
        "recent_days": recent_days,
        "metric_definitions": {
            "lot_count": "Distinct lots with a matching OKPD2 scope and publish_date < as_of",
            "procurement_count": "Distinct procedure_id values among matching lots",
            "award_count": "Distinct (lot_id, supplier_id) winning relations in scope",
            "top1_share": "Largest supplier award_count / total award_count",
            "top3_share": "Three largest supplier award_counts / total award_count",
            "hhi": "Sum of squared supplier award shares, on a 0–1 scale",
            "recent_winning": "Winning supplier with publish_date >= as_of - recent_days and < as_of",
        },
        "platform_semantics": {"AIS_GZ": "WINNER_ROWS_ONLY_OBSERVED",
                               "EM": "MIXED_WINNER_NONWINNER_ROWS_OBSERVED"},
        "distribution": describe_distribution(rows),
        "thresholds": vars(THRESHOLDS),
        "category_counts": {label: counts[label] for label in
                            ("INSUFFICIENT_DATA", "LOW", "MODERATE", "HIGH", "VERY_HIGH")},
        "demo_selection": {
            "primary": "Sterilized milk: recognizable product and very high concentration",
            "contrast": "Natural canned fish: recognizable food product and more dispersed awards",
            "backup": "Cranberry: another high-concentration example",
            "basis": "Similar support, understandable source product names, visible structural contrast; no recommendation score",
        },
        "top_concentrated_with_100_lots_and_awards": concentrated,
        "lower_concentration_comparisons": healthier,
        "demo_categories": cards,
        "performance": {"distribution_seconds": round(distribution_seconds, 2),
                        "single_code": timed_pool(conn, PoolScope("okpd2_code", DEMO_CODES["primary"], cutoff, recent_days)),
                        "group": timed_pool(conn, PoolScope("okpd2_group", "10.51", cutoff, recent_days))},
        "limitations": cards["primary"]["limitations"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, help="Strict publish_date cutoff (YYYY-MM-DD)")
    parser.add_argument("--recent-days", type=int, default=365)
    parser.add_argument("--scope-type", choices=("okpd2_code", "okpd2_group", "okpd2_class"))
    parser.add_argument("--scope-value")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    if args.recent_days < 1 or bool(args.scope_type) != bool(args.scope_value):
        parser.error("recent-days must be positive; scope-type and scope-value must be supplied together")
    with psycopg.connect(database_url()) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        if args.scope_type:
            result = analyze_pool(conn, PoolScope(args.scope_type, args.scope_value,
                                                  args.as_of, args.recent_days), THRESHOLDS)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
            return
        report = report_run(conn, args.as_of, args.recent_days)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "p3_001_pool_health.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (args.output_dir / "p3_001_pool_health.md").write_text(markdown(report), encoding="utf-8")
    print(f"Wrote P3-001 reports for {report['distribution']['all_codes']} codes to {args.output_dir}")


if __name__ == "__main__":
    main()
