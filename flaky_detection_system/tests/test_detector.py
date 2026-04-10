"""
Тесты модулей детектирования flaky-тестов.
"""

import pytest
from pathlib import Path

from detector.parser import ResultsParser, TestStatus, TestResult, TestHistory
from detector.analyzer import FlakyAnalyzer, OrderAnalysis, DependencyType
from detector.classifier import FlakyClassifier, FlakyType


class TestResultsParser:
    """Тесты парсера результатов."""

    def test_parse_file_success(self, sample_json_report):
        """Парсинг валидного JSON-отчёта."""
        parser = ResultsParser()
        report = parser.parse_file(sample_json_report, run_index=0)
        
        assert report is not None
        assert report.total_tests == 3
        assert report.passed == 2
        assert report.failed == 1
        assert len(report.tests) == 3

    def test_parse_file_not_found(self, temp_dir):
        """Парсинг несуществующего файла."""
        parser = ResultsParser()
        report = parser.parse_file(temp_dir / "nonexistent.json")
        
        assert report is None

    def test_parse_multiple_builds_histories(self, sample_json_report, temp_dir):
        """Парсинг нескольких файлов строит историю."""
        parser = ResultsParser()
        reports = parser.parse_multiple([sample_json_report])
        
        histories = parser.get_test_histories()
        
        assert len(histories) == 3
        assert "tests/test_a.py::test_one" in histories

    def test_get_flaky_tests_empty_when_stable(self, sample_test_history):
        """Стабильные тесты не попадают в flaky."""
        parser = ResultsParser()
        parser._test_histories = {
            sample_test_history.node_id: sample_test_history
        }
        
        flaky = parser.get_flaky_tests()
        
        assert len(flaky) == 0

    def test_get_flaky_tests_detects_flaky(self, flaky_test_history):
        """Flaky-тесты обнаруживаются."""
        parser = ResultsParser()
        parser._test_histories = {
            flaky_test_history.node_id: flaky_test_history
        }
        
        flaky = parser.get_flaky_tests()
        
        assert len(flaky) == 1
        assert flaky[0].node_id == flaky_test_history.node_id


class TestTestHistory:
    """Тесты класса TestHistory."""

    def test_is_flaky_false_for_all_passed(self, sample_test_history):
        """Тест не flaky если все прогоны passed."""
        assert not sample_test_history.is_flaky

    def test_is_flaky_true_for_mixed(self, flaky_test_history):
        """Тест flaky если есть и passed и failed."""
        assert flaky_test_history.is_flaky

    def test_pass_rate_calculation(self, flaky_test_history):
        """Расчёт pass rate."""
        # 2 passed из 3
        assert flaky_test_history.pass_rate == pytest.approx(2/3, rel=0.01)

    def test_avg_duration(self, flaky_test_history):
        """Расчёт среднего времени."""
        # (0.05 + 0.03 + 0.04) / 3 = 0.04
        assert flaky_test_history.avg_duration == pytest.approx(0.04, rel=0.01)


class TestFlakyAnalyzer:
    """Тесты анализатора flaky-тестов."""

    def test_analyze_finds_flaky(self, flaky_test_history, sample_test_history):
        """Анализатор находит flaky-тесты."""
        histories = {
            flaky_test_history.node_id: flaky_test_history,
            sample_test_history.node_id: sample_test_history,
        }
        
        analyzer = FlakyAnalyzer()
        result = analyzer.analyze_from_results(histories)
        
        assert len(result.flaky_tests) == 1
        assert flaky_test_history.node_id in result.flaky_tests

    def test_analyze_empty_histories(self):
        """Анализ пустой истории."""
        analyzer = FlakyAnalyzer()
        result = analyzer.analyze_from_results({})
        
        assert len(result.flaky_tests) == 0
        assert len(result.dependencies) == 0

    def test_build_order_analysis(self):
        """Построение анализа порядка выполнения."""
        analyzer = FlakyAnalyzer()
        
        test_order = ["test_a", "test_b", "test_c"]
        results = [
            TestResult("test_a", "test_a", TestStatus.PASSED, 0.1, 0),
            TestResult("test_b", "test_b", TestStatus.FAILED, 0.1, 0),
            TestResult("test_c", "test_c", TestStatus.PASSED, 0.1, 0),
        ]
        
        analysis = analyzer.build_order_analysis(0, test_order, results)
        
        assert analysis.run_index == 0
        assert len(analysis.passed_tests) == 2
        assert len(analysis.failed_tests) == 1
        assert "test_b" in analysis.failed_tests


class TestFlakyClassifier:
    """Тесты классификатора flaky-тестов."""

    def test_classify_returns_classification(self, flaky_test_history):
        """Классификация возвращает результат."""
        histories = {flaky_test_history.node_id: flaky_test_history}
        
        classifier = FlakyClassifier()
        result = classifier.classify(histories)
        
        assert len(result.classifications) == 1
        assert result.classifications[0].node_id == flaky_test_history.node_id

    def test_classify_single(self, flaky_test_history):
        """Классификация одного теста."""
        classifier = FlakyClassifier()
        classification = classifier.classify_single(
            flaky_test_history.node_id,
            flaky_test_history,
        )
        
        assert classification.node_id == flaky_test_history.node_id
        assert classification.flaky_type in FlakyType
        assert len(classification.recommendations) > 0

    def test_classify_stable_not_included(self, sample_test_history):
        """Стабильные тесты не классифицируются."""
        histories = {sample_test_history.node_id: sample_test_history}
        
        classifier = FlakyClassifier()
        result = classifier.classify(histories)
        
        assert len(result.classifications) == 0

    def test_summary_counts_types(self, flaky_test_history):
        """Summary подсчитывает типы."""
        histories = {flaky_test_history.node_id: flaky_test_history}
        
        classifier = FlakyClassifier()
        result = classifier.classify(histories)
        
        assert isinstance(result.summary, dict)
        total = sum(result.summary.values())
        assert total == 1
