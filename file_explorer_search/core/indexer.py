"""
Построение и управление инвертированным индексом.

Индекс имеет структуру:
    index: {term: {filepath: count}}
    doc_lengths: {filepath: total_tokens}

Позволяет сохранять/загружать индекс в JSON для переиспользования.
"""

import json
import time
from typing import Dict, Optional, Callable

from api.interface import FileSystemAPI
from core.ranker import tokenize, remove_stop_words


class FileIndexer:
    """Построение и управление инвертированным индексом."""

    def __init__(self):
        self.index: Dict[str, Dict[str, int]] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.total_docs: int = 0
        self.build_time: float = 0.0
        self._is_built = False

    @property
    def is_built(self) -> bool:
        """Построен ли индекс."""
        return self._is_built

    def build_index(
        self,
        root_path: str,
        api: FileSystemAPI,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        """
        Построить индекс по всем файлам начиная с root_path.

        Args:
            root_path: корневой путь для обхода
            api: реализация FileSystemAPI
            on_progress: колбэк (текущий, всего, имя_файла)
        """
        start = time.perf_counter()

        self.index.clear()
        self.doc_lengths.clear()

        files = api.walk(root_path)
        total = len(files)
        self.total_docs = total

        for i, file_info in enumerate(files):
            try:
                content = api.get_content(file_info.path)
            except (FileNotFoundError, Exception):
                continue

            tokens = tokenize(content)
            clean_tokens = remove_stop_words(tokens)

            self.doc_lengths[file_info.path] = len(clean_tokens)

            for token in clean_tokens:
                if token not in self.index:
                    self.index[token] = {}
                if file_info.path not in self.index[token]:
                    self.index[token][file_info.path] = 0
                self.index[token][file_info.path] += 1

            if on_progress:
                on_progress(i + 1, total, file_info.name)

        self.build_time = time.perf_counter() - start
        self._is_built = True

    def save_index(self, filepath: str) -> None:
        """Сохранить индекс в JSON-файл."""
        data = {
            "index": self.index,
            "doc_lengths": self.doc_lengths,
            "total_docs": self.total_docs,
            "build_time": self.build_time,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_index(self, filepath: str) -> None:
        """Загрузить индекс из JSON-файла."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.index = data.get("index", {})
        self.doc_lengths = data.get("doc_lengths", {})
        self.total_docs = data.get("total_docs", 0)
        self.build_time = data.get("build_time", 0.0)
        self._is_built = True

    def clear_index(self) -> None:
        """Очистить индекс."""
        self.index.clear()
        self.doc_lengths.clear()
        self.total_docs = 0
        self.build_time = 0.0
        self._is_built = False

    def get_stats(self) -> dict:
        """Статистика индекса."""
        return {
            "is_built": self._is_built,
            "total_terms": len(self.index),
            "total_docs": self.total_docs,
            "build_time": round(self.build_time, 4),
        }
