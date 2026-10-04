"""OKPD2 category resolver (V4): official taxonomy first, morphology-aware; independent of frozen lot ranking.

The index (category_index_build) holds every official OKPD2 code with precomputed tokens,
lemmas and hierarchy, plus observed procurement phrases for codes seen in the canonical
snapshot. Official names are terminology evidence; historical phrase counts are evidence,
not a learned classifier; semantic neighbors are supporting evidence only.

Resolution order:
  1. exact normalized official title          -> OFFICIAL_EXACT_TITLE  (resolves when all matches lie on one line)
  2. morphology-aware official title (lemmas) -> OFFICIAL_MORPH_TITLE  (same rule; used only without stage 1)
  3. IDF-weighted lemma coverage              -> OFFICIAL_TERMS        (ACCEPT / MARGIN rule below)
  4. dominant historical phrase -> HISTORICAL_DOMINANT, when official evidence is weak, or when it is
     ambiguous and exactly one dominant historical code lies on an official contender's line
  5. fuzzy / semantic neighbors               -> suggestions only, never RESOLVED

category_score = exact_phrase + morph_phrase + weighted_token (coverage x title focus x
term specificity) + historical_support + semantic_support, all in [0, 1]. Official
lexical evidence carries 0.87 of the scale and semantic support 0.03, so similarity
alone cannot override an official match. Automatic resolution needs
top1 >= ACCEPT and top1 - best_rival >= MARGIN; candidates on the leader's
ancestor line are not rivals (an ancestor is the same answer, only broader), while the
leader's own sub-categories are. Strong but close candidates -> CATEGORY_AMBIGUOUS.
Scores describe evidence strength, not calibrated probabilities.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from functools import lru_cache

from app.search import morphology as M
from app.shared.config import repo_root

# Score weights (sum to 1.0). Fixed by design, not tuned: official evidence dominates.
W_EXACT, W_MORPH, W_LEX, W_HIST, W_SEM = 0.10, 0.15, 0.62, 0.10, 0.03
# Decision thresholds, tuned on the dev split of benchmark/okpd2_resolver (see the V4 report).
ACCEPT = 0.36
MARGIN = 0.18
TOP_K = 5
ONE_WORD_EXACT_MIN_SPECIFICITY = 0.60
ONE_WORD_EXACT_RIVAL_SCORE = 0.40

# Procurement boilerplate lemmas that never identify a product category.
_BOILERPLATE = {"поставка", "закупка", "приобретение", "нужда", "товар", "продукция", "оказание",
                "выполнение", "контракт", "договор", "лот", "шт", "штука", "упаковка", "кг", "литр", "мл", "уп"}


@dataclass(frozen=True)
class CategorySuggestion:
    okpd2: str
    confidence: float
    basis: str
    evidence: list[str]
    official_name: str | None = None


@dataclass(frozen=True)
class Resolution:
    state: str  # RESOLVED | CATEGORY_AMBIGUOUS | CATEGORY_UNCERTAIN
    suggestions: list[CategorySuggestion]
    margin: float | None = None

    @property
    def ranking_code(self) -> str | None:
        return self.suggestions[0].okpd2 if self.state == "RESOLVED" else None


@dataclass
class _Code:
    code: str
    name: str | None
    normalized: str | None
    lemma_sets: list[frozenset[str]]
    parent: str | None
    depth: int
    lemma_union: frozenset[str] = frozenset()
    ancestors: frozenset[str] = frozenset()
    title_weights: list[float] = field(default_factory=list)


class CategoryIndex:
    def __init__(self, codes: list[dict]):
        self.rows = {row["code"]: row for row in codes}
        self.codes: dict[str, _Code] = {}
        for row in codes:
            sets = [frozenset(ls) for ls in row.get("lemmas", [])]
            self.codes[row["code"]] = _Code(row["code"], row.get("name"), row.get("normalized_name"), sets,
                                            row.get("parent"), row.get("depth") or 0, frozenset().union(*sets))
        for c in self.codes.values():
            chain, p = [], c.parent
            while p and p in self.codes:
                chain.append(p)
                p = self.codes[p].parent
            c.ancestors = frozenset(chain)
        named = [c for c in self.codes.values() if c.name]
        self.n = max(len(named), 2)
        self.postings: dict[str, set[str]] = defaultdict(set)
        self.by_title: dict[str, list[str]] = defaultdict(list)
        for c in named:
            for lemma in c.lemma_union:
                self.postings[lemma].add(c.code)
            self.by_title[c.normalized].append(c.code)
        for c in named:
            c.title_weights = [self.idf(self.df(ls)) for ls in c.lemma_sets]
        self.vocabulary = sorted(self.postings)
        # Historical phrase evidence (observed codes only), keyed by PostgreSQL FTS lexemes.
        self.phrase_items: dict[str, Counter[str]] = {}
        self.phrase_df: Counter[str] = Counter()
        for row in codes:
            terms = Counter()
            for phrase in row.get("phrases", []):
                for term in set(phrase.get("lexemes", [])):
                    terms[term] += phrase["items"]
            if terms:
                self.phrase_items[row["code"]] = terms
                self.phrase_df.update(terms)

    @classmethod
    def from_data(cls, data: dict) -> "CategoryIndex":
        return cls(data["codes"])

    def df(self, lemma_set) -> int:
        """Number of official category titles containing any lemma of one word."""
        return len(set().union(*(self.postings.get(lemma, ()) for lemma in lemma_set)))

    def idf(self, df: int) -> float:
        """IDF(term) = log(N / df(term)); a term absent from the taxonomy is maximally specific."""
        return math.log(self.n / max(df, 1))

    def related(self, a: str, b: str) -> bool:
        return a == b or a in self.codes[b].ancestors or b in self.codes[a].ancestors


@lru_cache(maxsize=1)
def load_index() -> CategoryIndex:
    path = repo_root() / "data" / "seed" / "okpd2_category_index.json"
    with path.open(encoding="utf-8") as source:
        return CategoryIndex.from_data(json.load(source))


@dataclass
class _Query:
    words: list[str]
    lemma_sets: list[frozenset[str]]
    weights: list[float]
    normalized: str


def _query(index: CategoryIndex, text: str) -> _Query:
    words, sets = [], []
    for word in M.content_tokens(text):
        lemmas = frozenset(M.lemmas(word))
        if lemmas & _BOILERPLATE:
            continue
        words.append(word)
        sets.append(lemmas)
    return _Query(words, sets, [index.idf(index.df(ls)) for ls in sets], M.normalize(text))


def _historical(index: CategoryIndex, code: str, q_terms: set[str]) -> tuple[float, bool, dict | None]:
    """(support in [0,1], V3 dominant-phrase rule satisfied, supporting phrase)."""
    terms = index.phrase_items.get(code)
    if not terms or not q_terms:
        return 0.0, False, None
    matched = q_terms & terms.keys()
    if not matched:
        return 0.0, False, None
    shares = {t: terms[t] / index.phrase_df[t] for t in matched}
    support = len(matched) / len(q_terms) * max(shares.values())
    if len(matched) < len(q_terms):
        return support, False, None
    distinctive = [t for t, s in shares.items() if s >= 0.85]
    if not distinctive or (len(q_terms) == 1 and min(terms[t] for t in distinctive) < 2):
        return support, False, None
    phrase = next((p for p in index.rows[code].get("phrases", []) if set(p.get("lexemes", [])) >= q_terms), None)
    return support, phrase is not None, phrase


def _fuzzy(index: CategoryIndex, words: list[str]) -> dict[str, tuple[float, str]]:
    """Typo-tolerant term neighbors (suggestions only): code -> (similarity, official lemma)."""
    out: dict[str, tuple[float, str]] = {}
    for word in words:
        lemma = M.lemmas(word)[0]
        if len(lemma) < 6 or any(form in index.postings for form in M.lemmas(word)):
            continue
        for term in index.vocabulary:
            if len(term) >= 6 and abs(len(term) - len(lemma)) <= 2:
                ratio = SequenceMatcher(None, lemma, term).ratio()
                if ratio >= 0.88:
                    for code in index.postings[term]:
                        if ratio > out.get(code, (0.0, ""))[0]:
                            out[code] = (ratio, term)
    return out


def _official(index: CategoryIndex, q: _Query, q_terms: set[str], sem: dict[str, float]) -> list[CategorySuggestion]:
    candidates = set(index.by_title.get(q.normalized, []))
    for ls in q.lemma_sets:
        for lemma in ls:
            candidates |= index.postings.get(lemma, set())
    total = sum(q.weights)
    log_n = math.log(index.n)
    out = []
    for code in candidates:
        c = index.codes[code]
        exact = q.normalized == c.normalized
        morph = exact or (len(q.lemma_sets) == len(c.lemma_sets) > 0 and
                          all(a & b for a, b in zip(q.lemma_sets, c.lemma_sets)))
        hit = [bool(ls & c.lemma_union) for ls in q.lemma_sets]
        coverage = 1.0 if exact else sum(w for w, h in zip(q.weights, hit) if h) / total if total else 0.0
        title_hit = [any(ts & ls for ls in q.lemma_sets) for ts in c.lemma_sets]
        title_total = sum(c.title_weights)
        title_focus = 1.0 if exact else (sum(w for w, h in zip(c.title_weights, title_hit) if h) / title_total
                                         if title_total else 0.0)
        specificity = 1.0 if exact else max((w for w, h in zip(q.weights, hit) if h), default=0.0) / log_n
        weighted_token = coverage * (0.45 + 0.40 * title_focus + 0.15 * specificity)
        support, _, _ = _historical(index, code, q_terms)
        score = (W_EXACT * exact + W_MORPH * morph + W_LEX * weighted_token
                 + W_HIST * support + W_SEM * sem.get(code, 0.0))
        basis = "OFFICIAL_EXACT_TITLE" if exact else "OFFICIAL_MORPH_TITLE" if morph else "OFFICIAL_TERMS"
        evidence = [f"Official category name: {c.name}"]
        if not exact:
            matched = ", ".join(w for w, h in zip(q.words, hit) if h)
            evidence.append(f"Matched official terms: {matched} ({round(coverage * 100)}% of query term weight)")
        if support:
            evidence.append(f"Historical procurement support: {round(support * 100)}%")
        out.append(CategorySuggestion(code, round(score, 3), basis, evidence, c.name))
    return out


def _contextual_weak(index: CategoryIndex, q: _Query,
                     suggestions: list[CategorySuggestion]) -> list[CategorySuggestion]:
    """Use an official parent title to surface relevant options without resolving them."""
    if len(q.words) < 4:
        return suggestions
    total = sum(q.weights)
    enriched = []
    for suggestion in suggestions:
        code = index.codes[suggestion.okpd2]
        if suggestion.basis != "OFFICIAL_TERMS" or not q.lemma_sets[0] & code.lemma_union:
            enriched.append(suggestion)
            continue
        ancestors = frozenset().union(*(index.codes[parent].lemma_union for parent in code.ancestors))
        context = sum(weight for lemmas, weight in zip(q.lemma_sets[1:], q.weights[1:])
                      if lemmas & ancestors and not lemmas & code.lemma_union)
        if not context:
            enriched.append(suggestion)
            continue
        enriched.append(replace(suggestion,
                                confidence=round(min(.49, suggestion.confidence + W_LEX * context / total), 3),
                                basis="OFFICIAL_CONTEXT",
                                evidence=suggestion.evidence + ["Additional terms match an official parent category"]))
    return sorted(enriched, key=lambda s: (-s.confidence, -index.codes[s.okpd2].depth, s.okpd2))


@dataclass(frozen=True)
class Evidence:
    official: list[CategorySuggestion]          # official-taxonomy candidates, best first
    margin: float | None                        # leader minus best rival (None without official candidates)
    title: list[CategorySuggestion]             # stage 1/2: exact, else morphology-aware official title matches
    historical: list[CategorySuggestion]        # dominant historical phrases (V3 rule)
    weak: list[CategorySuggestion]              # official partials + fuzzy + semantic, for uncertain results
    polysemous_exact_title: bool = False


def collect(index: CategoryIndex, text: str, lexemes: list[str], semantic: list[tuple[str, float]]) -> Evidence:
    """All category evidence for one query; threshold-free, so decisions can be replayed by `decide`.

    `lexemes` are PostgreSQL Russian FTS lexemes of the query (historical phrase channel);
    `semantic` is (code, similarity in [0,1]) from text/semantic retrieval (support only).
    """
    q = _query(index, text)
    # PostgreSQL keeps quantities such as "3.2" as lexemes; they do not identify a category.
    q_terms = {term for term in lexemes if any(ch.isalpha() for ch in term)}
    sem = {code: sim for code, sim in semantic if code in index.codes}

    def order(s: CategorySuggestion):
        return -s.confidence, -index.codes[s.okpd2].depth, s.okpd2

    official = sorted(_official(index, q, q_terms, sem), key=order)
    margin = None
    if official:
        top = official[0]
        # A broader ancestor of the leader is the same answer; anything else (including the
        # leader's own sub-categories) is a rival the query must out-score.
        rival = next((s for s in official[1:] if s.okpd2 not in index.codes[top.okpd2].ancestors), None)
        margin = round(top.confidence - (rival.confidence if rival else 0.0), 3)
    exact = [s for s in official if s.basis == "OFFICIAL_EXACT_TITLE"]
    title = exact or [s for s in official if s.basis == "OFFICIAL_MORPH_TITLE"]
    polysemous_exact_title = (
        len(q.words) == 1 and bool(exact)
        and q.weights[0] / math.log(index.n) < ONE_WORD_EXACT_MIN_SPECIFICITY
        and any(not index.related(exact[0].okpd2, s.okpd2)
                and s.confidence >= ONE_WORD_EXACT_RIVAL_SCORE for s in official)
    )

    historical = []
    for code in sorted(index.phrase_items):
        support, dominant, phrase = _historical(index, code, q_terms)
        if dominant:
            historical.append(CategorySuggestion(
                code, round(0.5 + 0.4 * support, 3), "HISTORICAL_DOMINANT",
                [f"Historical phrase: {phrase['text']}", f"Observed items: {phrase['items']}"], index.codes[code].name))
    historical.sort(key=order)

    weak, seen = list(official), {s.okpd2 for s in official}
    for code, (ratio, term) in sorted(_fuzzy(index, q.words).items()):
        if code not in seen:
            weak.append(CategorySuggestion(code, round(min(0.4, 0.2 + 0.2 * ratio), 3), "FUZZY",
                                           [f"Similar official term: {term}"], index.codes[code].name))
            seen.add(code)
    for code, similarity in sem.items():
        if code not in seen:
            weak.append(CategorySuggestion(code, round(min(0.2, 0.2 * similarity), 3), "SEMANTIC",
                                           ["Related retrieved product text"], index.codes[code].name))
            seen.add(code)
    return Evidence(official, margin, title, historical,
                    _contextual_weak(index, q, sorted(weak, key=order)), polysemous_exact_title)


def decision(index: CategoryIndex, ev: Evidence, accept: float = ACCEPT,
             min_margin: float = MARGIN) -> tuple[str, CategorySuggestion | None, str]:
    """(state, chosen suggestion, stage) — the whole decision rule, without building candidate lists."""
    if ev.title:
        # Stages 1-2: the query is an official title. One line of matches (a code and its ancestors)
        # identifies the category; the same title on unrelated lines is ambiguous.
        top = ev.title[0]
        one_line = all(index.related(top.okpd2, s.okpd2) for s in ev.title)
        if not one_line or ev.polysemous_exact_title:
            return "CATEGORY_AMBIGUOUS", None, "title"
        return "RESOLVED", top, "title"
    if ev.official and ev.official[0].confidence >= accept:
        # Stage 3: weighted official terms.
        if ev.margin >= min_margin:
            return "RESOLVED", ev.official[0], "official"
        # Stage 4 inside ambiguity: procurement history may choose among the official contenders,
        # but only a code on one of their lines — history never introduces a new category.
        contenders = [s for s in ev.official if s.confidence >= ev.official[0].confidence - min_margin]
        backed = [h for h in ev.historical if any(index.related(h.okpd2, s.okpd2) for s in contenders)]
        if len(backed) == 1:
            line = next(s for s in contenders if index.related(backed[0].okpd2, s.okpd2))
            return "RESOLVED", replace(backed[0], evidence=backed[0].evidence + [
                f"Official candidate: {line.official_name}"]), "official"
        return "CATEGORY_AMBIGUOUS", None, "official"
    # Stage 4: official evidence is weak; a dominant historical phrase may still identify the category.
    if ev.historical:
        return "RESOLVED", ev.historical[0], "historical"
    return "CATEGORY_UNCERTAIN", None, "weak"


def decide(index: CategoryIndex, ev: Evidence, accept: float = ACCEPT, min_margin: float = MARGIN) -> Resolution:
    state, chosen, stage = decision(index, ev, accept, min_margin)
    ranked = {"title": ev.title + [s for s in ev.official if s not in ev.title], "official": ev.official,
              "historical": ev.historical + ev.official, "weak": ev.weak}[stage]
    if chosen is not None:
        ranked = [chosen] + [s for s in ranked if s.okpd2 != chosen.okpd2]
    return Resolution(state, _distinct_lines(index, ranked), ev.margin)


def resolve(index: CategoryIndex, text: str, lexemes: list[str], semantic: list[tuple[str, float]]) -> Resolution:
    """Resolve free text to an official OKPD2 category, or report ambiguity / uncertainty."""
    return decide(index, collect(index, text, lexemes, semantic))


def _distinct_lines(index: CategoryIndex, ranked: list[CategorySuggestion]) -> list[CategorySuggestion]:
    """Ranked candidates without broader duplicates: an ancestor of a listed code adds no alternative."""
    out: list[CategorySuggestion] = []
    for s in ranked:
        if not any(s.okpd2 in index.codes[o.okpd2].ancestors or s.okpd2 == o.okpd2 for o in out):
            out.append(s)
            if len(out) == TOP_K:
                break
    return out
