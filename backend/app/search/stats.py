"""Lexeme document-frequency snapshot (IDF) built only from lots published before SNAPSHOT_BEFORE (no future statistics)."""
from __future__ import annotations

import math
from datetime import date

SNAPSHOT_BEFORE = date(2024, 7, 1)   # earlier than every replay split (warm-up starts 2024-07-01)
TS_CONFIG = "russian"


def build(conn, snapshot_before: date = SNAPSHOT_BEFORE) -> dict:
    """Rebuild lexeme_stats in one transaction from items of lots with publish_date < snapshot_before."""
    conn.execute("TRUNCATE lexeme_stats, lexeme_stats_meta")
    docs = conn.execute("""SELECT count(*) FROM procurement_item i JOIN procurement_lot l ON l.lot_id = i.lot_id
                           WHERE l.publish_date < %s AND i.product_name_normalized IS NOT NULL""", (snapshot_before,)).fetchone()[0]
    inner = (f"SELECT to_tsvector('{TS_CONFIG}'::regconfig, i.product_name_normalized) FROM procurement_item i "
             f"JOIN procurement_lot l ON l.lot_id = i.lot_id WHERE l.publish_date < DATE '{snapshot_before.isoformat()}' "
             f"AND i.product_name_normalized IS NOT NULL")
    conn.execute("INSERT INTO lexeme_stats (lexeme, ndoc) SELECT word, ndoc FROM ts_stat(%s)", (inner,))
    conn.execute("INSERT INTO lexeme_stats_meta (snapshot_before, documents, ts_config) VALUES (%s, %s, %s)",
                 (snapshot_before, docs, TS_CONFIG))
    n = conn.execute("SELECT count(*) FROM lexeme_stats").fetchone()[0]
    conn.commit()
    return {"snapshot_before": snapshot_before.isoformat(), "documents": docs, "lexemes": n}


class Idf:
    """idf(l) = ln((N + 1) / (df + 1)) + 1 ; unseen lexemes get the maximum (df = 0)."""

    def __init__(self, conn, lexemes):
        meta = conn.execute("SELECT documents, snapshot_before FROM lexeme_stats_meta").fetchone()
        if meta is None:
            raise RuntimeError("lexeme_stats is empty — run `python -m app.cli search build-stats`")
        self.n, self.snapshot_before = meta
        self.df = dict(conn.execute("SELECT lexeme, ndoc FROM lexeme_stats WHERE lexeme = ANY(%s)", (list(set(lexemes)),)).fetchall())

    def weight(self, lexeme: str) -> float:
        return math.log((self.n + 1) / (self.df.get(lexeme, 0) + 1)) + 1.0

    @property
    def max_weight(self) -> float:
        return math.log(self.n + 1) + 1.0

    def frequent(self, lexeme: str, max_df_ratio: float) -> bool:
        return self.df.get(lexeme, 0) > max_df_ratio * self.n
