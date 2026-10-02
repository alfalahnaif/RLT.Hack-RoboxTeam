"""Category resolution must separate terminology from noisy supplier retrieval."""
from app.search.category_resolver import CategoryIndex, resolve


def _index():
    return CategoryIndex.from_data({"codes": [
        {"code": "08.99.10.120", "name": "Асфальтиты и породы асфальтные",
         "name_lexemes": ["асфальтит", "пород", "асфальтн"], "items": 1, "lots": 1,
         "phrases": [{"text": "асфальт холодный 25 кг мешок", "items": 1, "lexemes": ["асфальт", "холодн", "мешок"]}]},
        {"code": "23.99.13.111", "name": "Смеси асфальтобетонные",
         "name_lexemes": ["смес", "асфальтобетон"], "items": 500, "lots": 100,
         "phrases": [{"text": "смесь асфальтобетонная", "items": 300, "lexemes": ["смес", "асфальтобетон"]}]},
        {"code": "10.51.11.141", "name": "Молоко питьевое стерилизованное",
         "name_lexemes": ["молок", "питьев", "стерилизова"], "items": 100, "lots": 50,
         "phrases": [{"text": "молоко ультрапастеризованное", "items": 80, "lexemes": ["молок", "ультрапастеризова"]}]},
    ]})


def test_exact_rare_official_term_overrides_unrelated_semantic_results():
    result = resolve(_index(), "Асфальтиты", ["асфальтит"], [])
    assert result.state == "RESOLVED"
    assert result.suggestions[0].okpd2 == "08.99.10.120"
    assert result.suggestions[0].basis == "EXACT_TERM"
    assert result.suggestions[0].confidence >= 0.9


def test_historical_specific_phrase_can_resolve_without_official_exact_match():
    result = resolve(_index(), "Молоко ультрапастеризованное", ["молок", "ультрапастеризова"], [])
    assert result.state == "RESOLVED"
    assert result.suggestions[0].okpd2 == "10.51.11.141"
    assert result.suggestions[0].basis == "HISTORICAL_DOMINANT"


def test_generic_or_semantic_only_evidence_is_uncertain():
    result = resolve(_index(), "Асфальт", ["асфальт"], [("23.99.13.111", 0.8)])
    assert result.state == "CATEGORY_UNCERTAIN"
    assert not result.ranking_code
    semantic = resolve(_index(), "неизвестное", ["неизвестн"], [("23.99.13.111", 0.95)])
    assert semantic.state == "CATEGORY_UNCERTAIN"
    assert semantic.suggestions[0].basis == "SEMANTIC"


def test_fuzzy_term_is_suggested_but_not_silently_assumed():
    result = resolve(_index(), "Асфальтитв", ["асфальтитв"], [])
    assert result.suggestions[0].okpd2 == "08.99.10.120"
    assert result.suggestions[0].basis == "FUZZY"
    assert result.state == "CATEGORY_UNCERTAIN"
