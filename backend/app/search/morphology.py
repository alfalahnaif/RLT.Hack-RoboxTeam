"""Deterministic Russian morphology for OKPD2 taxonomy resolution.

pymorphy3 (MIT, OpenCorpora dictionary bundled in pymorphy3-dicts-ru) runs fully
offline; both packages are pinned in requirements.txt, so the same word always
yields the same lemmas. The taxonomy index stores lemmas computed with this
module (category_index_build), and queries are lemmatized with it at search time.

A word keeps every nominal reading's lemma ("вина" -> {"вина", "вино"}), because
choosing one parse without context would silently drop the intended one. Verb
readings are discarded when a nominal reading exists ("стали" -> {"сталь"}, not
"стать"), and participles keep their adjective form ("моющие" -> "моющий") —
OKPD2 titles and product names are noun phrases.
"""
from __future__ import annotations

import re
from functools import lru_cache

_WORD = re.compile(r"[a-zа-я0-9]+")
_FUNCTION_POS = {"PREP", "CONJ", "PRCL", "INTJ"}
_NOMINAL_POS = {"NOUN", "ADJF", "ADJS", "PRTF", "PRTS", "NUMR", None}


@lru_cache(maxsize=1)
def _analyzer():
    import pymorphy3
    return pymorphy3.MorphAnalyzer()


def describe() -> dict:
    """Library and dictionary versions; recorded in the index so a drift is detectable."""
    import pymorphy3
    import pymorphy3_dicts_ru
    return {"library": "pymorphy3", "version": pymorphy3.__version__,
            "dictionary": "pymorphy3-dicts-ru", "dictionary_version": pymorphy3_dicts_ru.__version__}


def normalize(text: str) -> str:
    """Case, ё and punctuation-insensitive form used for exact official-title matching."""
    return " ".join(_WORD.findall((text or "").lower().replace("ё", "е")))


def is_function_word(word: str) -> bool:
    parses = _analyzer().parse(word)
    return bool(parses) and parses[0].tag.POS in _FUNCTION_POS


@lru_cache(maxsize=200_000)
def lemmas(word: str) -> tuple[str, ...]:
    """All nominal lemmas of one normalized word, most probable first."""
    if not re.search("[а-я]", word):
        return (word,)                    # Latin model names and codes are matched literally
    parses = _analyzer().parse(word)
    nominal = [p for p in parses if p.tag.POS in _NOMINAL_POS] or parses
    out: list[str] = []
    for p in nominal:
        lemma = p.normal_form
        if p.tag.POS in {"PRTF", "PRTS"}:
            form = p.inflect({"PRTF", "masc", "sing", "nomn"})
            lemma = form.word if form else lemma
        if lemma not in out:
            out.append(lemma)
    return tuple(out) or (word,)


def content_tokens(text: str) -> list[str]:
    """Normalized words that can carry category meaning (no digits, single letters or function words)."""
    return [w for w in normalize(text).split()
            if len(w) > 1 and not w.isdigit() and any(ch.isalpha() for ch in w) and not is_function_word(w)]
