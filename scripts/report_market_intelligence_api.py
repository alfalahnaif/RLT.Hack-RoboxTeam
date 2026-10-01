#!/usr/bin/env python3
"""Measure the local read-only API and write the P3-002C audit summary."""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.api.main import app  # noqa: E402


PRIMARY = "10.51.11.141"
CONTRAST = "10.20.25.111"
ENDPOINT = "/api/v1/market-intelligence/{okpd2}"
JSON_PATH = ROOT / "reports" / "p3_002c_market_intelligence_api.json"
MARKDOWN_PATH = ROOT / "reports" / "p3_002c_market_intelligence_api.md"


def _summary(payload: dict) -> dict:
    pool = payload["pool_health"]
    external = payload["external_expansion"]
    return {
        "okpd2": payload["category"]["okpd2"],
        "as_of": payload["category"]["as_of"],
        "pool_health": pool,
        "concentration": payload["concentration"],
        "historical_alternative_count": len(payload["historical_alternatives"]),
        "external_expansion_available": external["available"],
        "verified_count": external["verified_count"],
        "under_review_count": external["under_review_count"],
        "candidate_statuses": [
            {"supplier_inn": candidate["supplier_inn"],
             "reconciliation_status": candidate["reconciliation_status"],
             "verification_status": candidate["verification_status"],
             "exact_okpd2_asserted_by_source": candidate["exact_okpd2_asserted_by_source"]}
            for candidate in external["candidates"]
        ],
    }


def build_report() -> dict:
    with TestClient(app) as client:
        samples = []
        primary_response = None
        for _ in range(5):
            started = time.perf_counter()
            response = client.get(ENDPOINT.format(okpd2=PRIMARY))
            samples.append(round((time.perf_counter() - started) * 1000, 3))
            if response.status_code != 200:
                raise RuntimeError(f"Primary API request failed: {response.status_code} {response.text}")
            primary_response = response
        contrast_response = client.get(ENDPOINT.format(okpd2=CONTRAST))
        if contrast_response.status_code != 200:
            raise RuntimeError(f"Contrasting API request failed: {contrast_response.status_code} {contrast_response.text}")
    ordered = sorted(samples)
    p95_position = (len(ordered) - 1) * .95
    lower = int(p95_position)
    p95 = ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (p95_position - lower)
    return {
        "task": "P3-002C",
        "api_route": f"GET {ENDPOINT}",
        "query_parameters": {"as_of_default": "2026-01-01", "recent_days_default": 365},
        "response_sections": ["category", "pool_health", "concentration", "historical_alternatives",
                              "external_expansion", "provenance"],
        "primary": _summary(primary_response.json()),
        "contrast": _summary(contrast_response.json()),
        "performance": {
            "category": PRIMARY, "repeated_calls": 5, "samples_ms": samples,
            "median_ms": round(statistics.median(samples), 3),
            "p95_ms": round(p95, 3), "max_ms": max(samples),
            "response_payload_bytes": len(primary_response.content),
            "method": "Local FastAPI TestClient against canonical PostgreSQL; includes HTTP adapter and database work.",
        },
        "tests": "286 safe unit/API tests passed; integration tests that use shared test state were not run.",
        "central_app_change": "No existing FastAPI app/router existed; created backend/app/api/main.py and registered one router there.",
        "forbidden_files": "Search, semantic, ranking, benchmark, Docker, requirements, migrations, CLI and frontend files untouched.",
        "limitations": [
            "Historical concentration describes observed procurement awards, not the entire current supplier market.",
            "No curated external evidence in the catalog does not mean no external suppliers exist.",
            "Source URLs are validated syntactically and are not fetched during API requests.",
            "FastAPI, Pydantic, HTTPX and Uvicorn were installed in the local worktree virtual environment only; deployment dependency files remain unchanged under this task's constraints.",
            "Historical alternatives expose observed_relation_count because the accepted pool service does not expose a distinct per-supplier lot count.",
        ],
        "recommended_next_step": "After semantic retrieval work is accepted, integrate this endpoint with the frontend and historical recommendation flow; add runtime dependencies when the requirements-file constraint is lifted.",
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# P3-002C — Market Intelligence API Integration", "",
        f"Route: `{report['api_route']}`; defaults: `as_of={report['query_parameters']['as_of_default']}`, "
        f"`recent_days={report['query_parameters']['recent_days_default']}`.", "",
        "## Response contract", "",
        "Typed sections: " + ", ".join(f"`{section}`" for section in report["response_sections"]) + ".",
        "Historical procurement, external reconciliation and curated verification remain separate.", "",
        "## Real canonical-database responses", "",
        "| OKPD2 | Pool status | Lots | Known customers | Observed / winning suppliers | Awards | Top 1 | Top 3 | HHI | Signal | Alternatives | Curated external | Verified / review |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|",
    ]
    for key in ("primary", "contrast"):
        entry = report[key]
        pool = entry["pool_health"]
        lines.append(
            f"| `{entry['okpd2']}` | {pool['status']} | {pool['lot_count']} | {pool['known_customer_count']} | "
            f"{pool['observed_supplier_count']} / {pool['winning_supplier_count']} | {pool['award_count']} | "
            f"{pool['top1_share']:.4f} | {pool['top3_share']:.4f} | {pool['hhi']:.4f} | "
            f"{entry['concentration']['signal']} | {entry['historical_alternative_count']} | "
            f"{str(entry['external_expansion_available']).lower()} | "
            f"{entry['verified_count']} / {entry['under_review_count']} |"
        )
    lines += ["", "### Curated candidate states", "",
              "| INN | Reconciliation | Verification | Exact OKPD2 source assertion |",
              "|---|---|---|---|"]
    for candidate in report["primary"]["candidate_statuses"]:
        lines.append(f"| `{candidate['supplier_inn']}` | {candidate['reconciliation_status']} | "
                     f"{candidate['verification_status']} | "
                     f"{str(candidate['exact_okpd2_asserted_by_source']).lower()} |")
    performance = report["performance"]
    lines += ["", "## Performance", "",
              f"Five local calls: {performance['samples_ms']} ms; median **{performance['median_ms']} ms**, "
              f"p95 **{performance['p95_ms']} ms**, max **{performance['max_ms']} ms**; "
              f"response **{performance['response_payload_bytes']} bytes**.",
              performance["method"], "", "## Tests and integration", "",
              f"- {report['tests']}", f"- {report['central_app_change']}",
              f"- {report['forbidden_files']}", "", "## Limitations", ""]
    lines += [f"- {item}" for item in report["limitations"]]
    lines += ["", "## Next step", "", report["recommended_next_step"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {JSON_PATH.relative_to(ROOT)} and {MARKDOWN_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
