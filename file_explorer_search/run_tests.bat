@echo off
chcp 65001 >nul
title Запуск тестов

echo.
echo Запуск тестов
echo  ========================================
echo.

REM Проверка зависимостей
python -c "import pytest" >nul 2>&1
if errorlevel 1 (
    echo  Установка зависимостей...
    python -m pip install -r requirements.txt --quiet
)

echo  1. Все тесты (подробно)
echo  2. Все тесты (кратко)
echo  3. Тесты с покрытием кода
echo  4. Конкретный файл тестов
echo.

set /p MODE="  Выберите режим (1-4): "

if "%MODE%"=="1" (
    python -m pytest tests/ -v
) else if "%MODE%"=="2" (
    python -m pytest tests/ -q
) else if "%MODE%"=="3" (
    python -m pytest tests/ -v --cov=api --cov=algorithms --cov=core --cov=utils --cov-report=term-missing
) else if "%MODE%"=="4" (
    echo.
    echo  Доступные файлы:
    echo    1. test_naive.py
    echo    2. test_indexed.py
    echo    3. test_rankers.py
    echo    4. test_integration.py
    echo.
    set /p FILE="  Номер файла: "
    if "!FILE!"=="1" python -m pytest tests/test_naive.py -v
    if "!FILE!"=="2" python -m pytest tests/test_indexed.py -v
    if "!FILE!"=="3" python -m pytest tests/test_rankers.py -v
    if "!FILE!"=="4" python -m pytest tests/test_integration.py -v
) else (
    echo  Неверный выбор
)

echo.
pause
