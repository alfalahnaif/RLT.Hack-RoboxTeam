"""P5-001A identity-first enrichment pipeline: parsers, identity verification, contacts, freshness, roles, statuses.
Pure and deterministic (fake providers, fixed clock, no network, no database)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.enrichment import freshness as F
from app.enrichment import pipeline as P
from app.enrichment.profile_models import (ContactType, EnrichmentStatus, Page, Role, RoleStatus, SourceOutcome, SourceType,
                                           WebsiteConfidence, WebsiteVerification)
from app.enrichment.providers import (HtmlContactExtractor, SiteAndOkvedRoleEvidence, assess_identity, html_to_text,
                                      latest_year, merge_identities, normalize_phone, parse_checko, parse_egrul_rows)
from tests.enrichment.fakes import (CHECKO_URL, INN, NOW, OGRN, FakeRegistry, clock, identity, providers, site_pages)


# ------------------------------------------------------------------------------------------------------------ registry parsers
def test_egrul_parser_reads_identity_and_never_the_director():
    payload = {"rows": [
        {"i": INN, "n": "ООО СТАРОЕ", "o": "1027700000000", "e": "01.01.2015", "k": "ul"},
        {"i": INN, "n": 'ОБЩЕСТВО "ТЕСТ"', "c": 'ООО "ТЕСТ"', "o": OGRN, "p": "770101001", "r": "04.11.2002", "rn": "Москва",
         "g": "ДИРЕКТОР: Иванов Иван Иванович", "k": "ul"},
        {"i": "9999999999", "n": "ДРУГАЯ"}]}
    ident = parse_egrul_rows(payload, INN, NOW)
    assert ident.legal_name.value == 'ОБЩЕСТВО "ТЕСТ"' and ident.ogrn.value == OGRN and ident.kpp.value == "770101001"
    assert ident.legal_status.value == "ACTIVE" and ident.registration_date == date(2002, 11, 4)
    assert ident.legal_name.source_type == SourceType.FNS_EGRUL and ident.legal_name.checked_at == NOW
    assert "Иванов" not in repr(ident)
    assert parse_egrul_rows({"rows": []}, INN, NOW) is None


def test_egrul_ceased_and_individual_entrepreneur():
    ceased = parse_egrul_rows({"rows": [{"i": INN, "n": "X", "o": OGRN, "e": "01.02.2020", "k": "ul"}]}, INN, NOW)
    assert ceased.legal_status.value == "CEASED"
    ip = parse_egrul_rows({"rows": [{"i": "770123456789", "n": "ИП Петров", "o": "304770000000001", "k": "fl"}]}, "770123456789", NOW)
    assert ip.entity_kind == "INDIVIDUAL_ENTREPRENEUR" and ip.kpp is None


CHECKO_HTML = """<script type='application/ld+json'>{"@type":"Organization","name":"ООО \\"ТМЗ\\"","legalName":"ООО ТЕСТОВЫЙ",
"taxID":"%s","identifier":[{"propertyID":"ОГРН","value":"%s"},{"propertyID":"КПП","value":"770101001"}],
"address":{"addressRegion":"Москва"},"telephone":"+79161234567","email":"person@mail.ru"}</script>
<div class="text-success fw-600">Действующая компания</div>
<span id="copy-address" class="copy">123456, г. Москва, ул. Молочная, д. 1</span>
<tr> <td class="w-5">10.51.9</td> <td><a class="link" href="/x">Производство прочей молочной продукции</a><span class="question" data-bs-toggle="tooltip" data-bs-animation="false" data-bs-title="Основной вид деятельности"></span></td></tr>
<strong class="fw-700 d-block mt-3 mb-1">Веб-сайт</strong> <a class="link" target="_blank" href="https://moloko-test.ru">moloko-test.ru</a>"""


def test_checko_mirror_parser_requires_matching_inn_and_ignores_aggregated_contacts():
    ident = parse_checko(CHECKO_HTML % (INN, OGRN), INN, CHECKO_URL, NOW)
    assert ident.registered_address.value == "123456, г. Москва, ул. Молочная, д. 1"
    assert ident.primary_okved.value == "10.51.9 Производство прочей молочной продукции"
    assert ident.legal_status.value == "ACTIVE" and ident.region.value == "Москва"
    assert [h.value for h in ident.website_hints] == ["https://moloko-test.ru"]
    assert ident.registered_address.source_type == SourceType.FNS_EGRUL_DERIVED_REGISTRY
    assert "person@mail.ru" not in repr(ident) and "79161234567" not in repr(ident)
    assert parse_checko(CHECKO_HTML % ("7700000000", OGRN), INN, CHECKO_URL, NOW) is None


def test_mirror_with_contradicting_ogrn_is_rejected():
    primary = identity(site=None, okved=None)
    mirror = parse_checko(CHECKO_HTML % (INN, "1111111111111"), INN, CHECKO_URL, NOW)
    merged, conflict = merge_identities(primary, mirror)
    assert conflict == "MIRROR_OGRN_MISMATCH" and merged is primary
    merged, conflict = merge_identities(primary, parse_checko(CHECKO_HTML % (INN, OGRN), INN, CHECKO_URL, NOW))
    assert conflict is None and merged.primary_okved and merged.legal_name.source_type == SourceType.FNS_EGRUL


# ------------------------------------------------------------------------------------------------------------ website identity
def _pages(d):
    return [Page(u, h, html_to_text(h)) for u, h in d.items()]


def test_official_website_requires_requisites_on_site():
    conf, signals = assess_identity(identity(), _pages(site_pages()))
    assert conf == WebsiteConfidence.HIGH and {"INN_ON_SITE", "OGRN_ON_SITE"} <= set(signals)


def test_similar_name_alone_is_rejected():
    similar = {"https://moloko-test.ru/": "<p>Молочный завод «Тестовый-Плюс», г. Тверь</p>"}
    conf, _ = assess_identity(identity(), _pages(similar))
    assert conf == WebsiteConfidence.LOW


def test_exact_name_and_locality_without_requisites_is_medium_not_official():
    pages = {"https://moloko-test.ru/": '<p>ООО «Тестовый молочный завод», г. Москва</p>'}
    conf, signals = assess_identity(identity(), _pages(pages))
    assert conf == WebsiteConfidence.MEDIUM and set(signals) == {"EXACT_LEGAL_NAME", "REGISTERED_LOCALITY"}


def test_exact_name_and_registered_street_address_is_official():
    pages = {"https://moloko-test.ru/": '<p>ООО «Тестовый молочный завод»</p><p>Адрес: Москва, улица Молочная, дом 1</p>'}
    conf, signals = assess_identity(identity(), _pages(pages))
    assert conf == WebsiteConfidence.HIGH and "REGISTERED_STREET_ADDRESS" in signals
    wrong_house = {"https://moloko-test.ru/": '<p>ООО «Тестовый молочный завод»</p><p>г. Москва, ул. Молочная, д. 15</p>'}
    assert assess_identity(identity(), _pages(wrong_house))[0] == WebsiteConfidence.MEDIUM
    address_only = {"https://moloko-test.ru/": '<p>Магазин «Сыр», г. Москва, ул. Молочная, д. 1</p>'}
    assert assess_identity(identity(), _pages(address_only))[0] == WebsiteConfidence.LOW


def test_requisites_links_are_prioritised():
    from app.enrichment.providers import contact_links
    html = ('<a href="/about/">О компании</a><a href="https://other.ru/contacts">x</a><a href="/contacts/">Контакты</a>'
            '<a href="/rekvizity/">Реквизиты</a><a href="/privacy/">Политика конфиденциальности</a>')
    assert contact_links("https://moloko-test.ru/", html, 3) == ["https://moloko-test.ru/rekvizity/",
                                                                 "https://moloko-test.ru/contacts/",
                                                                 "https://moloko-test.ru/privacy/"]


def test_other_company_inn_on_site_does_not_verify():
    conf, _ = assess_identity(identity(), _pages(site_pages(inn="7709999999", ogrn="1027709999999")))
    assert conf != WebsiteConfidence.HIGH


# ------------------------------------------------------------------------------------------------------------ contacts
def _verified(pages=None, t=NOW, conf=WebsiteConfidence.HIGH):
    ps = _pages(pages or site_pages())
    return WebsiteVerification("https://moloko-test.ru", conf, ("INN_ON_SITE",), ps[0].url if conf == WebsiteConfidence.HIGH else None,
                               tuple(ps), latest_year(ps, t.date()), t)


def test_contacts_have_provenance_and_personal_values_are_dropped():
    cs = HtmlContactExtractor().extract(identity(), _verified())
    by = {c.type: c for c in reversed(cs)}         # first contact of each type
    assert by[ContactType.PHONE].value == "+7 (495) 123-45-67" and by[ContactType.PHONE].normalized == "74951234567"
    assert by[ContactType.EMAIL].value == "sales@moloko-test.ru"
    assert by[ContactType.WEBSITE].value == "https://moloko-test.ru/"
    for c in cs:
        assert c.source_url.startswith("https://moloko-test.ru/") and c.source_type == SourceType.FIRST_PARTY
        assert c.checked_at == NOW and c.verified and c.content_currency == F.CURRENT
    assert by[ContactType.PHONE].source_url == "https://moloko-test.ru/contacts/"
    values = " ".join(c.value for c in cs)
    assert "765-43-21" not in values and "ivanov" not in values    # director's mobile / personal e-mail never stored
    assert "kamenev" not in values                                   # person-like mailbox on the company domain
    phones = [c.normalized for c in cs if c.type == ContactType.PHONE]
    assert phones == ["74951234567", "79174701108"]                  # landline first, then the published mobile


def test_no_contacts_from_unverified_site():
    assert HtmlContactExtractor().extract(identity(), _verified(conf=WebsiteConfidence.MEDIUM)) == []


def test_phone_normalization():
    assert normalize_phone("8 (816) 642-80-88") == "78166428088" == normalize_phone("+7-816-642-8088")
    assert normalize_phone("123-45") is None


# ------------------------------------------------------------------------------------------------------------ freshness
def test_freshness_retrieved_today_is_not_fresh_when_page_is_outdated():
    assert F.content_currency(2011, date(2026, 10, 2)) == F.OUTDATED
    assert F.contact_freshness(NOW, F.OUTDATED, NOW.date()) == F.STALE
    assert F.contact_freshness(NOW, F.UNDATED, NOW.date()) == F.UNKNOWN
    assert F.contact_freshness(NOW, F.CURRENT, NOW.date()) == F.FRESH
    assert F.contact_freshness(NOW - timedelta(days=400), F.CURRENT, NOW.date()) == F.STALE
    assert F.contact_freshness(None, F.CURRENT, NOW.date()) == F.UNKNOWN
    assert F.content_currency(None, NOW.date()) == F.UNDATED and F.content_currency(2025, NOW.date()) == F.CURRENT


def test_undated_site_gives_unknown_freshness():
    pages = {u: h.replace("© 2014–2026", "") for u, h in site_pages().items()}
    cs = HtmlContactExtractor().extract(identity(), _verified(pages))
    assert {c.content_currency for c in cs} == {F.UNDATED}


def test_cache_policy():
    t = NOW
    assert F.cache_reusable("COMPLETE", False, t - timedelta(days=3), t, t)
    assert not F.cache_reusable("COMPLETE", False, t - timedelta(days=60), t, t)
    assert F.cache_reusable("FAILED", False, None, t - timedelta(days=60), t)          # not retryable: never re-query blindly
    assert F.cache_reusable("FAILED", True, None, t - timedelta(hours=1), t)
    assert not F.cache_reusable("FAILED", True, None, t - timedelta(hours=30), t)
    assert not F.cache_reusable("IN_PROGRESS", False, None, t - timedelta(hours=1), t)  # abandoned run
    assert not F.cache_reusable("NOT_ENRICHED", False, None, None, t)
    # a PARTIAL caused by a source outage is re-attempted after the retry delay, not kept for the whole profile TTL
    assert F.cache_reusable("PARTIAL", True, t - timedelta(hours=1), t, t)
    assert not F.cache_reusable("PARTIAL", True, t - timedelta(hours=30), t, t)
    assert F.cache_reusable("PARTIAL", False, t - timedelta(days=3), t, t)


# ------------------------------------------------------------------------------------------------------------ roles
def test_okved_alone_is_only_inferred_and_site_claims_need_review():
    roles = SiteAndOkvedRoleEvidence().collect(identity(), _verified())
    by = {(r.role, r.basis): r for r in roles}
    okv = by[(Role.MANUFACTURER, "OKVED_PRIMARY")]
    assert okv.status == RoleStatus.INFERRED and okv.source_url == CHECKO_URL
    claim = by[(Role.MANUFACTURER, "FIRST_PARTY_PRODUCTION_CLAIM")]
    assert claim.status == RoleStatus.UNDER_REVIEW and "Собственное производство" in claim.claim
    assert all(r.status != RoleStatus.VERIFIED for r in roles)


def test_no_role_is_forced():
    roles = SiteAndOkvedRoleEvidence().collect(identity(okved="62.01 Разработка компьютерного программного обеспечения"), None)
    assert roles == []
    whole = SiteAndOkvedRoleEvidence().collect(identity(okved="46.33 Торговля оптовая молочными продуктами"), None)
    assert [(r.role, r.status) for r in whole] == [(Role.DISTRIBUTOR, RoleStatus.INFERRED)]


# ------------------------------------------------------------------------------------------------------------ pipeline statuses
def test_known_supplier_complete():
    res = P.enrich(INN, providers(identity(), pages=site_pages()), clock())
    assert res.status == EnrichmentStatus.COMPLETE and res.website.official_url == "https://moloko-test.ru/"
    types = {c.type for c in res.contacts}
    assert types == {ContactType.PHONE, ContactType.EMAIL, ContactType.WEBSITE, ContactType.ADDRESS}
    assert res.content_currency == F.CURRENT
    assert {e.evidence_type for e in res.evidence} >= {"LEGAL_IDENTITY", "WEBSITE_IDENTITY", "OKVED_PRIMARY"}
    assert all(e.source_url and e.checked_at for e in res.evidence)


def test_legal_identity_only_is_partial():
    res = P.enrich(INN, providers(identity(site=None)), clock())
    assert res.status == EnrichmentStatus.PARTIAL and "NO_WEBSITE_CANDIDATE" in res.reasons
    assert {c.type for c in res.contacts} == {ContactType.ADDRESS}       # phone / e-mail stay absent (null in the API)


def test_candidate_website_rejected_when_identity_does_not_match():
    res = P.enrich(INN, providers(identity(), pages=site_pages(inn="7709999999", ogrn="1027709999999")), clock())
    assert res.status == EnrichmentStatus.PARTIAL and "WEBSITE_IDENTITY_NOT_CONFIRMED" in res.reasons
    assert res.website.official_url is None
    assert not any(c.type in (ContactType.PHONE, ContactType.EMAIL, ContactType.WEBSITE) for c in res.contacts)
    assert any(a.outcome == SourceOutcome.REJECTED for a in res.attempts)


def test_unreachable_website_is_partial_with_source_failure():
    res = P.enrich(INN, providers(identity(), site_error=True), clock())
    assert res.status == EnrichmentStatus.PARTIAL and "WEBSITE_UNAVAILABLE" in res.reasons
    assert any(a.outcome == SourceOutcome.UNAVAILABLE for a in res.attempts)


def test_registry_unavailable_is_failed_retryable():
    res = P.enrich(INN, providers(registry_error=True), clock())
    assert res.status == EnrichmentStatus.FAILED and res.retryable and res.reasons == ["SOURCE_UNAVAILABLE"]


def test_unknown_inn_is_failed_not_retryable():
    res = P.enrich(INN, providers(None), clock())
    assert res.status == EnrichmentStatus.FAILED and not res.retryable and "REGISTRY_NOT_FOUND" in res.reasons


def test_mirror_used_when_official_registry_down():
    mirror = FakeRegistry("CHECKO_REGISTRY_MIRROR", parse_checko(CHECKO_HTML % (INN, OGRN), INN, CHECKO_URL, NOW))
    res = P.enrich(INN, providers(registry_error=True, mirror=mirror), clock())
    assert res.status in (EnrichmentStatus.PARTIAL, EnrichmentStatus.COMPLETE)
    assert "PRIMARY_REGISTRY_UNAVAILABLE_MIRROR_USED" in res.reasons
    assert res.identity.legal_name.source_type == SourceType.FNS_EGRUL_DERIVED_REGISTRY


def test_individual_entrepreneur_contacts_not_collected():
    prov = providers(identity(inn="770123456789", kind="INDIVIDUAL_ENTREPRENEUR"), pages=site_pages())
    res = P.enrich("770123456789", prov, clock())
    assert res.status == EnrichmentStatus.PARTIAL and prov.verifier.calls == 0 and res.contacts == []
    assert "INDIVIDUAL_ENTREPRENEUR_CONTACTS_NOT_COLLECTED" in res.reasons


def test_pipeline_is_deterministic():
    a = P.enrich(INN, providers(identity(), pages=site_pages()), clock())
    b = P.enrich(INN, providers(identity(), pages=site_pages()), clock())
    assert (a.contacts, a.roles, a.evidence, a.status) == (b.contacts, b.roles, b.evidence, b.status)


def test_mirror_outage_is_partial_and_retryable():
    res = P.enrich(INN, providers(identity(), pages=site_pages(), mirror=FakeRegistry("CHECKO_REGISTRY_MIRROR", error=True)), clock())
    assert res.identity.legal_name.source_type == SourceType.FNS_EGRUL
    assert "REGISTRY_MIRROR_UNAVAILABLE" in res.reasons and res.retryable


def test_unreachable_website_is_retryable_but_plain_gaps_are_not():
    assert P.enrich(INN, providers(identity(), site_error=True), clock()).retryable
    res = P.enrich(INN, providers(identity(site=None)), clock())
    assert res.status == EnrichmentStatus.PARTIAL and "NO_WEBSITE_CANDIDATE" in res.reasons and not res.retryable


# ------------------------------------------------------------------------------------------------------------ HTTP politeness
def _fetcher(responses, **kw):
    import httpx
    from app.enrichment.providers import HttpFetcher
    seen, slept = [], []

    def handler(request):
        seen.append(str(request.url))
        status, headers = responses[min(len(seen), len(responses)) - 1]
        return httpx.Response(status, headers=headers, text="ok")
    t = [0.0]
    f = HttpFetcher(transport=httpx.MockTransport(handler), clock=lambda: t[0], sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)),
                    **kw)
    return f, seen, slept


def test_rate_limited_response_is_waited_out_once_then_retried():
    f, seen, slept = _fetcher([(429, {"Retry-After": "5"}), (200, {})])
    assert f.get("https://checko.ru/search?query=1")[1] == "ok"
    assert len(seen) == 2 and slept == [5.0]


def test_rate_limit_gives_up_after_one_backoff_or_a_long_retry_after():
    import pytest
    from app.enrichment.profile_models import SourceUnavailable
    f, seen, slept = _fetcher([(429, {}), (429, {})])
    with pytest.raises(SourceUnavailable, match="after one backoff"):
        f.get("https://checko.ru/x")
    assert len(seen) == 2 and slept == [10.0]
    f, seen, slept = _fetcher([(429, {"Retry-After": "3600"})])
    with pytest.raises(SourceUnavailable, match="too long"):
        f.get("https://checko.ru/x")
    assert len(seen) == 1 and slept == []


def test_mirror_host_gets_a_stricter_interval():
    f, seen, slept = _fetcher([(200, {})], host_intervals={"checko.ru": 3.0})
    f.get("https://checko.ru/a"); f.get("https://checko.ru/b"); f.get("https://example.ru/a"); f.get("https://example.ru/b")
    assert slept == [3.0, 1.0]
