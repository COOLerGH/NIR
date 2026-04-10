@echo off
echo === BDD-тесты (pytest-bdd) ===
echo.
python -m pytest tests/bdd/ -v --tb=short
echo.
echo === Все тесты (модульные + BDD) ===
echo.
python -m pytest tests/ -v --tb=short --cov=core --cov=algorithms --cov-report=term-missing
pause
