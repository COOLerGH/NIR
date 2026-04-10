"""
Модуль обновления конфигурации пайплайна.

Модифицирует конфигурационные файлы pytest и CI/CD
для учёта карантинных тестов.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from config import TARGET_PROJECT, QUARANTINE_DIR


@dataclass
class UpdateResult:
    """Результат обновления конфигурации."""
    file_path: Path
    success: bool
    action: str
    message: str = ""


class ConfigUpdater:
    """Обновление конфигурации для карантина."""

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or TARGET_PROJECT
        self._backups: Dict[Path, str] = {}

    def update_pytest_ini(
        self,
        quarantined_tests: List[str],
        create_if_missing: bool = True
    ) -> UpdateResult:
        """
        Обновить pytest.ini с игнорированием карантинных тестов.

        Args:
            quarantined_tests: список node_id тестов
            create_if_missing: создать файл если не существует

        Returns:
            UpdateResult
        """
        ini_path = self.project_dir / "pytest.ini"

        if not ini_path.exists():
            if create_if_missing:
                content = self._generate_pytest_ini(quarantined_tests)
                with open(ini_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return UpdateResult(
                    file_path=ini_path,
                    success=True,
                    action="created",
                    message="Created pytest.ini with quarantine configuration",
                )
            else:
                return UpdateResult(
                    file_path=ini_path,
                    success=False,
                    action="none",
                    message="pytest.ini not found",
                )

        with open(ini_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._backups[ini_path] = content

        new_content = self._update_pytest_ini_content(content, quarantined_tests)

        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return UpdateResult(
            file_path=ini_path,
            success=True,
            action="updated",
            message=f"Updated pytest.ini with {len(quarantined_tests)} quarantined tests",
        )

    def update_pyproject_toml(
        self,
        quarantined_tests: List[str]
    ) -> UpdateResult:
        """
        Обновить pyproject.toml с конфигурацией pytest.

        Args:
            quarantined_tests: список node_id тестов

        Returns:
            UpdateResult
        """
        toml_path = self.project_dir / "pyproject.toml"

        if not toml_path.exists():
            return UpdateResult(
                file_path=toml_path,
                success=False,
                action="none",
                message="pyproject.toml not found",
            )

        with open(toml_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._backups[toml_path] = content

        new_content = self._update_pyproject_content(content, quarantined_tests)

        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return UpdateResult(
            file_path=toml_path,
            success=True,
            action="updated",
            message=f"Updated pyproject.toml with {len(quarantined_tests)} quarantined tests",
        )

    def generate_workflow(
        self,
        quarantined_tests: List[str],
        output_path: Optional[Path] = None
    ) -> UpdateResult:
        """
        Сгенерировать GitHub Actions workflow с поддержкой карантина.

        Args:
            quarantined_tests: список node_id тестов
            output_path: путь для сохранения

        Returns:
            UpdateResult
        """
        if output_path is None:
            workflows_dir = self.project_dir / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            output_path = workflows_dir / "test_with_quarantine.yml"

        content = self._generate_workflow_content(quarantined_tests)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return UpdateResult(
            file_path=output_path,
            success=True,
            action="created",
            message="Generated GitHub Actions workflow with quarantine support",
        )

    def generate_deselect_file(
        self,
        quarantined_tests: List[str],
        output_path: Optional[Path] = None
    ) -> UpdateResult:
        """
        Сгенерировать файл со списком тестов для --deselect.

        Args:
            quarantined_tests: список node_id тестов
            output_path: путь для сохранения

        Returns:
            UpdateResult
        """
        output_path = output_path or (QUARANTINE_DIR / "deselect.txt")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = "\n".join(quarantined_tests)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return UpdateResult(
            file_path=output_path,
            success=True,
            action="created",
            message=f"Generated deselect file with {len(quarantined_tests)} tests",
        )

    def generate_pytest_args(self, quarantined_tests: List[str]) -> str:
        """
        Сгенерировать аргументы pytest для исключения карантинных тестов.

        Args:
            quarantined_tests: список node_id тестов

        Returns:
            строка аргументов
        """
        if not quarantined_tests:
            return ""

        deselect_args = " ".join(
            f"--deselect={node_id}" for node_id in quarantined_tests
        )
        return deselect_args

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

    def _generate_pytest_ini(self, quarantined_tests: List[str]) -> str:
        """Сгенерировать содержимое pytest.ini."""
        deselect_lines = "\n    ".join(
            f"--deselect={node_id}" for node_id in quarantined_tests
        )

        content = f"""[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    flaky(reruns): mark test as flaky with reruns
    quarantine: mark test as quarantined

addopts =
    -v
    --tb=short
    {deselect_lines}
"""
        return content

    def _update_pytest_ini_content(
        self,
        content: str,
        quarantined_tests: List[str]
    ) -> str:
        """Обновить существующий pytest.ini."""
        deselect_pattern = r"--deselect=[^\s]+"
        content = re.sub(deselect_pattern, "", content)

        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        if quarantined_tests:
            deselect_lines = "\n    ".join(
                f"--deselect={node_id}" for node_id in quarantined_tests
            )

            if "addopts" in content:
                content = re.sub(
                    r"(addopts\s*=\s*[^\n]*)",
                    rf"\1\n    {deselect_lines}",
                    content,
                )
            else:
                content += f"\naddopts =\n    {deselect_lines}\n"

        return content

    def _update_pyproject_content(
        self,
        content: str,
        quarantined_tests: List[str]
    ) -> str:
        """Обновить существующий pyproject.toml."""
        deselect_pattern = r'"--deselect=[^"]+",?\s*'
        content = re.sub(deselect_pattern, "", content)

        if not quarantined_tests:
            return content

        deselect_entries = ",\n    ".join(
            f'"--deselect={node_id}"' for node_id in quarantined_tests
        )

        if "[tool.pytest.ini_options]" in content:
            if "addopts" in content:
                content = re.sub(
                    r'(addopts\s*=\s*\[)([^\]]*)',
                    rf'\1\2    {deselect_entries},\n',
                    content,
                )
            else:
                content = re.sub(
                    r'(\[tool\.pytest\.ini_options\])',
                    rf'\1\naddopts = [\n    {deselect_entries}\n]',
                    content,
                )
        else:
            content += f"""
[tool.pytest.ini_options]
addopts = [
    {deselect_entries}
]
"""
        return content

    def _generate_workflow_content(self, quarantined_tests: List[str]) -> str:
        """Сгенерировать содержимое GitHub Actions workflow."""
        deselect_args = " ".join(
            f"--deselect={node_id}" for node_id in quarantined_tests
        )

        content = f"""name: Tests with Quarantine

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'

jobs:
  test-stable:
    name: Run Stable Tests
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest-json-report
          
      - name: Run stable tests
        run: |
          pytest tests/ -v --tb=short {deselect_args} --json-report --json-report-file=results/stable.json
          
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: stable-test-results
          path: results/

  test-quarantined:
    name: Run Quarantined Tests
    runs-on: ubuntu-latest
    continue-on-error: true
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest-rerunfailures pytest-json-report
          
      - name: Run quarantined tests
        run: |
          pytest tests/ -v --tb=short --reruns 3 --only-rerun AssertionError {self._generate_select_args(quarantined_tests)} --json-report --json-report-file=results/quarantined.json
          
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: quarantined-test-results
          path: results/

  flaky-detection:
    name: Detect Flaky Tests
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest-flakefinder pytest-json-report pytest-randomly
          
      - name: Run flaky detection
        run: |
          pytest tests/ -v --flake-finder --flake-runs=10 --json-report --json-report-file=results/flaky_detection.json
          
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: flaky-detection-results
          path: results/
"""
        return content

    def _generate_select_args(self, quarantined_tests: List[str]) -> str:
        """Сгенерировать аргументы для выбора только карантинных тестов."""
        if not quarantined_tests:
            return ""

        select_args = " ".join(
            f"-k {self._extract_test_name(node_id)}" for node_id in quarantined_tests[:5]
        )

        if len(quarantined_tests) > 5:
            test_names = " or ".join(
                self._extract_test_name(node_id) for node_id in quarantined_tests
            )
            select_args = f'-k "{test_names}"'

        return select_args

    def _extract_test_name(self, node_id: str) -> str:
        """Извлечь имя теста из node_id."""
        parts = node_id.split("::")
        return parts[-1] if parts else node_id
