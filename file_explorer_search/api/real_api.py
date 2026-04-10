"""
HTTP-клиент к REST API File Explorer.

Формат API:
    GET /{path}  — если папка, возвращает список [{name, size_bytes, ...}]
                 — если файл, возвращает {name, size_bytes, text, ...}
"""

import requests
from typing import List, Optional
from api.interface import FileSystemAPI, FileInfo


class APIConnectionError(Exception):
    """Ошибка соединения с API."""
    pass


class APIRequestError(Exception):
    """Ошибка при выполнении запроса к API."""
    pass


class RealFileExplorerAPI(FileSystemAPI):
    """HTTP-клиент к File Explorer REST API."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def _request(self, endpoint: str):
        """Выполнить GET-запрос к API."""
        url = self.base_url + "/" + endpoint.strip("/") if endpoint.strip("/") else self.base_url
        try:
            response = self._session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.ConnectionError:
            raise APIConnectionError(
                "Не удалось подключиться к API: {}. "
                "Убедитесь, что сервер запущен.".format(self.base_url)
            )
        except requests.Timeout:
            raise APIConnectionError(
                "Таймаут при запросе к {}. Сервер не отвечает.".format(url)
            )
        except requests.HTTPError as e:
            raise APIRequestError(
                "Ошибка API ({}): {}".format(e.response.status_code, url)
            )
        except ValueError:
            raise APIRequestError(
                "Некорректный ответ API (не JSON): {}".format(url)
            )

    def _is_directory(self, item: dict) -> bool:
        """Определить, является ли элемент директорией."""
        name = item.get("name", "")
        if name.endswith("/"):
            return True
        if item.get("size_bytes", 0) == 0 and "text" not in item and "." not in name:
            return True
        return False

    def list_directory(self, path: str) -> List[FileInfo]:
        """Список файлов и папок в директории."""
        clean_path = path.strip("/")
        data = self._request(clean_path)

        if not isinstance(data, list):
            return []

        result = []
        for item in data:
            name = item.get("name", "").rstrip("/")
            is_dir = self._is_directory(item)
            if clean_path:
                item_path = clean_path + "/" + name
            else:
                item_path = name

            result.append(FileInfo(
                name=name,
                path=item_path,
                size=item.get("size_bytes", 0),
                modified_date=item.get("modified_date", ""),
                is_dir=is_dir,
            ))

        return result

    def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Информация о файле."""
        clean_path = path.strip("/")
        try:
            data = self._request(clean_path)
        except (APIConnectionError, APIRequestError):
            return None

        if isinstance(data, list):
            # Это директория
            name = clean_path.rsplit("/", 1)[-1] if "/" in clean_path else clean_path
            return FileInfo(
                name=name, path=clean_path, size=0,
                modified_date="", is_dir=True,
            )

        if isinstance(data, dict):
            name = data.get("name", clean_path.rsplit("/", 1)[-1])
            return FileInfo(
                name=name,
                path=clean_path,
                size=data.get("size_bytes", 0),
                modified_date=data.get("modified_date", ""),
                is_dir=False,
            )

        return None

    def get_content(self, path: str) -> str:
        """Текстовое содержимое файла."""
        clean_path = path.strip("/")
        data = self._request(clean_path)

        if isinstance(data, dict):
            return data.get("text", "")

        return ""

    def walk(self, root_path: str) -> List[FileInfo]:
        """Рекурсивный обход всех файлов."""
        result = []
        self._walk_recursive(root_path.strip("/"), result)
        return result

    def _walk_recursive(self, path: str, result: List[FileInfo]) -> None:
        """Рекурсивный обход директории."""
        try:
            items = self.list_directory(path)
        except (APIConnectionError, APIRequestError):
            return

        for item in items:
            if item.is_dir:
                self._walk_recursive(item.path, result)
            else:
                result.append(item)

    def check_connection(self) -> bool:
        """Проверить доступность API."""
        try:
            self._session.get(self.base_url, timeout=5)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False
