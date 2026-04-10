@echo off
chcp 65001 >nul
title Мутационное тестирование

echo.
python mutation_test.py
pause