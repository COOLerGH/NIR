"""
Модуль классификации flaky-тестов по типам.

Типы flaky-тестов:
- ORDER_DEPENDENT: зависят от порядка выполнения
- NON_DETERMINISTIC: случайное поведение (время, рандом)
- INFRASTRUCTURE: проблемы инфраструктуры (сеть, файлы)
- RESOURCE_LEAK: утечки ресурсов
- TIMING: проблемы с таймингами
- UNKNOWN: не удалось определить
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from detector.parser import TestHistory, TestStatus
from detector.analyzer import AnalysisResult, DependencyType


class FlakyType(Enum):
    """Тип flaky-теста."""
    ORDER_DEPENDENT = "order_dependent"
    NON_DETERMINISTIC = "non_deterministic"
    INFRASTRUCTURE = "infrastructure"
    RESOURCE_LEAK = "resource_leak"
    TIMING = "timing"
    CONCURRENCY = "concurrency"
    UNKNOWN = "unknown"


@dataclass
class Classification:
    """Классификация одного теста."""
    node_id: str
    name: str
    flaky_type: FlakyType
    confidence: float
    reasons: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    related_tests: List[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Результат классификации всех тестов."""
    classifications: List[Classification] = field(default_factory=list)
    summary: Dict[FlakyType, int] = field(default_factory=dict)
    
    def get_by_type(self, flaky_type: FlakyType) -> List[Classification]:
        """Получить классификации по типу."""
        return [c for c in self.classifications if c.flaky_type == flaky_type]
    
    def get_by_node_id(self, node_id: str) -> Optional[Classification]:
        """Получить классификацию по node_id."""
        for c in self.classifications:
            if c.node_id == node_id:
                return c
        return None


class FlakyClassifier:
    """Классификатор flaky-тестов."""

    INFRASTRUCTURE_KEYWORDS = [
        "connection",
        "timeout",
        "network",
        "socket",
        "refused",
        "unreachable",
        "dns",
        "http",
        "ssl",
        "certificate",
    ]

    TIMING_KEYWORDS = [
        "timeout",
        "sleep",
        "wait",
        "async",
        "deadline",
        "expired",
        "slow",
        "time",
    ]

    RESOURCE_KEYWORDS = [
        "memory",
        "file",
        "handle",
        "descriptor",
        "leak",
        "resource",
        "permission",
        "denied",
        "locked",
    ]

    CONCURRENCY_KEYWORDS = [
        "thread",
        "lock",
        "deadlock",
        "race",
        "concurrent",
        "parallel",
        "mutex",
        "semaphore",
    ]

    def __init__(self):
        self._test_histories: Dict[str, TestHistory] = {}
        self._analysis_result: Optional[AnalysisResult] = None

    def classify(
        self,
        test_histories: Dict[str, TestHistory],
        analysis_result: Optional[AnalysisResult] = None
    ) -> ClassificationResult:
        """
        Классифицировать все flaky-тесты.

        Args:
            test_histories: история прогонов тестов
            analysis_result: результат анализа зависимостей

        Returns:
            ClassificationResult с классификациями
        """
        self._test_histories = test_histories
        self._analysis_result = analysis_result

        result = ClassificationResult()

        flaky_tests = [
            node_id for node_id, history in test_histories.items()
            if history.is_flaky
        ]

        for node_id in flaky_tests:
            classification = self._classify_test(node_id)
            result.classifications.append(classification)

        result.summary = self._build_summary(result.classifications)

        return result

    def classify_single(
        self,
        node_id: str,
        history: TestHistory,
        analysis_result: Optional[AnalysisResult] = None
    ) -> Classification:
        """
        Классифицировать один тест.

        Args:
            node_id: идентификатор теста
            history: история прогонов
            analysis_result: результат анализа

        Returns:
            Classification для теста
        """
        self._test_histories = {node_id: history}
        self._analysis_result = analysis_result
        return self._classify_test(node_id)

    def _classify_test(self, node_id: str) -> Classification:
        """Классифицировать один тест."""
        history = self._test_histories.get(node_id)
        if not history:
            return Classification(
                node_id=node_id,
                name=node_id.split("::")[-1],
                flaky_type=FlakyType.UNKNOWN,
                confidence=0.0,
            )

        scores: Dict[FlakyType, float] = {
            FlakyType.ORDER_DEPENDENT: 0.0,
            FlakyType.NON_DETERMINISTIC: 0.0,
            FlakyType.INFRASTRUCTURE: 0.0,
            FlakyType.RESOURCE_LEAK: 0.0,
            FlakyType.TIMING: 0.0,
            FlakyType.CONCURRENCY: 0.0,
        }

        reasons: List[str] = []
        related_tests: List[str] = []

        od_score, od_reasons, od_related = self._check_order_dependent(node_id)
        scores[FlakyType.ORDER_DEPENDENT] = od_score
        reasons.extend(od_reasons)
        related_tests.extend(od_related)

        error_messages = self._get_error_messages(history)

        infra_score = self._check_keywords(error_messages, self.INFRASTRUCTURE_KEYWORDS)
        scores[FlakyType.INFRASTRUCTURE] = infra_score
        if infra_score > 0.5:
            reasons.append("Infrastructure-related errors detected")

        timing_score = self._check_keywords(error_messages, self.TIMING_KEYWORDS)
        scores[FlakyType.TIMING] = timing_score
        if timing_score > 0.5:
            reasons.append("Timing-related errors detected")

        resource_score = self._check_keywords(error_messages, self.RESOURCE_KEYWORDS)
        scores[FlakyType.RESOURCE_LEAK] = resource_score
        if resource_score > 0.5:
            reasons.append("Resource-related errors detected")

        concurrency_score = self._check_keywords(error_messages, self.CONCURRENCY_KEYWORDS)
        scores[FlakyType.CONCURRENCY] = concurrency_score
        if concurrency_score > 0.5:
            reasons.append("Concurrency-related errors detected")

        if max(scores.values()) < 0.3:
            scores[FlakyType.NON_DETERMINISTIC] = 0.5
            reasons.append("No specific pattern detected, likely non-deterministic")

        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]

        recommendations = self._get_recommendations(best_type, reasons)

        return Classification(
            node_id=node_id,
            name=history.name,
            flaky_type=best_type,
            confidence=round(confidence, 3),
            reasons=reasons,
            recommendations=recommendations,
            related_tests=related_tests,
        )

    def _check_order_dependent(self, node_id: str) -> tuple:
        """Проверить на order-dependent."""
        score = 0.0
        reasons = []
        related = []

        if not self._analysis_result:
            return score, reasons, related

        if node_id in self._analysis_result.order_dependent_tests:
            score = 0.8
            reasons.append("Test behavior depends on execution order")

        for dep in self._analysis_result.dependencies:
            if dep.victim_id == node_id:
                score = max(score, dep.confidence)
                related.append(dep.polluter_id)
                reasons.append(f"Polluted by: {dep.polluter_id}")

        if node_id in self._analysis_result.polluters:
            score = max(score, 0.6)
            reasons.append("Test pollutes global state")

        return score, reasons, related

    def _get_error_messages(self, history: TestHistory) -> str:
        """Собрать все сообщения об ошибках."""
        messages = []
        for result in history.results:
            if result.status in (TestStatus.FAILED, TestStatus.ERROR):
                if result.error_message:
                    messages.append(result.error_message.lower())
                if result.longrepr:
                    messages.append(result.longrepr.lower())
        return " ".join(messages)

    def _check_keywords(self, text: str, keywords: List[str]) -> float:
        """Проверить наличие ключевых слов."""
        if not text:
            return 0.0

        matches = sum(1 for kw in keywords if kw in text)
        return min(matches / 3, 1.0)

    def _get_recommendations(
        self, flaky_type: FlakyType, reasons: List[str]
    ) -> List[str]:
        """Получить рекомендации по исправлению."""
        recommendations = {
            FlakyType.ORDER_DEPENDENT: [
                "Add proper setUp/tearDown to isolate test state",
                "Use fresh fixtures for each test",
                "Clear shared state (cache, database) between tests",
                "Consider using pytest-randomly to detect order issues",
            ],
            FlakyType.NON_DETERMINISTIC: [
                "Fix random seeds for reproducibility",
                "Mock time-dependent functions",
                "Avoid relying on dictionary ordering",
                "Check for floating-point comparison issues",
            ],
            FlakyType.INFRASTRUCTURE: [
                "Add retries for network operations",
                "Mock external services in tests",
                "Use testcontainers for dependencies",
                "Add proper timeout handling",
            ],
            FlakyType.RESOURCE_LEAK: [
                "Ensure all files are properly closed",
                "Use context managers for resources",
                "Add cleanup in tearDown methods",
                "Check for connection pool exhaustion",
            ],
            FlakyType.TIMING: [
                "Replace sleep() with proper synchronization",
                "Use polling instead of fixed delays",
                "Increase timeouts for slow CI environments",
                "Mock time-dependent behavior",
            ],
            FlakyType.CONCURRENCY: [
                "Add proper locking mechanisms",
                "Avoid shared mutable state",
                "Use thread-safe data structures",
                "Consider sequential test execution",
            ],
            FlakyType.UNKNOWN: [
                "Add more detailed logging",
                "Run test in isolation multiple times",
                "Check for environment-specific issues",
                "Review recent code changes",
            ],
        }
        return recommendations.get(flaky_type, [])

    def _build_summary(
        self, classifications: List[Classification]
    ) -> Dict[FlakyType, int]:
        """Построить сводку по типам."""
        summary = {t: 0 for t in FlakyType}
        for c in classifications:
            summary[c.flaky_type] += 1
        return summary
