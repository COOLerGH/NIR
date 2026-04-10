"""
Фикстуры для тестов системы детектирования.
"""

import pytest
import json
import tempfile
from pathlib import Path

from detector.parser import TestStatus, TestResult, TestHistory, ParsedReport
from detector.analyzer import AnalysisResult, OrderAnalysis
from detector.classifier import FlakyType, Classification, ClassificationResult
from quarantine.manager import QuarantineManager


@pytest.fixture
def temp_dir():
    """Временная директория для тестов."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_test_result():
    """Пример результата теста."""
    return TestResult(
        node_id="tests/test_example.py::TestClass::test_method",
        name="test_method",
        status=TestStatus.PASSED,
        duration=0.05,
        run_index=0,
    )


@pytest.fixture
def sample_failed_result():
    """Пример упавшего теста."""
    return TestResult(
        node_id="tests/test_example.py::TestClass::test_flaky",
        name="test_flaky",
        status=TestStatus.FAILED,
        duration=0.03,
        run_index=0,
        error_message="AssertionError: expected True",
    )


@pytest.fixture
def sample_test_history():
    """История прогонов теста."""
    history = TestHistory(
        node_id="tests/test_example.py::TestClass::test_method",
        name="test_method",
    )
    history.results = [
        TestResult(
            node_id="tests/test_example.py::TestClass::test_method",
            name="test_method",
            status=TestStatus.PASSED,
            duration=0.05,
            run_index=0,
        ),
        TestResult(
            node_id="tests/test_example.py::TestClass::test_method",
            name="test_method",
            status=TestStatus.PASSED,
            duration=0.04,
            run_index=1,
        ),
    ]
    return history


@pytest.fixture
def flaky_test_history():
    """История flaky-теста (есть и passed и failed)."""
    history = TestHistory(
        node_id="tests/test_example.py::TestClass::test_flaky",
        name="test_flaky",
    )
    history.results = [
        TestResult(
            node_id="tests/test_example.py::TestClass::test_flaky",
            name="test_flaky",
            status=TestStatus.PASSED,
            duration=0.05,
            run_index=0,
        ),
        TestResult(
            node_id="tests/test_example.py::TestClass::test_flaky",
            name="test_flaky",
            status=TestStatus.FAILED,
            duration=0.03,
            run_index=1,
            error_message="AssertionError",
        ),
        TestResult(
            node_id="tests/test_example.py::TestClass::test_flaky",
            name="test_flaky",
            status=TestStatus.PASSED,
            duration=0.04,
            run_index=2,
        ),
    ]
    return history


@pytest.fixture
def sample_json_report(temp_dir):
    """Пример JSON-отчёта pytest."""
    report_data = {
        "summary": {
            "total": 3,
            "passed": 2,
            "failed": 1,
            "error": 0,
            "skipped": 0,
        },
        "duration": 1.5,
        "tests": [
            {
                "nodeid": "tests/test_a.py::test_one",
                "outcome": "passed",
                "call": {"duration": 0.1},
            },
            {
                "nodeid": "tests/test_a.py::test_two",
                "outcome": "passed",
                "call": {"duration": 0.2},
            },
            {
                "nodeid": "tests/test_a.py::test_three",
                "outcome": "failed",
                "call": {
                    "duration": 0.15,
                    "longrepr": "AssertionError: test failed",
                    "crash": {"message": "AssertionError"},
                },
            },
        ],
    }
    
    report_file = temp_dir / "report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f)
    
    return report_file


@pytest.fixture
def quarantine_manager(temp_dir):
    """Менеджер карантина с временной директорией."""
    return QuarantineManager(quarantine_dir=temp_dir)
