"""
Модуль запуска тестов для детектирования flaky-тестов.

Использует pytest-flakefinder для многократного прогона
и pytest-xdist для параллельного выполнения.
"""

import subprocess
import time
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

from config import (
    TARGET_PROJECT,
    TESTS_DIR,
    RESULTS_DIR,
    DEFAULT_RUNS,
    DEFAULT_WORKERS,
    TEST_TIMEOUT,
    ensure_directories,
)


@dataclass
class RunConfig:
    """Конфигурация запуска тестов."""
    runs: int = DEFAULT_RUNS
    workers: int = DEFAULT_WORKERS
    timeout: int = TEST_TIMEOUT
    randomize_order: bool = True
    test_path: Optional[str] = None
    extra_args: List[str] = field(default_factory=list)


@dataclass
class RunResult:
    """Результат прогона тестов."""
    success: bool
    duration: float
    total_runs: int
    output_file: Path
    return_code: int
    stdout: str = ""
    stderr: str = ""


class TestRunner:
    """Запуск тестов с использованием pytest-flakefinder."""

    def __init__(self, config: Optional[RunConfig] = None):
        self.config = config or RunConfig()
        ensure_directories()

    def run(self, test_path: Optional[str] = None) -> RunResult:
        """
        Запустить тесты с многократным прогоном.

        Args:
            test_path: путь к тестам (файл или директория)

        Returns:
            RunResult с информацией о прогоне
        """
        target = test_path or self.config.test_path or str(TESTS_DIR)
        timestamp = int(time.time())
        output_file = RESULTS_DIR / f"run_{timestamp}.json"

        cmd = self._build_command(target, output_file)

        start_time = time.perf_counter()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=str(TARGET_PROJECT),
        )
        duration = time.perf_counter() - start_time

        return RunResult(
            success=result.returncode == 0,
            duration=duration,
            total_runs=self.config.runs,
            output_file=output_file,
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def run_single_order(self, test_path: Optional[str] = None, seed: int = 0) -> RunResult:
        """
        Запустить тесты один раз.

        Args:
            test_path: путь к тестам
            seed: seed (не используется, сохранён для совместимости)

        Returns:
            RunResult с информацией о прогоне
        """
        target = test_path or self.config.test_path or str(TESTS_DIR)
        timestamp = int(time.time())
        output_file = RESULTS_DIR / f"single_{timestamp}_{seed}.json"

        cmd = [
            "python", "-m", "pytest",
            str(target),
            "--json-report",
            f"--json-report-file={str(output_file.absolute())}",
            "-v",
        ]

        cmd.extend(self.config.extra_args)

        start_time = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                cwd=str(TARGET_PROJECT),
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                success=False,
                duration=self.config.timeout,
                total_runs=1,
                output_file=output_file,
                return_code=-1,
                stdout="",
                stderr="Timeout expired",
            )

        duration = time.perf_counter() - start_time

        return RunResult(
            success=result.returncode == 0,
            duration=duration,
            total_runs=1,
            output_file=output_file,
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def run_multiple_orders(
        self, test_path: Optional[str] = None, num_orders: int = 10
    ) -> List[RunResult]:
        """
        Запустить тесты несколько раз.

        Args:
            test_path: путь к тестам
            num_orders: количество прогонов

        Returns:
            список RunResult для каждого прогона
        """
        results = []
        for i in range(num_orders):
            result = self.run_single_order(test_path, seed=i)
            results.append(result)
        return results

    def _build_command(self, test_path: str, output_file: Path) -> List[str]:
        """Построить команду запуска pytest с flakefinder."""
        cmd = [
            "python", "-m", "pytest",
            str(test_path),
            "--flake-finder",
            f"--flake-runs={self.config.runs}",
            "--json-report",
            f"--json-report-file={str(output_file.absolute())}",
            "-v",
        ]

        if self.config.workers > 1:
            cmd.extend(["-n", str(self.config.workers)])

        cmd.extend(self.config.extra_args)

        return cmd

    def get_last_results(self, count: int = 10) -> List[Path]:
        """
        Получить пути к последним файлам результатов.

        Args:
            count: количество файлов

        Returns:
            список путей к файлам результатов
        """
        result_files = sorted(
            RESULTS_DIR.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return result_files[:count]
