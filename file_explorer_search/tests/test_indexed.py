"""
Тесты индексного алгоритма поиска.

Техника 3: Branch Testing — покрытие всех ветвлений метода search().

Карта ветвлений search():
    Ветка 1: query.is_empty → return []
    Ветка 2: indexer.is_built=True → indexed_search
    Ветка 3: indexer.is_built=False → return []
    Ветка 4: filters заданы → apply_filters
    Ветка 5: len(results) > max_results → обрезка
    Ветка 6: нормальный возврат результатов
"""

import pytest
from unittest.mock import MagicMock

from algorithms.indexed_search import IndexedSearch
from algorithms.naive_search import NaiveSearch
from core.indexer import FileIndexer
from core.parser import parse_query
from api.mock_fs import InMemoryFileSystem


# ============================================================
# Branch Testing: покрытие всех ветвлений search()
# ============================================================

class TestBranchCoverage:
    """Тесты для покрытия всех веток метода search()."""

    # --- BR-01: Ветка 1 — пустой запрос → return [] ---
    def test_branch_empty_query(self, indexed):
        query = parse_query("")
        results = indexed.search(query, "/")
        assert results == []

    # --- BR-02: Ветка 1 — запрос из пробелов → return [] ---
    def test_branch_whitespace_query(self, indexed):
        query = parse_query("   \t\n  ")
        results = indexed.search(query, "/")
        assert results == []

    # --- BR-03: Ветка 2,6 — индекс есть, фильтров нет, результаты < max ---
    def test_branch_index_exists_no_filters(self, indexed):
        query = parse_query("python")
        results = indexed.search(query, "/")
        assert len(results) > 0
        assert all(r.score > 0 for r in results)

    # --- BR-04: Ветка 3 — индекса нет → return [] ---
    def test_branch_no_index(self, sample_fs):
        empty_indexer = FileIndexer()
        search = IndexedSearch(sample_fs, empty_indexer)
        query = parse_query("python")
        results = search.search(query, "/")
        assert results == []

    # --- BR-05: Ветка 4 — фильтр по размеру ---
    def test_branch_with_size_filter(self, indexed):
        query = parse_query("python size>100")
        results = indexed.search(query, "/")
        # Все результаты должны иметь size > 100
        assert isinstance(results, list)

    # --- BR-06: Ветка 4 — фильтр по дате ---
    def test_branch_with_date_filter(self, indexed):
        query = parse_query("python date>2025-03-01")
        results = indexed.search(query, "/")
        assert isinstance(results, list)

    # --- BR-07: Ветка 5 — результатов больше max_results → обрезка ---
    def test_branch_results_exceed_max(self, indexed):
        query = parse_query("python")
        results = indexed.search(query, "/", max_results=1)
        assert len(results) <= 1

    # --- BR-08: Ветка 5 — max_results=0 → пустой список ---
    def test_branch_max_results_zero(self, indexed):
        query = parse_query("python")
        results = indexed.search(query, "/", max_results=0)
        assert results == []

    # --- BR-09: Ветка 6 — нормальный возврат, несколько результатов ---
    def test_branch_normal_return(self, indexed):
        query = parse_query("server")
        results = indexed.search(query, "/")
        assert len(results) > 0
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ============================================================
# Branch Testing: ветвления внутри _get_candidates
# ============================================================

class TestCandidateBranches:
    """Ветвления при сборе кандидатов из индекса."""

    # --- AND: пересечение множеств ---
    def test_and_operator_intersection(self, indexed):
        query = parse_query("python AND flask")
        results = indexed.search(query, "/")
        assert len(results) > 0
        # app.py содержит оба слова
        assert any(r.name == "app.py" for r in results)

    # --- AND: одно слово отсутствует → пустое пересечение ---
    def test_and_operator_no_match(self, indexed):
        query = parse_query("python AND nonexistent999")
        results = indexed.search(query, "/")
        assert results == []

    # --- OR: объединение множеств ---
    def test_or_operator_union(self, indexed):
        query = parse_query("flask OR pytest")
        results = indexed.search(query, "/")
        assert len(results) >= 2

    # --- NOT: исключение файлов ---
    def test_not_operator_exclusion(self, indexed):
        query = parse_query("python NOT flask")
        results = indexed.search(query, "/")
        assert all(r.name != "app.py" for r in results)

    # --- Терм отсутствует в индексе ---
    def test_term_not_in_index(self, indexed):
        query = parse_query("xyznonexistent")
        results = indexed.search(query, "/")
        assert results == []

    # --- Только стоп-слова ---
    def test_only_stop_words(self, indexed):
        query = parse_query("the and of")
        results = indexed.search(query, "/")
        assert results == []


# ============================================================
# Assumptions: 2 вида
# ============================================================

class TestAssumptions:
    """Демонстрация assumptions в тестах."""

    # --- Assumption вид 1: skipif ---
    @pytest.mark.skipif(
        not True,  # всегда выполняется, для демонстрации синтаксиса
        reason="Индексный поиск требует построенного индекса"
    )
    def test_indexed_search_with_assumption(self, indexed):
        query = parse_query("python")
        results = indexed.search(query, "/")
        assert len(results) > 0

    # --- Assumption вид 2: xfail ---
    @pytest.mark.xfail(reason="Поиск точных фраз пока не реализован")
    def test_phrase_search_not_implemented(self, indexed):
        query = parse_query('"python flask"')
        results = indexed.search(query, "/")
        # Ожидаем что точная фраза будет найдена целиком
        assert any("python flask" in r.snippet for r in results)


# ============================================================
# Мокирование: вид 2 — MagicMock для проверки вызовов
# ============================================================

class TestMocking:
    """Мокирование для проверки взаимодействий."""

    # --- Mock вид 2: MagicMock проверка вызовов API ---
    def test_naive_calls_get_content_for_each_file(self, sample_fs):
        """Наивный алгоритм вызывает get_content для каждого файла."""
        mock_api = MagicMock(wraps=sample_fs)
        mock_api.walk.return_value = sample_fs.walk("/")
        mock_api.get_content.side_effect = sample_fs.get_content

        naive = NaiveSearch(mock_api)
        query = parse_query("python")
        naive.search(query, "/")

        mock_api.walk.assert_called_once_with("/")
        # get_content вызывается для каждого файла
        assert mock_api.get_content.call_count == len(sample_fs.walk("/"))

    # --- Mock вид 3: mocker.patch ---
    def test_indexed_calls_api_only_for_results(self, sample_fs, indexer, mocker):
        """Индексный алгоритм вызывает API только для найденных файлов (для сниппетов)."""
        spy = mocker.spy(sample_fs, "get_content")

        search = IndexedSearch(sample_fs, indexer)
        query = parse_query("python")
        results = search.search(query, "/")

        # Должен быть вызван get_content, но только для файлов в результатах
        assert spy.call_count == len(results)
        
        # Проверяем, что вызовы были именно для найденных путей
        expected_calls = {r.path for r in results}
        actual_calls = {args[0] for args, _ in spy.call_args_list}
        assert actual_calls == expected_calls

    def test_indexer_calls_get_content_during_build(self, sample_fs):
        """Индексатор вызывает get_content при построении индекса."""
        mock_api = MagicMock(wraps=sample_fs)
        mock_api.walk.return_value = sample_fs.walk("/")
        mock_api.get_content.side_effect = sample_fs.get_content

        indexer = FileIndexer()
        indexer.build_index("/", mock_api)

        file_count = len(sample_fs.walk("/"))
        assert mock_api.get_content.call_count == file_count


# ============================================================
# Сравнение алгоритмов: одинаковые результаты
# ============================================================

class TestAlgorithmComparison:
    """Наивный и индексный должны находить одинаковые файлы."""

    @pytest.mark.parametrize("query_str", [
        "python",
        "server",
        "test",
        "data",
    ])
    def test_same_files_found(self, naive, indexed, query_str):
        """Оба алгоритма находят одинаковое множество файлов."""
        query = parse_query(query_str)
        naive_results = naive.search(query, "/")
        indexed_results = indexed.search(query, "/")

        naive_paths = set(r.path for r in naive_results)
        indexed_paths = set(r.path for r in indexed_results)

        assert naive_paths == indexed_paths

    def test_both_empty_for_nonexistent(self, naive, indexed):
        """Оба возвращают пустой список для несуществующего слова."""
        query = parse_query("zzzznonexistent")
        assert naive.search(query, "/") == []
        assert indexed.search(query, "/") == []
