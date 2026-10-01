"""Set-based distribution of exact observed OKPD2 values for threshold calibration."""
from __future__ import annotations

from datetime import date

from psycopg import Connection
from psycopg.rows import dict_row

from app.analytics.pool_health import _effective_as_of


DISTRIBUTION_SQL = """
WITH code_lots AS MATERIALIZED (
    SELECT DISTINCT i.okpd2_code AS code, i.lot_id
    FROM procurement_item i
    WHERE i.okpd2_code IS NOT NULL AND i.publish_date < %(as_of)s
), scope_lots AS MATERIALIZED (
    SELECT c.code, c.lot_id, l.procedure_id, l.customer_inn
    FROM code_lots c JOIN procurement_lot l ON l.lot_id = c.lot_id
    WHERE l.publish_date < %(as_of)s
), support AS (
    SELECT code, count(*) AS lot_count, count(DISTINCT procedure_id) AS procurement_count,
           count(DISTINCT customer_inn) AS customer_count
    FROM scope_lots GROUP BY code
), relations AS MATERIALIZED (
    SELECT DISTINCT sl.code, h.lot_id, h.supplier_id, h.is_winner, h.platform
    FROM scope_lots sl JOIN supplier_history h ON h.lot_id = sl.lot_id
    WHERE h.publish_date < %(as_of)s AND (
        (h.platform = 'AIS_GZ' AND h.is_winner AND h.coverage_semantics = 'WINNER_ROWS_ONLY_OBSERVED')
        OR (h.platform = 'EM' AND h.coverage_semantics = 'MIXED_WINNER_NONWINNER_ROWS_OBSERVED')
    )
), per_supplier AS (
    SELECT code, supplier_id,
           count(*) FILTER (WHERE is_winner) AS awards,
           bool_or(platform = 'EM') AS em_observed,
           bool_or(platform = 'EM' AND is_winner) AS em_winning,
           bool_or(platform = 'AIS_GZ' AND is_winner) AS ais_gz_winning
    FROM relations GROUP BY code, supplier_id
), ranked AS (
    SELECT *, row_number() OVER (PARTITION BY code ORDER BY awards DESC, supplier_id) AS position
    FROM per_supplier
), concentration AS (
    SELECT code, count(*) AS observed_supplier_count,
           count(*) FILTER (WHERE awards > 0) AS winning_supplier_count,
           count(*) FILTER (WHERE em_observed) AS em_observed_supplier_count,
           count(*) FILTER (WHERE em_winning) AS em_winning_supplier_count,
           count(*) FILTER (WHERE ais_gz_winning) AS ais_gz_winning_supplier_count,
           sum(awards) AS award_count,
           max(awards) AS top1_awards,
           sum(awards) FILTER (WHERE position <= 3) AS top3_awards,
           sum(awards * awards) AS squared_awards
    FROM ranked GROUP BY code
)
SELECT s.code, s.lot_count, s.procurement_count, s.customer_count,
       coalesce(c.observed_supplier_count, 0) AS observed_supplier_count,
       coalesce(c.winning_supplier_count, 0) AS winning_supplier_count,
       coalesce(c.em_observed_supplier_count, 0) AS em_observed_supplier_count,
       coalesce(c.em_winning_supplier_count, 0) AS em_winning_supplier_count,
       coalesce(c.ais_gz_winning_supplier_count, 0) AS ais_gz_winning_supplier_count,
       coalesce(c.award_count, 0)::bigint AS award_count,
       CASE WHEN c.award_count > 0 THEN c.top1_awards::double precision / c.award_count ELSE NULL END AS top1_share,
       CASE WHEN c.award_count > 0 THEN c.top3_awards::double precision / c.award_count ELSE NULL END AS top3_share,
       CASE WHEN c.award_count > 0 THEN c.squared_awards::double precision /
            (c.award_count::double precision * c.award_count) ELSE NULL END AS hhi
FROM support s LEFT JOIN concentration c ON c.code = s.code
ORDER BY s.code
"""


def full_code_distribution(conn: Connection, as_of: date | None = None) -> tuple[date, list[dict]]:
    """Return one row per exact OKPD2 value represented in the source, including zero-award pools."""
    cutoff = _effective_as_of(conn, as_of)
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(DISTRIBUTION_SQL, {"as_of": cutoff})
        return cutoff, cursor.fetchall()
