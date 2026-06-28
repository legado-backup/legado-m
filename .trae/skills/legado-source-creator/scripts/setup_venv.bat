@echo off
echo Setting up Legado Client virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -e .
pip install pytest pytest-cov
echo.
echo Virtual environment setup complete.
echo Run: .venv\Scripts\activate.bat
