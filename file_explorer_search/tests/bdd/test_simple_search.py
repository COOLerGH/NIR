"""BDD-тесты для простого поиска (императивный стиль)."""

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from api.mock_fs import InMemoryFileSystem
from core.parser import parse_query
from algorithms.naive_search import NaiveSearch


# --- Сценарии ---

@scenario("../../features/simple_search.feature", "Поиск существующего слова")
def test_search_existing():
    pass


@scenario("../../features/simple_search.feature", "Поиск несуществующего слова")
def test_search_nonexistent():
    pass


@scenario("../../features/simple_search.feature", "Пустой запрос")
def test_empty_query():
    pass


@scenario("../../features/simple_search.feature", "Запрос из спецсимволов")
def test_special_chars():
    pass


@scenario("../../features/simple_search.feature", "Поиск по различным запросам")
def test_parametrized_search():
    pass


# --- Фикстура контекста ---

@pytest.fixture
def ctx():
    return {"fs": None, "results": None}


# --- Утилита для Data Table ---

def parse_datatable(datatable):
    """Преобразовать Data Table из pytest-bdd в список словарей."""
    headers = datatable[0]
    rows = []
    for row in datatable[1:]:
        rows.append(dict(zip(headers, row)))
    return rows


# --- Given ---

@given("создана файловая система с файлами:", target_fixture="ctx")
def create_fs(ctx, datatable):
    fs = InMemoryFileSystem()
    for row in parse_datatable(datatable):
        fs.add_file(row["путь"], row["содержимое"])
    ctx = {"fs": fs, "results": None}
    return ctx

# --- When ---

@when(parsers.parse('пользователь выполняет поиск по слову "{query}"'), target_fixture="ctx")
def do_search(ctx, query):
    parsed = parse_query(query)
    naive = NaiveSearch(ctx["fs"])
    ctx["results"] = naive.search(parsed, "/")
    return ctx

@when('пользователь выполняет поиск по слову ""', target_fixture="ctx")
def do_empty_search(ctx):
    parsed = parse_query("")
    naive = NaiveSearch(ctx["fs"])
    ctx["results"] = naive.search(parsed, "/")
    return ctx

# --- Then ---

@then(parsers.parse("результат содержит {count:d} файла"))
def check_count(ctx, count):
    assert len(ctx["results"]) == count


@then(parsers.parse("результат содержит {count:d} файлов"))
def check_count_alt(ctx, count):
    assert len(ctx["results"]) == count


@then("каждый результат имеет score больше нуля")
def check_scores_positive(ctx):
    for r in ctx["results"]:
        assert r.score > 0


@then(parsers.parse('результат содержит файл "{name}"'))
def check_contains_file(ctx, name):
    names = [r.name for r in ctx["results"]]
    assert name in names


@then(parsers.parse('результат не содержит файл "{name}"'))
def check_not_contains_file(ctx, name):
    names = [r.name for r in ctx["results"]]
    assert name not in names


@then("результат пустой")
def check_empty(ctx):
    assert len(ctx["results"]) == 0
