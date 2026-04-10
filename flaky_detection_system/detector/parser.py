"""
Модуль парсинга результатов тестовых прогонов.

Читает JSON-отчеты pytest-json-report и извлекает
информацию о статусах тестов для анализа.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class TestStatus(Enum):
    """Статус выполнения теста."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    XFAILED = "xfailed"
    XPASSED = "xpassed"


@dataclass
class TestResult:
    """Результат выполнения одного теста."""
    node_id: str
    name: str
    status: TestStatus
    duration: float
    run_index: int = 0
    error_message: str = ""
    longrepr: str = ""


@dataclass
class TestHistory:
    """История прогонов одного теста."""
    node_id: str
    name: str
    results: List[TestResult] = field(default_factory=list)
    
    @property
    def total_runs(self) -> int:
        return len(self.results)
    
    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status in (TestStatus.FAILED, TestStatus.ERROR))
    
    @property
    def pass_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.passed_count / self.total_runs
    
    @property
    def is_flaky(self) -> bool:
        """Тест flaky если есть и passed и failed результаты."""
        has_passed = self.passed_count > 0
        has_failed = self.failed_count > 0
        return has_passed and has_failed
    
    @property
    def avg_duration(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.duration for r in self.results) / len(self.results)


@dataclass
class ParsedReport:
    """Распарсенный отчет одного прогона."""
    filepath: Path
    run_index: int
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float
    tests: List[TestResult] = field(default_factory=list)


class ResultsParser:
    """Парсер результатов pytest-json-report."""

    def __init__(self):
        self._reports: List[ParsedReport] = []
        self._test_histories: Dict[str, TestHistory] = {}

    def parse_file(self, filepath: Path, run_index: int = 0) -> Optional[ParsedReport]:
        """
        Распарсить один JSON-файл с результатами.

        Args:
            filepath: путь к JSON-файлу
            run_index: индекс прогона

        Returns:
            ParsedReport или None при ошибке
        """
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

        return self._parse_report_data(data, filepath, run_index)

    def parse_multiple(self, filepaths: List[Path]) -> List[ParsedReport]:
        """
        Распарсить несколько файлов результатов.

        Args:
            filepaths: список путей к JSON-файлам

        Returns:
            список ParsedReport
        """
        reports = []
        for i, filepath in enumerate(filepaths):
            report = self.parse_file(filepath, run_index=i)
            if report:
                reports.append(report)
        
        self._reports = reports
        self._build_test_histories()
        return reports

    def get_test_histories(self) -> Dict[str, TestHistory]:
        """
        Получить историю прогонов для всех тестов.

        Returns:
            словарь node_id -> TestHistory
        """
        return self._test_histories

    def get_flaky_tests(self) -> List[TestHistory]:
        """
        Получить список flaky-тестов.

        Returns:
            список TestHistory для flaky-тестов
        """
        return [h for h in self._test_histories.values() if h.is_flaky]

    def get_stable_tests(self) -> List[TestHistory]:
        """
        Получить список стабильных тестов.

        Returns:
            список TestHistory для стабильных тестов
        """
        return [h for h in self._test_histories.values() if not h.is_flaky]

    def get_summary(self) -> Dict[str, Any]:
        """
        Получить сводную статистику по всем прогонам.

        Returns:
            словарь со статистикой
        """
        total_tests = len(self._test_histories)
        flaky_tests = len(self.get_flaky_tests())
        stable_tests = len(self.get_stable_tests())
        
        total_runs = len(self._reports)
        total_duration = sum(r.duration for r in self._reports)

        return {
            "total_tests": total_tests,
            "flaky_tests": flaky_tests,
            "stable_tests": stable_tests,
            "flaky_rate": flaky_tests / total_tests if total_tests > 0 else 0.0,
            "total_runs": total_runs,
            "total_duration": round(total_duration, 2),
        }

    def _parse_report_data(
        self, data: Dict[str, Any], filepath: Path, run_index: int
    ) -> ParsedReport:
        """Извлечь данные из JSON-структуры отчета."""
        summary = data.get("summary", {})
        tests_data = data.get("tests", [])

        tests = []
        for test_data in tests_data:
            test_result = self._parse_test_data(test_data, run_index)
            if test_result:
                tests.append(test_result)

        return ParsedReport(
            filepath=filepath,
            run_index=run_index,
            total_tests=summary.get("total", len(tests)),
            passed=summary.get("passed", 0),
            failed=summary.get("failed", 0),
            errors=summary.get("error", 0),
            skipped=summary.get("skipped", 0),
            duration=data.get("duration", 0.0),
            tests=tests,
        )

    def _parse_test_data(
        self, test_data: Dict[str, Any], run_index: int
    ) -> Optional[TestResult]:
        """Извлечь данные одного теста."""
        node_id = test_data.get("nodeid", "")
        if not node_id:
            return None

        outcome = test_data.get("outcome", "")
        try:
            status = TestStatus(outcome)
        except ValueError:
            status = TestStatus.ERROR

        name = node_id.split("::")[-1] if "::" in node_id else node_id

        call_data = test_data.get("call", {})
        duration = call_data.get("duration", 0.0)

        error_message = ""
        longrepr = ""
        if status in (TestStatus.FAILED, TestStatus.ERROR):
            longrepr = call_data.get("longrepr", "")
            crash = call_data.get("crash", {})
            error_message = crash.get("message", "")

        return TestResult(
            node_id=node_id,
            name=name,
            status=status,
            duration=duration,
            run_index=run_index,
            error_message=error_message,
            longrepr=longrepr,
        )

    def _build_test_histories(self) -> None:
        """Построить историю прогонов для каждого теста."""
        self._test_histories.clear()

        for report in self._reports:
            for test_result in report.tests:
                node_id = test_result.node_id
                
                if node_id not in self._test_histories:
                    self._test_histories[node_id] = TestHistory(
                        node_id=node_id,
                        name=test_result.name,
                    )
                
                self._test_histories[node_id].results.append(test_result)
