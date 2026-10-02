"""Closed-world verifier tests use resolver-contract fixtures, without the V4 worktree."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from app.search.llm_verifier import (
    OpenAICompatibleProvider, VerificationResult, VerifierSettings, metrics_snapshot, verify_resolution,
)
from app.search.llm_benchmark import _metrics, run_benchmark
from app.search.category_resolver import load_index


@dataclass(frozen=True)
class Suggestion:
    okpd2: str
    confidence: float
    basis: str
    evidence: list[str]
    official_name: str | None = None


@dataclass(frozen=True)
class Resolution:
    state: str
    suggestions: list[Suggestion]
    margin: float | None = None

    @property
    def ranking_code(self) -> str | None:
        return self.suggestions[0].okpd2 if self.state == "RESOLVED" else None


MEDICAL = Suggestion("32.50.30.111", .62, "OFFICIAL_TERMS", [], "Столы смотровые, терапевтические")
OFFICE = Suggestion("31.01.12.110", .59, "OFFICIAL_TERMS", [], "Столы письменные деревянные для офисов, административных помещений")


class FakeProvider:
    name = "fixture"
    model = "fixture-model"

    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    def verify(self, query, candidates):
        self.calls.append((query, candidates))
        if self.error:
            raise self.error
        return self.answer


@pytest.fixture
def settings():
    return VerifierSettings(enabled=True, timeout_seconds=.5)


def result(decision="RESOLVED", code=MEDICAL.okpd2, confidence="HIGH"):
    return VerificationResult(decision=decision, selected_code=code, confidence=confidence,
                              reason="Medical procedures require a medical table.", matched_constraints=["medical use"])


def test_exact_title_and_high_confidence_bypass_provider(settings):
    provider = FakeProvider(result())
    exact = Resolution("CATEGORY_AMBIGUOUS", [Suggestion(MEDICAL.okpd2, .98, "OFFICIAL_EXACT_TITLE", [], MEDICAL.official_name), OFFICE])
    high = Resolution("RESOLVED", [Suggestion(MEDICAL.okpd2, .92, "OFFICIAL_TERMS", [], MEDICAL.official_name), OFFICE], .33)
    assert verify_resolution("exact", exact, provider, settings).resolution is exact
    assert verify_resolution("high", high, provider, settings).resolution is high
    assert provider.calls == []


def test_ambiguous_query_can_select_only_supplied_official_candidate(settings):
    provider = FakeProvider(result())
    original = Resolution("CATEGORY_AMBIGUOUS", [OFFICE, MEDICAL], .03)
    outcome = verify_resolution("Стол для медицинских процедур", original, provider, settings)
    assert outcome.resolution.ranking_code == MEDICAL.okpd2
    assert outcome.resolution.suggestions[0].okpd2 == MEDICAL.okpd2
    assert {c.code for c in provider.calls[0][1]} == {OFFICE.okpd2, MEDICAL.okpd2}
    assert outcome.status == "RESOLVED" and not outcome.fallback_used


def test_medium_uncertain_calls_provider_but_safe_margin_bypasses(settings):
    provider = FakeProvider(result())
    medium = Resolution("CATEGORY_UNCERTAIN", [OFFICE, MEDICAL], .03)
    safe = Resolution("CATEGORY_UNCERTAIN", [OFFICE, MEDICAL], .25)
    assert verify_resolution("Стол для процедур", medium, provider, settings).status == "RESOLVED"
    assert verify_resolution("Стол для процедур", safe, provider, settings).resolution is safe
    assert len(provider.calls) == 1


def test_invented_code_is_rejected_and_original_is_preserved(settings):
    provider = FakeProvider(result(code="99.99.99.999"))
    original = Resolution("CATEGORY_AMBIGUOUS", [OFFICE, MEDICAL], .03)
    outcome = verify_resolution("Стол", original, provider, settings)
    assert outcome.resolution is original and outcome.fallback_used
    assert outcome.status == "INVALID_RESPONSE"


@pytest.mark.parametrize("error", [ValueError("invalid JSON"), httpx.TimeoutException("timeout"), RuntimeError("model unavailable")])
def test_provider_failure_falls_back_without_breaking_search(settings, error):
    original = Resolution("CATEGORY_AMBIGUOUS", [OFFICE, MEDICAL], .03)
    outcome = verify_resolution("Стол", original, FakeProvider(error=error), settings)
    assert outcome.resolution is original and outcome.fallback_used


def test_ambiguous_response_preserves_ambiguity(settings):
    original = Resolution("CATEGORY_AMBIGUOUS", [OFFICE, MEDICAL], .03)
    outcome = verify_resolution("Стол", original, FakeProvider(result("AMBIGUOUS", None, "LOW")), settings)
    assert outcome.resolution is original and outcome.status == "AMBIGUOUS"


@pytest.mark.parametrize("decision, expected_state", [
    ("AMBIGUOUS", "CATEGORY_AMBIGUOUS"),
    ("ABSTAIN", "CATEGORY_UNCERTAIN"),
])
def test_verifier_can_withhold_weak_deterministic_resolution(settings, decision, expected_state):
    original = Resolution("RESOLVED", [MEDICAL, OFFICE], .03)
    outcome = verify_resolution("Стол для процедур", original,
                                FakeProvider(result(decision, None, "LOW")), settings)
    assert outcome.status == decision
    assert outcome.resolution.state == expected_state
    assert outcome.resolution.ranking_code is None


def test_nonsense_query_and_missing_official_names_never_call_provider(settings):
    provider = FakeProvider(result())
    original = Resolution("CATEGORY_UNCERTAIN", [Suggestion("00.00.00.000", .12, "FUZZY", [])])
    assert verify_resolution("xqz", original, provider, settings).resolution is original
    assert provider.calls == []


def test_disabled_verifier_is_noop():
    provider = FakeProvider(result())
    original = Resolution("CATEGORY_AMBIGUOUS", [OFFICE, MEDICAL], .03)
    outcome = verify_resolution("Стол", original, provider, VerifierSettings(enabled=False))
    assert outcome.resolution is original and outcome.status == "BYPASSED"
    assert provider.calls == []


def test_strict_response_schema_rejects_extra_fields_and_inconsistent_code():
    with pytest.raises(ValueError):
        VerificationResult.model_validate({**result().model_dump(), "invented": True})
    with pytest.raises(ValueError):
        result("AMBIGUOUS", MEDICAL.okpd2)


def test_http_provider_rejects_invalid_json_and_uses_strict_schema():
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})
    provider = OpenAICompatibleProvider("https://example.test/v1", "fixture", "secret", .5,
                                       transport=httpx.MockTransport(respond))
    with pytest.raises(ValueError):
        provider.verify("Стол", [])
    assert requests[0]["response_format"]["type"] == "json_schema"
    assert requests[0]["response_format"]["json_schema"]["strict"] is True
    assert "secret" not in json.dumps(requests[0])


def test_http_provider_validates_structured_response():
    def respond(request):
        return httpx.Response(200, json={"model": "fixture", "choices": [{"message": {"content": result().model_dump_json()}}]})
    provider = OpenAICompatibleProvider("https://example.test/v1", "fixture", "secret", .5,
                                       transport=httpx.MockTransport(respond))
    assert provider.verify("Стол", []).selected_code == MEDICAL.okpd2
    assert provider.http_successes == 1 and provider.valid_responses == 1
    assert provider.reported_model_id == "fixture"


def test_benchmark_candidates_are_in_official_index_and_replay_is_labeled():
    path = Path(__file__).resolve().parents[3] / "benchmark/okpd2_llm_verifier/validation.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    index = load_index()
    for case in cases:
        for candidate in case["deterministic"]["candidates"]:
            assert index.codes[candidate["code"]].name == candidate["official_name"]
    from app.search.llm_benchmark import FixtureReplayProvider
    report = run_benchmark(cases, FixtureReplayProvider(), fixture_replay=True)
    assert report["mode"] == "fixture_replay_not_model_accuracy"
    assert report["resolver_v4_plus_llm"]["correct_ambiguity_detection"] == 1


def test_live_benchmark_report_tracks_connection_and_valid_response():
    path = Path(__file__).resolve().parents[3] / "benchmark/okpd2_llm_verifier/validation.json"
    case = json.loads(path.read_text(encoding="utf-8"))[0]
    def respond(request):
        return httpx.Response(200, json={"choices": [{"message": {
            "content": json.dumps(case["fixture_response"]),
        }}]})
    provider = OpenAICompatibleProvider("https://example.test/v1", "qwen/qwen3.8-27b", "secret", .5,
                                       transport=httpx.MockTransport(respond))
    report = run_benchmark([case], provider)
    assert report["provider_connection_successful"] is True
    assert report["model_id"] == "qwen/qwen3.8-27b"
    assert report["valid_structured_output_responses"] == 1
    assert report["timeout_rate"] == 0 and report["invalid_response_rate"] == 0
    assert report["cases"][0]["verified_code"] == MEDICAL.okpd2


def test_benchmark_percentiles_use_interpolation():
    measurements = [(None, None, ms) for ms in [100.0, 200.0, 300.0, 400.0]]
    stats = _metrics(measurements)
    assert stats["p50_latency_ms"] == 250.0
    assert stats["p95_latency_ms"] == pytest.approx(385.0)


def test_metrics_include_call_rate_latency_and_timeout(settings):
    original = Resolution("CATEGORY_AMBIGUOUS", [OFFICE, MEDICAL], .03)
    verify_resolution("Стол", original, FakeProvider(error=httpx.TimeoutException("timeout")), settings)
    snapshot = metrics_snapshot()
    assert snapshot["call_rate"] >= 0
    assert snapshot["p50_latency_ms"] is not None
    assert snapshot["p95_latency_ms"] is not None
    assert snapshot["timeout_rate"] > 0
