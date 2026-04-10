# Flaky Test Detection System

Система автоматического детектирования и карантина order-dependent flaky-тестов в CI/CD-пайплайне.

## Описание

Система предназначена для выявления нестабильных тестов (flaky tests), результат выполнения которых зависит от порядка запуска в тестовом наборе. Использует многократный прогон тестов с анализом паттернов victim-polluter.

### Возможности

- Многократный прогон тестов для выявления нестабильности
- Классификация flaky-тестов по типам (order-dependent, timing, infrastructure и др.)
- Автоматический карантин обнаруженных тестов
- Генерация отчётов в форматах JSON, HTML
- Интеграция с GitHub Actions

## Структура проекта

flaky_detection_system/
├── config/ # Конфигурация
│ ├── settings.py # Глобальные настройки
│ └── thresholds.json # Пороговые значения
├── detector/ # Модули детектирования
│ ├── runner.py # Запуск тестов
│ ├── parser.py # Парсинг результатов
│ ├── analyzer.py # Анализ паттернов
│ └── classifier.py # Классификация
├── quarantine/ # Модули карантина
│ ├── manager.py # Управление карантином
│ ├── marker.py # Маркировка тестов
│ └── config_updater.py # Обновление конфигурации
├── reports/ # Генерация отчётов
│ ├── aggregator.py # Агрегация статистики
│ └── exporter.py # Экспорт отчётов
├── tests/ # Тесты системы
├── results/ # Результаты прогонов
├── reports/ # Сгенерированные отчёты
├── quarantine/ # Данные карантина
├── main.py # Точка входа
└── requirements.txt # Зависимости

## Установка

```bash
# Клонировать репозиторий
git clone <repository-url>
cd flaky_detection_system

# Установить зависимости
pip install -r requirements.txt
```
## Зависимости

Python 3.10+
pytest >= 8.0.0
pytest-flakefinder >= 1.1.0
pytest-xdist >= 3.5.0
pytest-json-report >= 1.5.0
pytest-html >= 4.1.0

## Использование
# Полный цикл детектирования

```bash
python main.py run-all --runs 10
```

Выполняет:

Многократный запуск тестов (10 прогонов)
Анализ результатов
Автоматический карантин flaky-тестов
Генерация отчётов

# Отдельные команды
```bash
# Детектирование
python main.py detect --runs 10

# Анализ результатов
python main.py analyze --last 10

# Управление карантином
python main.py quarantine --list
python main.py quarantine --add "tests/test_file.py::test_name" --reason "Flaky"
python main.py quarantine --remove "tests/test_file.py::test_name"

# Генерация отчётов
python main.py report --format all
python main.py report --format html
python main.py report --format json
```
# Параметры команд

Команда	Параметр	Описание
detect	--runs N	Количество прогонов (по умолчанию 10)
detect	--workers N	Количество параллельных воркеров
detect	--path PATH	Путь к тестам
analyze	--last N	Анализировать последние N результатов
analyze	--input FILE	Анализировать конкретный файл
quarantine	--list	Показать тесты в карантине
quarantine	--add NODE_ID	Добавить тест в карантин
quarantine	--remove NODE_ID	Удалить тест из карантина
quarantine	--cleanup	Очистить истёкшие записи
quarantine	--apply	Применить маркеры к тестам
report	--format FORMAT	Формат: json, html, allure, all

## Конфигурация
```bash
config/thresholds.json

{
    "detection": {
        "min_runs": 5,
        "flaky_threshold": 0.1,
        "confidence_level": 0.95
    },
    "quarantine": {
        "auto_quarantine": true,
        "max_failures_before_quarantine": 2,
        "quarantine_duration_days": 7
    },
    "runner": {
        "default_runs": 10,
        "max_runs": 100,
        "parallel_workers": 4,
        "timeout_seconds": 300
    }
}
```
## Типы flaky-тестов
Тип	Описание
ORDER_DEPENDENT	Зависит от порядка выполнения тестов
NON_DETERMINISTIC	Случайное поведение (рандом, время)
INFRASTRUCTURE	Проблемы инфраструктуры (сеть, файлы)
TIMING	Проблемы с таймингами
RESOURCE_LEAK	Утечки ресурсов
CONCURRENCY	Проблемы параллельного выполнения

## Паттерн Victim-Polluter
Система выявляет зависимости между тестами:
Polluter — тест, который изменяет глобальное состояние
Victim — тест, который падает если запускается после polluter
Пример:
```bash
# Polluter - загрязняет глобальный кэш
def test_polluter():
    _shared_cache.put("key", "value")

# Victim - ожидает пустой кэш
def test_victim():
    assert _shared_cache.size == 0  # Падает если polluter запустился раньше
```
## Интеграция с CI/CD
# GitHub Actions
Система включает готовый workflow .github/workflows/flaky_detection.yml:

Запуск стабильных тестов (без карантинных)
Запуск карантинных тестов отдельно
Автоматическое детектирование по расписанию
Генерация отчётов

## Отчёты
# HTML-отчёт
Содержит:
Сводную статистику (total, flaky, pass rate)
Распределение по типам
Таблицу flaky-тестов с рекомендациями
Информацию о карантине
# JSON-отчёт
Структурированные данные для автоматизации:
Метаданные прогона
Детальная информация по каждому тесту
Классификация и рекомендации
## Тестирование системы
```bash
# Запуск тестов системы
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ -v --cov=. --cov-report=html
```
# Пример вывода

============================================================
FLAKY TEST DETECTION - FULL CYCLE
============================================================

[1/4] Detection
----------------------------------------
Completed 10/10 runs

[2/4] Analysis
----------------------------------------
Found 7 flaky tests out of 190

[3/4] Quarantine
----------------------------------------
  Quarantined: test_victim_expects_empty_cache
  Quarantined: test_victim_expects_zero_counter
  Quarantined: test_victim_expects_empty_list
Updated deselect file with 7 tests

[4/4] Report Generation
----------------------------------------
  json: reports/report_20260410_031050.json
  html: reports/report_20260410_031050.html
  summary: reports/summary.json

============================================================
SUMMARY
============================================================
  Total tests:      190
  Flaky tests:      7
  Quarantined:      7
  Flaky rate:       3.7%
  Pass rate:        98.1%
============================================================

## Автор
Горюнов Михаил Александрович

Санкт-Петербургский политехнический университет Петра Великого
Высшая школа прикладной информатики, ИКНК

## Руководитель
Пархоменко В.А., старший преподаватель

## Лицензия
MIT License
