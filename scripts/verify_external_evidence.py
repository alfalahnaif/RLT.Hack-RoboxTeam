#!/usr/bin/env python3
"""P3-002B: evaluate the supplied evidence seed against read-only reconciliation."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.enrichment.models import CandidateInput  # noqa: E402
from app.enrichment.reconciliation import reconcile_candidates  # noqa: E402
from app.enrichment.verification import evaluate_seed, load_evidence_seed  # noqa: E402
from app.shared.config import database_url  # noqa: E402


SEED_PATH = ROOT / "data" / "seed" / "p3_002b_evidence_seed.json"
JSON_PATH = ROOT / "reports" / "p3_002b_verified_external_candidates.json"
MARKDOWN_PATH = ROOT / "reports" / "p3_002b_verified_external_candidates.md"
HISTORY_AS_OF = date(2026, 1, 1)


def _json_value(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def build_report() -> dict:
    seed = load_evidence_seed(SEED_PATH)
    with psycopg.connect(database_url()) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        history = reconcile_candidates(
            conn,
            [CandidateInput(candidate.supplier_inn, candidate.canonical_name)
             for candidate in seed.candidates],
            seed.target_okpd2,
            HISTORY_AS_OF,
        )
        results = evaluate_seed(seed, history)
    counts = Counter(candidate.verification_status.value for candidate in results)
    report = {
        "task": "P3-002B",
        "target_okpd2": seed.target_okpd2,
        "target_label": seed.target_label,
        "checked_at": seed.checked_at,
        "historical_as_of": HISTORY_AS_OF,
        "seed_path": SEED_PATH.relative_to(ROOT).as_posix(),
        "seed_sha256": hashlib.sha256(SEED_PATH.read_bytes()).hexdigest(),
        "reconciliation_definition": "Observed canonical procurement history with publish_date before historical_as_of; independent of evidence verification.",
        "verification_definition": "Curated status validated against current supporting evidence and explicit review reasons at checked_at; EXTERNAL_NEW alone gives no verification.",
        "exact_okpd2_definition": "True only when a structured source assertion names the exact target OKPD2 value; direct product wording and broader codes are separate.",
        "verification_status_counts": {status: counts[status] for status in ("UNVERIFIED", "UNDER_REVIEW", "VERIFIED")},
        "candidates": [candidate.to_dict() for candidate in results],
        "limitations": [
            "Evidence facts and source URLs are reproduced from the supplied curated seed; this run does not fetch or independently check the URLs.",
            "Evidence records are associated with the canonical supplier INN by the curated seed.",
            "A terminated or suspended declaration remains historical evidence and does not alone support current verification.",
            "All exact target OKPD2 assertions in this seed are false; product wording does not assert the leaf code.",
        ],
    }
    return json.loads(json.dumps(report, ensure_ascii=False, default=_json_value))


def _cell(value: object) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict) -> str:
    lines = [
        "# P3-002B — Curated External Supplier Verification", "",
        f"Target OKPD2 value: `{report['target_okpd2']}` ({report['target_label']}).",
        f"Evidence checked at: `{report['checked_at']}`. Historical cutoff: `{report['historical_as_of']}`.",
        f"Curated seed SHA-256: `{report['seed_sha256']}`.", "",
        "Reconciliation and verification are independent. `EXTERNAL_NEW` does not imply `VERIFIED`.",
        "Product wording does not establish an exact source assertion of the target OKPD2 value.", "",
        "## Candidates", "",
        "| INN | Company | Reconciliation | Market role | Verification | Strength | Product match | Evidence (active / total) | Exact OKPD2 asserted |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for candidate in report["candidates"]:
        lines.append(
            f"| `{candidate['supplier_inn']}` | {_cell(candidate['company_name'])} | "
            f"{candidate['reconciliation_status']} | {candidate['market_role']} | "
            f"{candidate['verification_status']} | {candidate['verification_strength']} | "
            f"{candidate['target_product_match']} | "
            f"{candidate['active_evidence_count']} / {candidate['evidence_count']} | "
            f"{str(candidate['exact_okpd2_asserted_by_source']).lower()} |"
        )
    lines += ["", "## Evidence and reasons", ""]
    for candidate in report["candidates"]:
        lines += [f"### {candidate['supplier_inn']} — {candidate['company_name']}", "",
                  f"**Why candidate:** {candidate['why_candidate']}", "",
                  f"**Aliases:** {', '.join(candidate['aliases']) or 'none'}.", "",
                  f"**Verification reason codes:** {', '.join(candidate['verification_reason_codes']) or 'none'}.", "",
                  f"**Review reasons:** {', '.join(candidate['review_reasons']) or 'none'}.", ""]
        for evidence in candidate["evidence_summary"]:
            url = evidence["source_url"]
            source = f"[{_cell(evidence['source_name'])}]({url})" if url else _cell(evidence["source_name"])
            lines += [
                f"- **{evidence['evidence_type']}** — {source}; status `{evidence['evidence_status']}`; "
                f"strength `{evidence['verification_strength']}`; authority `{evidence['source_authority']}`; "
                f"role `{evidence['role_assertion']}`; record ID `{_cell(evidence['source_record_id'])}`; "
                f"evidence date `{_cell(evidence['evidence_date'])}`; valid until `{_cell(evidence['valid_until'])}`; "
                f"retrieved `{_cell(evidence['retrieved_at'])}`."
            ]
            if evidence["product_scope"]:
                lines.append("  - Product scope: " + "; ".join(_cell(p) for p in evidence["product_scope"]) + ".")
            if evidence["asserted_okpd2_codes"]:
                lines.append("  - Source asserted OKPD2 values: " + ", ".join(evidence["asserted_okpd2_codes"]) + ".")
            if evidence["notes"]:
                lines.append("  - Seed note: " + _cell(evidence["notes"]))
        lines.append("")
    lines += ["## Verification counts", ""]
    for status, count in report["verification_status_counts"].items():
        lines.append(f"- `{status}`: {count}")
    lines += ["", "## Limits", ""]
    lines += [f"- {limit}" for limit in report["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {JSON_PATH.relative_to(ROOT)} and {MARKDOWN_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
