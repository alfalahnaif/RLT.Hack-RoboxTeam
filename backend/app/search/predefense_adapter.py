"""Read-only adapter for the organizer pre-defense CSV files (backend/data/predefense/, 2026 lots).

These files are QUERY INPUT ONLY: a pre-defense lot is looked up here before the historical DB, and its notice + item rows
become the query. Nothing from them is ever written to the historical tables, the ranking history or the evidence base.

Supplied item OKPD2 codes are not trusted blindly: each distinct (product_name, code) is checked against the official
OKPD2 taxonomy + historical phrases (resolver V4 index); missing or clearly mismatched codes go to resolver V4 and, when
ambiguous, the optional LLM verifier (closed-world: it can only pick one of the resolver's official candidates).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from app.search.category_resolver import load_index, resolve
from app.search.llm_verifier import verify_resolution
from app.search.models import QueryItem, QueryLot, SearchConfig
from app.search.retrieval import LEX, okpd2_dict, tech_tokens
from app.search.stats import Idf
from app.shared import normalize as N
from app.shared.config import repo_root

SOURCE = "PREDEFENSE_FILE"
NOTICE_FIELDS = ["publish_date", "procedure_id", "lot_id", "start_price", "reqnum", "procedure_name", "subject", "is_smp",
                 "customer_inn", "customer_kpp", "is_eshop_or_aisgz"]
# Предзащита_Извещения_1.csv stores "reqnum;procedure_name" as ONE quoted header field while its rows carry both columns.
_MALFORMED_HEADER = "reqnum;procedure_name"


@dataclass
class PredefenseItem:
    line_no: int
    product_name: str
    okpd2_code_raw: str


@dataclass
class PredefenseLot:
    lot_id: str
    notice: dict | None
    items: list[PredefenseItem] = field(default_factory=list)

    @property
    def platform(self) -> str:
        return "AIS_GZ" if (self.notice or {}).get("is_eshop_or_aisgz", "").upper() == "АИС ГЗ" else "EM"

    @property
    def publish_date(self) -> date:
        return date.fromisoformat(self.notice["publish_date"])

    @property
    def start_price(self) -> float | None:
        raw = (self.notice or {}).get("start_price", "")
        return float(raw.replace(",", ".")) if raw else None


@dataclass
class PredefenseIndex:
    lots: dict[str, PredefenseLot]
    files_loaded: int
    warnings: list[str]


def _rows(path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.reader(f, delimiter=";") if r]


def _read_notices(path, lots: dict[str, PredefenseLot], warnings: list[str]) -> None:
    rows = _rows(path)
    header = [h.strip() for h in rows[0]]
    if _MALFORMED_HEADER in header:
        header = NOTICE_FIELDS          # explicit 11-field mapping; the organizer's file is not modified
    for n, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            warnings.append(f"{path.name}:{n}: {len(row)} fields, expected {len(header)}; row skipped")
            continue
        rec = {k: v.strip() for k, v in zip(header, row)}
        lots.setdefault(rec["lot_id"], PredefenseLot(rec["lot_id"], None)).notice = rec


def _read_items(path, lots: dict[str, PredefenseLot], warnings: list[str]) -> None:
    rows = _rows(path)
    header = [h.strip() for h in rows[0]]
    for n, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            warnings.append(f"{path.name}:{n}: {len(row)} fields, expected {len(header)}; row skipped")
            continue
        rec = dict(zip(header, row))
        lot = lots.setdefault(rec["lot_id"].strip(), PredefenseLot(rec["lot_id"].strip(), None))
        lot.items.append(PredefenseItem(len(lot.items) + 1, rec["product_name"].strip(), rec["okpd2_code"].strip()))


@lru_cache(maxsize=1)
def load() -> PredefenseIndex:
    """Lazily loads and indexes all pre-defense files once (in memory, by lot_id)."""
    d = repo_root() / "backend" / "data" / "predefense"
    lots: dict[str, PredefenseLot] = {}
    warnings: list[str] = []
    notices = sorted(d.glob("Предзащита_Извещения_*.csv")) if d.exists() else []
    items = sorted(d.glob("Предзащита_Потоварка_*.csv")) if d.exists() else []
    for p in notices:
        _read_notices(p, lots, warnings)
    for p in items:
        _read_items(p, lots, warnings)
    return PredefenseIndex(lots, len(notices) + len(items), warnings)


def get(lot_id: str) -> PredefenseLot | None:
    lot = load().lots.get(str(lot_id).strip())
    return lot if lot is not None and lot.notice is not None else None


# ----------------------------------------------------------------------------------------------- OKPD2 validation

@dataclass(frozen=True)
class ItemCategory:
    okpd2_code: str | None          # code used for the query / market intelligence (None = no trustworthy code)
    status: str                     # SUPPLIED_ALIGNED | RESOLVED_FROM_TEXT | SUPPLIED_UNVERIFIED | UNRESOLVED
    evidence: str


def _lexemes(conn, name: str) -> list[str]:
    return list(conn.execute(f"SELECT {LEX.format(col='%s::text')}", (name,)).fetchone()[0])


_categories: dict[tuple[str, str], ItemCategory] = {}


def validate_category(conn, product_name: str, raw_code: str) -> ItemCategory:
    """Supplied code + product text -> category (cached; the files are fixed). Aligned supplied codes are used directly."""
    key = (product_name, raw_code)
    if key not in _categories:
        _categories[key] = _validate(conn, product_name, raw_code)
    return _categories[key]


def _validate(conn, product_name: str, raw_code: str) -> ItemCategory:
    index = load_index()
    o = N.normalize_okpd2(raw_code) if raw_code else None
    supplied = o.okpd2_code if o is not None and not o.flags else None
    official = index.codes.get(supplied) if supplied else None
    name = N.normalize_product_name(product_name).normalized or product_name.lower()
    lex = [t for t in _lexemes(conn, name) if any(ch.isalpha() for ch in t)]
    res = resolve(index, product_name, lex, [])
    if official is not None and official.name:
        shared = sorted(set(lex) & set(index.phrase_items.get(supplied, {})))
        near = [s.okpd2 for s in res.suggestions if s.okpd2[:5] == supplied[:5] or index.related(s.okpd2, supplied)]
        if shared or near:
            why = f"historical items share: {', '.join(shared[:4])}" if shared else f"resolver agrees ({near[0]})"
            return ItemCategory(supplied, "SUPPLIED_ALIGNED", f"official: {official.name}; {why}")
        if res.state == "RESOLVED" and res.ranking_code[:2] != supplied[:2]:
            return ItemCategory(res.ranking_code, "RESOLVED_FROM_TEXT",
                                f"supplied {supplied} ({official.name}) contradicts the product text; resolver V4: "
                                f"{res.suggestions[0].official_name or res.ranking_code}")
        return ItemCategory(supplied, "SUPPLIED_UNVERIFIED", f"official: {official.name}; text neither confirms nor contradicts")
    # missing, malformed or not an official code -> resolver V4 (+ closed-world LLM verifier when ambiguous)
    why = f"supplied '{raw_code}' is not an official OKPD2 code" if raw_code else "no supplied code"
    if res.state != "RESOLVED":
        res = verify_resolution(product_name, res, index=index).resolution
    if res.state == "RESOLVED" and res.ranking_code:
        return ItemCategory(res.ranking_code, "RESOLVED_FROM_TEXT",
                            f"{why}; resolver V4: {res.suggestions[0].official_name or res.ranking_code}")
    return ItemCategory(None, "UNRESOLVED", f"{why}; product text is ambiguous (candidates: "
                                            f"{', '.join(s.okpd2 for s in res.suggestions[:3]) or 'none'})")


# ----------------------------------------------------------------------------------------------- query construction

def build_query(conn, lot: PredefenseLot, codes: dict[int, str | None], cfg: SearchConfig) -> tuple[QueryLot, Idf]:
    """Same shape as retrieval.build_query, but from the file's item rows (one query item per distinct product/category).
    History cutoff = the notice's publish_date; the lot's own suppliers are unknown (2026 notice), never looked up."""
    subject = lot.notice.get("subject") or None
    subj_lex = _lexemes(conn, subject or "")
    distinct, seen = [], set()
    for it in lot.items:
        name = N.normalize_product_name(it.product_name).normalized or it.product_name.lower()
        code = codes.get(it.line_no)
        if (name, code) in seen:
            continue
        seen.add((name, code))
        o = N.normalize_okpd2(code) if code else None
        od = okpd2_dict(o.okpd2_code, o.okpd2_class, o.okpd2_subclass, o.okpd2_group, o.okpd2_subgroup, o.okpd2_kind) if o else None
        distinct.append((QueryItem(name, od, _lexemes(conn, name), tech_tokens(name, cfg.min_tech_token_len)), it.line_no))
    idf = Idf(conn, [lx for qi, _ in distinct for lx in qi.lexemes] + list(subj_lex))

    def info(qi: QueryItem) -> float:
        return sum(idf.weight(lx) for lx in set(qi.lexemes)) + idf.max_weight * len(qi.tech_tokens) + (1.0 if qi.okpd2 else 0.0)

    keep = sorted(distinct, key=lambda x: (-info(x[0]), x[1]))[:cfg.max_query_items]
    keep.sort(key=lambda x: x[1])
    q = QueryLot(as_of=lot.publish_date, subject=subject, items=[qi for qi, _ in keep],
                 customer_inn=lot.notice.get("customer_inn") or None, lot_id=lot.lot_id,
                 total_items=len(lot.items), subject_lexemes=list(subj_lex))
    return q, idf
