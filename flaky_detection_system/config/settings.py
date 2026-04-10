"""
Глобальные настройки системы детектирования flaky-тестов.
"""

import os
from pathlib import Path


# Корневые директории
BASE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BASE_DIR.parent
TARGET_PROJECT = PROJECT_ROOT / "file_explorer_search"
TESTS_DIR = TARGET_PROJECT / "tests"

# Директории для результатов
RESULTS_DIR = BASE_DIR / "results"
REPORTS_DIR = BASE_DIR / "reports"
QUARANTINE_DIR = BASE_DIR / "quarantine"

# Параметры запуска тестов
DEFAULT_RUNS = 10
DEFAULT_WORKERS = 4
TEST_TIMEOUT = 300

# Пороги детекции
FLAKY_THRESHOLD = 0.1
MIN_RUNS_FOR_DETECTION = 5

# Форматы отчетов
REPORT_FORMATS = ["json", "html"]

# Паттерны тестовых файлов
TEST_FILE_PATTERN = "test_*.py"


def ensure_directories():
    """Создать необходимые директории если не существуют."""
    for directory in [RESULTS_DIR, REPORTS_DIR, QUARANTINE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# Вывод путей для отладки (временно)
if __name__ == "__main__":
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"TARGET_PROJECT: {TARGET_PROJECT}")
    print(f"TESTS_DIR: {TESTS_DIR}")
    print(f"TESTS_DIR exists: {TESTS_DIR.exists()}")
