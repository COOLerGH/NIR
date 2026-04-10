"""
Валидация входных данных.

Проверяет корректность поисковых запросов, путей и фильтров
перед передачей в алгоритмы поиска.
"""

import re
from typing import Tuple

from core.parser import MAX_QUERY_LENGTH


def validate_query(query: str) -> Tuple[bool, str]:
    """
    Проверить корректность поискового запроса.

    Returns:
        (True, "") если запрос валиден
        (False, сообщение) если нет
    """
    if query is None:
        return False, "Запрос не может быть None"

    if not query.strip():
        return False, "Запрос не может быть пустым"

    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Запрос слишком длинный (макс. {MAX_QUERY_LENGTH} символов)"

    return True, ""


def validate_path(path: str) -> Tuple[bool, str]:
    """
    Проверить корректность пути.

    Returns:
        (True, "") если путь валиден
        (False, сообщение) если нет
    """
    if path is None:
        return False, "Путь не может быть None"

    if not path.strip():
        return False, "Путь не может быть пустым"

    forbidden = ["<", ">", "|", '"', "\0"]
    for char in forbidden:
        if char in path:
            return False, f"Путь содержит недопустимый символ: {char}"

    return True, ""


def validate_max_results(value: int) -> Tuple[bool, str]:
    """
    Проверить корректность ограничения на количество результатов.

    Returns:
        (True, "") если значение валидно
        (False, сообщение) если нет
    """
    if not isinstance(value, int):
        return False, "Значение должно быть целым числом"

    if value < 0:
        return False, "Значение не может быть отрицательным"

    return True, ""


def sanitize_query(query: str) -> str:
    """
    Очистить запрос: убрать лишние пробелы, ограничить длину.
    """
    if not query:
        return ""

    cleaned = " ".join(query.split())

    if len(cleaned) > MAX_QUERY_LENGTH:
        cleaned = cleaned[:MAX_QUERY_LENGTH]

    return cleaned
