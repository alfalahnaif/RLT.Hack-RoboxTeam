"""P5-002A official website & contact discovery: website verification status + signals, contact verification basis, and an
append-only history of every website identity check (evidence history; the profile keeps only the current snapshot).

Additive only (nullable / defaulted columns, new table); 0004 and earlier are untouched.

Revision ID: 0006_contact_discovery
Revises: 0005_supplier_enrichment
Create Date: 2026-10-02
"""
from alembic import op

revision = "0006_contact_discovery"
down_revision = "0005_supplier_enrichment"
branch_labels = None
depends_on = None

STATUSES = "('VERIFIED_STRONG', 'VERIFIED_COMPOSITE', 'REJECTED', 'UNKNOWN')"


def upgrade() -> None:
    op.execute(f"""
        ALTER TABLE supplier_enrichment_profile
            ADD COLUMN website_verification_status text CHECK (website_verification_status IN {STATUSES}),
            ADD COLUMN website_signals text[] NOT NULL DEFAULT '{{}}',
            ADD COLUMN website_discovered_via text;
        ALTER TABLE supplier_enrichment_profile
            ADD CONSTRAINT ck_official_website_verified
            CHECK (official_website IS NULL OR website_verification_status IS NULL
                   OR website_verification_status IN ('VERIFIED_STRONG', 'VERIFIED_COMPOSITE'));

        ALTER TABLE supplier_contact ADD COLUMN verification_basis text;

        -- append-only: one row per candidate website checked in a run (accepted or rejected), never updated
        CREATE TABLE supplier_website_check (
            id                  uuid PRIMARY KEY,
            seq                 bigint GENERATED ALWAYS AS IDENTITY,
            inn                 text NOT NULL CHECK (inn ~ '^([0-9]{{10}}|[0-9]{{12}})$'),
            checked_at          timestamptz NOT NULL,
            candidate_url       text NOT NULL,
            official_url        text CHECK (official_url ~ '^https?://'),
            discovered_via      text,
            verification_status text NOT NULL CHECK (verification_status IN {STATUSES}),
            signals             text[] NOT NULL DEFAULT '{{}}',
            reason              text,
            pipeline_version    text NOT NULL
        );
        CREATE INDEX ix_website_check_inn ON supplier_website_check (inn, seq);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS supplier_website_check;
        ALTER TABLE supplier_contact DROP COLUMN IF EXISTS verification_basis;
        ALTER TABLE supplier_enrichment_profile DROP CONSTRAINT IF EXISTS ck_official_website_verified,
            DROP COLUMN IF EXISTS website_discovered_via, DROP COLUMN IF EXISTS website_signals,
            DROP COLUMN IF EXISTS website_verification_status;
    """)
