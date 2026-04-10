@echo off
echo === Генерация датасетов ===
python benchmarks/generate_datasets.py
echo.
echo === Запуск экспериментов ===
python benchmarks/run_benchmarks.py
echo.
echo === Анализ результатов ===
python benchmarks/analyze_results.py
echo.
echo === Готово ===
pause
