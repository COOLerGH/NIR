"""
Пакет конфигурации системы детектирования.
"""

import json
from pathlib import Path

from config.settings import (
    BASE_DIR,
    PROJECT_ROOT,
    TARGET_PROJECT,
    TESTS_DIR,
    RESULTS_DIR,
    REPORTS_DIR,
    QUARANTINE_DIR,
    DEFAULT_RUNS,
    DEFAULT_WORKERS,
    TEST_TIMEOUT,
    FLAKY_THRESHOLD,
    MIN_RUNS_FOR_DETECTION,
    ensure_directories,
)


def load_thresholds() -> dict:
    """Загрузить пороговые значения из JSON-файла."""
    thresholds_path = Path(__file__).parent / "thresholds.json"
    if thresholds_path.exists():
        with open(thresholds_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


__all__ = [
    "BASE_DIR",
    "PROJECT_ROOT",
    "TARGET_PROJECT",
    "TESTS_DIR",
    "RESULTS_DIR",
    "REPORTS_DIR",
    "QUARANTINE_DIR",
    "DEFAULT_RUNS",
    "DEFAULT_WORKERS",
    "TEST_TIMEOUT",
    "FLAKY_THRESHOLD",
    "MIN_RUNS_FOR_DETECTION",
    "ensure_directories",
    "load_thresholds",
]
