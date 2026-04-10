"""
Мутационное тестирование.

Простой мутационный тестер для проверки качества тестов.
Вносит мутации в исходный код и проверяет, ловят ли тесты изменения.
"""

import subprocess
import shutil
import os
import re
import sys


# Мутационные операторы
MUTATIONS = [
    # (описание, что ищем, на что заменяем, файл, номер вхождения)

    # === core/ranker.py ===

    # M01: Замена оператора сравнения в tokenize
    {
        "id": "M01",
        "file": "core/ranker.py",
        "description": "tokenize: len(t) >= 2 -> len(t) >= 3",
        "original": "len(t) >= 2",
        "mutant": "len(t) >= 3",
        "operator": "Boundary mutation",
    },
    # M02: Замена оператора в compute_tf
    {
        "id": "M02",
        "file": "core/ranker.py",
        "description": "compute_tf: count / len(tokens) -> count * len(tokens)",
        "original": "count / len(tokens)",
        "mutant": "count * len(tokens)",
        "operator": "Arithmetic operator replacement",
    },
    # M03: Замена возвращаемого значения в compute_tf
    {
        "id": "M03",
        "file": "core/ranker.py",
        "description": "compute_tf: return 0.0 -> return 1.0 (empty tokens)",
        "original": "    if not tokens:\n        return 0.0",
        "mutant": "    if not tokens:\n        return 1.0",
        "operator": "Return value mutation",
    },
    # M04: Замена оператора в compute_idf
    {
        "id": "M04",
        "file": "core/ranker.py",
        "description": "compute_idf: total_docs / docs_with_term -> total_docs - docs_with_term",
        "original": "math.log(total_docs / docs_with_term)",
        "mutant": "math.log(total_docs - docs_with_term)",
        "operator": "Arithmetic operator replacement",
    },
    # M05: Замена условия в compute_idf
    {
        "id": "M05",
        "file": "core/ranker.py",
        "description": "compute_idf: docs_with_term <= 0 -> docs_with_term < 0",
        "original": "docs_with_term <= 0",
        "mutant": "docs_with_term < 0",
        "operator": "Relational operator replacement",
    },
    # M06: Замена оператора в compute_tfidf
    {
        "id": "M06",
        "file": "core/ranker.py",
        "description": "compute_tfidf: tf * idf -> tf + idf",
        "original": "return tf * idf",
        "mutant": "return tf + idf",
        "operator": "Arithmetic operator replacement",
    },
    # M07: Замена сортировки в rank_documents
    {
        "id": "M07",
        "file": "core/ranker.py",
        "description": "rank_documents: reverse=True -> reverse=False",
        "original": "reverse=True",
        "mutant": "reverse=False",
        "operator": "Boolean mutation",
    },
    # M08: Удаление накопления score
    {
        "id": "M08",
        "file": "core/ranker.py",
        "description": "rank_documents: scores[filepath] += tfidf -> scores[filepath] = tfidf",
        "original": "scores[filepath] += tfidf",
        "mutant": "scores[filepath] = tfidf",
        "operator": "Assignment mutation",
    },

    # === core/parser.py ===

    # M09: Замена оператора по умолчанию
    {
        "id": "M09",
        "file": "core/parser.py",
        "description": "parser: default operator AND -> OR",
        "original": '    result.operator = "AND"\n    result.terms = [t.lower() for t in tokens]',
        "mutant": '    result.operator = "OR"\n    result.terms = [t.lower() for t in tokens]',
        "operator": "Constant mutation",
    },
    # M10: Замена MAX_QUERY_LENGTH
    {
        "id": "M10",
        "file": "core/parser.py",
        "description": "parser: MAX_QUERY_LENGTH = 1000 -> MAX_QUERY_LENGTH = 0",
        "original": "MAX_QUERY_LENGTH = 1000",
        "mutant": "MAX_QUERY_LENGTH = 0",
        "operator": "Constant mutation",
    },

    # === core/cache.py ===

    # M11: Инвертирование условия кэш-попадания
    {
        "id": "M11",
        "file": "core/cache.py",
        "description": "cache.get: key in self._cache -> key not in self._cache",
        "original": "if key in self._cache:",
        "mutant": "if key not in self._cache:",
        "operator": "Negation mutation",
    },
    # M12: Удаление LRU-перемещения
    {
        "id": "M12",
        "file": "core/cache.py",
        "description": "cache.get: убрать move_to_end",
        "original": "            self._hits += 1\n            self._cache.move_to_end(key)",
        "mutant": "            self._hits += 1",
        "operator": "Statement deletion",
    },
    # M13: Замена счётчика
    {
        "id": "M13",
        "file": "core/cache.py",
        "description": "cache.get: self._hits += 1 -> self._misses += 1",
        "original": "            self._hits += 1",
        "mutant": "            self._misses += 1",
        "operator": "Variable mutation",
    },
    # M14: Замена popitem
    {
        "id": "M14",
        "file": "core/cache.py",
        "description": "cache.put: popitem(last=False) -> popitem(last=True)",
        "original": "self._cache.popitem(last=False)",
        "mutant": "self._cache.popitem(last=True)",
        "operator": "Boolean mutation",
    },

    # === algorithms/naive_search.py ===

    # M15: Замена условия score
    {
        "id": "M15",
        "file": "algorithms/naive_search.py",
        "description": "naive: score > 0 -> score >= 0",
        "original": "if score > 0:",
        "mutant": "if score >= 0:",
        "operator": "Relational operator replacement",
    },
    # M16: Замена сортировки
    {
        "id": "M16",
        "file": "algorithms/naive_search.py",
        "description": "naive: reverse=True -> reverse=False",
        "original": "results.sort(key=lambda r: r.score, reverse=True)",
        "mutant": "results.sort(key=lambda r: r.score, reverse=False)",
        "operator": "Boolean mutation",
    },
    # M17: Замена AND логики
    {
        "id": "M17",
        "file": "algorithms/naive_search.py",
        "description": "naive: any(c == 0) -> all(c == 0)",
        "original": "if any(c == 0 for c in counts.values()):",
        "mutant": "if all(c == 0 for c in counts.values()):",
        "operator": "Logic mutation",
    },

    # === core/indexer.py ===

    # M18: Замена инициализации счётчика
    {
        "id": "M18",
        "file": "core/indexer.py",
        "description": "indexer: self._is_built = True -> self._is_built = False",
        "original": "        self._is_built = True",
        "mutant": "        self._is_built = False",
        "operator": "Boolean mutation",
    },

    # === algorithms/base.py ===

    # M19: Замена оператора фильтра размера
    {
        "id": "M19",
        "file": "algorithms/base.py",
        "description": "base: r.size > value -> r.size >= value",
        "original": '            if op == ">" and r.size > value:',
        "mutant": '            if op == ">" and r.size >= value:',
        "operator": "Relational operator replacement",
    },
    # M20: Удаление обрезки результатов
    {
        "id": "M20",
        "file": "algorithms/base.py",
        "description": "base: results = results[:max_results] -> pass",
        "original": "            results = results[:max_results]",
        "mutant": "            pass",
        "operator": "Statement deletion",
    },
]


def run_tests():
    """Запустить тесты и вернуть True если все прошли."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-x", "--tb=no", "-q"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def apply_mutation(mutation):
    """Применить мутацию к файлу. Возвращает оригинальное содержимое."""
    filepath = mutation["file"]
    with open(filepath, "r", encoding="utf-8") as f:
        original_content = f.read()

    if mutation["original"] not in original_content:
        return None

    mutated = original_content.replace(
        mutation["original"], mutation["mutant"], 1
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(mutated)

    return original_content


def restore_file(filepath, original_content):
    """Восстановить файл."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(original_content)


def main():
    print()
    print("=" * 60)
    print("  Мутационное тестирование")
    print("=" * 60)
    print()

    # Проверяем что тесты проходят без мутаций
    print("  Проверка тестов без мутаций...", end=" ", flush=True)
    if not run_tests():
        print("ОШИБКА")
        print("  Тесты не проходят без мутаций. Исправьте тесты.")
        return
    print("OK")
    print()

    killed = 0
    survived = 0
    errors = 0
    total = len(MUTATIONS)

    survived_list = []
    killed_list = []

    for i, mutation in enumerate(MUTATIONS):
        mid = mutation["id"]
        desc = mutation["description"]
        print("  [{}/{}] {} - {}".format(i + 1, total, mid, desc), end=" ... ", flush=True)

        original_content = apply_mutation(mutation)

        if original_content is None:
            print("ПРОПУСК (паттерн не найден)")
            errors += 1
            continue

        try:
            tests_pass = run_tests()
        except Exception as e:
            print("ОШИБКА ({})".format(e))
            errors += 1
            restore_file(mutation["file"], original_content)
            continue

        restore_file(mutation["file"], original_content)

        if tests_pass:
            print("ВЫЖИЛ")
            survived += 1
            survived_list.append(mutation)
        else:
            print("УБИТ")
            killed += 1
            killed_list.append(mutation)

    # Итоги
    print()
    print("=" * 60)
    print("  Результаты мутационного тестирования")
    print("=" * 60)
    print()
    print("  Всего мутантов: {}".format(total))
    print("  Убито:          {} ({:.0f}%)".format(killed, killed / max(total - errors, 1) * 100))
    print("  Выжило:         {} ({:.0f}%)".format(survived, survived / max(total - errors, 1) * 100))
    print("  Ошибки/пропуск: {}".format(errors))
    print()

    applicable = killed + survived
    if applicable > 0:
        msi = killed / applicable * 100
        print("  MSI (Mutation Score Indicator): {:.1f}%".format(msi))
    print()

    if survived_list:
        print("  Выжившие мутанты (тесты НЕ поймали изменение):")
        print("  " + "-" * 50)
        for m in survived_list:
            print("    {} [{}]".format(m["id"], m["operator"]))
            print("      {}".format(m["description"]))
            print("      Файл: {}".format(m["file"]))
            print()

    if killed_list:
        print("  Убитые мутанты (тесты поймали изменение):")
        print("  " + "-" * 50)
        for m in killed_list:
            print("    {} [{}]".format(m["id"], m["operator"]))
            print("      {}".format(m["description"]))
        print()

    # Сохранение отчёта
    report = {
        "total": total,
        "killed": killed,
        "survived": survived,
        "errors": errors,
        "msi": round(killed / max(applicable, 1) * 100, 1),
        "survived_mutations": [
            {"id": m["id"], "description": m["description"],
             "operator": m["operator"], "file": m["file"]}
            for m in survived_list
        ],
        "killed_mutations": [
            {"id": m["id"], "description": m["description"],
             "operator": m["operator"], "file": m["file"]}
            for m in killed_list
        ],
    }

    from utils.file_io import save_json
    try:
        save_json(report, "results/mutation_report.json")
        print("  Отчёт сохранён: results/mutation_report.json")
    except Exception:
        pass

    print()


if __name__ == "__main__":
    main()
