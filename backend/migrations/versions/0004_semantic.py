"""Semantic text index (P2-001; added only after the feasibility gate returned GO — reports/p2_001_feasibility.json).

One row per distinct normalized product text (text_hash = md5(normalized_text)); first_seen_publish_date = earliest item date of the text.
Temporal safety: a text is eligible only if first_seen_publish_date < as_of, AND every item/lot used as evidence must itself satisfy
publish_date < as_of (enforced in the retrieval SQL). The HNSW index is built by `python -m app.cli semantic build` after the bulk
embedding (definition below in SEMANTIC_HNSW_DDL).

Revision ID: 0004_semantic
Revises: 0003_item_publish_date
Create Date: 2026-10-01
"""
from alembic import op

revision = "0004_semantic"
down_revision = "0003_item_publish_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE semantic_text (
            text_hash                char(32) PRIMARY KEY,
            normalized_text          text     NOT NULL,
            first_seen_publish_date  date     NOT NULL,
            embedding                vector(384),
            model_revision           text,
            CHECK ((embedding IS NULL) = (model_revision IS NULL))
        );
        CREATE INDEX ix_semantic_text_first_seen ON semantic_text (first_seen_publish_date);
        CREATE INDEX ix_item_name_md5_date ON procurement_item (md5(product_name_normalized), publish_date DESC)
            WHERE product_name_normalized IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_item_name_md5_date;
        DROP TABLE IF EXISTS semantic_text;
    """)
