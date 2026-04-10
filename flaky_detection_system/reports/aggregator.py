"""
Модуль агрегации статистики прогонов.

Собирает и обрабатывает метрики из результатов
тестовых прогонов для формирования отчётов.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from detector.parser import TestHistory, ParsedReport, TestStatus
from detector.analyzer import AnalysisResult
from detector.classifier import ClassificationResult, FlakyType
from quarantine.manager import QuarantineManager


@dataclass
class TestStats:
    """Статистика одного теста."""
    node_id: str
    name: str
    total_runs: int
    passed: int
    failed: int
    pass_rate: float
    avg_duration: float
    min_duration: float
    max_duration: float
    is_flaky: bool
    flaky_type: Optional[str] = None
    is_quarantined: bool = False


@dataclass
class AggregatedStats:
    """Агрегированная статистика."""
    timestamp: str
    total_tests: int
    total_runs: int
    total_duration: float
    flaky_count: int
    stable_count: int
    quarantined_count: int
    flaky_rate: float
    pass_rate: float
    tests: List[TestStats] = field(default_factory=list)
    by_type: Dict[str, int] = field(default_factory=dict)
    trends: Dict[str, Any] = field(default_factory=dict)


class StatsAggregator:
    """Агрегатор статистики тестовых прогонов."""

    def __init__(self):
        self._test_histories: Dict[str, TestHistory] = {}
        self._reports: List[ParsedReport] = []
        self._analysis: Optional[AnalysisResult] = None
        self._classification: Optional[ClassificationResult] = None
        self._quarantine: Optional[QuarantineManager] = None

    def aggregate(
        self,
        test_histories: Dict[str, TestHistory],
        reports: Optional[List[ParsedReport]] = None,
        analysis: Optional[AnalysisResult] = None,
        classification: Optional[ClassificationResult] = None,
        quarantine: Optional[QuarantineManager] = None
    ) -> AggregatedStats:
        """
        Агрегировать статистику из всех источников.

        Args:
            test_histories: история прогонов тестов
            reports: список отчётов прогонов
            analysis: результат анализа
            classification: результат классификации
            quarantine: менеджер карантина

        Returns:
            AggregatedStats
        """
        self._test_histories = test_histories
        self._reports = reports or []
        self._analysis = analysis
        self._classification = classification
        self._quarantine = quarantine

        test_stats = self._build_test_stats()
        
        flaky_count = sum(1 for t in test_stats if t.is_flaky)
        stable_count = sum(1 for t in test_stats if not t.is_flaky)
        quarantined_count = sum(1 for t in test_stats if t.is_quarantined)

        total_passed = sum(t.passed for t in test_stats)
        total_failed = sum(t.failed for t in test_stats)
        total_results = total_passed + total_failed

        return AggregatedStats(
            timestamp=datetime.now().isoformat(),
            total_tests=len(test_stats),
            total_runs=len(self._reports),
            total_duration=sum(r.duration for r in self._reports),
            flaky_count=flaky_count,
            stable_count=stable_count,
            quarantined_count=quarantined_count,
            flaky_rate=flaky_count / len(test_stats) if test_stats else 0.0,
            pass_rate=total_passed / total_results if total_results > 0 else 0.0,
            tests=test_stats,
            by_type=self._count_by_type(),
            trends=self._calculate_trends(),
        )

    def aggregate_from_files(
        self,
        result_files: List[Path],
        quarantine: Optional[QuarantineManager] = None
    ) -> AggregatedStats:
        """
        Агрегировать статистику из файлов результатов.

        Args:
            result_files: список путей к JSON-файлам
            quarantine: менеджер карантина

        Returns:
            AggregatedStats
        """
        from detector.parser import ResultsParser
        from detector.analyzer import FlakyAnalyzer
        from detector.classifier import FlakyClassifier

        parser = ResultsParser()
        reports = parser.parse_multiple(result_files)
        test_histories = parser.get_test_histories()

        analyzer = FlakyAnalyzer()
        analysis = analyzer.analyze_from_results(test_histories)

        classifier = FlakyClassifier()
        classification = classifier.classify(test_histories, analysis)

        return self.aggregate(
            test_histories=test_histories,
            reports=reports,
            analysis=analysis,
            classification=classification,
            quarantine=quarantine,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Получить краткую сводку."""
        stats = self.aggregate(self._test_histories)
        return {
            "total_tests": stats.total_tests,
            "flaky_tests": stats.flaky_count,
            "stable_tests": stats.stable_count,
            "quarantined_tests": stats.quarantined_count,
            "flaky_rate": round(stats.flaky_rate * 100, 2),
            "pass_rate": round(stats.pass_rate * 100, 2),
        }

    def get_flaky_summary(self) -> List[Dict[str, Any]]:
        """Получить сводку по flaky-тестам."""
        result = []

        for node_id, history in self._test_histories.items():
            if not history.is_flaky:
                continue

            flaky_type = None
            if self._classification:
                cls = self._classification.get_by_node_id(node_id)
                if cls:
                    flaky_type = cls.flaky_type.value

            is_quarantined = False
            if self._quarantine:
                is_quarantined = self._quarantine.is_quarantined(node_id)

            result.append({
                "node_id": node_id,
                "name": history.name,
                "pass_rate": round(history.pass_rate * 100, 2),
                "total_runs": history.total_runs,
                "flaky_type": flaky_type,
                "is_quarantined": is_quarantined,
            })

        result.sort(key=lambda x: x["pass_rate"])
        return result

    def _build_test_stats(self) -> List[TestStats]:
        """Построить статистику для каждого теста."""
        stats = []

        for node_id, history in self._test_histories.items():
            durations = [r.duration for r in history.results]

            flaky_type = None
            if self._classification:
                cls = self._classification.get_by_node_id(node_id)
                if cls:
                    flaky_type = cls.flaky_type.value

            is_quarantined = False
            if self._quarantine:
                is_quarantined = self._quarantine.is_quarantined(node_id)

            stats.append(TestStats(
                node_id=node_id,
                name=history.name,
                total_runs=history.total_runs,
                passed=history.passed_count,
                failed=history.failed_count,
                pass_rate=history.pass_rate,
                avg_duration=history.avg_duration,
                min_duration=min(durations) if durations else 0.0,
                max_duration=max(durations) if durations else 0.0,
                is_flaky=history.is_flaky,
                flaky_type=flaky_type,
                is_quarantined=is_quarantined,
            ))

        return stats

    def _count_by_type(self) -> Dict[str, int]:
        """Подсчитать количество тестов по типам."""
        counts: Dict[str, int] = {}

        if not self._classification:
            return counts

        for flaky_type in FlakyType:
            count = len(self._classification.get_by_type(flaky_type))
            if count > 0:
                counts[flaky_type.value] = count

        return counts

    def _calculate_trends(self) -> Dict[str, Any]:
        """Рассчитать тренды по прогонам."""
        if len(self._reports) < 2:
            return {}

        pass_rates = []
        for report in self._reports:
            total = report.passed + report.failed
            if total > 0:
                pass_rates.append(report.passed / total)

        if len(pass_rates) < 2:
            return {}

        first_half = pass_rates[:len(pass_rates) // 2]
        second_half = pass_rates[len(pass_rates) // 2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        trend = "stable"
        if avg_second > avg_first + 0.05:
            trend = "improving"
        elif avg_second < avg_first - 0.05:
            trend = "degrading"

        return {
            "pass_rate_trend": trend,
            "first_half_avg": round(avg_first * 100, 2),
            "second_half_avg": round(avg_second * 100, 2),
        }
