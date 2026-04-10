"""
Пакет управления карантином flaky-тестов.

Содержит модули:
- manager: управление списком карантинных тестов
- marker: применение pytest.mark.flaky к тестам
- config_updater: модификация конфигурации пайплайна
"""

from quarantine.manager import QuarantineManager, QuarantinedTest
from quarantine.marker import TestMarker
from quarantine.config_updater import ConfigUpdater


__all__ = [
    "QuarantineManager",
    "QuarantinedTest",
    "TestMarker",
    "ConfigUpdater",
]
