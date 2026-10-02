"""P5-001A provider interfaces and the MVP implementations actually reachable during the hackathon.

Interfaces (the service layer depends only on these; a paid registry/data provider plugs in without touching the pipeline):
  CompanyRegistryProvider.lookup_by_inn(inn)                      -> RegistryIdentity | None (raises SourceUnavailable)
  WebsiteDiscoveryProvider.discover(identity)                      -> list[WebsiteCandidate]
  WebsiteVerifier.verify_company_site(identity, candidate)         -> WebsiteVerification
  ContactExtractor.extract(identity, verification)                 -> list[ContactValue]   (official sites only)
  RoleEvidenceProvider.collect(identity, verification)             -> list[RoleEvidenceItem]

MVP implementations:
  FnsEgrulRegistry      egrul.nalog.ru (official FNS search): legal name, short name, OGRN, KPP, region, registration date,
                        ceased/active. Director names returned by the service are never read.
  CheckoRegistryMirror  checko.ru (FNS-derived mirror, used in P4-005C for legal address): registered address, primary OKVED,
                        website hint. Accepted only when its INN and OGRN match. Its phones/e-mails are NOT used
                        (aggregated, possibly personal or outdated).
  RegistryWebsiteDiscovery  website hints from the registry mirror (candidates only; OPTIONAL_SECONDARY_HINT).
  P5-002A website search providers (EGRUL e-mail domain, search APIs, Wikidata, legal-name domains): app/enrichment/discovery.py
  HttpWebsiteVerifier   fetches the candidate's site root + a bounded set of same-host high-value pages (requisites, contacts,
                        about, policy, catalog); robots.txt respected. Official only if this company's INN or OGRN is published
                        there as self-identification (not inside a warning notice; not on a directory-like page listing many
                        companies) = VERIFIED_STRONG, or its exact legal name + registered street address / KPP = VERIFIED_COMPOSITE.
  HtmlContactExtractor  general phones / e-mails from verified first-party pages; personal-context values, fax lines and
                        unrelated third-party e-mail domains are dropped; every value carries its verification basis.
  SiteAndOkvedRoleEvidence  OKVED -> INFERRED only; first-party production/distribution claims -> UNDER_REVIEW only.
"""
from __future__ import annotations

import html as htmlmod
import json
import re
import time
from dataclasses import replace
from datetime import date, datetime
from typing import Callable, Protocol
from urllib.parse import urljoin, urlsplit

from app.enrichment import freshness as F
from app.enrichment.profile_models import (ContactType, ContactValue, Page, RegistryIdentity, Role, RoleEvidenceItem, RoleStatus,
                                           SourceAttempt, SourceOutcome, SourceRateLimited, SourceSkipped, SourceType,
                                           SourceUnavailable, Sourced, Strength, WebsiteCandidate, WebsiteConfidence,
                                           WebsiteVerification, WebsiteVerificationStatus, outcome_of)

USER_AGENT = "SupplierRadar-Enrichment/0.2 (RLT.Hack 2026 research prototype; public business data only)"
ROBOTS_AGENT = "SupplierRadar-Enrichment"
MAX_BYTES = 1_500_000


# ------------------------------------------------------------------------------------------------------------ interfaces
class CompanyRegistryProvider(Protocol):
    name: str

    def lookup_by_inn(self, inn: str) -> RegistryIdentity | None: ...


class WebsiteDiscoveryProvider(Protocol):
    name: str

    def discover(self, identity: RegistryIdentity) -> list[WebsiteCandidate]: ...


class WebsiteVerifier(Protocol):
    name: str

    def verify_company_site(self, identity: RegistryIdentity, candidate: WebsiteCandidate) -> WebsiteVerification: ...


class ContactExtractor(Protocol):
    name: str

    def extract(self, identity: RegistryIdentity, verification: WebsiteVerification) -> list[ContactValue]: ...


class RoleEvidenceProvider(Protocol):
    name: str

    def collect(self, identity: RegistryIdentity, verification: WebsiteVerification | None) -> list[RoleEvidenceItem]: ...


# ------------------------------------------------------------------------------------------------------------ HTTP
class HttpFetcher:
    """Small polite HTTP client: per-host minimum interval (stricter for registry mirrors), timeouts, size cap, charset
    detection. No retries storm: a 429/503 is waited out once (Retry-After, capped) and retried once, then reported."""

    RATE_LIMITED = (429, 503)

    def __init__(self, timeout: float = 8.0, min_interval: float = 1.0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, host_intervals: dict[str, float] | None = None,
                 max_backoff: float = 30.0, default_backoff: float = 10.0, transport=None) -> None:
        import httpx
        self._httpx = httpx
        self.timeout, self.min_interval, self._clock, self._sleep = timeout, min_interval, clock, sleep
        self.host_intervals, self.max_backoff, self.default_backoff = host_intervals or {}, max_backoff, default_backoff
        self._last: dict[str, float] = {}
        self._robots: dict[str, object] = {}     # host -> RobotFileParser | None (None = no usable robots.txt -> allowed)
        self._client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(timeout), transport=transport,
                                    headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.5"})
        self._insecure = None

    def _interval(self, host: str) -> float:
        for h, iv in self.host_intervals.items():
            if host == h or host.endswith("." + h):
                return max(iv, self.min_interval)
        return self.min_interval

    def _wait(self, url: str) -> None:
        host = urlsplit(url).hostname or ""
        last = self._last.get(host)
        if last is not None:
            delta = self._interval(host) - (self._clock() - last)
            if delta > 0:
                self._sleep(delta)
        self._last[host] = self._clock()

    def _backoff(self, resp) -> float | None:
        """Seconds to wait before the single retry of a rate-limited response, or None when the server asks for too long."""
        ra = (resp.headers.get("retry-after") or "").strip()
        wait = float(ra) if ra.isdigit() else self.default_backoff
        return wait if wait <= self.max_backoff else None

    def request(self, method: str, url: str, data: dict | None = None, headers: dict | None = None) -> tuple[str, str]:
        """(final_url, decoded text). Raises SourceUnavailable on any transport / HTTP error (SourceRateLimited on 429/503)."""
        resp = self._send(method, url, data, headers)
        return str(resp.url), decode(resp.content[:MAX_BYTES], resp.headers.get("content-type", ""))

    def request_json(self, url: str, headers: dict | None = None) -> dict:
        """GET a JSON API (search APIs, Wikidata). Non-JSON answers are a source failure, never parsed loosely."""
        _, body = self.request("GET", url, None, headers)
        try:
            out = json.loads(body)
        except ValueError as e:
            raise SourceUnavailable(f"non-JSON answer from {urlsplit(url).hostname}") from e
        if not isinstance(out, dict):
            raise SourceUnavailable(f"unexpected JSON from {urlsplit(url).hostname}")
        return out

    def get_bytes(self, url: str) -> bytes:
        resp = self._send("GET", url, None)
        if len(resp.content) > MAX_BYTES:
            raise SourceUnavailable(f"response larger than {MAX_BYTES} bytes")
        return resp.content

    def _send(self, method: str, url: str, data: dict | None, headers: dict | None = None):
        self._wait(url)
        try:
            try:
                try:
                    resp = self._client.request(method, url, data=data, headers=headers)
                except self._httpx.TimeoutException:   # one retry: small sites are often slow on the first byte
                    resp = self._client.request(method, url, data=data, headers=headers)
            except self._httpx.ConnectError as e:  # e.g. Russian-CA certificates: retry once without TLS verification
                if "CERTIFICATE" not in str(e).upper():
                    raise
                if self._insecure is None:
                    self._insecure = self._httpx.Client(follow_redirects=True, verify=False,
                                                        timeout=self._httpx.Timeout(self.timeout),
                                                        headers={"User-Agent": USER_AGENT})
                resp = self._insecure.request(method, url, data=data)
        except self._httpx.HTTPError as e:
            raise SourceUnavailable(f"{type(e).__name__}: {e}"[:200]) from e
        if resp.status_code in self.RATE_LIMITED:
            wait = self._backoff(resp)
            if wait is None:
                raise SourceRateLimited(f"HTTP {resp.status_code} (Retry-After too long)")
            self._sleep(wait)
            self._last[urlsplit(url).hostname or ""] = self._clock()
            try:
                resp = self._client.request(method, url, data=data, headers=headers)
            except self._httpx.HTTPError as e:
                raise SourceUnavailable(f"{type(e).__name__}: {e}"[:200]) from e
            if resp.status_code in self.RATE_LIMITED:
                raise SourceRateLimited(f"HTTP {resp.status_code} after one backoff")
        if resp.status_code >= 400:
            raise SourceUnavailable(f"HTTP {resp.status_code}")
        return resp

    def get(self, url: str, robots: bool = False) -> tuple[str, str]:
        """robots=True (first-party company sites): refuse URLs the site's robots.txt disallows for our agent."""
        if robots and not self.allowed(url):
            raise SourceSkipped(f"robots.txt disallows {urlsplit(url).path or '/'}")
        return self.request("GET", url)

    def allowed(self, url: str) -> bool:
        """robots.txt check, cached per host. An unreachable / missing / unparsable robots.txt allows (RFC 9309 §2.3.1.3)."""
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            from urllib.robotparser import RobotFileParser
            rp = None
            try:
                resp = self._send("GET", host + "/robots.txt", None)
                if resp.status_code == 200 and "html" not in resp.headers.get("content-type", "").lower():
                    rp = RobotFileParser()
                    rp.parse(decode(resp.content[:65536], resp.headers.get("content-type", "")).splitlines())
            except SourceUnavailable:
                rp = None
            self._robots[host] = rp
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(ROBOTS_AGENT, url)

    def post(self, url: str, data: dict) -> tuple[str, str]:
        return self.request("POST", url, data)

    def close(self) -> None:
        self._client.close()
        if self._insecure is not None:
            self._insecure.close()


_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.I)


def decode(raw: bytes, content_type: str = "") -> str:
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    cands = [m.group(1)] if m else []
    mm = _META_CHARSET.search(raw[:4096])
    if mm:
        cands.append(mm.group(1).decode("ascii", "ignore"))
    for enc in cands + ["utf-8", "cp1251"]:
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


_SCRIPT = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def html_to_text(html: str) -> str:
    return _WS.sub(" ", htmlmod.unescape(_TAG.sub(" ", _SCRIPT.sub(" ", html)))).strip()


def _fold(s: str) -> str:
    return _WS.sub(" ", s.casefold().replace("ё", "е").replace("«", '"').replace("»", '"').replace("“", '"')
                   .replace("”", '"')).strip()


# ------------------------------------------------------------------------------------------------------------ registries
EGRUL_URL = "https://egrul.nalog.ru/"
EGRUL_PUBLIC_URL = "https://egrul.nalog.ru/index.html"


def parse_egrul_rows(payload: dict, inn: str, checked_at: datetime) -> RegistryIdentity | None:
    """Pure parser of the egrul.nalog.ru search-result JSON. Prefers the non-ceased row for the INN. Ignores `g` (director)."""
    rows = [r for r in payload.get("rows", []) if r.get("i") == inn]
    if not rows:
        return None
    rows.sort(key=lambda r: (bool(r.get("e")), r.get("o", "")))
    r = rows[0]

    def s(v):
        return Sourced(v, EGRUL_PUBLIC_URL, SourceType.FNS_EGRUL, checked_at) if v else None

    reg = None
    if r.get("r"):
        try:
            reg = datetime.strptime(r["r"], "%d.%m.%Y").date()
        except ValueError:
            reg = None
    kind = "INDIVIDUAL_ENTREPRENEUR" if r.get("k") == "fl" else "LEGAL_ENTITY"
    return RegistryIdentity(
        inn=inn, entity_kind=kind, legal_name=s(r.get("n")), short_name=s(r.get("c")), ogrn=s(r.get("o")),
        kpp=s(r.get("p")) if kind == "LEGAL_ENTITY" else None,
        legal_status=s("CEASED" if r.get("e") else "ACTIVE"), region=s(r.get("rn")), registration_date=reg)


# Official EGRUL / EGRIP extract (выписка, PDF) — the FNS source of the registered address and the primary OKVED.
_EXTRACT_FOOTER = re.compile(r"^(?:Страница \d+ из.*|Выписка из ЕГР(?:ЮЛ|ИП)|\d{2}\.\d{2}\.\d{4} \d{2}:\d{2} ОГРН(?:ИП)? \d+)\s*$")
# Identity of the extract: the spaced-digit header (ИНН 7 8 0 4 …, ОГРН 1 0 2 7 …) or the "ИНН юридического лица" row.
# Other "ИНН" rows belong to people (director, founders) and are never read.
_EXTRACT_HEADER_INN = re.compile(r"^ИНН\s+((?:\d\s+){9,11}\d)\s*$", re.M)
_EXTRACT_HEADER_OGRN = re.compile(r"^ОГРН(?:ИП)?\s+((?:\d\s+){12,14}\d)\s*$", re.M)
_EXTRACT_ROW_INN = re.compile(r"ИНН юридического лица\s+(\d{10})")
_EXTRACT_ADDRESS = re.compile(r"(?:^|\n)\d+\s+Адрес(?: \(место нахождения\))? юридического лица\s+(.*?)\n\d+\s+ГРН", re.S)
_EXTRACT_OKVED = re.compile(r"Сведения об основном виде деятельности.*?Код и наименование вида деятельности\s+"
                            r"(\d{2}(?:\.\d{1,2}){0,3})\s+(.*?)\n\d+\s+ГРН", re.S)


_EXTRACT_EMAIL = re.compile(r"(?:^|\n)\d+\s+E-?mail\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24})", re.I)


def parse_egrul_email(text: str, checked_at: datetime) -> Sourced | None:
    """E-mail registered in EGRUL («Адрес электронной почты … E-mail X»). Called only after parse_egrul_extract accepted the
    extract's identity. Lower-cased; never inferred."""
    body = "\n".join(ln.rstrip() for ln in text.splitlines() if not _EXTRACT_FOOTER.match(ln.strip()))
    m = _EXTRACT_EMAIL.search(body)
    return Sourced(m.group(1).lower(), EGRUL_PUBLIC_URL, SourceType.FNS_EGRUL, checked_at) if m else None


class ExtractMismatch(ValueError):
    """The extract does not belong to the requested INN (never used)."""


def _digits(m: re.Match | None) -> str | None:
    return re.sub(r"\s", "", m.group(1)) if m else None


def parse_egrul_extract(text: str, inn: str, checked_at: datetime,
                        ogrn: str | None = None) -> tuple[Sourced | None, Sourced | None]:
    """Pure parser of the official extract text: (registered address, primary OKVED "code name"). Page headers/footers are
    removed first so a field split across pages stays whole. Raises ExtractMismatch unless the extract is this company's: its
    INN (header or legal-entity row) equals the INN, or — when it carries no company INN — its header OGRN equals the OGRN of
    the registry search row. Any contradicting INN / OGRN rejects it."""
    body = "\n".join(ln.rstrip() for ln in text.splitlines() if not _EXTRACT_FOOTER.match(ln.strip()))
    inns = {v for v in (_digits(_EXTRACT_HEADER_INN.search(body)), _digits(_EXTRACT_ROW_INN.search(body))) if v}
    h_ogrn = _digits(_EXTRACT_HEADER_OGRN.search(body))
    if inns - {inn} or (ogrn and h_ogrn and h_ogrn != ogrn):
        raise ExtractMismatch("extract INN / OGRN contradicts the registry record")
    if inn not in inns and not (ogrn and h_ogrn == ogrn):
        raise ExtractMismatch("extract identity not confirmed (no matching INN or OGRN)")

    def s(v):
        return Sourced(v, EGRUL_PUBLIC_URL, SourceType.FNS_EGRUL, checked_at) if v else None

    a = _EXTRACT_ADDRESS.search(body)
    o = _EXTRACT_OKVED.search(body)
    address = _WS.sub(" ", a.group(1)).strip().rstrip(",") if a else None
    okved = f"{o.group(1)} {_WS.sub(' ', o.group(2)).strip()}" if o else None
    return s(address), s(okved)


def pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # deployment without the enrichment extra: identity still works, extract fields stay empty
        raise SourceUnavailable("pypdf is not installed (requirements-enrichment.txt)") from e
    import io
    try:
        return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages)
    except Exception as e:  # malformed / truncated PDF
        raise SourceUnavailable(f"unreadable extract PDF: {type(e).__name__}") from e


class FnsEgrulRegistry:
    """egrul.nalog.ru: the search result (name, OGRN, KPP, status, registration date, region) plus the official extract
    (registered address, primary OKVED). The extract is a sub-step: when it fails, identity is still returned and the failure
    is recorded as a FNS_EGRUL_EXTRACT sub-attempt."""
    name = "FNS_EGRUL"
    EXTRACT = "FNS_EGRUL_EXTRACT"

    def __init__(self, fetcher: HttpFetcher, now: Callable[[], datetime], polls: int = 4, extract_polls: int = 8,
                 with_extract: bool = True) -> None:
        self.fetcher, self.now, self.polls, self.extract_polls, self.with_extract = fetcher, now, polls, extract_polls, with_extract

    @staticmethod
    def _json(body: str, what: str) -> dict:
        try:
            return json.loads(body)
        except ValueError as e:
            raise SourceUnavailable(f"EGRUL: non-JSON {what}") from e

    def _search(self, inn: str) -> dict:
        _, body = self.fetcher.post(EGRUL_URL, {"query": inn})
        token = self._json(body, "token response")
        if token.get("captchaRequired") or not token.get("t"):
            raise SourceUnavailable("EGRUL: captcha required / no token")
        for _ in range(self.polls):
            _, body = self.fetcher.get(f"{EGRUL_URL}search-result/{token['t']}")
            payload = self._json(body, "result")
            if payload.get("status") != "wait":
                return payload
        raise SourceUnavailable("EGRUL: result not ready")

    def _extract_text(self, row_token: str) -> str:
        req = self._json(self.fetcher.get(f"{EGRUL_URL}vyp-request/{row_token}")[1], "extract request")
        if req.get("captchaRequired"):
            raise SourceUnavailable("EGRUL extract: captcha required")
        for _ in range(self.extract_polls):
            st = self._json(self.fetcher.get(f"{EGRUL_URL}vyp-status/{row_token}")[1], "extract status")
            if st.get("status") == "ready":
                return pdf_text(self.fetcher.get_bytes(f"{EGRUL_URL}vyp-download/{row_token}"))
        raise SourceUnavailable("EGRUL extract: not ready")

    def lookup_by_inn(self, inn: str) -> RegistryIdentity | None:
        payload = self._search(inn)
        ident = parse_egrul_rows(payload, inn, self.now())
        if ident is None or not self.with_extract:
            return ident
        rows = sorted((r for r in payload.get("rows", []) if r.get("i") == inn), key=lambda r: (bool(r.get("e")), r.get("o", "")))
        token = rows[0].get("t") if rows else None
        if not token:
            return replace(ident, sub_attempts=(SourceAttempt(self.EXTRACT, SourceOutcome.NOT_FOUND, "no extract token"),))
        t0 = time.perf_counter()
        try:
            text = self._extract_text(token)
            address, okved = parse_egrul_extract(text, inn, self.now(), ident.ogrn.value if ident.ogrn else None)
        except (ExtractMismatch, SourceUnavailable) as e:
            outcome = SourceOutcome.REJECTED if isinstance(e, ExtractMismatch) else outcome_of(e)
            return replace(ident, sub_attempts=(SourceAttempt(self.EXTRACT, outcome, str(e)[:200],
                                                              int((time.perf_counter() - t0) * 1000)),))
        email = parse_egrul_email(text, self.now())
        if ident.entity_kind != "LEGAL_ENTITY":
            address = email = None   # an entrepreneur's residence address / e-mail are personal data
        found = [k for k, v in (("address", address), ("okved", okved), ("email", email)) if v]
        return replace(ident, registered_address=address, primary_okved=okved, registered_email=email,
                       sub_attempts=(SourceAttempt(self.EXTRACT, SourceOutcome.OK, "fields: " + (", ".join(found) or "none"),
                                                   int((time.perf_counter() - t0) * 1000)),))


# ------------------------------------------------------------------------------------------------------------ circuit breaker
class CircuitBreaker:
    """Per-process breaker for an optional provider: after `threshold` consecutive rate-limited answers the provider is not
    called again until `cooldown_s` has passed (None = for the lifetime of the breaker, i.e. the rest of the batch)."""

    def __init__(self, threshold: int = 2, cooldown_s: float | None = 900.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.threshold, self.cooldown_s, self._clock = threshold, cooldown_s, clock
        self.reset()

    def reset(self) -> None:
        self.consecutive, self.opened_at, self.skipped = 0, None, 0

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if self.cooldown_s is not None and self._clock() - self.opened_at >= self.cooldown_s:
            self.consecutive, self.opened_at = 0, None     # half-open: the next call probes the source again
            return False
        return True

    def record(self, rate_limited: bool) -> None:
        self.consecutive = self.consecutive + 1 if rate_limited else 0
        if self.consecutive >= self.threshold and self.opened_at is None:
            self.opened_at = self._clock()


class GuardedRegistry:
    """Wraps an optional registry provider with a CircuitBreaker (same name, so attempts stay attributable)."""

    def __init__(self, inner, breaker: CircuitBreaker) -> None:
        self.inner, self.breaker, self.name = inner, breaker, inner.name

    def lookup_by_inn(self, inn: str) -> RegistryIdentity | None:
        if self.breaker.is_open:
            self.breaker.skipped += 1
            raise SourceSkipped(f"circuit open after {self.breaker.threshold} consecutive rate-limited responses")
        try:
            out = self.inner.lookup_by_inn(inn)
        except SourceUnavailable as e:
            self.breaker.record(isinstance(e, SourceRateLimited))
            raise
        self.breaker.record(False)
        return out


CHECKO_SEARCH = "https://checko.ru/search?query={inn}"
_LD = re.compile(r"<script type=['\"]application/ld\+json['\"]>(.*?)</script>", re.S)
_CHECKO_ADDR = re.compile(r'id="copy-address"[^>]*>([^<]+)<')
_CHECKO_OKVED = re.compile(r'<td[^>]*>\s*(\d{2}(?:\.\d{1,2}){0,3})\s*</td>\s*<td>(?:<a[^>]*>)?([^<]+)(?:</a>)?'
                           r'<span class="question"[^>]*data-bs-title="Основной вид деятельности"')
_CHECKO_SITE = re.compile(r'Веб-сайт</strong>\s*<a[^>]*href="(https?://[^"]+)"')


def parse_checko(page_html: str, inn: str, page_url: str, checked_at: datetime) -> RegistryIdentity | None:
    """Pure parser of a checko.ru company page; None unless the page's schema.org taxID is exactly this INN."""
    org = None
    for m in _LD.finditer(page_html):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") == "Organization":
            org = d
    if not org or org.get("taxID") != inn:
        return None
    ids = {p.get("propertyID"): p.get("value") for p in org.get("identifier", []) if isinstance(p, dict)}

    def s(v):
        return Sourced(htmlmod.unescape(v).strip(), page_url, SourceType.FNS_EGRUL_DERIVED_REGISTRY, checked_at) if v else None

    text = html_to_text(page_html[:200_000])
    status = None
    if "Действующая компания" in text:
        status = "ACTIVE"
    elif re.search(r"Организация ликвидирована|прекратила деятельность|Ликвидирована", text):
        status = "CEASED"
    addr = _CHECKO_ADDR.search(page_html)
    okved = _CHECKO_OKVED.search(page_html)
    site = _CHECKO_SITE.search(page_html)
    region = (org.get("address") or {}).get("addressRegion") if isinstance(org.get("address"), dict) else None
    return RegistryIdentity(
        inn=inn, entity_kind="LEGAL_ENTITY" if len(inn) == 10 else "INDIVIDUAL_ENTREPRENEUR",
        legal_name=s(org.get("legalName") or org.get("name")), short_name=s(org.get("name")), ogrn=s(ids.get("ОГРН")),
        kpp=s(ids.get("КПП")), legal_status=s(status), region=s(region),
        registered_address=s(addr.group(1)) if addr else None,
        primary_okved=s(f"{okved.group(1)} {htmlmod.unescape(okved.group(2)).strip()}") if okved else None,
        website_hints=(s(site.group(1)),) if site else ())


class CheckoRegistryMirror:
    name = "CHECKO_REGISTRY_MIRROR"

    def __init__(self, fetcher: HttpFetcher, now: Callable[[], datetime]) -> None:
        self.fetcher, self.now = fetcher, now

    def lookup_by_inn(self, inn: str) -> RegistryIdentity | None:
        url, body = self.fetcher.get(CHECKO_SEARCH.format(inn=inn))
        if "/company/" not in url and "/entrepreneur/" not in url:
            return None
        return parse_checko(body, inn, url, self.now())


def merge_identities(primary: RegistryIdentity | None, mirror: RegistryIdentity | None) -> tuple[RegistryIdentity | None, str | None]:
    """Primary (official) fields win; the mirror only fills gaps and is rejected when its OGRN contradicts the primary."""
    if primary is None:
        return mirror, None
    if mirror is None:
        return primary, None
    if primary.ogrn and mirror.ogrn and primary.ogrn.value != mirror.ogrn.value:
        return primary, "MIRROR_OGRN_MISMATCH"
    fields = {}
    for name in ("short_name", "ogrn", "kpp", "legal_status", "region", "registered_address", "primary_okved"):
        fields[name] = getattr(primary, name) or getattr(mirror, name)
    return RegistryIdentity(inn=primary.inn, entity_kind=primary.entity_kind, legal_name=primary.legal_name,
                            registration_date=primary.registration_date, website_hints=mirror.website_hints,
                            registered_email=primary.registered_email, sub_attempts=primary.sub_attempts, **fields), None


# ------------------------------------------------------------------------------------------------------------ website
_BLOCKED_HOSTS = ("checko.ru", "rusprofile.ru", "list-org.com", "zachestnyibiznes.ru", "sbis.ru", "vk.com", "ok.ru",
                  "t.me", "facebook.com", "instagram.com", "youtube.com", "yandex.ru", "2gis.ru", "avito.ru", "hh.ru")


def host_of(url: str) -> str:
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


class RegistryWebsiteDiscovery:
    name = "REGISTRY_WEBSITE_HINT"

    def discover(self, identity: RegistryIdentity) -> list[WebsiteCandidate]:
        out, seen = [], set()
        for hint in identity.website_hints:
            h = host_of(hint.value)
            if not h or h in seen or any(h == b or h.endswith("." + b) for b in _BLOCKED_HOSTS):
                continue
            seen.add(h)
            out.append(WebsiteCandidate(hint.value, hint))
        return out


_LINK = re.compile(r"""<a\s[^>]*href=["']([^"'#]+)["'][^>]*>(.*?)</a>""", re.S | re.I)
# link hints by priority: requisites pages carry INN/OGRN most often, then contacts, privacy policy, about
_LINK_HINTS = (
    re.compile(r"rekvizit|requisit|реквизит|svedeniya|сведения о", re.I),
    re.compile(r"kontakt|contact|контакт", re.I),
    re.compile(r"politik|privacy|konfidenc|personal|политик|конфиденц|персональн", re.I),
    re.compile(r"about|o-kompanii|o_kompanii|o-nas|company|о компании|о нас|documents|dokument|документ|/doc\b", re.I),
    re.compile(r"catalog|katalog|products|produkci|каталог|продукци", re.I),   # P5-002A: role/product evidence, lowest priority
)
_COPYRIGHT = re.compile(r"(?:©|&copy;|copyright|\(c\))\s*(?:(?:19|20)\d{2}\s*(?:[-–—]|&ndash;|&mdash;)\s*)?((?:19|20)\d{2})", re.I)
_LOCALITY = re.compile(r"(?:^|[\s,])(?:г|город|д|с|пос|пгт|рп|п|ст-ца|х)(?:\.\s*|\s+)([А-ЯЁ][А-Яа-яЁё-]{2,})", re.I)
_STREET = re.compile(r"(?:^|(?<=[\s,.]))(?:ул|улица|пр-кт|проспект|пр|пер|переулок|ш|шоссе|наб|набережная|б-р|бульвар|пл|площадь|проезд|тракт|мкр)"
                     r"\.?\s+([А-ЯЁ0-9][А-Яа-яЁё0-9-]{2,})", re.I)
_HOUSE = re.compile(r"(?:^|[\s,])(?:д|дом|зд|здание|влд|владение)\.?\s*(\d+)", re.I)
_NAME_CORE = re.compile(r'"([^"]{3,})"')
_LEGAL_FORMS = re.compile(
    r"^(?:общество с ограниченной ответственностью|акционерное общество|публичное акционерное общество|закрытое акционерное "
    r"общество|открытое акционерное общество|непубличное акционерное общество|федеральное государственное (?:казенное|бюджетное|"
    r"унитарное)? ?(?:учреждение|предприятие)|государственное (?:бюджетное|казенное|автономное)? ?учреждение|"
    r"индивидуальный предприниматель|ооо|ао|пао|зао|оао|нао|фгку|фгуп|гбу|гку|ип)\s+", re.I)
_QUOTES = re.compile(r"[\"«»“”„'`]")
# a requisites block that warns about impostors: an INN inside it identifies someone the site is NOT
_WARNING = re.compile(r"мошенни|злоумышленн|от имени[^.]{0,80}(?:не является|не являются|не имеет|не связан)|не является[^.]{0,60}"
                      r"(?:сотрудник|представител|сайт|организатор)|не имеет отношения|не принадлеж|поддельн|фальшив|фейков|"
                      r"остерегайтесь|осторожно|убедительно просим|с особым вниманием", re.I)
_INN_LABEL = re.compile(r"ИНН\D{0,12}?(\d{10}|\d{12})(?!\d)")


def contact_links(base_url: str, page_html: str, limit: int = 3) -> list[str]:
    """Same-host links that likely carry requisites / contacts, ordered by hint priority then page order."""
    base_host = host_of(base_url)
    ranked: dict[str, tuple[int, int]] = {}
    for pos, (href, label) in enumerate(_LINK.findall(page_html)):
        hay = href + " " + html_to_text(label)
        prio = next((k for k, rx in enumerate(_LINK_HINTS) if rx.search(hay)), None)
        if prio is None:
            continue
        url = urljoin(base_url, htmlmod.unescape(href.strip()))
        if not url.startswith("http") or host_of(url) != base_host or url.rstrip("/") == base_url.rstrip("/"):
            continue
        if url not in ranked or (prio, pos) < ranked[url]:
            ranked[url] = (prio, pos)
    return [u for u, _ in sorted(ranked.items(), key=lambda kv: kv[1])][:limit]


_META_DATE = re.compile(r"""(?:article:modified_time|og:updated_time|dateModified|datePublished|last-modified)["']?\s*"""
                        r"""(?:content=|:)\s*["']((?:19|20)\d{2})-\d{2}""", re.I)
_TIME_TAG = re.compile(r"""<time[^>]+datetime=["']((?:19|20)\d{2})-\d{2}""", re.I)


def latest_year(pages: list[Page], today: date) -> int | None:
    """Latest content year: copyright notice, page metadata (modified / published time) or <time datetime>. Never the HTTP
    retrieval date. None -> freshness stays UNKNOWN."""
    years = [int(y) for p in pages for y in _COPYRIGHT.findall(p.html) + _COPYRIGHT.findall(p.text)
             + _META_DATE.findall(p.html) + _TIME_TAG.findall(p.html)]
    years = [y for y in years if 1990 <= y <= today.year]
    return max(years) if years else None


def _street_signal(address: str, folded: str) -> bool:
    """Registered street name AND its house number appear together (house number within 40 chars after the street)."""
    st, hs = _STREET.search(address), _HOUSE.search(address)
    if not st or not hs:
        return False
    name = _fold(st.group(1))
    return any(re.search(rf"(?<!\d){hs.group(1)}(?!\d)", folded[m.end():m.end() + 40])
               for m in re.finditer(re.escape(name), folded))


def name_cores(identity: RegistryIdentity) -> list[str]:
    """Folded legal-name cores without the legal form and quotes: «ООО "КОМПАНИЯ "ТЕНЗОР"» -> 'компания тензор'."""
    out = []
    for src in (identity.legal_name, identity.short_name):
        if not src:
            continue
        core = _WS.sub(" ", _QUOTES.sub(" ", _LEGAL_FORMS.sub("", _fold(src.value)))).strip(" -")
        if len(core) >= 3 and core not in out:
            out.append(core)
    return out


def _unquoted(folded: str) -> str:
    return _WS.sub(" ", _QUOTES.sub(" ", folded))


def _self_identified(number: str, texts: list[str]) -> tuple[bool, bool]:
    """(found as self-identification, found only inside a warning context) for an INN / OGRN on the pages."""
    seen = warned = False
    for t in texts:
        for m in re.finditer(rf"(?<!\d){number}(?!\d)", t):
            window = t[max(0, m.start() - 300):m.end() + 500]
            if _WARNING.search(window):
                warned = True
            else:
                seen = True
    return seen, warned and not seen


def assess_identity(identity: RegistryIdentity, pages: list[Page]) -> tuple[WebsiteConfidence, tuple[str, ...]]:
    """Identity-first grading of a candidate site (a similar-looking name alone is never enough):
      HIGH   STRONG: this company's INN or OGRN published on the site as self-identification, or
             COMPOSITE: exact legal-name core + registered street address (street + house), or + this company's KPP
      MEDIUM exact legal-name core + registered locality only  -> NOT official
      LOW    anything else, an INN/OGRN only inside an impostor-warning notice, or a directory-like page set
             (three or more different companies' INNs)            -> rejected"""
    text = " ".join(p.text for p in pages)
    texts = [p.text for p in pages] + [p.html for p in pages]
    signals = []
    inn_ok, inn_warn = _self_identified(identity.inn, texts)
    ogrn_ok, ogrn_warn = _self_identified(identity.ogrn.value, texts) if identity.ogrn else (False, False)
    if inn_ok:
        signals.append("INN_ON_SITE")
    if ogrn_ok:
        signals.append("OGRN_ON_SITE")
    if (inn_warn or ogrn_warn) and not (inn_ok or ogrn_ok):
        signals.append("ID_ONLY_IN_WARNING_CONTEXT")
    if identity.kpp and re.search(rf"(?<![\dA-Z]){identity.kpp.value}(?![\dA-Z])", text):
        signals.append("KPP_ON_SITE")
    folded = _fold(text)
    plain = _unquoted(folded)
    if any(re.search(rf"(?<![\w-]){re.escape(c)}(?![\w])", plain) for c in name_cores(identity)):
        signals.append("EXACT_LEGAL_NAME")
    addr = identity.registered_address.value if identity.registered_address else ""
    loc = _LOCALITY.search(addr)
    if loc and _fold(loc.group(1)) in folded:
        signals.append("REGISTERED_LOCALITY")
    if addr and _street_signal(addr, folded):
        signals.append("REGISTERED_STREET_ADDRESS")
    other_inns = {m.group(1) for m in _INN_LABEL.finditer(text)} - {identity.inn}
    if len(other_inns) >= 3:
        signals.append("DIRECTORY_LIKE")
    sig = set(signals)
    # the company's INN/OGRN appear only inside an impostor warning: the site belongs to someone else, and the name /
    # address / KPP found there come from that same warning -> never a composite match
    if "DIRECTORY_LIKE" in sig or "ID_ONLY_IN_WARNING_CONTEXT" in sig:
        return WebsiteConfidence.LOW, tuple(signals)
    if {"INN_ON_SITE", "OGRN_ON_SITE"} & sig:
        return WebsiteConfidence.HIGH, tuple(signals)
    if "EXACT_LEGAL_NAME" in sig and {"REGISTERED_STREET_ADDRESS", "KPP_ON_SITE"} & sig:
        return WebsiteConfidence.HIGH, tuple(signals)
    if {"EXACT_LEGAL_NAME", "REGISTERED_LOCALITY"} <= sig:
        return WebsiteConfidence.MEDIUM, tuple(signals)
    return WebsiteConfidence.LOW, tuple(signals)


def verification_status(confidence: WebsiteConfidence, signals: tuple[str, ...]) -> WebsiteVerificationStatus:
    if confidence == WebsiteConfidence.HIGH:
        return (WebsiteVerificationStatus.VERIFIED_STRONG if {"INN_ON_SITE", "OGRN_ON_SITE"} & set(signals)
                else WebsiteVerificationStatus.VERIFIED_COMPOSITE)
    return WebsiteVerificationStatus.REJECTED


# tried only when the start page links to no requisites / contact page (bounded high-value paths, P5-002A)
FALLBACK_CONTACT_PATHS = ("/contacts/", "/kontakty/", "/requisites/", "/rekvizity/", "/about/", "/o-kompanii/")


def site_root(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme or 'https'}://{p.netloc}/"


class HttpWebsiteVerifier:
    """Bounded first-party check: site root + at most `extra_pages` same-host high-value pages (requisites, contacts, policy,
    about, catalog), robots.txt respected, per-host delay / timeout / size cap from the fetcher. A search hit's own page is
    read first (it is often the requisites page that matched the INN query)."""
    name = "FIRST_PARTY_WEBSITE"

    def __init__(self, fetcher: HttpFetcher, now: Callable[[], datetime], extra_pages: int = 6) -> None:
        self.fetcher, self.now, self.extra_pages = fetcher, now, extra_pages

    def _get(self, url: str) -> tuple[str, str]:
        if hasattr(self.fetcher, "allowed"):      # HttpFetcher: robots.txt respected on company sites
            return self.fetcher.get(url, robots=True)
        return self.fetcher.get(url)              # test fetchers

    def verify_company_site(self, identity: RegistryIdentity, candidate: WebsiteCandidate) -> WebsiteVerification:
        checked = self.now()
        root = site_root(candidate.url)
        # SourceUnavailable propagates (recorded by the pipeline). A redirect to another domain is assessed on the landing page.
        final_url, body = self._get(root)
        pages = [Page(final_url, body, html_to_text(body))]
        queue = contact_links(final_url, body, self.extra_pages) or [urljoin(final_url, p) for p in FALLBACK_CONTACT_PATHS]
        if candidate.url.rstrip("/") != root.rstrip("/") and host_of(candidate.url) == host_of(final_url):
            queue.insert(0, candidate.url)
        seen = {final_url.rstrip("/"), root.rstrip("/")}
        conf, signals = assess_identity(identity, pages)
        # breadth-first over likely requisites/contact pages (same host, bounded); stop once identity is proven
        while queue and len(pages) <= self.extra_pages and conf != WebsiteConfidence.HIGH:
            url = queue.pop(0)
            if url.rstrip("/") in seen:
                continue
            seen.add(url.rstrip("/"))
            try:
                u, b = self._get(url)
            except SourceUnavailable:
                continue
            if host_of(u) != host_of(final_url):
                continue                       # never follow a page onto another domain
            seen.add(u.rstrip("/"))
            pages.append(Page(u, b, html_to_text(b)))
            queue += [x for x in contact_links(u, b, self.extra_pages) if x.rstrip("/") not in seen and x not in queue]
            conf, signals = assess_identity(identity, pages)
        if conf == WebsiteConfidence.HIGH:     # contacts: make sure the contacts / requisites pages themselves were read
            for url in contact_links(final_url, body, self.extra_pages):
                if (url.rstrip("/") not in seen and (_LINK_HINTS[0].search(url) or _LINK_HINTS[1].search(url))
                        and len(pages) <= self.extra_pages + 1):
                    seen.add(url.rstrip("/"))
                    try:
                        u, b = self._get(url)
                        if host_of(u) == host_of(final_url):
                            pages.append(Page(u, b, html_to_text(b)))
                    except SourceUnavailable:
                        pass
        pages = list({p.url.rstrip("/"): p for p in reversed(pages)}.values())[::-1]   # one page per final URL, order kept
        official = final_url if conf == WebsiteConfidence.HIGH else None
        return WebsiteVerification(candidate_url=candidate.url, confidence=conf, signals=signals,
                                   official_url=site_root(official) if official else None, pages=tuple(pages),
                                   latest_year=latest_year(pages, checked.date()), checked_at=checked,
                                   reason=None if conf == WebsiteConfidence.HIGH else "IDENTITY_NOT_CONFIRMED_ON_SITE",
                                   status=verification_status(conf, signals), provider=candidate.provider)


# ------------------------------------------------------------------------------------------------------------ contacts
_TEL_LINK = re.compile(r"""href=["']tel:([^"']+)["'][^>]*>(.*?)</a>""", re.S | re.I)
_MAILTO = re.compile(r"""href=["']mailto:([^"'?]+)""", re.I)
_PHONE_TXT = re.compile(r"(?<![\d+])(?:\+7|8)[\s \-–(]*\d{3,5}[\s \-–)]*\d{1,3}[\s \-–]*\d{2}[\s \-–]*\d{2}(?!\d)")
_EMAIL_TXT = re.compile(r"(?<![\w.+-])[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}(?![\w-])")
_PATRONYMIC = re.compile(r"\b[А-ЯЁ][а-яё]+(?:ович|евич|ьич|овна|евна|ична|инична)\b")
_PERSON_ROLE = re.compile(r"директор|бухгалтер|руководител|заместител|менеджер\s+[А-ЯЁ]|специалист\s+[А-ЯЁ]", re.I)
_GENERIC_LOCAL = re.compile(r"^(info|sales|office|zakaz|order|orders|mail|secretary|priem|priemnaya|opt|market|marketing|"
                            r"client|clients|hello|contact|contacts|post|sale|torg|snab|tender|tenders|general|company|"
                            r"reception|kanc|kancelyariya|support|service|shop|manager|otdel|help|zakupki|purchase|"
                            r"procurement|commerce|kommerc|dir|director|buh|hr|personal|pr|press|yur|legal)\d*$", re.I)
# person-like mailbox: initial + surname (a.bondar), surname + initial (kamenev.m), name.surname (nikiforova.kseniya),
# name_surname, or a bare transliterated Russian surname (ivanov, petrova, kovalenko, sokolsky)
_PERSON_LOCAL = re.compile(r"^(?:[a-z]{1,2}[._-][a-z]{3,}|[a-z]{3,}[._-][a-z]{1,2}|[a-z]{3,}[._][a-z]{3,}|"
                           r"[a-z]{2,}(?:ov|ev|ova|eva|in|ina|yn|yna|sky|skiy|skaya|skii|enko|chuk|yuk|uk|ich))\d*$", re.I)
_FILE_TLD = re.compile(r"\.(png|jpe?g|gif|svg|webp|css|js)$", re.I)
_BAD_EMAIL_DOMAINS = ("example.com", "sentry.io", "wixpress.com", "domain.ru", "site.ru", "mail.example")
FREE_MAIL = ("mail.ru", "bk.ru", "list.ru", "inbox.ru", "internet.ru", "yandex.ru", "ya.ru", "yandex.com", "gmail.com",
             "rambler.ru", "lenta.ru", "ro.ru", "outlook.com", "hotmail.com", "icloud.com")
_FAX_BEFORE = re.compile(r"(факс|fax|ф\.)\s*[:.]?\s*$", re.I)
_PHONE_BEFORE = re.compile(r"тел\w*\.?\s*/\s*(?:факс|fax)\s*[:.]?\s*$", re.I)


def normalize_phone(raw: str) -> str | None:
    d = re.sub(r"\D", "", raw)
    if len(d) == 11 and d[0] in "78":
        return "7" + d[1:]
    if len(d) == 10 and d[0] in "3489":
        return "7" + d
    return None


def registrable_domain(host: str) -> str:
    """Naive registrable domain: last two labels (three for regional second-level zones such as spb.ru, msk.ru, com.ru)."""
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in ("spb.ru", "msk.ru", "com.ru", "net.ru", "org.ru", "pp.ru", "co.uk"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _personal_context(text: str, pos: int) -> bool:
    window = text[max(0, pos - 90):pos + 40]
    return bool(_PATRONYMIC.search(window) or _PERSON_ROLE.search(window))


def _fax_only(text: str, raw: str) -> bool:
    """Every visible occurrence of this number is labelled «Факс» (a combined «тел./факс» line is a phone)."""
    occ = [m.start() for m in re.finditer(re.escape(raw), text)]
    if not occ:
        return False
    return all(_FAX_BEFORE.search(text[max(0, p - 25):p]) and not _PHONE_BEFORE.search(text[max(0, p - 25):p]) for p in occ)


def email_accepted(email: str, site_domain: str, company_domains: set[str], site_label: str) -> str | None:
    """Basis label for a public business e-mail, or None. Company domain (the verified site's or the EGRUL-registered
    e-mail domain): any non-person mailbox. Public free-mail: only role mailboxes or ones named after the company site.
    Any other third-party domain: rejected (not explained by the official site)."""
    local, _, dom = email.partition("@")
    if not dom or _PERSON_LOCAL.match(local):
        return None
    reg = registrable_domain(dom)
    if reg == site_domain or reg in company_domains:
        return "COMPANY_DOMAIN"
    if reg in FREE_MAIL or dom in FREE_MAIL:
        if _GENERIC_LOCAL.match(local) or (len(site_label) >= 4 and site_label in local):
            return "PUBLIC_MAILBOX_ON_OFFICIAL_SITE"
        return None
    return None


class HtmlContactExtractor:
    name = "FIRST_PARTY_CONTACT_EXTRACTOR"

    def __init__(self, max_per_type: int = 3) -> None:
        self.max_per_type = max_per_type

    def extract(self, identity: RegistryIdentity, verification: WebsiteVerification) -> list[ContactValue]:
        if verification.confidence != WebsiteConfidence.HIGH or not verification.official_url:
            return []          # identity first: never collect contacts from an unverified site
        today = (verification.checked_at or datetime.now()).date()
        currency = F.content_currency(verification.latest_year, today)
        checked = verification.checked_at
        status = verification.verification_status.value
        key = [x for x in verification.signals if x in ("INN_ON_SITE", "OGRN_ON_SITE", "KPP_ON_SITE", "EXACT_LEGAL_NAME",
                                                         "REGISTERED_STREET_ADDRESS")]
        basis = f"OFFICIAL_SITE_{status}:{'+'.join(key)}"
        site_host = host_of(verification.official_url)
        site_domain = registrable_domain(site_host)
        company_domains = {site_domain}
        if identity.registered_email:
            company_domains.add(registrable_domain(identity.registered_email.value.partition("@")[2]))
        company_domains -= set(FREE_MAIL)
        label = site_domain.split(".")[0]
        phones: dict[str, tuple[int, ContactValue]] = {}
        emails: dict[str, tuple[int, ContactValue]] = {}
        order = 0
        for page in verification.pages:
            if host_of(page.url) != site_host:
                continue       # contact data only from the verified domain
            text = page.text
            found_p = []
            for href, label_html in _TEL_LINK.findall(page.html):
                shown = html_to_text(label_html)
                found_p.append(shown if normalize_phone(shown) else htmlmod.unescape(href).strip())
            found_p += [m.group(0) for m in _PHONE_TXT.finditer(text)]
            for raw in found_p:
                norm = normalize_phone(raw)
                pos = text.find(raw)
                if (not norm or norm in phones or (pos >= 0 and _personal_context(text, pos)) or _fax_only(text, raw)):
                    continue
                order += 1
                phones[norm] = (order, ContactValue(ContactType.PHONE, raw.strip(), norm, "general phone (published on the official website)",
                                                    page.url, SourceType.FIRST_PARTY, checked, currency, True, basis))
            found_e = [htmlmod.unescape(m).strip() for m in _MAILTO.findall(page.html)] + _EMAIL_TXT.findall(text)
            for raw in found_e:
                norm = raw.lower()
                local, _, dom = norm.partition("@")
                pos = text.find(raw)
                if (not dom or norm in emails or _FILE_TLD.search(norm) or any(dom.endswith(b) for b in _BAD_EMAIL_DOMAINS)
                        or (pos >= 0 and _personal_context(text, pos))):
                    continue
                how = email_accepted(norm, site_domain, company_domains, label)
                if how is None:
                    continue
                order += 1
                emails[norm] = (order, ContactValue(ContactType.EMAIL, norm, norm,
                                                    "general e-mail" if _GENERIC_LOCAL.match(local) else "company e-mail",
                                                    page.url, SourceType.FIRST_PARTY, checked, currency, True, f"{basis}|{how}"))
        # landlines before mobile numbers (a mobile may be an employee's), then page order
        out = [v for _, v in sorted(phones.values(), key=lambda t: (t[1].normalized[1] == "9", t[0]))[:self.max_per_type]]
        out += [v for _, v in sorted(emails.values(), key=lambda t: (not _GENERIC_LOCAL.match(t[1].normalized.split("@")[0]), t[0]))
                ][:self.max_per_type]
        how = ("requisites (INN/OGRN)" if {"INN_ON_SITE", "OGRN_ON_SITE"} & set(verification.signals)
               else "exact legal name + registered address / KPP")
        out.append(ContactValue(ContactType.WEBSITE, verification.official_url, site_host,
                                f"official website (identity confirmed on the site by {how})", verification.official_url,
                                SourceType.FIRST_PARTY, checked, currency, True, basis))
        return out


def registry_contacts(identity: RegistryIdentity) -> list[ContactValue]:
    """Registered legal address and the business e-mail registered in EGRUL (official registry record -> CURRENT). A
    person-like registered mailbox (name.surname@…, initial.surname@…) is not shown."""
    out = []
    a = identity.registered_address
    if a:
        out.append(ContactValue(ContactType.ADDRESS, a.value, _fold(a.value), "registered legal address", a.source_url, a.source_type,
                                a.checked_at, F.CURRENT, True, "FNS_EGRUL_EXTRACT"))
    e = identity.registered_email
    if e and identity.entity_kind == "LEGAL_ENTITY":
        local, _, dom = e.value.partition("@")
        public = dom in FREE_MAIL or registrable_domain(dom) in FREE_MAIL
        if not _PERSON_LOCAL.match(local) and (not public or _GENERIC_LOCAL.match(local)):
            out.append(ContactValue(ContactType.EMAIL, e.value, e.value, "e-mail registered in EGRUL", e.source_url, e.source_type,
                                    e.checked_at, F.CURRENT, True, "FNS_EGRUL_REGISTERED_EMAIL"))
    return out


# ------------------------------------------------------------------------------------------------------------ roles
_PRODUCTION = re.compile(r"собственн\w*\s+производств\w*|завод[- ]изготовител\w*|мы производим|наше производство|"
                         r"производственн\w+\s+(?:площадк|мощност|цех|комплекс)\w*", re.I)
_OFFICIAL_DIST = re.compile(r"официальн\w+\s+(?:дилер|дистрибьютор|дистрибутор|представител)\w*", re.I)


def _snippet(text: str, m: re.Match) -> str:
    return text[max(0, m.start() - 60):m.end() + 60].strip()


class SiteAndOkvedRoleEvidence:
    """Never VERIFIED: OKVED alone -> INFERRED candidate (A2); automated first-party claims -> UNDER_REVIEW for a human."""
    name = "ROLE_EVIDENCE"

    def collect(self, identity: RegistryIdentity, verification: WebsiteVerification | None) -> list[RoleEvidenceItem]:
        out = []
        ok = identity.primary_okved
        if ok:
            code = ok.value.split(" ", 1)[0]
            try:
                div = int(code.split(".")[0])
            except ValueError:
                div = -1
            if 10 <= div <= 33:
                out.append(RoleEvidenceItem(Role.MANUFACTURER, RoleStatus.INFERRED, "OKVED_PRIMARY",
                                            f"Primary OKVED {ok.value} is a manufacturing activity (registry). OKVED alone is an "
                                            "inferred candidate, never a verified manufacturer.",
                                            ok.source_url, ok.source_type.value, ok.checked_at, Strength.WEAK))
            elif div == 46:
                out.append(RoleEvidenceItem(Role.DISTRIBUTOR, RoleStatus.INFERRED, "OKVED_PRIMARY",
                                            f"Primary OKVED {ok.value} is wholesale trade (registry); inferred only.",
                                            ok.source_url, ok.source_type.value, ok.checked_at, Strength.WEAK))
        if verification and verification.confidence == WebsiteConfidence.HIGH:
            for role, rx, basis in ((Role.MANUFACTURER, _PRODUCTION, "FIRST_PARTY_PRODUCTION_CLAIM"),
                                    (Role.OFFICIAL_DISTRIBUTOR, _OFFICIAL_DIST, "FIRST_PARTY_DISTRIBUTION_CLAIM")):
                for page in verification.pages:
                    m = rx.search(page.text)
                    if m:
                        out.append(RoleEvidenceItem(role, RoleStatus.UNDER_REVIEW, basis,
                                                    f"Official website states: «{_snippet(page.text, m)}» — automated "
                                                    "extraction, needs human review before verification.",
                                                    page.url, SourceType.FIRST_PARTY.value, verification.checked_at,
                                                    Strength.MODERATE))
                        break
        return out
