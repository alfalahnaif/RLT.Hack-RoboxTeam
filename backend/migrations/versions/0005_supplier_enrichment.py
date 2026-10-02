"""P5-001A Supplier 360 enrichment persistence (keyed by supplier INN; reusable by every procurement relation of that INN).

External enrichment only — historical procurement evidence stays in the canonical tables and is never copied here.
No FK to `supplier`: external (non-historical) suppliers can be enriched too, and organizer reloads must not cascade here;
`supplier_id` is the deterministic uuid5 of the INN (app.shared.ids.supplier_uuid) when the INN is historical.
The legacy (empty) supplier_profile / supplier_evidence tables of 0001 are left untouched.

Revision ID: 0005_supplier_enrichment
Revises: 0004_semantic
Create Date: 2026-10-02
"""
from alembic import op

revision = "0005_supplier_enrichment"
down_revision = "0004_semantic"
branch_labels = None
depends_on = None

INN = "text NOT NULL CHECK (inn ~ '^([0-9]{10}|[0-9]{12})$')"
SRC = "text NOT NULL CHECK (source_type IN ('FNS_EGRUL', 'FNS_EGRUL_DERIVED_REGISTRY', 'FIRST_PARTY'))"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE supplier_enrichment_profile (
            inn                 text PRIMARY KEY CHECK (inn ~ '^([0-9]{{10}}|[0-9]{{12}})$'),
            supplier_id         uuid,
            entity_kind         text CHECK (entity_kind IN ('LEGAL_ENTITY', 'INDIVIDUAL_ENTREPRENEUR')),
            legal_name          text,
            short_name          text,
            ogrn                text CHECK (ogrn ~ '^([0-9]{{13}}|[0-9]{{15}})$'),
            kpp                 text CHECK (kpp ~ '^[0-9]{{4}}[0-9A-Z]{{2}}[0-9]{{3}}$'),
            legal_status        text CHECK (legal_status IN ('ACTIVE', 'CEASED')),
            registration_date   date,
            registered_address  text,
            primary_okved       text,
            region              text,
            identity_source_url text,
            identity_source_type text,
            identity_checked_at timestamptz,
            official_website    text CHECK (official_website ~ '^https?://'),
            website_confidence  text NOT NULL DEFAULT 'NONE' CHECK (website_confidence IN ('HIGH', 'MEDIUM', 'LOW', 'NONE')),
            website_candidate   text,
            website_checked_at  timestamptz,
            content_currency    text CHECK (content_currency IN ('CURRENT', 'UNDATED', 'OUTDATED')),
            enrichment_status   text NOT NULL CHECK (enrichment_status IN ('NOT_ENRICHED', 'IN_PROGRESS', 'COMPLETE', 'PARTIAL', 'FAILED')),
            status_reasons      text[] NOT NULL DEFAULT '{{}}',
            retryable           boolean NOT NULL DEFAULT false,
            pipeline_version    text NOT NULL,
            duration_ms         integer,
            last_enriched_at    timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (official_website IS NULL OR website_confidence = 'HIGH'),
            CHECK (enrichment_status NOT IN ('COMPLETE', 'PARTIAL') OR legal_name IS NOT NULL)
        );

        CREATE TABLE supplier_contact (
            id               uuid PRIMARY KEY,
            inn              {INN} REFERENCES supplier_enrichment_profile (inn) ON DELETE CASCADE,
            contact_type     text NOT NULL CHECK (contact_type IN ('PHONE', 'EMAIL', 'WEBSITE', 'ADDRESS')),
            value            text NOT NULL CHECK (value <> ''),
            normalized_value text NOT NULL,
            label            text,
            source_url       text NOT NULL CHECK (source_url ~ '^https?://'),
            source_type      {SRC},
            checked_at       timestamptz NOT NULL,
            content_currency text CHECK (content_currency IN ('CURRENT', 'UNDATED', 'OUTDATED')),
            verified         boolean NOT NULL,
            UNIQUE (inn, contact_type, normalized_value)
        );

        CREATE TABLE supplier_enrichment_evidence (
            id             uuid PRIMARY KEY,
            inn            {INN} REFERENCES supplier_enrichment_profile (inn) ON DELETE CASCADE,
            evidence_type  text NOT NULL,
            claim          text NOT NULL,
            value          text,
            source_url     text NOT NULL CHECK (source_url ~ '^https?://'),
            source_type    {SRC},
            checked_at     timestamptz NOT NULL,
            valid_until    date,
            strength       text NOT NULL CHECK (strength IN ('STRONG', 'MODERATE', 'WEAK'))
        );

        CREATE TABLE supplier_role_evidence (
            id           uuid PRIMARY KEY,
            inn          {INN} REFERENCES supplier_enrichment_profile (inn) ON DELETE CASCADE,
            role         text NOT NULL CHECK (role IN ('MANUFACTURER', 'OFFICIAL_DISTRIBUTOR', 'DISTRIBUTOR', 'SUPPLIER', 'UNKNOWN')),
            status       text NOT NULL CHECK (status IN ('VERIFIED', 'INFERRED', 'UNDER_REVIEW', 'UNKNOWN')),
            basis        text NOT NULL,
            claim        text NOT NULL,
            source_url   text CHECK (source_url ~ '^https?://'),
            source_type  text NOT NULL,
            checked_at   timestamptz,
            strength     text NOT NULL CHECK (strength IN ('STRONG', 'MODERATE', 'WEAK')),
            -- automated pipeline output is never a verified role (verification stays with curated evidence, A2)
            CHECK (status <> 'VERIFIED')
        );

        -- append-only run log: one run_id per pipeline run; seq orders runs even when two share a start timestamp
        CREATE TABLE supplier_enrichment_attempt (
            id            uuid PRIMARY KEY,
            seq           bigint GENERATED ALWAYS AS IDENTITY,
            run_id        uuid NOT NULL,
            inn           {INN},
            run_started_at timestamptz NOT NULL,
            source        text NOT NULL,
            outcome       text NOT NULL CHECK (outcome IN ('OK', 'NOT_FOUND', 'UNAVAILABLE', 'REJECTED', 'SKIPPED')),
            detail        text,
            duration_ms   integer NOT NULL DEFAULT 0
        );
        CREATE INDEX ix_enrichment_attempt_inn ON supplier_enrichment_attempt (inn, seq);
        CREATE INDEX ix_enrichment_profile_status ON supplier_enrichment_profile (enrichment_status);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS supplier_enrichment_attempt, supplier_role_evidence, supplier_enrichment_evidence,
            supplier_contact, supplier_enrichment_profile;
    """)
