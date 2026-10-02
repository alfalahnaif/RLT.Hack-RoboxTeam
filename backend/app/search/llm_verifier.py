"""Optional, closed-world OKPD2 verification after deterministic classification.

This module accepts the published Resolver V4 result contract. It never adds a
candidate; a failed or unsupported answer returns the exact original result.
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass, replace
from typing import Literal, Protocol, Sequence

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerificationCandidate:
    code: str
    official_name: str
    score: float
    basis: str


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    decision: Literal["RESOLVED", "AMBIGUOUS", "ABSTAIN"]
    selected_code: str | None
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    reason: str = Field(min_length=1, max_length=300)
    matched_constraints: list[str] = Field(max_length=8)

    @model_validator(mode="after")
    def selection_matches_decision(self) -> "VerificationResult":
        if (self.decision == "RESOLVED") != (self.selected_code is not None):
            raise ValueError("selected_code is required only for RESOLVED")
        if self.decision == "RESOLVED" and self.confidence == "LOW":
            raise ValueError("LOW confidence cannot resolve a category")
        if any(not item.strip() or len(item) > 120 for item in self.matched_constraints):
            raise ValueError("matched_constraints must be short nonempty strings")
        return self


class LlmVerifierProvider(Protocol):
    name: str
    model: str

    def verify(self, query: str, candidates: Sequence[VerificationCandidate]) -> VerificationResult: ...


@dataclass(frozen=True)
class VerifierSettings:
    enabled: bool = False
    timeout_seconds: float = .65

    @classmethod
    def from_env(cls) -> "VerifierSettings":
        enabled = os.getenv("OKPD2_LLM_VERIFIER_ENABLED", "0") == "1"
        try:
            timeout = float(os.getenv("OKPD2_LLM_TIMEOUT_SECONDS", ".65"))
        except ValueError:
            timeout = .65
        if not math.isfinite(timeout):
            timeout = .65
        return cls(enabled=enabled, timeout_seconds=min(max(timeout, .1), 2.0))


class OpenAICompatibleProvider:
    """One replaceable transport adapter; HTTP and model credentials come from env."""

    name = "openai-compatible"

    def __init__(self, base_url: str, model: str, api_key: str, timeout_seconds: float,
                 transport: httpx.BaseTransport | None = None):
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._key = api_key
        self._timeout = timeout_seconds
        self._transport = transport
        self.http_successes = 0
        self.valid_responses = 0
        self.reported_model_id: str | None = None

    def verify(self, query: str, candidates: Sequence[VerificationCandidate]) -> VerificationResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({
                    "query": query,
                    "official_candidates": [vars(candidate) for candidate in candidates],
                }, ensure_ascii=False)},
            ],
            "temperature": 0,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "okpd2_verification", "strict": True, "schema": VerificationResult.model_json_schema(),
            }},
        }
        with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
            response = client.post(self._url, headers={"Authorization": f"Bearer {self._key}"}, json=payload)
            response.raise_for_status()
        self.http_successes += 1
        body = response.json()
        self.reported_model_id = body.get("model") if isinstance(body, dict) else None
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("provider returned no JSON content")
        result = VerificationResult.model_validate_json(content)
        self.valid_responses += 1
        return result


SYSTEM_PROMPT = (
    "You verify an OKPD2 category using only the supplied official_candidates. "
    "The candidate list is authoritative: never invent or change a code. "
    "Use the full procurement intent, product purpose, use, and context. "
    "Match at the official category level: a category title need not repeat every product specification "
    "(such as adjustability) when the product purpose clearly fits. "
    "Do not choose the first candidate merely because it is ranked first. "
    "Return AMBIGUOUS if the query lacks the details needed to distinguish candidates; "
    "return ABSTAIN if none is supported. Prefer uncertainty over unsupported certainty. "
    "Give only a short user-facing reason and concise matched constraints; no hidden reasoning."
)


def provider_from_env(settings: VerifierSettings) -> LlmVerifierProvider:
    model = os.getenv("OKPD2_LLM_MODEL", "")
    key = os.getenv("OKPD2_LLM_API_KEY", "")
    url = os.getenv("OKPD2_LLM_BASE_URL", "https://api.openai.com/v1")
    if not model or not key or not url.startswith("https://"):
        raise ValueError("LLM provider configuration missing or insecure")
    return OpenAICompatibleProvider(url, model, key, settings.timeout_seconds)


@dataclass(frozen=True)
class VerificationOutcome:
    resolution: object
    status: str
    fallback_used: bool
    latency_ms: float = 0.0
    reason: str | None = None
    failure_code: str | None = None


class _Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.searches = 0
        self.calls = 0
        self.timeouts = 0
        self.latencies: list[float] = []

    def record(self, *, called: bool, latency_ms: float = 0.0, timed_out: bool = False) -> None:
        with self.lock:
            self.searches += 1
            if called:
                self.calls += 1
                self.latencies.append(latency_ms)
            if timed_out:
                self.timeouts += 1

    def snapshot(self) -> dict:
        with self.lock:
            ordered = sorted(self.latencies)
            percentile = lambda q: ordered[min(len(ordered) - 1, round((len(ordered) - 1) * q))] if ordered else None
            return {"searches": self.searches, "calls": self.calls,
                    "call_rate": self.calls / self.searches if self.searches else 0.0,
                    "p50_latency_ms": percentile(.5), "p95_latency_ms": percentile(.95),
                    "timeout_rate": self.timeouts / self.calls if self.calls else 0.0}


_metrics = _Metrics()


def metrics_snapshot() -> dict:
    """Process-local measurements for monitoring; restart resets the counters."""
    return _metrics.snapshot()


def _official_name(suggestion: object, index: object | None) -> str | None:
    name = getattr(suggestion, "official_name", None)
    if name:
        return name
    if index is None:
        return None
    row = getattr(index, "codes", {}).get(suggestion.okpd2)
    return row.get("name") if isinstance(row, dict) else getattr(row, "name", None)


def _candidates(resolution: object, index: object | None) -> list[VerificationCandidate]:
    unique: dict[str, VerificationCandidate] = {}
    for suggestion in resolution.suggestions:
        name = _official_name(suggestion, index)
        if name and suggestion.okpd2 not in unique:
            unique[suggestion.okpd2] = VerificationCandidate(
                suggestion.okpd2, name, suggestion.confidence, suggestion.basis)
    return list(unique.values())


def _eligible(resolution: object, candidates: list[VerificationCandidate]) -> bool:
    if len(candidates) < 2 or any(c.basis == "OFFICIAL_EXACT_TITLE" for c in candidates):
        return False
    if resolution.state == "CATEGORY_AMBIGUOUS":
        return True
    if resolution.state not in {"CATEGORY_UNCERTAIN", "RESOLVED"}:
        return False
    top = candidates[0].score
    margin = getattr(resolution, "margin", None)
    if margin is None:
        margin = top - candidates[1].score
    return .4 <= top < .85 and margin < .18


def _audit(query: str, candidates: list[VerificationCandidate], provider: LlmVerifierProvider | None,
           outcome: VerificationOutcome, decision: VerificationResult | None) -> None:
    log.info("okpd2_llm_verification %s", json.dumps({
        "query": query, "deterministic_candidates": [vars(c) for c in candidates],
        "decision": decision.decision if decision else None,
        "selected_code": decision.selected_code if decision else None,
        "reason": decision.reason if decision else None,
        "matched_constraints": decision.matched_constraints if decision else [],
        "provider": provider.name if provider else None, "model": provider.model if provider else None,
        "latency_ms": round(outcome.latency_ms, 1), "fallback_used": outcome.fallback_used,
        "status": outcome.status, "failure_code": outcome.failure_code,
    }, ensure_ascii=False))


def verify_resolution(query: str, resolution: object, provider: LlmVerifierProvider | None = None,
                      settings: VerifierSettings | None = None, index: object | None = None) -> VerificationOutcome:
    """Apply an optional verifier and return the original resolver result on any failure."""
    settings = settings or VerifierSettings.from_env()
    candidates = _candidates(resolution, index)
    if not settings.enabled or not _eligible(resolution, candidates):
        _metrics.record(called=False)
        return VerificationOutcome(resolution, "BYPASSED", False)

    started = time.perf_counter()
    decision = None
    called = False
    try:
        provider = provider or provider_from_env(settings)
        called = True
        decision = provider.verify(query, candidates)
        if not isinstance(decision, VerificationResult):
            raise ValueError("provider did not return a validated result")
        if decision.decision == "RESOLVED" and decision.selected_code not in {c.code for c in candidates}:
            raise ValueError("selected code is not a supplied official candidate")
        if decision.decision == "RESOLVED":
            selected = next(s for s in resolution.suggestions if s.okpd2 == decision.selected_code)
            reordered = [selected] + [s for s in resolution.suggestions if s.okpd2 != decision.selected_code]
            updated = replace(resolution, state="RESOLVED", suggestions=reordered)
            outcome = VerificationOutcome(updated, "RESOLVED", False, reason=decision.reason)
        elif resolution.state == "RESOLVED":
            state = "CATEGORY_AMBIGUOUS" if decision.decision == "AMBIGUOUS" else "CATEGORY_UNCERTAIN"
            outcome = VerificationOutcome(replace(resolution, state=state), decision.decision, False,
                                          reason=decision.reason)
        else:
            outcome = VerificationOutcome(resolution, decision.decision, False, reason=decision.reason)
    except Exception as exc:
        status = ("CONFIGURATION_ERROR" if not called else "TIMEOUT" if isinstance(exc, httpx.TimeoutException)
                  else "INVALID_RESPONSE" if isinstance(exc, ValueError) else "PROVIDER_ERROR")
        failure_code = f"HTTP_{exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
        outcome = VerificationOutcome(resolution, status, True, failure_code=failure_code)
    latency = (time.perf_counter() - started) * 1000
    outcome = replace(outcome, latency_ms=latency)
    _metrics.record(called=called, latency_ms=latency, timed_out=outcome.status == "TIMEOUT")
    _audit(query, candidates, provider, outcome, decision)
    return outcome
