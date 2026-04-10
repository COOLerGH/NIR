"""
Абстрактный интерфейс файловой системы и модели данных.

Все компоненты приложения работают с FileSystemAPI,
что позволяет подменять реализацию (реальный HTTP-клиент или in-memory для тестов).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class FileInfo:
    """Информация о файле или директории."""
    name: str
    path: str
    size: int = 0
    modified_date: str = ""
    is_dir: bool = False
    extension: str = ""

    def __post_init__(self):
        if not self.extension and not self.is_dir and "." in self.name:
            self.extension = "." + self.name.rsplit(".", 1)[-1].lower()


@dataclass
class SearchResult:
    """Результат поиска с оценкой релевантности."""
    path: str
    name: str
    score: float = 0.0
    size: int = 0
    modified_date: str = ""
    snippet: str = ""


class FileSystemAPI(ABC):
    """Абстрактный интерфейс для доступа к файловой системе."""

    @abstractmethod
    def list_directory(self, path: str) -> List[FileInfo]:
        """Возвращает список файлов и папок в указанной директории."""
        pass

    @abstractmethod
    def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Возвращает информацию о конкретном файле/папке."""
        pass

    @abstractmethod
    def get_content(self, path: str) -> str:
        """Возвращает текстовое содержимое файла."""
        pass

    @abstractmethod
    def walk(self, root_path: str) -> List[FileInfo]:
        """
        Рекурсивно обходит все файлы начиная с root_path.
        Возвращает плоский список только файлов (без директорий).
        """
        pass
