"""
Модуль управления карантином flaky-тестов.

Хранит список тестов в карантине, управляет сроками
и предоставляет API для добавления/удаления тестов.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict

from config import QUARANTINE_DIR, load_thresholds


@dataclass
class QuarantinedTest:
    """Информация о тесте в карантине."""
    node_id: str
    name: str
    reason: str
    flaky_type: str
    confidence: float
    added_date: str
    expire_date: str
    pass_rate: float = 0.0
    total_runs: int = 0
    polluters: List[str] = field(default_factory=list)
    is_active: bool = True

    def is_expired(self) -> bool:
        """Проверить истёк ли срок карантина."""
        expire = datetime.fromisoformat(self.expire_date)
        return datetime.now() > expire

    def days_remaining(self) -> int:
        """Количество дней до истечения карантина."""
        expire = datetime.fromisoformat(self.expire_date)
        delta = expire - datetime.now()
        return max(0, delta.days)


class QuarantineManager:
    """Менеджер карантина flaky-тестов."""

    QUARANTINE_FILE = "quarantine.json"

    def __init__(self, quarantine_dir: Optional[Path] = None):
        self.quarantine_dir = quarantine_dir or QUARANTINE_DIR
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_file = self.quarantine_dir / self.QUARANTINE_FILE
        self._quarantined: Dict[str, QuarantinedTest] = {}
        self._load()

    def add(
        self,
        node_id: str,
        name: str,
        reason: str,
        flaky_type: str = "unknown",
        confidence: float = 0.0,
        pass_rate: float = 0.0,
        total_runs: int = 0,
        polluters: Optional[List[str]] = None,
        duration_days: Optional[int] = None,
    ) -> QuarantinedTest:
        """
        Добавить тест в карантин.

        Args:
            node_id: идентификатор теста
            name: имя теста
            reason: причина карантина
            flaky_type: тип flaky-теста
            confidence: уверенность классификации
            pass_rate: процент успешных прогонов
            total_runs: общее количество прогонов
            polluters: список загрязнителей
            duration_days: срок карантина в днях

        Returns:
            QuarantinedTest
        """
        if duration_days is None:
            thresholds = load_thresholds()
            duration_days = thresholds.get("quarantine", {}).get(
                "quarantine_duration_days", 7
            )

        now = datetime.now()
        expire = now + timedelta(days=duration_days)

        test = QuarantinedTest(
            node_id=node_id,
            name=name,
            reason=reason,
            flaky_type=flaky_type,
            confidence=confidence,
            added_date=now.isoformat(),
            expire_date=expire.isoformat(),
            pass_rate=pass_rate,
            total_runs=total_runs,
            polluters=polluters or [],
            is_active=True,
        )

        self._quarantined[node_id] = test
        self._save()
        return test

    def remove(self, node_id: str) -> bool:
        """
        Удалить тест из карантина.

        Args:
            node_id: идентификатор теста

        Returns:
            True если тест был удалён
        """
        if node_id in self._quarantined:
            del self._quarantined[node_id]
            self._save()
            return True
        return False

    def deactivate(self, node_id: str) -> bool:
        """
        Деактивировать тест в карантине (не удаляя запись).

        Args:
            node_id: идентификатор теста

        Returns:
            True если тест был деактивирован
        """
        if node_id in self._quarantined:
            self._quarantined[node_id].is_active = False
            self._save()
            return True
        return False

    def get(self, node_id: str) -> Optional[QuarantinedTest]:
        """Получить информацию о тесте в карантине."""
        return self._quarantined.get(node_id)

    def get_all(self) -> List[QuarantinedTest]:
        """Получить все тесты в карантине."""
        return list(self._quarantined.values())

    def get_active(self) -> List[QuarantinedTest]:
        """Получить активные тесты в карантине."""
        return [t for t in self._quarantined.values() if t.is_active]

    def get_expired(self) -> List[QuarantinedTest]:
        """Получить тесты с истёкшим сроком карантина."""
        return [t for t in self._quarantined.values() if t.is_expired()]

    def is_quarantined(self, node_id: str) -> bool:
        """Проверить находится ли тест в активном карантине."""
        test = self._quarantined.get(node_id)
        return test is not None and test.is_active and not test.is_expired()

    def cleanup_expired(self) -> List[str]:
        """
        Деактивировать тесты с истёкшим сроком.

        Returns:
            список node_id деактивированных тестов
        """
        expired = []
        for node_id, test in self._quarantined.items():
            if test.is_active and test.is_expired():
                test.is_active = False
                expired.append(node_id)

        if expired:
            self._save()
        return expired

    def extend(self, node_id: str, days: int) -> bool:
        """
        Продлить срок карантина.

        Args:
            node_id: идентификатор теста
            days: количество дней для продления

        Returns:
            True если срок был продлён
        """
        if node_id not in self._quarantined:
            return False

        test = self._quarantined[node_id]
        current_expire = datetime.fromisoformat(test.expire_date)
        new_expire = current_expire + timedelta(days=days)
        test.expire_date = new_expire.isoformat()
        test.is_active = True
        self._save()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику карантина."""
        all_tests = list(self._quarantined.values())
        active = [t for t in all_tests if t.is_active]
        expired = [t for t in all_tests if t.is_expired()]

        by_type: Dict[str, int] = {}
        for test in active:
            by_type[test.flaky_type] = by_type.get(test.flaky_type, 0) + 1

        return {
            "total": len(all_tests),
            "active": len(active),
            "expired": len(expired),
            "by_type": by_type,
        }

    def get_node_ids(self) -> List[str]:
        """Получить список node_id активных тестов в карантине."""
        return [t.node_id for t in self.get_active()]

    def _load(self) -> None:
        """Загрузить данные из файла."""
        if not self.quarantine_file.exists():
            self._quarantined = {}
            return

        try:
            with open(self.quarantine_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._quarantined = {}
            return

        self._quarantined = {}
        for node_id, test_data in data.items():
            self._quarantined[node_id] = QuarantinedTest(**test_data)

    def _save(self) -> None:
        """Сохранить данные в файл."""
        data = {
            node_id: asdict(test)
            for node_id, test in self._quarantined.items()
        }
        with open(self.quarantine_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
