"""Denormalize lot publish_date onto procurement_item + composite OKPD2/date indexes (P1-002 SQL review).

Before (EXPLAIN ANALYZE, dev lot 5668942): OKPD2 'kind' retrieval walked every lot backwards by date (41,114 index probes, 389 ms)
because procurement_item had no date to filter/sort on; ix_item_okpd2_kind could not serve "newest visible lots first".
After: (okpd2_code|okpd2_kind|okpd2_group, publish_date) index range scans with early stop. publish_date here is a physical copy
of procurement_lot.publish_date (same value, kept by ingestion) — the temporal rule is applied as i.publish_date < as_of.

Revision ID: 0003_item_publish_date
Revises: 0002_lexeme_stats
Create Date: 2026-10-01
"""
from alembic import op

from app.db.schema import SECONDARY_INDEXES_0003

revision = "0003_item_publish_date"
down_revision = "0002_lexeme_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE procurement_item ADD COLUMN publish_date date")
    op.execute("UPDATE procurement_item i SET publish_date = l.publish_date FROM procurement_lot l WHERE l.lot_id = i.lot_id")
    op.execute("ALTER TABLE procurement_item ALTER COLUMN publish_date SET NOT NULL")
    for _name, _table, ddl in SECONDARY_INDEXES_0003:
        op.execute(ddl)


def downgrade() -> None:
    for name, _table, _ddl in SECONDARY_INDEXES_0003:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.execute("ALTER TABLE procurement_item DROP COLUMN publish_date")
