"""Exercise the integrated supplier-search API without reading ranking HOLDOUT data."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen


QUERIES = {
    "A_asphaltites": "Асфальтиты",
    "B_asphaltite": "Асфальтит",
    "C_exact_wine": "Вина столовые прочие",
    "D_natural_bitumen": "Битум природный",
    "E_table": "Стол",
    "F_medical_table": "Стол для медицинских процедур с регулируемой высотой",
    "G_pipes": "Трубы",
    "H_unknown": "Флюрбикс заквант",
    "I_acer": "Ноутбук Acer Aspire 5 A515-57-50R7",
    "J_nitrile_gloves": "Перчатки нитриловые",
    "K_milk": "Молоко ультрапастеризованное 3.2%",
}


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (position - low), 1)


def run_query(base_url: str, case_id: str, query: str) -> dict:
    payload = json.dumps({"query": query, "limit": 5}, ensure_ascii=False).encode("utf-8")
    request = Request(base_url.rstrip("/") + "/supplier-search", payload,
                      {"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    with urlopen(request, timeout=180) as response:
        status = response.status
        body = json.load(response)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    classification = body["classification"]
    warnings = classification["warnings"]
    verifier = next((warning for warning in warnings if warning.startswith("LLM_VERIFIER_")
                     or warning.startswith("LLM_VERIFIED_CATEGORY")), None)
    result = {
        "id": case_id, "query": query, "http_status": status, "elapsed_ms": elapsed_ms,
        "category_state": classification["category_state"],
        "leading_code": classification["top_candidates"][0]["code"] if classification["top_candidates"] else None,
        "leading_basis": classification["top_candidates"][0]["basis"] if classification["top_candidates"] else None,
        "ranking_code": classification["ranking_okpd2"],
        "official_candidates": [{"code": candidate["code"], "title": candidate["official_name"]}
                                for candidate in classification["top_candidates"]],
        "supplier_count": len(body["suppliers"]),
        "llm_verification_ms": round(body.get("timings_ms", {}).get("llm_verification_ms", 0), 1),
        "verifier_result": verifier, "warnings": warnings,
    }
    print(f"{case_id}: {result['category_state']} {result['leading_code']} "
          f"{elapsed_ms} ms, LLM {result['llm_verification_ms']} ms", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8012/api/v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    warmup = run_query(args.base_url, "warmup", QUERIES["A_asphaltites"])
    rows = [run_query(args.base_url, case_id, query) for case_id, query in QUERIES.items()]
    deterministic = [row["elapsed_ms"] for row in rows if row["llm_verification_ms"] == 0]
    llm = [row["llm_verification_ms"] for row in rows if row["llm_verification_ms"] > 0]
    report = {
        "api": args.base_url, "warmup_elapsed_ms": warmup["elapsed_ms"],
        "query_count": len(rows), "llm_invocation_count": len(llm),
        "llm_invocation_rate": len(llm) / len(rows),
        "deterministic_total_p50_ms": percentile(deterministic, .5),
        "deterministic_total_p95_ms": percentile(deterministic, .95),
        "llm_p50_ms": percentile(llm, .5), "llm_p95_ms": percentile(llm, .95),
        "http_429_count": sum("HTTP_429" in (row["verifier_result"] or "") for row in rows),
        "timeout_count": sum("TIMEOUT" in (row["verifier_result"] or "") for row in rows),
        "fallback_count": sum((row["verifier_result"] or "").startswith("LLM_VERIFIER_FALLBACK") for row in rows),
        "cases": rows,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
