"""Orchestration of the accepted services for the product API (P4-001). No ranking, retrieval or concentration logic lives here:
recommendations come from app.search.recommend.recommend() (DEFAULT_CONFIG = P2_001_SEMANTIC) and market intelligence from
app.api.market_service.build_market_intelligence() (accepted P3 formulas)."""
from __future__ import annotations

import time

import psycopg
from psycopg import Connection

from app.api.market_service import InvalidCategory, UnknownCategory, build_market_intelligence
from app.api.recommendation_models import (AnalysisResponse, MarketIntelligenceEntry, ProcurementItemResponse,
                                           ProcurementResponse, RecommendationResponse, RecommendationSection, SectionError)
from app.enrichment.catalog import CuratedEvidenceCatalog, EvidenceCatalogError
from app.search import predefense_adapter as PD
from app.search.models import DEFAULT_CONFIG
from app.search.recommend import recommend, recommend_query

CONFIG_NAME = "P2_001_SEMANTIC"


class LotNotFound(LookupError):
    pass


def recommendation(conn: Connection, lot_id: str) -> RecommendationResponse:
    """recommend(conn, lot_id) with the default (accepted S3) configuration, typed for the API. Expects an idle connection.
    Pre-defense lots (organizer files) are checked first and queried from their item rows; nothing is written anywhere."""
    conn.execute("SET TRANSACTION READ ONLY")
    pd_lot = PD.get(lot_id)
    if pd_lot is not None:
        codes = {it.line_no: PD.validate_category(conn, it.product_name, it.okpd2_code_raw).okpd2_code for it in pd_lot.items}
        q, idf = PD.build_query(conn, pd_lot, codes, DEFAULT_CONFIG)
        out = recommend_query(conn, q, idf)
    else:
        if conn.execute("SELECT 1 FROM procurement_lot WHERE lot_id = %s", (lot_id,)).fetchone() is None:
            raise LotNotFound(f"lot {lot_id} not found")
        out = recommend(conn, lot_id)
    conn.rollback()                                   # ends the read transaction (SET LOCAL hnsw settings)
    branch_ms = out["retrieval"]["branch_ms"]
    return RecommendationResponse(
        lot_id=out["lot_id"], as_of=out["as_of"], recommendation_version=f"{CONFIG_NAME} (engine {out['baseline_version']})",
        config_name=CONFIG_NAME if out["config"] == DEFAULT_CONFIG.to_dict() else "CUSTOM", config=out["config"],
        semantic_enabled="semantic" in branch_ms, warnings=out["warnings"], candidate_count=out["candidates"],
        query=out["query"], retrieval=out["retrieval"], results=out["results"], timings_ms=out["timings_ms"])


def _predefense_procurement(conn: Connection, lot: PD.PredefenseLot) -> ProcurementResponse:
    items = []
    for it in lot.items:
        cat = PD.validate_category(conn, it.product_name, it.okpd2_code_raw)
        items.append(ProcurementItemResponse(line_no=it.line_no, product_name=it.product_name, okpd2_code=cat.okpd2_code,
                                             okpd2_code_raw=it.okpd2_code_raw, okpd2_status=cat.status, okpd2_evidence=cat.evidence))
    n = lot.notice
    return ProcurementResponse(lot_id=lot.lot_id, subject=n.get("subject") or n.get("procedure_name") or None,
                               publish_date=lot.publish_date, platform=lot.platform, start_price=lot.start_price,
                               customer_inn=n.get("customer_inn") or None, items_total=len(items), items=items,
                               source=PD.SOURCE)


def procurement(conn: Connection, lot_id: str) -> ProcurementResponse:
    pd_lot = PD.get(lot_id)
    if pd_lot is not None:                            # pre-defense file first; query input only, never stored
        return _predefense_procurement(conn, pd_lot)
    lot = conn.execute("""SELECT lot_id, subject, publish_date, platform, start_price, customer_inn FROM procurement_lot
                          WHERE lot_id = %s""", (lot_id,)).fetchone()
    if lot is None:
        raise LotNotFound(f"lot {lot_id} not found")
    items = conn.execute("""SELECT line_no, product_name_raw, okpd2_code, okpd2_code_raw FROM procurement_item
                            WHERE lot_id = %s ORDER BY line_no""", (lot_id,)).fetchall()
    return ProcurementResponse(
        lot_id=lot[0], subject=lot[1], publish_date=lot[2], platform=lot[3], start_price=None if lot[4] is None else float(lot[4]),
        customer_inn=lot[5], items_total=len(items),
        items=[ProcurementItemResponse(line_no=r[0], product_name=r[1], okpd2_code=r[2], okpd2_code_raw=r[3]) for r in items])


def _error(code: str, error: Exception) -> SectionError:
    return SectionError(code=code, message=str(error))


def analysis(conn: Connection, lot_id: str, catalog: CuratedEvidenceCatalog | None = None) -> AnalysisResponse:
    """One response: procurement + recommendations + market intelligence per distinct exact OKPD2 (each section fails alone)."""
    t0 = time.perf_counter()
    timings: dict[str, float] = {}
    proc = procurement(conn, lot_id)
    conn.rollback()
    t = time.perf_counter()
    try:
        rec = RecommendationSection(status="OK", data=recommendation(conn, lot_id), error=None)
    except (psycopg.Error, RuntimeError, ValueError) as e:
        conn.rollback()
        rec = RecommendationSection(status="UNAVAILABLE", data=None, error=_error("RECOMMENDATION_UNAVAILABLE", e))
    timings["recommendations_ms"] = (time.perf_counter() - t) * 1000

    lines_by_code: dict[str, list[int]] = {}
    for it in proc.items:
        if it.okpd2_code:
            lines_by_code.setdefault(it.okpd2_code, []).append(it.line_no)
    catalog = catalog or CuratedEvidenceCatalog()
    t = time.perf_counter()
    entries = []
    for code in sorted(lines_by_code):
        try:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")       # connection is idle here (rolled back), so this is the first statement
                mi = build_market_intelligence(conn, catalog, code, proc.publish_date)
            entries.append(MarketIntelligenceEntry(okpd2=code, item_lines=lines_by_code[code], status="OK", data=mi, error=None))
        except InvalidCategory as e:
            entries.append(MarketIntelligenceEntry(okpd2=code, item_lines=lines_by_code[code], status="UNAVAILABLE", data=None,
                                                   error=_error("INVALID_OKPD2", e)))
        except UnknownCategory as e:
            entries.append(MarketIntelligenceEntry(okpd2=code, item_lines=lines_by_code[code], status="UNAVAILABLE", data=None,
                                                   error=_error("CATEGORY_NOT_OBSERVED", e)))
        except EvidenceCatalogError as e:
            entries.append(MarketIntelligenceEntry(okpd2=code, item_lines=lines_by_code[code], status="UNAVAILABLE", data=None,
                                                   error=_error("EVIDENCE_CATALOG_UNAVAILABLE", e)))
        except (psycopg.Error, RuntimeError, ValueError) as e:
            entries.append(MarketIntelligenceEntry(okpd2=code, item_lines=lines_by_code[code], status="UNAVAILABLE", data=None,
                                                   error=_error("HISTORICAL_DATA_UNAVAILABLE", e)))
        finally:
            conn.rollback()
    timings["market_intelligence_ms"] = (time.perf_counter() - t) * 1000
    timings["total_ms"] = (time.perf_counter() - t0) * 1000
    complete = rec.status == "OK" and all(e.status == "OK" for e in entries)
    return AnalysisResponse(
        procurement=proc, recommendations=rec, market_intelligence=entries, market_intelligence_as_of=proc.publish_date,
        items_without_okpd2=[it.line_no for it in proc.items if not it.okpd2_code], availability="COMPLETE" if complete else "PARTIAL",
        timings_ms={k: round(v, 1) for k, v in timings.items()})
