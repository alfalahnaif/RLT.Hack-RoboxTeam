"""Rebuild the read-only OKPD2 index: full official taxonomy + observed procurement terms.

Usage: python -m app.search.category_index_build --names okpd2.json [--meta okpd2_meta.json]
                                                   --output data/seed/okpd2_category_index.json
The input is the official code/name/parent JSON list. Every official code is indexed
with its precomputed tokens, lemmas, phrase lemmas, parent chain and depth, so the
resolver never lemmatizes the taxonomy at query time. Observed procurement statistics
come from canonical procurement_item in a read-only transaction; no table is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from app.search import morphology as M

_LEXEME = re.compile(r"'([^']+)'(?=:\d)")


def _lexemes(vector: str) -> list[str]:
    return sorted(set(_LEXEME.findall(vector)))


def _parents(raw: list[dict]) -> dict[str, str | None]:
    """Parent per code. The source flattens subcategories (10.51.11.121) under their type
    (10.51.11); OKPD2 places them under the category ending in 0 (10.51.11.120)."""
    codes = {row["c"].strip() for row in raw}
    out: dict[str, str | None] = {}
    for row in raw:
        code, parent = row["c"].strip(), (row.get("p") or "").strip()
        if len(code) == 12 and code[-1] != "0" and code[:-1] + "0" in codes:
            parent = code[:-1] + "0"
        out[code] = parent if parent in codes else None
    return out


def taxonomy_rows(raw: list[dict]) -> dict[str, dict]:
    parents = _parents(raw)

    def chain(code: str) -> list[str]:
        out, p = [], parents[code]
        while p:
            out.append(p)
            p = parents[p]
        return out[::-1]                  # root ... direct parent

    rows = {}
    for row in raw:
        code, name = row["c"].strip(), row["n"].strip()
        tokens = M.content_tokens(name)
        lemmas = [list(M.lemmas(t)) for t in tokens]
        ancestors = chain(code)
        rows[code] = {"code": code, "name": name, "normalized_name": M.normalize(name), "tokens": tokens,
                      "lemmas": lemmas, "phrase_lemmas": " ".join(ls[0] for ls in lemmas),
                      "parent": parents[code], "depth": len(ancestors) + 1}
    return rows


def observed_rows(conn) -> dict[str, dict]:
    conn.execute("SET TRANSACTION READ ONLY")
    stats = conn.execute("""
        SELECT okpd2_code, count(*)::int, count(DISTINCT lot_id)::int
        FROM procurement_item WHERE okpd2_code IS NOT NULL
        GROUP BY okpd2_code ORDER BY okpd2_code""").fetchall()
    rows = {code: {"items": items, "lots": lots, "phrases": []} for code, items, lots in stats}
    # Counts and tie-breaks are deterministic. Five frequent phrases per observed
    # code keep the checked-in index small while retaining real dataset examples.
    phrases = conn.execute("""
        WITH counts AS (
          SELECT okpd2_code, product_name_normalized, count(*)::int AS items
          FROM procurement_item
          WHERE okpd2_code IS NOT NULL AND product_name_normalized IS NOT NULL
          GROUP BY okpd2_code, product_name_normalized
        ), ranked AS (
          SELECT *, row_number() OVER (
            PARTITION BY okpd2_code ORDER BY items DESC, product_name_normalized
          ) AS rn FROM counts
        )
        SELECT okpd2_code, product_name_normalized, items,
               to_tsvector('russian', product_name_normalized)::text
        FROM ranked WHERE rn <= 5 ORDER BY okpd2_code, rn""").fetchall()
    for code, name, items, vector in phrases:
        rows[code]["phrases"].append({"text": name, "items": items, "lexemes": _lexemes(vector)})
    term_codes: Counter[str] = Counter()
    for row in rows.values():
        term_codes.update({term for phrase in row["phrases"] for term in phrase["lexemes"]})
    for row in rows.values():
        weighted = Counter()
        for phrase in row["phrases"]:
            weighted.update({term: phrase["items"] for term in phrase["lexemes"]})
        row["distinctive_terms"] = [term for term, _ in sorted(weighted.items(), key=lambda kv: (-kv[1], kv[0]))
                                    if term_codes[term] <= 3][:8]
    return rows


def build(conn, raw: list[dict]) -> dict:
    official = taxonomy_rows(raw)
    observed = observed_rows(conn)
    codes = []
    for code in sorted(set(official) | set(observed)):
        row = official.get(code) or {"code": code, "name": None, "normalized_name": None, "tokens": [], "lemmas": [],
                                     "phrase_lemmas": "", "parent": None, "depth": None}
        row.update(observed.get(code) or {"items": 0, "lots": 0, "phrases": [], "distinctive_terms": []})
        codes.append(row)
    return {"schema_version": 2, "source_table": "procurement_item",
            "official_codes": len(official), "observed_codes": len(observed),
            "observed_codes_without_official_name": len(set(observed) - set(official)),
            "total_items_with_code": sum(row["items"] for row in observed.values()),
            "morphology": M.describe(), "codes": codes}


def main() -> None:
    import psycopg

    from app.shared.config import database_url

    parser = argparse.ArgumentParser()
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--meta", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_bytes = args.names.read_bytes()
    raw = [row for row in json.loads(source_bytes.decode("utf-8")) if row.get("c") and row.get("n")]
    with psycopg.connect(database_url()) as conn:
        data = build(conn, raw)
    meta = json.loads(args.meta.read_text(encoding="utf-8")) if args.meta else {}
    data["terminology_source"] = {
        "classifier": meta.get("classifier_name", "ОКПД2 (ОК 034-2014)"),
        "official_source_url": meta.get("source_url"), "official_source_date": meta.get("source_date"),
        "mirror": "https://github.com/prog815/okpd2/tree/71fe224628b3404056376249a6cd99bcc9dad44e",
        "records": len(raw), "sha256": hashlib.sha256(source_bytes).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Indexed {data['official_codes']} official / {data['observed_codes']} observed OKPD2 codes "
          f"/ {data['total_items_with_code']} items")


if __name__ == "__main__":
    main()
