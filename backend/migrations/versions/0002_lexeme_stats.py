"""Lexeme document-frequency snapshot for query-term selection and IDF weighting (P1-002).

Built by `python -m app.cli search build-stats` from items of lots published strictly before a fixed snapshot date
(default 2024-07-01 — earlier than every benchmark split), so no future vocabulary statistics leak into replay.

Revision ID: 0002_lexeme_stats
Revises: 0001_organizer_schema
Create Date: 2026-10-01
"""
from alembic import op

revision = "0002_lexeme_stats"
down_revision = "0001_organizer_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE lexeme_stats (
            lexeme  text PRIMARY KEY,
            ndoc    integer NOT NULL CHECK (ndoc > 0)
        );
        CREATE TABLE lexeme_stats_meta (
            id                 boolean PRIMARY KEY DEFAULT true CHECK (id),
            snapshot_before    date    NOT NULL,
            documents          integer NOT NULL,
            ts_config          text    NOT NULL,
            built_at           timestamptz NOT NULL DEFAULT now()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS lexeme_stats, lexeme_stats_meta")
