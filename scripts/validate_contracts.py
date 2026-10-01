#!/usr/bin/env python3
"""P1-001B — Validate canonical contracts v0.2.0 (stdlib only, no network, read-only).

Checks
  1. Every contracts/*.schema.json is well-formed: Draft 2020-12 $schema, $id == file name, version == 0.2.0,
     and uses ONLY the keyword subset this validator implements (an unsupported keyword is an error, never
     silently ignored).
  2. contracts/source_mapping.json covers every source column listed in reports/dataset_profile.json
     (MAPPED or NOT_MAPPED with a reason) — no silent dropping.
  3. Representative source rows (contracts/fixtures/source_rows.json — real shapes, masked identifiers) are
     mapped with the REFERENCE mapping below and every resulting record validates; enrichment fixtures validate.
  4. Every negative case in contracts/fixtures/invalid_records.json is rejected.
  5. Mapping is deterministic (two runs produce identical output).
  6. Optional: --raw DIR maps and validates real rows for the first N lots of the organizer CSVs (read-only).

Why a built-in validator: no JSON Schema library is installed (python `jsonschema` absent; the frontend's
transitive `ajv` 6.x supports only draft-07). Formats date / date-time / uuid / uri are asserted.

The reference mapping is a specification aid for P1-001B; production normalization belongs to P1-001C
(scripts/backend shared normalize) and ingestion to P1-001D. Rules: docs/domain/DATA_MAPPING.md.

Usage: python scripts/validate_contracts.py [--raw data/raw] [--raw-lots 2000]
"""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"
CONTRACT_VERSION = "0.2.0"
DRAFT = "https://json-schema.org/draft/2020-12/schema"
NAMESPACE = uuid.UUID("9a58f195-b16e-554c-b016-5a636976af05")  # = uuid5(NAMESPACE_URL, "urn:supplier-radar:canonical")

ENTITY_SCHEMAS = {
    "procurement_lot": "procurement_lot.schema.json",
    "procurement_item": "procurement_item.schema.json",
    "supplier_history": "supplier_history.schema.json",
    "supplier": "supplier.schema.json",
    "supplier_profile": "supplier_profile.schema.json",
    "supplier_evidence": "supplier_evidence.schema.json",
}
SOURCE_FILES = {"notices_24_25": "Извещения_24-25.csv", "suppliers_24_25": "Поставщики_24-25.csv", "items_24_25": "ТРУ_24-25.csv"}

# ============================================================================ minimal JSON Schema 2020-12 validator
SCHEMA_KEYS = {"$schema", "$id", "$ref", "$defs", "type", "enum", "const", "pattern", "format", "minLength", "maxLength",
               "minimum", "maximum", "required", "properties", "additionalProperties", "items", "minItems", "maxItems",
               "uniqueItems", "contains", "allOf", "anyOf", "oneOf", "not", "if", "then", "else"}
ANNOTATION_KEYS = {"title", "description", "version", "$comment", "examples", "default"}
SUBSCHEMA_KEYS = {"items", "contains", "not", "if", "then", "else", "additionalProperties"}
SUBSCHEMA_LIST_KEYS = {"allOf", "anyOf", "oneOf"}
SUBSCHEMA_MAP_KEYS = {"properties", "$defs"}
FORMAT_CHECKS = {
    "date": lambda s: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)) and _try(lambda: dt.date.fromisoformat(s)),
    "date-time": lambda s: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})", s))
    and _try(lambda: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))),
    "uuid": lambda s: bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", s)),
    "uri": lambda s: bool(urlparse(s).scheme) and bool(urlparse(s).netloc),
}


def _try(fn) -> bool:
    try:
        fn()
        return True
    except ValueError:
        return False


def meta_check(schema, where="#", errors=None):
    """Reject unsupported keywords anywhere in a schema."""
    errors = [] if errors is None else errors
    if isinstance(schema, bool):
        return errors
    if not isinstance(schema, dict):
        errors.append(f"{where}: schema must be an object or boolean")
        return errors
    for k, v in schema.items():
        if k in ANNOTATION_KEYS:
            continue
        if k not in SCHEMA_KEYS:
            errors.append(f"{where}: unsupported keyword '{k}'")
            continue
        if k in SUBSCHEMA_KEYS:
            meta_check(v, f"{where}/{k}", errors)
        elif k in SUBSCHEMA_LIST_KEYS:
            for i, s in enumerate(v):
                meta_check(s, f"{where}/{k}/{i}", errors)
        elif k in SUBSCHEMA_MAP_KEYS:
            for name, s in v.items():
                meta_check(s, f"{where}/{k}/{name}", errors)
    return errors


def _type_ok(t, x) -> bool:
    return {
        "null": x is None, "boolean": isinstance(x, bool), "object": isinstance(x, dict), "array": isinstance(x, list),
        "string": isinstance(x, str), "integer": isinstance(x, int) and not isinstance(x, bool),
        "number": isinstance(x, (int, float)) and not isinstance(x, bool),
    }[t]


def _eq(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


class Validator:
    def __init__(self, schemas: dict):
        self.schemas = schemas  # $id -> schema

    def resolve(self, ref: str, base_id: str):
        doc_id, _, frag = ref.partition("#")
        doc_id = doc_id or base_id
        node = self.schemas[doc_id]
        for part in [p for p in frag.split("/") if p]:
            node = node[part]
        return node, doc_id

    def validate(self, schema, x, base_id, path="$"):
        errs = []
        if schema is True:
            return errs
        if schema is False:
            return [f"{path}: not allowed"]
        if "$ref" in schema:
            target, doc = self.resolve(schema["$ref"], base_id)
            errs += self.validate(target, x, doc, path)
        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_type_ok(t, x) for t in types):
                return errs + [f"{path}: expected type {types}, got {type(x).__name__}"]
        if "enum" in schema and not any(_eq(x, e) for e in schema["enum"]):
            errs.append(f"{path}: {x!r} not in enum")
        if "const" in schema and not _eq(x, schema["const"]):
            errs.append(f"{path}: {x!r} != const {schema['const']!r}")
        if isinstance(x, str):
            if "minLength" in schema and len(x) < schema["minLength"]:
                errs.append(f"{path}: shorter than {schema['minLength']}")
            if "maxLength" in schema and len(x) > schema["maxLength"]:
                errs.append(f"{path}: longer than {schema['maxLength']}")
            if "pattern" in schema and not re.search(schema["pattern"], x):
                errs.append(f"{path}: {x[:60]!r} does not match {schema['pattern']}")
            if "format" in schema and not FORMAT_CHECKS[schema["format"]](x):
                errs.append(f"{path}: {x[:60]!r} is not a valid {schema['format']}")
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            if "minimum" in schema and x < schema["minimum"]:
                errs.append(f"{path}: {x} < {schema['minimum']}")
            if "maximum" in schema and x > schema["maximum"]:
                errs.append(f"{path}: {x} > {schema['maximum']}")
        if isinstance(x, dict):
            for r in schema.get("required", []):
                if r not in x:
                    errs.append(f"{path}: missing required '{r}'")
            props = schema.get("properties", {})
            for k, v in x.items():
                if k in props:
                    errs += self.validate(props[k], v, base_id, f"{path}.{k}")
                elif schema.get("additionalProperties") is False:
                    errs.append(f"{path}: unexpected property '{k}'")
        if isinstance(x, list):
            if "minItems" in schema and len(x) < schema["minItems"]:
                errs.append(f"{path}: fewer than {schema['minItems']} items")
            if "maxItems" in schema and len(x) > schema["maxItems"]:
                errs.append(f"{path}: more than {schema['maxItems']} items")
            if schema.get("uniqueItems"):
                seen = [json.dumps(i, sort_keys=True) for i in x]
                if len(seen) != len(set(seen)):
                    errs.append(f"{path}: items not unique")
            if "items" in schema:
                for i, v in enumerate(x):
                    errs += self.validate(schema["items"], v, base_id, f"{path}[{i}]")
            if "contains" in schema and not any(not self.validate(schema["contains"], v, base_id) for v in x):
                errs.append(f"{path}: no item matches 'contains'")
        for s in schema.get("allOf", []):
            errs += self.validate(s, x, base_id, path)
        if "anyOf" in schema and all(self.validate(s, x, base_id, path) for s in schema["anyOf"]):
            errs.append(f"{path}: matches none of anyOf")
        if "oneOf" in schema and sum(1 for s in schema["oneOf"] if not self.validate(s, x, base_id, path)) != 1:
            errs.append(f"{path}: must match exactly one of oneOf")
        if "not" in schema and not self.validate(schema["not"], x, base_id, path):
            errs.append(f"{path}: matches 'not'")
        if "if" in schema:
            branch = "then" if not self.validate(schema["if"], x, base_id, path) else "else"
            if branch in schema:
                errs += self.validate(schema[branch], x, base_id, path)
        return errs


# ============================================================================ reference mapping (spec aid)
PLATFORM = {"АИС ГЗ": "AIS_GZ", "ЭМ": "EM"}
COVERAGE = {"AIS_GZ": "WINNER_ROWS_ONLY_OBSERVED", "EM": "MIXED_WINNER_NONWINNER_ROWS_OBSERVED"}
BOOL = {"true": True, "false": False}
FLAG_ORDER = ["MISSING_INN", "INVALID_INN_FORMAT", "INVALID_INN_CHECKSUM", "MISSING_KPP", "INVALID_KPP_FORMAT",
              "MISSING_START_PRICE", "ZERO_START_PRICE", "MISSING_SUBJECT", "MISSING_PRODUCT_NAME", "MISSING_OKPD2",
              "INVALID_OKPD2", "DUPLICATE_SUPPLIER_RELATION"]
OKPD2_RE = re.compile(r"^[0-9]{2}(\.([0-9]|[0-9]{2}(\.([0-9]|[0-9]{2}(\.[0-9]{1,3})?))?))?$")
KPP_RE = re.compile(r"^[0-9]{4}[0-9A-Z]{2}[0-9]{3}$")
DECIMAL_RE = re.compile(r"^[0-9]{1,15}(\.[0-9]{1,4})?$")
SECTIONS = [("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39), ("F", 41, 43), ("G", 45, 47),
            ("H", 49, 53), ("I", 55, 56), ("J", 58, 63), ("K", 64, 66), ("L", 68, 68), ("M", 69, 75), ("N", 77, 82),
            ("O", 84, 84), ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96), ("T", 97, 98), ("U", 99, 99)]


class StructuralError(ValueError):
    """Row cannot be represented canonically (quarantine in ingestion)."""


def uid(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


def flags_sorted(fs) -> list:
    return sorted(set(fs), key=FLAG_ORDER.index)


def cmp_norm(s: str) -> str:
    """Comparison-only normalization used to decide procedure_name_variant (not the search normalization)."""
    s = (s or "").lower().replace("ё", "е")
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", s)).strip()


def inn_checksum_ok(inn: str) -> bool:
    d = [int(c) for c in inn]
    ctrl = lambda w: sum(a * b for a, b in zip(w, d)) % 11 % 10  # noqa: E731
    if len(d) == 10:
        return ctrl([2, 4, 10, 3, 5, 9, 4, 6, 8]) == d[9]
    return ctrl([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == d[10] and ctrl([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == d[11]


def inn_flags(inn: str | None) -> list:
    if inn is None:
        return ["MISSING_INN"]
    if not re.fullmatch(r"[0-9]{10}|[0-9]{12}", inn):
        return ["INVALID_INN_FORMAT"]
    return [] if inn_checksum_ok(inn) else ["INVALID_INN_CHECKSUM"]


def kpp_value_flags(kpp_raw: str):
    k = kpp_raw.strip()
    if not k:
        return None, ["MISSING_KPP"]
    return k, ([] if KPP_RE.fullmatch(k) else ["INVALID_KPP_FORMAT"])


def okpd2_section(cls: str):
    n = int(cls)
    for letter, lo, hi in SECTIONS:
        if lo <= n <= hi:
            return letter
    return None


def okpd2_fields(raw: str):
    code = raw.strip()
    empty = {k: None for k in ("okpd2_code", "okpd2_depth", "okpd2_section", "okpd2_class", "okpd2_subclass",
                               "okpd2_group", "okpd2_subgroup", "okpd2_kind")}
    if not code:
        return empty, ["MISSING_OKPD2"]
    if not OKPD2_RE.fullmatch(code) or okpd2_section(code[:2]) is None:
        return empty, ["INVALID_OKPD2"]
    segs = code.split(".")
    group = f"{segs[0]}.{segs[1]}" if len(segs) >= 2 and len(segs[1]) == 2 else None
    return {
        "okpd2_code": code, "okpd2_depth": len(segs), "okpd2_section": okpd2_section(segs[0]), "okpd2_class": segs[0],
        "okpd2_subclass": f"{segs[0]}.{segs[1][0]}" if len(segs) >= 2 else None,
        "okpd2_group": group,
        "okpd2_subgroup": f"{group}.{segs[2][0]}" if len(segs) >= 3 else None,
        "okpd2_kind": f"{group}.{segs[2]}" if len(segs) >= 3 and len(segs[2]) == 2 else None,
    }, []


def map_notice(row: dict, row_number: int, lots_with_history: set | None) -> dict:
    platform_raw = row["is_eshop_or_aisgz"].strip()
    if platform_raw not in PLATFORM:
        raise StructuralError(f"unknown platform {platform_raw!r}")
    if row["is_smp"].strip() not in BOOL:
        raise StructuralError(f"is_smp not boolean: {row['is_smp']!r}")
    flags = []
    lot_id = row["lot_id"].strip()
    subject = row["subject"].strip() or None
    if subject is None:
        flags.append("MISSING_SUBJECT")
    pn = row["procedure_name"].strip()
    variant = pn if pn and cmp_norm(pn) != cmp_norm(subject or "") else None
    price = row["start_price"].strip() or None
    if price is None:
        flags.append("MISSING_START_PRICE")
    elif not DECIMAL_RE.fullmatch(price):
        raise StructuralError(f"start_price not a non-negative decimal: {price!r}")
    elif re.fullmatch(r"0+(\.0+)?", price):
        flags.append("ZERO_START_PRICE")
    cinn = row["customer_inn"].strip() or None
    flags += inn_flags(cinn)
    ckpp, kf = kpp_value_flags(row["customer_kpp"])
    flags += kf
    rec = {
        "id": uid(f"lot:{lot_id}"), "lot_id": lot_id, "procedure_id": row["procedure_id"].strip(),
        "publish_date": row["publish_date"].strip(), "platform": PLATFORM[platform_raw], "subject": subject,
        "procedure_name_variant": variant, "start_price": price, "reqnum": row["reqnum"].strip() or None,
        "is_smp": BOOL[row["is_smp"].strip()], "customer_inn": cinn, "customer_kpp": ckpp,
        "data_quality_flags": flags_sorted(flags), "source_ref": {"dataset": "notices_24_25", "row_number": row_number},
    }
    if lots_with_history is not None:
        rec["has_supplier_history"] = lot_id in lots_with_history
    return rec


def map_items(rows: list) -> list:
    """rows: [(row_number, row)] in source-file order. line_no = ordinal of the row within its lot."""
    line = Counter()
    out = []
    for row_number, row in rows:
        lot_id = row["lot_id"].strip()
        line[lot_id] += 1
        name_raw, code_raw = row["product_name"], row["okpd2_code"]
        fields, flags = okpd2_fields(code_raw)
        if not name_raw.strip():
            flags = ["MISSING_PRODUCT_NAME"] + flags
        out.append({
            "id": uid(f"item:{lot_id}:{line[lot_id]}"), "lot_id": lot_id, "line_no": line[lot_id],
            "content_hash": hashlib.sha256(f"{lot_id}\x1f{name_raw}\x1f{code_raw}".encode("utf-8")).hexdigest(),
            "product_name_raw": name_raw, "product_name_normalized": None, "okpd2_code_raw": code_raw, **fields,
            "data_quality_flags": flags_sorted(flags), "source_ref": {"dataset": "items_24_25", "row_number": row_number},
        })
    return out


def map_history(rows: list, lots: dict) -> list:
    """rows: [(row_number, row)] in file order; lots: lot_id -> canonical lot. Dedup on (lot_id, inn)."""
    groups = defaultdict(list)
    for row_number, row in rows:
        lot_id, inn = row["lot_id"].strip(), row["supplier_inn"].strip()
        if lot_id not in lots:
            raise StructuralError(f"supplier row {row_number}: unknown lot {lot_id}")
        if not inn:
            raise StructuralError(f"supplier row {row_number}: empty INN")
        if row["is_winner"].strip() not in BOOL:
            raise StructuralError(f"supplier row {row_number}: is_winner not boolean")
        groups[(lot_id, inn)].append((row_number, row))
    out = []
    for (lot_id, inn), g in groups.items():
        kpp_raw = next((r["supplier_kpp"] for _, r in g if r["supplier_kpp"].strip()), "")
        kpp, kf = kpp_value_flags(kpp_raw)
        flags = [f for f in inn_flags(inn) if f != "MISSING_INN"] + kf
        if len(g) > 1:
            flags.append("DUPLICATE_SUPPLIER_RELATION")
        lot = lots[lot_id]
        out.append({
            "id": uid(f"history:{lot_id}:{inn}"), "lot_id": lot_id, "supplier_id": uid(f"supplier:inn:{inn}"),
            "supplier_inn": inn, "supplier_kpp": kpp, "is_winner": any(BOOL[r["is_winner"].strip()] for _, r in g),
            "platform": lot["platform"], "publish_date": lot["publish_date"], "coverage_semantics": COVERAGE[lot["platform"]],
            "data_quality_flags": flags_sorted(flags),
            "source_refs": [{"dataset": "suppliers_24_25", "row_number": n} for n, _ in g],
        })
    return out


def map_suppliers(histories: list) -> list:
    first = {}
    for h in histories:
        inn = h["supplier_inn"]
        first[inn] = min(first.get(inn, h["publish_date"]), h["publish_date"])
    out = []
    for inn in sorted(first):
        fl = inn_flags(inn)
        et = "legal_entity" if len(inn) == 10 else "individual_entrepreneur"
        if "INVALID_INN_FORMAT" in fl:
            et = "unknown"
        out.append({
            "supplier_id": uid(f"supplier:inn:{inn}"), "inn": inn, "entity_type": et,
            "inn_region_code": None if et == "unknown" else inn[:2], "origin": "ORGANIZER_DATA",
            "first_seen_publish_date": first[inn], "data_quality_flags": flags_sorted(fl),
        })
    return out


def map_all(notices, items, suppliers) -> dict:
    """notices/items/suppliers: [(row_number, row_dict)] in file order."""
    lot_hist = {r["lot_id"].strip() for _, r in suppliers}
    lots = {}
    for n, r in notices:
        rec = map_notice(r, n, lot_hist)
        lots[rec["lot_id"]] = rec
    hist = map_history(suppliers, lots)
    return {"procurement_lot": list(lots.values()), "procurement_item": map_items(items),
            "supplier_history": hist, "supplier": map_suppliers(hist)}


def key_of(entity: str, rec: dict) -> str:
    return {
        "procurement_lot": lambda r: r["lot_id"], "procurement_item": lambda r: f"{r['lot_id']}:{r['line_no']}",
        "supplier_history": lambda r: f"{r['lot_id']}:{r['supplier_inn']}", "supplier": lambda r: r["inn"],
    }[entity](rec)


# ============================================================================ raw-data mode
def read_raw(raw: Path, n_lots: int):
    def rows(name):
        f = open(raw / name, encoding="utf-8-sig", newline="")
        r = csv.reader(f, delimiter=";", quotechar='"')
        header = next(r)
        for i, row in enumerate(r, 1):
            if len(row) == len(header):
                yield i, dict(zip(header, row))
        f.close()
    notices = []
    for i, row in rows(SOURCE_FILES["notices_24_25"]):
        notices.append((i, row))
        if len(notices) >= n_lots:
            break
    keep = {r["lot_id"].strip() for _, r in notices}
    items = [(i, r) for i, r in rows(SOURCE_FILES["items_24_25"]) if r["lot_id"].strip() in keep]
    sups = [(i, r) for i, r in rows(SOURCE_FILES["suppliers_24_25"]) if r["lot_id"].strip() in keep]
    return notices, items, sups


# ============================================================================ main
def main() -> int:
    ap = argparse.ArgumentParser(description="Validate canonical contracts v0.2.0")
    ap.add_argument("--raw", type=Path, help="organizer CSV directory (optional real-row check)")
    ap.add_argument("--raw-lots", type=int, default=2000)
    args = ap.parse_args()
    failures = []

    def fail(msg):
        failures.append(msg)
        print("FAIL", msg)

    # 1. schemas
    schemas = {}
    for p in sorted(CONTRACTS.glob("*.schema.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        for cond, msg in ((s.get("$schema") == DRAFT, "$schema is not Draft 2020-12"), (s.get("$id") == p.name, "$id != file name"),
                          (s.get("version") == CONTRACT_VERSION, f"version != {CONTRACT_VERSION}")):
            if not cond:
                fail(f"{p.name}: {msg}")
        for e in meta_check(s):
            fail(f"{p.name}: {e}")
        schemas[p.name] = s
    for ent, fn in ENTITY_SCHEMAS.items():
        if fn not in schemas:
            fail(f"missing contract {fn}")
    V = Validator(schemas)
    print(f"Contracts: {len(schemas)} schema files checked (version {CONTRACT_VERSION})")

    # 2. column coverage against P1-001A evidence
    mapping = json.loads((CONTRACTS / "source_mapping.json").read_text(encoding="utf-8"))
    profile = json.loads((ROOT / "reports" / "dataset_profile.json").read_text(encoding="utf-8"))
    prof_key = {"notices_24_25": "notices", "suppliers_24_25": "suppliers", "items_24_25": "items"}
    n_cols = 0
    for ds, pk in prof_key.items():
        cols = profile["files"][pk]["columns"]
        spec = mapping["datasets"][ds]["columns"]
        for c in cols:
            n_cols += 1
            st = spec.get(c, {}).get("status")
            if st == "MAPPED" and spec[c].get("targets"):
                continue
            if st == "NOT_MAPPED" and spec[c].get("reason"):
                continue
            fail(f"column {ds}.{c} is neither MAPPED with targets nor NOT_MAPPED with reason")
        for c in spec:
            if c not in cols:
                fail(f"mapping lists {ds}.{c} which is not a source column")
    print(f"Source columns covered: {n_cols} (from reports/dataset_profile.json)")

    # 3. map fixtures + validate
    src = json.loads((CONTRACTS / "fixtures" / "source_rows.json").read_text(encoding="utf-8"))
    as_rows = lambda ds: [(r["row_number"], {k: v for k, v in r.items() if k != "row_number"}) for r in src[ds]]  # noqa: E731
    mapped = map_all(as_rows("notices_24_25"), as_rows("items_24_25"), as_rows("suppliers_24_25"))
    mapped2 = map_all(as_rows("notices_24_25"), as_rows("items_24_25"), as_rows("suppliers_24_25"))
    if json.dumps(mapped, sort_keys=True) != json.dumps(mapped2, sort_keys=True):
        fail("reference mapping is not deterministic")
    records = {}
    flag_counts = Counter()
    for ent, recs in mapped.items():
        for r in recs:
            records[f"{ent}:{key_of(ent, r)}"] = r
            flag_counts.update(r["data_quality_flags"])
            for e in V.validate(schemas[ENTITY_SCHEMAS[ent]], r, ENTITY_SCHEMAS[ent]):
                fail(f"{ent}:{key_of(ent, r)}: {e}")
    enr = json.loads((CONTRACTS / "fixtures" / "enrichment_records.json").read_text(encoding="utf-8"))
    for ent in ("supplier_profile", "supplier_evidence"):
        for name, r in enr[ent].items():
            records[f"{ent}:{name}"] = r
            for e in V.validate(schemas[ENTITY_SCHEMAS[ent]], r, ENTITY_SCHEMAS[ent]):
                fail(f"{ent}:{name}: {e}")
    counts = {ent: len(v) for ent, v in mapped.items()}
    counts.update({ent: len(enr[ent]) for ent in ("supplier_profile", "supplier_evidence")})
    print(f"Valid fixture records: {counts}")
    print(f"Quality flags exercised: {dict(sorted(flag_counts.items()))}")
    missing_flags = set(FLAG_ORDER) - set(flag_counts)
    if missing_flags:
        fail(f"quality flags never exercised by fixtures: {sorted(missing_flags)}")

    # 4. negative cases
    neg = json.loads((CONTRACTS / "fixtures" / "invalid_records.json").read_text(encoding="utf-8"))["cases"]
    rejected = 0
    for case in neg:
        ent = case["base"].split(":", 1)[0]
        if case["base"] not in records:
            fail(f"negative case '{case['name']}': unknown base {case['base']}")
            continue
        rec = copy.deepcopy(records[case["base"]])
        rec.update(case.get("patch", {}))
        for k in case.get("remove", []):
            rec.pop(k, None)
        errs = V.validate(schemas[ENTITY_SCHEMAS[ent]], rec, ENTITY_SCHEMAS[ent])
        if errs:
            rejected += 1
        else:
            fail(f"negative case accepted: {case['name']}")
    print(f"Negative cases rejected: {rejected}/{len(neg)}")

    # 6. optional real rows
    if args.raw:
        if not all((args.raw / f).is_file() for f in SOURCE_FILES.values()):
            fail(f"--raw {args.raw}: organizer CSV files not found")
        else:
            n, it, sp = read_raw(args.raw, args.raw_lots)
            try:
                real = map_all(n, it, sp)
            except StructuralError as e:
                fail(f"raw structural error: {e}")
                real = {}
            bad = Counter()
            rf = Counter()
            for ent, recs in real.items():
                for r in recs:
                    rf.update(r["data_quality_flags"])
                    if V.validate(schemas[ENTITY_SCHEMAS[ent]], r, ENTITY_SCHEMAS[ent]):
                        bad[ent] += 1
            print(f"Raw rows mapped: lots={len(n)} items={len(it)} supplier_rows={len(sp)} -> "
                  f"{ {k: len(v) for k, v in real.items()} }; invalid={dict(bad)}; flags={dict(sorted(rf.items()))}")
            if bad:
                fail(f"real records failed validation: {dict(bad)}")

    print("RESULT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
