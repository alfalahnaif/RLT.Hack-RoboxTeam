"""Strict parsing and deterministic evaluation of a curated external-evidence seed.

The seed is input data, not an instruction source. No URL is fetched and no
database table is mutated. A source's product wording never becomes an exact
OKPD2 assertion unless the seed supplies a structured exact-code assertion.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Sequence, TypeVar

from app.enrichment.models import (CuratedCandidate, EvidenceSeed, EvidenceStatus, EvidenceType,
                                   ExternalCandidate, MarketRole, ReconciliationStatus, RoleAssertion,
                                   SourceAuthority, SupplierEvidence, TargetProductMatch,
                                   VerificationStatus, VerificationStrength, VerifiedExternalCandidate)
from app.shared.normalize import normalize_inn, normalize_okpd2


EnumType = TypeVar("EnumType", bound=Enum)
DIRECT_PRODUCT_WORDING = "молоко питьевое стерилизованное"
NON_BLOCKING_REVIEW_REASONS = frozenset({
    "LEGAL_NAME_CHANGED_RECENTLY_ALIAS_PRESERVED",
    "NO_CURRENT_REGISTRY_DECLARATION_LOCATED_IN_THIS_RESEARCH_PASS",
})
REASON_SHAPE = re.compile(r"[A-Z][A-Z0-9_]*\Z")
DATE_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def _object(value: object, field: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _string(value: object, field: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return tuple(value)


def _enum(enum_type: type[EnumType], value: object, field: str) -> EnumType:
    try:
        return enum_type(value)
    except (ValueError, TypeError):
        raise ValueError(f"Unsupported {field}: {value!r}") from None


def _date(value: object, field: str, *, optional: bool = False) -> date | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not DATE_SHAPE.fullmatch(value):
        raise ValueError(f"{field} must be an ISO date YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Malformed {field}: {value!r}") from None


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Malformed {field}: {value!r}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _reason_codes(value: object, field: str) -> tuple[str, ...]:
    codes = _strings(value, field)
    if len(codes) != len(set(codes)) or any(not REASON_SHAPE.fullmatch(code) for code in codes):
        raise ValueError(f"{field} contains duplicate or malformed reason codes")
    return codes


def _parse_evidence(raw: object, checked_at: datetime, field: str) -> SupplierEvidence:
    item = _object(raw, field)
    evidence_type = _enum(EvidenceType, item.get("evidence_type"), f"{field}.evidence_type")
    status = _enum(EvidenceStatus, item.get("evidence_status"), f"{field}.evidence_status")
    strength = _enum(VerificationStrength, item.get("verification_strength"), f"{field}.verification_strength")
    valid_until = _date(item.get("valid_until"), f"{field}.valid_until", optional=True)
    retrieved_at = _timestamp(item.get("retrieved_at"), f"{field}.retrieved_at")
    if retrieved_at > checked_at:
        raise ValueError(f"{field}.retrieved_at is after checked_at")
    if status == EvidenceStatus.ACTIVE and valid_until and valid_until < checked_at.date():
        raise ValueError(f"{field}.valid_until is before checked_at for ACTIVE evidence")
    record_id = _string(item.get("source_record_id"), f"{field}.source_record_id", optional=True)
    if evidence_type == EvidenceType.CONFORMITY_DECLARATION and record_id is None:
        raise ValueError(f"{field}.source_record_id is required for a declaration")
    asserted_codes = _strings(item.get("asserted_okpd2_codes", []), f"{field}.asserted_okpd2_codes")
    if any(normalize_okpd2(code).flags for code in asserted_codes):
        raise ValueError(f"{field}.asserted_okpd2_codes contains an invalid code")
    return SupplierEvidence(
        evidence_type=evidence_type,
        source_url=_string(item.get("source_url"), f"{field}.source_url", optional=True),
        source_name=_string(item.get("source_name"), f"{field}.source_name"),
        product_scope=_strings(item.get("product_scope", []), f"{field}.product_scope"),
        evidence_date=_date(item.get("evidence_date"), f"{field}.evidence_date", optional=True),
        checked_at=checked_at, evidence_status=status, verification_strength=strength,
        notes=_string(item.get("notes"), f"{field}.notes", optional=True),
        source_record_id=record_id,
        source_authority=_enum(SourceAuthority, item.get("source_authority"), f"{field}.source_authority"),
        valid_until=valid_until, retrieved_at=retrieved_at,
        role_assertion=_enum(RoleAssertion, item.get("role_assertion"), f"{field}.role_assertion"),
        asserted_okpd2_codes=asserted_codes,
    )


def _parse_candidate(raw: object, target: str, checked_at: datetime, index: int) -> CuratedCandidate:
    field = f"candidates[{index}]"
    item = _object(raw, field)
    inn = normalize_inn(item.get("supplier_inn"))
    if inn.inn is None or inn.flags:
        raise ValueError(f"{field}.supplier_inn is an invalid INN: {inn.flags}")
    aliases = _strings(item.get("aliases", []), f"{field}.aliases")
    if len(aliases) != len(set(aliases)):
        raise ValueError(f"{field}.aliases contains duplicates")
    exact = item.get("exact_okpd2_asserted_by_source")
    if type(exact) is not bool:
        raise ValueError(f"{field}.exact_okpd2_asserted_by_source must be boolean")
    raw_evidence = item.get("evidence_records")
    if not isinstance(raw_evidence, list):
        raise ValueError(f"{field}.evidence_records must be a list")
    evidence = tuple(_parse_evidence(record, checked_at, f"{field}.evidence_records[{i}]")
                     for i, record in enumerate(raw_evidence))
    has_exact_assertion = any(target in record.asserted_okpd2_codes for record in evidence)
    if exact != has_exact_assertion:
        raise ValueError(f"{field}.exact_okpd2_asserted_by_source conflicts with structured source assertions")
    return CuratedCandidate(
        supplier_inn=inn.inn,
        canonical_name=_string(item.get("canonical_name"), f"{field}.canonical_name"),
        aliases=aliases,
        reconciliation_status=_enum(ReconciliationStatus, item.get("reconciliation_status"), f"{field}.reconciliation_status"),
        market_role=_enum(MarketRole, item.get("market_role"), f"{field}.market_role"),
        verification_status=_enum(VerificationStatus, item.get("verification_status"), f"{field}.verification_status"),
        overall_strength=_enum(VerificationStrength, item.get("overall_strength"), f"{field}.overall_strength"),
        target_product_match=_enum(TargetProductMatch, item.get("target_product_match"), f"{field}.target_product_match"),
        exact_okpd2_asserted_by_source=exact,
        verification_reason_codes=_reason_codes(item.get("verification_reason_codes", []), f"{field}.verification_reason_codes"),
        review_reasons=_reason_codes(item.get("review_reasons", []), f"{field}.review_reasons"),
        notes=_string(item.get("notes"), f"{field}.notes", optional=True),
        evidence_records=evidence,
    )


def parse_evidence_seed(payload: object) -> EvidenceSeed:
    """Validate the seed without executing its policy_notes or fetching source URLs."""
    data = _object(payload, "seed")
    target = normalize_okpd2(data.get("target_okpd2"))
    if target.okpd2_code is None or target.flags:
        raise ValueError("target_okpd2 must be a valid exact OKPD2 value")
    checked_at = _timestamp(data.get("checked_at"), "checked_at")
    raw_candidates = data.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("candidates must be a list")
    candidates = tuple(_parse_candidate(raw, target.okpd2_code, checked_at, index)
                       for index, raw in enumerate(raw_candidates))
    inns = [candidate.supplier_inn for candidate in candidates]
    if len(inns) != len(set(inns)):
        raise ValueError("Duplicate candidate INN would split one canonical identity")
    demo = _strings(data.get("recommended_demo_subset", []), "recommended_demo_subset")
    review = _strings(data.get("recommended_review_queue", []), "recommended_review_queue")
    if any(inn not in inns for inn in demo + review):
        raise ValueError("Recommended lists refer to an unknown supplier INN")
    return EvidenceSeed(target.okpd2_code, _string(data.get("target_label"), "target_label"),
                        checked_at, candidates, demo, review)


def load_evidence_seed(path: Path) -> EvidenceSeed:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot load evidence seed: {error}") from error
    return parse_evidence_seed(payload)


def _direct_product(evidence: SupplierEvidence) -> bool:
    return any(DIRECT_PRODUCT_WORDING in phrase.casefold() for phrase in evidence.product_scope)


def _active(evidence: SupplierEvidence) -> bool:
    return evidence.evidence_status == EvidenceStatus.ACTIVE


def _declaration_support(candidate: CuratedCandidate) -> bool:
    if candidate.target_product_match != TargetProductMatch.DIRECT_PRODUCT_TEXT:
        return False
    return any(_active(e) and e.evidence_type == EvidenceType.CONFORMITY_DECLARATION
               and e.verification_strength == VerificationStrength.STRONG
               and e.role_assertion == RoleAssertion.MANUFACTURER_AND_APPLICANT
               and _direct_product(e) for e in candidate.evidence_records)


def _corroborated_support(candidate: CuratedCandidate) -> bool:
    if candidate.target_product_match != TargetProductMatch.DIRECT_PRODUCT_TEXT:
        return False
    legal = any(_active(e) and e.evidence_type == EvidenceType.LEGAL_IDENTITY
                and e.role_assertion == RoleAssertion.ACTIVE_DAIRY_MANUFACTURER
                and e.verification_strength == VerificationStrength.STRONG
                for e in candidate.evidence_records)
    product = any(_active(e) and e.evidence_type == EvidenceType.CURRENT_PRODUCT_LISTING
                  and e.role_assertion == RoleAssertion.MANUFACTURER_NAMED_ON_PRODUCT_LISTING
                  and e.verification_strength in (VerificationStrength.MODERATE, VerificationStrength.STRONG)
                  and _direct_product(e) for e in candidate.evidence_records)
    return legal and product


def _evidence_summary(evidence: SupplierEvidence) -> dict:
    return {
        "evidence_type": evidence.evidence_type,
        "source_name": evidence.source_name,
        "source_url": evidence.source_url,
        "source_record_id": evidence.source_record_id,
        "source_authority": evidence.source_authority,
        "product_scope": evidence.product_scope,
        "evidence_date": evidence.evidence_date,
        "valid_until": evidence.valid_until,
        "retrieved_at": evidence.retrieved_at,
        "evidence_status": evidence.evidence_status,
        "verification_strength": evidence.verification_strength,
        "role_assertion": evidence.role_assertion,
        "asserted_okpd2_codes": evidence.asserted_okpd2_codes,
        "notes": evidence.notes,
    }


def _why(candidate: CuratedCandidate, declaration: bool, corroborated: bool) -> str:
    if candidate.verification_status == VerificationStatus.UNDER_REVIEW:
        return "Curated review required: " + ", ".join(candidate.review_reasons) + ". Evidence is retained without a current verified conclusion."
    if candidate.verification_status == VerificationStatus.UNVERIFIED:
        return "Curated evidence does not authorize a verified conclusion."
    if declaration:
        basis = "Curated active strong declaration directly covers sterilized drinking milk and names the INN-linked entity as manufacturer/applicant."
    elif corroborated:
        basis = "Curated active legal-manufacturer record and current product listing jointly support sterilized drinking milk."
    else:
        raise ValueError("VERIFIED candidate lacks supporting evidence")
    if not candidate.exact_okpd2_asserted_by_source:
        basis += " The curated seed records no exact target OKPD2 source assertion."
    return basis


def evaluate_seed(seed: EvidenceSeed, reconciled: Sequence[ExternalCandidate]) -> tuple[VerifiedExternalCandidate, ...]:
    """Evaluate curated decisions while keeping reconciliation untouched and separate."""
    historical = {candidate.supplier_inn: candidate for candidate in reconciled}
    if len(historical) != len(reconciled) or set(historical) != {c.supplier_inn for c in seed.candidates}:
        raise ValueError("Reconciliation candidates do not match seed INNs exactly")
    results = []
    for candidate in seed.candidates:
        history = historical[candidate.supplier_inn]
        if history.target_okpd2 != seed.target_okpd2 or history.reconciliation_status != candidate.reconciliation_status:
            raise ValueError(f"Reconciliation status or target mismatch for INN {candidate.supplier_inn}")
        declaration = _declaration_support(candidate)
        corroborated = _corroborated_support(candidate)
        blocking = set(candidate.review_reasons) - NON_BLOCKING_REVIEW_REASONS
        if "LEGAL_NAME_CHANGED_RECENTLY_ALIAS_PRESERVED" in candidate.review_reasons and not candidate.aliases:
            raise ValueError(f"Alias review reason has no aliases for INN {candidate.supplier_inn}")
        if candidate.verification_status == VerificationStatus.VERIFIED:
            if blocking:
                raise ValueError(f"Explicit review reasons block VERIFIED for INN {candidate.supplier_inn}")
            if not (declaration or corroborated):
                raise ValueError(f"VERIFIED has no current supporting evidence for INN {candidate.supplier_inn}")
            if candidate.overall_strength in (VerificationStrength.NONE, VerificationStrength.WEAK):
                raise ValueError(f"VERIFIED strength is too weak for INN {candidate.supplier_inn}")
        if candidate.verification_status == VerificationStatus.UNDER_REVIEW and not candidate.review_reasons:
            raise ValueError(f"UNDER_REVIEW requires explicit review reasons for INN {candidate.supplier_inn}")
        results.append(VerifiedExternalCandidate(
            supplier_inn=candidate.supplier_inn, company_name=candidate.canonical_name,
            aliases=candidate.aliases, reconciliation_status=history.reconciliation_status,
            market_role=candidate.market_role, verification_status=candidate.verification_status,
            verification_strength=candidate.overall_strength,
            target_product_match=candidate.target_product_match,
            exact_okpd2_asserted_by_source=candidate.exact_okpd2_asserted_by_source,
            verification_reason_codes=candidate.verification_reason_codes,
            review_reasons=candidate.review_reasons,
            why_candidate=_why(candidate, declaration, corroborated),
            evidence_summary=tuple(_evidence_summary(e) for e in candidate.evidence_records),
            evidence_count=len(candidate.evidence_records),
            active_evidence_count=sum(_active(e) for e in candidate.evidence_records),
        ))
    return tuple(results)
