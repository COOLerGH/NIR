"""
Пакет детектирования flaky-тестов.

Содержит модули:
- runner: запуск тестов через pytest-flakefinder
- parser: парсинг результатов прогонов
- analyzer: анализ паттернов victim-polluter
- classifier: классификация типов flaky-тестов
"""

from detector.runner import TestRunner
from detector.parser import ResultsParser
from detector.analyzer import FlakyAnalyzer
from detector.classifier import FlakyClassifier


__all__ = [
    "TestRunner",
    "ResultsParser",
    "FlakyAnalyzer",
    "FlakyClassifier",
]
