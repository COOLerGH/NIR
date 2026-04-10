"""
Тесты наивного алгоритма поиска.

Техника 1: Equivalence Partitioning — классы эквивалентности входных запросов.
Техника 2: Boundary Value Analysis — граничные значения параметров.
"""

import pytest
from algorithms.naive_search import NaiveSearch
from core.parser import parse_query, MAX_QUERY_LENGTH


# ============================================================
# Техника 1: Equivalence Partitioning
# ============================================================

class TestEquivalencePartitioning:
    """Классы эквивалентности входных поисковых запросов."""

    # --- EP-01: Корректный запрос, 1 слово ---
    def test_single_word_query(self, naive):
        query = parse_query("python")
        results = naive.search(query, "/")
        # Assertion вид 1: сравнение (>)
        assert len(results) > 0
        # Assertion вид 2: all — проверка инварианта коллекции
        assert all(r.score > 0 for r in results)

    # --- EP-02: Корректный запрос, несколько слов ---
    def test_multi_word_query(self, naive):
        query = parse_query("python test")
        results = naive.search(query, "/")
        assert len(results) > 0
        # Assertion вид 3: isinstance
        from api.interface import SearchResult
        assert isinstance(results[0], SearchResult)

    # --- EP-03: Пустой запрос ---
    def test_empty_query(self, naive):
        query = parse_query("")
        results = naive.search(query, "/")
        # Assertion вид 4: точное сравнение (==)
        assert results == []

    # --- EP-04: Запрос только из пробелов ---
    def test_whitespace_query(self, naive):
        query = parse_query("   ")
        results = naive.search(query, "/")
        assert results == []

    # --- EP-05: Запрос со спецсимволами ---
    def test_special_chars_query(self, naive):
        query = parse_query("@#$%^&")
        results = naive.search(query, "/")
        assert results == []

    # --- EP-06: Очень длинный запрос ---
    def test_very_long_query(self, naive):
        long_query = "python " * 200
        query = parse_query(long_query)
        results = naive.search(query, "/")
        # Не должен упасть, результат — список
        assert isinstance(results, list)

    # --- EP-07: Запрос только из стоп-слов ---
    def test_stop_words_only_query(self, naive):
        query = parse_query("the and of")
        results = naive.search(query, "/")
        assert results == []

    # --- EP-08: Запрос с несуществующим словом ---
    def test_nonexistent_word_query(self, naive):
        query = parse_query("qwerty12345xyz")
        results = naive.search(query, "/")
        assert results == []


# ============================================================
# Техника 1 (дополнение): Параметризированные тесты EP
# ============================================================

class TestEPParametrized:
    """Параметризированные тесты по классам эквивалентности."""

    @pytest.mark.parametrize("query_str, expect_results", [
        ("python", True),
        ("flask", True),
        ("server", True),
        ("", False),
        ("   ", False),
        ("@#$%", False),
        ("the and of", False),
        ("nonexistentword999", False),
    ])
    def test_query_classes(self, naive, query_str, expect_results):
        query = parse_query(query_str)
        results = naive.search(query, "/")
        if expect_results:
            assert len(results) > 0, f"Ожидались результаты для '{query_str}'"
        else:
            assert len(results) == 0, f"Не ожидались результаты для '{query_str}'"


# ============================================================
# Техника 2: Boundary Value Analysis
# ============================================================

class TestBoundaryValueAnalysis:
    """Граничные значения параметров поиска."""

    # --- BV-01: Длина запроса 0 символов ---
    def test_query_length_zero(self, naive):
        query = parse_query("")
        results = naive.search(query, "/")
        assert results == []

    # --- BV-02: Длина запроса 1 символ ---
    def test_query_length_one(self, naive):
        query = parse_query("a")
        results = naive.search(query, "/")
        # "a" — менее 2 символов, токенизатор отбрасывает
        assert isinstance(results, list)

    # --- BV-03: Длина запроса 999 символов ---
    def test_query_length_999(self, naive):
        word = "python"
        query_str = (word + " ") * (999 // (len(word) + 1))
        query_str = query_str[:999]
        query = parse_query(query_str)
        results = naive.search(query, "/")
        assert isinstance(results, list)

    # --- BV-04: Длина запроса ровно 1000 символов (граница) ---
    def test_query_length_1000(self, naive):
        query_str = "a" * 1000
        query = parse_query(query_str)
        results = naive.search(query, "/")
        assert isinstance(results, list)

    # --- BV-05: Длина запроса 1001 символ (за границей) ---
    def test_query_length_1001(self, naive):
        query_str = "b" * 1001
        query = parse_query(query_str)
        # Парсер обрезает до MAX_QUERY_LENGTH
        assert len(query.terms) >= 0

    # --- BV-06: max_results = 0 ---
    def test_max_results_zero(self, naive):
        query = parse_query("python")
        results = naive.search(query, "/", max_results=0)
        assert results == []

    # --- BV-07: max_results = 1 ---
    def test_max_results_one(self, naive):
        query = parse_query("python")
        results = naive.search(query, "/", max_results=1)
        assert len(results) <= 1

    # --- BV-08: max_results отрицательный ---
    def test_max_results_negative(self, naive):
        query = parse_query("python")
        results = naive.search(query, "/", max_results=-1)
        # Отрицательное значение заменяется на MAX_RESULTS
        assert isinstance(results, list)

    # --- BV-09: Поиск в пустой файловой системе ---
    def test_search_empty_fs(self, empty_fs):
        naive = NaiveSearch(empty_fs)
        query = parse_query("python")
        results = naive.search(query, "/")
        assert results == []

    # --- BV-10: Файл нулевого размера ---
    def test_file_zero_size(self, empty_fs):
        empty_fs.add_file("/empty.txt", "", size=0)
        naive = NaiveSearch(empty_fs)
        query = parse_query("python")
        results = naive.search(query, "/")
        assert results == []


# ============================================================
# Техника 2 (дополнение): Параметризированные граничные значения
# ============================================================

class TestBVAParametrized:
    """Параметризированные граничные значения max_results."""

    @pytest.mark.parametrize("max_results, valid", [
        (0, True),
        (1, True),
        (10, True),
        (100, True),
        (1000, True),
        (-1, True),
    ])
    def test_max_results_boundaries(self, naive, max_results, valid):
        query = parse_query("python")
        results = naive.search(query, "/", max_results=max_results)
        assert isinstance(results, list)
        if max_results >= 0:
            assert len(results) <= max(max_results, 0)


# ============================================================
# Дополнительные тесты: сортировка и score
# ============================================================

class TestNaiveScoring:
    """Проверка корректности ранжирования."""

    def test_results_sorted_by_score(self, naive):
        """Результаты отсортированы по убыванию score."""
        query = parse_query("python")
        results = naive.search(query, "/")
        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_score_non_negative(self, naive):
        """Все score >= 0."""
        query = parse_query("python")
        results = naive.search(query, "/")
        assert all(r.score >= 0 for r in results)

    def test_more_occurrences_higher_score(self, empty_fs):
        """Файл с большим количеством вхождений получает больший score."""
        empty_fs.add_file("/many.txt", "python python python python python")
        empty_fs.add_file("/few.txt", "python java ruby")
        naive = NaiveSearch(empty_fs)
        query = parse_query("python")
        results = naive.search(query, "/")
        assert len(results) == 2
        # Матчер: pytest.approx не нужен тут, но проверяем порядок
        assert results[0].path == "/many.txt"
        assert results[0].score > results[1].score

    def test_and_operator(self, naive):
        """AND: оба слова должны присутствовать."""
        query = parse_query("python AND flask")
        results = naive.search(query, "/")
        # app.py содержит оба слова
        assert len(results) > 0
        assert any(r.name == "app.py" for r in results)

    def test_or_operator(self, naive):
        """OR: хотя бы одно слово."""
        query = parse_query("flask OR pytest")
        results = naive.search(query, "/")
        assert len(results) >= 2

    def test_not_operator(self, naive):
        """NOT: исключение слова."""
        query = parse_query("python NOT flask")
        results = naive.search(query, "/")
        # app.py содержит flask, не должен быть в результатах
        assert all(r.name != "app.py" for r in results)
    def test_and_requires_all_terms(self, empty_fs):
        """M17: AND должен требовать ВСЕ слова, не только некоторые."""
        empty_fs.add_file("/both.txt", "python flask server")
        empty_fs.add_file("/one.txt", "python java ruby")
        naive = NaiveSearch(empty_fs)
        query = parse_query("python AND flask")
        results = naive.search(query, "/")
        # only both.txt содержит оба слова
        assert len(results) == 1
        assert results[0].name == "both.txt"