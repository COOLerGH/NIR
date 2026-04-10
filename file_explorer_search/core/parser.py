"""
Парсер поисковых запросов.

Поддерживает синтаксис:
    python AND test       — оба слова
    python OR java        — любое из слов
    python NOT java       — исключить слово
    *.py                  — wildcard по имени файла
    size>1024             — фильтр по размеру (байты)
    date>2025-01-01       — фильтр по дате
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


MAX_QUERY_LENGTH = 1000


@dataclass
class ParsedQuery:
    """Результат разбора поискового запроса."""
    terms: List[str] = field(default_factory=list)
    operator: str = "AND"
    exclude_terms: List[str] = field(default_factory=list)
    wildcard: Optional[str] = None
    size_filter: Optional[dict] = None
    date_filter: Optional[dict] = None
    is_empty: bool = False


class QueryParseError(Exception):
    """Ошибка разбора запроса."""
    pass


def parse_query(raw: str) -> ParsedQuery:
    """
    Разобрать строку запроса в структурированный объект.

    Args:
        raw: исходная строка запроса от пользователя

    Returns:
        ParsedQuery с заполненными полями
    """
    if not raw or not raw.strip():
        return ParsedQuery(is_empty=True)

    query = raw.strip()
    if len(query) > MAX_QUERY_LENGTH:
        query = query[:MAX_QUERY_LENGTH]

    result = ParsedQuery()

    tokens = query.split()
    if not tokens:
        return ParsedQuery(is_empty=True)

    _extract_wildcards(tokens, result)
    _extract_size_filter(tokens, result)
    _extract_date_filter(tokens, result)
    _extract_operator_and_terms(tokens, result)

    if not result.terms and not result.wildcard:
        result.is_empty = True

    return result


def _extract_wildcards(tokens: list, result: ParsedQuery) -> None:
    """Извлечь wildcard-паттерны из токенов."""
    remaining = []
    for token in tokens:
        if "*" in token or "?" in token:
            result.wildcard = token
        else:
            remaining.append(token)
    tokens.clear()
    tokens.extend(remaining)


def _extract_size_filter(tokens: list, result: ParsedQuery) -> None:
    """Извлечь фильтр по размеру (size>1024, size<500)."""
    remaining = []
    pattern = re.compile(r"^size([><=!]+)(\d+)$", re.IGNORECASE)
    for token in tokens:
        match = pattern.match(token)
        if match:
            result.size_filter = {
                "op": match.group(1),
                "value": int(match.group(2)),
            }
        else:
            remaining.append(token)
    tokens.clear()
    tokens.extend(remaining)


def _extract_date_filter(tokens: list, result: ParsedQuery) -> None:
    """Извлечь фильтр по дате (date>2025-01-01)."""
    remaining = []
    pattern = re.compile(r"^date([><=!]+)([\d-]+)$", re.IGNORECASE)
    for token in tokens:
        match = pattern.match(token)
        if match:
            result.date_filter = {
                "op": match.group(1),
                "value": match.group(2),
            }
        else:
            remaining.append(token)
    tokens.clear()
    tokens.extend(remaining)


def _extract_operator_and_terms(tokens: list, result: ParsedQuery) -> None:
    """Извлечь оператор (AND/OR/NOT) и разделить термы."""
    if not tokens:
        return

    upper_tokens = [t.upper() for t in tokens]

    if "NOT" in upper_tokens:
        idx = upper_tokens.index("NOT")
        before = [tokens[i] for i in range(len(tokens))
                  if i < idx and upper_tokens[i] not in ("AND", "OR", "NOT")]
        after = [tokens[i] for i in range(len(tokens))
                 if i > idx and upper_tokens[i] not in ("AND", "OR", "NOT")]
        result.terms = [t.lower() for t in before] if before else []
        result.exclude_terms = [t.lower() for t in after]
        result.operator = "NOT"
        return

    if "OR" in upper_tokens:
        result.operator = "OR"
        result.terms = [t.lower() for t in tokens
                        if t.upper() not in ("AND", "OR", "NOT")]
        return

    if "AND" in upper_tokens:
        result.operator = "AND"
        result.terms = [t.lower() for t in tokens
                        if t.upper() not in ("AND", "OR", "NOT")]
        return

    result.operator = "AND"
    result.terms = [t.lower() for t in tokens]
