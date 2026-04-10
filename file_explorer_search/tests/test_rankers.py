"""
Тесты TF-IDF ранжирования, кэша и индексатора.

Техника 4: Data Flow Testing — отслеживание жизненного цикла переменных.

Ключевые переменные и паттерны:
    index:   build_index(def) → search(use) → clear_index(kill)
    cache:   put(def) → get(use) → clear(kill)
    query:   parse(def) → search(use)
    results: search(def) → display/save(use)
"""

import math
import pytest

from core.ranker import (
    tokenize, remove_stop_words,
    compute_tf, compute_idf, compute_tfidf,
    rank_documents,
)
from core.indexer import FileIndexer
from core.cache import SearchCache
from core.parser import parse_query
from algorithms.naive_search import NaiveSearch
from algorithms.indexed_search import IndexedSearch
from api.mock_fs import InMemoryFileSystem
from utils.file_io import save_json, load_json, FileIOError


# ============================================================
# Data Flow: переменная index
# ============================================================

class TestIndexDataFlow:
    """Потоки данных переменной index."""

    # --- DF-01: def-use (норма) — построить, затем использовать ---
    def test_build_then_search(self, sample_fs):
        indexer = FileIndexer()
        # def: построение индекса
        indexer.build_index("/", sample_fs)
        # use: поиск по индексу
        search = IndexedSearch(sample_fs, indexer)
        query = parse_query("python")
        results = search.search(query, "/")
        assert len(results) > 0

    # --- DF-02: def-def (переопределение) — двойное построение ---
    def test_double_build(self, sample_fs):
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        stats1 = indexer.get_stats()
        # повторное def: не должно ломать состояние
        indexer.build_index("/", sample_fs)
        stats2 = indexer.get_stats()
        assert stats1["total_terms"] == stats2["total_terms"]
        assert stats1["total_docs"] == stats2["total_docs"]

    # --- DF-03: use без def — поиск без построения индекса ---
    def test_search_without_build(self, sample_fs):
        indexer = FileIndexer()
        # use без def: индекс не построен
        search = IndexedSearch(sample_fs, indexer)
        query = parse_query("python")
        results = search.search(query, "/")
        assert results == []

    # --- DF-04: def-kill-use — построить, очистить, искать ---
    def test_build_clear_search(self, sample_fs):
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        assert indexer.is_built is True
        # kill: очистка индекса
        indexer.clear_index()
        assert indexer.is_built is False
        # use после kill
        search = IndexedSearch(sample_fs, indexer)
        query = parse_query("python")
        results = search.search(query, "/")
        assert results == []

    # --- DF-05: def → save → load → use — сохранение/загрузка ---
    def test_save_load_index(self, sample_fs, tmp_path):
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        filepath = str(tmp_path / "test_index.json")
        # save
        indexer.save_index(filepath)
        # load в новый индексатор
        indexer2 = FileIndexer()
        indexer2.load_index(filepath)
        assert indexer2.is_built is True
        assert indexer2.get_stats()["total_terms"] == indexer.get_stats()["total_terms"]
        # use после load
        search = IndexedSearch(sample_fs, indexer2)
        query = parse_query("python")
        results = search.search(query, "/")
        assert len(results) > 0


# ============================================================
# Data Flow: переменная cache
# ============================================================

class TestCacheDataFlow:
    """Потоки данных переменной cache."""

    # --- DF-06: def-use (норма) — сохранить, затем получить ---
    def test_put_then_get(self, cache):
        data = [{"path": "/test.py", "score": 0.5}]
        # def
        cache.put("python", data)
        # use
        result = cache.get("python")
        assert result == data

    # --- DF-07: use без def — получить несуществующий ключ ---
    def test_get_missing_key(self, cache):
        result = cache.get("nonexistent")
        assert result is None

    # --- DF-08: def-kill-use — сохранить, очистить, получить ---
    def test_put_clear_get(self, cache):
        cache.put("python", [1, 2, 3])
        cache.clear()
        result = cache.get("python")
        assert result is None

    # --- DF-09: статистика кэша ---
    def test_cache_stats_flow(self, cache):
        cache.get("miss1")
        cache.get("miss2")
        cache.put("hit", [1])
        cache.get("hit")

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        # Матчер: pytest.approx
        assert stats["hit_rate"] == pytest.approx(1 / 3, rel=1e-2)

    # --- DF-10: LRU вытеснение ---
    def test_cache_lru_eviction(self):
        small_cache = SearchCache(max_size=2)
        small_cache.put("first", [1])
        small_cache.put("second", [2])
        small_cache.put("third", [3])
        # first должен быть вытеснен
        assert small_cache.get("first") is None
        assert small_cache.get("second") == [2]
        assert small_cache.get("third") == [3]

    # --- DF-11: нормализация ключей ---
    def test_cache_key_normalization(self, cache):
        cache.put("Python Test", [1])
        result = cache.get("python  test")
        assert result == [1]
    def test_cache_lru_order_after_access(self):
        """M12: Доступ к элементу должен обновлять его позицию в LRU."""
        small_cache = SearchCache(max_size=2)
        small_cache.put("first", [1])
        small_cache.put("second", [2])
        # Обращение к first — теперь он самый свежий
        small_cache.get("first")
        # Добавляем третий — должен вытеснить second (не first)
        small_cache.put("third", [3])
        assert small_cache.get("first") == [1]
        assert small_cache.get("second") is None
        assert small_cache.get("third") == [3]

# ============================================================
# Data Flow: переменная query
# ============================================================

class TestQueryDataFlow:
    """Потоки данных переменной query."""

    # --- DF-12: def → use — парсинг и поиск ---
    def test_query_parse_then_search(self, naive):
        # def: парсинг
        query = parse_query("python test")
        assert not query.is_empty
        # use: поиск
        results = naive.search(query, "/")
        assert len(results) > 0

    # --- DF-13: невалидный запрос ловится на этапе парсинга ---
    def test_invalid_query_parsed_as_empty(self):
        query = parse_query("")
        assert query.is_empty is True
        query2 = parse_query("   ")
        assert query2.is_empty is True


# ============================================================
# Data Flow: переменная results
# ============================================================

class TestResultsDataFlow:
    """Потоки данных переменной results."""

    # --- DF-14: def → save → load — сериализация результатов ---
    def test_results_save_load(self, naive, tmp_path):
        query = parse_query("python")
        # def
        results = naive.search(query, "/")
        assert len(results) > 0
        # save
        filepath = str(tmp_path / "results.json")
        data = [{"path": r.path, "name": r.name, "score": r.score} for r in results]
        save_json(data, filepath)
        # load
        loaded = load_json(filepath)
        assert len(loaded) == len(results)
        assert loaded[0]["path"] == results[0].path

    # --- DF-15: load несуществующий файл → исключение ---
    def test_load_nonexistent_file(self):
        # Assertion вид 5: pytest.raises
        with pytest.raises(FileIOError):
            load_json("/nonexistent/path.json")


# ============================================================
# Математическая верификация TF-IDF
# ============================================================

class TestTFIDFMath:
    """Проверка корректности вычислений TF-IDF."""

    def test_tokenize_basic(self):
        tokens = tokenize("Hello World python test")
        assert tokens == ["hello", "world", "python", "test"]

    def test_tokenize_empty(self):
        assert tokenize("") == []
        assert tokenize(None) == []

    def test_tokenize_special_chars(self):
        tokens = tokenize("hello-world! foo@bar.com")
        assert "hello" in tokens
        assert "world" in tokens

    def test_tokenize_short_words_removed(self):
        tokens = tokenize("I a am is it go do")
        # Слова короче 2 символов отбрасываются
        assert "i" not in tokens
        assert "a" not in tokens
        assert "am" in tokens
        assert "is" in tokens

    def test_remove_stop_words(self):
        tokens = ["the", "python", "and", "test", "is", "good"]
        cleaned = remove_stop_words(tokens)
        assert "python" in cleaned
        assert "test" in cleaned
        assert "good" in cleaned
        assert "the" not in cleaned
        assert "and" not in cleaned
        assert "is" not in cleaned

    def test_compute_tf(self):
        tokens = ["python", "python", "java", "python", "test"]
        tf = compute_tf("python", tokens)
        # 3 / 5 = 0.6
        assert tf == pytest.approx(0.6, rel=1e-6)

    def test_compute_tf_missing_term(self):
        tokens = ["python", "java"]
        tf = compute_tf("ruby", tokens)
        assert tf == pytest.approx(0.0, rel=1e-6)

    def test_compute_tf_empty_tokens(self):
        tf = compute_tf("python", [])
        assert tf == pytest.approx(0.0, rel=1e-6)

    def test_compute_idf(self):
        # 10 документов, слово в 2 из них
        idf = compute_idf(10, 2)
        expected = math.log(10 / 2)
        assert idf == pytest.approx(expected, rel=1e-6)

    def test_compute_idf_all_docs(self):
        # Слово во всех документах
        idf = compute_idf(10, 10)
        assert idf == pytest.approx(0.0, rel=1e-6)

    def test_compute_idf_zero_docs(self):
        idf = compute_idf(0, 0)
        assert idf == pytest.approx(0.0, rel=1e-6)

    def test_compute_tfidf(self):
        tf = 0.6
        idf = math.log(10 / 2)
        tfidf = compute_tfidf(tf, idf)
        expected = 0.6 * math.log(5)
        assert tfidf == pytest.approx(expected, rel=1e-6)

    def test_rank_documents_ordering(self):
        """Документ с большим количеством вхождений ранжируется выше."""
        index = {
            "python": {"/many.py": 5, "/few.py": 1},
            "java": {"/other.py": 3},
        }
        doc_lengths = {"/many.py": 5, "/few.py": 5, "/other.py": 5}
        ranked = rank_documents(["python"], index, doc_lengths, 3)
        assert len(ranked) == 2
        assert ranked[0][0] == "/many.py"
        assert ranked[0][1] > ranked[1][1]


    def test_rank_documents_empty_query(self):
        ranked = rank_documents([], {}, {}, 0)
        assert ranked == []

    def test_rank_documents_term_not_in_index(self):
        index = {"python": {"/a.py": 1}}
        ranked = rank_documents(["nonexistent"], index, {"/a.py": 5}, 1)
        assert ranked == []
    def test_compute_idf_zero_docs_with_term(self):
        """M05: IDF при docs_with_term=0 должен быть 0."""
        idf = compute_idf(10, 0)
        assert idf == pytest.approx(0.0, rel=1e-6)

    def test_rank_documents_multi_term_accumulation(self):
        """M08: Score должен накапливаться по нескольким термам."""
        index = {
            "python": {"/a.py": 3},
            "flask": {"/a.py": 2},
            "java": {"/b.py": 1},
        }
        doc_lengths = {"/a.py": 10, "/b.py": 10}
        # Запрос из двух слов — score должен суммироваться
        ranked_multi = rank_documents(["python", "flask"], index, doc_lengths, 3)
        ranked_single = rank_documents(["python"], index, doc_lengths, 3)
        # Score для /a.py с двумя термами должен быть больше чем с одним
        multi_score = dict(ranked_multi).get("/a.py", 0)
        single_score = dict(ranked_single).get("/a.py", 0)
        assert multi_score > single_score

# ============================================================
# Тесты индексатора
# ============================================================

class TestIndexerUnit:
    """Модульные тесты индексатора."""

    def test_build_on_empty_fs(self):
        fs = InMemoryFileSystem()
        indexer = FileIndexer()
        indexer.build_index("/", fs)
        assert indexer.is_built is True
        assert indexer.total_docs == 0
        assert len(indexer.index) == 0

    def test_build_stats(self, sample_fs):
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        stats = indexer.get_stats()
        assert stats["is_built"] is True
        assert stats["total_docs"] > 0
        assert stats["total_terms"] > 0
        assert stats["build_time"] >= 0

    def test_progress_callback(self, sample_fs):
        indexer = FileIndexer()
        progress_calls = []

        def on_progress(current, total, name):
            progress_calls.append((current, total, name))

        indexer.build_index("/", sample_fs, on_progress=on_progress)
        assert len(progress_calls) > 0
        # Последний вызов: current == total
        last = progress_calls[-1]
        assert last[0] == last[1]

    def test_clear_resets_state(self, sample_fs):
        indexer = FileIndexer()
        indexer.build_index("/", sample_fs)
        indexer.clear_index()
        stats = indexer.get_stats()
        assert stats["is_built"] is False
        assert stats["total_terms"] == 0
        assert stats["total_docs"] == 0
