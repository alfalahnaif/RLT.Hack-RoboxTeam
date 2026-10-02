"""P4-005A free-text supplier discovery service. Orchestration only:
  ranking      = accepted engine (text_query.build_text_query -> recommend.prepare_query -> scoring.rank_suppliers, DEFAULT_CONFIG)
  pool health  = accepted P3 build_market_intelligence (unchanged formulas)
  external     = accepted P3 curated evidence (reconciliation + verification), enriched with source-backed contact/freshness only
Nothing is invented: no supplier names, phones, e-mails or addresses exist in procurement data or in the curated seed, so they
are null unless a source provides them. No price claims (the dataset has no supplier-level prices).
"""
from __future__ import annotations

import base64
import csv
import io
import json
import time
from datetime import date

import psycopg
from psycopg import Connection

from app.api.market_service import (InvalidCategory, UnknownCategory, _external_expansion, build_external_expansion,
                                    build_market_intelligence)
from app.api.market_models import ExternalCandidateResponse, ExternalExpansionResponse
from app.api.recommendation_models import SectionError
from app.api.supplier_search_models import (CategoryCandidate, Classification, CodeHistoryResponse, Contact,
                                            ContactSource, ExternalCandidateResult,
                                            ExternalExpansionEntry, Freshness, HistoricalEvidence, Integration,
                                            PoolHealthEntry, PriceIntelligence, QueryEcho, SuggestedOkpd2,
                                            SupplierResult, SupplierSearchRequest, SupplierSearchResponse)
from app.enrichment import contacts as CE
from app.enrichment.catalog import CuratedEvidenceCatalog, EvidenceCatalogError
from app.search import text_query as TQ
from app.search.category_resolver import CategorySuggestion, load_index, resolve
from app.search.llm_verifier import verify_resolution
from app.search.candidates import build_pool, score_lots
from app.search.models import DEFAULT_CONFIG
from app.search.recommend import prepare_query
from app.search.retrieval import retrieve
from app.search.scoring import rank_suppliers

FRESH_DAYS = 180   # curated evidence checked within this many days is FRESH, older is STALE
PRICE = PriceIntelligence(available=False, reason="Comparable supplier-level pricing is not available in the current dataset.")
EVIDENCE_RANK = {"ACTIVE": 0, "SUSPENDED": 1, "UNKNOWN": 2, "TERMINATED": 3}
STRENGTH_RANK = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "NONE": 3}
SUPPORT_RANK = {"DIRECT": 0, "RELATED": 1, "NONE": 2}


class InvalidSearchId(ValueError):
    pass


# ------------------------------------------------------------------------------------------------ stateless search id
def encode_search_id(req: SupplierSearchRequest) -> str:
    raw = json.dumps(req.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_search_id(search_id: str) -> SupplierSearchRequest:
    try:
        raw = base64.urlsafe_b64decode(search_id + "=" * (-len(search_id) % 4))
        return SupplierSearchRequest.model_validate_json(raw)
    except Exception as e:  # malformed base64 / JSON / contract
        raise InvalidSearchId("invalid search_id") from e


# ------------------------------------------------------------------------------------------------ contact / freshness
def contact_of(c: ExternalCandidateResponse | None, record: CE.ContactRecord | None, today: date) -> Contact | None:
    """Source-backed contact. P4-005C enrichment record when present; otherwise only a first-party website from the
    verification evidence. Absent fields stay null. Verification evidence and status are never modified here."""
    if record is not None:
        src = {k: ContactSource(value=f.value, source_url=f.source_url, source_authority=f.source_authority,
                                checked_at=f.checked_at, address_type=f.address_type)
               for k, f in record.fields.items() if f is not None}
        last, url, status = record.freshness(today)
        return Contact(phone=src["phone"].value if "phone" in src else None, email=src["email"].value if "email" in src else None,
                       website=src["website"].value if "website" in src else None,
                       address=src["address"].value if "address" in src else None, sources=src,
                       identity_basis=record.identity_basis, freshness=Freshness(last_checked_at=last, source_url=url, status=status))
    if c is None:
        return None
    ev = next((e for e in c.evidence_summary if e.evidence_type == "FIRST_PARTY_WEBSITE" and e.source_url), None)
    src = {"website": ContactSource(value=ev.source_url, source_url=ev.source_url, source_authority="FIRST_PARTY",
                                    checked_at=ev.retrieved_at)} if ev else {}
    return Contact(phone=None, email=None, website=ev.source_url if ev else None, address=None, sources=src)


def freshness_of(c: ExternalCandidateResponse, today: date) -> Freshness:
    if not c.evidence_summary:
        return Freshness(last_checked_at=None, source_url=None, status="UNKNOWN")
    last = max(e.retrieved_at for e in c.evidence_summary)
    best = min(c.evidence_summary, key=lambda e: (EVIDENCE_RANK.get(e.evidence_status, 9), STRENGTH_RANK.get(e.verification_strength, 9),
                                                   SUPPORT_RANK.get(e.target_product_support, 9), e.source_url or ""))
    return Freshness(last_checked_at=last, source_url=best.source_url,
                     status="FRESH" if (today - last.date()).days <= FRESH_DAYS else "STALE")


def _external_entry(x: ExternalExpansionResponse, code: str, source: str, today: date,
                    records: dict[str, CE.ContactRecord]) -> ExternalExpansionEntry:
    return ExternalExpansionEntry(
        okpd2=code, source=source, available=x.available, evidence_checked_at=x.evidence_checked_at,
        verified_count=x.verified_count, under_review_count=x.under_review_count,
        candidates=[ExternalCandidateResult(**c.model_dump(), contact=contact_of(c, records.get(c.supplier_inn), today),
                                            freshness=freshness_of(c, today))
                    for c in x.candidates])


def _seed_profiles(conn: Connection, catalog: CuratedEvidenceCatalog, as_of: date) -> dict[str, ExternalCandidateResponse]:
    """INN -> evaluated curated candidate, over every seed in the catalog (used to enrich historical suppliers)."""
    out: dict[str, ExternalCandidateResponse] = {}
    for code in sorted(catalog.all()):
        for c in _external_expansion(conn, catalog, code, as_of)[0].candidates:
            out.setdefault(c.supplier_inn, c)
    return out


# ------------------------------------------------------------------------------------------------ main search
def supplier_search(conn: Connection, req: SupplierSearchRequest, catalog: CuratedEvidenceCatalog | None = None,
                    today: date | None = None) -> SupplierSearchResponse:
    t0 = time.perf_counter()
    cfg = DEFAULT_CONFIG
    catalog = catalog or CuratedEvidenceCatalog()
    today = today or date.today()
    conn.execute("SET TRANSACTION READ ONLY")
    o = TQ.normalize_code(req.okpd2)
    provided = o.okpd2_code if o else None
    as_of = TQ.data_as_of(conn)
    warnings: list[str] = []

    hist_provided = TQ.code_history(conn, provided, as_of) if provided else None
    # 1) text-only pass (text / technical / semantic): ranking for text-only searches and the OKPD2 suggestions + alignment
    q, idf = TQ.build_text_query(conn, req.query, None, cfg, as_of)
    ret, pool, timings = prepare_query(conn, q, idf, cfg)
    historical_suggestions, support = TQ.suggest_codes(q, ret, idf, cfg)
    category_index = load_index()
    resolution = resolve(category_index, req.query, q.items[0].lexemes,
                         [(s.okpd2, s.share) for s in historical_suggestions])
    verification = verify_resolution(req.query, resolution, index=category_index)
    resolution = verification.resolution
    timings["llm_verification_ms"] = verification.latency_ms
    if verification.fallback_used:
        warnings.append(f"LLM_VERIFIER_FALLBACK: {verification.status}; deterministic classification retained")
    elif verification.status == "RESOLVED":
        warnings.append(f"LLM_VERIFIED_CATEGORY: {verification.reason}")
    elif verification.status in {"AMBIGUOUS", "ABSTAIN"}:
        warnings.append(f"LLM_VERIFIER_{verification.status}: {verification.reason}")
    historical_by_code = {s.okpd2: s for s in historical_suggestions}
    if resolution.state != "CATEGORY_UNCERTAIN":
        ordered = resolution.suggestions
    else:
        # Preserve useful baseline suggestions for exploratory searches (notably
        # technical model strings) while labeling their category as uncertain.
        ordered = [next((s for s in resolution.suggestions if s.okpd2 == h.okpd2),
                        CategorySuggestion(h.okpd2, min(0.49, round(h.share, 3)), "UNCERTAIN",
                                           ["Historical text/semantic retrieval; category not confirmed"]))
                   for h in historical_suggestions]
        ordered += [s for s in resolution.suggestions if s.okpd2 not in historical_by_code]
    suggestions = [SuggestedOkpd2(
        okpd2=s.okpd2, share=historical_by_code[s.okpd2].share if s.okpd2 in historical_by_code else 0.0,
        supporting_items=historical_by_code[s.okpd2].supporting_items if s.okpd2 in historical_by_code else 0,
        supporting_lots=historical_by_code[s.okpd2].supporting_lots if s.okpd2 in historical_by_code else 0,
        example_products=historical_by_code[s.okpd2].example_products if s.okpd2 in historical_by_code else [],
        confidence=s.confidence, basis=s.basis, evidence=s.evidence) for s in ordered[:3]]
    align = TQ.alignment(provided, historical_suggestions, support)
    if provided and resolution.ranking_code:
        relation = TQ._relation(provided, resolution.ranking_code)
        align = "ALIGNED" if relation >= 2 else "UNCERTAIN" if relation == 1 else "MISMATCH"
    elif provided and resolution.state == "CATEGORY_AMBIGUOUS" and provided in {s.okpd2 for s in resolution.suggestions}:
        align = "ALIGNED"                              # the user confirmed one of the ambiguous candidates
    category_confirmed = resolution.state == "RESOLVED" or (provided is not None and align == "ALIGNED")
    # 2) the supplied code joins the ranking only when it has history and does not contradict the text evidence;
    #    it is never replaced by a suggested code (a contradicting code is analyzed in pool health, not ranked on)
    ranking_code = o if hist_provided is not None and hist_provided.status != "NONE" and align != "MISMATCH" else None
    inferred_code = ranking_code is None and resolution.ranking_code is not None and (provided is None or align == "MISMATCH")
    resolved_history = TQ.code_history(conn, resolution.ranking_code, as_of) if inferred_code else None
    if inferred_code and resolved_history.status == "NONE":
        # An official category without procurement history has no exact-code supplier pool;
        # keep text ranking (exploratory) rather than return an empty list.
        inferred_code = False
        warnings.append("RESOLVED_CATEGORY_NOT_OBSERVED: the identified category has no procurement history; "
                        "supplier results come from text evidence and are exploratory")
    if inferred_code:
        ranking_code = TQ.normalize_code(resolution.ranking_code)
    if ranking_code is not None:
        conn.rollback()
        conn.execute("SET TRANSACTION READ ONLY")
        q, idf = TQ.build_text_query(conn, req.query, ranking_code, cfg, as_of)
        if inferred_code:
            # Keep the frozen scorer and weights. For an inferred exact category,
            # construct its candidate pool from exact-code items only so generic
            # semantic/text neighbors cannot supply or rank unrelated companies.
            t_retrieve = time.perf_counter()
            ret = retrieve(conn, q, cfg.with_(semantic_top_k=0), idf)
            t2 = {"retrieval_ms": (time.perf_counter() - t_retrieve) * 1000}
            ret.items = {item_id: item for item_id, item in ret.items.items()
                         if item.okpd2 and item.okpd2["code"] == ranking_code.okpd2_code}
            t_lots = time.perf_counter()
            lots = score_lots(q, ret, idf, cfg)
            t2["lot_aggregation_ms"] = (time.perf_counter() - t_lots) * 1000
            t_pool = time.perf_counter()
            pool = build_pool(conn, q, lots, cfg.historical_lot_limit)
            t2["candidates_ms"] = (time.perf_counter() - t_pool) * 1000
        else:
            ret, pool, t2 = prepare_query(conn, q, idf, cfg)
        timings = {k: timings[k] + t2[k] for k in t2}
    t = time.perf_counter()
    recs, _ = rank_suppliers(q, pool, cfg)
    timings["scoring_ms"] = (time.perf_counter() - t) * 1000

    if hist_provided and hist_provided.status == "NONE":
        warnings.append("OKPD2_NOT_OBSERVED: no procurement history for the supplied code; ranking uses text and semantic evidence only")
    elif hist_provided and hist_provided.status == "SPARSE":
        warnings.append("OKPD2_HISTORY_SPARSE: little procurement history for the supplied code; results rely mostly on text evidence")
    warnings += [w for w in ret.warnings]
    if support < TQ.WEAK_EVIDENCE_ITEMS and resolution.state == "CATEGORY_UNCERTAIN":
        warnings.append("WEAK_TEXT_EVIDENCE: few historical items match the text; OKPD2 suggestions are unreliable")
    if resolution.state == "CATEGORY_UNCERTAIN" and ranking_code is None:
        warnings.append("CATEGORY_UNCERTAIN: category identification is low confidence; supplier results are exploratory")
    if resolution.state == "CATEGORY_AMBIGUOUS" and not category_confirmed:
        warnings.append("CATEGORY_AMBIGUOUS: several procurement categories match the request; select the intended "
                        "category — supplier results are exploratory until it is confirmed")
    if align == "MISMATCH":
        warnings.append("OKPD2_TEXT_MISMATCH: the supplied OKPD2 does not match the historical codes of similar products; "
                        "it is kept as supplied and analyzed below; see ranking_okpd2 and suggested_okpd2")
    elif align == "UNCERTAIN":
        warnings.append("OKPD2_ALIGNMENT_UNCERTAIN: the supplied OKPD2 could not be confirmed from historical text evidence")
    if req.region:
        warnings.append("REGION_IS_REGISTRATION_REGION: the region filter uses the supplier's INN registration region, "
                        "not its delivery area")

    top_suggested = suggestions[0].okpd2 if suggestions else None
    analyzed = ([(provided, "PROVIDED")] if provided else []) + \
               ([(top_suggested, "SUGGESTED")] if resolution.state == "RESOLVED" and top_suggested and top_suggested != provided else [])
    hist = hist_provided or (TQ.code_history(conn, top_suggested, as_of) if resolution.state == "RESOLVED" and top_suggested else None)
    regions = dict(conn.execute("SELECT supplier_id::text, inn_region_code FROM supplier WHERE supplier_id = ANY(%s::uuid[])",
                                ([r.supplier_id for r in recs],)).fetchall()) if recs else {}
    conn.rollback()                                    # end the read transaction (SET LOCAL hnsw settings)

    t = time.perf_counter()
    records = CE.load()
    pool_entries, external_entries = [], []
    for code, source in analyzed:
        try:
            with conn.transaction():
                mi = build_market_intelligence(conn, catalog, code, as_of)
            pool_entries.append(PoolHealthEntry(okpd2=code, source=source, status="OK", error=None, pool_health=mi.pool_health,
                                                concentration=mi.concentration, historical_alternatives=mi.historical_alternatives))
        except UnknownCategory as e:
            pool_entries.append(_pool_unavailable(code, source, "CATEGORY_NOT_OBSERVED", e))
        except (InvalidCategory, EvidenceCatalogError, psycopg.Error, RuntimeError, ValueError) as e:
            pool_entries.append(_pool_unavailable(code, source, type(e).__name__, e))
        try:
            with conn.transaction():
                x = build_external_expansion(conn, catalog, code, as_of)
            external_entries.append(_external_entry(x, code, source, today, records))
        except (InvalidCategory, EvidenceCatalogError, psycopg.Error) as e:
            warnings.append(f"EXTERNAL_EVIDENCE_UNAVAILABLE for {code}: {e}")
    with conn.transaction():
        profiles = _seed_profiles(conn, catalog, as_of)
    conn.rollback()
    timings["market_ms"] = (time.perf_counter() - t) * 1000

    visible = [r for r in recs if not req.region or regions.get(r.supplier_id) == req.region][:req.limit]
    suppliers = [_supplier(r, regions.get(r.supplier_id), profiles.get(r.supplier_inn), records.get(r.supplier_inn), today)
                 for r in visible]
    timings["total_ms"] = (time.perf_counter() - t0) * 1000
    search_id = encode_search_id(req)
    return SupplierSearchResponse(
        search_id=search_id,
        query=QueryEcho(text=req.query, normalized_text=q.items[0].product_name, technical_tokens=q.items[0].tech_tokens,
                        okpd2=provided, region=req.region, limit=req.limit, as_of=as_of),
        classification=Classification(
            provided_okpd2=provided, category_state=resolution.state,
            top_candidates=[CategoryCandidate(code=s.okpd2, official_name=s.official_name, score=s.confidence, basis=s.basis)
                            for s in resolution.suggestions],
            suggested_okpd2=suggestions,
            history_status=hist.status if hist else "NONE",
            history=CodeHistoryResponse(**hist.__dict__) if hist else None,
            text_okpd2_alignment=align, ranking_okpd2=ranking_code.okpd2_code if ranking_code else None,
            warnings=warnings),
        candidate_count=len(recs), suppliers=suppliers, pool_health=pool_entries, external_expansion=external_entries,
        price_intelligence=PRICE,
        integration=Integration(export_available=True, export_formats=["json", "csv"],
                                export_url=f"/api/v1/supplier-search/{search_id}/export"),
        semantic_enabled="semantic" in ret.branch_ms, warnings=warnings,
        timings_ms={k: round(v, 1) for k, v in timings.items()})


def _pool_unavailable(code: str, source: str, err: str, e: Exception) -> PoolHealthEntry:
    return PoolHealthEntry(okpd2=code, source=source, status="UNAVAILABLE", error=SectionError(code=err, message=str(e)),
                           pool_health=None, concentration=None, historical_alternatives=[])


def _supplier(r, region: str | None, profile: ExternalCandidateResponse | None, record: CE.ContactRecord | None,
              today: date) -> SupplierResult:
    return SupplierResult(
        rank=r.rank, supplier_id=r.supplier_id, inn=r.supplier_inn, registration_region=region, score=r.score,
        company_name=profile.company_name if profile else record.company_name if record else None,
        role=profile.market_role if profile else None,
        role_evidence_status=profile.verification_status if profile else "NO_EVIDENCE",
        reasons=[x for x in r.reasons if not x.startswith("semantically similar")],
        historical_evidence=HistoricalEvidence(
            relevant_lots=r.relevant_lots, relevant_awards=r.relevant_awards, relevant_ais_awards=r.relevant_ais_awards,
            relevant_em_participations=r.relevant_em_participations, most_recent_relevant=r.most_recent_relevant,
            best_products=r.best_products, best_okpd2=r.best_okpd2, evidence_lot_ids=r.evidence_lot_ids,
            components=r.components, contributions=r.contributions),
        semantic_evidence=r.semantic_evidence,
        contact=contact_of(profile, record, today),
        freshness=freshness_of(profile, today) if profile else None)


# ------------------------------------------------------------------------------------------------ export (CRM / ERP / SRM)
EXPORT_COLUMNS = ["record_type", "rank", "supplier_id", "inn", "company_name", "score", "role", "role_evidence_status",
                  "verification_status", "registration_region", "phone", "email", "website", "address", "last_checked_at",
                  "freshness_status", "source_url", "reasons", "evidence_summary", "contact_checked_at",
                  "contact_freshness_status", "contact_sources"]


def _contact_cols(c: Contact | None) -> dict:
    f = c.freshness if c else None
    return {"contact_checked_at": f.last_checked_at.isoformat() if f and f.last_checked_at else None,
            "contact_freshness_status": f.status if f else None,
            "contact_sources": "; ".join(f"{k}={v.source_url} ({v.source_authority}, {v.checked_at.date().isoformat()})"
                                         for k, v in sorted(c.sources.items())) if c and c.sources else None}


def export_rows(res: SupplierSearchResponse) -> list[dict]:
    rows = []
    for s in res.suppliers:
        c, f, h = s.contact, s.freshness, s.historical_evidence
        rows.append({"record_type": "HISTORICAL_SUPPLIER", "rank": s.rank, "supplier_id": s.supplier_id, "inn": s.inn,
                     "company_name": s.company_name, "score": s.score, "role": s.role, "role_evidence_status": s.role_evidence_status,
                     "verification_status": None, "registration_region": s.registration_region,
                     "phone": c.phone if c else None, "email": c.email if c else None, "website": c.website if c else None,
                     "address": c.address if c else None,
                     "last_checked_at": f.last_checked_at.isoformat() if f and f.last_checked_at else None,
                     "freshness_status": f.status if f else None, "source_url": f.source_url if f else None,
                     "reasons": "; ".join(s.reasons),
                     "evidence_summary": f"{h.relevant_lots} relevant lots; {h.relevant_awards} relevant awards; "
                                         f"last {h.most_recent_relevant.isoformat()}; lots {', '.join(h.evidence_lot_ids)}",
                     **_contact_cols(c)})
    for x in res.external_expansion:
        for c in x.candidates:
            rows.append({"record_type": "EXTERNAL_CANDIDATE", "rank": None, "supplier_id": None, "inn": c.supplier_inn,
                         "company_name": c.company_name, "score": None, "role": c.market_role,
                         "role_evidence_status": c.verification_status, "verification_status": c.verification_status,
                         "registration_region": None, "phone": c.contact.phone, "email": c.contact.email,
                         "website": c.contact.website, "address": c.contact.address,
                         "last_checked_at": c.freshness.last_checked_at.isoformat() if c.freshness.last_checked_at else None,
                         "freshness_status": c.freshness.status, "source_url": c.freshness.source_url,
                         "reasons": "; ".join(c.verification_reason_codes + [f"REVIEW:{r}" for r in c.review_reasons]),
                         "evidence_summary": f"OKPD2 {x.okpd2}; {c.evidence_count} evidence records "
                                             f"({c.active_evidence_count} active); exact OKPD2 asserted by source: "
                                             f"{str(c.exact_okpd2_asserted_by_source).lower()}",
                         **_contact_cols(c.contact)})
    return rows


def export_json(res: SupplierSearchResponse) -> dict:
    return {"search_id": res.search_id, "query": res.query.model_dump(mode="json"),
            "classification": {"provided_okpd2": res.classification.provided_okpd2,
                               "text_okpd2_alignment": res.classification.text_okpd2_alignment,
                               "history_status": res.classification.history_status},
            "price_intelligence": res.price_intelligence.model_dump(), "columns": EXPORT_COLUMNS, "records": export_rows(res)}


def export_csv(res: SupplierSearchResponse) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in export_rows(res):
        w.writerow({k: "" if v is None else v for k, v in r.items()})
    return buf.getvalue()

