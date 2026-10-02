"""OKPD2 resolver benchmark: generate labelled cases, tune decision thresholds on dev, report on test.

  python -m app.search.category_benchmark generate   # -> benchmark/okpd2_resolver/cases.json
  python -m app.search.category_benchmark run [--baseline-module v3.py --baseline-index v3.json]
                                                     # -> reports/okpd2_resolver_v4.json

Labels come from the official taxonomy itself (titles, their inflections, term postings), from
hand-curated cases, and from consistently coded procurement item names published before the
sealed HOLDOUT period (2025-H2; HOLDOUT lot ids are also excluded explicitly). Splits are by a
hash of the case id. Thresholds are tuned on dev only; test is reported, never tuned on.
The supplier-ranking benchmark and HOLDOUT are not touched.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import random
import re
import sys
import time
from pathlib import Path

from app.search import category_resolver as R
from app.search import morphology as M
from app.shared.config import repo_root

SEED = 20261002
HOLDOUT_START = "2025-07-01"
SIZES = {"exact_title": 120, "number_variant": 120, "case_variant": 120, "one_word_distinctive": 120,
         "one_word_ambiguous": 120, "procurement_description": 150, "unknown": 60}
BENCH_DIR = Path("benchmark") / "okpd2_resolver"


# ------------------------------------------------------------------------------------------------ generation
def _split(case_id: str) -> str:
    return "dev" if int(hashlib.sha256(case_id.encode()).hexdigest(), 16) % 2 == 0 else "test"


def _morph_equal(index: R.CategoryIndex, code: str) -> list[str]:
    """Other codes whose title has the same lemma sequence (a morphological variant cannot tell them apart)."""
    c = index.codes[code]
    if not c.lemma_sets:
        return []
    pool = set().union(*(index.postings.get(lemma, set()) for lemma in c.lemma_sets[0]))
    return [d for d in sorted(pool) if d != code and len(index.codes[d].lemma_sets) == len(c.lemma_sets)
            and all(a & b for a, b in zip(index.codes[d].lemma_sets, c.lemma_sets))]


def _leading_phrase(name: str) -> list[str]:
    """Words of the head noun phrase: everything before the first comma, bracket or function word."""
    out = []
    for raw in re.split(r"\s+", name.strip()):
        word = raw.strip("«»\"'()").lower().replace("ё", "е")
        if not word or not re.fullmatch("[а-я-]+", word) or M.is_function_word(word):
            break
        out.append(word)
        if re.search(r"[,;:()]$", raw):
            break
    return out


def _inflect_phrase(words: list[str], mode: str) -> tuple[str | None, bool]:
    """Inflect the head phrase: mode 'number' flips singular/plural, 'gent' / 'datv' change case.
    Returns (variant, adjective_changed). Adjectives take the head noun's gender in the singular."""
    morph = M._analyzer()
    parses = []
    for w in words:
        ps = [p for p in morph.parse(w) if p.tag.POS in {"NOUN", "ADJF", "PRTF"} and p.tag.case == "nomn"]
        parses.append(ps[0] if ps else None)
    head = next((p for p in parses if p is not None and p.tag.POS == "NOUN"), None)
    if head is None:
        return None, False
    number = "sing" if head.tag.number == "plur" else "plur"
    gender = head.normal_form and morph.parse(head.normal_form)[0].tag.gender
    out, adj_changed = [], False
    for w, p in zip(words, parses):
        if p is None:
            out.append(w)
            continue
        if mode == "number":
            target = {number, "nomn"} | ({gender} if number == "sing" and p.tag.POS != "NOUN" and gender else set())
        else:
            target = {mode}
        form = p.inflect(target)
        if form is None:
            return None, False
        adj_changed |= p.tag.POS != "NOUN" and form.word != w
        out.append(form.word)
    variant = " ".join(out)
    return (variant if variant != " ".join(words) else None), adj_changed


def _holdout_lots() -> list[str]:
    path = repo_root() / "benchmark" / "replay" / "queries.csv"
    with path.open(encoding="utf-8") as f:
        return sorted(row["lot_id"] for row in csv.DictReader(f) if row["split"] == "holdout")


def generate(conn, index: R.CategoryIndex) -> dict:
    rng = random.Random(SEED)
    named = sorted(c for c, v in index.codes.items() if v.name and v.lemma_sets)
    unique = [c for c in named if len(index.by_title[index.codes[c].normalized]) == 1 and not _morph_equal(index, c)]
    cases: list[dict] = []

    def add(kind: str, query: str, expected_state: str, expected_code: str | None, **extra) -> None:
        case_id = f"{kind}:{hashlib.sha256((kind + '|' + query).encode()).hexdigest()[:12]}"
        if any(c["id"] == case_id for c in cases):
            return
        cases.append({"id": case_id, "kind": kind, "query": query, "expected_state": expected_state,
                      "expected_code": expected_code, "split": _split(case_id), **extra})

    for code in rng.sample(unique, SIZES["exact_title"]):
        add("exact_title", index.codes[code].name, "RESOLVED", code)

    for mode, kind in (("number", "number_variant"), ("gent", "case_variant"), ("datv", "case_variant")):
        target = SIZES[kind] if mode == "number" else SIZES[kind] // 2
        made = 0
        for code in rng.sample(unique, len(unique)):
            words = _leading_phrase(index.codes[code].name)
            if not words or len(words) != len(index.codes[code].lemma_sets):
                continue                  # whole title must be the head phrase, so the variant names this code only
            variant, adj = _inflect_phrase(words, mode)
            if variant:
                add(kind, variant, "RESOLVED", code, inflection=mode, adjective_inflected=adj, source_title=index.codes[code].name)
                made += 1
                if made == target:
                    break

    titles_one_word = {lemma for c in named if len(index.codes[c].lemma_sets) == 1 for lemma in index.codes[c].lemma_sets[0]}
    distinctive, ambiguous = [], []
    for lemma in sorted(index.postings):
        if len(lemma) < 5 or not re.fullmatch("[а-я]+", lemma) or lemma in titles_one_word:
            continue
        codes = sorted(index.postings[lemma])
        lines: list[str] = []
        for c in sorted(codes, key=lambda x: (-index.codes[x].depth, x)):
            if not any(index.related(c, o) for o in lines):
                lines.append(c)
        pos = M._analyzer().parse(lemma)[0].tag.POS
        if len(lines) == 1 and len(codes) <= 4 and pos in {"NOUN", "ADJF"}:
            distinctive.append((lemma, lines[0]))
        elif len(lines) >= 4 and pos == "NOUN":
            ambiguous.append((lemma, codes))
    for lemma, code in rng.sample(distinctive, min(SIZES["one_word_distinctive"], len(distinctive))):
        surface = next((t for t, ls in zip(index.rows[code]["tokens"], index.codes[code].lemma_sets) if lemma in ls), lemma)
        query = lemma if surface != lemma else (_inflect_phrase([lemma], "number")[0] or lemma)
        add("one_word_distinctive", query, "RESOLVED", code, title_form=surface)
    for lemma, codes in rng.sample(ambiguous, min(SIZES["one_word_ambiguous"], len(ambiguous))):
        query = lemma if rng.random() < 0.5 else (_inflect_phrase([lemma], "number")[0] or lemma)
        add("one_word_ambiguous", query, "CATEGORY_AMBIGUOUS", None, matching_codes=len(codes))

    conn.execute("SET TRANSACTION READ ONLY")
    rows = conn.execute("""
        WITH names AS (
          SELECT product_name_normalized AS n, okpd2_code AS c, count(*)::int AS k, min(product_name_raw) AS raw
          FROM procurement_item
          WHERE publish_date < %s AND product_name_normalized IS NOT NULL AND okpd2_code IS NOT NULL
            AND lot_id <> ALL(%s)
          GROUP BY 1, 2
        ), totals AS (SELECT n, sum(k) AS t FROM names GROUP BY n)
        SELECT names.n, c, k, raw FROM names JOIN totals USING (n)
        WHERE k >= 3 AND k >= 0.95 * t AND length(n) >= 15
        ORDER BY md5(names.n || %s), names.n""", (HOLDOUT_START, _holdout_lots(), str(SEED))).fetchall()
    made = 0
    for _n, code, k, raw in rows:
        if code in index.codes and index.codes[code].name and len(M.content_tokens(raw)) >= 2:
            add("procurement_description", raw, "RESOLVED", code, observed_items=k)
            made += 1
            if made == SIZES["procurement_description"]:
                break

    syllables = ["бра", "квы", "зош", "мту", "фле", "жик", "пров", "ыгд", "щур", "клем", "дво", "ньк", "хар", "тсу"]
    made = 0
    while made < SIZES["unknown"]:
        words = ["".join(rng.choice(syllables) for _ in range(rng.randint(2, 4))) for _ in range(rng.randint(1, 3))]
        if all(not set(M.lemmas(w)) & index.postings.keys() for w in words):
            add("unknown", " ".join(words).capitalize(), "CATEGORY_UNCERTAIN", None)
            made += 1

    curated = json.loads((repo_root() / BENCH_DIR / "curated_cases.json").read_text(encoding="utf-8"))
    for case in curated["cases"]:
        add(case["kind"], case["query"], case["expected_state"], case.get("expected_code"),
            curated=True, note=case.get("note"))
    return {"name": "okpd2-resolver-benchmark", "version": "1.0.0", "seed": SEED,
            "generator": "backend/app/search/category_benchmark.py",
            "holdout_excluded": {"publish_date_before": HOLDOUT_START, "holdout_lots_excluded": True},
            "counts": {kind: sum(c["kind"] == kind for c in cases) for kind in sorted({c["kind"] for c in cases})},
            "splits": {s: sum(c["split"] == s for c in cases) for s in ("dev", "test")},
            "cases": cases}


# ------------------------------------------------------------------------------------------------ evaluation
def _lexemes(conn, text: str) -> list[str]:
    from app.search.text_query import LEX
    from app.shared import normalize as N
    name = N.normalize_product_name(text).normalized or text.lower()
    return list(conn.execute(f"SELECT {LEX.format(col='%s::text')}", (name,)).fetchone()[0])


def metrics(cases: list[dict], outcomes: list[dict]) -> dict:
    by_kind: dict[str, list[tuple[dict, dict]]] = {}
    for c, o in zip(cases, outcomes):
        by_kind.setdefault(c["kind"], []).append((c, o))

    def rate(pairs, ok) -> dict:
        n = len(pairs)
        hits = sum(1 for c, o in pairs if ok(c, o))
        return {"n": n, "value": round(hits / n, 4) if n else None}

    resolved_ok = lambda c, o: o["state"] == "RESOLVED" and o["code"] == c["expected_code"]   # noqa: E731
    with_code = [(c, o) for c, o in zip(cases, outcomes) if c["expected_code"]]
    morph = by_kind.get("number_variant", []) + by_kind.get("case_variant", [])
    abstain = [(c, o) for c, o in zip(cases, outcomes) if c["expected_state"] != "RESOLVED"]
    wrong = lambda c, o: o["state"] == "RESOLVED" and (c["expected_code"] is None or o["code"] != c["expected_code"])  # noqa: E731
    resolved = [(c, o) for c, o in zip(cases, outcomes) if o["state"] == "RESOLVED"]
    return {
        "exact_title_accuracy": rate(by_kind.get("exact_title", []), resolved_ok),
        "morphological_variant_accuracy": rate(morph, resolved_ok),
        "morph_number_variant_accuracy": rate(by_kind.get("number_variant", []), resolved_ok),
        "morph_case_variant_accuracy": rate(by_kind.get("case_variant", []), resolved_ok),
        "morph_adjective_inflection_accuracy": rate([p for p in morph if p[0].get("adjective_inflected")], resolved_ok),
        "one_word_distinctive_accuracy": rate(by_kind.get("one_word_distinctive", []), resolved_ok),
        "procurement_description_resolved_accuracy": rate(by_kind.get("procurement_description", []), resolved_ok),
        "procurement_description_wrong_resolution": rate(by_kind.get("procurement_description", []), wrong),
        "top1_accuracy": rate(with_code, lambda c, o: o["top"][:1] == [c["expected_code"]]),
        "top3_accuracy": rate(with_code, lambda c, o: c["expected_code"] in o["top"][:3]),
        "ambiguity_detection_accuracy": rate([p for p in abstain if p[0]["expected_state"] == "CATEGORY_AMBIGUOUS"],
                                             lambda c, o: o["state"] == "CATEGORY_AMBIGUOUS"),
        "false_ambiguity_rate": rate(with_code, lambda c, o: o["state"] == "CATEGORY_AMBIGUOUS"),
        "correct_abstention_rate": rate(abstain, lambda c, o: o["state"] != "RESOLVED"),
        "unknown_uncertain_rate": rate(by_kind.get("unknown", []), lambda c, o: o["state"] == "CATEGORY_UNCERTAIN"),
        "wrong_high_confidence_rate": rate(list(zip(cases, outcomes)), wrong),
        "resolved_precision": rate(resolved, lambda c, o: not wrong(c, o)),
    }


def _utility(cases: list[dict], outcomes: list[dict]) -> float:
    """Tuning objective: correct decisions minus twice the wrong confident resolutions."""
    total = 0.0
    for c, o in zip(cases, outcomes):
        if o["state"] == "RESOLVED":
            total += 1.0 if c["expected_code"] and o["code"] == c["expected_code"] else -2.0
        elif o["state"] == c["expected_state"]:
            total += 1.0
    return total


def _outcome(index, ev, accept, margin) -> dict:
    r = R.decide(index, ev, accept, margin)
    return {"state": r.state, "code": r.ranking_code, "top": [s.okpd2 for s in r.suggestions[:3]],
            "basis": r.suggestions[0].basis if r.suggestions else None}


def _fast(ev: R.Evidence, accept: float, margin: float) -> dict:
    """State and code only, for the threshold grid (the real decision rule, without suggestion lists)."""
    state, chosen, _ = R.decision(R.load_index(), ev, accept, margin)
    return {"state": state, "code": chosen.okpd2 if state == "RESOLVED" else None}


def _baseline(module_path: Path, index_path: Path, cases: list[dict], lexemes: list[list[str]]) -> list[dict]:
    spec = importlib.util.spec_from_file_location("baseline_resolver", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    index = module.CategoryIndex.from_data(json.loads(index_path.read_text(encoding="utf-8")))
    out = []
    for case, lex in zip(cases, lexemes):
        r = module.resolve(index, case["query"], lex, [])
        out.append({"state": r.state, "code": r.ranking_code, "top": [s.okpd2 for s in r.suggestions[:3]],
                    "basis": r.suggestions[0].basis if r.suggestions else None})
    return out


def run(conn, index: R.CategoryIndex, bench: dict, baseline: tuple[Path, Path] | None) -> dict:
    cases = bench["cases"]
    conn.execute("SET TRANSACTION READ ONLY")
    lexemes = [_lexemes(conn, c["query"]) for c in cases]
    t = time.perf_counter()
    evidence = [R.collect(index, c["query"], lex, []) for c, lex in zip(cases, lexemes)]
    latency_ms = (time.perf_counter() - t) * 1000 / len(cases)
    dev = [i for i, c in enumerate(cases) if c["split"] == "dev"]
    grid = []
    for a in range(30, 71):
        for m in range(0, 81):
            accept, margin = a / 100, m / 200
            outs = [_fast(evidence[i], accept, margin) for i in dev]
            grid.append((_utility([cases[i] for i in dev], outs), margin, accept))
    best_utility = max(g[0] for g in grid)
    # The optimum is a plateau: take its centre (median margin, then median acceptance at that margin)
    # rather than an edge, so a small shift in the data does not cross the decision boundary.
    optimal = sorted(g for g in grid if g[0] == best_utility)
    margins = sorted({g[1] for g in optimal})
    tuned_margin = margins[len(margins) // 2]
    accepts = sorted(g[2] for g in optimal if g[1] == tuned_margin)
    tuned_accept = accepts[len(accepts) // 2]
    final = [_outcome(index, ev, R.ACCEPT, R.MARGIN) for ev in evidence]

    def by_split(outcomes):
        return {s: metrics([c for c in cases if c["split"] == s], [o for c, o in zip(cases, outcomes) if c["split"] == s])
                for s in ("dev", "test")} | {"all": metrics(cases, outcomes)}

    report = {"benchmark": {k: bench[k] for k in ("name", "version", "seed", "counts", "splits", "holdout_excluded")},
              "morphology": M.describe(),
              "tuning": {"split": "dev", "objective": "correct decisions - 2 x wrong confident resolutions",
                         "grid": {"accept": [0.30, 0.70, 0.01], "margin": [0.0, 0.40, 0.005]},
                         "optimal_plateau": {"margin": [margins[0], margins[-1]],
                                             "accept": [min(g[2] for g in optimal), max(g[2] for g in optimal)]},
                         "best_dev_utility": best_utility, "tuned_accept": tuned_accept, "tuned_margin": tuned_margin,
                         "configured_accept": R.ACCEPT, "configured_margin": R.MARGIN},
              "weights": {"exact": R.W_EXACT, "morph": R.W_MORPH, "lexical": R.W_LEX, "historical": R.W_HIST,
                          "semantic": R.W_SEM},
              "latency_ms_per_query": round(latency_ms, 1),
              "v4": by_split(final),
              "cases": [{**{k: c[k] for k in ("id", "kind", "query", "split", "expected_state", "expected_code")},
                         "v4": o} for c, o in zip(cases, final)]}
    if baseline:
        base = _baseline(*baseline, cases, lexemes)
        report["v3_baseline"] = by_split(base)
        for row, o in zip(report["cases"], base):
            row["v3"] = o
    return report


def main() -> None:
    import psycopg

    from app.shared.config import database_url

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["generate", "run"])
    parser.add_argument("--baseline-module", type=Path)
    parser.add_argument("--baseline-index", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    index = R.load_index()
    cases_path = repo_root() / BENCH_DIR / "cases.json"
    with psycopg.connect(database_url()) as conn:
        if args.command == "generate":
            bench = generate(conn, index)
            cases_path.write_text(json.dumps(bench, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(json.dumps({k: bench[k] for k in ("counts", "splits")}, ensure_ascii=False))
            return
        bench = json.loads(cases_path.read_text(encoding="utf-8"))
        baseline = (args.baseline_module, args.baseline_index) if args.baseline_module else None
        report = run(conn, index, bench, baseline)
    out = args.output or repo_root() / "reports" / "okpd2_resolver_v4.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"tuning": report["tuning"], "test": report["v4"]["test"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
