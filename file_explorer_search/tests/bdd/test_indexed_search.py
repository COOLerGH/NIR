"""BDD-тесты для индексного поиска (декларативный стиль)."""

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from api.mock_fs import InMemoryFileSystem
from core.parser import parse_query
from core.indexer import FileIndexer
from algorithms.indexed_search import IndexedSearch


# --- Сценарии ---

@scenario("../../features/indexed_search.feature", "Поиск по одному слову")
def test_single_word():
    pass


@scenario("../../features/indexed_search.feature", "Более релевантный документ ранжируется выше")
def test_relevance_ranking():
    pass


@scenario("../../features/indexed_search.feature", "Поиск несуществующего слова")
def test_nonexistent_word():
    pass


@scenario("../../features/indexed_search.feature", "Оператор AND")
def test_operator_and():
    pass


@scenario("../../features/indexed_search.feature", "Оператор OR")
def test_operator_or():
    pass


@scenario("../../features/indexed_search.feature", "Оператор NOT")
def test_operator_not():
    pass


@scenario("../../features/indexed_search.feature", "Поиск без построенного индекса")
def test_no_index():
    pass


# --- Фикстура контекста ---

@pytest.fixture
def ctx():
    return {"fs": None, "indexer": None, "indexed": None, "results": None}


# --- Given (Background) ---

@given("проиндексированная коллекция документов", target_fixture="ctx")
def indexed_collection(ctx):
    fs = InMemoryFileSystem()
    fs.add_file("/src/app.py", "python flask web application python server python")
    fs.add_file("/src/test_app.py", "python pytest test automation")
    fs.add_file("/src/utils.py", "python utility helper functions")
    fs.add_file("/src/web.py", "flask web server routes handler")
    fs.add_file("/docs/readme.txt", "project documentation guide overview")
    fs.add_file("/docs/api.md", "flask api endpoints rest documentation")
    fs.add_file("/data/report.csv", "name age city alice bob")

    indexer = FileIndexer()
    indexer.build_index("/", fs)

    ctx = {
        "fs": fs,
        "indexer": indexer,
        "indexed": IndexedSearch(fs, indexer),
        "results": None,
    }
    return ctx


@given("индекс не построен", target_fixture="ctx")
def no_index(ctx):
    fs = InMemoryFileSystem()
    fs.add_file("/src/app.py", "python flask web")
    indexer = FileIndexer()
    ctx = {
        "fs": fs,
        "indexer": indexer,
        "indexed": IndexedSearch(fs, indexer),
        "results": None,
    }
    return ctx


# --- When ---

@when(parsers.parse('пользователь ищет "{query}"'), target_fixture="ctx")
def do_search(ctx, query):
    parsed = parse_query(query)
    ctx["results"] = ctx["indexed"].search(parsed, "/")
    return ctx


# --- Then ---

@then(parsers.parse('результаты содержат файлы со словом "{word}"'))
def check_results_contain_word(ctx, word):
    assert len(ctx["results"]) > 0
    for r in ctx["results"]:
        content = ctx["fs"].get_content(r.path).lower()
        assert word in content


@then("результаты отсортированы по убыванию релевантности")
def check_sorted_desc(ctx):
    scores = [r.score for r in ctx["results"]]
    assert scores == sorted(scores, reverse=True)


@then("файл с наибольшим количеством вхождений имеет наивысший score")
def check_most_relevant_first(ctx):
    assert len(ctx["results"]) > 0
    best = ctx["results"][0]
    assert best.score >= max(r.score for r in ctx["results"])


@then("результат пустой")
def check_empty(ctx):
    assert len(ctx["results"]) == 0


@then("каждый результат содержит оба слова")
def check_both_words(ctx):
    for r in ctx["results"]:
        content = ctx["fs"].get_content(r.path).lower()
        assert "python" in content
        assert "flask" in content


@then(parsers.parse("результатов не менее {count:d}"))
def check_min_count(ctx, count):
    assert len(ctx["results"]) >= count


@then("каждый результат содержит хотя бы одно из слов")
def check_any_word(ctx):
    for r in ctx["results"]:
        content = ctx["fs"].get_content(r.path).lower()
        assert "flask" in content or "pytest" in content


@then(parsers.parse('результаты содержат слово "{word}"'))
def check_contains_word(ctx, word):
    assert len(ctx["results"]) > 0
    for r in ctx["results"]:
        content = ctx["fs"].get_content(r.path).lower()
        assert word in content


@then(parsers.parse('ни один результат не содержит слово "{word}"'))
def check_not_contains_word(ctx, word):
    for r in ctx["results"]:
        content = ctx["fs"].get_content(r.path).lower()
        assert word not in content
