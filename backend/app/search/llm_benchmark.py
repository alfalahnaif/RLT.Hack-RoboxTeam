"""Small, isolated OKPD2 ambiguity benchmark. Never reads supplier ranking HOLDOUT."""
from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass, replace
from pathlib import Path

from app.search.llm_verifier import VerificationResult, VerifierSettings, provider_from_env, verify_resolution


@dataclass(frozen=True)
class Candidate:
    okpd2: str
    official_name: str
    confidence: float
    basis: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolverResult:
    state: str
    suggestions: list[Candidate]
    margin: float | None = None

    @property
    def ranking_code(self) -> str | None:
        return self.suggestions[0].okpd2 if self.state == "RESOLVED" else None


class FixtureReplayProvider:
    """Tests the benchmark plumbing; fixture decisions are not model measurements."""
    name = "fixture-replay"
    model = "fixture-replay"

    def __init__(self):
        self.answer: dict = {}

    def verify(self, query, candidates):
        return VerificationResult.model_validate(self.answer)


def _metrics(rows: list[tuple[str | None, str | None, float]]) -> dict:
    labeled = [(expected, predicted) for expected, predicted, _ in rows if expected is not None]
    ambiguous = [(expected, predicted) for expected, predicted, _ in rows if expected is None]
    latencies = sorted(ms for _, _, ms in rows)
    def percentile(q: float) -> float | None:
        if not latencies:
            return None
        position = (len(latencies) - 1) * q
        low, high = math.floor(position), math.ceil(position)
        return latencies[low] + (latencies[high] - latencies[low]) * (position - low)
    return {
        "cases": len(rows),
        "ambiguous_top1_accuracy": sum(a == b for a, b in labeled) / len(labeled) if labeled else None,
        "correct_ambiguity_detection": sum(b is None for _, b in ambiguous) / len(ambiguous) if ambiguous else None,
        "wrong_confident_selection_rate": sum(b is not None and b != a for a, b, _ in rows) / len(rows) if rows else None,
        "abstention_rate": sum(b is None for _, b, _ in rows) / len(rows) if rows else None,
        "p50_latency_ms": percentile(.5), "p95_latency_ms": percentile(.95),
    }


def _load_local_env(path: Path) -> None:
    """Read only verifier settings from an ignored local file; never print secrets."""
    if not path.is_file():
        return
    allowed = {"OKPD2_LLM_API_KEY", "GROQ_API_KEY", "OKPD2_LLM_BASE_URL",
               "OKPD2_LLM_MODEL", "OKPD2_LLM_TIMEOUT_SECONDS"}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name in allowed and not os.getenv(name):
            os.environ[name] = value.strip().strip('"').strip("'")


def run_benchmark(cases: list[dict], provider, *, fixture_replay: bool = False) -> dict:
    baseline, verified = [], []
    details = []
    timeouts = invalid = provider_errors = rate_limits = valid_decisions = 0
    for case in cases:
        deterministic = case["deterministic"]
        resolution = ResolverResult(deterministic["status"],
                                    [Candidate(c["code"], c["official_name"], c["score"], c["basis"])
                                     for c in deterministic["candidates"]], deterministic.get("margin"))
        if fixture_replay:
            provider.answer = case["fixture_response"]
        outcome = verify_resolution(case["query"], resolution, provider, VerifierSettings(enabled=True))
        timeouts += outcome.status == "TIMEOUT"
        invalid += outcome.status == "INVALID_RESPONSE"
        provider_errors += outcome.status == "PROVIDER_ERROR"
        rate_limits += outcome.failure_code == "HTTP_429"
        valid_decisions += outcome.status in {"RESOLVED", "AMBIGUOUS", "ABSTAIN"}
        expected = case["expected_code"]
        baseline.append((expected, resolution.ranking_code, 0.0))
        verified.append((expected, outcome.resolution.ranking_code, outcome.latency_ms))
        details.append({"id": case["id"], "expected_code": expected,
                        "resolver_code": resolution.ranking_code, "verified_code": outcome.resolution.ranking_code,
                        "verification_status": outcome.status, "reason": outcome.reason,
                        "latency_ms": round(outcome.latency_ms, 1), "failure_code": outcome.failure_code,
                        "fallback_used": outcome.fallback_used})
    return {"mode": "fixture_replay_not_model_accuracy" if fixture_replay else "live_model",
            "candidate_source": "temporary_resolver_contract_fixtures",
            "provider": provider.name, "model_id": provider.model,
            "reported_model_id": getattr(provider, "reported_model_id", None),
            "response_format": "json_schema_strict",
            "provider_connection_successful": getattr(provider, "http_successes", 0) > 0 if not fixture_replay else None,
            "valid_structured_output_responses": getattr(provider, "valid_responses", valid_decisions),
            "timeout_rate": timeouts / len(cases) if cases else 0.0,
            "invalid_response_rate": invalid / len(cases) if cases else 0.0,
            "provider_error_rate": provider_errors / len(cases) if cases else 0.0,
            "http_429_rate": rate_limits / len(cases) if cases else 0.0,
            "resolver_v4_alone": _metrics(baseline), "resolver_v4_plus_llm": _metrics(verified), "cases": details}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mode", choices=["live", "fixture-replay"], required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"),
                        help="Ignored local verifier settings; only used in live mode")
    args = parser.parse_args()
    cases = json.loads(args.input.read_text(encoding="utf-8"))
    if args.mode == "live":
        _load_local_env(args.env_file)
    settings = replace(VerifierSettings.from_env(), enabled=True)
    provider = FixtureReplayProvider() if args.mode == "fixture-replay" else provider_from_env(settings)
    print(json.dumps(run_benchmark(cases, provider, fixture_replay=args.mode == "fixture-replay"),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
