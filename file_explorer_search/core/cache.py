"""
LRU-кэш результатов поиска.

Хранит результаты последних запросов. При переполнении
вытесняет самые старые записи. Ведёт статистику обращений.
"""

from collections import OrderedDict
from typing import Any, Optional, Dict


class SearchCache:
    """LRU-кэш с фиксированным максимальным размером."""

    def __init__(self, max_size: int = 100):
        if max_size < 0:
            max_size = 0
        self._max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, query: str) -> Optional[Any]:
        """
        Получить результат из кэша.
        Возвращает None при промахе.
        При попадании перемещает запись в конец (самая свежая).
        """
        key = self._normalize_key(query)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, query: str, results: Any) -> None:
        """
        Сохранить результат в кэш.
        При переполнении удаляет самую старую запись.
        """
        if self._max_size == 0:
            return
        key = self._normalize_key(query)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = results
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[key] = results

    def clear(self) -> None:
        """Очистить кэш. Статистика сохраняется."""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Статистика кэша."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }

    def reset_stats(self) -> None:
        """Сбросить счётчики статистики."""
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        """Текущее количество записей в кэше."""
        return len(self._cache)

    @staticmethod
    def _normalize_key(query: str) -> str:
        """
        Нормализация ключа кэша.
        Приводит к нижнему регистру, убирает лишние пробелы.
        """
        return " ".join(query.lower().split())
