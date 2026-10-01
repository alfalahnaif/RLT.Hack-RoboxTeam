"""Organizer CSV row -> canonical row tuples (contracts v0.2.0). All value semantics come from app.shared.normalize;
this module only arranges values into table columns and applies the dedup rule of DATA_MAPPING §3.3."""
from __future__ import annotations

from app.shared import ids
from app.shared import normalize as N

NOTICE_COLUMNS = ["publish_date", "procedure_id", "lot_id", "start_price", "reqnum", "procedure_name", "subject",
                  "is_smp", "customer_inn", "customer_kpp", "is_eshop_or_aisgz"]
SUPPLIER_COLUMNS = ["lot_id", "supplier_inn", "supplier_kpp", "is_winner"]
ITEM_COLUMNS = ["lot_id", "product_name", "okpd2_code"]
SOURCE_COLUMNS = {"notices_24_25": NOTICE_COLUMNS, "suppliers_24_25": SUPPLIER_COLUMNS, "items_24_25": ITEM_COLUMNS}

LOT_COLS = ["lot_id", "id", "procedure_id", "publish_date", "platform", "subject", "procedure_name_variant", "start_price",
            "reqnum", "is_smp", "customer_inn", "customer_kpp", "has_supplier_history", "data_quality_flags",
            "source_sha256", "source_row_no"]
SUPPLIER_COLS = ["supplier_id", "inn", "entity_type", "inn_region_code", "origin", "first_seen_publish_date", "data_quality_flags"]
HISTORY_COLS = ["id", "lot_id", "supplier_id", "supplier_inn", "supplier_kpp", "is_winner", "platform", "publish_date",
                "coverage_semantics", "data_quality_flags", "source_sha256", "source_row_nos"]
ITEM_COLS = ["item_id", "lot_id", "line_no", "content_hash", "product_name_raw", "product_name_normalized",
             "is_generic_type_name", "okpd2_code_raw", "okpd2_code", "okpd2_depth", "okpd2_section", "okpd2_class",
             "okpd2_subclass", "okpd2_group", "okpd2_subgroup", "okpd2_kind", "data_quality_flags", "source_sha256",
             "source_row_no", "publish_date"]


def map_notice(row: list[str], row_no: int, sha: str, lots_with_history) -> tuple:
    """Извещения row (list in NOTICE_COLUMNS order) -> procurement_lot tuple. Raises NormalizationError if structural."""
    (publish_date, procedure_id, lot_id, start_price, reqnum, procedure_name, subject, is_smp,
     customer_inn, customer_kpp, platform_raw) = row
    lot_id = lot_id.strip()
    procedure_id = procedure_id.strip()
    if not lot_id or not procedure_id:
        raise N.NormalizationError("empty lot_id/procedure_id")
    platform = N.normalize_platform(platform_raw)
    date = N.normalize_date(publish_date)
    smp = N.parse_bool(is_smp)
    subj = N.normalize_subject(subject)
    price = N.normalize_price(start_price)
    inn = N.normalize_inn(customer_inn)
    kpp = N.normalize_kpp(customer_kpp)
    flags = N.sort_flags(subj.flags + price.flags + inn.flags + kpp.flags)
    return (lot_id, ids.lot_uuid(lot_id), procedure_id, date, platform, subj.subject,
            N.procedure_name_variant(procedure_name, subj.subject), price.value, reqnum.strip() or None, smp,
            inn.inn, kpp.kpp, lot_id in lots_with_history, flags, sha, row_no)


def parse_supplier_row(row: list[str]) -> tuple[str, str, str, bool]:
    """Поставщики row -> (lot_id, inn, kpp_raw, is_winner). Empty INN / non-boolean is structural."""
    lot_id, inn_raw, kpp_raw, is_winner = row
    lot_id = lot_id.strip()
    inn = N.normalize_inn(inn_raw)
    if inn.inn is None:
        raise N.NormalizationError("empty supplier INN")
    if not lot_id:
        raise N.NormalizationError("empty lot_id")
    return lot_id, inn.inn, kpp_raw, N.parse_bool(is_winner)


def history_row(lot_id: str, inn: str, rows: list[tuple[int, str, bool]], platform: str, publish_date, sha: str) -> tuple:
    """Deduplicated relation (DATA_MAPPING §3.3): is_winner = OR; KPP = first non-empty in file order; all row numbers kept."""
    kpp_raw = next((k for _, k, _ in rows if k.strip()), "")
    kpp = N.normalize_kpp(kpp_raw)
    inn_n = N.normalize_inn(inn)
    flags = list(inn_n.flags) + list(kpp.flags)
    if len(rows) > 1:
        flags.append(N.DUPLICATE_SUPPLIER_RELATION)
    return (ids.history_uuid(lot_id, inn), lot_id, ids.supplier_uuid(inn), inn, kpp.kpp, any(w for _, _, w in rows),
            platform, publish_date, N.coverage_semantics(platform), N.sort_flags(flags), sha, [n for n, _, _ in rows])


def supplier_row(inn: str, first_seen) -> tuple:
    n = N.normalize_inn(inn)
    return (ids.supplier_uuid(inn), n.inn, n.entity_type, n.inn_region_code, "ORGANIZER_DATA", first_seen,
            N.sort_flags(n.flags))


def item_row(lot_id: str, line_no: int, product_name_raw: str, okpd2_raw: str, sha: str, row_no: int, publish_date) -> tuple:
    """ТРУ row -> procurement_item tuple; line_no is the caller's per-lot ordinal in immutable file order."""
    name = N.normalize_product_name(product_name_raw)
    o = N.normalize_okpd2(okpd2_raw)
    return (ids.item_uuid(lot_id, line_no), lot_id, line_no, ids.item_content_hash(lot_id, product_name_raw, okpd2_raw),
            product_name_raw, name.normalized, name.has_generic_type_marker, okpd2_raw, o.okpd2_code, o.okpd2_depth,
            o.okpd2_section, o.okpd2_class, o.okpd2_subclass, o.okpd2_group, o.okpd2_subgroup, o.okpd2_kind,
            N.sort_flags(name.flags + o.flags), sha, row_no, publish_date)
