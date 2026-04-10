"""
Демонстрационные order-dependent тесты.

Эти тесты специально созданы для демонстрации работы
системы детектирования flaky-тестов.

Паттерн victim-polluter:
- polluter: тест, который изменяет глобальное состояние
- victim: тест, который падает если запускается после polluter
"""

import pytest
from core.cache import SearchCache
from core.indexer import FileIndexer
from api.mock_fs import InMemoryFileSystem


# Глобальное состояние для демонстрации OD-тестов
_shared_cache = SearchCache(max_size=10)
_shared_state = {"counter": 0, "initialized": False}


class TestOrderDependentDemo:
    """Демонстрация order-dependent тестов."""

    def test_polluter_modifies_cache(self):
        """
        POLLUTER: Этот тест добавляет данные в глобальный кэш.
        Если запустится перед victim, то victim упадёт.
        """
        _shared_cache.put("query1", ["result1", "result2"])
        _shared_cache.put("query2", ["result3"])
        
        assert _shared_cache.size == 2

    def test_victim_expects_empty_cache(self):
        """
        VICTIM: Этот тест ожидает пустой кэш.
        Падает если test_polluter_modifies_cache запустился раньше.
        """
        # Если polluter запустился раньше, кэш не пустой
        assert _shared_cache.size == 0, "Cache should be empty but polluter ran first!"

    def test_polluter_changes_counter(self):
        """
        POLLUTER: Изменяет глобальный счётчик.
        """
        _shared_state["counter"] += 10
        assert _shared_state["counter"] >= 10

    def test_victim_expects_zero_counter(self):
        """
        VICTIM: Ожидает что счётчик равен 0.
        """
        assert _shared_state["counter"] == 0, f"Counter should be 0, got {_shared_state['counter']}"


class TestStateLeakage:
    """Тесты с утечкой состояния через класс."""

    _class_data = []

    def test_polluter_adds_to_list(self):
        """POLLUTER: Добавляет элементы в список класса."""
        TestStateLeakage._class_data.append("item1")
        TestStateLeakage._class_data.append("item2")
        assert len(TestStateLeakage._class_data) >= 2

    def test_victim_expects_empty_list(self):
        """VICTIM: Ожидает пустой список."""
        assert len(TestStateLeakage._class_data) == 0, \
            f"List should be empty, got {TestStateLeakage._class_data}"

    def test_another_polluter(self):
        """POLLUTER: Ещё один тест изменяющий состояние."""
        TestStateLeakage._class_data.extend(["a", "b", "c"])
        assert "a" in TestStateLeakage._class_data


class TestIndexerStateLeak:
    """OD-тесты связанные с индексатором."""

    _shared_indexer = FileIndexer()
    _shared_fs = InMemoryFileSystem()

    @classmethod
    def setup_class(cls):
        """Настройка тестовой файловой системы."""
        cls._shared_fs.add_file("/doc1.txt", "python flask web")
        cls._shared_fs.add_file("/doc2.txt", "java spring boot")

    def test_polluter_builds_index(self):
        """POLLUTER: Строит индекс."""
        TestIndexerStateLeak._shared_indexer.build_index(
            "/", TestIndexerStateLeak._shared_fs
        )
        assert TestIndexerStateLeak._shared_indexer.is_built

    def test_victim_expects_no_index(self):
        """VICTIM: Ожидает что индекс не построен."""
        assert not TestIndexerStateLeak._shared_indexer.is_built, \
            "Indexer should not be built yet!"

    def test_polluter_clears_index(self):
        """POLLUTER: Очищает индекс после использования."""
        if TestIndexerStateLeak._shared_indexer.is_built:
            TestIndexerStateLeak._shared_indexer.clear_index()
        assert not TestIndexerStateLeak._shared_indexer.is_built

    def test_victim_expects_built_index(self):
        """VICTIM: Ожидает построенный индекс."""
        assert TestIndexerStateLeak._shared_indexer.is_built, \
            "Indexer should be built!"


class TestFileSystemStateLeak:
    """OD-тесты с файловой системой."""

    _fs = InMemoryFileSystem()

    def test_polluter_adds_files(self):
        """POLLUTER: Добавляет файлы."""
        TestFileSystemStateLeak._fs.add_file("/test_file.txt", "test content")
        TestFileSystemStateLeak._fs.add_directory("/test_dir")
        
        info = TestFileSystemStateLeak._fs.get_file_info("/test_file.txt")
        assert info is not None

    def test_victim_expects_no_files(self):
        """VICTIM: Ожидает отсутствие файла."""
        info = TestFileSystemStateLeak._fs.get_file_info("/test_file.txt")
        assert info is None, "File should not exist!"

    def test_polluter_modifies_file(self):
        """POLLUTER: Модифицирует файл."""
        TestFileSystemStateLeak._fs.add_file(
            "/config.txt", "modified=true", modified_date="2025-12-01"
        )
        content = TestFileSystemStateLeak._fs.get_content("/config.txt")
        assert "modified" in content

    def test_victim_expects_original_content(self):
        """VICTIM: Ожидает оригинальное содержимое."""
        try:
            content = TestFileSystemStateLeak._fs.get_content("/config.txt")
            assert content == "", f"Expected empty, got: {content}"
        except FileNotFoundError:
            pass  # Это тоже приемлемо
