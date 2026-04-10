"""
Запуск нагрузочных экспериментов.

1. Предварительный эксперимент — поиск максимальных границ
2. Профилирование — замеры составных частей
3. Основной эксперимент — сравнение на 4 датасетах
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.mock_fs import InMemoryFileSystem
from core.parser import parse_query
from core.indexer import FileIndexer
from algorithms.naive_search import NaiveSearch
from algorithms.indexed_search import IndexedSearch
from benchmarks.generate_datasets import (
    generate_dataset, load_dataset_to_fs, load_dataset,
    DATASETS, TARGET_WORDS,
)


REPEATS = 5
QUERY_WORD = "test"
RESULTS_DIR = "results"


def measure_search(algorithm, query_str, root="/", repeats=REPEATS):
    """Замерить среднее время поиска."""
    parsed = parse_query(query_str)
    times = []
    result = None

    for _ in range(repeats):
        start = time.perf_counter()
        result = algorithm.search(parsed, root)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "std": (sum((t - sum(times)/len(times))**2 for t in times) / len(times)) ** 0.5,
        "times": times,
        "num_results": len(result) if result else 0,
    }


def measure_indexing(fs, root="/"):
    """Замерить время построения индекса."""
    indexer = FileIndexer()
    start = time.perf_counter()
    indexer.build_index(root, fs)
    elapsed = time.perf_counter() - start

    return {
        "time": elapsed,
        "total_terms": len(indexer.index),
        "total_docs": indexer.total_docs,
        "indexer": indexer,
    }


def measure_memory(indexer):
    """Оценить потребление памяти индексом."""
    index_size = sys.getsizeof(indexer.index)
    for term, postings in indexer.index.items():
        index_size += sys.getsizeof(term)
        index_size += sys.getsizeof(postings)

    doc_lengths_size = sys.getsizeof(indexer.doc_lengths)
    for path, length in indexer.doc_lengths.items():
        doc_lengths_size += sys.getsizeof(path)
        doc_lengths_size += sys.getsizeof(length)

    return {
        "index_bytes": index_size,
        "doc_lengths_bytes": doc_lengths_size,
        "total_bytes": index_size + doc_lengths_size,
        "total_mb": (index_size + doc_lengths_size) / (1024 * 1024),
    }


def run_preliminary_experiment():
    """Предварительный эксперимент — поиск границ производительности."""
    print("=" * 60)
    print("ПРЕДВАРИТЕЛЬНЫЙ ЭКСПЕРИМЕНТ")
    print("=" * 60)

    results = []

    # Тип A: увеличиваем количество коротких файлов
    a_sizes = [100, 500, 1000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]
    print("\nТип A (50 токенов/файл):")
    print(f"{'Файлов':>10} {'Индексация':>12} {'Наивный':>12} {'Индексный':>12}")
    print("-" * 50)

    for num in a_sizes:
        files = generate_dataset("A_prelim", num, 50)
        fs = load_dataset_to_fs(files)

        idx_result = measure_indexing(fs)
        indexer = idx_result["indexer"]

        naive = NaiveSearch(fs)
        indexed = IndexedSearch(fs, indexer)

        naive_result = measure_search(naive, QUERY_WORD)
        indexed_result = measure_search(indexed, QUERY_WORD)

        print(f"{num:>10} {idx_result['time']:>11.4f}с "
              f"{naive_result['mean']:>11.4f}с {indexed_result['mean']:>11.4f}с")

        results.append({
            "type": "A", "num_files": num, "tokens_per_file": 50,
            "index_time": idx_result["time"],
            "naive_mean": naive_result["mean"],
            "indexed_mean": indexed_result["mean"],
            "naive_times": naive_result["times"],
            "indexed_times": indexed_result["times"],
        })

        # Остановка если наивный > 2 мин
        if naive_result["mean"] > 120:
            print(f"  -> Достигнут порог 2 мин для типа A: {num} файлов")
            break

    # Тип B: увеличиваем количество длинных файлов
    b_sizes = [20, 50, 100, 500, 1000, 2000, 5000, 10000, 20000, 50000]
    print(f"\nТип B (2500 токенов/файл):")
    print(f"{'Файлов':>10} {'Индексация':>12} {'Наивный':>12} {'Индексный':>12}")
    print("-" * 50)

    for num in b_sizes:
        files = generate_dataset("B_prelim", num, 2500)
        fs = load_dataset_to_fs(files)

        idx_result = measure_indexing(fs)
        indexer = idx_result["indexer"]

        naive = NaiveSearch(fs)
        indexed = IndexedSearch(fs, indexer)

        naive_result = measure_search(naive, QUERY_WORD)
        indexed_result = measure_search(indexed, QUERY_WORD)

        print(f"{num:>10} {idx_result['time']:>11.4f}с "
              f"{naive_result['mean']:>11.4f}с {indexed_result['mean']:>11.4f}с")

        results.append({
            "type": "B", "num_files": num, "tokens_per_file": 2500,
            "index_time": idx_result["time"],
            "naive_mean": naive_result["mean"],
            "indexed_mean": indexed_result["mean"],
            "naive_times": naive_result["times"],
            "indexed_times": indexed_result["times"],
        })

        if naive_result["mean"] > 120:
            print(f"  -> Достигнут порог 2 мин для типа B: {num} файлов")
            break

    return results


def run_main_experiment():
    """Основной эксперимент — профилирование на 4 датасетах."""
    print("\n" + "=" * 60)
    print("ОСНОВНОЙ ЭКСПЕРИМЕНТ")
    print("=" * 60)

    results = {}

    for name, params in DATASETS.items():
        print(f"\nДатасет: {name} ({params['num_files']} файлов, "
              f"{params['tokens_per_file']} токенов/файл)")
        print("-" * 40)

        # Генерация
        gen_start = time.perf_counter()
        files = generate_dataset(name, **params)
        fs = load_dataset_to_fs(files)
        gen_time = time.perf_counter() - gen_start
        print(f"  Генерация: {gen_time:.4f} сек")

        # Индексация
        idx_result = measure_indexing(fs)
        indexer = idx_result["indexer"]
        print(f"  Индексация: {idx_result['time']:.4f} сек "
              f"({idx_result['total_terms']} термов)")

        # Память
        mem = measure_memory(indexer)
        print(f"  Память индекса: {mem['total_mb']:.2f} МБ")

        # Наивный поиск
        naive = NaiveSearch(fs)
        naive_result = measure_search(naive, QUERY_WORD)
        print(f"  Наивный поиск: {naive_result['mean']:.4f} сек "
              f"(±{naive_result['std']:.4f}), {naive_result['num_results']} рез.")

        # Индексный поиск
        indexed = IndexedSearch(fs, indexer)
        indexed_result = measure_search(indexed, QUERY_WORD)
        print(f"  Индексный поиск: {indexed_result['mean']:.4f} сек "
              f"(±{indexed_result['std']:.4f}), {indexed_result['num_results']} рез.")

        # Ускорение
        if indexed_result["mean"] > 0:
            speedup = naive_result["mean"] / indexed_result["mean"]
            print(f"  Ускорение: {speedup:.1f}x")

        results[name] = {
            "params": params,
            "generation_time": gen_time,
            "index_time": idx_result["time"],
            "index_terms": idx_result["total_terms"],
            "index_docs": idx_result["total_docs"],
            "memory": mem,
            "naive": naive_result,
            "indexed": indexed_result,
        }

    return results


def save_results(preliminary, main_results):
    """Сохранить все результаты в JSON."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    data = {
        "preliminary": preliminary,
        "main": main_results,
    }

    filepath = os.path.join(RESULTS_DIR, "benchmark_results.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nРезультаты сохранены: {filepath}")


if __name__ == "__main__":
    prelim = run_preliminary_experiment()
    main = run_main_experiment()
    save_results(prelim, main)
