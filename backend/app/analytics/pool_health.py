"""Temporal-safe, historical OKPD2 supplier-pool health from canonical tables only.

One award is one distinct (lot, winning supplier) relation in a scope. The HHI
uses each supplier's share of these observed awards, not money or all bids.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from psycopg import Connection
from psycopg import sql

from app.analytics.models import (PoolAlternatives, PoolConcentration, PoolHealth,
                                  PoolScope, PoolSupport, PoolSuppliers, PoolThresholds)


SCOPE_COLUMNS = {"okpd2_code": "okpd2_code", "okpd2_group": "okpd2_group", "okpd2_class": "okpd2_class"}
LIMITATIONS = (
    "Historical procurement concentration does not establish current market concentration.",
    "Procurement records do not cover the entire supplier market.",
    "AIS_GZ provides observed winner rows only; EM contains observed winner and non-winner rows.",
    "Observed EM non-winners do not establish a complete participant or market population.",
    "Supplier registration region does not establish delivery capability.",
    "External supplier expansion is a separate stage.",
    "Labels are Supplier Radar analytical categories, not legal classifications.",
)


def concentration_shares(award_counts: list[int]) -> tuple[float | None, float | None, float | None]:
    """Top-one share, top-three share and 0..1 HHI from positive award counts."""
    counts = sorted((n for n in award_counts if n > 0), reverse=True)
    total = sum(counts)
    if total == 0:
        return None, None, None
    return counts[0] / total, sum(counts[:3]) / total, sum((n / total) ** 2 for n in counts)


def classify(lots: int, awards: int, top1: float | None, hhi: float | None,
             thresholds: PoolThresholds) -> str:
    if lots < thresholds.min_lots or awards < thresholds.min_awards or top1 is None or hhi is None:
        return "INSUFFICIENT_DATA"
    if top1 >= thresholds.very_high_top1 or hhi >= thresholds.very_high_hhi:
        return "VERY_HIGH"
    if top1 >= thresholds.high_top1 or hhi >= thresholds.high_hhi:
        return "HIGH"
    if top1 >= thresholds.moderate_top1 or hhi >= thresholds.moderate_hhi:
        return "MODERATE"
    return "LOW"


def _effective_as_of(conn: Connection, requested: date | None) -> date:
    if requested is not None:
        return requested
    latest = conn.execute("SELECT max(publish_date) FROM procurement_lot").fetchone()[0]
    return latest + timedelta(days=1) if latest else date.today()


def _pool_query(kind: str) -> sql.Composed:
    return sql.SQL("""
        WITH scope_lots AS MATERIALIZED (
            SELECT DISTINCT l.lot_id, l.procedure_id, l.customer_inn, l.publish_date
            FROM procurement_item i
            JOIN procurement_lot l ON l.lot_id = i.lot_id
            WHERE i.{} = %(value)s AND i.publish_date < %(as_of)s AND l.publish_date < %(as_of)s
        ), relations AS MATERIALIZED (
            SELECT DISTINCT h.lot_id, h.supplier_id, h.is_winner, h.platform, h.publish_date
            FROM scope_lots sl JOIN supplier_history h ON h.lot_id = sl.lot_id
            WHERE h.publish_date < %(as_of)s AND (
                (h.platform = 'AIS_GZ' AND h.is_winner AND h.coverage_semantics = 'WINNER_ROWS_ONLY_OBSERVED')
                OR (h.platform = 'EM' AND h.coverage_semantics = 'MIXED_WINNER_NONWINNER_ROWS_OBSERVED')
            )
        ), per_supplier AS (
            SELECT r.supplier_id, s.inn,
                   count(*) FILTER (WHERE r.is_winner) AS awards,
                   count(*) AS observed_relations,
                   count(*) FILTER (WHERE r.is_winner AND r.publish_date >= %(recent_start)s) AS recent_awards,
                   bool_or(r.platform = 'EM') AS em_observed,
                   bool_or(r.platform = 'EM' AND r.is_winner) AS em_winning,
                   bool_or(r.platform = 'AIS_GZ' AND r.is_winner) AS ais_gz_winning
            FROM relations r JOIN supplier s ON s.supplier_id = r.supplier_id
            GROUP BY r.supplier_id, s.inn
        )
        SELECT (SELECT count(*) FROM scope_lots) AS lots,
               (SELECT count(DISTINCT procedure_id) FROM scope_lots) AS procurements,
               (SELECT count(DISTINCT customer_inn) FROM scope_lots) AS customers,
               COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.awards DESC, p.supplier_id)
                         FROM per_supplier p), '[]'::jsonb) AS suppliers
    """).format(sql.Identifier(SCOPE_COLUMNS[kind]))


def _pool_rows(conn: Connection, scope: PoolScope, recent_start: date) -> tuple[int, int, int, list[dict]]:
    lots, procurements, customers, suppliers = conn.execute(_pool_query(scope.kind),
                                                            {"value": scope.value, "as_of": scope.as_of,
                                                             "recent_start": recent_start}).fetchone()
    return lots, procurements, customers, suppliers


def explain_pool(conn: Connection, scope: PoolScope) -> dict:
    """PostgreSQL EXPLAIN ANALYZE for the exact service query (read-only)."""
    scope = replace(scope, as_of=_effective_as_of(conn, scope.as_of))
    query = sql.SQL("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ") + _pool_query(scope.kind)
    plan = conn.execute(query, {"value": scope.value, "as_of": scope.as_of,
                                "recent_start": scope.as_of - timedelta(days=scope.recent_days)}).fetchone()[0][0]
    return {"execution_ms": plan["Execution Time"], "planning_ms": plan["Planning Time"],
            "plan": plan["Plan"]}


def _reasons(support: PoolSupport, suppliers: PoolSuppliers, concentration: PoolConcentration) -> tuple[str, ...]:
    if support.awards == 0:
        return ("No observed winning supplier awards are available in this scope.",)
    reasons = [f"{suppliers.winning} suppliers won {support.awards} observed awards across {support.lots} lots.",
               f"The top supplier accounts for {concentration.top1_share:.1%} of observed awards.",
               f"The top three suppliers account for {concentration.top3_share:.1%} of observed awards.",
               f"Award-share HHI is {concentration.hhi:.3f}."]
    if concentration.label == "INSUFFICIENT_DATA":
        reasons.append("This category has too little history for a concentration label.")
    else:
        reasons.append(f"Supplier Radar historical concentration label: {concentration.label}.")
    return tuple(reasons)


def analyze_pool(conn: Connection, scope: PoolScope, thresholds: PoolThresholds,
                 alternative_limit: int = 10) -> PoolHealth:
    """Analyze one full code, group or class using history strictly before as_of."""
    if alternative_limit < 0:
        raise ValueError("alternative_limit must be non-negative")
    scope = replace(scope, as_of=_effective_as_of(conn, scope.as_of))
    recent_start = scope.as_of - timedelta(days=scope.recent_days)
    lots, procurements, customers, rows = _pool_rows(conn, scope, recent_start)
    winners = [r for r in rows if r["awards"] > 0]
    awards = sum(r["awards"] for r in winners)
    support = PoolSupport(lots, procurements, customers, awards)
    suppliers = PoolSuppliers(len(rows), len(winners), sum(r["recent_awards"] > 0 for r in winners),
                              sum(bool(r["em_observed"]) for r in rows),
                              sum(bool(r["em_winning"]) for r in rows),
                              sum(bool(r["ais_gz_winning"]) for r in rows))
    top1, top3, hhi = concentration_shares([r["awards"] for r in winners])
    concentration = PoolConcentration(top1, top3, hhi, classify(lots, awards, top1, hhi, thresholds))
    dominant = winners[0] if winners else None
    alternatives = [r for r in rows if dominant and r["supplier_id"] != dominant["supplier_id"]]
    alt = PoolAlternatives(len(alternatives), sum(r["awards"] > 0 for r in alternatives),
                           sum(r["awards"] == 0 for r in alternatives), tuple(alternatives[:alternative_limit]))
    return PoolHealth(scope, support, suppliers, concentration, dominant, alt,
                      _reasons(support, suppliers, concentration), LIMITATIONS)
