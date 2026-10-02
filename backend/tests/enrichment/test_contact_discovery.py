"""P5-002A website discovery, identity verification and business-contact extraction (pure; no network)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date

import httpx
import pytest

from app.enrichment import discovery as D
from app.enrichment import pipeline as P
from app.enrichment import providers as PR
from app.enrichment.profile_models import (Page, SourceRateLimited, SourceSkipped, SourceType, SourceUnavailable, Sourced,
                                           WebsiteCandidate, WebsiteConfidence, WebsiteVerification, WebsiteVerificationStatus)
from tests.enrichment.fakes import INN, NOW, OGRN, FakeRegistry, FakeVerifier, identity, site_pages


def page(url: str, html: str) -> Page:
    return Page(url, html, PR.html_to_text(html))


def ident(**kw):
    base = identity(site=None)
    return replace(base, **kw)


def fns(v):
    return Sourced(v, PR.EGRUL_PUBLIC_URL, SourceType.FNS_EGRUL, NOW)


# ------------------------------------------------------------------------------------------------ discovery
@pytest.mark.parametrize("host,cls", [("www.rusprofile.ru", "REGISTRY_MIRROR"), ("checko.ru", "REGISTRY_MIRROR"),
                                      ("spb.zoon.ru", "DIRECTORY"), ("vk.com", "SOCIAL"), ("ozon.ru", "MARKETPLACE"),
                                      ("zakupki.gov.ru", "PROCUREMENT_PORTAL"), ("ria.ru", "NEWS"), ("socpitanie.spb.ru", "DIRECTORY"),
                                      ("artiskids.ru", None), ("www.multioperator.ru", None)])
def test_classify_host(host, cls):
    assert D.classify_host(host) == cls


def test_queries_are_high_precision_and_bounded():
    q = D.build_queries(ident(), limit=3)
    assert q == [f'"тестовый молочный завод" "{INN}"', f'"тестовый молочный завод" "{OGRN}"', '"тестовый молочный завод" "Москва"']
    assert len(D.build_queries(ident(), limit=5)) == 5 and D.build_queries(ident(), limit=5)[3] == f'"{INN}"'


def test_name_cores_handle_nested_quotes_and_legal_forms():
    i = ident(legal_name=fns('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ  "КОМПАНИЯ "ТЕНЗОР"'), short_name=fns('ООО "КОМПАНИЯ "ТЕНЗОР"'))
    assert PR.name_cores(i) == ["компания тензор"]
    i2 = ident(legal_name=fns('АКЦИОНЕРНОЕ ОБЩЕСТВО "АРТИС-ДЕТСКОЕ ПИТАНИЕ"'), short_name=None)
    assert PR.name_cores(i2) == ["артис-детское питание"]


def test_egrul_email_domain_provider_skips_free_mail():
    assert D.EgrulEmailDomainSearch().search(ident(registered_email=fns("info@bsspharm.ru")))[0].url == "https://bsspharm.ru/"
    assert D.EgrulEmailDomainSearch().search(ident(registered_email=fns("szuomt@mail.ru"))) == []
    assert D.EgrulEmailDomainSearch().search(ident()) == []


def test_parse_egrul_email_from_extract():
    text = "Сведения об адресе электронной почты\nАдрес электронной почты\n10 E-mail INFO@BSSPHARM.RU\nСтраница 2 из 9\n"
    assert PR.parse_egrul_email(text, NOW).value == "info@bsspharm.ru"
    assert PR.parse_egrul_email("нет почты", NOW) is None


def test_search_api_parsers():
    brave = {"web": {"results": [{"url": "https://artiskids.ru/", "title": "Артис", "description": "ИНН 7804054351"},
                                 {"url": "https://www.rusprofile.ru/id/1", "title": "x"}]}}
    hits = D.BraveSearchApi.parse(brave, "q")
    assert [h.url for h in hits] == ["https://artiskids.ru/", "https://www.rusprofile.ru/id/1"] and hits[0].snippet
    xml = ("<yandexsearch><response><results><grouping><group><doc><url>https://artiskids.ru/</url><title>Артис</title>"
           "<passages><passage>ИНН 7804054351</passage></passages></doc></group></grouping></results></response></yandexsearch>")
    y = D.YandexSearchApi.parse(xml, "q")
    assert y[0].url == "https://artiskids.ru/" and "7804054351" in y[0].snippet
    with pytest.raises(SourceRateLimited):
        D.YandexSearchApi.parse('<yandexsearch><response><error code="55">limit</error></response></yandexsearch>', "q")
    wd = {"results": {"bindings": [{"site": {"value": "https://www.sberbank.ru"}}, {"site": {"value": "https://www.sberbank.ru"}}]}}
    assert [h.url for h in D.WikidataOgrnSearch.parse(wd)] == ["https://www.sberbank.ru"]


def test_legal_name_domains_are_bounded_guesses_kept_only_when_resolving():
    i = ident(legal_name=fns('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "КАРДАН"'), short_name=None)
    hosts = D.name_domains(i)
    assert hosts[:2] == ["kardan.ru", "kardan.com"] and "кардан.рф" in hosts and len(hosts) <= 8
    hits = D.LegalNameDomainSearch(resolver=lambda h: h == "kardan.ru").search(i)
    assert [h.url for h in hits] == ["https://kardan.ru/"]


class StubProvider:
    def __init__(self, name, hits=(), error=None):
        self.name, self.role, self.hits, self.error, self.calls = name, "PRIMARY", list(hits), error, 0

    def search(self, identity):
        self.calls += 1
        if self.error:
            raise self.error
        return self.hits


def test_discovery_ranks_dedupes_filters_and_survives_provider_failures():
    guess = StubProvider("LEGAL_NAME_DOMAIN", [D.SearchHit("https://moloko.ru/", "LEGAL_NAME_DOMAIN", 0)])
    egrul = StubProvider("EGRUL_EMAIL_DOMAIN", [D.SearchHit("https://moloko-test.ru/", "EGRUL_EMAIL_DOMAIN", 0)])
    api = StubProvider("BRAVE_SEARCH_API", [D.SearchHit("https://www.rusprofile.ru/id/9", "BRAVE_SEARCH_API", 0),
                                            D.SearchHit("https://www.moloko-test.ru/contacts", "BRAVE_SEARCH_API", 1, None, "", f"ИНН {INN}")])
    broken = StubProvider("WIKIDATA_OGRN", error=RuntimeError("bug"))
    d = D.WebsiteDiscovery([guess, broken, egrul, api], lambda: NOW)
    cands = d.discover(ident())
    assert [c.url for c in cands] == ["https://moloko-test.ru/", "https://moloko.ru/"]     # deduped by domain; EGRUL first
    assert cands[0].provider == "EGRUL_EMAIL_DOMAIN"
    assert ("https://www.rusprofile.ru/id/9", "REGISTRY_MIRROR", "BRAVE_SEARCH_API") in d.last_log.rejected
    assert {a.source: a.outcome.value for a in d.last_log.attempts}["WIKIDATA_OGRN"] == "UNAVAILABLE"


def test_discovery_circuit_breaker_skips_a_rate_limited_provider():
    api = StubProvider("BRAVE_SEARCH_API", error=SourceRateLimited("429"))
    d = D.WebsiteDiscovery([api], lambda: NOW, max_candidates=3)
    for _ in range(3):
        d.discover(ident())
    assert api.calls == 2 and d.last_log.attempts[0].outcome.value == "SKIPPED"


def test_build_discovery_uses_keys_only_when_configured():
    f = PR.HttpFetcher()
    try:
        names = D.provider_names(D.build_discovery(f, lambda: NOW, {}))
        assert names == ["EGRUL_EMAIL_DOMAIN", "WIKIDATA_OGRN", "LEGAL_NAME_DOMAIN", "REGISTRY_MIRROR_HINT"]
        names = D.provider_names(D.build_discovery(f, lambda: NOW, {"BRAVE_SEARCH_API_KEY": "k", "ENRICHMENT_DOMAIN_GUESS": "off"},
                                                   use_secondary_hint=False))
        assert names == ["EGRUL_EMAIL_DOMAIN", "BRAVE_SEARCH_API", "WIKIDATA_OGRN"]
    finally:
        f.close()


# ------------------------------------------------------------------------------------------------ identity verification
# shape of the real notice on tsmb.ru/contacts (2026-10-02): another group company's requisites inside an impostor warning
TSMB_WARNING = ("<p>Уважаемые партнеры! Убедительно просим с особым вниманием отнестись к нижеуказанной информации. От имени "
                "ООО «СЗУ ОМТ» (ИНН {inn}, КПП 781301001, ОГРН {ogrn}, юридический адрес: 197110, Санкт-Петербург, ул. Большая "
                "Зеленина дом 24), входящего в группу компаний «ЦМБ» злоумышленниками осуществляются рассылки …</p>")


def test_inn_inside_an_impostor_warning_is_not_self_identification():
    v = PR.assess_identity(ident(), [page("https://tsmb.ru/contacts/", TSMB_WARNING.format(inn=INN, ogrn=OGRN))])
    assert v[0] == WebsiteConfidence.LOW and "ID_ONLY_IN_WARNING_CONTEXT" in v[1] and "INN_ON_SITE" not in v[1]


def test_warning_page_never_becomes_a_composite_match():
    """Regression (golden run 2026-10-02): name + KPP + registered street quoted inside the warning made tsmb.ru a
    VERIFIED_COMPOSITE site of the warned-about company."""
    i = ident(short_name=fns('ООО "СЗУ ОМТ"'), kpp=fns("781301001"),
              registered_address=fns("197110, Г.САНКТ-ПЕТЕРБУРГ, УЛ. БОЛЬШАЯ ЗЕЛЕНИНА, Д. 24, СТР. 1"))
    v = PR.assess_identity(i, [page("https://tsmb.ru/contacts/", TSMB_WARNING.format(inn=INN, ogrn=OGRN))])
    assert {"KPP_ON_SITE", "EXACT_LEGAL_NAME", "ID_ONLY_IN_WARNING_CONTEXT"} <= set(v[1])
    assert v[0] == WebsiteConfidence.LOW


def test_directory_like_pages_are_rejected_even_with_the_inn():
    rows = "".join(f"<li>ООО «Фирма {k}» ИНН 77010000{k:02d}</li>" for k in range(3))
    v = PR.assess_identity(ident(), [page("https://catalog.example/", f"<ul>{rows}<li>ИНН {INN}</li></ul>")])
    assert v[0] == WebsiteConfidence.LOW and "DIRECTORY_LIKE" in v[1]
    two = PR.assess_identity(ident(), [page("https://rsvo.example/", f"ИНН {INN} … филиал ИНН 9200015508")])
    assert two[0] == WebsiteConfidence.HIGH        # a branch INN next to ours is not a directory


def test_kpp_counts_only_with_the_exact_legal_name():
    named = PR.assess_identity(ident(), [page("https://x.ru/", "ООО «Тестовый молочный завод», КПП 770101001")])
    assert named[0] == WebsiteConfidence.HIGH and PR.verification_status(*named) == WebsiteVerificationStatus.VERIFIED_COMPOSITE
    alone = PR.assess_identity(ident(), [page("https://x.ru/", "ООО «Другая фирма», КПП 770101001")])
    assert alone[0] == WebsiteConfidence.LOW


def test_name_match_is_word_bounded():
    i = ident(legal_name=fns('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "КАРДАН"'), short_name=None,
              registered_address=fns("197375, Г.САНКТ-ПЕТЕРБУРГ, УЛ АВТОБУСНАЯ, Д. 5, ЛИТЕРА А"))
    sub = PR.assess_identity(i, [page("https://x.ru/", "Работаем с карданами. Санкт-Петербург, Автобусная ул, д.5")])
    assert "EXACT_LEGAL_NAME" not in sub[1] and sub[0] == WebsiteConfidence.LOW
    brand = PR.assess_identity(i, [page("https://kardan-fix.ru/", "«Кардан-Фикс». Санкт-Петербург, Автобусная ул, д.5")])
    assert {"EXACT_LEGAL_NAME", "REGISTERED_STREET_ADDRESS"} <= set(brand[1]) and brand[0] == WebsiteConfidence.HIGH


def test_strong_status_from_inn():
    v = PR.assess_identity(ident(), [page("https://x.ru/", f"Реквизиты: ИНН {INN}")])
    assert PR.verification_status(*v) == WebsiteVerificationStatus.VERIFIED_STRONG


# ------------------------------------------------------------------------------------------------ contacts
CONTACTS = """<html><body>
<p>Офис: <a href="tel:+78127791177">+7 (812) 779-11-77</a> cosmetics@bsspharm.ru</p>
<p>Приёмная Телефон: +7 (812) 388-36-64 Факс: +7 (812) 388-67-80 E-mail: dir@moloko-test.ru</p>
<p>Тел./факс: +7 (812) 555-12-34</p>
<p>Склад: г. Колпино, ул. Северная, д. 14</p>
<p>Руководитель департамента Мария Ширкина m.shirkina@moloko-test.ru +7 (925) 036-37-42</p>
<p>Менеджеры: a.bondar@moloko-test.ru, kamenev.m@moloko-test.ru, petrova@moloko-test.ru, nikiforova.kseniya@moloko-test.ru</p>
<p>Разработка сайта: studio@webdev-agency.ru · zakaz@yandex.ru · ivanov77@mail.ru</p>
<p>р/с 40702810455000000906 в Северо-Западном банке</p>
<p>Реквизиты: ИНН {inn}, ОГРН {ogrn}</p></body></html>"""


def verified(pages, signals=("INN_ON_SITE",), url="https://moloko-test.ru/", latest=2026):
    return WebsiteVerification(url, WebsiteConfidence.HIGH, signals, url, tuple(pages), latest, NOW)


def test_extractor_business_contacts_only():
    i = ident(registered_email=fns("info@bsspharm.ru"))
    html = CONTACTS.format(inn=INN, ogrn=OGRN)
    other = page("https://other-company.ru/", "<a href='tel:+74950000000'>+7 495 000-00-00</a> info@other-company.ru")
    out = PR.HtmlContactExtractor(max_per_type=5).extract(i, verified([page("https://moloko-test.ru/contacts/", html), other]))
    phones = {c.normalized for c in out if c.type.value == "PHONE"}
    emails = {c.normalized for c in out if c.type.value == "EMAIL"}
    assert phones == {"78127791177", "78123883664", "78125551234"}           # fax-only and person-associated numbers dropped
    assert "78123886780" not in phones and "79250363742" not in phones and "74950000000" not in phones
    assert "78104550000" not in {p[:11] for p in phones}                      # bank account digits are never a phone
    assert emails == {"cosmetics@bsspharm.ru", "dir@moloko-test.ru", "zakaz@yandex.ru"}
    assert all(c.verification_basis and c.verification_basis.startswith("OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE") for c in out)
    assert any(c.type.value == "WEBSITE" and c.value == "https://moloko-test.ru/" for c in out)


def test_extractor_never_reads_unverified_sites():
    v = WebsiteVerification("https://x.ru/", WebsiteConfidence.MEDIUM, (), None, (page("https://x.ru/", "info@x.ru"),), None, NOW)
    assert PR.HtmlContactExtractor().extract(ident(), v) == []


def test_email_acceptance_rules():
    acc = PR.email_accepted
    assert acc("sales@moloko.ru", "moloko.ru", {"moloko.ru"}, "moloko") == "COMPANY_DOMAIN"
    assert acc("cosmetics@bsspharm.ru", "bsscosmetics.ru", {"bsscosmetics.ru", "bsspharm.ru"}, "bsscosmetics") == "COMPANY_DOMAIN"
    assert acc("a.bondar@bsspharm.ru", "bsscosmetics.ru", {"bsspharm.ru"}, "bsscosmetics") is None
    assert acc("studio@webdev.ru", "moloko.ru", {"moloko.ru"}, "moloko") is None
    assert acc("info@mail.ru", "moloko.ru", {"moloko.ru"}, "moloko") == "PUBLIC_MAILBOX_ON_OFFICIAL_SITE"
    assert acc("moloko-spb@yandex.ru", "moloko.ru", {"moloko.ru"}, "moloko") == "PUBLIC_MAILBOX_ON_OFFICIAL_SITE"
    assert acc("kval78@yandex.ru", "kardan-fix.ru", {"kardan-fix.ru"}, "kardan-fix") is None


def test_registry_contacts_include_business_egrul_email_only():
    out = PR.registry_contacts(ident(registered_email=fns("info@bsspharm.ru")))
    assert [(c.type.value, c.value, c.verification_basis) for c in out] == [
        ("ADDRESS", "123456, г. Москва, ул. Молочная, д. 1", "FNS_EGRUL_EXTRACT"), ("EMAIL", "info@bsspharm.ru", "FNS_EGRUL_REGISTERED_EMAIL")]
    assert all(c.type.value != "EMAIL" for c in PR.registry_contacts(ident(registered_email=fns("ivan.petrov@mail.ru"))))
    assert all(c.type.value != "EMAIL" for c in PR.registry_contacts(ident(registered_email=fns("petrov77@mail.ru"))))


def test_latest_year_reads_page_metadata_not_retrieval_date():
    meta = page("https://x.ru/", '<meta property="article:modified_time" content="2025-11-03T10:00:00+03:00">')
    assert PR.latest_year([meta], date(2026, 10, 2)) == 2025
    assert PR.latest_year([page("https://x.ru/", "<p>no dates</p>")], date(2026, 10, 2)) is None


# ------------------------------------------------------------------------------------------------ robots.txt
def test_fetcher_respects_robots_txt():
    def handler(req: httpx.Request):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n", headers={"content-type": "text/plain"})
        return httpx.Response(200, text="<html>ok</html>", headers={"content-type": "text/html"})
    f = PR.HttpFetcher(min_interval=0, transport=httpx.MockTransport(handler), sleep=lambda s: None)
    try:
        assert f.get("https://site.example/contacts/", robots=True)[1] == "<html>ok</html>"
        with pytest.raises(SourceSkipped):
            f.get("https://site.example/private/x", robots=True)
        assert f.get("https://site.example/private/x")[1] == "<html>ok</html>"      # registries / APIs: not a site crawl
    finally:
        f.close()


# ------------------------------------------------------------------------------------------------ stored-site protection
class ListDiscovery:
    name = "WEBSITE_DISCOVERY"

    def __init__(self, urls):
        self.urls, self.last_log = urls, D.DiscoveryLog()

    def discover(self, identity):
        return [WebsiteCandidate(u, Sourced(u, u, SourceType.FIRST_PARTY, NOW), provider="LEGAL_NAME_DOMAIN") for u in self.urls]


class RoutingVerifier(FakeVerifier):
    """Per-host pages; a host mapped to None is unreachable."""

    def __init__(self, sites):
        super().__init__({})
        self.sites, self.seen = sites, []

    def verify_company_site(self, ident_, cand):
        self.seen.append(cand.url)
        pages = self.sites[PR.host_of(cand.url)]
        if pages is None:
            raise SourceUnavailable("timeout")
        self.pages = pages
        return super().verify_company_site(ident_, cand)


def run(sites, discovered, prior):
    ver = RoutingVerifier(sites)
    prov = P.Providers(registries=[FakeRegistry("FNS_EGRUL", ident())], discovery=ListDiscovery(discovered), verifier=ver,
                       extractor=PR.HtmlContactExtractor(), roles=PR.SiteAndOkvedRoleEvidence())
    return P.enrich(INN, prov, lambda: NOW, prior_website=prior), ver


def test_stored_site_still_verified_is_kept_and_new_candidates_not_checked():
    res, ver = run({"moloko-test.ru": site_pages(), "other.ru": site_pages()}, ["https://other.ru/"], "https://moloko-test.ru/")
    assert ver.seen == ["https://moloko-test.ru/"] and res.prior_site_rechecked and res.website.official_url


def test_unreachable_stored_site_is_kept_and_nothing_else_replaces_it():
    res, ver = run({"moloko-test.ru": None, "other.ru": site_pages()}, ["https://other.ru/"], "https://moloko-test.ru/")
    assert ver.seen == ["https://moloko-test.ru/"] and res.website is None and "STORED_WEBSITE_NOT_RECHECKED" in res.reasons


def test_stored_site_failing_recheck_lets_other_candidates_compete():
    res, ver = run({"moloko-test.ru": site_pages(with_requisites=False), "other.ru": site_pages()}, ["https://other.ru/"],
                   "https://moloko-test.ru/")
    assert ver.seen == ["https://moloko-test.ru/", "https://other.ru/"] and "STORED_WEBSITE_FAILED_RECHECK" in res.reasons
    assert res.prior_site_rechecked and len(res.website_checks) == 2
