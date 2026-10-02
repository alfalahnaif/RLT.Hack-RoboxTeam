"""Deterministic fake providers for P5-001A tests (no network)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.enrichment import pipeline as P
from app.enrichment.profile_models import (Page, RegistryIdentity, SourceType, SourceUnavailable, Sourced, WebsiteCandidate,
                                           WebsiteVerification)
from app.enrichment.providers import (HtmlContactExtractor, RegistryWebsiteDiscovery, SiteAndOkvedRoleEvidence, assess_identity,
                                      html_to_text, latest_year)

NOW = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)
INN = "7701234567"
OGRN = "1027700000001"
CHECKO_URL = "https://checko.ru/company/test-1027700000001"


def clock(t: datetime = NOW):
    return lambda: t


def identity(inn: str = INN, okved: str | None = "10.51.9 Производство прочей молочной продукции", site: str | None = "https://moloko-test.ru",
             kind: str = "LEGAL_ENTITY", t: datetime = NOW) -> RegistryIdentity:
    def fns(v):
        return Sourced(v, "https://egrul.nalog.ru/index.html", SourceType.FNS_EGRUL, t)

    def mir(v):
        return Sourced(v, CHECKO_URL, SourceType.FNS_EGRUL_DERIVED_REGISTRY, t)

    return RegistryIdentity(inn=inn, entity_kind=kind, legal_name=fns('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ТЕСТОВЫЙ МОЛОЧНЫЙ ЗАВОД"'),
                            short_name=fns('ООО "ТМЗ"'), ogrn=fns(OGRN), kpp=fns("770101001") if kind == "LEGAL_ENTITY" else None,
                            legal_status=fns("ACTIVE"), region=fns("Москва"),
                            registered_address=mir("123456, г. Москва, ул. Молочная, д. 1") if kind == "LEGAL_ENTITY" else None,
                            primary_okved=mir(okved) if okved else None, website_hints=(mir(site),) if site else ())


SITE_HOME = """<html><head><title>Тестовый молочный завод</title></head><body>
<a href="/contacts/">Контакты</a> <a href="/catalog/">Каталог</a>
<p>Собственное производство цельномолочной продукции с 1995 года.</p>
<footer>© 2014–2026 ООО «Тестовый молочный завод»</footer></body></html>"""
SITE_CONTACTS = """<html><body><h1>Контакты</h1>
<p>Закупки: kamenev.m@moloko-test.ru, тел. 8 (917) 470-11-08</p>
<p>Отдел продаж: <a href="tel:+74951234567">+7 (495) 123-45-67</a>, e-mail: <a href="mailto:sales@moloko-test.ru">sales@moloko-test.ru</a></p>
<p>Генеральный директор Иванов Иван Иванович, моб. +7 916 765-43-21, ivanov.ii@gmail.com</p>
<p>Реквизиты: ИНН {inn}, ОГРН {ogrn}</p></body></html>"""


class FakeRegistry:
    def __init__(self, name: str, result=None, error: bool = False):
        self.name, self.result, self.error, self.calls = name, result, error, 0

    def lookup_by_inn(self, inn):
        self.calls += 1
        if self.error:
            raise SourceUnavailable("timeout")
        return self.result


class FakeVerifier:
    """Serves fixed pages; identity assessment is the real one."""
    name = "FIRST_PARTY_WEBSITE"

    def __init__(self, pages: dict[str, str] | None = None, error: bool = False, t: datetime = NOW):
        self.pages, self.error, self.t, self.calls = pages, error, t, 0

    def verify_company_site(self, ident, cand: WebsiteCandidate) -> WebsiteVerification:
        self.calls += 1
        if self.error:
            raise SourceUnavailable("connect timeout")
        pages = [Page(u, h, html_to_text(h)) for u, h in self.pages.items()]
        conf, signals = assess_identity(ident, pages)
        return WebsiteVerification(cand.url, conf, signals, pages[0].url if conf.value == "HIGH" else None, tuple(pages),
                                   latest_year(pages, self.t.date()), self.t)


def site_pages(inn: str = INN, ogrn: str = OGRN, with_requisites: bool = True) -> dict[str, str]:
    contacts = SITE_CONTACTS.format(inn=inn, ogrn=ogrn) if with_requisites else SITE_CONTACTS.replace(
        "<p>Реквизиты: ИНН {inn}, ОГРН {ogrn}</p>", "")
    return {"https://moloko-test.ru/": SITE_HOME, "https://moloko-test.ru/contacts/": contacts}


def providers(registry_result=None, registry_error=False, pages=None, site_error=False, mirror=None) -> P.Providers:
    regs = [FakeRegistry("FNS_EGRUL", registry_result, registry_error)]
    if mirror is not None:
        regs.append(mirror)
    return P.Providers(registries=regs, discovery=RegistryWebsiteDiscovery(), verifier=FakeVerifier(pages or {}, site_error),
                       extractor=HtmlContactExtractor(), roles=SiteAndOkvedRoleEvidence())
