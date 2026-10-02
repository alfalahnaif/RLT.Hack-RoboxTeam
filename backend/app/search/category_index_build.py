"""Rebuild the read-only OKPD2 term snapshot from canonical procurement_item.

Usage: python -m app.search.category_index_build --names okpd2.json --output data/seed/okpd2_category_index.json
The input is a code/name JSON list; only codes actually present in procurement_item
are retained. No procurement table is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import psycopg

from app.shared.config import database_url

_LEXEME = re.compile(r"'([^']+)'(?=:\d)")


def _lexemes(vector: str) -> list[str]:
    return sorted(set(_LEXEME.findall(vector)))


def build(conn, names: dict[str, str]) -> dict:
    conn.execute("SET TRANSACTION READ ONLY")
    stats = conn.execute("""
        SELECT okpd2_code, count(*)::int, count(DISTINCT lot_id)::int
        FROM procurement_item WHERE okpd2_code IS NOT NULL
        GROUP BY okpd2_code ORDER BY okpd2_code""").fetchall()
    rows = {code: {"code": code, "name": names.get(code), "name_lexemes": [],
                   "items": items, "lots": lots, "phrases": []}
            for code, items, lots in stats}
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
    official = [(code, row["name"]) for code, row in rows.items() if row["name"]]
    for code, name in official:
        vector = conn.execute("SELECT to_tsvector('russian', %s)::text", (name,)).fetchone()[0]
        rows[code]["name_lexemes"] = _lexemes(vector)
    term_codes: Counter[str] = Counter()
    for row in rows.values():
        term_codes.update({term for phrase in row["phrases"] for term in phrase["lexemes"]})
    for row in rows.values():
        weighted = Counter()
        for phrase in row["phrases"]:
            weighted.update({term: phrase["items"] for term in phrase["lexemes"]})
        row["distinctive_terms"] = [term for term, _ in sorted(weighted.items(), key=lambda kv: (-kv[1], kv[0]))
                                    if term_codes[term] <= 3][:8]
    return {"schema_version": 1, "source_table": "procurement_item", "observed_codes": len(rows),
            "total_items_with_code": sum(row["items"] for row in rows.values()),
            "terminology_source": "https://github.com/prog815/okpd2/tree/71fe224628b3404056376249a6cd99bcc9dad44e (code/name snapshot 2025-12-05)",
            "codes": list(rows.values())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_bytes = args.names.read_bytes()
    raw = json.loads(source_bytes.decode("utf-8"))
    names = {row["c"].strip(): row["n"].strip() for row in raw if row.get("c") and row.get("n")}
    with psycopg.connect(database_url()) as conn:
        data = build(conn, names)
    data["terminology_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Indexed {data['observed_codes']} observed OKPD2 codes / {data['total_items_with_code']} items")


if __name__ == "__main__":
    main()
