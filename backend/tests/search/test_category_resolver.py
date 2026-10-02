"""OKPD2 resolver V4: official taxonomy + Russian morphology + ambiguity, against the checked-in index."""
import json

import pytest

from app.search import category_resolver as R
from app.search import morphology as M
from app.shared.config import repo_root

ASPHALTITES = "08.99.10.120"
NATURAL_BITUMEN = "08.99.10.110"


@pytest.fixture(scope="module")
def index():
    return R.load_index()


def resolve(index, text, lexemes=(), semantic=()):
    return R.resolve(index, text, list(lexemes), list(semantic))


@pytest.mark.parametrize("query", ["Асфальтиты", "Асфальтит", "асфальтитов", "АСФАЛЬТИТАМИ"])
def test_singular_plural_and_case_forms_converge(index, query):
    result = resolve(index, query)
    assert result.state == "RESOLVED"
    assert result.ranking_code == ASPHALTITES
    assert result.suggestions[0].basis == "OFFICIAL_TERMS"


def test_exact_official_title_comes_first(index):
    result = resolve(index, "Вина столовые прочие")
    assert result.state == "RESOLVED" and result.ranking_code == "11.02.12.159"
    assert result.suggestions[0].basis == "OFFICIAL_EXACT_TITLE"
    assert result.suggestions[0].official_name == "Вина столовые прочие"


def test_polysemous_one_word_exact_title_requires_confirmation(index):
    result = resolve(index, "Трубы")
    assert result.state == "CATEGORY_AMBIGUOUS" and result.ranking_code is None
    assert result.suggestions[0].okpd2 == "32.20.13.161"
    assert any(s.okpd2 != "32.20.13.161" and not index.related(s.okpd2, "32.20.13.161")
               for s in result.suggestions)


@pytest.mark.parametrize("query, code", [("Принтеры", "26.20.16.120"), ("Песчаник", "08.11.12.180")])
def test_distinctive_one_word_exact_titles_still_resolve(index, query, code):
    result = resolve(index, query)
    assert result.state == "RESOLVED" and result.ranking_code == code


def test_morphological_title_variant(index):
    result = resolve(index, "Вино столовое прочее")
    assert result.state == "RESOLVED" and result.ranking_code == "11.02.12.159"
    assert result.suggestions[0].basis == "OFFICIAL_MORPH_TITLE"


def test_exact_title_outranks_its_morphological_twin(index):
    exact = resolve(index, "Вина столовые")                    # 11.02.12.150; "Вино столовое" is 11.02.12.151
    assert exact.ranking_code == "11.02.12.150" and exact.suggestions[0].basis == "OFFICIAL_EXACT_TITLE"


@pytest.mark.parametrize("query", ["Стол", "Столы", "Асфальт"])
def test_broad_one_word_query_is_ambiguous_not_arbitrary(index, query):
    result = resolve(index, query)
    assert result.state == "CATEGORY_AMBIGUOUS"
    assert result.ranking_code is None
    assert len(result.suggestions) >= 2
    a, b = result.suggestions[:2]
    assert not index.related(a.okpd2, b.okpd2)                 # genuinely different categories, not parent/child
    assert all(s.official_name for s in result.suggestions)


def test_natural_bitumen_stays_distinct_from_asphaltites(index):
    result = resolve(index, "Битум природный")
    # Natural bitumen leads; bituminous mixtures (23.99.13) also name natural bitumen, and at the dev-tuned
    # margin the two are reported for confirmation rather than resolved. Asphaltites are never chosen.
    assert result.suggestions[0].okpd2 == NATURAL_BITUMEN and result.ranking_code != ASPHALTITES
    assert ASPHALTITES not in [s.okpd2 for s in result.suggestions]
    assert result.ranking_code in (NATURAL_BITUMEN, None)
    plural = resolve(index, "Битумы природные")
    assert (plural.state, plural.suggestions[0].okpd2) == (result.state, result.suggestions[0].okpd2)


def test_unknown_query_is_uncertain(index):
    result = resolve(index, "Флюрбикс заквант")
    assert result.state == "CATEGORY_UNCERTAIN" and result.ranking_code is None


def test_semantic_similarity_cannot_override_official_match(index):
    result = resolve(index, "Асфальтит", semantic=[("23.99.13.111", 1.0), ("42.11.20.300", 1.0)])
    assert result.ranking_code == ASPHALTITES


def test_semantic_only_evidence_is_uncertain(index):
    result = resolve(index, "Флюрбикс заквант", semantic=[("23.99.13.111", 0.95)])
    assert result.state == "CATEGORY_UNCERTAIN"
    assert result.suggestions[0].basis == "SEMANTIC" and result.suggestions[0].confidence < R.ACCEPT


def test_fuzzy_term_is_suggested_but_not_assumed(index):
    result = resolve(index, "Асфальтитв")
    assert result.state == "CATEGORY_UNCERTAIN"
    assert result.suggestions[0].okpd2 == ASPHALTITES and result.suggestions[0].basis == "FUZZY"


def test_historical_dominant_phrase_resolves_when_official_terms_are_weak(index):
    result = resolve(index, "Перчатки нитриловые", lexemes=["нитрилов", "перчатк"])
    assert result.state == "RESOLVED" and result.ranking_code == "22.19.60.119"
    assert result.suggestions[0].basis == "HISTORICAL_DOMINANT"


def test_ancestors_are_not_rivals(index):
    assert {"08.99.10", "08.99.1"} <= index.codes[ASPHALTITES].ancestors
    result = resolve(index, "Асфальтит")
    assert result.margin == result.suggestions[0].confidence     # its parents share the term but are not rivals
    assert not any(s.okpd2 in index.codes[ASPHALTITES].ancestors for s in result.suggestions)


def test_subcategory_parent_is_the_zero_category(index):
    assert index.codes["10.51.11.121"].parent == "10.51.11.120"
    assert index.codes["10.51.11.120"].parent == "10.51.11"


def test_term_specificity_uses_taxonomy_document_frequency(index):
    rare = index.df(frozenset(M.lemmas("асфальтит")))
    common = index.df(frozenset(M.lemmas("стол")))
    assert 1 <= rare <= 3 < common
    assert index.idf(rare) > index.idf(common)


def test_taxonomy_is_not_lemmatized_at_query_time(index, monkeypatch):
    calls = []
    real = M.lemmas
    monkeypatch.setattr(M, "lemmas", lambda word: calls.append(word) or real(word))
    resolve(index, "Битум природный")
    assert set(calls) == {"битум", "природный"}                  # only the query's own words


def test_index_covers_full_taxonomy_and_records_morphology(index):
    data = json.loads((repo_root() / "data" / "seed" / "okpd2_category_index.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 2 and data["official_codes"] == data["terminology_source"]["records"]
    assert data["morphology"] == M.describe()                    # the runtime lemmatizer matches the index
    row = next(r for r in data["codes"] if r["code"] == ASPHALTITES)
    assert row["tokens"] == ["асфальтиты", "породы", "асфальтные"]
    assert row["lemmas"][0] == ["асфальтит"] and row["phrase_lemmas"].startswith("асфальтит порода")
    assert row["parent"] == "08.99.10" and row["depth"] == len(index.codes[ASPHALTITES].ancestors) + 1 >= 4


def test_resolution_is_deterministic(index):
    first = [resolve(index, q) for q in ("Стол", "Асфальтит", "Молоко")]
    assert first == [resolve(index, q) for q in ("Стол", "Асфальтит", "Молоко")]
