"""Read-only, temporal reconciliation of external INNs with canonical history.

Supplier table presence alone is not historical presence. Only valid observed
supplier_history relations with publish_date strictly before as_of qualify.
The exact target code is matched against procurement_item.okpd2_code, never a
broader hierarchy field.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from psycopg import Connection
from psycopg.rows import dict_row

from app.enrichment.models import CandidateInput, ExternalCandidate, ReconciliationStatus
from app.shared.normalize import normalize_inn, normalize_okpd2


RECONCILIATION_SQL = """
WITH matched_supplier AS MATERIALIZED (
    SELECT supplier_id, inn FROM supplier WHERE inn = ANY(%(inns)s)
), observed_history AS MATERIALIZED (
    SELECT DISTINCT s.inn, h.lot_id, h.publish_date, h.is_winner
    FROM matched_supplier s
    JOIN supplier_history h ON h.supplier_id = s.supplier_id
    JOIN procurement_lot l ON l.lot_id = h.lot_id
    WHERE h.publish_date < %(as_of)s AND l.publish_date < %(as_of)s
      AND ((h.platform = 'AIS_GZ' AND h.is_winner
            AND h.coverage_semantics = 'WINNER_ROWS_ONLY_OBSERVED')
           OR (h.platform = 'EM'
            AND h.coverage_semantics = 'MIXED_WINNER_NONWINNER_ROWS_OBSERVED'))
), global_history AS (
    SELECT inn, min(publish_date) AS first_seen, max(publish_date) AS last_seen,
           count(DISTINCT lot_id) AS lot_count,
           count(DISTINCT lot_id) FILTER (WHERE is_winner) AS win_count
    FROM observed_history GROUP BY inn
), target_lots AS MATERIALIZED (
    SELECT DISTINCT lot_id FROM procurement_item
    WHERE okpd2_code = %(target)s AND publish_date < %(as_of)s
), target_history AS (
    SELECT h.inn, count(DISTINCT h.lot_id) AS lot_count,
           count(DISTINCT h.lot_id) FILTER (WHERE h.is_winner) AS win_count
    FROM observed_history h JOIN target_lots t ON t.lot_id = h.lot_id
    GROUP BY h.inn
)
SELECT g.inn, g.first_seen, g.last_seen, g.lot_count AS historical_lot_count,
       g.win_count AS historical_win_count,
       coalesce(t.lot_count, 0) AS target_category_lot_count,
       coalesce(t.win_count, 0) AS target_category_win_count
FROM global_history g LEFT JOIN target_history t ON t.inn = g.inn
ORDER BY g.inn
"""


def _history_by_inn(conn: Connection, inns: list[str], target: str, as_of: date) -> dict[str, dict]:
    if not inns:
        return {}
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(RECONCILIATION_SQL, {"inns": sorted(set(inns)), "target": target, "as_of": as_of})
        return {row["inn"]: row for row in cursor.fetchall()}


def reconcile_candidates(conn: Connection, candidates: Sequence[CandidateInput],
                         target_okpd2: str, as_of: date) -> list[ExternalCandidate]:
    """Preserve input order; every result defaults to UNVERIFIED with no web evidence."""
    if type(as_of) is not date:
        raise ValueError("as_of must be a date for the strict historical cutoff")
    target = normalize_okpd2(target_okpd2)
    if target.flags or target.okpd2_code is None:
        raise ValueError("target_okpd2 must be a valid exact observed OKPD2 value")
    normalized = [(candidate, normalize_inn(candidate.supplier_inn)) for candidate in candidates]
    history = _history_by_inn(conn, [norm.inn for _, norm in normalized if norm.inn and not norm.flags],
                              target.okpd2_code, as_of)
    results = []
    for candidate, norm in normalized:
        record = history.get(norm.inn) if norm.inn and not norm.flags else None
        known = record is not None
        target_observed = bool(record and record["target_category_lot_count"])
        if norm.flags or norm.inn is None:
            status = ReconciliationStatus.INVALID_INN
        elif target_observed:
            status = ReconciliationStatus.CATEGORY_HISTORICAL
        elif known:
            status = ReconciliationStatus.HISTORICAL_OTHER_CATEGORY
        else:
            status = ReconciliationStatus.EXTERNAL_NEW
        results.append(ExternalCandidate(
            supplier_inn=norm.inn, company_name=candidate.company_name,
            target_okpd2=target.okpd2_code, as_of=as_of,
            inn_valid=not norm.flags, inn_validation_flags=tuple(norm.flags),
            reconciliation_status=status, historically_known=known,
            target_category_observed=target_observed,
            historical_first_seen=record["first_seen"] if record else None,
            historical_last_seen=record["last_seen"] if record else None,
            historical_lot_count=record["historical_lot_count"] if record else 0,
            historical_win_count=record["historical_win_count"] if record else 0,
            target_category_lot_count=record["target_category_lot_count"] if record else 0,
            target_category_win_count=record["target_category_win_count"] if record else 0,
        ))
    return results
