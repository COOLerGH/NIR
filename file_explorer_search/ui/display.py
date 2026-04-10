"""
Форматирование вывода в консоль.

Цветной текст, таблицы, прогресс-бар, вывод результатов поиска,
рекомендации пользователю.
"""

from typing import List, Dict, Any

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class _Stub:
        def __getattr__(self, name):
            return ""
    Fore = _Stub()
    Style = _Stub()

from api.interface import SearchResult


def print_colored(text: str, color: str = "white") -> None:
    """Вывести цветной текст."""
    colors = {
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "cyan": Fore.CYAN,
        "magenta": Fore.MAGENTA,
        "white": Fore.WHITE,
    }
    prefix = colors.get(color, "")
    print(f"{prefix}{text}{Style.RESET_ALL}")


def print_header(text: str) -> None:
    """Вывести заголовок."""
    line = "=" * 50
    print_colored(line, "cyan")
    print_colored(f"  {text}", "cyan")
    print_colored(line, "cyan")


def print_menu(options: List[str]) -> None:
    """Вывести пронумерованное меню."""
    print()
    for i, option in enumerate(options, 1):
        print_colored(f"  {i}. {option}", "white")
    print()


def print_results(results: List[SearchResult]) -> None:
    """Вывести результаты поиска в виде таблицы."""
    if not results:
        print_colored("  Ничего не найдено.", "yellow")
        return

    print()
    header = f"  {'#':<4} {'Файл':<40} {'Score':<10} {'Размер':<10}"
    print_colored(header, "green")
    print_colored("  " + "-" * 64, "green")

    for i, r in enumerate(results, 1):
        score_str = f"{r.score:.4f}"
        size_str = _format_size(r.size)
        line = f"  {i:<4} {r.name:<40} {score_str:<10} {size_str:<10}"
        print(line)

        if r.snippet:
            snippet_display = r.snippet[:80]
            print_colored(f"       {snippet_display}", "cyan")

    print()
    print_colored(f"  Найдено результатов: {len(results)}", "green")


def print_table(headers: List[str], rows: List[List[str]]) -> None:
    """Вывести произвольную таблицу."""
    if not headers:
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    header_line = "  "
    for i, h in enumerate(headers):
        header_line += f"{h:<{widths[i] + 2}}"
    print_colored(header_line, "green")
    print_colored("  " + "-" * sum(w + 2 for w in widths), "green")

    for row in rows:
        line = "  "
        for i, cell in enumerate(row):
            w = widths[i] if i < len(widths) else 10
            line += f"{str(cell):<{w + 2}}"
        print(line)


def print_comparison(naive_time: float, indexed_time: float,
                     naive_count: int, indexed_count: int) -> None:
    """Вывести отчёт сравнения алгоритмов."""
    print_header("Сравнение алгоритмов")
    headers = ["Алгоритм", "Время (сек)", "Результатов"]
    rows = [
        ["Наивный", f"{naive_time:.4f}", str(naive_count)],
        ["Индексный", f"{indexed_time:.4f}", str(indexed_count)],
    ]
    print_table(headers, rows)

    if indexed_time > 0 and naive_time > 0:
        speedup = naive_time / indexed_time
        print()
        print_colored(f"  Ускорение: x{speedup:.1f}", "green")


def print_stats(stats: Dict[str, Any]) -> None:
    """Вывести статистику."""
    print()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()


def print_progress(current: int, total: int, prefix: str = "Прогресс") -> None:
    """Вывести прогресс-бар в одну строку."""
    if total <= 0:
        return
    ratio = current / total
    bar_len = 30
    filled = int(bar_len * ratio)
    bar = "#" * filled + "." * (bar_len - filled)
    percent = int(ratio * 100)
    print(f"\r  {prefix}: [{bar}] {percent}% ({current}/{total})", end="", flush=True)
    if current >= total:
        print()


def print_recommendation(message: str) -> None:
    """Вывести рекомендацию пользователю."""
    print_colored(f"  [Совет] {message}", "yellow")


def print_error(message: str) -> None:
    """Вывести сообщение об ошибке."""
    print_colored(f"  [Ошибка] {message}", "red")


def print_success(message: str) -> None:
    """Вывести сообщение об успехе."""
    print_colored(f"  [OK] {message}", "green")


def _format_size(size: int) -> str:
    """Форматировать размер файла."""
    if size < 1024:
        return "{} B".format(size)
    elif size < 1024 * 1024:
        kb = size / 1024
        return "{:.1f} KB".format(kb)
    else:
        mb = size / (1024 * 1024)
        return "{:.1f} MB".format(mb)

