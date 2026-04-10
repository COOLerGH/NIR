"""
Модуль анализа паттернов order-dependent flaky-тестов.

Выявляет связи victim-polluter:
- victim: тест, который падает из-за побочных эффектов другого теста
- polluter: тест, который загрязняет глобальное состояние
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from detector.parser import TestHistory, TestResult, TestStatus


class DependencyType(Enum):
    """Тип зависимости между тестами."""
    POLLUTER_VICTIM = "polluter_victim"
    STATE_SETTER = "state_setter"
    BRITTLE = "brittle"
    UNKNOWN = "unknown"


@dataclass
class TestDependency:
    """Зависимость между двумя тестами."""
    victim_id: str
    polluter_id: str
    dependency_type: DependencyType
    confidence: float
    occurrences: int = 0
    description: str = ""


@dataclass
class OrderAnalysis:
    """Результат анализа одного порядка выполнения."""
    run_index: int
    test_order: List[str]
    failed_tests: List[str]
    passed_tests: List[str]


@dataclass
class AnalysisResult:
    """Полный результат анализа flaky-тестов."""
    flaky_tests: List[str] = field(default_factory=list)
    order_dependent_tests: List[str] = field(default_factory=list)
    dependencies: List[TestDependency] = field(default_factory=list)
    polluters: Set[str] = field(default_factory=set)
    victims: Set[str] = field(default_factory=set)
    confidence_scores: Dict[str, float] = field(default_factory=dict)


class FlakyAnalyzer:
    """Анализатор паттернов order-dependent тестов."""

    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence
        self._order_analyses: List[OrderAnalysis] = []
        self._test_histories: Dict[str, TestHistory] = {}

    def analyze(
        self,
        test_histories: Dict[str, TestHistory],
        order_analyses: Optional[List[OrderAnalysis]] = None
    ) -> AnalysisResult:
        """
        Провести полный анализ flaky-тестов.

        Args:
            test_histories: история прогонов тестов
            order_analyses: анализ порядков выполнения

        Returns:
            AnalysisResult с результатами анализа
        """
        self._test_histories = test_histories
        self._order_analyses = order_analyses or []

        result = AnalysisResult()

        result.flaky_tests = self._find_flaky_tests()

        if self._order_analyses:
            result.order_dependent_tests = self._find_order_dependent_tests()
            result.dependencies = self._find_dependencies()
            
            for dep in result.dependencies:
                result.polluters.add(dep.polluter_id)
                result.victims.add(dep.victim_id)

        result.confidence_scores = self._calculate_confidence_scores(result)

        return result

    def analyze_from_results(
        self,
        test_histories: Dict[str, TestHistory]
    ) -> AnalysisResult:
        """
        Анализ только на основе историй тестов без информации о порядке.

        Args:
            test_histories: история прогонов тестов

        Returns:
            AnalysisResult с результатами анализа
        """
        self._test_histories = test_histories
        self._order_analyses = []

        result = AnalysisResult()
        result.flaky_tests = self._find_flaky_tests()
        result.confidence_scores = self._calculate_confidence_scores(result)

        return result

    def build_order_analysis(
        self,
        run_index: int,
        test_order: List[str],
        results: List[TestResult]
    ) -> OrderAnalysis:
        """
        Построить анализ одного порядка выполнения.

        Args:
            run_index: индекс прогона
            test_order: порядок выполнения тестов
            results: результаты тестов

        Returns:
            OrderAnalysis для данного прогона
        """
        failed = []
        passed = []

        results_map = {r.node_id: r for r in results}

        for node_id in test_order:
            if node_id in results_map:
                if results_map[node_id].status == TestStatus.PASSED:
                    passed.append(node_id)
                elif results_map[node_id].status in (TestStatus.FAILED, TestStatus.ERROR):
                    failed.append(node_id)

        return OrderAnalysis(
            run_index=run_index,
            test_order=test_order,
            failed_tests=failed,
            passed_tests=passed,
        )

    def _find_flaky_tests(self) -> List[str]:
        """Найти все flaky-тесты."""
        flaky = []
        for node_id, history in self._test_histories.items():
            if history.is_flaky:
                flaky.append(node_id)
        return flaky

    def _find_order_dependent_tests(self) -> List[str]:
        """Найти тесты, зависящие от порядка выполнения."""
        if len(self._order_analyses) < 2:
            return []

        order_dependent = set()

        for node_id in self._find_flaky_tests():
            if self._is_order_dependent(node_id):
                order_dependent.add(node_id)

        return list(order_dependent)

    def _is_order_dependent(self, node_id: str) -> bool:
        """Проверить, зависит ли тест от порядка выполнения."""
        pass_positions = []
        fail_positions = []

        for analysis in self._order_analyses:
            if node_id not in analysis.test_order:
                continue

            position = analysis.test_order.index(node_id)

            if node_id in analysis.passed_tests:
                pass_positions.append(position)
            elif node_id in analysis.failed_tests:
                fail_positions.append(position)

        if not pass_positions or not fail_positions:
            return False

        avg_pass_pos = sum(pass_positions) / len(pass_positions)
        avg_fail_pos = sum(fail_positions) / len(fail_positions)

        return abs(avg_pass_pos - avg_fail_pos) > 1

    def _find_dependencies(self) -> List[TestDependency]:
        """Найти зависимости victim-polluter."""
        dependencies = []
        flaky_tests = set(self._find_flaky_tests())

        for victim_id in flaky_tests:
            potential_polluters = self._find_potential_polluters(victim_id)
            
            for polluter_id, confidence, occurrences in potential_polluters:
                if confidence >= self.min_confidence:
                    dep = TestDependency(
                        victim_id=victim_id,
                        polluter_id=polluter_id,
                        dependency_type=DependencyType.POLLUTER_VICTIM,
                        confidence=confidence,
                        occurrences=occurrences,
                        description=f"{polluter_id} pollutes state for {victim_id}",
                    )
                    dependencies.append(dep)

        return dependencies

    def _find_potential_polluters(
        self, victim_id: str
    ) -> List[Tuple[str, float, int]]:
        """
        Найти потенциальных загрязнителей для жертвы.

        Returns:
            список (polluter_id, confidence, occurrences)
        """
        polluter_stats: Dict[str, Dict[str, int]] = {}

        for analysis in self._order_analyses:
            if victim_id not in analysis.test_order:
                continue

            victim_pos = analysis.test_order.index(victim_id)
            victim_failed = victim_id in analysis.failed_tests

            for i, test_id in enumerate(analysis.test_order):
                if i >= victim_pos:
                    break
                if test_id == victim_id:
                    continue

                if test_id not in polluter_stats:
                    polluter_stats[test_id] = {
                        "before_and_failed": 0,
                        "before_and_passed": 0,
                    }

                if victim_failed:
                    polluter_stats[test_id]["before_and_failed"] += 1
                else:
                    polluter_stats[test_id]["before_and_passed"] += 1

        results = []
        for polluter_id, stats in polluter_stats.items():
            total = stats["before_and_failed"] + stats["before_and_passed"]
            if total < 2:
                continue

            fail_rate_when_before = stats["before_and_failed"] / total

            not_before_failed = 0
            not_before_passed = 0

            for analysis in self._order_analyses:
                if victim_id not in analysis.test_order:
                    continue
                if polluter_id not in analysis.test_order:
                    continue

                victim_pos = analysis.test_order.index(victim_id)
                polluter_pos = analysis.test_order.index(polluter_id)

                if polluter_pos > victim_pos:
                    if victim_id in analysis.failed_tests:
                        not_before_failed += 1
                    else:
                        not_before_passed += 1

            not_before_total = not_before_failed + not_before_passed
            if not_before_total > 0:
                fail_rate_when_not_before = not_before_failed / not_before_total
                confidence = fail_rate_when_before - fail_rate_when_not_before
            else:
                confidence = fail_rate_when_before

            if confidence > 0:
                results.append((
                    polluter_id,
                    min(confidence, 1.0),
                    stats["before_and_failed"],
                ))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _calculate_confidence_scores(
        self, result: AnalysisResult
    ) -> Dict[str, float]:
        """Рассчитать confidence score для каждого flaky-теста."""
        scores = {}

        for node_id in result.flaky_tests:
            history = self._test_histories.get(node_id)
            if not history:
                scores[node_id] = 0.0
                continue

            flaky_score = 1.0 - abs(history.pass_rate - 0.5) * 2

            if node_id in result.order_dependent_tests:
                od_score = 0.8
            else:
                od_score = 0.2

            deps_as_victim = [
                d for d in result.dependencies
                if d.victim_id == node_id
            ]
            if deps_as_victim:
                dep_score = max(d.confidence for d in deps_as_victim)
            else:
                dep_score = 0.0

            final_score = (flaky_score * 0.3 + od_score * 0.4 + dep_score * 0.3)
            scores[node_id] = round(final_score, 3)

        return scores

    def get_polluter_impact(self) -> Dict[str, List[str]]:
        """
        Получить влияние каждого загрязнителя.

        Returns:
            словарь polluter_id -> список victim_id
        """
        impact: Dict[str, List[str]] = {}
        
        for analysis in [self.analyze(self._test_histories, self._order_analyses)]:
            for dep in analysis.dependencies:
                if dep.polluter_id not in impact:
                    impact[dep.polluter_id] = []
                if dep.victim_id not in impact[dep.polluter_id]:
                    impact[dep.polluter_id].append(dep.victim_id)

        return impact
