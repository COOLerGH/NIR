"""BDD-тесты для парсера запросов (бизнес-идея)."""

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from core.parser import parse_query


# --- Сценарии ---

@scenario("../../features/query_parser.feature", "Простой запрос из одного слова")
def test_simple_query():
    pass


@scenario("../../features/query_parser.feature", "Запрос с оператором AND")
def test_and_query():
    pass


@scenario("../../features/query_parser.feature", "Запрос с оператором OR")
def test_or_query():
    pass


@scenario("../../features/query_parser.feature", "Запрос с оператором NOT")
def test_not_query():
    pass


@scenario("../../features/query_parser.feature", "Запрос с wildcard")
def test_wildcard_query():
    pass


@scenario("../../features/query_parser.feature", "Запрос с фильтром размера")
def test_size_filter():
    pass


@scenario("../../features/query_parser.feature", "Запрос с фильтром даты")
def test_date_filter():
    pass


@scenario("../../features/query_parser.feature", "Пустой запрос")
def test_empty_query():
    pass


@scenario("../../features/query_parser.feature", "Различные форматы запросов")
def test_various_formats():
    pass


# --- Фикстура контекста ---

@pytest.fixture
def ctx():
    return {"parsed": None}


# --- When ---

@when(parsers.parse('пользователь вводит запрос "{query}"'), target_fixture="ctx")
def parse_input(ctx, query):
    ctx = {"parsed": parse_query(query)}
    return ctx


@when('пользователь вводит запрос ""', target_fixture="ctx")
def parse_empty_input(ctx):
    ctx = {"parsed": parse_query("")}
    return ctx


# --- Then ---

@then(parsers.parse('парсер распознаёт терм "{term}"'))
def check_single_term(ctx, term):
    assert term in ctx["parsed"].terms


@then(parsers.parse('оператор по умолчанию "{op}"'))
def check_default_operator(ctx, op):
    assert ctx["parsed"].operator == op


@then("запрос не пустой")
def check_not_empty(ctx):
    assert ctx["parsed"].is_empty is False


@then(parsers.parse('парсер распознаёт термы "{term1}" и "{term2}"'))
def check_two_terms(ctx, term1, term2):
    assert term1 in ctx["parsed"].terms
    assert term2 in ctx["parsed"].terms


@then(parsers.parse('оператор "{op}"'))
def check_operator(ctx, op):
    assert ctx["parsed"].operator == op


@then(parsers.parse('исключённый терм "{term}"'))
def check_excluded(ctx, term):
    assert term in ctx["parsed"].exclude_terms


@then(parsers.parse('парсер распознаёт wildcard "{pattern}"'))
def check_wildcard(ctx, pattern):
    assert ctx["parsed"].wildcard == pattern


@then(parsers.parse('фильтр размера с оператором "{op}" и значением {value:d}'))
def check_size_filter(ctx, op, value):
    assert ctx["parsed"].size_filter is not None
    assert ctx["parsed"].size_filter["op"] == op
    assert ctx["parsed"].size_filter["value"] == value


@then(parsers.parse('фильтр даты с оператором "{op}" и значением "{value}"'))
def check_date_filter(ctx, op, value):
    assert ctx["parsed"].date_filter is not None
    assert ctx["parsed"].date_filter["op"] == op
    assert ctx["parsed"].date_filter["value"] == value


@then("запрос пустой")
def check_empty(ctx):
    assert ctx["parsed"].is_empty is True


@then(parsers.parse("запрос пустой равен {expected}"))
def check_is_empty_flag(ctx, expected):
    expected_bool = expected.strip() == "True"
    assert ctx["parsed"].is_empty is expected_bool
