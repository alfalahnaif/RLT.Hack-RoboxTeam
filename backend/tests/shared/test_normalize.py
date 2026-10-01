"""Table-driven tests for app.shared.normalize (P1-001C).

All INN/KPP values are synthetic, format-preserving masks (checksum-valid where the case requires it) —
no real supplier identifiers. Product texts are real public procurement wording.
"""
import datetime as dt
from decimal import Decimal

import pytest

from app.shared import normalize as N

# ============================================================================ text
TEXT_CASES = [
    # (id, raw, expected normalized)
    ("cyrillic-lower", "Поставка Интерактивной Панели", "поставка интерактивной панели"),
    ("yo", "Ёмкость для жёсткой воды", "емкость для жесткой воды"),
    ("spaces", "  Бумага   туалетная \t\n рулон  ", "бумага туалетная рулон"),
    ("nbsp-zero-width", "Ноутбук ASUS​", "ноутбук asus"),
    ("soft-hyphen", "санитарно­химическим", "санитарнохимическим"),
    ("guillemets", "Сорт пшеницы «Полтавская №1»", "сорт пшеницы полтавская 1"),
    ("curly-quotes", "ПМ “Контур.Отель” по тарифу", "пм контур отель по тарифу"),
    ("straight-quotes", 'Программный комплекс "СБиС"', "программный комплекс сбис"),
    ("footnote-superscript", "Клей канцелярский¹ тип 2", "клей канцелярский тип 2"),
    ("unit-superscript", "площадь 22 м², объем до 100 дм³", "площадь 22 м2 объем до 100 дм3"),
    ("degree-superscript", "уголок 90⁰, 250х250", "уголок 90 250x250"),
    ("model-acer", 'Ноутбук Acer Aspire 5 A515-57-50R7 15.6"', 'ноутбук acer aspire 5 a515-57-50r7 15.6"'),
    ("model-hp", "МФУ HP LaserJet Pro 4103dw", "мфу hp laserjet pro 4103dw"),
    ("dimension-latin", "Швабра 60x9 см", "швабра 60x9 см"),
    ("dimension-cyrillic-x", "Сверло 8х117 мм", "сверло 8x117 мм"),
    ("dimension-times-spaced", "Трубка 4 × 6мм", "трубка 4x6мм"),
    ("dimension-asterisk", "каучуковый 60*20*7мм", "каучуковый 60x20x7мм"),
    ("dimension-spaced-cyrillic", "Угольник 90 х 50", "угольник 90x50"),
    ("model-suffix-not-joined", "Картридж HP CF280X (6,8K)", "картридж hp cf280x 6,8k"),
    ("model-suffix-cyrillic", "Картридж Pantum TL-5120Х 15000 стр", "картридж pantum tl-5120х 15000 стр"),
    ("dimension-fractions", "Ниппель 1/2 x 3/4", "ниппель 1/2x3/4"),
    ("dimension-chain", "Коробка 30 x 20 x 10 см", "коробка 30x20x10 см"),
    ("lone-asterisk", "Товар * со звездочкой*", "товар со звездочкой"),
    ("modifier-double-prime-inch", "Экран 15,6ʺ", 'экран 15,6"'),
    ("ordinal-as-degree", "Угол 90º", "угол 90"),
    ("greek-and-accents-kept", "β-каротин Ø20 café", "β-каротин ø20 café"),
    ("units-attached", "16ГБ DDR4, 512ГБ SSD, 8ТБ", "16гб ddr4 512гб ssd 8тб"),
    ("cpu", "AMD Ryzen 5 7430U", "amd ryzen 5 7430u"),
    ("roman-numeral", "Интерфейс SATA III", "интерфейс sata iii"),
    ("decimal-comma-kept", "масло 82,5% жирности", "масло 82,5% жирности"),
    ("pipe-inch", "Угол 90° ⌀25 мм х 3/4\" ВР", 'угол 90 25 мм х 3/4" вр'),
    ("quoted-name-ending-in-digit", 'Программа "СБиС 2" для ЭВМ', "программа сбис 2 для эвм"),
    ("two-inch-marks", 'Труба 3/4" и 1/2"', 'труба 3/4" и 1/2"'),
    ("quote-then-inch", 'Ноутбук "Acer" 15.6"', 'ноутбук acer 15.6"'),
    ("double-prime-inch", "Экран 75″", 'экран 75"'),
    ("slash-in-token", "Мясо говядина б/к 16ГБ/512ГБ", "мясо говядина б/к 16гб/512гб"),
    ("plus-in-token", "ДРОТАВЕРИН+КОФЕИН", "дротаверин+кофеин"),
    ("dash-variants", "Петербург – Москва — 6−10 мм PFI‐107", "петербург москва 6-10 мм pfi-107"),
    ("non-breaking-hyphen", "Санкт‑Петербурга", "санкт-петербурга"),
    ("repeated-punct", "Внимание!!! Срочно...  (см.) ;;", "внимание срочно см"),
    ("dots-in-words", "Контур.Экстерн и т.д.", "контур экстерн и т д"),
    ("underscore", "весы ВСП-15_2 шт", "весы всп-15 2 шт"),
    ("control-chars", "наб.\x02реки", "наб реки"),
    ("decomposed-y", "Блок системы й", "блок системы й"),
    ("only-punct", "—", None),
    ("empty", "", None),
    ("none", None, None),
]


@pytest.mark.parametrize("raw,expected", [c[1:] for c in TEXT_CASES], ids=[c[0] for c in TEXT_CASES])
def test_normalize_text(raw, expected):
    assert N.normalize_text(raw) == expected


@pytest.mark.parametrize("raw", [c[1] for c in TEXT_CASES], ids=[c[0] for c in TEXT_CASES])
def test_normalize_text_idempotent(raw):
    once = N.normalize_text(raw)
    assert N.normalize_text(once) == once


@pytest.mark.parametrize("raw,marker", [
    ("Пюре томатное тип 1", "тип 1"),
    ("Пюре томатное тип 1¹", "тип 1"),
    ("Ноутбук¹ тип 3", "тип 3"),
    ("Йогурт ТИП 12", "тип 12"),
    ("Мешок полимерный тип1", "тип 1"),
    ("Прототип 3 модели", None),
    ("Ноутбук ASUS", None),
    ("", None),
])
def test_type_marker(raw, marker):
    r = N.normalize_product_name(raw)
    assert r.type_marker == marker
    assert r.has_generic_type_marker is (marker is not None)
    if raw.strip():
        assert "тип" in (r.normalized or "") or marker is None  # marker is exposed, never deleted from the text


def test_product_name_keeps_raw_and_flags_empty():
    raw = "  Ноутбук¹ тип 3 "
    r = N.normalize_product_name(raw)
    assert r.raw == raw and r.normalized == "ноутбук тип 3" and r.flags == ()
    for empty in ("", "   ", None):
        e = N.normalize_product_name(empty)
        assert e.normalized is None and e.flags == (N.MISSING_PRODUCT_NAME,)


def test_numeric_tokens():
    assert N.numeric_tokens(N.normalize_text('Ноутбук Acer Aspire 5 A515-57-50R7 15.6" 16ГБ')) == \
        ["5", "a515-57-50r7", '15.6"', "16гб"]


@pytest.mark.parametrize("raw,subject,flags", [
    ("  Поставка мебели ", "Поставка мебели", ()),
    ("", None, (N.MISSING_SUBJECT,)),
    ("   ", None, (N.MISSING_SUBJECT,)),
])
def test_subject(raw, subject, flags):
    r = N.normalize_subject(raw)
    assert (r.raw, r.subject, r.flags) == (raw, subject, flags)


@pytest.mark.parametrize("pn,subject,variant", [
    ("Поставка мебели", "Поставка мебели", None),
    ("Поставка  мебели.", "ПОСТАВКА МЕБЕЛИ", None),          # same comparison key
    ("Поставка ёлок", "Поставка елок", None),
    ("Закупка медицинских изделий (лот 2)", "Поставка медицинских изделий", "Закупка медицинских изделий (лот 2)"),
    ("", "Поставка", None),
])
def test_procedure_name_variant(pn, subject, variant):
    assert N.procedure_name_variant(pn, subject) == variant


# ============================================================================ INN
INN_CASES = [
    # (id, raw, inn, entity_type, region, flags)
    ("valid-10", "7800000010", "7800000010", "legal_entity", "78", ()),
    ("valid-12", "780000000177", "780000000177", "individual_entrepreneur", "78", ()),
    ("outer-whitespace", "  4715000038 ", "4715000038", "legal_entity", "47", ()),
    ("checksum-10", "7800000042", "7800000042", "legal_entity", "78", (N.INVALID_INN_CHECKSUM,)),
    ("checksum-12", "780000000178", "780000000178", "individual_entrepreneur", "78", (N.INVALID_INN_CHECKSUM,)),
    ("empty", "", None, "unknown", None, (N.MISSING_INN,)),
    ("blank", "   ", None, "unknown", None, (N.MISSING_INN,)),
    ("none", None, None, "unknown", None, (N.MISSING_INN,)),
    ("len-9", "123456789", "123456789", "unknown", None, (N.INVALID_INN_FORMAT,)),
    ("len-13", "1234567890123", "1234567890123", "unknown", None, (N.INVALID_INN_FORMAT,)),
    ("len-15", "123456789012345", "123456789012345", "unknown", None, (N.INVALID_INN_FORMAT,)),
    ("letters+8", "AB12345678", "AB12345678", "unknown", None, (N.INVALID_INN_FORMAT,)),
    ("cyrillic-o", "78О0000010", "78О0000010", "unknown", None, (N.INVALID_INN_FORMAT,)),
    ("inner-space", "78000 00010", "78000 00010", "unknown", None, (N.INVALID_INN_FORMAT,)),
]


@pytest.mark.parametrize("raw,inn,et,region,flags", [c[1:] for c in INN_CASES], ids=[c[0] for c in INN_CASES])
def test_normalize_inn(raw, inn, et, region, flags):
    r = N.normalize_inn(raw)
    assert (r.raw, r.inn, r.entity_type, r.inn_region_code, r.flags) == (raw, inn, et, region, flags)
    assert r.inn is None or isinstance(r.inn, str)  # never an int


@pytest.mark.parametrize("raw", [c[1] for c in INN_CASES], ids=[c[0] for c in INN_CASES])
def test_normalize_inn_idempotent(raw):
    r = N.normalize_inn(raw)
    if r.inn is not None:
        r2 = N.normalize_inn(r.inn)
        assert r2[1:] == r[1:]


def test_inn_keeps_leading_zero():
    assert N.normalize_inn("0100000005").inn == "0100000005"


# ============================================================================ KPP
KPP_CASES = [
    ("valid", "780101001", "780101001", ()),
    ("valid-letters", "7801AB001", "7801AB001", ()),
    ("outer-whitespace", " 780101001 ", "780101001", ()),
    ("empty", "", None, (N.MISSING_KPP,)),
    ("none", None, None, (N.MISSING_KPP,)),
    ("len-8", "78020100", "78020100", (N.INVALID_KPP_FORMAT,)),
    ("lowercase-letters", "7801ab001", "7801ab001", (N.INVALID_KPP_FORMAT,)),
    ("junk", "n/a", "n/a", (N.INVALID_KPP_FORMAT,)),
]


@pytest.mark.parametrize("raw,kpp,flags", [c[1:] for c in KPP_CASES], ids=[c[0] for c in KPP_CASES])
def test_normalize_kpp(raw, kpp, flags):
    r = N.normalize_kpp(raw)
    assert (r.raw, r.kpp, r.flags) == (raw, kpp, flags)
    if r.kpp is not None:
        assert N.normalize_kpp(r.kpp)[1:] == r[1:]


# ============================================================================ OKPD2
OKPD2_CASES = [
    # (id, raw, code, depth, section, class, subclass, group, subgroup, kind, flags)
    ("full", "26.20.11.110", "26.20.11.110", 4, "C", "26", "26.2", "26.20", "26.20.1", "26.20.11", ()),
    ("full-000", "58.29.50.000", "58.29.50.000", 4, "J", "58", "58.2", "58.29", "58.29.5", "58.29.50", ()),
    ("4seg-1digit", "10.39.17.1", "10.39.17.1", 4, "C", "10", "10.3", "10.39", "10.39.1", "10.39.17", ()),
    ("kind", "21.20.23", "21.20.23", 3, "C", "21", "21.2", "21.20", "21.20.2", "21.20.23", ()),
    ("subgroup", "33.12.1", "33.12.1", 3, "C", "33", "33.1", "33.12", "33.12.1", None, ()),
    ("group", "21.20", "21.20", 2, "C", "21", "21.2", "21.20", None, None, ()),
    ("subclass", "31.0", "31.0", 2, "C", "31", "31.0", None, None, None, ()),
    ("class", "33", "33", 1, "C", "33", None, None, None, None, ()),
    ("services-section-q", "86.90.19.110", "86.90.19.110", 4, "Q", "86", "86.9", "86.90", "86.90.1", "86.90.19", ()),
    ("section-a", "01.25.19.150", "01.25.19.150", 4, "A", "01", "01.2", "01.25", "01.25.1", "01.25.19", ()),
    ("outer-whitespace", " 33.12.1 ", "33.12.1", 3, "C", "33", "33.1", "33.12", "33.12.1", None, ()),
]
OKPD2_INVALID = [
    ("empty", "", N.MISSING_OKPD2),
    ("blank", "  ", N.MISSING_OKPD2),
    ("known-malformed", "25.71.11.1200", N.INVALID_OKPD2),
    ("letter-o", "22.19.6O.119", N.INVALID_OKPD2),
    ("class-outside-sections", "04.11", N.INVALID_OKPD2),
    ("subclass-then-more", "26.2.11", N.INVALID_OKPD2),
    ("trailing-dot", "26.20.", N.INVALID_OKPD2),
    ("five-segments", "26.20.11.110.1", N.INVALID_OKPD2),
]


@pytest.mark.parametrize("raw,code,depth,section,cls,subclass,group,subgroup,kind,flags",
                         [c[1:] for c in OKPD2_CASES], ids=[c[0] for c in OKPD2_CASES])
def test_normalize_okpd2_valid(raw, code, depth, section, cls, subclass, group, subgroup, kind, flags):
    r = N.normalize_okpd2(raw)
    assert r == (raw, code, depth, section, cls, subclass, group, subgroup, kind, flags)
    assert N.normalize_okpd2(r.okpd2_code)[1:] == r[1:]  # idempotent on the canonical code


@pytest.mark.parametrize("raw,flag", [c[1:] for c in OKPD2_INVALID], ids=[c[0] for c in OKPD2_INVALID])
def test_normalize_okpd2_invalid_preserves_raw(raw, flag):
    r = N.normalize_okpd2(raw)
    assert r.okpd2_code_raw == raw and r.flags == (flag,)
    assert r[1:9] == (None,) * 8


def test_okpd2_field_names_match_item_contract():
    import json
    from pathlib import Path
    schema = json.loads((Path(__file__).resolve().parents[3] / "contracts" / "procurement_item.schema.json").read_text(encoding="utf-8"))
    for f in N.Okpd2Norm._fields:
        if f != "flags":
            assert f in schema["properties"], f


def test_okpd2_sections_cover_expected_classes():
    m = N.OKPD2_SECTION_BY_CLASS
    assert (m["01"], m["10"], m["33"], m["35"], m["58"], m["85"], m["99"]) == ("A", "C", "C", "D", "J", "P", "U")
    assert all(k not in m for k in ("00", "04", "34", "40", "44", "48", "54", "57", "67", "76", "83", "89"))


# ============================================================================ price
PRICE_CASES = [
    ("ordinary", "71985.00", Decimal("71985.00"), ()),
    ("no-decimals", "530000", Decimal("530000"), ()),
    ("cents", "2835.54", Decimal("2835.54"), ()),
    ("large", "19941130.78", Decimal("19941130.78"), ()),
    ("very-large", "123456789012345.6789", Decimal("123456789012345.6789"), ()),
    ("zero", "0.00", Decimal("0.00"), (N.ZERO_START_PRICE,)),
    ("zero-int", "0", Decimal("0"), (N.ZERO_START_PRICE,)),
    ("missing", "", None, (N.MISSING_START_PRICE,)),
    ("missing-none", None, None, (N.MISSING_START_PRICE,)),
    ("whitespace", " 250000.50 ", Decimal("250000.50"), ()),
]


@pytest.mark.parametrize("raw,value,flags", [c[1:] for c in PRICE_CASES], ids=[c[0] for c in PRICE_CASES])
def test_normalize_price(raw, value, flags):
    r = N.normalize_price(raw)
    assert (r.raw, r.value, r.flags) == (raw, value, flags)
    assert r.value is None or isinstance(r.value, Decimal)


def test_price_exact_decimal_and_contract_string():
    r = N.normalize_price("0.10")
    assert r.value + Decimal("0.20") == Decimal("0.30")  # exact (float would fail)
    assert N.price_to_contract(N.normalize_price("71985.00").value) == "71985.00"
    assert N.price_to_contract(N.normalize_price("0").value) == "0"
    assert N.price_to_contract(None) is None
    assert N.normalize_price("0.00").value is not None  # zero is not missing


@pytest.mark.parametrize("raw", ["-1.00", "1 000,00", "1e5", "12,50", "abc", "1.23456"])
def test_normalize_price_structural(raw):
    with pytest.raises(N.NormalizationError):
        N.normalize_price(raw)


# ============================================================================ date / bool / platform
@pytest.mark.parametrize("raw,expected", [("2025-06-16", dt.date(2025, 6, 16)), (" 2024-01-08 ", dt.date(2024, 1, 8)),
                                          ("2024-02-29", dt.date(2024, 2, 29))])
def test_normalize_date(raw, expected):
    d = N.normalize_date(raw)
    assert d == expected and type(d) is dt.date  # no time, no timezone


@pytest.mark.parametrize("raw", ["", None, "2025-13-01", "2025-02-30", "16.06.2025", "2025-6-16", "2025-06-16T00:00:00", "20250616"])
def test_normalize_date_invalid(raw):
    with pytest.raises(N.NormalizationError):
        N.normalize_date(raw)


@pytest.mark.parametrize("raw,expected", [("true", True), ("false", False), (" false ", False)])
def test_parse_bool(raw, expected):
    assert N.parse_bool(raw) is expected


@pytest.mark.parametrize("raw", ["", None, "False", "TRUE", "1", "0", "yes", "f", "истина"])
def test_parse_bool_strict(raw):
    with pytest.raises(N.NormalizationError):
        N.parse_bool(raw)


@pytest.mark.parametrize("raw,platform,coverage", [
    ("АИС ГЗ", "AIS_GZ", "WINNER_ROWS_ONLY_OBSERVED"),
    ("ЭМ", "EM", "MIXED_WINNER_NONWINNER_ROWS_OBSERVED"),
    (" ЭМ ", "EM", "MIXED_WINNER_NONWINNER_ROWS_OBSERVED"),
])
def test_platform_and_coverage(raw, platform, coverage):
    p = N.normalize_platform(raw)
    assert p == platform and N.coverage_semantics(p) == coverage


@pytest.mark.parametrize("raw", ["", None, "AIS_GZ", "аис гз", "EM", "ЕИС"])
def test_platform_unknown(raw):
    with pytest.raises(N.NormalizationError):
        N.normalize_platform(raw)


# ============================================================================ flags vocabulary
def test_flag_vocabulary_matches_contract():
    import json
    from pathlib import Path
    common = json.loads((Path(__file__).resolve().parents[3] / "contracts" / "common.schema.json").read_text(encoding="utf-8"))
    assert list(N.FLAG_ORDER) == common["$defs"]["quality_flag"]["enum"]


def test_sort_flags():
    assert N.sort_flags([N.MISSING_KPP, N.INVALID_INN_FORMAT, N.MISSING_KPP]) == [N.INVALID_INN_FORMAT, N.MISSING_KPP]
