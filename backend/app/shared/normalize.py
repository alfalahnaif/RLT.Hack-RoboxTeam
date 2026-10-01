"""Canonical normalization layer (P1-001C) — one implementation for ingestion, retrieval and ranking.

Pure, deterministic, side-effect free, stdlib only. Every function keeps the raw value next to the canonical value
and reports data-quality flags from the controlled vocabulary of contracts v0.2.0 (contracts/common.schema.json).
Rules and rationale: docs/domain/DATA_MAPPING.md (§2 columns, §4 derived fields, §4.1 OKPD2, §5 flags, §10 text).

Two failure kinds (DATA_MAPPING §1):
  * data-quality problems  -> value kept (raw preserved) + flag          (e.g. malformed INN, missing OKPD2)
  * structural problems    -> NormalizationError (row is quarantined)   (e.g. unknown platform, non-boolean literal)
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import NamedTuple, Optional

NORMALIZATION_VERSION = "1.0.0"
OKPD2_SECTIONS_VERSION = "OK034-2014-sections-1"

# ---------------------------------------------------------------------------- quality flags (contract vocabulary)
MISSING_INN = "MISSING_INN"
INVALID_INN_FORMAT = "INVALID_INN_FORMAT"
INVALID_INN_CHECKSUM = "INVALID_INN_CHECKSUM"
MISSING_KPP = "MISSING_KPP"
INVALID_KPP_FORMAT = "INVALID_KPP_FORMAT"
MISSING_START_PRICE = "MISSING_START_PRICE"
ZERO_START_PRICE = "ZERO_START_PRICE"
MISSING_SUBJECT = "MISSING_SUBJECT"
MISSING_PRODUCT_NAME = "MISSING_PRODUCT_NAME"
MISSING_OKPD2 = "MISSING_OKPD2"
INVALID_OKPD2 = "INVALID_OKPD2"
DUPLICATE_SUPPLIER_RELATION = "DUPLICATE_SUPPLIER_RELATION"

FLAG_ORDER = (MISSING_INN, INVALID_INN_FORMAT, INVALID_INN_CHECKSUM, MISSING_KPP, INVALID_KPP_FORMAT,
              MISSING_START_PRICE, ZERO_START_PRICE, MISSING_SUBJECT, MISSING_PRODUCT_NAME, MISSING_OKPD2,
              INVALID_OKPD2, DUPLICATE_SUPPLIER_RELATION)
_FLAG_RANK = {f: i for i, f in enumerate(FLAG_ORDER)}


def sort_flags(flags) -> list[str]:
    """Deduplicate and order flags deterministically (contract order)."""
    return sorted(set(flags), key=_FLAG_RANK.__getitem__)


class NormalizationError(ValueError):
    """Structural problem: the value cannot be represented canonically (quarantine the row)."""


def _strip(raw: Optional[str]) -> str:
    return "" if raw is None else raw.strip()


# ============================================================================ text
# Character-level map applied after NFC (str.translate: one pass, cheap).
_DELETE = dict.fromkeys(map(ord, "­​‌‍‎‏⁠﻿"), None)  # soft hyphen, zero-width, bidi marks
_TO_SPACE = dict.fromkeys(range(0x00, 0x20), " ")                                           # control chars (incl. \t \n)
_TO_SPACE.update(dict.fromkeys(range(0xE000, 0xF900), " "))                                 # private-use area
_CHAR_MAP = {
    **_DELETE, **_TO_SPACE,
    # typographic quotes are never inch marks -> space; straight/prime double quotes -> " (resolved by _resolve_quotes)
    **dict.fromkeys(map(ord, "«»„“”‟"), " "),
    **dict.fromkeys(map(ord, "″〃＂ʺ"), '"'),
    ord("º"): " ",  # masculine ordinal used as a degree sign (90º) — like °
    # single-quote / apostrophe variants -> '
    **dict.fromkeys(map(ord, "‘’‚‛′`´"), "'"),
    # dash / minus variants -> -
    **dict.fromkeys(map(ord, "‐‑‒–—―−﹘﹣－"), "-"),
    ord("ё"): "е", ord("Ё"): "Е",
    ord("×"): "x",
}
_SUPERSCRIPT_UNIT = re.compile(r"(?<=[мm])([²³])")            # м² дм³ -> м2 дм3 (units)
_SUPERSCRIPTS = re.compile(r"[²³¹⁰-₟]")  # remaining superscripts/subscripts = footnote marks (¹, ⁰ …)
# dimension separator between digits, symmetric only: 60x9 / 60*20 / 60 х 9 -> 60x9; never a model suffix (cf280x 6,8k)
_DIM_SEP = re.compile(r"(?<=\d)(?:[xх*]| [xх*] )(?=\d)")
_STAR = re.compile(r"\*")
_DOT_COMMA = re.compile(r"(?<!\d)[.,]|[.,](?!\d)")             # keep . , only between digits (15.6, 82,5)
_HYPHEN_SLASH_PLUS = re.compile(r"(?<!\w)[-/+]|[-/+](?!\w|[-/+])")  # keep - / + inside tokens (A515-57-50R7, б/к, X+Y)
_PERCENT = re.compile(r"(?<!\d)%")                             # keep % only after a digit
_OTHER = re.compile(r"[^\w\s.,\-/+\"%*]|_")                    # everything else (quotes ' ( ) № : ; ! ? ° ± …) -> space; * kept for _DIM_SEP
_SPACES = re.compile(r"\s+")
_TYPE_MARKER = re.compile(r"(?<!\w)тип\s?(\d{1,3})(?!\w)")
_DIGIT_TOKEN = re.compile(r"\S*\d\S*")


def _resolve_quotes(s: str) -> str:
    """Keep a straight '"' only as an inch mark: right after a digit while no quotation is open (15.6", 3/4" и 1/2").
    Opening/closing quotation marks ('"СБиС 2"') become spaces. Output contains only inch marks -> idempotent."""
    if '"' not in s:
        return s
    out, open_q = [], False
    for i, ch in enumerate(s):
        if ch != '"':
            out.append(ch)
        elif open_q:
            open_q = False
            out.append(" ")
        elif i > 0 and s[i - 1].isdigit():
            out.append('"')
        else:
            open_q = i + 1 < len(s) and not s[i + 1].isspace()
            out.append(" ")
    return "".join(out)


def normalize_text(raw: Optional[str]) -> Optional[str]:
    """Search representation of Russian procurement text; None when nothing meaningful remains.

    Keeps model numbers, dimensions, units, quantities and brands (A515-57-50R7, 16гб, 60x9, 15.6", 82,5%).
    Does not stem, transliterate, convert decimal commas, or remove "тип N" (see type_marker). Idempotent.
    """
    if not raw:
        return None
    s = unicodedata.normalize("NFC", raw).translate(_CHAR_MAP).lower()
    s = _SUPERSCRIPT_UNIT.sub(lambda m: "2" if m.group(1) == "²" else "3", s)
    s = _SUPERSCRIPTS.sub(" ", s)
    s = _OTHER.sub(" ", s)
    s = _DOT_COMMA.sub(" ", s)
    s = _resolve_quotes(s)
    s = _PERCENT.sub(" ", s)
    # repeated hyphen/slash/plus runs are cleaned until stable (rare; keeps idempotence)
    prev = None
    while prev != s:
        prev, s = s, _HYPHEN_SLASH_PLUS.sub(" ", s)
    s = _SPACES.sub(" ", s)
    s = _DIM_SEP.sub("x", s)          # last: runs on final token adjacency (idempotent)
    s = _SPACES.sub(" ", _STAR.sub(" ", s)).strip()
    return s or None


def comparison_key(raw: Optional[str]) -> str:
    """Comparison-only key used to decide ProcurementLot.procedure_name_variant (DATA_MAPPING §4 'cmp_norm').
    Kept exactly as specified in P1-001A/B (lower, ё→е, non-word→space, collapse) — not the search normalization."""
    s = (raw or "").lower().replace("ё", "е")
    return _SPACES.sub(" ", re.sub(r"[^\w]+", " ", s)).strip()


def type_marker(normalized: Optional[str]) -> Optional[str]:
    """Low-information catalog marker such as 'тип 3' found in normalized text (kept in the text; exposed for weighting)."""
    if not normalized:
        return None
    m = _TYPE_MARKER.search(normalized)
    return f"тип {m.group(1)}" if m else None


def numeric_tokens(normalized: Optional[str]) -> list[str]:
    """Tokens containing a digit (model numbers, dimensions, quantities) in order — not an attribute extractor."""
    return _DIGIT_TOKEN.findall(normalized) if normalized else []


class TextNorm(NamedTuple):
    raw: str
    normalized: Optional[str]
    type_marker: Optional[str]
    has_generic_type_marker: bool
    flags: tuple


def normalize_product_name(raw: Optional[str]) -> TextNorm:
    """ТРУ product_name -> ProcurementItem.product_name_raw / product_name_normalized / is_generic_type_name."""
    raw = raw or ""
    flags = (MISSING_PRODUCT_NAME,) if not raw.strip() else ()
    norm = normalize_text(raw) if not flags else None
    tm = type_marker(norm)
    return TextNorm(raw, norm, tm, tm is not None, flags)


class SubjectNorm(NamedTuple):
    raw: str
    subject: Optional[str]           # canonical display value (trimmed)
    normalized: Optional[str]        # search representation
    flags: tuple


def normalize_subject(raw: Optional[str]) -> SubjectNorm:
    raw = raw or ""
    subject = raw.strip() or None
    return SubjectNorm(raw, subject, normalize_text(subject), () if subject else (MISSING_SUBJECT,))


def procedure_name_variant(procedure_name: Optional[str], subject: Optional[str]) -> Optional[str]:
    """procedure_name (trimmed) only when its comparison key differs from the subject's; else None (BR-44)."""
    pn = _strip(procedure_name)
    if not pn or comparison_key(pn) == comparison_key(subject):
        return None
    return pn


# ============================================================================ INN / KPP
_INN_SHAPE = re.compile(r"[0-9]{10}|[0-9]{12}")
_KPP_SHAPE = re.compile(r"[0-9]{4}[0-9A-Z]{2}[0-9]{3}")
_W10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_W11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_W12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def inn_checksum_ok(inn: str) -> bool:
    """FNS control digits for a well-formed 10/12-digit INN."""
    d = [ord(c) - 48 for c in inn]
    if len(d) == 10:
        return sum(w * x for w, x in zip(_W10, d)) % 11 % 10 == d[9]
    if len(d) == 12:
        return (sum(w * x for w, x in zip(_W11, d)) % 11 % 10 == d[10]
                and sum(w * x for w, x in zip(_W12, d)) % 11 % 10 == d[11])
    return False


class InnNorm(NamedTuple):
    raw: Optional[str]
    inn: Optional[str]               # canonical: raw with outer whitespace trimmed; None only when empty
    entity_type: str                 # legal_entity | individual_entrepreneur | unknown
    inn_region_code: Optional[str]   # tax-registration region signal (NOT delivery capability)
    flags: tuple


def normalize_inn(raw: Optional[str]) -> InnNorm:
    """INN as a string (never int). Empty -> None + MISSING_INN (a supplier row with an empty INN is structural —
    the caller decides). Malformed non-empty values are preserved + INVALID_INN_FORMAT. Checksum failures keep the
    value and the entity type + INVALID_INN_CHECKSUM. Idempotent on the canonical value."""
    s = _strip(raw)
    if not s:
        return InnNorm(raw, None, "unknown", None, (MISSING_INN,))
    if not _INN_SHAPE.fullmatch(s):
        return InnNorm(raw, s, "unknown", None, (INVALID_INN_FORMAT,))
    et = "legal_entity" if len(s) == 10 else "individual_entrepreneur"
    return InnNorm(raw, s, et, s[:2], () if inn_checksum_ok(s) else (INVALID_INN_CHECKSUM,))


class KppNorm(NamedTuple):
    raw: Optional[str]
    kpp: Optional[str]
    flags: tuple


def normalize_kpp(raw: Optional[str]) -> KppNorm:
    """KPP: trimmed; empty -> None + MISSING_KPP; malformed kept + INVALID_KPP_FORMAT. Never identity, never synthesized."""
    s = _strip(raw)
    if not s:
        return KppNorm(raw, None, (MISSING_KPP,))
    return KppNorm(raw, s, () if _KPP_SHAPE.fullmatch(s) else (INVALID_KPP_FORMAT,))


# ============================================================================ OKPD2
_OKPD2_SHAPE = re.compile(r"[0-9]{2}(\.([0-9]|[0-9]{2}(\.([0-9]|[0-9]{2}(\.[0-9]{1,3})?))?))?")
# ОКПД2 section letters by class range (ОК 034-2014 / КПЕС 2008) — static, versioned (OKPD2_SECTIONS_VERSION)
_SECTION_RANGES = (("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39), ("F", 41, 43),
                   ("G", 45, 47), ("H", 49, 53), ("I", 55, 56), ("J", 58, 63), ("K", 64, 66), ("L", 68, 68),
                   ("M", 69, 75), ("N", 77, 82), ("O", 84, 84), ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93),
                   ("S", 94, 96), ("T", 97, 98), ("U", 99, 99))
OKPD2_SECTION_BY_CLASS = {f"{n:02d}": letter for letter, lo, hi in _SECTION_RANGES for n in range(lo, hi + 1)}


class Okpd2Norm(NamedTuple):
    okpd2_code_raw: str
    okpd2_code: Optional[str]
    okpd2_depth: Optional[int]
    okpd2_section: Optional[str]
    okpd2_class: Optional[str]       # Класс     XX
    okpd2_subclass: Optional[str]    # Подкласс  XX.X
    okpd2_group: Optional[str]       # Группа    XX.XX
    okpd2_subgroup: Optional[str]    # Подгруппа XX.XX.X
    okpd2_kind: Optional[str]        # Вид       XX.XX.XX
    flags: tuple


def normalize_okpd2(raw: Optional[str]) -> Okpd2Norm:
    """OKPD2 code + hierarchy (DATA_MAPPING §4.1). Supports every valid depth (XX … XX.XX.XX.XXX); never 'fixes'
    malformed codes (e.g. '25.71.11.1200' -> None + INVALID_OKPD2, raw kept). Field names match the item contract."""
    raw = raw or ""
    s = raw.strip()
    if not s:
        return Okpd2Norm(raw, None, None, None, None, None, None, None, None, (MISSING_OKPD2,))
    section = OKPD2_SECTION_BY_CLASS.get(s[:2])
    if section is None or not _OKPD2_SHAPE.fullmatch(s):
        return Okpd2Norm(raw, None, None, None, None, None, None, None, None, (INVALID_OKPD2,))
    seg = s.split(".")
    depth = len(seg)
    subclass = f"{seg[0]}.{seg[1][0]}" if depth >= 2 else None
    group = f"{seg[0]}.{seg[1]}" if depth >= 2 and len(seg[1]) == 2 else None
    subgroup = f"{group}.{seg[2][0]}" if depth >= 3 else None
    kind = f"{group}.{seg[2]}" if depth >= 3 and len(seg[2]) == 2 else None
    return Okpd2Norm(raw, s, depth, section, seg[0], subclass, group, subgroup, kind, ())


# ============================================================================ price / date / bool / platform
_DECIMAL_SHAPE = re.compile(r"[0-9]{1,15}(\.[0-9]{1,4})?")


class PriceNorm(NamedTuple):
    raw: Optional[str]
    value: Optional[Decimal]         # exact Decimal (source scale kept: '71985.00' -> Decimal('71985.00'))
    flags: tuple


def normalize_price(raw: Optional[str]) -> PriceNorm:
    """start_price with Decimal semantics. Empty -> None + MISSING_START_PRICE; zero -> Decimal + ZERO_START_PRICE
    (zero is NOT treated as missing here); non-decimal / negative -> NormalizationError (structural)."""
    s = _strip(raw)
    if not s:
        return PriceNorm(raw, None, (MISSING_START_PRICE,))
    if not _DECIMAL_SHAPE.fullmatch(s):
        raise NormalizationError(f"start_price is not a non-negative decimal: {s!r}")
    try:
        v = Decimal(s)
    except InvalidOperation as e:  # pragma: no cover - shape regex already guarantees validity
        raise NormalizationError(f"start_price not parseable: {s!r}") from e
    return PriceNorm(raw, v, (ZERO_START_PRICE,) if v == 0 else ())


def price_to_contract(value: Optional[Decimal]) -> Optional[str]:
    """Decimal -> contract decimal_string (plain notation, scale preserved)."""
    return None if value is None else format(value, "f")


_DATE_SHAPE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def normalize_date(raw: Optional[str]) -> dt.date:
    """Strict ISO date 'YYYY-MM-DD' (publish_date). No timezone. Malformed -> NormalizationError."""
    s = _strip(raw)
    if not _DATE_SHAPE.fullmatch(s):
        raise NormalizationError(f"date is not YYYY-MM-DD: {s!r}")
    try:
        return dt.date.fromisoformat(s)
    except ValueError as e:
        raise NormalizationError(f"invalid calendar date: {s!r}") from e


_BOOL = {"true": True, "false": False}


def parse_bool(raw: Optional[str]) -> bool:
    """Strict source boolean: exactly 'true' / 'false' (outer whitespace ignored). Never Python truthiness."""
    s = _strip(raw)
    try:
        return _BOOL[s]
    except KeyError:
        raise NormalizationError(f"not a boolean literal: {s!r}") from None


PLATFORM_BY_SOURCE = {"АИС ГЗ": "AIS_GZ", "ЭМ": "EM"}
# Observed dataset structure, not official completeness (ADR-H1 A1/A3/A4).
COVERAGE_SEMANTICS = {"AIS_GZ": "WINNER_ROWS_ONLY_OBSERVED", "EM": "MIXED_WINNER_NONWINNER_ROWS_OBSERVED"}


def normalize_platform(raw: Optional[str]) -> str:
    """is_eshop_or_aisgz -> AIS_GZ | EM. Unknown literal -> NormalizationError."""
    s = _strip(raw)
    try:
        return PLATFORM_BY_SOURCE[s]
    except KeyError:
        raise NormalizationError(f"unknown platform literal: {s!r}") from None


def coverage_semantics(platform: str) -> str:
    return COVERAGE_SEMANTICS[platform]
