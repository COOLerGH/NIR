"""
Общие фикстуры для тестов.
"""

import pytest
from api.mock_fs import InMemoryFileSystem
from algorithms.naive_search import NaiveSearch
from algorithms.indexed_search import IndexedSearch
from core.indexer import FileIndexer
from core.cache import SearchCache


@pytest.fixture
def sample_fs():
    """Файловая система с тестовыми данными."""
    fs = InMemoryFileSystem()

    fs.add_directory("/docs")
    fs.add_directory("/src")
    fs.add_directory("/src/utils")

    fs.add_file(
        "/src/app.py",
        "python flask web application server routing",
        modified_date="2025-03-15",
    )
    fs.add_file(
        "/src/test_app.py",
        "python pytest test automation unit testing framework",
        modified_date="2025-03-16",
    )
    fs.add_file(
        "/src/utils/helpers.py",
        "python utility helper functions data processing",
        modified_date="2025-02-10",
    )
    fs.add_file(
        "/src/data.csv",
        "name age city alice bob charlie",
        modified_date="2025-01-05",
    )
    fs.add_file(
        "/docs/readme.txt",
        "project documentation guide installation python overview",
        modified_date="2025-02-20",
    )
    fs.add_file(
        "/docs/api.txt",
        "rest api endpoints methods authentication server",
        modified_date="2025-03-01",
    )
    fs.add_file(
        "/docs/changelog.md",
        "changelog version release bug fixes improvements update",
        modified_date="2025-04-10",
    )

    return fs


@pytest.fixture
def empty_fs():
    """Пустая файловая система."""
    return InMemoryFileSystem()


@pytest.fixture
def naive(sample_fs):
    """Наивный алгоритм с тестовой ФС."""
    return NaiveSearch(sample_fs)


@pytest.fixture
def indexer(sample_fs):
    """Построенный индексатор."""
    idx = FileIndexer()
    idx.build_index("/", sample_fs)
    return idx


@pytest.fixture
def indexed(sample_fs, indexer):
    """Индексный алгоритм с построенным индексом."""
    return IndexedSearch(sample_fs, indexer)


@pytest.fixture
def cache():
    """Чистый кэш."""
    return SearchCache(max_size=10)
