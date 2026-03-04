@echo off
chcp 65001 >nul 2>&1

:: Check for Python 3.11 specifically
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 not found.
    echo [ERROR] Download: https://www.python.org/downloads/release/python-3119/
    pause & exit /b 1
)

if not exist .venv (
    echo [SETUP] Creating venv with Python 3.11...
    py -3.11 -m venv .venv
)

call .venv\Scripts\activate.bat

echo [SETUP] Installing dependencies...
pip install -r requirements.txt -q

echo [SERVER] Starting at http://localhost:8000
echo [SERVER] Press Ctrl+C to stop
echo.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
