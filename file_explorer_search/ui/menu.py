"""
Главное меню приложения.

10 опций, обработка ввода, маршрутизация к функциям поиска,
индексации, анализа и сравнения алгоритмов.
"""

import time
from typing import Optional
from fnmatch import fnmatch

from api.interface import FileSystemAPI, SearchResult
from algorithms.naive_search import NaiveSearch
from algorithms.indexed_search import IndexedSearch
from core.indexer import FileIndexer
from core.cache import SearchCache
from core.parser import parse_query
from core.ranker import tokenize, remove_stop_words
from utils.validators import validate_query, sanitize_query
from utils.file_io import load_json, save_json, FileIOError
from ui.display import (
    print_header, print_menu, print_results, print_table,
    print_comparison, print_stats, print_progress,
    print_recommendation, print_error, print_success, print_colored,
    _format_size,
)


MENU_OPTIONS = [
    "Простой поиск",
    "Расширенный поиск (AND/OR/NOT, фильтры)",
    "Поиск по маске (дикий символ)",
    "Быстрый поиск (по индексу)",
    "Анализ файлов",
    "Сравнение алгоритмов",
    "Настройки путей",
    "Управление индексом",
    "Статистика работы",
    "Выход",
]

HELP_TEXTS = {
    1: "Поиск файлов по одному ключевому слову. Используется текущий алгоритм.",
    2: "Поиск с операторами: python AND test, python OR java, python NOT java. "
       "Фильтры: size>1024, date>2025-01-01.",
    3: "Поиск по маске имени файла: *.txt, data?.csv.",
    4: "Поиск по предварительно построенному индексу. Быстрее наивного.",
    5: "Топ-10 файлов по размеру, статистика по расширениям.",
    6: "Запуск одного запроса двумя алгоритмами, сравнение времени.",
    7: "Изменить корневую папку для поиска.",
    8: "Построить, сохранить, загрузить или очистить индекс.",
    9: "Размер индекса, количество файлов, hit rate кэша.",
    10: "Завершить работу приложения.",
}


class MainMenu:
    """Главное меню приложения."""

    def __init__(self, api: FileSystemAPI):
        self.api = api
        self.indexer = FileIndexer()
        self.cache = SearchCache()
        self.naive = NaiveSearch(api)
        self.indexed = IndexedSearch(api, self.indexer)
        self.root_path = ""
        self.search_count = 0
        self.total_search_time = 0.0

    def run(self) -> None:
        """Главный цикл."""
        print_header("Интеллектуальный поиск файлов")
        while True:
            print_menu(MENU_OPTIONS)
            choice = self._get_choice(len(MENU_OPTIONS))
            if choice is None:
                continue
            if choice == 10:
                self._exit()
                break
            self._dispatch(choice)

    def _get_choice(self, max_opt: int) -> Optional[int]:
        """Получить выбор пользователя."""
        raw = input("  Выберите опцию (help — справка): ").strip()
        if raw.lower() == "help":
            self._show_all_help()
            return None
        if raw.lower().startswith("help "):
            try:
                num = int(raw.split()[1])
                self._show_help(num)
            except (ValueError, IndexError):
                print_error("Формат: help <номер>")
            return None
        try:
            choice = int(raw)
            if 1 <= choice <= max_opt:
                return choice
            print_error(f"Введите число от 1 до {max_opt}")
        except ValueError:
            print_error("Введите число")
        return None

    def _dispatch(self, choice: int) -> None:
        """Маршрутизация к обработчику."""
        handlers = {
            1: self._simple_search,
            2: self._advanced_search,
            3: self._wildcard_search,
            4: self._fast_search,
            5: self._analyze_files,
            6: self._compare_algorithms,
            7: self._settings,
            8: self._manage_index,
            9: self._show_stats,
        }
        handler = handlers.get(choice)
        if handler:
            handler()

    # --- Опция 1: Простой поиск ---
    def _simple_search(self) -> None:
        print_header("Простой поиск")
        raw = input("  Введите ключевое слово: ").strip()
        valid, msg = validate_query(raw)
        if not valid:
            print_error(msg)
            return
        query = parse_query(sanitize_query(raw))
        start = time.perf_counter()
        results = self.naive.search(query, self.root_path)
        elapsed = time.perf_counter() - start
        self._record_search(elapsed)
        print_results(results)
        print_colored(f"  Время: {elapsed:.4f} сек", "cyan")
        if not self.indexer.is_built:
            print_recommendation("Постройте индекс (опция 8) для ускорения поиска.")

    # --- Опция 2: Расширенный поиск ---
    def _advanced_search(self) -> None:
        print_header("Расширенный поиск")
        print_colored("  Синтаксис: python AND test | python OR java | python NOT java", "cyan")
        print_colored("  Фильтры: size>1024  date>2025-01-01", "cyan")
        raw = input("  Запрос: ").strip()
        valid, msg = validate_query(raw)
        if not valid:
            print_error(msg)
            return
        query = parse_query(sanitize_query(raw))
        algorithm = self.indexed if self.indexer.is_built else self.naive
        start = time.perf_counter()
        results = algorithm.search(query, self.root_path)
        elapsed = time.perf_counter() - start
        self._record_search(elapsed)
        print_results(results)
        print_colored(f"  Время: {elapsed:.4f} сек", "cyan")

    # --- Опция 3: Поиск по маске ---
    def _wildcard_search(self) -> None:
        print_header("Поиск по маске")
        pattern = input("  Маска (например *.txt, data?.csv): ").strip()
        if not pattern:
            print_error("Маска не может быть пустой")
            return
        files = self.api.walk(self.root_path)
        matched = [f for f in files if fnmatch(f.name, pattern)]
        if not matched:
            print_colored("  Ничего не найдено.", "yellow")
            return
        headers = ["#", "Файл", "Размер", "Дата"]
        rows = []
        for i, f in enumerate(matched, 1):
            rows.append([str(i), f.name, str(f.size), f.modified_date])
        print_table(headers, rows)
        print_colored(f"  Найдено: {len(matched)}", "green")

    # --- Опция 4: Быстрый поиск ---
    def _fast_search(self) -> None:
        print_header("Быстрый поиск (по индексу)")
        if not self.indexer.is_built:
            print_error("Индекс не построен. Используйте опцию 8.")
            print_recommendation("Постройте индекс для использования быстрого поиска.")
            return
        raw = input("  Запрос: ").strip()
        valid, msg = validate_query(raw)
        if not valid:
            print_error(msg)
            return
        sanitized = sanitize_query(raw)
        cached = self.cache.get(sanitized)
        if cached is not None:
            print_colored("  (результат из кэша)", "cyan")
            print_results(cached)
            return
        query = parse_query(sanitized)
        start = time.perf_counter()
        results = self.indexed.search(query, self.root_path)
        elapsed = time.perf_counter() - start
        self._record_search(elapsed)
        self.cache.put(sanitized, results)
        print_results(results)
        print_colored(f"  Время: {elapsed:.4f} сек", "cyan")

    # --- Опция 5: Анализ файлов ---
    def _analyze_files(self) -> None:
        print_header("Анализ файлов")
        files = self.api.walk(self.root_path)
        if not files:
            print_colored("  Файлы не найдены.", "yellow")
            return
        # Топ-10 по размеру
        by_size = sorted(files, key=lambda f: f.size, reverse=True)[:10]
        print_colored("\n  Топ-10 по размеру:", "green")
        headers = ["#", "Файл", "Размер"]
        rows = [[str(i), f.name, _format_size(f.size)] for i, f in enumerate(by_size, 1)]
        print_table(headers, rows)
        # Статистика по расширениям
        ext_stats = {}
        for f in files:
            ext = f.extension if f.extension else "(без расширения)"
            if ext not in ext_stats:
                ext_stats[ext] = {"count": 0, "total_size": 0}
            ext_stats[ext]["count"] += 1
            ext_stats[ext]["total_size"] += f.size
        print_colored("\n  Статистика по расширениям:", "green")
        headers = ["Расширение", "Количество", "Общий размер"]
        rows = []
        for ext, data in sorted(ext_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            rows.append([ext, str(data["count"]), _format_size(data["total_size"])])
        print_table(headers, rows)

    # --- Опция 6: Сравнение алгоритмов ---
    def _compare_algorithms(self) -> None:
        print_header("Сравнение алгоритмов")
        if not self.indexer.is_built:
            print_error("Индекс не построен. Используйте опцию 8.")
            return
        raw = input("  Запрос для сравнения: ").strip()
        valid, msg = validate_query(raw)
        if not valid:
            print_error(msg)
            return
        query = parse_query(sanitize_query(raw))
        # Наивный
        start = time.perf_counter()
        naive_results = self.naive.search(query, self.root_path)
        naive_time = time.perf_counter() - start
        # Индексный
        start = time.perf_counter()
        indexed_results = self.indexed.search(query, self.root_path)
        indexed_time = time.perf_counter() - start

        print_comparison(naive_time, indexed_time, len(naive_results), len(indexed_results))
        # Сохранение отчёта
        report = {
            "query": raw,
            "naive": {"time": naive_time, "results_count": len(naive_results)},
            "indexed": {"time": indexed_time, "results_count": len(indexed_results)},
        }
        try:
            save_json(report, "results/comparison_report.json")
            print_success("Отчёт сохранён в results/comparison_report.json")
        except FileIOError as e:
            print_error(str(e))

    # --- Опция 7: Настройки путей ---
    def _settings(self) -> None:
        print_header("Настройки путей")
        current = self.root_path if self.root_path else "(корень)"
        print_colored("  Текущий путь: {}".format(current), "cyan")
        print_colored("  Введите новый путь, / для корня, Enter — оставить", "cyan")
        new_path = input("  Новый путь: ").strip()
        if not new_path:
            return
        if new_path == "/":
            self.root_path = ""
            print_success("Путь сброшен на корень")
        else:
            self.root_path = new_path
            print_success("Путь изменён на: {}".format(self.root_path))
        if self.indexer.is_built:
            print_recommendation("Индекс построен для старого пути. Перестройте его (опция 8).")


    # --- Опция 8: Управление индексом ---
    def _manage_index(self) -> None:
        print_header("Управление индексом")
        print_colored("  1. Построить индекс", "white")
        print_colored("  2. Сохранить индекс", "white")
        print_colored("  3. Загрузить индекс", "white")
        print_colored("  4. Очистить индекс", "white")
        print_colored("  5. Назад", "white")
        raw = input("  Выбор: ").strip()
        if raw == "1":
            self._build_index()
        elif raw == "2":
            self._save_index()
        elif raw == "3":
            self._load_index()
        elif raw == "4":
            self.indexer.clear_index()
            self.cache.clear()
            print_success("Индекс и кэш очищены.")
        elif raw == "5":
            return
        else:
            print_error("Неверный выбор")

    def _build_index(self) -> None:
        def on_progress(current, total, name):
            print_progress(current, total, "Индексация")
        print_colored("  Построение индекса...", "cyan")
        self.indexer.build_index(self.root_path, self.api, on_progress)
        self.cache.clear()
        stats = self.indexer.get_stats()
        print_success(
            f"Индекс построен: {stats['total_terms']} термов, "
            f"{stats['total_docs']} файлов, {stats['build_time']} сек"
        )

    def _save_index(self) -> None:
        if not self.indexer.is_built:
            print_error("Индекс не построен.")
            return
        path = input("  Путь для сохранения (Enter — data/index.json): ").strip()
        if not path:
            path = "data/index.json"
        try:
            self.indexer.save_index(path)
            print_success(f"Индекс сохранён: {path}")
        except Exception as e:
            print_error(str(e))

    def _load_index(self) -> None:
        path = input("  Путь к файлу индекса (Enter — data/index.json): ").strip()
        if not path:
            path = "data/index.json"
        try:
            self.indexer.load_index(path)
            self.cache.clear()
            stats = self.indexer.get_stats()
            print_success(
                f"Индекс загружен: {stats['total_terms']} термов, "
                f"{stats['total_docs']} файлов"
            )
        except Exception as e:
            print_error(str(e))

    # --- Опция 9: Статистика ---
    def _show_stats(self) -> None:
        print_header("Статистика работы")
        index_stats = self.indexer.get_stats()
        cache_stats = self.cache.stats()
        avg_time = (self.total_search_time / self.search_count
                    if self.search_count > 0 else 0.0)
        all_stats = {
            "Индекс построен": "Да" if index_stats["is_built"] else "Нет",
            "Термов в индексе": index_stats["total_terms"],
            "Файлов в индексе": index_stats["total_docs"],
            "Время построения (сек)": index_stats["build_time"],
            "Записей в кэше": cache_stats["size"],
            "Попаданий кэша": cache_stats["hits"],
            "Промахов кэша": cache_stats["misses"],
            "Доля попадания кэша": cache_stats["hit_rate"],
            "Всего поисков": self.search_count,
            "Среднее время поиска (сек)": round(avg_time, 4),
        }
        print_stats(all_stats)

    # --- Опция 10: Выход ---
    def _exit(self) -> None:
        if self.indexer.is_built:
            save = input("  Сохранить индекс перед выходом? (y/n): ").strip().lower()
            if save == "y":
                self._save_index()
        print_colored("  До свидания!", "green")

    # --- Справка ---
    def _show_help(self, num: int) -> None:
        text = HELP_TEXTS.get(num)
        if text:
            print_colored(f"  Опция {num}: {text}", "cyan")
        else:
            print_error(f"Нет справки для опции {num}")

    def _show_all_help(self) -> None:
        print_header("Справка")
        for num, text in HELP_TEXTS.items():
            print_colored(f"  {num}. {text}", "cyan")

    def _record_search(self, elapsed: float) -> None:
        self.search_count += 1
        self.total_search_time += elapsed
