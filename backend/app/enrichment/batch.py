"""P5-001A controlled batch enrichment: deterministic supplier selection, bounded runs, truthful coverage metrics.

Selection order (deduplicated, then cut to --limit): explicit INNs -> top awarded suppliers per requested OKPD2 prefix
(demo categories) -> most active suppliers in the last 180 days of data. Suppliers that are labelled in the sealed HOLDOUT
benchmark qrels are always excluded (the holdout is never touched, only its supplier list is read to stay clear of it).
"""
from __future__ import annotations

import csv
import statistics
import time
from collections import Counter
from datetime import datetime
from typing import Callable

from psycopg import Connection

from app.shared.config import repo_root

RECENT_DAYS = 180


def holdout_inns(conn: Connection) -> set[str]:
    base = repo_root() / "benchmark" / "replay"
    try:
        with open(base / "queries.csv", encoding="utf-8") as f:
            hq = {r["query_id"] for r in csv.DictReader(f) if r["split"] == "holdout"}
        with open(base / "qrels.csv", encoding="utf-8") as f:
            sids = sorted({r["supplier_id"] for r in csv.DictReader(f) if r["query_id"] in hq})
    except FileNotFoundError:
        return set()
    if not sids:
        return set()
    return {r[0] for r in conn.execute("SELECT inn FROM supplier WHERE supplier_id = ANY(%s::uuid[])", (sids,)).fetchall()}


def top_in_prefix(conn: Connection, prefix: str, n: int) -> list[str]:
    return [r[0] for r in conn.execute("""
        SELECT h.supplier_inn FROM supplier_history h
        JOIN (SELECT DISTINCT lot_id FROM procurement_item WHERE okpd2_code LIKE %s) i ON i.lot_id = h.lot_id
        WHERE h.is_winner GROUP BY h.supplier_inn ORDER BY count(*) DESC, max(h.publish_date) DESC, h.supplier_inn LIMIT %s""",
                                        (prefix.rstrip(".") + "%", n)).fetchall()]


def most_active(conn: Connection, n: int) -> list[str]:
    return [r[0] for r in conn.execute("""
        SELECT supplier_inn FROM supplier_history
        WHERE is_winner AND publish_date > (SELECT max(publish_date) FROM supplier_history) - %s
        GROUP BY supplier_inn ORDER BY count(*) DESC, max(publish_date) DESC, supplier_inn LIMIT %s""",
                                        (RECENT_DAYS, n)).fetchall()]


def select_inns(conn: Connection, limit: int, inns: list[str] = (), prefixes: list[str] = (), per_prefix: int = 10) -> tuple[list[str], int]:
    """(selected INNs, number excluded as holdout suppliers). Deterministic for a given database."""
    excluded = holdout_inns(conn)
    picked, dropped = [], 0
    pools = [list(inns)] + [top_in_prefix(conn, p, per_prefix * 3) for p in prefixes] + [most_active(conn, limit * 3)]
    for k, pool in enumerate(pools):
        taken = 0
        for inn in pool:
            if len(picked) >= limit or (0 < k < len(pools) - 1 and taken >= per_prefix):
                break
            if inn in picked:
                continue
            if inn in excluded:
                dropped += 1
                continue
            picked.append(inn)
            taken += 1
    return picked, dropped


def run_batch(conn: Connection, inns: list[str], enrich_one: Callable[[str], object], log=print) -> list[dict]:
    out = []
    for n, inn in enumerate(inns, 1):
        t0 = time.perf_counter()
        try:
            prof = enrich_one(inn)
            status, cache = prof.enrichment.status, prof.enrichment.cache
        except Exception as e:  # one bad supplier never stops the batch
            status, cache = f"ERROR:{type(e).__name__}", "NONE"
        secs = round(time.perf_counter() - t0, 2)
        out.append({"inn": inn, "status": status, "cache": cache, "wall_seconds": secs})
        log(f"[{n}/{len(inns)}] {inn} {status} {cache} {secs}s")
    return out


def metrics(conn: Connection, inns: list[str]) -> dict:
    rows = conn.execute("""SELECT inn, enrichment_status, legal_name IS NOT NULL, official_website IS NOT NULL, duration_ms,
                                  status_reasons, website_confidence, entity_kind
                           FROM supplier_enrichment_profile WHERE inn = ANY(%s)""", (inns,)).fetchall()
    by = {r[0]: r for r in rows}
    ctypes = {(i, t) for i, t in conn.execute("SELECT DISTINCT inn, contact_type FROM supplier_contact WHERE inn = ANY(%s)",
                                              (inns,)).fetchall()}
    roles = {i for (i,) in conn.execute("SELECT DISTINCT inn FROM supplier_role_evidence WHERE inn = ANY(%s)", (inns,)).fetchall()}
    attempts = conn.execute("""SELECT a.source, a.outcome, count(*) FROM supplier_enrichment_attempt a
                               JOIN (SELECT DISTINCT ON (inn) run_id FROM supplier_enrichment_attempt WHERE inn = ANY(%s)
                                     ORDER BY inn, seq DESC) l ON l.run_id = a.run_id
                               GROUP BY 1, 2 ORDER BY 1, 2""", (inns,)).fetchall()
    n = len(inns)
    status = Counter(by[i][1] if i in by else "NOT_ENRICHED" for i in inns)
    durs = [by[i][4] for i in inns if i in by and by[i][4]]

    def cov(pred):
        k = sum(1 for i in inns if pred(i))
        return {"count": k, "pct": round(100 * k / n, 1) if n else 0.0}

    reasons = Counter(r for i in inns if i in by for r in by[i][5])
    return {
        "suppliers_attempted": n,
        "status_counts": dict(sorted(status.items())),
        "coverage": {
            "legal_name": cov(lambda i: i in by and by[i][2]),
            "official_website": cov(lambda i: i in by and by[i][3]),
            "phone": cov(lambda i: (i, "PHONE") in ctypes),
            "email": cov(lambda i: (i, "EMAIL") in ctypes),
            "address": cov(lambda i: (i, "ADDRESS") in ctypes),
            "role_evidence": cov(lambda i: i in roles),
        },
        "website_confidence_counts": dict(sorted(Counter(by[i][6] for i in inns if i in by).items())),
        "entity_kind_counts": dict(sorted(Counter(by[i][7] or "UNKNOWN" for i in inns if i in by).items())),
        "median_enrichment_ms": int(statistics.median(durs)) if durs else None,
        "p90_enrichment_ms": int(sorted(durs)[int(0.9 * (len(durs) - 1))]) if durs else None,
        "status_reason_counts": dict(sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))),
        "source_outcomes_last_run": [{"source": s, "outcome": o, "count": c} for s, o, c in attempts],
        "source_failure_counts": {s: c for s, o, c in attempts if o == "UNAVAILABLE"},
        "computed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def render_md(doc: dict) -> str:
    """reports/p5_001a_supplier_enrichment.md from the pilot JSON (numbers only from the JSON; no hand-edited metrics)."""
    m, sel = doc["metrics"], doc["selection"]
    n = m["suppliers_attempted"]
    lines = ["# P5-001A — Automated Supplier Enrichment Backend MVP (pilot report)", "",
             f"> Generated by `python -m app.cli enrichment report` from `reports/p5_001a_supplier_enrichment.json` · "
             f"metrics computed {m['computed_at']}. Bounded pilot on real supplier INNs from the organizer data; HOLDOUT-labelled "
             "suppliers excluded; ranking, S3, verification decisions and embeddings untouched.", "",
             "## Architecture", "",
             "INN → legal identity (`CompanyRegistryProvider`) → candidate website (`WebsiteDiscoveryProvider`) → website identity "
             "verification (`WebsiteVerifier`) → first-party contacts (`ContactExtractor`) → role evidence (`RoleEvidenceProvider`) → "
             "freshness (`app/enrichment/freshness.py`) → persistence (migration 0005: `supplier_enrichment_profile`, "
             "`supplier_contact`, `supplier_enrichment_evidence`, `supplier_role_evidence`, `supplier_enrichment_attempt`). "
             "Pipeline = `app/enrichment/pipeline.py` (pure, injected providers); API = `GET /api/v1/suppliers/{inn}/profile` "
             "(read-only, never live) and `POST /api/v1/suppliers/{inn}/enrich[?refresh=true]` (cache-first, bounded, synchronous).",
             "", "## Provider sources actually used", "",
             "| Provider | Source | Used for | Not used for |", "|---|---|---|---|",
             "| FNS_EGRUL | egrul.nalog.ru (official FNS search) | legal name, short name, OGRN, KPP, region, registration date, "
             "active/ceased | director names (ignored) |",
             "| CHECKO_REGISTRY_MIRROR | checko.ru (FNS-derived registry mirror; accepted in P4-005C) | registered address, primary "
             "OKVED, website hint; only when INN + OGRN match | its phones / e-mails (aggregated, possibly personal / stale) |",
             "| FIRST_PARTY_WEBSITE | the company's own site (≤ 6 same-host pages) | identity verification, general phone / e-mail, "
             "content currency, first-party role claims | anything when identity is not confirmed |", "",
             "Official website = INN or OGRN published on the site, or exact legal name + registered street address (street + house "
             "number). Exact name + locality only = MEDIUM (stored as candidate, not official). Roles: OKVED → INFERRED only; "
             "first-party production / official-distribution wording → UNDER_REVIEW; the pipeline never writes VERIFIED (DB check). "
             "Individual entrepreneurs: identity only (their contacts are personal data).", "",
             "## Pilot", "",
             f"- Suppliers attempted: **{n}** (limit {sel['limit']}; explicit {len(sel['explicit_inns'])}; OKPD2 prefixes "
             f"{', '.join(sel['okpd2_prefixes']) or '—'} × {sel['per_prefix']}; rest = most active suppliers of the last "
             f"{RECENT_DAYS} days of data; {sel['holdout_suppliers_skipped']} holdout suppliers skipped)",
             f"- Status: " + ", ".join(f"{k} {v}" for k, v in m["status_counts"].items()),
             f"- Median enrichment time: **{m['median_enrichment_ms']} ms** (p90 {m['p90_enrichment_ms']} ms; includes polite "
             "per-host delays)", "", "## Coverage", "", "| Field | Suppliers | % |", "|---|---:|---:|"]
    for k, v in m["coverage"].items():
        lines.append(f"| {k.replace('_', ' ')} | {v['count']} / {n} | {v['pct']} |")
    lines += ["", f"Website confidence: {m['website_confidence_counts']} · entity kinds: {m['entity_kind_counts']}", "",
              "## Status reasons (PARTIAL / FAILED explanations)", "", "| Reason | Suppliers |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in m["status_reason_counts"].items()]
    lines += ["", "## Source outcomes (last run per supplier)", "", "| Source | Outcome | Count |", "|---|---|---:|"]
    lines += [f"| {r['source']} | {r['outcome']} | {r['count']} |" for r in m["source_outcomes_last_run"]]
    lines += ["", f"Source failure counts (UNAVAILABLE): {m['source_failure_counts'] or 'none'}", ""]
    for status in ("COMPLETE", "PARTIAL", "FAILED"):
        ex = [p for p in doc["profiles"] if p["enrichment"]["status"] == status][:2]
        if not ex:
            continue
        lines += [f"## Example — {status}", ""]
        for p in ex:
            s, e = p["supplier"], p["enrichment"]
            lines += [f"**{s['inn']} · {s['display_name'] or '—'}** — website `{e['official_website'] or '—'}` "
                      f"({e['website_confidence']}), reasons {e['reasons'] or '—'}, contacts freshness {p['freshness']['contacts']}", ""]
            for c in p["contacts"]:
                lines.append(f"- {c['type']}: {c['value']} — {c['source_type']} <{c['source_url']}> · {c['freshness_status']}")
            for r in p["roles"]:
                lines.append(f"- role {r['role']} / {r['status']} ({r['basis']})")
            lines.append("")
    return "\n".join(lines) + "\n"
