"""
Загрузка и сохранение данных в JSON.

Обеспечивает ввод/вывод данных: загрузка входных файлов,
сохранение результатов поиска и отчётов.
"""

import json
import os
from typing import Any


class FileIOError(Exception):
    """Ошибка при работе с файлами."""
    pass


def load_json(filepath: str) -> Any:
    """
    Загрузить данные из JSON-файла.

    Args:
        filepath: путь к файлу

    Returns:
        dict или list — содержимое файла

    Raises:
        FileIOError: если файл не найден или содержит невалидный JSON
    """
    if not os.path.exists(filepath):
        raise FileIOError(f"Файл не найден: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise FileIOError(f"Невалидный JSON в файле {filepath}: {e}")
    except OSError as e:
        raise FileIOError(f"Ошибка чтения файла {filepath}: {e}")


def save_json(data: Any, filepath: str) -> None:
    """
    Сохранить данные в JSON-файл.

    Args:
        data: данные для сохранения (dict, list)
        filepath: путь к файлу

    Raises:
        FileIOError: если не удалось записать файл
    """
    try:
        ensure_directory(os.path.dirname(filepath))
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise FileIOError(f"Ошибка записи файла {filepath}: {e}")


def ensure_directory(path: str) -> None:
    """
    Создать директорию, если она не существует.

    Args:
        path: путь к директории
    """
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
