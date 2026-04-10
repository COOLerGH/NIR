"""Общие фикстуры и шаги для BDD-тестов."""

import pytest
from pytest_bdd import given, when, then, parsers

from api.mock_fs import InMemoryFileSystem
from core.parser import parse_query
from core.indexer import FileIndexer
from core.cache import SearchCache
from algorithms.naive_search import NaiveSearch
from algorithms.indexed_search import IndexedSearch


@pytest.fixture
def fs():
    """Пустая файловая система."""
    return InMemoryFileSystem()


@pytest.fixture
def indexer():
    """Чистый индексатор."""
    return FileIndexer()


@pytest.fixture
def cache():
    """Кэш по умолчанию (размер 100)."""
    return SearchCache()


@pytest.fixture
def search_context():
    """Общий контекст для передачи данных между шагами."""
    return {
        "fs": None,
        "indexer": None,
        "naive": None,
        "indexed": None,
        "query": None,
        "naive_results": None,
        "indexed_results": None,
        "naive_time": 0.0,
        "indexed_time": 0.0,
        "cache": None,
        "cache_result": None,
    }


# --- Общие шаги Given ---

@given("создана файловая система с файлами:", target_fixture="search_context")
def fs_with_files(search_context, datatable):
    """Создать ФС из Data Table (столбцы: путь, содержимое)."""
    fs = InMemoryFileSystem()
    for row in datatable:
        fs.add_file(row["путь"], row["содержимое"])
    search_context["fs"] = fs
    search_context["naive"] = NaiveSearch(fs)
    return search_context


@given("индекс построен для файловой системы", target_fixture="search_context")
def index_built(search_context):
    """Построить индекс для текущей ФС."""
    indexer = FileIndexer()
    indexer.build_index("/", search_context["fs"])
    search_context["indexer"] = indexer
    search_context["indexed"] = IndexedSearch(search_context["fs"], indexer)
    return search_context
