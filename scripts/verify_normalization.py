#!/usr/bin/env python3
"""P1-001C — Read-only verification of backend/app/shared/normalize.py against the real organizer data.

Covers all distinct supplier/customer INNs, all KPPs, all distinct OKPD2 codes, all distinct product names, every
platform / boolean literal, every date and price value. Cross-checks INN/KPP/OKPD2 results with the P1-001B
reference mapping (scripts/validate_contracts.py) and compares counts with P1-001A facts (reports/dataset_profile.json).
Writes reports/normalization_verification.json (deterministic; timings are printed only).

Usage: python scripts/verify_normalization.py [--raw data/raw]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.shared import normalize as N  # noqa: E402
import validate_contracts as ref  # noqa: E402  (P1-001B reference mapping = oracle)

csv.field_size_limit(10 ** 9)
FILES = {"notices": "Извещения_24-25.csv", "suppliers": "Поставщики_24-25.csv", "items": "ТРУ_24-25.csv"}
NORMALIZED_CHARS = re.compile(r"[a-zа-я0-9 .,\-/+\"%]")
UNIT_SUP = re.compile(r"(?<=[мm])[²³]")


def rows(raw: Path, key: str):
    with open(raw / FILES[key], encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f, delimiter=";", quotechar='"')
        header = next(r)
        for row in r:
            yield dict(zip(header, row))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    args = ap.parse_args()
    profile = json.loads((ROOT / "reports" / "dataset_profile.json").read_text(encoding="utf-8"))
    out, timings, problems = {"normalization_version": N.NORMALIZATION_VERSION}, {}, []

    # ---------------- notices: platform, is_smp, dates, prices, customer INN/KPP, subject
    t = time.perf_counter()
    plat, smp, date_shape, cust_inn, cust_kpp, price_flags, subj_flags = (Counter() for _ in range(7))
    dates, errors, pn_variant = set(), Counter(), 0
    for r in rows(args.raw, "notices"):
        try:
            plat[N.normalize_platform(r["is_eshop_or_aisgz"])] += 1
        except N.NormalizationError:
            errors["platform"] += 1
        try:
            smp[str(N.parse_bool(r["is_smp"]))] += 1
        except N.NormalizationError:
            errors["is_smp"] += 1
        dates.add(r["publish_date"])
        date_shape[re.sub(r"\d", "9", r["publish_date"])] += 1
        try:
            price_flags.update(N.normalize_price(r["start_price"]).flags or ("OK",))
        except N.NormalizationError:
            errors["start_price"] += 1
        ci = N.normalize_inn(r["customer_inn"])
        cust_inn.update(ci.flags or (ci.entity_type,))
        ck = N.normalize_kpp(r["customer_kpp"])
        cust_kpp.update(ck.flags or ("OK",))
        subj_flags.update(N.normalize_subject(r["subject"]).flags or ("OK",))
        pn_variant += N.procedure_name_variant(r["procedure_name"], r["subject"]) is not None
    date_errors = 0
    for d in dates:
        try:
            N.normalize_date(d)
        except N.NormalizationError:
            date_errors += 1
    timings["notices_s"] = round(time.perf_counter() - t, 1)
    out["notices"] = {"platform": dict(plat), "is_smp": dict(smp), "structural_errors": dict(errors),
                      "date_shapes": dict(date_shape), "distinct_dates": len(dates), "invalid_dates": date_errors,
                      "start_price_flags": dict(price_flags), "customer_inn": dict(cust_inn), "customer_kpp": dict(cust_kpp),
                      "subject_flags": dict(subj_flags), "procedure_name_variant_lots": pn_variant}

    # ---------------- suppliers: distinct INN (raw spellings), KPP, is_winner
    t = time.perf_counter()
    raw_inns, kpps, win, win_err = Counter(), Counter(), Counter(), 0
    for r in rows(args.raw, "suppliers"):
        raw_inns[r["supplier_inn"]] += 1
        kpps[r["supplier_kpp"]] += 1
        try:
            win[str(N.parse_bool(r["is_winner"]))] += 1
        except N.NormalizationError:
            win_err += 1
    canon, et, inn_flags_distinct, inn_flag_rows, oracle_mismatch = {}, Counter(), Counter(), Counter(), []
    for raw, n in raw_inns.items():
        res = N.normalize_inn(raw)
        inn_flag_rows.update({f: n for f in res.flags})
        if res.inn not in canon:
            canon[res.inn] = res
            et[res.entity_type] += 1
            inn_flags_distinct.update(res.flags)
        if res.inn and list(res.flags) != [f for f in ref.inn_flags(res.inn)]:
            oracle_mismatch.append(("inn", raw))
    kpp_flags = Counter()
    for raw, n in kpps.items():
        k = N.normalize_kpp(raw)
        kpp_flags.update({f: n for f in (k.flags or ("OK",))})
        kv, kf = ref.kpp_value_flags(raw)
        if (k.kpp, list(k.flags)) != (kv, kf):
            oracle_mismatch.append(("kpp", raw))
    timings["suppliers_s"] = round(time.perf_counter() - t, 1)
    out["suppliers"] = {"distinct_raw_inn_spellings": len(raw_inns), "distinct_canonical_inns": len(canon),
                        "entity_type_distinct": dict(et), "inn_flags_distinct": dict(inn_flags_distinct),
                        "inn_flags_rows": dict(inn_flag_rows), "kpp_flags_rows": dict(kpp_flags),
                        "is_winner": dict(win), "is_winner_errors": win_err,
                        "malformed_inn_shapes": dict(Counter(re.sub(r"[^\W\d_]", "a", re.sub(r"\d", "9", k))
                                                             for k, v in canon.items() if v.entity_type == "unknown"))}

    # ---------------- items: distinct OKPD2, distinct product names
    t = time.perf_counter()
    codes, names = Counter(), Counter()
    for r in rows(args.raw, "items"):
        codes[r["okpd2_code"]] += 1
        names[r["product_name"]] += 1
    okpd_depth_distinct, okpd_flags_rows, okpd_invalid = Counter(), Counter(), []
    canon_codes = set()
    for raw, n in codes.items():
        o = N.normalize_okpd2(raw)
        okpd_flags_rows.update({f: n for f in (o.flags or ("OK",))})
        if o.okpd2_code:
            if o.okpd2_code not in canon_codes:
                canon_codes.add(o.okpd2_code)
                okpd_depth_distinct[str(o.okpd2_depth)] += 1
        elif o.flags == (N.INVALID_OKPD2,):
            okpd_invalid.append(raw)
        fields, flags = ref.okpd2_fields(raw)
        if (o.okpd2_code, list(o.flags)) != (fields["okpd2_code"], flags) or \
                any(getattr(o, k) != v for k, v in fields.items()):
            oracle_mismatch.append(("okpd2", raw))
    name_flags, markers, empty_after, not_idem, digit_loss, bad_chars, examples = (Counter(), Counter(), 0, 0, 0, Counter(), [])
    for raw, n in names.items():
        p = N.normalize_product_name(raw)
        name_flags.update({f: n for f in (p.flags or ("OK",))})
        if p.type_marker:
            markers[p.type_marker] += n
        if not p.flags and p.normalized is None:
            empty_after += n
            if len(examples) < 5:
                examples.append(raw[:60])
        if p.normalized is not None:
            if N.normalize_text(p.normalized) != p.normalized:
                not_idem += 1
            base = unicodedata.normalize("NFC", raw).lower()
            # isdecimal(): superscripts (¹ ² ³) are not decimal digits; only м²/м³ add a digit
            expected_digits = sum(c.isdecimal() for c in base) + len(UNIT_SUP.findall(base))
            if sum(c.isdecimal() for c in p.normalized) != expected_digits:
                digit_loss += 1
            for ch in NORMALIZED_CHARS.sub("", p.normalized):
                bad_chars[ch] += n
    timings["items_s"] = round(time.perf_counter() - t, 1)
    out["items"] = {"distinct_raw_okpd2": len(codes), "distinct_valid_okpd2": len(canon_codes),
                    "okpd2_depth_distinct_valid": dict(okpd_depth_distinct), "okpd2_flags_rows": dict(okpd_flags_rows),
                    "okpd2_invalid_values": sorted(okpd_invalid),
                    "distinct_product_names": len(names), "product_name_flags_rows": dict(name_flags),
                    "generic_type_marker_rows": sum(markers.values()), "top_type_markers": sorted(markers.items(), key=lambda kv: (-kv[1], kv[0]))[:5],
                    "nonempty_names_normalized_to_null_rows": empty_after, "nonempty_names_normalized_to_null_examples": examples,
                    "non_idempotent_distinct_names": not_idem, "digit_count_mismatch_distinct_names": digit_loss,
                    "chars_outside_core_alphabet_rows": dict(sorted(bad_chars.items(), key=lambda kv: (-kv[1], kv[0]))[:25])}

    # ---------------- comparisons with P1-001A / P1-001B facts
    P = profile
    expect = {
        "platform AIS_GZ lots": (plat["AIS_GZ"], P["notices"]["by_platform"]["АИС ГЗ"]),
        "platform EM lots": (plat["EM"], P["notices"]["by_platform"]["ЭМ"]),
        "is_smp true": (smp["True"], P["notices"]["is_smp_by_platform"].get("АИС ГЗ|true", 0)),
        "MISSING_START_PRICE": (price_flags[N.MISSING_START_PRICE], 3),
        "ZERO_START_PRICE": (price_flags[N.ZERO_START_PRICE], 21),
        "MISSING_SUBJECT": (subj_flags[N.MISSING_SUBJECT], 1),
        "customer MISSING_INN": (cust_inn[N.MISSING_INN], 8449),
        "customer INVALID_INN_FORMAT": (cust_inn[N.INVALID_INN_FORMAT], 0),
        "customer INVALID_INN_CHECKSUM": (cust_inn[N.INVALID_INN_CHECKSUM], 0),
        "customer MISSING_KPP": (cust_kpp[N.MISSING_KPP], 8449),
        "distinct supplier INNs": (len(canon), P["suppliers"]["unique_inns"]),
        "legal_entity": (et["legal_entity"], P["suppliers"]["inn_kind_unique"]["legal_entity"]),
        "individual_entrepreneur": (et["individual_entrepreneur"], P["suppliers"]["inn_kind_unique"]["individual_entrepreneur"]),
        "unknown (malformed)": (et["unknown"], P["suppliers"]["inn_kind_unique"]["invalid"]),
        "INN checksum invalid (distinct)": (inn_flags_distinct[N.INVALID_INN_CHECKSUM], P["suppliers"]["inn_checksum_invalid_unique"]),
        "INN checksum invalid (rows)": (inn_flag_rows[N.INVALID_INN_CHECKSUM], 119),
        "supplier MISSING_KPP rows": (kpp_flags[N.MISSING_KPP], P["suppliers"]["kpp_empty_rows"]),
        "INVALID_KPP_FORMAT rows": (kpp_flags[N.INVALID_KPP_FORMAT], 0),
        "is_winner true": (win["True"], P["suppliers"]["is_winner_values"]["true"]),
        "MISSING_OKPD2 rows": (okpd_flags_rows[N.MISSING_OKPD2], P["items"]["okpd2"]["empty_rows"]),
        "INVALID_OKPD2 rows": (okpd_flags_rows[N.INVALID_OKPD2], 1),
        "distinct valid OKPD2": (len(canon_codes), P["items"]["okpd2"]["unique_codes"] - 1),
        "MISSING_PRODUCT_NAME rows": (name_flags[N.MISSING_PRODUCT_NAME], P["items"]["product_name_empty_rows"]),
        "reference-mapping mismatches": (len(oracle_mismatch), 0),
        "structural errors (platform/bool/price/date)": (sum(errors.values()) + win_err + date_errors, 0),
        "non-idempotent names": (not_idem, 0),
        "digit-count mismatches": (digit_loss, 0),
    }
    out["checks"] = {k: {"normalize": a, "expected": b, "ok": a == b} for k, (a, b) in expect.items()}
    for k, v in out["checks"].items():
        if not v["ok"]:
            problems.append(f"{k}: {v['normalize']} != {v['expected']}")
    out["reference_mismatch_examples"] = oracle_mismatch[:10]

    # ---------------- throughput (in-memory, informative)
    sample_names = list(names)[:200_000]
    sample_inns = list(raw_inns)
    sample_codes = list(codes)
    t = time.perf_counter(); [N.normalize_product_name(x) for x in sample_names]; tn = time.perf_counter() - t
    t = time.perf_counter(); [N.normalize_inn(x) for x in sample_inns]; ti = time.perf_counter() - t
    t = time.perf_counter(); [N.normalize_okpd2(x) for x in sample_codes]; to = time.perf_counter() - t
    timings["throughput"] = {"product_name_per_s": int(len(sample_names) / tn), "inn_per_s": int(len(sample_inns) / ti),
                             "okpd2_per_s": int(len(sample_codes) / to),
                             "est_seconds_for_2_97M_names": round(2_971_651 / (len(sample_names) / tn), 1)}

    (ROOT / "reports").mkdir(exist_ok=True)
    with open(ROOT / "reports" / "normalization_verification.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({"checks_failed": problems, "timings": timings}, ensure_ascii=False, indent=1))
    print("RESULT:", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
