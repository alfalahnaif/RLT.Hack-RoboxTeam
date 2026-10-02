"""P5-001A.1: official EGRUL is the primary identity source (search + extract); checko.ru is an optional secondary provider
behind a circuit breaker. Pure tests: fake fetcher / providers, fixed clock, no network, no database."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.enrichment import pipeline as P
from app.enrichment import providers as PR
from app.enrichment.profile_models import (EnrichmentStatus, SourceOutcome, SourceRateLimited, SourceSkipped, SourceType,
                                           SourceUnavailable)
from tests.enrichment.fakes import INN, NOW, OGRN, FakeRegistry, clock, identity, providers, site_pages

# Layout of a real extract as pypdf renders it: numbered rows, a page footer in the middle of a field, spaced INN digits.
EXTRACT = f"""ВЫПИСКА
из Единого государственного реестра юридических лиц
ОГРН {' '.join(OGRN)}
ИНН {' '.join(INN)}
Место нахождения и адрес юридического лица
5 Адрес юридического лица 123456,
Г.МОСКВА,
Страница 1 из 9
Выписка из ЕГРЮЛ
02.10.2026 10:00 ОГРН {OGRN}
УЛ. МОЛОЧНАЯ,
Д. 1
6 ГРН и дата внесения в ЕГРЮЛ записи,
Сведения об основном виде деятельности
ОКВЭД ОК 029-2014 (КДЕС Ред. 2)
44 Код и наименование вида деятельности 10.51.9 Производство прочей молочной
продукции
45 ГРН и дата внесения в ЕГРЮЛ записи,
Сведения о дополнительных видах деятельности
46 Код и наименование вида деятельности 46.33 Торговля оптовая молочными продуктами
47 ГРН и дата внесения в ЕГРЮЛ записи,
"""


def test_extract_gives_address_and_primary_okved_across_page_breaks():
    address, okved = PR.parse_egrul_extract(EXTRACT, INN, NOW)
    assert address.value == "123456, Г.МОСКВА, УЛ. МОЛОЧНАЯ, Д. 1"
    assert okved.value == "10.51.9 Производство прочей молочной продукции"      # the primary one, not an additional one
    assert address.source_type == okved.source_type == SourceType.FNS_EGRUL and address.checked_at == NOW


def test_extract_of_another_inn_is_rejected():
    with pytest.raises(PR.ExtractMismatch):
        PR.parse_egrul_extract(EXTRACT, "7709999999", NOW)


def test_extract_identity_never_comes_from_a_persons_inn_row():
    """Real layout seen in the pilot: no INN in the header, a founder's personal INN row first, the company INN row later."""
    no_header = EXTRACT.replace(f"ИНН {' '.join(INN)}\n", "")
    person_first = no_header.replace("Сведения об основном", "17 ИНН 780536293060\nСведения об основном", 1)
    with_row = person_first + f"37 ИНН юридического лица {INN}\n"
    assert PR.parse_egrul_extract(with_row, INN, NOW)[0] is not None
    assert PR.parse_egrul_extract(person_first, INN, NOW, ogrn=OGRN)[1] is not None     # header OGRN confirms identity
    with pytest.raises(PR.ExtractMismatch):
        PR.parse_egrul_extract(person_first, INN, NOW)                                   # nothing confirms it
    with pytest.raises(PR.ExtractMismatch):
        PR.parse_egrul_extract(with_row, INN, NOW, ogrn="1027709999999")               # contradicting OGRN


def test_extract_without_the_sections_gives_no_values():
    assert PR.parse_egrul_extract(f"ИНН {' '.join(INN)}\n", INN, NOW) == (None, None)


def test_unreadable_pdf_is_a_source_failure():
    with pytest.raises(SourceUnavailable):
        PR.pdf_text(b"not a pdf")


class FakeFetcher:
    """egrul.nalog.ru endpoints: token -> search result -> extract request / status / download."""

    def __init__(self, extract_error: Exception | None = None, rows=None):
        self.extract_error, self.calls = extract_error, []
        self.rows = rows if rows is not None else [{"i": INN, "n": 'ООО "ТЕСТ"', "c": 'ООО "ТЕСТ"', "o": OGRN, "p": "770101001",
                                                    "r": "04.11.2002", "rn": "Москва", "k": "ul", "t": "ROWTOKEN"}]

    def post(self, url, data):
        self.calls.append(url)
        return url, json.dumps({"t": "SEARCHTOKEN", "captchaRequired": False})

    def get(self, url):
        self.calls.append(url)
        if "search-result" in url:
            return url, json.dumps({"rows": self.rows})
        if self.extract_error:
            raise self.extract_error
        if "vyp-request" in url:
            return url, json.dumps({"t": "X", "captchaRequired": False})
        return url, json.dumps({"status": "ready"})

    def get_bytes(self, url):
        self.calls.append(url)
        return b"%PDF"


@pytest.fixture
def extract_text(monkeypatch):
    monkeypatch.setattr(PR, "pdf_text", lambda data: EXTRACT)


def test_official_egrul_alone_gives_identity_address_and_okved(extract_text):
    ident = PR.FnsEgrulRegistry(FakeFetcher(), clock()).lookup_by_inn(INN)
    assert ident.legal_name.source_type == SourceType.FNS_EGRUL and ident.ogrn.value == OGRN and ident.kpp.value == "770101001"
    assert ident.registered_address.value.startswith("123456") and ident.primary_okved.value.startswith("10.51.9")
    assert ident.registered_address.source_type == ident.primary_okved.source_type == SourceType.FNS_EGRUL
    assert [(a.source, a.outcome) for a in ident.sub_attempts] == [("FNS_EGRUL_EXTRACT", SourceOutcome.OK)]


def test_entrepreneur_extract_gives_okved_but_never_an_address(extract_text):
    rows = [{"i": INN, "n": "ИВАНОВ ИВАН ИВАНОВИЧ", "o": OGRN, "k": "fl", "t": "ROWTOKEN"}]   # same record as the extract
    ident = PR.FnsEgrulRegistry(FakeFetcher(rows=rows), clock()).lookup_by_inn(INN)
    assert ident.entity_kind == "INDIVIDUAL_ENTREPRENEUR" and ident.registered_address is None and ident.primary_okved


def test_extract_failure_keeps_identity_and_is_recorded(extract_text):
    ident = PR.FnsEgrulRegistry(FakeFetcher(SourceRateLimited("HTTP 429 after one backoff")), clock()).lookup_by_inn(INN)
    assert ident.legal_name and ident.registered_address is None and ident.primary_okved is None
    assert [(a.source, a.outcome) for a in ident.sub_attempts] == [("FNS_EGRUL_EXTRACT", SourceOutcome.RATE_LIMITED)]
    res = P.enrich(INN, providers(ident), clock())
    assert res.status == EnrichmentStatus.PARTIAL and res.retryable and "EGRUL_EXTRACT_UNAVAILABLE" in res.reasons
    assert ("FNS_EGRUL_EXTRACT", SourceOutcome.RATE_LIMITED) in [(a.source, a.outcome) for a in res.attempts]


def _egrul_identity():
    """What the official path returns: every legal field from FNS_EGRUL, no website hint (EGRUL publishes none)."""
    base = identity()

    def fns(s):
        return replace(s, source_url=PR.EGRUL_PUBLIC_URL, source_type=SourceType.FNS_EGRUL)
    return replace(base, registered_address=fns(base.registered_address), primary_okved=fns(base.primary_okved), website_hints=())


class CountingMirror:
    name = "CHECKO_REGISTRY_MIRROR"

    def __init__(self, error=None, result=None):
        self.error, self.result, self.calls = error, result, 0

    def lookup_by_inn(self, inn):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def test_checko_rate_limited_does_not_fail_the_supplier():
    mirror = CountingMirror(SourceRateLimited("HTTP 429 after one backoff"))
    res = P.enrich(INN, providers(_egrul_identity(), mirror=mirror), clock())
    assert res.status == EnrichmentStatus.PARTIAL and res.retryable
    assert "REGISTRY_MIRROR_RATE_LIMITED" in res.reasons and "SOURCE_UNAVAILABLE" not in res.reasons
    assert res.identity.registered_address.source_type == SourceType.FNS_EGRUL
    assert res.identity.primary_okved.source_type == SourceType.FNS_EGRUL
    assert ("CHECKO_REGISTRY_MIRROR", SourceOutcome.RATE_LIMITED) in [(a.source, a.outcome) for a in res.attempts]
    assert any(r.basis == "OKVED_PRIMARY" for r in res.roles)          # role evidence from the official OKVED alone


def test_official_fields_win_over_the_mirror_and_mirror_only_adds_the_website_hint():
    mirror_ident = replace(identity(), registered_address=replace(identity().registered_address, value="другой адрес"))
    res = P.enrich(INN, providers(_egrul_identity(), pages=site_pages(), mirror=FakeRegistry("CHECKO_REGISTRY_MIRROR", mirror_ident)),
                   clock())
    assert res.identity.registered_address.source_type == SourceType.FNS_EGRUL
    assert res.identity.registered_address.value != "другой адрес"
    assert res.status == EnrichmentStatus.COMPLETE and not res.retryable      # the website hint came from the mirror


def test_official_registry_down_and_mirror_rate_limited_is_failed_retryable():
    res = P.enrich(INN, providers(registry_error=True, mirror=CountingMirror(SourceRateLimited("429"))), clock())
    assert res.status == EnrichmentStatus.FAILED and res.retryable and res.reasons == ["SOURCE_UNAVAILABLE"]


# ------------------------------------------------------------------------------------------------------------ circuit breaker
def test_breaker_stops_calling_a_rate_limited_mirror_for_the_rest_of_the_batch():
    inner = CountingMirror(SourceRateLimited("HTTP 429"))
    breaker = PR.CircuitBreaker(threshold=2, cooldown_s=None)
    guarded = PR.GuardedRegistry(inner, breaker)
    outcomes = []
    for _ in range(5):
        res = P.enrich(INN, providers(_egrul_identity(), mirror=guarded), clock())
        outcomes.append(next(a.outcome for a in res.attempts if a.source == "CHECKO_REGISTRY_MIRROR"))
        assert res.status == EnrichmentStatus.PARTIAL                       # the supplier never fails because of the mirror
    assert inner.calls == 2 and breaker.skipped == 3
    assert outcomes == [SourceOutcome.RATE_LIMITED] * 2 + [SourceOutcome.SKIPPED] * 3
    assert "REGISTRY_MIRROR_SKIPPED" in res.reasons


def test_breaker_counts_only_consecutive_rate_limits_and_half_opens_after_cooldown():
    t = [0.0]
    breaker = PR.CircuitBreaker(threshold=2, cooldown_s=60, clock=lambda: t[0])
    breaker.record(True)
    breaker.record(False)              # a success in between resets the streak
    breaker.record(True)
    assert not breaker.is_open
    breaker.record(True)
    assert breaker.is_open
    t[0] = 61
    assert not breaker.is_open         # cooldown over: the next call probes the source again
    inner = CountingMirror(SourceUnavailable("timeout"))
    guarded = PR.GuardedRegistry(inner, PR.CircuitBreaker(threshold=2, cooldown_s=None))
    for _ in range(3):
        with pytest.raises(SourceUnavailable) as e:
            guarded.lookup_by_inn(INN)
        assert not isinstance(e.value, SourceSkipped)       # plain outages do not open the breaker
    assert inner.calls == 3
