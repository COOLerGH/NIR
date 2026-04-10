"""
Базовый класс для алгоритмов поиска.

Определяет общий интерфейс и логику фильтрации/ограничения результатов.
Конкретные алгоритмы реализуют метод _execute_search.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from fnmatch import fnmatch

from api.interface import FileSystemAPI, SearchResult
from core.parser import ParsedQuery


MAX_RESULTS = 1000


class SearchAlgorithm(ABC):
    """Базовый класс алгоритма поиска."""

    def __init__(self, api: FileSystemAPI):
        self.api = api

    def search(
        self,
        query: ParsedQuery,
        root_path: str,
        max_results: int = MAX_RESULTS,
    ) -> List[SearchResult]:
        """
        Выполнить поиск.

        Args:
            query: разобранный запрос
            root_path: корневой путь для поиска
            max_results: максимальное количество результатов

        Returns:
            список SearchResult, отсортированный по убыванию score
        """
        if query.is_empty:
            return []

        results = self._execute_search(query, root_path)

        if query.size_filter:
            results = self._apply_size_filter(results, query.size_filter)

        if query.date_filter:
            results = self._apply_date_filter(results, query.date_filter)

        if query.wildcard:
            results = self._apply_wildcard_filter(results, query.wildcard)

        if max_results < 0:
            max_results = MAX_RESULTS

        if len(results) > max_results:
            results = results[:max_results]

        return results

    @abstractmethod
    def _execute_search(
        self, query: ParsedQuery, root_path: str
    ) -> List[SearchResult]:
        """Основная логика поиска. Реализуется в наследниках."""
        pass

    @staticmethod
    def _apply_size_filter(
        results: List[SearchResult], size_filter: dict
    ) -> List[SearchResult]:
        """Фильтр по размеру файла."""
        op = size_filter.get("op", ">")
        value = size_filter.get("value", 0)

        filtered = []
        for r in results:
            if op == ">" and r.size > value:
                filtered.append(r)
            elif op == ">=" and r.size >= value:
                filtered.append(r)
            elif op == "<" and r.size < value:
                filtered.append(r)
            elif op == "<=" and r.size <= value:
                filtered.append(r)
            elif op == "=" and r.size == value:
                filtered.append(r)
        return filtered

    @staticmethod
    def _apply_date_filter(
        results: List[SearchResult], date_filter: dict
    ) -> List[SearchResult]:
        """Фильтр по дате модификации."""
        op = date_filter.get("op", ">")
        value = date_filter.get("value", "")

        if not value:
            return results

        filtered = []
        for r in results:
            if not r.modified_date:
                continue
            if op == ">" and r.modified_date > value:
                filtered.append(r)
            elif op == ">=" and r.modified_date >= value:
                filtered.append(r)
            elif op == "<" and r.modified_date < value:
                filtered.append(r)
            elif op == "<=" and r.modified_date <= value:
                filtered.append(r)
            elif op == "=" and r.modified_date == value:
                filtered.append(r)
        return filtered

    @staticmethod
    def _apply_wildcard_filter(
        results: List[SearchResult], pattern: str
    ) -> List[SearchResult]:
        """Фильтр по wildcard-маске имени файла."""
        return [r for r in results if fnmatch(r.name, pattern)]
