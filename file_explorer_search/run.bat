@echo off
chcp 65001 >nul
title  Интеллектуальный поиск файлов

echo.
echo  Интеллектуальный поиск файлов
echo  ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [Ошибка] Python не найден. Установите Python 3.11+
    pause
    exit /b 1
)

REM Установка зависимостей если нужно
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo  Установка зависимостей...
    python -m pip install -r requirements.txt --quiet
)

REM Создание папок для данных и результатов
if not exist "data" mkdir data
if not exist "results" mkdir results

echo.
echo  1. Запуск с подключением к API (localhost:8000)
echo  2. Запуск в демо-режиме (без сервера)
echo.

set /p MODE="  Выберите режим (1 или 2): "

if "%MODE%"=="2" (
    python main.py --demo
) else (
    python main.py
)

pause
