"""
Модуль маркировки тестов для карантина.

Добавляет декоратор @pytest.mark.flaky к тестам,
модифицируя исходные файлы или генерируя conftest.py.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from config import TARGET_PROJECT, TESTS_DIR


@dataclass
class MarkerResult:
    """Результат применения маркировки."""
    node_id: str
    file_path: Path
    success: bool
    method: str
    message: str = ""


class TestMarker:
    """Маркировщик тестов для карантина."""

    FLAKY_MARKER = "pytest.mark.flaky"
    QUARANTINE_MARKER = "pytest.mark.quarantine"

    def __init__(self, tests_dir: Optional[Path] = None):
        self.tests_dir = tests_dir or TESTS_DIR
        self._backups: Dict[Path, str] = {}

    def mark_tests(
        self,
        node_ids: List[str],
        marker: str = "flaky",
        reruns: int = 3
    ) -> List[MarkerResult]:
        """
        Применить маркировку к списку тестов.

        Args:
            node_ids: список идентификаторов тестов
            marker: тип маркера (flaky или quarantine)
            reruns: количество повторных запусков

        Returns:
            список MarkerResult
        """
        results = []

        grouped = self._group_by_file(node_ids)

        for file_path, tests in grouped.items():
            file_results = self._mark_file(file_path, tests, marker, reruns)
            results.extend(file_results)

        return results

    def mark_single(
        self,
        node_id: str,
        marker: str = "flaky",
        reruns: int = 3
    ) -> MarkerResult:
        """
        Применить маркировку к одному тесту.

        Args:
            node_id: идентификатор теста
            marker: тип маркера
            reruns: количество повторных запусков

        Returns:
            MarkerResult
        """
        results = self.mark_tests([node_id], marker, reruns)
        return results[0] if results else MarkerResult(
            node_id=node_id,
            file_path=Path(),
            success=False,
            method="none",
            message="Failed to mark test",
        )

    def unmark_tests(self, node_ids: List[str]) -> List[MarkerResult]:
        """
        Удалить маркировку с тестов.

        Args:
            node_ids: список идентификаторов тестов

        Returns:
            список MarkerResult
        """
        results = []

        grouped = self._group_by_file(node_ids)

        for file_path, tests in grouped.items():
            file_results = self._unmark_file(file_path, tests)
            results.extend(file_results)

        return results

    def generate_conftest(
        self,
        node_ids: List[str],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Сгенерировать conftest.py с хуком для карантина.

        Args:
            node_ids: список идентификаторов тестов
            output_path: путь для сохранения

        Returns:
            путь к сгенерированному файлу
        """
        output_path = output_path or (self.tests_dir / "conftest_quarantine.py")

        content = self._generate_conftest_content(node_ids)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def restore_backups(self) -> List[Path]:
        """
        Восстановить файлы из резервных копий.

        Returns:
            список восстановленных файлов
        """
        restored = []

        for file_path, original_content in self._backups.items():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(original_content)
            restored.append(file_path)

        self._backups.clear()
        return restored

    def _group_by_file(self, node_ids: List[str]) -> Dict[Path, List[str]]:
        """Сгруппировать тесты по файлам."""
        grouped: Dict[Path, List[str]] = {}

        for node_id in node_ids:
            file_path = self._get_file_path(node_id)
            if file_path:
                if file_path not in grouped:
                    grouped[file_path] = []
                grouped[file_path].append(node_id)

        return grouped

    def _get_file_path(self, node_id: str) -> Optional[Path]:
        """Извлечь путь к файлу из node_id."""
        if "::" not in node_id:
            return None

        file_part = node_id.split("::")[0]

        if file_part.startswith("tests/"):
            file_path = TARGET_PROJECT / file_part
        else:
            file_path = self.tests_dir / file_part

        if file_path.exists():
            return file_path

        alt_path = TARGET_PROJECT / "tests" / Path(file_part).name
        if alt_path.exists():
            return alt_path

        return None

    def _get_test_name(self, node_id: str) -> str:
        """Извлечь имя теста из node_id."""
        parts = node_id.split("::")
        if len(parts) >= 2:
            return parts[-1]
        return node_id

    def _get_class_name(self, node_id: str) -> Optional[str]:
        """Извлечь имя класса из node_id."""
        parts = node_id.split("::")
        if len(parts) >= 3:
            return parts[-2]
        return None

    def _mark_file(
        self,
        file_path: Path,
        tests: List[str],
        marker: str,
        reruns: int
    ) -> List[MarkerResult]:
        """Применить маркировку к тестам в файле."""
        results = []

        if not file_path.exists():
            for node_id in tests:
                results.append(MarkerResult(
                    node_id=node_id,
                    file_path=file_path,
                    success=False,
                    method="none",
                    message="File not found",
                ))
            return results

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._backups[file_path] = content

        modified_content = content
        has_import = "import pytest" in content or "from pytest" in content

        if not has_import:
            modified_content = "import pytest\n" + modified_content

        for node_id in tests:
            test_name = self._get_test_name(node_id)
            class_name = self._get_class_name(node_id)

            modified_content, success = self._add_marker_to_test(
                modified_content,
                test_name,
                class_name,
                marker,
                reruns,
            )

            results.append(MarkerResult(
                node_id=node_id,
                file_path=file_path,
                success=success,
                method="decorator",
                message="" if success else "Could not find test function",
            ))

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)

        return results

    def _add_marker_to_test(
        self,
        content: str,
        test_name: str,
        class_name: Optional[str],
        marker: str,
        reruns: int
    ) -> Tuple[str, bool]:
        """Добавить декоратор к тесту."""
        if marker == "flaky":
            decorator = f"@pytest.mark.flaky(reruns={reruns})"
        else:
            decorator = f"@pytest.mark.{marker}"

        if class_name:
            pattern = rf"(class\s+{re.escape(class_name)}.*?)(def\s+{re.escape(test_name)}\s*\()"
            flags = re.DOTALL
        else:
            pattern = rf"^(\s*)(def\s+{re.escape(test_name)}\s*\()"
            flags = re.MULTILINE

        match = re.search(pattern, content, flags)
        if not match:
            return content, False

        if decorator in content:
            return content, True

        if class_name:
            def_match = re.search(
                rf"([ \t]*)(def\s+{re.escape(test_name)}\s*\()",
                content[match.start():],
            )
            if def_match:
                indent = def_match.group(1)
                insert_pos = match.start() + def_match.start()
                new_content = (
                    content[:insert_pos] +
                    f"{indent}{decorator}\n" +
                    content[insert_pos:]
                )
                return new_content, True
        else:
            indent = match.group(1)
            insert_pos = match.start()
            new_content = (
                content[:insert_pos] +
                f"{indent}{decorator}\n" +
                content[insert_pos:]
            )
            return new_content, True

        return content, False

    def _unmark_file(
        self,
        file_path: Path,
        tests: List[str]
    ) -> List[MarkerResult]:
        """Удалить маркировку с тестов в файле."""
        results = []

        if not file_path.exists():
            for node_id in tests:
                results.append(MarkerResult(
                    node_id=node_id,
                    file_path=file_path,
                    success=False,
                    method="none",
                    message="File not found",
                ))
            return results

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._backups[file_path] = content

        for node_id in tests:
            test_name = self._get_test_name(node_id)

            pattern = rf"^\s*@pytest\.mark\.(flaky|quarantine)(\([^)]*\))?\s*\n(\s*def\s+{re.escape(test_name)}\s*\()"

            match = re.search(pattern, content, re.MULTILINE)
            if match:
                content = content[:match.start()] + match.group(3) + content[match.end():]
                results.append(MarkerResult(
                    node_id=node_id,
                    file_path=file_path,
                    success=True,
                    method="decorator_removal",
                ))
            else:
                results.append(MarkerResult(
                    node_id=node_id,
                    file_path=file_path,
                    success=False,
                    method="none",
                    message="Marker not found",
                ))

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return results

    def _generate_conftest_content(self, node_ids: List[str]) -> str:
        """Сгенерировать содержимое conftest.py."""
        quarantine_list = ",\n    ".join(f'"{node_id}"' for node_id in node_ids)

        content = f'''"""
Автоматически сгенерированный conftest для карантина flaky-тестов.
"""

import pytest


QUARANTINED_TESTS = [
    {quarantine_list}
]


def pytest_collection_modifyitems(config, items):
    """Применить маркер flaky к тестам в карантине."""
    flaky_marker = pytest.mark.flaky(reruns=3)
    
    for item in items:
        if item.nodeid in QUARANTINED_TESTS:
            item.add_marker(flaky_marker)


def pytest_configure(config):
    """Зарегистрировать маркеры."""
    config.addinivalue_line(
        "markers",
        "flaky(reruns): mark test as flaky with optional reruns"
    )
    config.addinivalue_line(
        "markers",
        "quarantine: mark test as quarantined"
    )
'''
        return content
