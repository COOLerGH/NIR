"""
Тесты модулей карантина.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta

from quarantine.manager import QuarantineManager, QuarantinedTest
from quarantine.marker import TestMarker
from quarantine.config_updater import ConfigUpdater


class TestQuarantineManager:
    """Тесты менеджера карантина."""

    def test_add_test(self, quarantine_manager):
        """Добавление теста в карантин."""
        test = quarantine_manager.add(
            node_id="tests/test_a.py::test_flaky",
            name="test_flaky",
            reason="Detected as flaky",
            flaky_type="order_dependent",
        )
        
        assert test.node_id == "tests/test_a.py::test_flaky"
        assert test.is_active
        assert quarantine_manager.is_quarantined("tests/test_a.py::test_flaky")

    def test_remove_test(self, quarantine_manager):
        """Удаление теста из карантина."""
        quarantine_manager.add(
            node_id="tests/test_a.py::test_flaky",
            name="test_flaky",
            reason="Test",
        )
        
        result = quarantine_manager.remove("tests/test_a.py::test_flaky")
        
        assert result is True
        assert not quarantine_manager.is_quarantined("tests/test_a.py::test_flaky")

    def test_remove_nonexistent(self, quarantine_manager):
        """Удаление несуществующего теста."""
        result = quarantine_manager.remove("nonexistent")
        
        assert result is False

    def test_get_active(self, quarantine_manager):
        """Получение активных тестов."""
        quarantine_manager.add("test_1", "test_1", "reason1")
        quarantine_manager.add("test_2", "test_2", "reason2")
        
        active = quarantine_manager.get_active()
        
        assert len(active) == 2

    def test_deactivate(self, quarantine_manager):
        """Деактивация теста."""
        quarantine_manager.add("test_1", "test_1", "reason")
        
        quarantine_manager.deactivate("test_1")
        
        assert not quarantine_manager.is_quarantined("test_1")
        assert quarantine_manager.get("test_1") is not None

    def test_extend_quarantine(self, quarantine_manager):
        """Продление срока карантина."""
        quarantine_manager.add("test_1", "test_1", "reason", duration_days=7)
        original = quarantine_manager.get("test_1")
        original_expire = datetime.fromisoformat(original.expire_date)
        
        quarantine_manager.extend("test_1", days=3)
        
        updated = quarantine_manager.get("test_1")
        new_expire = datetime.fromisoformat(updated.expire_date)
        
        assert new_expire > original_expire

    def test_get_stats(self, quarantine_manager):
        """Получение статистики."""
        quarantine_manager.add("test_1", "test_1", "reason", flaky_type="order_dependent")
        quarantine_manager.add("test_2", "test_2", "reason", flaky_type="timing")
        
        stats = quarantine_manager.get_stats()
        
        assert stats["total"] == 2
        assert stats["active"] == 2
        assert "order_dependent" in stats["by_type"]

    def test_persistence(self, temp_dir):
        """Сохранение и загрузка карантина."""
        manager1 = QuarantineManager(quarantine_dir=temp_dir)
        manager1.add("test_1", "test_1", "reason")
        
        manager2 = QuarantineManager(quarantine_dir=temp_dir)
        
        assert manager2.is_quarantined("test_1")

    def test_get_node_ids(self, quarantine_manager):
        """Получение списка node_id."""
        quarantine_manager.add("test_1", "test_1", "reason")
        quarantine_manager.add("test_2", "test_2", "reason")
        
        node_ids = quarantine_manager.get_node_ids()
        
        assert len(node_ids) == 2
        assert "test_1" in node_ids


class TestQuarantinedTest:
    """Тесты класса QuarantinedTest."""

    def test_is_expired_false(self):
        """Тест не истёк."""
        future = (datetime.now() + timedelta(days=7)).isoformat()
        test = QuarantinedTest(
            node_id="test",
            name="test",
            reason="reason",
            flaky_type="unknown",
            confidence=0.5,
            added_date=datetime.now().isoformat(),
            expire_date=future,
        )
        
        assert not test.is_expired()

    def test_is_expired_true(self):
        """Тест истёк."""
        past = (datetime.now() - timedelta(days=1)).isoformat()
        test = QuarantinedTest(
            node_id="test",
            name="test",
            reason="reason",
            flaky_type="unknown",
            confidence=0.5,
            added_date=(datetime.now() - timedelta(days=8)).isoformat(),
            expire_date=past,
        )
        
        assert test.is_expired()

    def test_days_remaining(self):
        """Расчёт оставшихся дней."""
        future = (datetime.now() + timedelta(days=5)).isoformat()
        test = QuarantinedTest(
            node_id="test",
            name="test",
            reason="reason",
            flaky_type="unknown",
            confidence=0.5,
            added_date=datetime.now().isoformat(),
            expire_date=future,
        )
        
        assert test.days_remaining() >= 4


class TestConfigUpdater:
    """Тесты обновления конфигурации."""

    def test_generate_deselect_file(self, temp_dir):
        """Генерация файла deselect."""
        updater = ConfigUpdater(project_dir=temp_dir)
        quarantine_dir = temp_dir / "quarantine"
        quarantine_dir.mkdir()
        
        node_ids = ["test_a.py::test_1", "test_b.py::test_2"]
        result = updater.generate_deselect_file(
            node_ids,
            output_path=quarantine_dir / "deselect.txt"
        )
        
        assert result.success
        assert result.file_path.exists()
        
        content = result.file_path.read_text()
        assert "test_a.py::test_1" in content
        assert "test_b.py::test_2" in content

    def test_generate_pytest_args(self, temp_dir):
        """Генерация аргументов pytest."""
        updater = ConfigUpdater(project_dir=temp_dir)
        
        node_ids = ["test_a.py::test_1", "test_b.py::test_2"]
        args = updater.generate_pytest_args(node_ids)
        
        assert "--deselect=test_a.py::test_1" in args
        assert "--deselect=test_b.py::test_2" in args

    def test_generate_pytest_args_empty(self, temp_dir):
        """Пустые аргументы для пустого списка."""
        updater = ConfigUpdater(project_dir=temp_dir)
        
        args = updater.generate_pytest_args([])
        
        assert args == ""

    def test_generate_workflow(self, temp_dir):
        """Генерация workflow файла."""
        updater = ConfigUpdater(project_dir=temp_dir)
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)  # Добавить эту строку

        node_ids = ["test_a.py::test_1"]
        result = updater.generate_workflow(
            node_ids,
            output_path=workflows_dir / "test.yml"
        )

        assert result.success
        assert result.file_path.exists()

