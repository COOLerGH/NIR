"""
Интеграционные тесты.

Проверяют совместную работу модулей:
- полный цикл поиска
- сравнение алгоритмов
- парсер запросов
- валидация
- сериализация
"""

import pytest
import time

from api.mock_fs import InMemoryFileSystem
from algorithms.naive_search import NaiveSearch
from algorithms.indexed_search import IndexedSearch
from core.indexer import FileIndexer
from core.cache import SearchCache
from core.parser import parse_query
from core.ranker import tokenize
from utils.validators import validate_query, validate_path, validate_max_results, sanitize_query
from utils.file_io import save_json, load_json, FileIOError


# ============================================================
# Кастомный матчер
# ============================================================

class ContainsPaths:
    """Матчер: проверяет что результаты содержат файлы с указанными путями."""

    def __init__(self, expected_paths):
        self.expected_paths = set(expected_paths)

    def __eq__(self, other):
        actual_paths = set(r.path for r in other)
        return self.expected_paths.issubset(actual_paths)

    def __repr__(self):
        return "ContainsPaths({})".format(self.expected_paths)


class AllScoresPositive:
    """Матчер: проверяет что все score > 0."""

    def __eq__(self, other):
        return all(r.score > 0 for r in other)

    def __repr__(self):
        return "AllScoresPositive()"


# ============================================================
# Полный цикл поиска
# ============================================================

class TestFullCycle:
    """End-to-end тесты полного цикла."""

    def test_index_search_save_load(self, sample_fs, tmp_path):
        """Построить индекс → поиск → сохранить результат → загрузить."""
        # Построить индекс
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        assert indexer.is_built

        # Поиск
        search = IndexedSearch(sample_fs, indexer)
        query = parse_query("python")
        results = search.search(query, "/")
        assert len(results) > 0

        # Сохранить результаты
        filepath = str(tmp_path / "results.json")
        data = [{"path": r.path, "name": r.name, "score": r.score} for r in results]
        save_json(data, filepath)

        # Загрузить и проверить
        loaded = load_json(filepath)
        assert len(loaded) == len(results)
        for original, saved in zip(results, loaded):
            assert original.path == saved["path"]
            assert original.score == pytest.approx(saved["score"], rel=1e-6)

    def test_index_save_load_search(self, sample_fs, tmp_path):
        """Построить → сохранить индекс → загрузить → поиск идентичен."""
        # Построить и найти
        indexer1 = FileIndexer()
        indexer1.build_index("/", sample_fs)
        search1 = IndexedSearch(sample_fs, indexer1)
        query = parse_query("python")
        results1 = search1.search(query, "/")

        # Сохранить индекс
        index_path = str(tmp_path / "index.json")
        indexer1.save_index(index_path)

        # Загрузить в новый индексатор
        indexer2 = FileIndexer()
        indexer2.load_index(index_path)
        search2 = IndexedSearch(sample_fs, indexer2)
        results2 = search2.search(query, "/")

        # Результаты идентичны
        paths1 = [r.path for r in results1]
        paths2 = [r.path for r in results2]
        assert paths1 == paths2

    def test_cache_hit_returns_same(self, sample_fs):
        """Кэш возвращает идентичный результат."""
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        search = IndexedSearch(sample_fs, indexer)
        cache = SearchCache()

        query = parse_query("python")
        results = search.search(query, "/")
        cache.put("python", results)

        cached = cache.get("python")
        assert cached == results
        assert cache.stats()["hits"] == 1
    def test_size_filter_exact_boundary(self, sample_fs):
        """M19: Фильтр size>N не должен включать файлы с размером ровно N."""
        naive = NaiveSearch(sample_fs)
        query = parse_query("python")
        results_no_filter = naive.search(query, "/")
        # Берём размер первого результата как порог
        if results_no_filter:
            boundary_size = results_no_filter[0].size
            query_with_filter = parse_query("python size>{}".format(boundary_size))
            results_filtered = naive.search(query_with_filter, "/")
            # Файл с размером ровно boundary_size НЕ должен попасть
            for r in results_filtered:
                assert r.size > boundary_size

# ============================================================
# Сравнение алгоритмов
# ============================================================

class TestAlgorithmComparison:
    """Сравнение наивного и индексного алгоритмов."""

    @pytest.mark.parametrize("query_str", [
        "python",
        "server",
        "test",
        "documentation",
    ])
    def test_same_file_set(self, sample_fs, query_str):
        """Оба алгоритма находят одинаковое множество файлов."""
        naive = NaiveSearch(sample_fs)
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        indexed = IndexedSearch(sample_fs, indexer)

        query = parse_query(query_str)
        naive_results = naive.search(query, "/")
        indexed_results = indexed.search(query, "/")

        naive_paths = set(r.path for r in naive_results)
        indexed_paths = set(r.path for r in indexed_results)
        assert naive_paths == indexed_paths

    def test_indexed_not_slower_on_repeat(self, sample_fs):
        """Индексный поиск не медленнее при повторных запросах."""
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        indexed = IndexedSearch(sample_fs, indexer)
        query = parse_query("python")

        # Первый запрос
        start = time.perf_counter()
        indexed.search(query, "/")
        first_time = time.perf_counter() - start

        # Второй запрос
        start = time.perf_counter()
        indexed.search(query, "/")
        second_time = time.perf_counter() - start

        # Второй не должен быть значительно медленнее
        assert second_time <= first_time * 10

    def test_both_empty_for_gibberish(self, sample_fs):
        """Оба возвращают пусто для бессмыслицы."""
        naive = NaiveSearch(sample_fs)
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        indexed = IndexedSearch(sample_fs, indexer)

        query = parse_query("zzzzqqqxxx")
        assert naive.search(query, "/") == []
        assert indexed.search(query, "/") == []


# ============================================================
# Кастомные матчеры в действии
# ============================================================

class TestCustomMatchers:
    """Демонстрация кастомных матчеров."""

    def test_contains_paths_matcher(self, naive):
        query = parse_query("python")
        results = naive.search(query, "/")
        # Матчер: результаты содержат app.py
        assert results == ContainsPaths(["/src/app.py"])

    def test_all_scores_positive_matcher(self, naive):
        query = parse_query("python")
        results = naive.search(query, "/")
        # Матчер: все score > 0
        assert results == AllScoresPositive()


# ============================================================
# Тесты парсера запросов
# ============================================================

class TestParser:
    """Тесты парсера поисковых запросов."""

    def test_simple_query(self):
        q = parse_query("python")
        assert q.terms == ["python"]
        assert q.operator == "AND"
        assert not q.is_empty

    def test_multi_word(self):
        q = parse_query("python test")
        assert q.terms == ["python", "test"]

    def test_and_operator(self):
        q = parse_query("python AND test")
        assert q.terms == ["python", "test"]
        assert q.operator == "AND"

    def test_or_operator(self):
        q = parse_query("python OR java")
        assert q.terms == ["python", "java"]
        assert q.operator == "OR"

    def test_not_operator(self):
        q = parse_query("python NOT java")
        assert q.terms == ["python"]
        assert q.exclude_terms == ["java"]
        assert q.operator == "NOT"

    def test_wildcard(self):
        q = parse_query("*.py")
        assert q.wildcard == "*.py"

    def test_size_filter(self):
        q = parse_query("python size>1024")
        assert q.terms == ["python"]
        assert q.size_filter == {"op": ">", "value": 1024}

    def test_date_filter(self):
        q = parse_query("python date>2025-01-01")
        assert q.terms == ["python"]
        assert q.date_filter == {"op": ">", "value": "2025-01-01"}

    def test_empty_query(self):
        q = parse_query("")
        assert q.is_empty is True

    def test_whitespace_query(self):
        q = parse_query("   ")
        assert q.is_empty is True

    def test_long_query_truncated(self):
        q = parse_query("a" * 2000)
        assert not q.is_empty


# ============================================================
# Тесты валидаторов
# ============================================================

class TestValidators:
    """Тесты валидации входных данных."""

    @pytest.mark.parametrize("query, expected_valid", [
        ("python", True),
        ("", False),
        ("   ", False),
        (None, False),
        ("a" * 1001, False),
        ("normal query", True),
    ])
    def test_validate_query(self, query, expected_valid):
        valid, msg = validate_query(query)
        assert valid == expected_valid
        if not valid:
            assert len(msg) > 0

    @pytest.mark.parametrize("path, expected_valid", [
        ("/home", True),
        ("", False),
        (None, False),
        ("/valid/path", True),
        ("path<bad", False),
    ])
    def test_validate_path(self, path, expected_valid):
        valid, msg = validate_path(path)
        assert valid == expected_valid

    def test_validate_max_results(self):
        assert validate_max_results(10) == (True, "")
        assert validate_max_results(0) == (True, "")
        valid, msg = validate_max_results(-1)
        assert valid is False

    def test_sanitize_query(self):
        assert sanitize_query("  hello   world  ") == "hello world"
        assert sanitize_query("") == ""
        assert sanitize_query("a" * 2000) == "a" * 1000
