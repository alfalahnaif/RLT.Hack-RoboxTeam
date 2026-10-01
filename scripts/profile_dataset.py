#!/usr/bin/env python3
"""P1-001A — Reproducible profiling of the organizer dataset (RLT.Hack 2024–2025).

Reads the three raw CSVs in full (no sampling, read-only, no network, stdlib only) and writes:
  reports/dataset_profile.json       deterministic machine-readable report (identical across runs)
  reports/dataset_profile.md         human-readable report rendered from the JSON
  reports/dataset_profile.meta.json  run metadata (timestamp, runtime, python) — NOT deterministic

Usage:  python scripts/profile_dataset.py [--raw data/raw] [--out reports]

Privacy: supplier INNs are never written to the outputs (53% are individuals/IEs — NFR-PRIV-01).
Conventions: quantiles use the lower nearest-rank rule  v[min(n-1, floor(q*n))];
percentages are rounded to 1 decimal, shares to 3 decimals.
Docs: docs/analysis/REAL_DATASET_ANALYSIS_2024_2025.md · docs/HACKATHON_EXECUTION_BASELINE.md (ADR-H1).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import platform as py_platform
import re
import sys
import time
from array import array
from collections import Counter, defaultdict
from pathlib import Path

PROFILE_VERSION = "1.0.0"

FILES = {
    "notices": "Извещения_24-25.csv",
    "suppliers": "Поставщики_24-25.csv",
    "items": "ТРУ_24-25.csv",
}
EXPECTED_COLUMNS = {
    "notices": ["publish_date", "procedure_id", "lot_id", "start_price", "reqnum", "procedure_name",
                "subject", "is_smp", "customer_inn", "customer_kpp", "is_eshop_or_aisgz"],
    "suppliers": ["lot_id", "supplier_inn", "supplier_kpp", "is_winner"],
    "items": ["lot_id", "product_name", "okpd2_code"],
}

CONFIG = {
    "quantiles": [0.01, 0.25, 0.5, 0.75, 0.95, 0.99],
    # temporal replay (HD-06): target lots on this platform published on/after replay_from;
    # history = lots with strictly earlier publish_date (any platform)
    "replay_platform": "ЭМ",
    "replay_from": "2025-01-01",
    # supplier pool health (HD-08)
    "recent_from": "2025-07-01",
    "pool_min_lots": 30,
    "shortlist_max_section": 32,      # goods: OKPD2 sections 01–32
    "shortlist_min_lots": 40,
    "shortlist_min_customers": 8,
    "shortlist_size": 40,
    "fewest_winners_size": 25,
    "pool_health_codes": ["10.39.17.111", "10.51.11.141", "10.42.10.111", "01.25.19.150", "10.61.22.130",
                          "10.62.11.112", "01.13.16.000", "10.12.10.170", "10.51.52.111"],
    "pool_health_class_prefixes": ["10.39.17"],
    # golden demo candidates (dataset analysis §9)
    "golden_lots": ["5612123", "5545252", "5542696", "5659204", "5718896"],
    "extra_golden_lots": ["5875992", "6022687", "5510873", "5548828"],
    "example_lots": ["4900162"],
    # generic-title heuristic (extra golden candidates)
    "generic_subject_regex": r"^(поставка|закупка|приобретение)\s+(товар|компьютерн|оргтехник|оборудован|мебел|расходн|хозяйств|канцеляр|медицинск)",
    "generic_subject_max_len": 70,
    "generic_min_participants": 6,
    "generic_max_items": 3,
    "generic_list_size": 40,
}

OKPD2_RE = re.compile(r"\d{2}(\.\d{1,3}){0,4}")
KPP_RE = re.compile(r"\d{4}[0-9A-Z]{2}\d{3}")
WORD_RE = re.compile(r"[^\w]+")
SPACE_RE = re.compile(r"\s+")


# ----------------------------------------------------------------------------- helpers
def norm_text(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    return SPACE_RE.sub(" ", WORD_RE.sub(" ", s)).strip()


def pct(a: int, b: int) -> float:
    return round(100.0 * a / b, 1) if b else 0.0


def quantiles(sorted_values, qs):
    n = len(sorted_values)
    if not n:
        return {}
    return {f"p{int(round(q * 100)):02d}": sorted_values[min(n - 1, int(q * n))] for q in qs}


def top(counter: Counter, n: int):
    """Deterministic most_common: count desc, key asc."""
    return [[k, v] for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def inn_checksum_ok(inn: str) -> bool:
    d = [int(c) for c in inn]

    def ctrl(weights):
        return sum(w * x for w, x in zip(weights, d)) % 11 % 10

    if len(d) == 10:
        return ctrl([2, 4, 10, 3, 5, 9, 4, 6, 8]) == d[9]
    if len(d) == 12:
        return (ctrl([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == d[10]
                and ctrl([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == d[11])
    return False


def inn_kind(inn: str) -> str:
    if inn.isdigit() and len(inn) == 10:
        return "legal_entity"
    if inn.isdigit() and len(inn) == 12:
        return "individual_entrepreneur"
    return "invalid"


def okpd2_depth(code: str) -> int:
    return code.count(".") + 1


def reader(path: Path):
    f = open(path, encoding="utf-8-sig", newline="")
    r = csv.reader(f, delimiter=";", quotechar='"')
    header = next(r)
    return f, r, header


def file_facts(path: Path) -> dict:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        first = f.read(3)
        h.update(first)
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    f, _rd, header = reader(path)
    f.close()
    return {"name": path.name, "size_bytes": path.stat().st_size, "sha256": h.hexdigest(),
            "utf8_bom": first == b"\xef\xbb\xbf", "columns": header}


csv.field_size_limit(10 ** 9)


# ----------------------------------------------------------------------------- profiling
def profile(raw: Path) -> dict:
    C = CONFIG
    R: dict = {"profile_version": PROFILE_VERSION, "config": C, "files": {}}
    for key, name in FILES.items():
        R["files"][key] = file_facts(raw / name)

    interest = set(C["golden_lots"]) | set(C["extra_golden_lots"]) | set(C["example_lots"])

    # ---------------- notices
    f, rd, header = reader(raw / FILES["notices"])
    ix = {c: i for i, c in enumerate(header)}
    lot = {}  # lot_id -> (date, platform, customer_inn, subject_norm, price|None, is_smp)
    subj_raw = {}
    rows = bad_rows = dup_lots = 0
    procs = set()
    lots_per_proc = Counter()
    by_year, by_platform, by_platform_year = Counter(), Counter(), Counter()
    smp_by_platform = Counter()
    customers = set()
    cust_kpp_empty = cust_kpp_bad = cust_inn_bad = 0
    reqnum_filled = price_empty = price_zero = 0
    prices = array("d")
    same_exact = same_norm = subj_empty = pname_empty = 0
    dmin, dmax = "9999-99-99", "0000-00-00"
    for row in rd:
        rows += 1
        if len(row) != len(header):
            bad_rows += 1
            continue
        lid = row[ix["lot_id"]]
        d = row[ix["publish_date"]]
        p = row[ix["is_eshop_or_aisgz"]]
        if lid in lot:
            dup_lots += 1
        dmin, dmax = min(dmin, d), max(dmax, d)
        by_year[d[:4]] += 1
        by_platform[p] += 1
        by_platform_year[f"{p}|{d[:4]}"] += 1
        smp = row[ix["is_smp"]]
        smp_by_platform[f"{p}|{smp}"] += 1
        pid = row[ix["procedure_id"]]
        procs.add(pid)
        lots_per_proc[pid] += 1
        cinn = row[ix["customer_inn"]].strip()
        customers.add(cinn)
        if inn_kind(cinn) == "invalid":
            cust_inn_bad += 1
        ckpp = row[ix["customer_kpp"]].strip()
        if not ckpp:
            cust_kpp_empty += 1
        elif not KPP_RE.fullmatch(ckpp):
            cust_kpp_bad += 1
        if row[ix["reqnum"]].strip():
            reqnum_filled += 1
        pr_s = row[ix["start_price"]].strip()
        price = None
        if pr_s:
            try:
                price = float(pr_s)
                prices.append(price)
                if price == 0:
                    price_zero += 1
            except ValueError:
                price_empty += 1
        else:
            price_empty += 1
        pn, sj = row[ix["procedure_name"]], row[ix["subject"]]
        if not sj.strip():
            subj_empty += 1
        if not pn.strip():
            pname_empty += 1
        if pn == sj:
            same_exact += 1
        sjn = norm_text(sj)
        if norm_text(pn) == sjn:
            same_norm += 1
        lot[lid] = (d, p, cinn, sjn, price, smp)
        if lid in interest:
            subj_raw[lid] = sj.strip()
    f.close()
    prices = sorted(prices)
    n_lots = len(lot)
    R["notices"] = {
        "rows": rows, "malformed_rows": bad_rows, "unique_lots": n_lots, "duplicate_lot_rows": dup_lots,
        "unique_procedures": len(procs),
        "max_lots_per_procedure": max(lots_per_proc.values()),
        "procedures_with_multiple_lots": sum(1 for v in lots_per_proc.values() if v > 1),
        "date_min": dmin, "date_max": dmax,
        "by_year": dict(by_year), "by_platform": dict(by_platform), "by_platform_year": dict(by_platform_year),
        "platform_share_pct": {k: pct(v, n_lots) for k, v in by_platform.items()},
        "unique_customers": len(customers), "customer_inn_invalid_rows": cust_inn_bad,
        "customer_kpp_empty_rows": cust_kpp_empty, "customer_kpp_bad_format_rows": cust_kpp_bad,
        "is_smp_by_platform": dict(smp_by_platform),
        "reqnum_filled": reqnum_filled, "reqnum_filled_pct": pct(reqnum_filled, n_lots),
        "start_price_empty_or_unparsable": price_empty, "start_price_zero": price_zero,
        "start_price_quantiles": {k: round(v, 2) for k, v in quantiles(prices, C["quantiles"]).items()},
        "procedure_name_eq_subject_exact": same_exact,
        "procedure_name_eq_subject_exact_pct": pct(same_exact, n_lots),
        "procedure_name_eq_subject_normalized": same_norm,
        "procedure_name_eq_subject_normalized_pct": pct(same_norm, n_lots),
        "subject_empty": subj_empty, "procedure_name_empty": pname_empty,
    }
    del prices, procs, lots_per_proc
    print(f"[profile] notices: {rows:,} rows", file=sys.stderr, flush=True)

    # ---------------- suppliers
    f, rd, header = reader(raw / FILES["suppliers"])
    ix = {c: i for i, c in enumerate(header)}
    sups = defaultdict(list)  # lot_id -> [(inn, is_winner)]
    rows = bad_rows = 0
    inn_len_rows, winner_vals = Counter(), Counter()
    inn_nondigit_rows = kpp_empty = kpp_bad = dup_pairs = 0
    orphan_rows = 0
    orphan_lots = set()
    seen_pair = set()
    unique_inns = set()
    for row in rd:
        rows += 1
        if len(row) != len(header):
            bad_rows += 1
            continue
        lid = row[ix["lot_id"]]
        inn = row[ix["supplier_inn"]].strip()
        w = row[ix["is_winner"]].strip()
        unique_inns.add(inn)
        inn_len_rows[str(len(inn))] += 1
        if not inn.isdigit():
            inn_nondigit_rows += 1
        kpp = row[ix["supplier_kpp"]].strip()
        if not kpp:
            kpp_empty += 1
        elif not KPP_RE.fullmatch(kpp):
            kpp_bad += 1
        winner_vals[w] += 1
        k = (lid, inn)
        if k in seen_pair:
            dup_pairs += 1
        seen_pair.add(k)
        if lid not in lot:
            orphan_rows += 1
            orphan_lots.add(lid)
        sups[lid].append((inn, w == "true"))
    f.close()
    del seen_pair
    kinds = Counter(inn_kind(i) for i in unique_inns)
    checksum_bad = sum(1 for i in unique_inns if inn_kind(i) != "invalid" and not inn_checksum_ok(i))
    region_unique = Counter(i[:2] for i in unique_inns)
    region_rows = Counter()
    for s in sups.values():
        for inn, _ in s:
            region_rows[inn[:2]] += 1
    R["suppliers"] = {
        "rows": rows, "malformed_rows": bad_rows, "unique_lots": len(sups), "unique_inns": len(unique_inns),
        "inn_length_rows": dict(inn_len_rows), "inn_nondigit_rows": inn_nondigit_rows,
        "inn_kind_unique": dict(kinds),
        "inn_kind_unique_pct": {k: pct(v, len(unique_inns)) for k, v in kinds.items()},
        "inn_checksum_invalid_unique": checksum_bad,
        "kpp_empty_rows": kpp_empty, "kpp_empty_pct": pct(kpp_empty, rows), "kpp_bad_format_rows": kpp_bad,
        "is_winner_values": dict(winner_vals),
        "duplicate_lot_inn_pairs": dup_pairs,
        "orphan_rows_lot_not_in_notices": orphan_rows, "orphan_lots": len(orphan_lots),
        "inn_region_prefix_unique_top": [[k, v, pct(v, len(unique_inns))] for k, v in top(region_unique, 8)],
        "inn_region_prefix_rows_top": [[k, v, pct(v, rows)] for k, v in top(region_rows, 8)],
    }
    print(f"[profile] suppliers: {rows:,} rows", file=sys.stderr, flush=True)

    # ---------------- items (ТРУ)
    f, rd, header = reader(raw / FILES["items"])
    ix = {c: i for i, c in enumerate(header)}
    items_per_lot = Counter()
    lot_codes = defaultdict(set)
    interest_items = defaultdict(list)
    rows = bad_rows = 0
    code_rows, depth_rows, section_rows = Counter(), Counter(), Counter()
    okpd_empty = okpd_bad = name_empty = 0
    eq_subject = in_subject = 0
    orphan_rows = 0
    name_lens = array("I")
    for row in rd:
        rows += 1
        if len(row) != len(header):
            bad_rows += 1
            continue
        lid = row[ix["lot_id"]]
        nm = row[ix["product_name"]]
        code = row[ix["okpd2_code"]].strip()
        items_per_lot[lid] += 1
        name_lens.append(len(nm))
        if not nm.strip():
            name_empty += 1
        if not code:
            okpd_empty += 1
        else:
            code_rows[code] += 1
            depth_rows[str(okpd2_depth(code))] += 1
            section_rows[code[:2]] += 1
            if not OKPD2_RE.fullmatch(code):
                okpd_bad += 1
            lot_codes[lid].add(code)
        info = lot.get(lid)
        if info is None:
            orphan_rows += 1
        else:
            nn = norm_text(nm)
            if nn == info[3]:
                eq_subject += 1
            elif nn and nn in info[3]:
                in_subject += 1
        if lid in interest:
            interest_items[lid].append((nm.strip(), code))
    f.close()
    name_lens = sorted(name_lens)
    ipl = Counter(min(v, 11) for v in items_per_lot.values())
    n_item_lots = len(items_per_lot)
    dist_codes = Counter(min(len(s), 4) for s in lot_codes.values())
    # OKPD2 hierarchy: distinct prefixes per segment level, depth of distinct codes
    distinct_by_level = {}
    for lvl in range(1, 5):
        distinct_by_level[str(lvl)] = len({".".join(c.split(".")[:lvl]) for c in code_rows if okpd2_depth(c) >= lvl})
    R["items"] = {
        "rows": rows, "malformed_rows": bad_rows, "unique_lots": n_item_lots,
        "orphan_rows_lot_not_in_notices": orphan_rows,
        "items_per_lot_mean": round(rows / n_item_lots, 2), "items_per_lot_max": max(items_per_lot.values()),
        "items_per_lot_hist_11plus": {str(k): v for k, v in sorted(ipl.items())},
        "items_per_lot_pct": {"1": pct(ipl[1], n_item_lots),
                              "2_10": pct(sum(ipl[k] for k in range(2, 11)), n_item_lots),
                              "11plus": pct(ipl[11], n_item_lots)},
        "distinct_okpd2_per_lot_hist_4plus": {str(k): v for k, v in sorted(dist_codes.items())},
        "lots_with_multiple_okpd2": sum(v for k, v in dist_codes.items() if k > 1),
        "lots_with_multiple_okpd2_pct": pct(sum(v for k, v in dist_codes.items() if k > 1), len(lot_codes)),
        "product_name_empty_rows": name_empty,
        "product_name_length_quantiles": quantiles(name_lens, C["quantiles"]),
        "product_name_eq_subject_normalized_rows": eq_subject,
        "product_name_eq_subject_pct": pct(eq_subject, rows),
        "product_name_substring_of_subject_rows": in_subject,
        "product_name_substring_of_subject_pct": pct(in_subject, rows),
        "product_name_adds_text_pct": pct(rows - eq_subject - in_subject, rows),
        "okpd2": {
            "unique_codes": len(code_rows), "empty_rows": okpd_empty, "bad_format_rows": okpd_bad,
            "depth_rows": dict(depth_rows),
            "depth_rows_pct": {k: pct(v, rows - okpd_empty) for k, v in depth_rows.items()},
            "depth_unique_codes": dict(Counter(str(okpd2_depth(c)) for c in code_rows)),
            "distinct_prefixes_by_segment_level": distinct_by_level,
            "top_sections_rows": top(section_rows, 15),
            "top_codes_rows": top(code_rows, 20),
        },
    }
    del name_lens
    print(f"[profile] items: {rows:,} rows", file=sys.stderr, flush=True)

    # ---------------- coverage
    cov = Counter()
    nosup_by_year, nosup_by_month = Counter(), Counter()
    for lid, info in lot.items():
        p = info[1]
        cov[f"{p}|total"] += 1
        ns, nt = lid not in sups, lid not in items_per_lot
        if ns:
            cov[f"{p}|no_supplier"] += 1
            nosup_by_year[info[0][:4]] += 1
            nosup_by_month[info[0][:7]] += 1
        if nt:
            cov[f"{p}|no_items"] += 1
        if ns and nt:
            cov[f"{p}|neither"] += 1
    R["coverage"] = {
        "by_platform": dict(cov),
        "lots_without_supplier_by_year": dict(nosup_by_year),
        "lots_without_supplier_by_month": dict(nosup_by_month),
    }

    # ---------------- is_winner semantics per platform/year
    sem = {}
    for lid, info in lot.items():
        key = f"{info[1]}|{info[0][:4]}"
        a = sem.setdefault(key, Counter())
        a["lots"] += 1
        s = sups.get(lid)
        if not s:
            continue
        nw = sum(1 for _, w in s if w)
        a["lots_with_supplier"] += 1
        a["supplier_rows"] += len(s)
        a["rows_winner"] += nw
        a["rows_non_winner"] += len(s) - nw
        a["lots_with_2plus_suppliers"] += len(s) >= 2
        a["lots_single_supplier"] += len(s) == 1
        a["lots_with_0_winners"] += nw == 0
        a["lots_with_2plus_winners"] += nw >= 2
        a[f"suppliers_per_lot={min(len(s), 6)}"] += 1
        a["max_suppliers_per_lot"] = max(a["max_suppliers_per_lot"], len(s))
    for key, a in sem.items():
        a2 = dict(a)
        if a["lots_with_supplier"]:
            a2["mean_suppliers_per_lot"] = round(a["supplier_rows"] / a["lots_with_supplier"], 2)
            a2["winner_row_pct"] = pct(a["rows_winner"], a["supplier_rows"])
            a2["lots_with_2plus_suppliers_pct"] = pct(a["lots_with_2plus_suppliers"], a["lots_with_supplier"])
            a2["lots_single_supplier_pct"] = pct(a["lots_single_supplier"], a["lots_with_supplier"])
            a2["lots_with_0_winners_pct"] = pct(a["lots_with_0_winners"], a["lots_with_supplier"])
        sem[key] = a2
    plat_inns = defaultdict(set)
    em_winners = set()
    for lid, s in sups.items():
        p = lot[lid][1] if lid in lot else "?"
        for inn, w in s:
            plat_inns[p].add(inn)
            if p == "ЭМ" and w:
                em_winners.add(inn)
    ais, em = plat_inns.get("АИС ГЗ", set()), plat_inns.get("ЭМ", set())
    R["supplier_semantics"] = {
        "by_platform_year": sem,
        "all_ais_gz_rows_winner": all(v.get("rows_non_winner", 0) == 0 for k, v in sem.items() if k.startswith("АИС ГЗ")),
        "inn_platform_overlap": {"ais_gz_only": len(ais - em), "em_only": len(em - ais), "both": len(ais & em)},
        "em_participants_never_won_on_em": len(em - em_winners),
    }

    # ---------------- benchmark pool
    pool = Counter()
    for lid, s in sups.items():
        info = lot.get(lid)
        if not info or lid not in lot_codes:
            continue
        nw = sum(1 for _, w in s if w)
        key = f"{info[1]}|{info[0][:4]}"
        if nw >= 1:
            pool[f"{key}|winner_and_items"] += 1
            if len(s) >= 2:
                pool[f"{key}|winner_items_2plus_participants"] += 1
    R["benchmark_pool"] = dict(pool)

    # ---------------- temporal replay feasibility
    order = sorted(lot.items(), key=lambda kv: (kv[1][0], kv[0]))
    seen_any, seen_code, seen_cls, seen_cust = set(), set(), set(), set()
    st, pst = Counter(), Counter()
    pending, cur = [], None

    def flush():
        for l in pending:
            codes = lot_codes.get(l, ())
            cust = lot[l][2]
            for inn, _ in sups.get(l, ()):
                seen_any.add(inn)
                seen_cust.add((inn, cust))
                for c in codes:
                    seen_code.add((inn, c))
                    seen_cls.add((inn, c[:5]))
        pending.clear()

    for lid, (d, p, cust, _sj, _pr, _smp) in order:
        if d != cur:
            flush()
            cur = d
        pending.append(lid)
        if p != C["replay_platform"] or d < C["replay_from"]:
            continue
        s = sups.get(lid, [])
        codes = lot_codes.get(lid)
        win = sorted(i for i, w in s if w)
        if not win or not codes:
            continue
        w0 = win[0]
        st["target_lots"] += 1
        st["winner_seen_any"] += w0 in seen_any
        st["winner_seen_same_full_code"] += any((w0, c) in seen_code for c in codes)
        st["winner_seen_same_class_xx_xx"] += any((w0, c[:5]) in seen_cls for c in codes)
        st["winner_seen_same_customer"] += (w0, cust) in seen_cust
        for inn, _ in s:
            pst["participants"] += 1
            pst["participant_seen_same_class_xx_xx"] += any((inn, c[:5]) in seen_cls for c in codes)
    flush()
    del seen_any, seen_code, seen_cls, seen_cust
    t = st["target_lots"]
    R["replay"] = {
        "definition": "targets: platform=replay_platform, publish_date>=replay_from, has winner and items; "
                      "history: all lots with strictly earlier publish_date; class = first 5 chars (XX.XX)",
        **dict(st),
        "pct": {k: pct(v, t) for k, v in st.items() if k != "target_lots"},
        **dict(pst),
        "participant_seen_same_class_pct": pct(pst["participant_seen_same_class_xx_xx"], pst["participants"]),
    }
    print("[profile] replay done", file=sys.stderr, flush=True)

    # ---------------- golden lots: naive same-code award-count baseline (preview, not a product metric)
    golden = {}
    winner_of = {}
    for g in C["golden_lots"] + C["extra_golden_lots"]:
        if g not in lot:
            golden[g] = {"exists": False}
            continue
        d, p, cust, _sj, price, _smp = lot[g]
        gc = lot_codes.get(g, set())
        cnt, cls = Counter(), Counter()
        gcls = {c[:5] for c in gc}
        for l, s in sups.items():
            if lot[l][0] >= d:
                continue
            lc = lot_codes.get(l, set())
            hit = bool(lc & gc)
            hitc = bool({c[:5] for c in lc} & gcls)
            if not (hit or hitc):
                continue
            for inn, w in s:
                if w and hit:
                    cnt[inn] += 1
                if w and hitc:
                    cls[inn] += 1
        ranked = [k for k, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))]
        s = sups.get(g, [])
        win = sorted(i for i, w in s if w)
        winner_of[g] = set(win)
        top20 = set(ranked[:20])
        golden[g] = {
            "exists": True, "publish_date": d, "platform": p, "start_price": price,
            "subject": subj_raw.get(g, ""), "n_items": len(interest_items.get(g, [])),
            "items": [[n[:200], c] for n, c in interest_items.get(g, [])[:15]],
            "okpd2_codes": sorted(gc), "participants": len(s), "winners": len(win),
            "winner_entity_types": [inn_kind(w) for w in win],
            "same_code_candidates_before": len(cnt),
            "winner_prior_same_code_awards": [cnt[w] for w in win],
            "winner_prior_same_class_awards": [cls[w] for w in win],
            # tie-independent competition rank: 1 + suppliers with strictly more prior same-code awards
            "winner_naive_rank": [1 + sum(1 for v in cnt.values() if v > cnt[w]) if w in cnt else None for w in win],
            "winner_naive_rank_ties": [sum(1 for v in cnt.values() if v == cnt[w]) - 1 if w in cnt else None for w in win],
            "participants_in_naive_top20": sum(1 for i, _ in s if i in top20),
        }
    for g, info in golden.items():
        if info.get("exists"):
            info["winner_participates_in_other_golden_lots"] = sorted(
                o for o in golden if o != g and golden[o].get("exists")
                and winner_of[g] & {i for i, _ in sups.get(o, [])})
    R["golden_lots"] = golden
    R["example_lots"] = {
        e: {"subject": subj_raw.get(e, ""), "n_items": len(interest_items.get(e, [])),
            "okpd2_codes": sorted(lot_codes.get(e, set())),
            "items_sample": [[n[:120], c] for n, c in interest_items.get(e, [])[:10]]}
        for e in C["example_lots"]}

    # ---------------- generic-title candidates
    gen_re = re.compile(C["generic_subject_regex"], re.I)
    gl = []  # filled after the second ТРУ pass (needs item names of candidate lots)

    # ---------------- supplier pool health
    def health(level_fn, min_lots):
        agg = {}
        for lid, codes in lot_codes.items():
            info = lot.get(lid)
            if not info:
                continue
            keys = {level_fn(c) for c in codes}
            s = sups.get(lid, [])
            for k in keys:
                a = agg.get(k)
                if a is None:
                    a = agg[k] = {"lots": 0, "em_lots": 0, "cust": set(), "sup": set(), "win": Counter(), "recent": set()}
                a["lots"] += 1
                a["cust"].add(info[2])
                if info[1] == "ЭМ":
                    a["em_lots"] += 1
                for inn, w in s:
                    a["sup"].add(inn)
                    if w:
                        a["win"][inn] += 1
                        if info[0] >= C["recent_from"]:
                            a["recent"].add(inn)
        out = {}
        for k, a in agg.items():
            tw = sum(a["win"].values())
            if a["lots"] < min_lots or tw == 0:
                continue
            shares = sorted(a["win"].values(), reverse=True)
            out[k] = {
                "lots": a["lots"], "em_lots": a["em_lots"], "customers": len(a["cust"]),
                "observed_suppliers": len(a["sup"]), "winning_suppliers": len(a["win"]),
                "recent_winning_suppliers": len(a["recent"]), "awards": tw,
                "top1_share": round(shares[0] / tw, 3), "top3_share": round(sum(shares[:3]) / tw, 3),
                "hhi": round(sum((c / tw) ** 2 for c in shares), 3),
                "top3_award_counts": shares[:3],
            }
        return out

    full = health(lambda c: c, C["pool_min_lots"])
    cands = [(k, v) for k, v in full.items()
             if k[:2].isdigit() and int(k[:2]) <= C["shortlist_max_section"]
             and v["lots"] >= C["shortlist_min_lots"] and v["customers"] >= C["shortlist_min_customers"]]
    by_conc = sorted(cands, key=lambda kv: (-kv[1]["top1_share"], -kv[1]["lots"], kv[0]))[:C["shortlist_size"]]
    by_few = sorted(cands, key=lambda kv: (kv[1]["winning_suppliers"], -kv[1]["lots"], kv[0]))[:C["fewest_winners_size"]]
    cls_h = health(lambda c: ".".join(c.split(".")[:3]), 10)
    R["pool_health"] = {
        "definition": "per full OKPD2 code; lot counted if any item has the code; awards = winner rows (both platforms); "
                      "recent = won a lot published >= recent_from",
        "codes_evaluated": len(full),
        "shortlist_candidates": len(cands),
        "selected": {c: full.get(c) for c in C["pool_health_codes"]},
        "selected_prefixes": {c: cls_h.get(c) for c in C["pool_health_class_prefixes"]},
        "shortlist_by_top1_share": [[k, v] for k, v in by_conc],
        "shortlist_fewest_winners": [[k, v] for k, v in by_few],
    }
    names_for = set(C["pool_health_codes"]) | {k for k, _ in by_conc} | {"26.20.13.000", "26.20.11.110", "31.01.11.150",
                                                                        "22.19.60.119", "32.99.59.000"}

    # ---------------- second ТРУ pass: names for codes + generic-title candidates
    em25 = {lid for lid, info in lot.items() if info[1] == "ЭМ" and info[0] >= "2025-01-01"
            and len(sups.get(lid, [])) >= C["generic_min_participants"]
            and any(w for _, w in sups.get(lid, []))
            and 1 <= items_per_lot.get(lid, 0) <= C["generic_max_items"]}
    em25_items = defaultdict(list)
    code_names = defaultdict(Counter)
    f, rd, header = reader(raw / FILES["items"])
    ix = {c: i for i, c in enumerate(header)}
    for row in rd:
        if len(row) != len(header):
            continue
        lid, nm, code = row[ix["lot_id"]], row[ix["product_name"]], row[ix["okpd2_code"]].strip()
        if code in names_for:
            code_names[code][nm.strip().lower()[:70]] += 1
        if lid in em25:
            em25_items[lid].append((nm.strip(), code))
    f.close()
    R["pool_health"]["top_item_names_by_code"] = {c: top(code_names[c], 6) for c in sorted(names_for)}

    # subjects for generic candidates require raw subjects: re-read notices for em25 lots only
    f, rd, header = reader(raw / FILES["notices"])
    ix = {c: i for i, c in enumerate(header)}
    em25_subj = {}
    for row in rd:
        if len(row) == len(header) and row[ix["lot_id"]] in em25:
            em25_subj[row[ix["lot_id"]]] = row[ix["subject"]].strip()
    f.close()
    for lid in em25:
        sj = em25_subj.get(lid, "")
        it = em25_items.get(lid, [])
        if (gen_re.search(sj) and len(sj) < C["generic_subject_max_len"]
                and all(n.lower()[:25] not in sj.lower() for n, _ in it)):
            gl.append([lid, lot[lid][0], sj[:80], [[n[:90], c] for n, c in it], len(sups[lid])])
    gl.sort(key=lambda x: (-x[4], x[0]))
    R["generic_title_candidates"] = {"count": len(gl), "top": gl[:C["generic_list_size"]]}
    return R


# ----------------------------------------------------------------------------- markdown
def fmt(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def render_md(R: dict) -> str:
    N, S, I, O = R["notices"], R["suppliers"], R["items"], R["items"]["okpd2"]
    L = []
    a = L.append
    a("# Dataset Profile — Organizer Data 2024–2025 (P1-001A)")
    a("")
    a(f"> Generated by `scripts/profile_dataset.py` v{R['profile_version']} from `reports/dataset_profile.json`. "
      "Full scan of all rows; deterministic; supplier INNs are never printed. Run metadata: `reports/dataset_profile.meta.json`.")
    a("> Interpretation and decisions: `docs/analysis/REAL_DATASET_ANALYSIS_2024_2025.md`.")
    a("")
    a("## 1. Files")
    a("| Key | File | Bytes | Rows | Malformed rows | SHA-256 (first 16) |")
    a("|---|---|---:|---:|---:|---|")
    for k, sec in (("notices", N), ("suppliers", S), ("items", I)):
        fi = R["files"][k]
        a(f"| {k} | `{fi['name']}` | {fmt(fi['size_bytes'])} | {fmt(sec['rows'])} | {sec['malformed_rows']} | `{fi['sha256'][:16]}` |")
    a("")
    a("## 2. Notices (lots)")
    a(f"- Unique lots **{fmt(N['unique_lots'])}** (duplicate rows {N['duplicate_lot_rows']}); unique procedures {fmt(N['unique_procedures'])} "
      f"(max lots per procedure {N['max_lots_per_procedure']}).")
    a(f"- Dates {N['date_min']} → {N['date_max']}; by year {N['by_year']}.")
    a(f"- Platform × year: {N['by_platform_year']}; share % {N['platform_share_pct']}.")
    a(f"- Customers {fmt(N['unique_customers'])}; customer KPP empty {fmt(N['customer_kpp_empty_rows'])}.")
    a(f"- `procedure_name` = `subject`: exact {fmt(N['procedure_name_eq_subject_exact'])} ({N['procedure_name_eq_subject_exact_pct']}%), "
      f"normalized {fmt(N['procedure_name_eq_subject_normalized'])} ({N['procedure_name_eq_subject_normalized_pct']}%).")
    a(f"- `is_smp` by platform: {N['is_smp_by_platform']}; `reqnum` filled {fmt(N['reqnum_filled'])} ({N['reqnum_filled_pct']}%).")
    a(f"- `start_price`: empty {N['start_price_empty_or_unparsable']}, zero {N['start_price_zero']}, quantiles {N['start_price_quantiles']}.")
    a("")
    a("## 3. Integrity & coverage")
    a(f"- Supplier rows with unknown lot: {S['orphan_rows_lot_not_in_notices']}; item rows with unknown lot: {I['orphan_rows_lot_not_in_notices']}.")
    a(f"- Coverage by platform: {R['coverage']['by_platform']}.")
    a(f"- Lots without supplier by year: {R['coverage']['lots_without_supplier_by_year']}.")
    a(f"- Duplicate (lot, INN) pairs: {S['duplicate_lot_inn_pairs']}.")
    a("")
    a("## 4. Supplier relations & `is_winner`")
    a("| Platform\\|year | Lots | With supplier | Rows | Winner rows | Non-winner rows | ≥2 suppliers | 0 winners | Mean suppliers/lot | Max |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k, v in sorted(R["supplier_semantics"]["by_platform_year"].items()):
        a(f"| {k} | {fmt(v.get('lots', 0))} | {fmt(v.get('lots_with_supplier', 0))} | {fmt(v.get('supplier_rows', 0))} | "
          f"{fmt(v.get('rows_winner', 0))} | {fmt(v.get('rows_non_winner', 0))} | {fmt(v.get('lots_with_2plus_suppliers', 0))} | "
          f"{fmt(v.get('lots_with_0_winners', 0))} | {v.get('mean_suppliers_per_lot', '-')} | {v.get('max_suppliers_per_lot', '-')} |")
    a("")
    a(f"- All АИС ГЗ supplier rows have `is_winner=true`: **{R['supplier_semantics']['all_ais_gz_rows_winner']}** "
      "(fact; \"award-only\" is a working interpretation pending OQ-33).")
    a(f"- INN platform overlap: {R['supplier_semantics']['inn_platform_overlap']}; ЭМ participants never won on ЭМ: "
      f"{fmt(R['supplier_semantics']['em_participants_never_won_on_em'])}.")
    a(f"- Unique INNs {fmt(S['unique_inns'])}; kinds {S['inn_kind_unique']} ({S['inn_kind_unique_pct']} %); "
      f"checksum-invalid (well-formed length) {S['inn_checksum_invalid_unique']}.")
    a(f"- INN length (rows) {S['inn_length_rows']}; non-digit rows {S['inn_nondigit_rows']}; KPP empty {fmt(S['kpp_empty_rows'])} "
      f"({S['kpp_empty_pct']}%), KPP bad format {S['kpp_bad_format_rows']}.")
    a(f"- INN region prefix (unique INNs): {S['inn_region_prefix_unique_top']}; (rows): {S['inn_region_prefix_rows_top']}.")
    a("")
    a("## 5. ТРУ items")
    a(f"- Rows {fmt(I['rows'])} over {fmt(I['unique_lots'])} lots; mean {I['items_per_lot_mean']} items/lot, max {I['items_per_lot_max']}.")
    a(f"- Items per lot (11 = 11+): {I['items_per_lot_hist_11plus']} → % {I['items_per_lot_pct']}.")
    a(f"- Distinct OKPD2 per lot (4 = 4+): {I['distinct_okpd2_per_lot_hist_4plus']}; multi-code lots {fmt(I['lots_with_multiple_okpd2'])} ({I['lots_with_multiple_okpd2_pct']}%).")
    a(f"- `product_name` length quantiles {I['product_name_length_quantiles']}; empty {I['product_name_empty_rows']}.")
    a(f"- Item = lot subject (normalized) {fmt(I['product_name_eq_subject_normalized_rows'])} ({I['product_name_eq_subject_pct']}%); "
      f"contained in subject {fmt(I['product_name_substring_of_subject_rows'])} ({I['product_name_substring_of_subject_pct']}%); "
      f"adds text {I['product_name_adds_text_pct']}%.")
    a("")
    a("## 6. OKPD2")
    a(f"- Unique codes {fmt(O['unique_codes'])}; empty {O['empty_rows']}; bad format {O['bad_format_rows']}.")
    a(f"- Depth (segments) rows {O['depth_rows']} → % {O['depth_rows_pct']}; distinct codes by depth {O['depth_unique_codes']}.")
    a(f"- Distinct prefixes per segment level {O['distinct_prefixes_by_segment_level']}.")
    a(f"- Top sections (rows): {O['top_sections_rows']}.")
    a(f"- Top codes (rows): {O['top_codes_rows']}.")
    a("")
    a("## 7. Temporal replay feasibility")
    rp = R["replay"]
    a(f"- {rp['definition']}.")
    a(f"- Target lots {fmt(rp['target_lots'])}; winner seen before: any {fmt(rp['winner_seen_any'])}, same class {fmt(rp['winner_seen_same_class_xx_xx'])}, "
      f"same full code {fmt(rp['winner_seen_same_full_code'])}, same customer {fmt(rp['winner_seen_same_customer'])} → % {rp['pct']}.")
    a(f"- Participants seen in same class: {fmt(rp['participant_seen_same_class_xx_xx'])} / {fmt(rp['participants'])} ({rp['participant_seen_same_class_pct']}%).")
    a(f"- Benchmark pool: {R['benchmark_pool']}.")
    a("")
    a("## 8. Golden lots (naive same-code award-count rank of the winner — preview only)")
    a("| lot | date | platform | items | OKPD2 | participants | same-code candidates | winner prior same-code awards | naive rank | in other golden lots |")
    a("|---|---|---|---:|---|---:|---:|---|---|---|")
    for g, v in R["golden_lots"].items():
        if not v.get("exists"):
            a(f"| {g} | missing | | | | | | | | |")
            continue
        a(f"| {g} | {v['publish_date']} | {v['platform']} | {v['n_items']} | {', '.join(v['okpd2_codes'])} | {v['participants']} | "
          f"{v['same_code_candidates_before']} | {v['winner_prior_same_code_awards']} | {v['winner_naive_rank']} (ties {v['winner_naive_rank_ties']}) | "
          f"{', '.join(v['winner_participates_in_other_golden_lots']) or '-'} |")
    a("")
    for g, v in R["golden_lots"].items():
        if v.get("exists"):
            a(f"- **{g}** — {v['subject'][:120]} → " + "; ".join(n[:100] for n, _ in v["items"][:3]))
    a("")
    for e, v in R["example_lots"].items():
        a(f"- Example {e}: {v['subject']} — {v['n_items']} items, codes {v['okpd2_codes']}.")
    a("")
    a(f"Generic-title candidates (ЭМ 2025): {R['generic_title_candidates']['count']} found; top by participants:")
    for lid, d, sj, it, n in R["generic_title_candidates"]["top"][:15]:
        a(f"- {lid} ({d}, {n} participants): {sj} → " + "; ".join(x[0][:70] for x in it))
    a("")
    a("## 9. Supplier pool health")
    ph = R["pool_health"]
    a(f"- {ph['definition']}. Codes evaluated {ph['codes_evaluated']}; goods shortlist candidates {ph['shortlist_candidates']}.")
    a("")
    a("| OKPD2 | Top item name | Lots | Customers | Observed suppliers | Winning suppliers | Recent winners | Top-1 | Top-3 | HHI |")
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    rows = list(ph["selected"].items()) + [(k, v) for k, v in ph["shortlist_by_top1_share"] if k not in ph["selected"]]
    for k, v in rows[:30]:
        if not v:
            continue
        nm = (ph["top_item_names_by_code"].get(k) or [["", 0]])[0][0]
        a(f"| {k} | {nm[:45]} | {v['lots']} | {v['customers']} | {v['observed_suppliers']} | {v['winning_suppliers']} | "
          f"{v['recent_winning_suppliers']} | {v['top1_share']} | {v['top3_share']} | {v['hhi']} |")
    a("")
    a(f"- Class prefixes: {ph['selected_prefixes']}.")
    a("")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- main
def main() -> int:
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", type=Path, default=root / "data" / "raw")
    ap.add_argument("--out", type=Path, default=root / "reports")
    args = ap.parse_args()
    for name in FILES.values():
        if not (args.raw / name).is_file():
            print(f"missing input: {args.raw / name}", file=sys.stderr)
            return 2
    t0 = time.perf_counter()
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    R = profile(args.raw)
    for key, cols in EXPECTED_COLUMNS.items():
        R["files"][key]["columns_match_expected"] = R["files"][key]["columns"] == cols
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "dataset_profile.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    with open(args.out / "dataset_profile.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(render_md(R))
    runtime = round(time.perf_counter() - t0, 1)
    meta = {"started_utc": started, "runtime_seconds": runtime, "python": sys.version.split()[0],
            "platform": py_platform.platform(), "profile_version": PROFILE_VERSION}
    with open(args.out / "dataset_profile.meta.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"[profile] done in {runtime}s → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
