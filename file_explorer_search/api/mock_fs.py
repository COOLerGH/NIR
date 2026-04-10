"""
In-memory реализация файловой системы.

Хранит файлы и директории в словаре. Позволяет программно
наполнять файловую систему для тестов и демонстрации.
"""

from typing import List, Optional, Dict
from api.interface import FileSystemAPI, FileInfo


class InMemoryFileSystem(FileSystemAPI):
    """Файловая система в оперативной памяти."""

    def __init__(self):
        self._files: Dict[str, dict] = {}
        self._directories: Dict[str, dict] = {}
        self.add_directory("/")

    def add_file(self, path: str, content: str = "",
                 size: int = None, modified_date: str = "2025-01-01") -> None:
        """Добавить файл в виртуальную ФС."""
        name = path.rsplit("/", 1)[-1] if "/" in path else path
        actual_size = size if size is not None else len(content.encode("utf-8"))
        self._files[path] = {
            "name": name,
            "path": path,
            "content": content,
            "size": actual_size,
            "modified_date": modified_date,
        }
        parent = path.rsplit("/", 1)[0] if "/" in path else "/"
        if parent and parent not in self._directories:
            self.add_directory(parent)

    def add_directory(self, path: str, modified_date: str = "2025-01-01") -> None:
        """Добавить директорию в виртуальную ФС."""
        name = path.rsplit("/", 1)[-1] if "/" in path and path != "/" else path
        self._directories[path] = {
            "name": name,
            "path": path,
            "modified_date": modified_date,
        }

    def list_directory(self, path: str) -> List[FileInfo]:
        """Список файлов и папок в указанной директории."""
        result = []
        prefix = path.rstrip("/") + "/"

        for fpath, fdata in self._files.items():
            if self._is_direct_child(fpath, prefix):
                result.append(FileInfo(
                    name=fdata["name"],
                    path=fdata["path"],
                    size=fdata["size"],
                    modified_date=fdata["modified_date"],
                    is_dir=False,
                ))

        for dpath, ddata in self._directories.items():
            if dpath != path and self._is_direct_child(dpath, prefix):
                result.append(FileInfo(
                    name=ddata["name"],
                    path=ddata["path"],
                    size=0,
                    modified_date=ddata["modified_date"],
                    is_dir=True,
                ))

        return result

    def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Информация о файле или директории."""
        if path in self._files:
            f = self._files[path]
            return FileInfo(
                name=f["name"], path=f["path"], size=f["size"],
                modified_date=f["modified_date"], is_dir=False,
            )
        if path in self._directories:
            d = self._directories[path]
            return FileInfo(
                name=d["name"], path=d["path"], size=0,
                modified_date=d["modified_date"], is_dir=True,
            )
        return None

    def get_content(self, path: str) -> str:
        """Содержимое файла."""
        if path in self._files:
            return self._files[path]["content"]
        raise FileNotFoundError(f"File not found: {path}")

    def walk(self, root_path: str) -> List[FileInfo]:
        """Рекурсивный обход — все файлы начиная с root_path."""
        result = []
        prefix = root_path.rstrip("/") + "/"

        for fpath, fdata in self._files.items():
            if fpath.startswith(prefix) or fpath == root_path:
                result.append(FileInfo(
                    name=fdata["name"],
                    path=fdata["path"],
                    size=fdata["size"],
                    modified_date=fdata["modified_date"],
                    is_dir=False,
                ))

        return result

    @staticmethod
    def _is_direct_child(item_path: str, parent_prefix: str) -> bool:
        """Проверяет, что item_path — прямой потомок (без вложенности)."""
        if not item_path.startswith(parent_prefix):
            return False
        remainder = item_path[len(parent_prefix):]
        return "/" not in remainder and remainder != ""
