"""BDD-тесты для сравнения алгоритмов и нагрузочного тестирования."""

import time
import random
import pytest
from pytest_bdd import scenario, given, when, then, parsers

from api.mock_fs import InMemoryFileSystem
from core.parser import parse_query
from core.indexer import FileIndexer
from algorithms.naive_search import NaiveSearch
from algorithms.indexed_search import IndexedSearch


# --- Словарь для генерации ---

WORD_POOL = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho",
    "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega", "apple",
    "banana", "cherry", "date", "elder", "fig", "grape", "honey", "iris",
    "jasmine", "kiwi", "lemon", "mango", "nectar", "olive", "peach",
    "quince", "rose", "sage", "tulip", "umbra", "violet", "willow",
    "xenon", "yarrow", "zinnia", "abstract", "binary", "compile",
    "debug", "execute", "function", "global", "handle", "import",
    "join", "kernel", "library", "module", "network", "object",
    "process", "query", "runtime", "stack", "thread", "update",
    "value", "widget", "xml", "yield", "zero", "access", "buffer",
    "cache", "driver", "engine", "format", "gateway", "hash",
    "index", "journal", "key", "loader", "mapper", "node", "output",
    "parser", "queue", "reader", "schema", "table", "unit", "vector",
    "worker", "proxy", "scope", "token",
]

TARGET_WORDS = ["python", "search", "algorithm", "test", "data"]
TARGET_PROBABILITY = 0.3
SEED = 42


# --- Утилита ---

def parse_datatable(datatable):
    """Преобразовать Data Table в список словарей."""
    headers = datatable[0]
    rows = []
    for row in datatable[1:]:
        rows.append(dict(zip(headers, row)))
    return rows


def generate_dataset(num_files, tokens_per_file, seed=SEED):
    """Сгенерировать InMemoryFileSystem."""
    rng = random.Random(seed)
    fs = InMemoryFileSystem()

    for i in range(num_files):
        words = []
        for _ in range(tokens_per_file):
            if rng.random() < TARGET_PROBABILITY:
                words.append(rng.choice(TARGET_WORDS))
            else:
                words.append(rng.choice(WORD_POOL))
        content = " ".join(words)
        fs.add_file(f"/gen/file_{i:06d}.txt", content)

    return fs


# --- Сценарии ---

@scenario(
    "../../features/algorithm_comparison.feature",
    "Оба алгоритма возвращают одинаковые результаты",
)
def test_same_results():
    pass


@scenario(
    "../../features/algorithm_comparison.feature",
    "Нагрузочное тестирование",
)
def test_load():
    pass


# --- Фикстура контекста ---

@pytest.fixture
def ctx():
    return {
        "fs": None,
        "indexer": None,
        "naive": None,
        "indexed": None,
        "naive_results": None,
        "indexed_results": None,
        "naive_time": 0.0,
        "indexed_time": 0.0,
    }


# --- Given ---

@given("создана файловая система с файлами:", target_fixture="ctx")
def create_fs(ctx, datatable):
    fs = InMemoryFileSystem()
    for row in parse_datatable(datatable):
        fs.add_file(row["путь"], row["содержимое"])
    ctx = {
        "fs": fs, "indexer": None, "naive": NaiveSearch(fs),
        "indexed": None, "naive_results": None,
        "indexed_results": None, "naive_time": 0.0, "indexed_time": 0.0,
    }
    return ctx


@given("индекс построен для файловой системы")
def build_index(ctx):
    indexer = FileIndexer()
    indexer.build_index("/", ctx["fs"])
    ctx["indexer"] = indexer
    ctx["indexed"] = IndexedSearch(ctx["fs"], indexer)


@given(
    parsers.parse('сгенерирована коллекция типа "{typ}" размером {num:d} файлов'),
    target_fixture="ctx",
)
def generate_collection(ctx, typ, num):
    ctx = {
        "fs": None, "indexer": None, "naive": None,
        "indexed": None, "naive_results": None,
        "indexed_results": None, "naive_time": 0.0, "indexed_time": 0.0,
        "_num_files": num, "_type": typ,
    }
    return ctx


@given(parsers.parse("каждый файл содержит примерно {tokens:d} токенов"))
def set_tokens_and_generate(ctx, tokens):
    fs = generate_dataset(ctx["_num_files"], tokens)
    ctx["fs"] = fs
    ctx["naive"] = NaiveSearch(fs)


@given("индекс построен для сгенерированной коллекции")
def build_generated_index(ctx):
    indexer = FileIndexer()
    indexer.build_index("/", ctx["fs"])
    ctx["indexer"] = indexer
    ctx["indexed"] = IndexedSearch(ctx["fs"], indexer)


# --- When ---

@when(parsers.parse('выполнен поиск наивным алгоритмом по запросу "{query}"'))
def naive_search(ctx, query):
    parsed = parse_query(query)
    start = time.perf_counter()
    ctx["naive_results"] = ctx["naive"].search(parsed, "/")
    ctx["naive_time"] = time.perf_counter() - start


@when("замерено время наивного поиска")
def record_naive_time(ctx):
    print(f"\n  Наивный поиск: {ctx['naive_time']:.4f} сек")


@when(parsers.parse('выполнен поиск индексным алгоритмом по запросу "{query}"'))
def indexed_search(ctx, query):
    parsed = parse_query(query)
    start = time.perf_counter()
    ctx["indexed_results"] = ctx["indexed"].search(parsed, "/")
    ctx["indexed_time"] = time.perf_counter() - start


@when("замерено время индексного поиска")
def record_indexed_time(ctx):
    print(f"  Индексный поиск: {ctx['indexed_time']:.4f} сек")
    if ctx["indexed_time"] > 0:
        print(f"  Ускорение: {ctx['naive_time'] / ctx['indexed_time']:.1f}x")


# --- Then ---

@then("оба алгоритма нашли одинаковое множество файлов")
def check_same_files(ctx):
    naive_paths = {r.path for r in ctx["naive_results"]}
    indexed_paths = {r.path for r in ctx["indexed_results"]}
    assert naive_paths == indexed_paths


@then("индексный поиск быстрее наивного")
def check_indexed_faster(ctx):
    assert ctx["indexed_time"] < ctx["naive_time"]
