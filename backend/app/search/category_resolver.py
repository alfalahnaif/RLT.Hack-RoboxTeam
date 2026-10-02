"""Ad-hoc OKPD2 terminology resolver; independent of frozen lot ranking.

The checked-in index contains only codes observed in the canonical procurement
snapshot. Official category names are terminology evidence, not procurement
history. Historical phrase counts are evidence, not a learned classifier.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from app.shared.config import repo_root

_WORDS = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
_STOP = {"и", "или", "для", "из", "по", "на", "в", "с", "не", "прочие", "прочий", "прочая", "прочее"}


@dataclass(frozen=True)
class CategorySuggestion:
    okpd2: str
    confidence: float
    basis: str
    evidence: list[str]


@dataclass(frozen=True)
class Resolution:
    state: str  # RESOLVED | CATEGORY_UNCERTAIN
    suggestions: list[CategorySuggestion]

    @property
    def ranking_code(self) -> str | None:
        return self.suggestions[0].okpd2 if self.state == "RESOLVED" else None


class CategoryIndex:
    def __init__(self, codes: list[dict]):
        self.codes = {row["code"]: row for row in codes}
        self.name_df: Counter[str] = Counter()
        self.phrase_items: dict[str, Counter[str]] = defaultdict(Counter)
        self.phrase_df: Counter[str] = Counter()
        for row in codes:
            self.name_df.update(set(row.get("name_lexemes", [])))
            terms = Counter()
            for phrase in row.get("phrases", []):
                for term in set(phrase.get("lexemes", [])):
                    terms[term] += phrase["items"]
            self.phrase_items[row["code"]] = terms
            self.phrase_df.update(terms)

    @classmethod
    def from_data(cls, data: dict) -> "CategoryIndex":
        return cls(data["codes"])


@lru_cache(maxsize=1)
def load_index() -> CategoryIndex:
    path = repo_root() / "data" / "seed" / "okpd2_category_index.json"
    with path.open(encoding="utf-8") as source:
        return CategoryIndex.from_data(json.load(source))


def _words(text: str) -> list[str]:
    return [w for w in _WORDS.findall(text.lower().replace("ё", "е")) if w not in _STOP and not w.isdigit()]


def resolve(index: CategoryIndex, text: str, lexemes: list[str], semantic: list[tuple[str, float]]) -> Resolution:
    """Prioritize unique official terms, then dominant historical phrases.

    A lone historical occurrence or fuzzy/semantic neighbor cannot silently
    establish a category. Confidence values describe evidence strength rather
    than calibrated probabilities.
    """
    # PostgreSQL keeps quantities such as "3.2" as lexemes; a concentration or
    # package size does not identify an OKPD2 category.
    q_terms = {term for term in lexemes if any(ch.isalpha() for ch in term)}
    q_words = _words(text)
    candidates: dict[str, CategorySuggestion] = {}

    def offer(code: str, confidence: float, basis: str, evidence: list[str]) -> None:
        prev = candidates.get(code)
        if prev is None or confidence > prev.confidence:
            candidates[code] = CategorySuggestion(code, round(confidence, 3), basis, evidence)

    for code, row in index.codes.items():
        name_terms = set(row.get("name_lexemes", []))
        shared = q_terms & name_terms
        rare = [term for term in shared if index.name_df[term] <= 3]
        if q_terms and q_terms <= name_terms and rare:
            offer(code, 0.98 if len(q_terms) == 1 else 0.96, "EXACT_TERM",
                  [f"Category name: {row['name']}", f"Distinctive official term: {sorted(rare)[0]}"])
        elif q_terms and len(shared) >= 2 and rare and len(shared) / len(q_terms) >= 0.75:
            offer(code, 0.87, "EXACT_TERM", [f"Category name: {row['name']}"])

        terms = index.phrase_items[code]
        matched = q_terms & terms.keys()
        if matched and len(matched) == len(q_terms) and q_terms:
            distinctive = [t for t in matched if index.phrase_df[t] and terms[t] / index.phrase_df[t] >= 0.85]
            if distinctive and (len(q_terms) > 1 or min(terms[t] for t in distinctive) >= 2):
                phrase = next((p for p in row.get("phrases", []) if set(p.get("lexemes", [])) >= q_terms), None)
                if phrase:
                    offer(code, 0.89, "HISTORICAL_DOMINANT",
                          [f"Historical phrase: {phrase['text']}", f"Observed items: {phrase['items']}"])

        if q_words and not candidates.get(code) and not any(s.confidence >= 0.82 for s in candidates.values()):
            name_words = _words(row.get("name") or "")
            best = max((SequenceMatcher(None, qword, nword).ratio() for qword in q_words for nword in name_words
                        if min(len(qword), len(nword)) >= 6), default=0.0)
            if best >= 0.88:
                offer(code, min(0.72, round(0.48 + best * 0.25, 3)), "FUZZY",
                      [f"Similar category term: {row['name']}"])

    for code, similarity in semantic:
        if code in index.codes:
            offer(code, min(0.39, 0.2 + similarity * 0.2), "SEMANTIC", ["Related retrieved product text"])

    ranked = sorted(candidates.values(), key=lambda x: (-x.confidence, x.okpd2))[:3]
    certain = bool(ranked and ranked[0].confidence >= 0.82 and
                   (len(ranked) == 1 or ranked[0].confidence - ranked[1].confidence >= 0.1))
    return Resolution("RESOLVED" if certain else "CATEGORY_UNCERTAIN", ranked)
