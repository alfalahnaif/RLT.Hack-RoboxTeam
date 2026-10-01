"""Single source of truth for organizer-schema DDL fragments shared by the Alembic migration and the ingestion CLI.

Secondary indexes are defined here once: the migration creates them; a fresh bulk load drops and rebuilds them
(faster than maintaining GIN indexes row by row) using exactly the same statements.
"""
from __future__ import annotations

from app.shared import normalize as N

LOT_FLAGS = [N.MISSING_INN, N.INVALID_INN_FORMAT, N.INVALID_INN_CHECKSUM, N.MISSING_KPP, N.INVALID_KPP_FORMAT,
             N.MISSING_START_PRICE, N.ZERO_START_PRICE, N.MISSING_SUBJECT]
ITEM_FLAGS = [N.MISSING_PRODUCT_NAME, N.MISSING_OKPD2, N.INVALID_OKPD2]
HISTORY_FLAGS = [N.INVALID_INN_FORMAT, N.INVALID_INN_CHECKSUM, N.MISSING_KPP, N.INVALID_KPP_FORMAT,
                 N.DUPLICATE_SUPPLIER_RELATION]
SUPPLIER_FLAGS = [N.INVALID_INN_FORMAT, N.INVALID_INN_CHECKSUM]


def flags_check(column: str, allowed: list[str]) -> str:
    return f"CHECK ({column} <@ ARRAY[{', '.join(repr(f) for f in allowed)}]::text[])"


# Tables that hold organizer-derived data (scope of --reset-organizer-data). Order = safe delete order.
ORGANIZER_TABLES = ["procurement_item", "supplier_history", "procurement_lot", "ingestion_quarantine",
                    "raw_procurement_item", "raw_supplier_relation", "raw_notice"]

# (name, table, DDL). FTS: 'simple' keeps exact technical tokens (a515-57-50r7, 4103dw, cf280x) unstemmed; 'russian'
# adds morphology; pg_trgm covers partial/fuzzy model numbers. All on the normalized search text (normalize.py).
SECONDARY_INDEXES = [
    ("ix_lot_publish_date", "procurement_lot", "CREATE INDEX ix_lot_publish_date ON procurement_lot (publish_date)"),
    ("ix_lot_customer_inn", "procurement_lot", "CREATE INDEX ix_lot_customer_inn ON procurement_lot (customer_inn)"),
    ("ix_lot_platform_date", "procurement_lot", "CREATE INDEX ix_lot_platform_date ON procurement_lot (platform, publish_date)"),
    ("ix_item_lot", "procurement_item", "CREATE INDEX ix_item_lot ON procurement_item (lot_id)"),
    ("ix_item_okpd2_code", "procurement_item", "CREATE INDEX ix_item_okpd2_code ON procurement_item (okpd2_code text_pattern_ops)"),
    ("ix_item_okpd2_kind", "procurement_item", "CREATE INDEX ix_item_okpd2_kind ON procurement_item (okpd2_kind)"),
    ("ix_item_okpd2_group", "procurement_item", "CREATE INDEX ix_item_okpd2_group ON procurement_item (okpd2_group)"),
    ("ix_item_okpd2_class", "procurement_item", "CREATE INDEX ix_item_okpd2_class ON procurement_item (okpd2_class)"),
    ("ix_item_name_trgm", "procurement_item",
     "CREATE INDEX ix_item_name_trgm ON procurement_item USING gin (product_name_normalized gin_trgm_ops)"),
    ("ix_item_name_fts_simple", "procurement_item",
     "CREATE INDEX ix_item_name_fts_simple ON procurement_item USING gin (to_tsvector('simple'::regconfig, coalesce(product_name_normalized, '')))"),
    ("ix_item_name_fts_russian", "procurement_item",
     "CREATE INDEX ix_item_name_fts_russian ON procurement_item USING gin (to_tsvector('russian'::regconfig, coalesce(product_name_normalized, '')))"),
    ("ix_history_lot", "supplier_history", "CREATE INDEX ix_history_lot ON supplier_history (lot_id)"),
    ("ix_history_supplier_date", "supplier_history",
     "CREATE INDEX ix_history_supplier_date ON supplier_history (supplier_id, publish_date)"),
    ("ix_history_date", "supplier_history", "CREATE INDEX ix_history_date ON supplier_history (publish_date)"),
    ("ix_history_platform_winner_date", "supplier_history",
     "CREATE INDEX ix_history_platform_winner_date ON supplier_history (platform, is_winner, publish_date)"),
    ("ix_supplier_first_seen", "supplier", "CREATE INDEX ix_supplier_first_seen ON supplier (first_seen_publish_date)"),
]

# Added by migration 0003 (P1-002 SQL review): item-level date for "newest visible lots first" OKPD2 retrieval.
SECONDARY_INDEXES_0003 = [
    ("ix_item_okpd2_code_date", "procurement_item",
     "CREATE INDEX ix_item_okpd2_code_date ON procurement_item (okpd2_code, publish_date DESC)"),
    ("ix_item_okpd2_kind_date", "procurement_item",
     "CREATE INDEX ix_item_okpd2_kind_date ON procurement_item (okpd2_kind, publish_date DESC)"),
    ("ix_item_okpd2_group_date", "procurement_item",
     "CREATE INDEX ix_item_okpd2_group_date ON procurement_item (okpd2_group, publish_date DESC)"),
    ("ix_item_okpd2_class_date", "procurement_item",
     "CREATE INDEX ix_item_okpd2_class_date ON procurement_item (okpd2_class, publish_date DESC)"),
]

# Everything a fresh bulk load drops and rebuilds (current head schema).
ALL_SECONDARY_INDEXES = SECONDARY_INDEXES + SECONDARY_INDEXES_0003
