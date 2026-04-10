"""
Пакет генерации отчётов.

Содержит модули:
- aggregator: агрегация статистики прогонов
- exporter: экспорт в форматы JSON, HTML, Allure
"""

from reports.aggregator import StatsAggregator, AggregatedStats
from reports.exporter import ReportExporter


__all__ = [
    "StatsAggregator",
    "AggregatedStats",
    "ReportExporter",
]
