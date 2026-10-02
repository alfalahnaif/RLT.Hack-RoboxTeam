"""P5-002A golden-set evaluation of website / contact discovery (benchmark/enrichment/p5_002a_contact_golden.json).

The expected values were established by hand before the discovery code existed; this module only SCORES pipeline output
against them — it never derives expectations from the pipeline.

Definitions (coverage is reported separately from accuracy):
  website   eligible  = suppliers with an expected official domain (not individual entrepreneurs)
            found     = suppliers whose profile has an official website
            correct   = found and its registrable domain is expected
            wrong-company match = found, not expected, not a same-company domain (any website for a no-site supplier counts)
            coverage  = correct / eligible     precision = correct / found
  phone / email (values)
            eligible  = suppliers with at least one acceptable value
            coverage  = suppliers with >= 1 correct value / eligible
            precision = correct values / returned values
            violation = returned value listed as forbidden (fax, person-associated, wrong company)
            unlisted  = returned value neither acceptable nor forbidden (reported for manual adjudication)
  invented  = a returned first-party value that does not occur in the content of its own source_url (re-fetched now)
"""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Callable

from app.enrichment.providers import host_of, normalize_phone, registrable_domain

FIRST_PARTY = "FIRST_PARTY"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dom(url: str | None) -> str | None:
    return registrable_domain(host_of(url)) if url else None


def _values(profile: dict, ctype: str) -> list[dict]:
    return [c for c in profile.get("contacts", []) if c["type"] == ctype and c.get("origin") == "ENRICHMENT_PIPELINE"]


def _norm(ctype: str, value: str) -> str:
    return (normalize_phone(value) or re.sub(r"\D", "", value)) if ctype == "PHONE" else value.strip().lower()


def score_supplier(g: dict, p: dict | None) -> dict:
    """Per-supplier verdicts for one golden row and its stored profile (API JSON)."""
    p = p or {"contacts": [], "enrichment": {}, "supplier": {}}
    site = p.get("enrichment", {}).get("official_website")
    dom = _dom(site)
    expected = set(g["expected_official_domains"])
    same = set(g.get("same_company_domains", []))
    if site is None:
        site_verdict = "MISSED" if expected else "CORRECT_NONE"
    elif dom in expected:
        site_verdict = "CORRECT"
    elif dom in same:
        site_verdict = "SAME_COMPANY_UNVERIFIABLE"
    else:
        site_verdict = "WRONG_COMPANY"          # expected another domain, or none at all (incl. every listed forbidden domain)
    out = {"inn": g["inn"], "name": g["name"], "tags": g["tags"], "expected_domains": sorted(expected), "found_website": site,
           "website_verdict": site_verdict, "website_status": (p.get("enrichment", {}).get("website_verification") or {}).get("status"),
           "website_signals": (p.get("enrichment", {}).get("website_verification") or {}).get("signals", []),
           "discovered_via": (p.get("enrichment", {}).get("website_verification") or {}).get("discovered_via"),
           "legal_identity_ok": bool(p.get("supplier", {}).get("legal_name")) and
                                (g.get("ogrn") is None or p.get("supplier", {}).get("ogrn") == g.get("ogrn")),
           "enrichment_status": p.get("enrichment", {}).get("status")}
    for ctype, key in (("PHONE", "phones"), ("EMAIL", "emails")):
        acc = set(g[key]["acceptable"])
        bad = set(g[key]["forbidden"])
        vals = [(_norm(ctype, c["value"]), c) for c in _values(p, ctype)]
        out[key] = {"returned": [v for v, _ in vals], "correct": [v for v, _ in vals if v in acc],
                    "violations": [v for v, _ in vals if v in bad], "unlisted": [v for v, _ in vals if v not in acc and v not in bad],
                    "eligible": bool(acc),
                    "sources": {v: {"source_type": c["source_type"], "source_url": c["source_url"],
                                    "basis": c.get("verification_basis")} for v, c in vals}}
    return out


def invented_check(rows: list[dict], fetch: Callable[[str], str]) -> list[dict]:
    """Re-fetch the source page of every returned FIRST_PARTY phone / e-mail and confirm the value occurs in it."""
    out, cache = [], {}
    for r in rows:
        for key in ("phones", "emails"):
            for v, src in r[key]["sources"].items():
                if src["source_type"] != FIRST_PARTY:
                    continue
                url = src["source_url"]
                if url not in cache:
                    try:
                        cache[url] = fetch(url)
                    except Exception as e:  # unreachable now: reported, never counted as verified
                        cache[url] = e
                page = cache[url]
                if isinstance(page, Exception):
                    out.append({"inn": r["inn"], "value": v, "source_url": url, "present": None, "note": f"refetch failed: {page}"[:120]})
                    continue
                hay = re.sub(r"\D", "", page) if key == "phones" else page.lower()
                needle = v[1:] if key == "phones" else v                  # phones: digits without the country code
                out.append({"inn": r["inn"], "value": v, "source_url": url, "present": needle in hay})
    return out


def _cov(n: int, d: int) -> dict:
    return {"count": n, "of": d, "pct": round(100 * n / d, 1) if d else None}


def metrics(rows: list[dict], durations_ms: dict[str, int], invented: list[dict], adversarial: list[dict],
            provider_failures: dict[str, int]) -> dict:
    sites_eligible = [r for r in rows if r["expected_domains"]]
    found = [r for r in rows if r["found_website"]]
    correct = [r for r in rows if r["website_verdict"] == "CORRECT"]
    wrong = [r for r in rows if r["website_verdict"] == "WRONG_COMPANY"]
    m = {
        "suppliers": len(rows),
        "legal_identity_accuracy": _cov(sum(r["legal_identity_ok"] for r in rows), len(rows)),
        "official_website": {"eligible": len(sites_eligible), "found": len(found), "correct": len(correct),
                             "coverage": _cov(len(correct), len(sites_eligible)),
                             "precision": _cov(len(correct), len(found)), "wrong_company_matches": len(wrong),
                             "same_company_unverifiable": sum(r["website_verdict"] == "SAME_COMPANY_UNVERIFIABLE" for r in rows),
                             "by_status": {s: sum(1 for r in found if r["website_status"] == s)
                                           for s in ("VERIFIED_STRONG", "VERIFIED_COMPOSITE")}},
    }
    for key in ("phones", "emails"):
        elig = [r for r in rows if r[key]["eligible"]]
        returned = sum(len(r[key]["returned"]) for r in rows)
        corr = sum(len(r[key]["correct"]) for r in rows)
        m[key] = {"eligible": len(elig), "suppliers_found": sum(1 for r in rows if r[key]["returned"]),
                  "coverage": _cov(sum(1 for r in elig if r[key]["correct"]), len(elig)),
                  "values_returned": returned, "values_correct": corr, "precision": _cov(corr, returned),
                  "violations": sum(len(r[key]["violations"]) for r in rows),
                  "unlisted": [{"inn": r["inn"], "value": v} for r in rows for v in r[key]["unlisted"]]}
    durs = sorted(durations_ms.values())
    m["invented_contacts"] = sum(1 for x in invented if x["present"] is False)
    m["invented_check_unverifiable"] = sum(1 for x in invented if x["present"] is None)
    m["wrong_identity_matches"] = len(wrong) + sum(1 for a in adversarial if a["status"] in ("VERIFIED_STRONG", "VERIFIED_COMPOSITE"))
    m["adversarial_checks"] = {"total": len(adversarial),
                               "rejected_or_unknown": sum(1 for a in adversarial if a["status"] in ("REJECTED", "UNKNOWN"))}
    m["discovery_time_ms"] = {"median": int(statistics.median(durs)) if durs else None,
                              "p95": durs[min(len(durs) - 1, int(round(0.95 * (len(durs) - 1))))] if durs else None,
                              "max": durs[-1] if durs else None}
    m["provider_failures"] = provider_failures
    return m
