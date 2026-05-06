@echo off
title LOCK IN — Phone Guard Setup
color 0A
cd /d "%~dp0"

echo.
echo ============================================================
echo   LOCK IN — Phone Guard
echo   Watches your camera. Catches your phone. Locks your PC.
echo ============================================================
echo.

:: ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo  1. Go to https://python.org/downloads
    echo  2. Download Python 3.10 or newer
    echo  3. Check "Add Python to PATH" during install
    echo  4. Re-run this file
    echo.
    pause
    exit /b 1
)

echo [+] Python found:
python --version
echo.

:: ── Install dependencies ──────────────────────────────────────
echo [*] Installing dependencies (this may take a minute first time)...
echo.
python -m pip install ultralytics opencv-python --quiet --upgrade
echo.
echo [+] Dependencies ready.
echo.

:: ── Launch ───────────────────────────────────────────────────
echo ============================================================
echo   Starting Phone Guard...
echo   - Allow camera access if prompted
echo   - First run downloads the AI model (~6 MB)
echo   - Press Q or Ctrl+C to stop
echo ============================================================
echo.

python phone_guard.py

echo.
pause
