"""Organizer real-data schema v0.2.0 (P1-001D): provenance, raw staging, canonical tables, enrichment tables, indexes.

Revision ID: 0001_organizer_schema
Revises:
Create Date: 2026-10-01
"""
from alembic import op

from app.db.schema import (HISTORY_FLAGS, ITEM_FLAGS, LOT_FLAGS, SECONDARY_INDEXES, SUPPLIER_FLAGS, flags_check)

revision = "0001_organizer_schema"
down_revision = None
branch_labels = None
depends_on = None

DDL = f"""
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------------------------------------------------------------- provenance
CREATE TABLE source_file (
    sha256        char(64) PRIMARY KEY,
    dataset       text     NOT NULL CHECK (dataset IN ('notices_24_25', 'suppliers_24_25', 'items_24_25')),
    file_name     text     NOT NULL,
    size_bytes    bigint   NOT NULL,
    header        text[]   NOT NULL,
    data_rows     integer  -- set when the file has been fully parsed
);

CREATE TABLE ingestion_delivery (
    delivery_id           uuid PRIMARY KEY,
    notices_sha256        char(64) NOT NULL REFERENCES source_file,
    suppliers_sha256      char(64) NOT NULL REFERENCES source_file,
    items_sha256          char(64) NOT NULL REFERENCES source_file,
    normalization_version text     NOT NULL,
    status                text     NOT NULL CHECK (status IN ('complete')),
    completed_at          timestamptz NOT NULL DEFAULT now(),
    counts                jsonb    NOT NULL
);

CREATE TABLE ingestion_quarantine (
    source_sha256  char(64) NOT NULL REFERENCES source_file,
    source_row_no  integer  NOT NULL,
    dataset        text     NOT NULL,
    reason         text     NOT NULL,
    PRIMARY KEY (source_sha256, source_row_no)
);

-- ---------------------------------------------------------------- raw staging (immutable, typed text = exactly as parsed)
CREATE TABLE raw_notice (
    source_sha256     char(64) NOT NULL REFERENCES source_file,
    source_row_no     integer  NOT NULL,
    publish_date      text NOT NULL, procedure_id text NOT NULL, lot_id text NOT NULL, start_price text NOT NULL,
    reqnum            text NOT NULL, procedure_name text NOT NULL, subject text NOT NULL, is_smp text NOT NULL,
    customer_inn      text NOT NULL, customer_kpp text NOT NULL, is_eshop_or_aisgz text NOT NULL,
    PRIMARY KEY (source_sha256, source_row_no)
);

CREATE TABLE raw_supplier_relation (
    source_sha256  char(64) NOT NULL REFERENCES source_file,
    source_row_no  integer  NOT NULL,
    lot_id text NOT NULL, supplier_inn text NOT NULL, supplier_kpp text NOT NULL, is_winner text NOT NULL,
    PRIMARY KEY (source_sha256, source_row_no)
);

CREATE TABLE raw_procurement_item (
    source_sha256  char(64) NOT NULL REFERENCES source_file,
    source_row_no  integer  NOT NULL,
    lot_id text NOT NULL, product_name text NOT NULL, okpd2_code text NOT NULL,
    PRIMARY KEY (source_sha256, source_row_no)
);

-- ---------------------------------------------------------------- canonical (contracts v0.2.0)
CREATE TABLE procurement_lot (
    lot_id                 text PRIMARY KEY,
    id                     uuid NOT NULL UNIQUE,
    procedure_id           text NOT NULL,
    publish_date           date NOT NULL,
    platform               text NOT NULL CHECK (platform IN ('AIS_GZ', 'EM')),
    subject                text CHECK (subject <> ''),
    procedure_name_variant text CHECK (procedure_name_variant <> ''),
    start_price            numeric CHECK (start_price >= 0),
    reqnum                 text,
    is_smp                 boolean NOT NULL,
    customer_inn           text,
    customer_kpp           text,
    has_supplier_history   boolean NOT NULL,
    data_quality_flags     text[] NOT NULL DEFAULT '{{}}' {flags_check('data_quality_flags', LOT_FLAGS)},
    source_sha256          char(64) NOT NULL,
    source_row_no          integer NOT NULL,
    CHECK ((customer_inn IS NULL) = ('MISSING_INN' = ANY (data_quality_flags))),
    CHECK ((start_price IS NULL) = ('MISSING_START_PRICE' = ANY (data_quality_flags)))
);

CREATE TABLE supplier (
    supplier_id             uuid PRIMARY KEY,
    inn                     text NOT NULL UNIQUE,
    entity_type             text NOT NULL CHECK (entity_type IN ('legal_entity', 'individual_entrepreneur', 'unknown')),
    inn_region_code         text CHECK (inn_region_code ~ '^[0-9]{{2}}$'),
    origin                  text NOT NULL CHECK (origin IN ('ORGANIZER_DATA', 'EXTERNAL_ENRICHMENT')),
    first_seen_publish_date date,
    data_quality_flags      text[] NOT NULL DEFAULT '{{}}' {flags_check('data_quality_flags', SUPPLIER_FLAGS)},
    CHECK ((origin = 'ORGANIZER_DATA') = (first_seen_publish_date IS NOT NULL)),
    CHECK ((entity_type = 'unknown') = ('INVALID_INN_FORMAT' = ANY (data_quality_flags))),
    CHECK (entity_type <> 'legal_entity' OR inn ~ '^[0-9]{{10}}$'),
    CHECK (entity_type <> 'individual_entrepreneur' OR inn ~ '^[0-9]{{12}}$')
);

CREATE TABLE supplier_history (
    id                  uuid PRIMARY KEY,
    lot_id              text NOT NULL REFERENCES procurement_lot (lot_id),
    supplier_id         uuid NOT NULL REFERENCES supplier (supplier_id),
    supplier_inn        text NOT NULL,
    supplier_kpp        text,
    is_winner           boolean NOT NULL,
    platform            text NOT NULL CHECK (platform IN ('AIS_GZ', 'EM')),
    publish_date        date NOT NULL,
    coverage_semantics  text NOT NULL,
    data_quality_flags  text[] NOT NULL DEFAULT '{{}}' {flags_check('data_quality_flags', HISTORY_FLAGS)},
    source_sha256       char(64) NOT NULL,
    source_row_nos      integer[] NOT NULL CHECK (cardinality(source_row_nos) >= 1),
    UNIQUE (lot_id, supplier_inn),
    CHECK ((platform = 'AIS_GZ' AND coverage_semantics = 'WINNER_ROWS_ONLY_OBSERVED')
        OR (platform = 'EM' AND coverage_semantics = 'MIXED_WINNER_NONWINNER_ROWS_OBSERVED')),
    CHECK ((cardinality(source_row_nos) > 1) = ('DUPLICATE_SUPPLIER_RELATION' = ANY (data_quality_flags)))
);

CREATE TABLE procurement_item (
    item_id                  uuid PRIMARY KEY,
    lot_id                   text NOT NULL REFERENCES procurement_lot (lot_id),
    line_no                  integer NOT NULL CHECK (line_no >= 1),
    content_hash             char(64) NOT NULL,
    product_name_raw         text NOT NULL,
    product_name_normalized  text CHECK (product_name_normalized <> ''),
    is_generic_type_name     boolean NOT NULL,
    okpd2_code_raw           text NOT NULL,
    okpd2_code               text,
    okpd2_depth              smallint CHECK (okpd2_depth BETWEEN 1 AND 4),
    okpd2_section            char(1),
    okpd2_class              text,
    okpd2_subclass           text,
    okpd2_group              text,
    okpd2_subgroup           text,
    okpd2_kind               text,
    data_quality_flags       text[] NOT NULL DEFAULT '{{}}' {flags_check('data_quality_flags', ITEM_FLAGS)},
    source_sha256            char(64) NOT NULL,
    source_row_no            integer NOT NULL,
    UNIQUE (lot_id, line_no),
    CHECK ((okpd2_code IS NULL) = (okpd2_class IS NULL))
);

-- ---------------------------------------------------------------- enrichment (P3; empty in P1-001D)
CREATE TABLE supplier_profile (
    supplier_id        uuid PRIMARY KEY REFERENCES supplier (supplier_id),
    display_name       text, ogrn text CHECK (ogrn ~ '^([0-9]{{13}}|[0-9]{{15}})$'),
    legal_status       text CHECK (legal_status IN ('active', 'inactive', 'unknown')),
    region text, city text, website text CHECK (website ~ '^https?://'), okved_primary text,
    market_role        text NOT NULL CHECK (market_role IN ('manufacturer', 'distributor', 'dealer', 'supplier', 'reseller', 'other_intermediary', 'unknown')),
    role_basis         text CHECK (role_basis IN ('official_registry', 'first_party_production', 'dealer_certificate', 'company_website',
                                                  'okved', 'procurement_history', 'procurement_pattern', 'declared', 'manual_review')),
    role_verification  text NOT NULL CHECK (role_verification IN ('VERIFIED', 'INFERRED', 'UNVERIFIED')),
    role_confidence    numeric NOT NULL CHECK (role_confidence BETWEEN 0 AND 1),
    role_evidence_ids  uuid[] NOT NULL DEFAULT '{{}}',
    observed_at        timestamptz NOT NULL,
    CHECK (market_role = 'unknown' OR (role_basis IS NOT NULL AND cardinality(role_evidence_ids) >= 1)),
    CHECK (market_role <> 'unknown' OR role_verification = 'UNVERIFIED'),
    CHECK (role_basis NOT IN ('okved', 'procurement_pattern', 'declared') OR (role_verification <> 'VERIFIED' AND role_confidence <= 0.4)),
    CHECK (NOT (market_role = 'manufacturer' AND role_verification = 'VERIFIED')
           OR role_basis IN ('official_registry', 'first_party_production'))
);

CREATE TABLE supplier_evidence (
    evidence_id          uuid PRIMARY KEY,
    supplier_id          uuid NOT NULL REFERENCES supplier (supplier_id),
    claim                text NOT NULL CHECK (length(claim) BETWEEN 3 AND 500),
    evidence_type        text NOT NULL CHECK (evidence_type IN ('PROCUREMENT_HISTORY', 'OFFICIAL_REGISTRY', 'LEGAL_REGISTRY',
                                                                 'FIRST_PARTY_PRODUCTION', 'COMPANY_WEBSITE', 'DEALER_CERTIFICATE', 'PRODUCT_CATALOG')),
    supports             text NOT NULL CHECK (supports IN ('MARKET_ROLE', 'PRODUCT_RELEVANCE', 'LEGAL_IDENTITY')),
    source_name          text NOT NULL,
    source_url           text CHECK (source_url ~ '^https?://'),
    source_record_ref    text,
    observed_at          timestamptz NOT NULL,
    verification_status  text NOT NULL CHECK (verification_status IN ('VERIFIED', 'UNVERIFIED')),
    confidence           numeric NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    related_okpd2_codes  text[] NOT NULL DEFAULT '{{}}',
    CHECK (source_url IS NOT NULL OR source_record_ref IS NOT NULL),
    CHECK (evidence_type <> 'PROCUREMENT_HISTORY' OR source_record_ref ~ '^lot:\\S+$')
);
CREATE INDEX ix_evidence_supplier ON supplier_evidence (supplier_id);
"""


def upgrade() -> None:
    op.execute(DDL)
    for _name, _table, ddl in SECONDARY_INDEXES:
        op.execute(ddl)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS supplier_evidence, supplier_profile, procurement_item, supplier_history, supplier,
            procurement_lot, raw_procurement_item, raw_supplier_relation, raw_notice, ingestion_quarantine,
            ingestion_delivery, source_file CASCADE;
    """)
