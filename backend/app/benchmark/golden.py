"""P1-001F — frozen golden demo cases (qualitative demo/debugging only — never benchmark tuning or a holdout substitute).

Facts in the case cards are generated from PostgreSQL; the selection, roles and demo stories below are curated text.
Selection used only data characteristics, procurement clarity, demo value and historical-difficulty metadata — no system output.
History facts use the benchmark's strict visibility rule (publish_date < target date).
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from app.benchmark.temporal import METADATA_SQL, VISIBLE

GOLDEN_VERSION = "1.0.0"

SELECTION = [
    {"lot_id": "5718896", "role": "primary", "capabilities": ["generic title, specific item", "technical model identifier", "multiple observed suppliers"],
     "why": "Generic lot title hides a precise laptop model in the ТРУ line; 13 observed suppliers; very common category (large candidate pool).",
     "story": {"input": "Lot 5718896 — «Поставка компьютерного оборудования» (generic title)",
               "evidence": "ТРУ line «Ноутбук Acer Aspire 5 A515-57-50R7 15.6\"» (OKPD2 26.20.11.110) — model number + screen size",
               "expected_capability": "Retrieval and explanation driven by item-level evidence (model tokens, OKPD2) rather than the generic subject."}},
    {"lot_id": "5545252", "role": "primary", "capabilities": ["spec-rich product text", "brand/model identifier", "ranking difficulty among many suppliers"],
     "why": "Long, concrete specification (brand, model, dimensions, load, warranty) for an everyday object; 14 observed suppliers; "
            "the winner sits mid-pack by simple historical award counts — ranking is not trivial.",
     "story": {"input": "Lot 5545252 — office chairs for a St Petersburg school",
               "evidence": "ТРУ line «Кресло офисное Бюрократ CH-695NLT …» with seat height, width, load and warranty attributes (OKPD2 31.01.11.150)",
               "expected_capability": "Explain why suppliers are relevant using item text + OKPD2 + history, and show that simple award counts alone are not enough."}},
    {"lot_id": "5542696", "role": "primary", "capabilities": ["honest hard case", "explainable OKPD2/text evidence", "many observed suppliers"],
     "why": "Clear medical consumable; 15 observed suppliers; the eventual winner had only one prior same-code award — demonstrates the "
            "limits of history-only ranking and the need for transparent evidence.",
     "story": {"input": "Lot 5542696 — «Поставка перчаток смотровых (процедурных) нитриловых»",
               "evidence": "ТРУ line «Перчатки смотровые/процедурные нитриловые, неопудренные, нестерильные» (OKPD2 22.19.60.119)",
               "expected_capability": "Show the evidence behind each candidate honestly, including when the eventual winner has thin history."}},
    {"lot_id": "6022687", "role": "backup", "capabilities": ["generic title, specific items", "multi-item, multi-OKPD2", "technical model identifiers"],
     "why": "Generic title with two concrete items (HP LaserJet Pro 4103dw MFP, ASUS VivoBook 17X laptop) in two OKPD2 codes; latest date "
            "in the data (maximum visible history).",
     "story": None},
    {"lot_id": "5612123", "role": "backup", "capabilities": ["category/OKPD2 evidence when item text adds nothing", "multiple observed suppliers"],
     "why": "The project's original UC-01 example (interactive panel); the item text repeats the title, so the case shows OKPD2/category "
            "evidence rather than text detail.",
     "story": None},
]
NOT_SELECTED = {
    "5659204": "laptop case duplicating the 5718896 story (title already detailed)",
    "5875992": "multi-category mix (mouse + 75\" TV) — harder to narrate in 5 minutes",
    "5548828": "low-value single mouse lot — weaker demo story",
    "5510873": "already a replay-benchmark query (benchmark/replay/queries.csv) — must not be reused",
}

CARD_SQL = """
SELECT l.lot_id, l.publish_date, l.platform, l.subject, l.start_price, l.customer_inn IS NOT NULL,
       (SELECT count(*) FROM procurement_item i WHERE i.lot_id = l.lot_id),
       (SELECT count(DISTINCT i.okpd2_code) FROM procurement_item i WHERE i.lot_id = l.lot_id),
       (SELECT coalesce(array_agg(DISTINCT i.okpd2_code ORDER BY i.okpd2_code) FILTER (WHERE i.okpd2_code IS NOT NULL), '{}')
          FROM procurement_item i WHERE i.lot_id = l.lot_id),
       (SELECT array_agg(left(p.product_name_raw, 200) ORDER BY p.line_no) FROM
          (SELECT product_name_raw, line_no FROM procurement_item i WHERE i.lot_id = l.lot_id ORDER BY line_no LIMIT 3) p),
       (SELECT count(*) FROM supplier_history h WHERE h.lot_id = l.lot_id),
       (SELECT count(*) FROM supplier_history h WHERE h.lot_id = l.lot_id AND h.is_winner)
FROM procurement_lot l WHERE l.lot_id = %(lot)s
"""

# Descriptive difficulty (same statistic as P1-001A §9; NOT a Supplier Radar result): suppliers ranked by number of distinct earlier
# lots won that share a full OKPD2 code with the target; competition rank of the winner + tie span. Strictly earlier facts only.
AWARD_RANK_SQL = f"""
WITH t AS (SELECT lot_id, publish_date AS as_of FROM procurement_lot WHERE lot_id = %(lot)s),
codes AS (SELECT DISTINCT okpd2_code FROM procurement_item WHERE lot_id = %(lot)s AND okpd2_code IS NOT NULL),
aw AS (SELECT h.supplier_id, count(DISTINCT h.lot_id) AS n FROM supplier_history h, t
       WHERE h.is_winner AND {VISIBLE.format(as_of='t.as_of')}
         AND EXISTS (SELECT 1 FROM procurement_item i WHERE i.lot_id = h.lot_id AND i.okpd2_code IN (SELECT okpd2_code FROM codes))
       GROUP BY h.supplier_id),
w AS (SELECT h.supplier_id, coalesce(aw.n, 0) AS n FROM supplier_history h LEFT JOIN aw USING (supplier_id)
      WHERE h.lot_id = %(lot)s AND h.is_winner)
SELECT (SELECT count(*) FROM aw), w.n, 1 + (SELECT count(*) FROM aw WHERE aw.n > w.n),
       (SELECT count(*) FROM aw WHERE aw.n = w.n) - (CASE WHEN w.n > 0 THEN 1 ELSE 0 END)
FROM w ORDER BY w.n DESC
"""


def build_card(conn, lot_id: str) -> dict:
    r = conn.execute(CARD_SQL, {"lot": lot_id}).fetchone()
    if r is None:
        raise ValueError(f"golden lot {lot_id} not found")
    meta = conn.execute(METADATA_SQL, {"lots": [lot_id]}).fetchone()
    ranks = conn.execute(AWARD_RANK_SQL, {"lot": lot_id}).fetchall()
    return {
        "lot_id": r[0], "publish_date": r[1].isoformat(), "platform": r[2], "subject": r[3],
        "start_price": None if r[4] is None else format(r[4], "f"), "customer_identifier_available": r[5],
        "number_of_items": r[6], "number_of_distinct_okpd2": r[7], "okpd2_codes": list(r[8]),
        "representative_product_names": list(r[9] or []), "observed_supplier_relations": r[10], "winner_count": r[11],
        "temporal_history": {
            "rule": "facts with publish_date < target publish_date only",
            "winner_seen_before_anywhere": bool(meta and meta[1]), "winner_seen_same_okpd2": bool(meta and meta[2]),
            "winner_seen_same_okpd2_group": bool(meta and meta[3]), "winner_seen_same_customer": bool(meta and meta[4]),
        },
        "descriptive_difficulty": {
            "note": "Historical award-count statistic (P1-001A §9 definition). NOT a Supplier Radar recommendation result.",
            "prior_same_okpd2_winning_suppliers": ranks[0][0] if ranks else 0,
            "winner_prior_same_okpd2_awards": [x[1] for x in ranks],
            "winner_award_count_rank": [x[2] for x in ranks],
            "winner_award_count_rank_ties": [x[3] for x in ranks],
        },
    }


def build(conn) -> dict:
    cards = []
    for s in SELECTION:
        c = build_card(conn, s["lot_id"])
        c.update({"role": s["role"], "capabilities": s["capabilities"], "why_selected": s["why"]})
        if s["story"]:
            c["demo_story"] = s["story"]
        cards.append(c)
    return {
        "version": GOLDEN_VERSION,
        "purpose": "Golden cases are for qualitative demonstration and debugging only (live demo, screenshots, explanation examples, "
                   "final presentation). The quantitative evaluation source is benchmark/replay.",
        "primary": [c for c in cards if c["role"] == "primary"],
        "backup": [c for c in cards if c["role"] == "backup"],
        "selection_rules": [
            "Selected only on data characteristics, procurement clarity, demo value and historical-difficulty metadata.",
            "No Supplier Radar output was available or used (P1-002 not implemented); no ranking result is claimed.",
            "Together the cases cover: generic title vs specific item, technical identifiers, many observed suppliers, "
            "non-trivial ranking difficulty, OKPD2/text evidence, 5-minute clarity.",
            "History facts use only publish_date < target date.",
            "No golden lot may appear in benchmark/replay/queries.csv.",
        ],
        "considered_not_selected": NOT_SELECTED,
        "prohibited_uses": ["benchmark tuning", "holdout replacement", "reporting quantitative quality", "claiming a #1 supplier before P1-002 evaluates it"],
        "privacy": "No supplier INNs or names are stored; customer identity is reported only as availability.",
    }


def write(doc: dict, out_dir: Path) -> bytes:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False) + "\n").encode("utf-8")
    (out_dir / "golden_cases.json").write_bytes(data)
    return data


def validate(conn, out_dir: Path, queries_csv: Path) -> dict:
    doc = json.loads((out_dir / "golden_cases.json").read_text(encoding="utf-8"))
    cases = doc["primary"] + doc["backup"]
    lots = [c["lot_id"] for c in cases]
    with open(queries_csv, encoding="utf-8", newline="") as f:
        bench = {r["lot_id"] for r in csv.DictReader(f)}
    fresh = {c["lot_id"]: build_card(conn, c["lot_id"]) for c in cases}
    keys = [k for k in fresh[lots[0]]]
    checks = {
        "3 primary + 2 backup": len(doc["primary"]) == 3 and len(doc["backup"]) == 2,
        "no duplicate lots": len(set(lots)) == len(lots),
        "every lot exists": all(fresh[l]["lot_id"] == l for l in lots),
        "every lot has items": all(fresh[l]["number_of_items"] >= 1 for l in lots),
        "every lot has supplier history": all(fresh[l]["observed_supplier_relations"] >= 1 for l in lots),
        "every primary has a demo story": all("demo_story" in c for c in doc["primary"]),
        "stored facts match PostgreSQL": all({k: c[k] for k in keys} == fresh[c["lot_id"]] for c in cases),
        "no overlap with benchmark/replay/queries.csv": not (set(lots) & bench),
        "no supplier identifiers stored": not any(k in json.dumps(doc) for k in ("supplier_inn", "supplier_id")),
    }
    return {"checks": checks, "passed": all(checks.values()),
            "sha256": hashlib.sha256((out_dir / "golden_cases.json").read_bytes()).hexdigest()}
