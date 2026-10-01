"""Read-only composition of historical pool and curated external evidence."""
from __future__ import annotations

from datetime import date

from psycopg import Connection

from app.analytics.models import PoolScope, PoolThresholds
from app.analytics.pool_health import analyze_pool
from app.api.market_models import (CategoryResponse, ConcentrationResponse, EvidenceSummaryResponse,
                                   ExternalCandidateResponse, ExternalExpansionResponse,
                                   HistoricalAlternativeResponse, MarketIntelligenceResponse,
                                   PoolHealthResponse, ProvenanceResponse)
from app.enrichment.catalog import CuratedEvidenceCatalog, EvidenceCatalogError
from app.enrichment.models import CandidateInput, VerificationStatus
from app.enrichment.reconciliation import reconcile_candidates
from app.enrichment.verification import evaluate_seed
from app.shared.normalize import normalize_okpd2


DEFAULT_AS_OF = date(2026, 1, 1)
DEFAULT_RECENT_DAYS = 365
# Accepted P3-001 calibration. Keep these values aligned with analyze_pool_health.py.
POOL_THRESHOLDS = PoolThresholds(20, 20, moderate_top1=.25, high_top1=.50, very_high_top1=.80,
                                 moderate_hhi=.125, high_hhi=.32, very_high_hhi=.60)
STATUS_ORDER = {"VERIFIED": 0, "UNDER_REVIEW": 1, "UNVERIFIED": 2}
STRENGTH_ORDER = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "NONE": 3}


class InvalidCategory(ValueError):
    pass


class UnknownCategory(LookupError):
    pass


def expansion_signal(status: str, top1_share: float | None, winning_suppliers: int) -> ConcentrationResponse:
    if status == "INSUFFICIENT_DATA":
        return ConcentrationResponse(signal="INSUFFICIENT_DATA", reason_codes=["INSUFFICIENT_HISTORY"])
    if status == "LOW":
        return ConcentrationResponse(signal="NO_EXPANSION_SIGNAL", reason_codes=["LOW_HISTORICAL_CONCENTRATION"])
    if status == "MODERATE":
        return ConcentrationResponse(signal="REVIEW_POOL", reason_codes=["MODERATE_CONCENTRATION"])
    codes = [f"{status}_CONCENTRATION"]
    if top1_share is not None and top1_share >= POOL_THRESHOLDS.very_high_top1:
        codes.append("DOMINANT_TOP_SUPPLIER")
    if winning_suppliers <= 3:
        codes.append("LIMITED_WINNING_SUPPLIERS")
    return ConcentrationResponse(signal="EXPANSION_RECOMMENDED", reason_codes=codes)


def _candidate_response(candidate) -> ExternalCandidateResponse:
    evidence = [EvidenceSummaryResponse(
        evidence_type=item["evidence_type"].value,
        source_name=item["source_name"], source_url=item["source_url"],
        source_record_id=item["source_record_id"], source_authority=item["source_authority"].value,
        evidence_status=item["evidence_status"].value,
        verification_strength=item["verification_strength"].value,
        target_product_support=item["target_product_support"].value,
        product_scope=list(item["product_scope"]), evidence_date=item["evidence_date"],
        valid_until=item["valid_until"], retrieved_at=item["retrieved_at"],
        role_assertion=item["role_assertion"].value,
    ) for item in candidate.evidence_summary]
    return ExternalCandidateResponse(
        supplier_inn=candidate.supplier_inn, company_name=candidate.company_name,
        aliases=list(candidate.aliases), reconciliation_status=candidate.reconciliation_status.value,
        market_role=candidate.market_role.value, verification_status=candidate.verification_status.value,
        verification_strength=candidate.verification_strength.value,
        target_product_match=candidate.target_product_match.value,
        exact_okpd2_asserted_by_source=candidate.exact_okpd2_asserted_by_source,
        why_candidate=candidate.why_candidate,
        verification_reason_codes=list(candidate.verification_reason_codes),
        review_reasons=list(candidate.review_reasons), evidence_count=candidate.evidence_count,
        active_evidence_count=candidate.active_evidence_count, evidence_summary=evidence,
    )


def build_market_intelligence(conn: Connection, catalog: CuratedEvidenceCatalog, okpd2: str,
                              as_of: date = DEFAULT_AS_OF,
                              recent_days: int = DEFAULT_RECENT_DAYS) -> MarketIntelligenceResponse:
    normalized = normalize_okpd2(okpd2)
    if normalized.flags or normalized.okpd2_code is None:
        raise InvalidCategory("OKPD2 must be a valid observed-code format")
    code = normalized.okpd2_code
    if recent_days < 1:
        raise ValueError("recent_days must be positive")
    observed = conn.execute("SELECT 1 FROM procurement_item WHERE okpd2_code = %s LIMIT 1", (code,)).fetchone()
    if observed is None:
        raise UnknownCategory(f"OKPD2 {code} is not observed in the canonical dataset")

    pool = analyze_pool(conn, PoolScope("okpd2_code", code, as_of, recent_days), POOL_THRESHOLDS)
    historical_alternatives = [HistoricalAlternativeResponse(
        supplier_id=str(item["supplier_id"]), supplier_inn=item["inn"],
        historical_award_count=item["awards"], observed_relation_count=item["observed_relations"],
        is_winner_in_category=item["awards"] > 0,
    ) for item in sorted(pool.alternatives.suppliers,
                         key=lambda item: (-item["awards"], str(item["supplier_id"])))]

    seed = catalog.get(code)
    external_candidates: list[ExternalCandidateResponse] = []
    verified = ()
    if seed is not None:
        reconciled = reconcile_candidates(
            conn,
            [CandidateInput(candidate.supplier_inn, candidate.canonical_name) for candidate in seed.candidates],
            code,
            as_of,
        )
        try:
            verified = evaluate_seed(seed, reconciled)
        except ValueError as error:
            raise EvidenceCatalogError(f"Curated evidence evaluation failed: {error}") from error
        ordered = sorted(verified,
                         key=lambda item: (STATUS_ORDER[item.verification_status.value],
                                           STRENGTH_ORDER[item.verification_strength.value],
                                           item.company_name.casefold(), item.supplier_inn))
        external_candidates = [_candidate_response(candidate) for candidate in ordered]

    return MarketIntelligenceResponse(
        category=CategoryResponse(okpd2=code, as_of=as_of),
        pool_health=PoolHealthResponse(
            status=pool.concentration.label, lot_count=pool.support.lots,
            procurement_count=pool.support.procurements, known_customer_count=pool.support.customers,
            observed_supplier_count=pool.suppliers.observed, winning_supplier_count=pool.suppliers.winning,
            recent_winning_supplier_count=pool.suppliers.recent_winning, award_count=pool.support.awards,
            top1_share=pool.concentration.top1_share, top3_share=pool.concentration.top3_share,
            hhi=pool.concentration.hhi, alternative_supplier_count=pool.alternatives.total_count,
        ),
        concentration=expansion_signal(pool.concentration.label, pool.concentration.top1_share,
                                       pool.suppliers.winning),
        historical_alternatives=historical_alternatives,
        external_expansion=ExternalExpansionResponse(
            available=seed is not None, evidence_checked_at=seed.checked_at if seed else None,
            verified_count=sum(c.verification_status == VerificationStatus.VERIFIED for c in verified),
            under_review_count=sum(c.verification_status == VerificationStatus.UNDER_REVIEW for c in verified),
            candidates=external_candidates,
        ),
        provenance=ProvenanceResponse(
            historical_source="canonical procurement database",
            external_source="curated evidence seed" if seed else "none in current catalog",
            history_cutoff_rule="publish_date < as_of",
            verification_method="CURATED_EVIDENCE_POLICY" if seed else "NOT_AVAILABLE",
        ),
    )
