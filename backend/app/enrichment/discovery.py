"""P5-002A official-website discovery for historical suppliers (no dependency on checko.ru).

The official EGRUL identity (INN, OGRN, KPP, legal name, registered address, region, e-mail) is the ground truth; discovery
only proposes a bounded, ranked list of candidate sites. A candidate becomes the official website only after
HttpWebsiteVerifier proves the identity on the site itself (providers.assess_identity). Nothing here is ever a fact.

  WebsiteSearchProvider.search(identity) -> list[SearchHit]          (raises SourceUnavailable; one provider = one source)

Providers (replaceable; the service builds the list from configuration, see build_discovery):
  EgrulEmailDomainSearch    domain of the e-mail registered in EGRUL (official FNS record; free-mail domains skipped)
  BraveSearchApi            Brave Search API (official API, key BRAVE_SEARCH_API_KEY) — high-precision query combinations
  YandexSearchApi           Yandex Search API XML (key YANDEX_SEARCH_API_KEY + YANDEX_SEARCH_FOLDER_ID)
  WikidataOgrnSearch        Wikidata: official website (P856) of the item with this OGRN (P7011); CC0 SPARQL endpoint
  LegalNameDomainSearch     domains derived from the legal-name core (transliterated + .рф), kept only when DNS resolves
  RegistryHintSearch        website hint of an optional registry mirror (checko.ru) — OPTIONAL_SECONDARY_HINT, never required
HTML result pages of web search engines are NOT scraped: their robots.txt disallows /search (checked 2026-10-02).

Safety: hosts of directories, registry mirrors, marketplaces, social networks, news and procurement portals are never
candidates (they may only be logged as rejected hints); every provider sits behind its own circuit breaker; the candidate list
is deduplicated by registrable domain and capped.
"""
from __future__ import annotations

import concurrent.futures
import re
import socket
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Protocol
from urllib.parse import urlencode, urlsplit

from app.enrichment.profile_models import (RegistryIdentity, SourceAttempt, SourceOutcome, SourceRateLimited, SourceType,
                                           SourceUnavailable, Sourced, WebsiteCandidate, outcome_of)
from app.enrichment.providers import FREE_MAIL, CircuitBreaker, HttpFetcher, _fold, host_of, name_cores, registrable_domain

MAX_CANDIDATES = 4
MAX_QUERIES = 3


# ------------------------------------------------------------------------------------------------------------ host classes
HOST_CLASSES: dict[str, tuple[str, ...]] = {
    "REGISTRY_MIRROR": ("checko.ru", "rusprofile.ru", "list-org.com", "zachestnyibiznes.ru", "sbis.ru", "saby.ru",
                        "spark-interfax.ru", "kartoteka.ru", "synapsenet.ru", "star-pro.ru", "vbankcenter.ru", "audit-it.ru",
                        "vbr.ru", "b2b.house", "find-org.com", "firmoteka.ru", "bbnt.ru", "sevem.pro", "myseldon.com",
                        "credinform.ru", "1prime.ru", "reputation.ru", "companium.ru", "skrin.ru", "e-ecolog.ru", "egrul.nalog.ru",
                        "nalog.ru", "nalog.gov.ru", "tbank.ru", "companies.rbc.ru", "ogrn.online", "rusprofile.com", "kontur.ru",
                        "focus.kontur.ru", "spark.ru", "zcb.ru", "datanewton.ru", "excheck.pro", "xn--90aiaqqbd.xn--p1ai"),
    "DIRECTORY": ("2gis.ru", "2gis.com", "yell.ru", "zoon.ru", "yp.ru", "spravka.city", "orgpage.ru", "spr.ru", "flamp.ru",
                  "tenderguru.ru", "clearspending.ru", "emis.com", "fishnet.ru", "milknet.biz", "kaspz.ru", "spravker.ru",
                  "rubrikator.org", "cataloxy.ru", "allbiz.ru", "pulscen.ru", "blizko.ru", "tiu.ru", "satom.ru", "whoiswho.dp.ru",
                  "yapl.ru", "fooby.ru", "socpitanie.spb.ru", "gosadmin.ru", "platforms.su", "reestr.digital.gov.ru",
                  "old-reestr.digital.gov.ru", "normacs.info", "avto-mesta.ru"),
    "MARKETPLACE": ("avito.ru", "ozon.ru", "wildberries.ru", "market.yandex.ru", "aliexpress.ru", "tiu.ru", "otc.ru",
                    "megamarket.ru", "lamoda.ru"),
    "SOCIAL": ("vk.com", "ok.ru", "t.me", "telegram.me", "facebook.com", "instagram.com", "youtube.com", "rutube.ru", "dzen.ru",
               "habr.com", "twitter.com", "x.com", "linkedin.com", "tiktok.com", "livejournal.com", "pikabu.ru"),
    "AGGREGATOR": ("yandex.ru", "ya.ru", "google.com", "google.ru", "bing.com", "duckduckgo.com", "mail.ru", "rambler.ru",
                   "wikipedia.org", "wikidata.org", "hh.ru", "superjob.ru", "rabota.ru", "zarplata.ru", "otzovik.com",
                   "irecommend.ru", "pravda-sotrudnikov.ru", "dreamjob.ru"),
    "NEWS": ("ria.ru", "tass.ru", "rbc.ru", "kommersant.ru", "fontanka.ru", "interfax.ru", "vedomosti.ru", "lenta.ru",
             "gazeta.ru", "iz.ru", "dp.ru", "spb.aif.ru", "aif.ru", "regnum.ru"),
    "PROCUREMENT_PORTAL": ("zakupki.gov.ru", "rts-tender.ru", "roseltorg.ru", "sberbank-ast.ru", "b2b-center.ru", "fabrikant.ru",
                           "tektorg.ru", "etp-ets.ru", "zakazrf.ru", "gz-spb.ru", "agzrt.ru", "lot-online.ru", "rostender.info",
                           "tenderpro.ru", "bicotender.ru", "zakupki.mos.ru", "poisktenderov.ru", "tenderplan.ru"),
}


def classify_host(host: str) -> str | None:
    """Category of a host that can never be a company's official website, or None."""
    h = host.lower().removeprefix("www.")
    for cls, hosts in HOST_CLASSES.items():
        if any(h == x or h.endswith("." + x) for x in hosts):
            return cls
    return None


# ------------------------------------------------------------------------------------------------------------ interface
@dataclass(frozen=True)
class SearchHit:
    url: str
    provider: str
    rank: int                 # provider-local rank (0 = first)
    query: str | None = None
    title: str = ""
    snippet: str = ""


class WebsiteSearchProvider(Protocol):
    name: str
    role: str                 # PRIMARY | OPTIONAL_SECONDARY_HINT

    def search(self, identity: RegistryIdentity) -> list[SearchHit]: ...


def build_queries(identity: RegistryIdentity, limit: int = MAX_QUERIES) -> list[str]:
    """High-precision query combinations (most specific first), bounded."""
    cores = name_cores(identity)
    name = cores[0] if cores else None
    q = []
    if name:
        q.append(f'"{name}" "{identity.inn}"')
        if identity.ogrn:
            q.append(f'"{name}" "{identity.ogrn.value}"')
        if identity.region:
            q.append(f'"{name}" "{identity.region.value}"')
    q.append(f'"{identity.inn}"')
    if identity.ogrn:
        q.append(f'"{identity.ogrn.value}"')
    return q[:limit]


# ------------------------------------------------------------------------------------------------------------ providers
class EgrulEmailDomainSearch:
    """The official EGRUL record's e-mail domain (e.g. INFO@BSSPHARM.RU -> bsspharm.ru). Free-mail domains are skipped."""
    name, role = "EGRUL_EMAIL_DOMAIN", "PRIMARY"

    def search(self, identity: RegistryIdentity) -> list[SearchHit]:
        e = identity.registered_email
        if not e or "@" not in e.value:
            return []
        dom = e.value.partition("@")[2].lower()
        if dom in FREE_MAIL or registrable_domain(dom) in FREE_MAIL:
            return []
        return [SearchHit(f"https://{registrable_domain(dom)}/", self.name, 0, None, "EGRUL e-mail", e.value)]


class BraveSearchApi:
    """Brave Search API (https://api.search.brave.com/res/v1/web/search) — the official API, not the robots-disallowed HTML."""
    name, role = "BRAVE_SEARCH_API", "PRIMARY"
    URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, fetcher: HttpFetcher, per_query: int = 8, max_queries: int = MAX_QUERIES) -> None:
        self.api_key, self.fetcher, self.per_query, self.max_queries = api_key, fetcher, per_query, max_queries

    @staticmethod
    def parse(payload: dict, query: str, provider: str = "BRAVE_SEARCH_API") -> list[SearchHit]:
        out = []
        for i, r in enumerate((payload.get("web") or {}).get("results") or []):
            if isinstance(r, dict) and r.get("url"):
                out.append(SearchHit(r["url"], provider, i, query, r.get("title") or "", r.get("description") or ""))
        return out

    def search(self, identity: RegistryIdentity) -> list[SearchHit]:
        hits = []
        for q in build_queries(identity, self.max_queries):
            url = f"{self.URL}?{urlencode({'q': q, 'count': self.per_query, 'country': 'RU', 'search_lang': 'ru'})}"
            body = self.fetcher.request_json(url, {"Accept": "application/json", "X-Subscription-Token": self.api_key})
            hits += self.parse(body, q)
        return hits


class YandexSearchApi:
    """Yandex Search API, XML interface (https://yandex.ru/search/xml?folderid=…&apikey=…)."""
    name, role = "YANDEX_SEARCH_API", "PRIMARY"
    URL = "https://yandex.ru/search/xml"

    def __init__(self, api_key: str, folder_id: str, fetcher: HttpFetcher, max_queries: int = MAX_QUERIES) -> None:
        self.api_key, self.folder_id, self.fetcher, self.max_queries = api_key, folder_id, fetcher, max_queries

    @staticmethod
    def parse(xml_text: str, query: str, provider: str = "YANDEX_SEARCH_API") -> list[SearchHit]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise SourceUnavailable("Yandex Search API: unreadable XML") from e
        err = root.find(".//error")
        if err is not None:
            code = err.get("code", "")
            raise (SourceRateLimited if code in ("32", "55") else SourceUnavailable)(f"Yandex Search API error {code}")
        out = []
        for i, doc in enumerate(root.iter("doc")):
            url = (doc.findtext("url") or "").strip()
            if url:
                title = "".join(doc.find("title").itertext()) if doc.find("title") is not None else ""
                snip = " ".join("".join(p.itertext()) for p in doc.iter("passage"))
                out.append(SearchHit(url, provider, i, query, title, snip))
        return out

    def search(self, identity: RegistryIdentity) -> list[SearchHit]:
        hits = []
        for q in build_queries(identity, self.max_queries):
            params = {"folderid": self.folder_id, "apikey": self.api_key, "query": q, "l10n": "ru", "sortby": "rlv",
                      "filter": "none", "groupby": "attr=d.mode=deep.groups-on-page=8.docs-in-group=1"}
            _, body = self.fetcher.get(f"{self.URL}?{urlencode(params)}")
            hits += self.parse(body, q)
        return hits


class WikidataOgrnSearch:
    """Wikidata item with this OGRN (P7011 «Russian organisation number») -> its official website (P856)."""
    name, role = "WIKIDATA_OGRN", "PRIMARY"
    URL = "https://query.wikidata.org/sparql"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    @staticmethod
    def parse(payload: dict, provider: str = "WIKIDATA_OGRN") -> list[SearchHit]:
        rows = ((payload.get("results") or {}).get("bindings")) or []
        sites = [r["site"]["value"] for r in rows if isinstance(r, dict) and r.get("site", {}).get("value")]
        return [SearchHit(u, provider, i, "P7011", "Wikidata P856", "") for i, u in enumerate(dict.fromkeys(sites))]

    def search(self, identity: RegistryIdentity) -> list[SearchHit]:
        if not identity.ogrn or not re.fullmatch(r"\d{13}|\d{15}", identity.ogrn.value):
            return []
        q = f'SELECT ?site WHERE {{ ?i wdt:P7011 "{identity.ogrn.value}" . ?i wdt:P856 ?site }} LIMIT 5'
        body = self.fetcher.request_json(f"{self.URL}?{urlencode({'query': q, 'format': 'json'})}",
                                         {"Accept": "application/sparql-results+json"})
        return self.parse(body)


_TRANSLIT = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
             "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh",
             "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}
_TRANSLIT_ALT = {**_TRANSLIT, "х": "h", "ц": "c", "щ": "sch", "ю": "u", "й": "i"}
_GENERIC_WORDS = {"компания", "торговый", "дом", "группа", "производственное", "объединение", "предприятие", "центр", "фирма",
                  "научно", "производственная", "холдинг", "управление", "комбинат"}


def translit(s: str, table: dict[str, str] = _TRANSLIT) -> str:
    return "".join(table.get(ch, ch) for ch in s.lower())


def name_domains(identity: RegistryIdentity, tlds: tuple[str, ...] = ("ru", "com", "рф"), limit: int = 8) -> list[str]:
    """Bounded host guesses from the legal-name core. Never a fact: kept only when DNS resolves, then identity-verified."""
    cores = name_cores(identity)
    if not cores:
        return []
    words = [w for w in re.split(r"[^\wё-]+", cores[0].replace("ё", "е")) if w]
    meaningful = [w for w in words if w not in _GENERIC_WORDS] or words
    slugs_cyr = ["-".join(meaningful), "".join(meaningful)]
    out: list[str] = []
    for table in (_TRANSLIT, _TRANSLIT_ALT):
        for sc in slugs_cyr:
            lat = re.sub(r"[^a-z0-9-]", "", translit(sc, table)).strip("-")
            if len(lat) >= 3:
                for tld in tlds:
                    if tld == "рф":
                        continue
                    out.append(f"{lat}.{tld}")
    if "рф" in tlds:
        cyr = re.sub(r"[^а-я0-9-]", "", slugs_cyr[0]).strip("-")
        if len(cyr) >= 3:
            out.append(f"{cyr}.рф")
    return list(dict.fromkeys(out))[:limit]


def _resolves(host: str, timeout: float) -> bool:
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(socket.getaddrinfo, ascii_host, 443)
        try:
            return bool(fut.result(timeout=timeout))
        except (concurrent.futures.TimeoutError, OSError, UnicodeError):
            return False


class LegalNameDomainSearch:
    """Domains derived from the legal-name core, kept when they resolve in DNS (no web search)."""
    name, role = "LEGAL_NAME_DOMAIN", "PRIMARY"

    def __init__(self, resolver: Callable[[str], bool] | None = None, timeout: float = 3.0, max_hosts: int = 6) -> None:
        self.resolver = resolver or (lambda h: _resolves(h, timeout))
        self.max_hosts = max_hosts

    def search(self, identity: RegistryIdentity) -> list[SearchHit]:
        hosts = name_domains(identity)[:self.max_hosts]
        return [SearchHit(f"https://{h}/", self.name, i, h, "", "") for i, h in enumerate(hosts) if self.resolver(h)]


class RegistryHintSearch:
    """Website hint published by an optional registry mirror (checko.ru). OPTIONAL_SECONDARY_HINT: never required."""
    name, role = "REGISTRY_MIRROR_HINT", "OPTIONAL_SECONDARY_HINT"

    def search(self, identity: RegistryIdentity) -> list[SearchHit]:
        return [SearchHit(h.value, self.name, i, None, "registry mirror hint", "") for i, h in enumerate(identity.website_hints)]


# ------------------------------------------------------------------------------------------------------------ composite
PROVIDER_PRIOR = {"STORED_OFFICIAL_SITE": 200, "EGRUL_EMAIL_DOMAIN": 100, "WIKIDATA_OGRN": 90, "BRAVE_SEARCH_API": 60,
                  "YANDEX_SEARCH_API": 60, "REGISTRY_MIRROR_HINT": 45, "LEGAL_NAME_DOMAIN": 20}


def score_hit(hit: SearchHit, identity: RegistryIdentity) -> float:
    s = PROVIDER_PRIOR.get(hit.provider, 10) - hit.rank
    hay = f"{hit.title} {hit.snippet} {hit.url}"
    if identity.inn in hay:
        s += 30
    if identity.ogrn and identity.ogrn.value in hay:
        s += 30
    if any(c in _fold(hay) for c in name_cores(identity)):
        s += 10
    return s


@dataclass
class DiscoveryLog:
    attempts: list[SourceAttempt] = field(default_factory=list)
    rejected: list[tuple[str, str, str]] = field(default_factory=list)   # (url, category, provider)


class WebsiteDiscovery:
    """Runs the configured providers (each behind its own circuit breaker), drops non-company hosts, deduplicates by
    registrable domain and returns at most `max_candidates` candidates, best first. Implements WebsiteDiscoveryProvider."""
    name = "WEBSITE_DISCOVERY"

    def __init__(self, providers: list[WebsiteSearchProvider], now: Callable, max_candidates: int = MAX_CANDIDATES,
                 breakers: dict[str, CircuitBreaker] | None = None) -> None:
        self.providers, self.now, self.max_candidates = providers, now, max_candidates
        self.breakers = breakers if breakers is not None else {p.name: CircuitBreaker(threshold=2, cooldown_s=900.0) for p in providers}
        self.last_log = DiscoveryLog()

    def discover(self, identity: RegistryIdentity) -> list[WebsiteCandidate]:
        log = DiscoveryLog()
        hits: list[SearchHit] = []
        for p in self.providers:
            br = self.breakers.setdefault(p.name, CircuitBreaker(threshold=2, cooldown_s=900.0))
            t0 = time.perf_counter()
            if br.is_open:
                br.skipped += 1
                log.attempts.append(SourceAttempt(p.name, SourceOutcome.SKIPPED, "circuit open", 0))
                continue
            try:
                found = p.search(identity)
            except SourceUnavailable as e:
                br.record(isinstance(e, SourceRateLimited))
                log.attempts.append(SourceAttempt(p.name, outcome_of(e), str(e)[:200], int((time.perf_counter() - t0) * 1000)))
                continue
            except Exception as e:  # a provider bug must never break the supplier (one supplier never breaks the batch)
                log.attempts.append(SourceAttempt(p.name, SourceOutcome.UNAVAILABLE, f"{type(e).__name__}: {e}"[:200],
                                                  int((time.perf_counter() - t0) * 1000)))
                continue
            br.record(False)
            log.attempts.append(SourceAttempt(p.name, SourceOutcome.OK if found else SourceOutcome.NOT_FOUND,
                                              f"{len(found)} hit(s)", int((time.perf_counter() - t0) * 1000)))
            hits += found
        best: dict[str, tuple[float, SearchHit]] = {}
        for h in hits:
            host = host_of(h.url)
            if not host or not urlsplit(h.url).scheme.startswith("http"):
                continue
            cls = classify_host(host)
            if cls:
                log.rejected.append((h.url, cls, h.provider))
                continue
            dom = registrable_domain(host)
            sc = score_hit(h, identity)
            if dom not in best or sc > best[dom][0]:
                best[dom] = (sc, h)
        ranked = sorted(best.values(), key=lambda t: (-t[0], t[1].url))[:self.max_candidates]
        self.last_log = log
        now = self.now()
        return [WebsiteCandidate(h.url, Sourced(h.url, h.url, SourceType.FIRST_PARTY, now), provider=h.provider, rank=i,
                                 hint=(h.query or h.title or None))
                for i, (_, h) in enumerate(ranked)]


def build_discovery(fetcher: HttpFetcher, now: Callable, env: dict[str, str], use_secondary_hint: bool = True) -> WebsiteDiscovery:
    """Providers from configuration. Search APIs are enabled only when their keys are present; the other providers need no
    key. ENRICHMENT_DOMAIN_GUESS=off / ENRICHMENT_WIKIDATA=off disable those providers."""
    providers: list[WebsiteSearchProvider] = [EgrulEmailDomainSearch()]
    if env.get("BRAVE_SEARCH_API_KEY"):
        providers.append(BraveSearchApi(env["BRAVE_SEARCH_API_KEY"], fetcher))
    if env.get("YANDEX_SEARCH_API_KEY") and env.get("YANDEX_SEARCH_FOLDER_ID"):
        providers.append(YandexSearchApi(env["YANDEX_SEARCH_API_KEY"], env["YANDEX_SEARCH_FOLDER_ID"], fetcher))
    if env.get("ENRICHMENT_WIKIDATA", "on") != "off":
        providers.append(WikidataOgrnSearch(fetcher))
    if env.get("ENRICHMENT_DOMAIN_GUESS", "on") != "off":
        providers.append(LegalNameDomainSearch())
    if use_secondary_hint:
        providers.append(RegistryHintSearch())
    return WebsiteDiscovery(providers, now)


def provider_names(d: WebsiteDiscovery) -> list[str]:
    return [p.name for p in d.providers]

