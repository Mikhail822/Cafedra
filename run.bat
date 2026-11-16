@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Python 3.11 or 3.12 is required. Install it from python.org and enable the py launcher.
    pause
    exit /b 1
  )
)

if not exist ".venv\.requirements-installed" (
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
  type nul > ".venv\.requirements-installed"
)

".venv\Scripts\python.exe" -m app.main
if errorlevel 1 pause
