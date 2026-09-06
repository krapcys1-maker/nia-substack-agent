@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not exist ".venv\Scripts\python.exe" (
  echo First run: double-click Install-NIA.cmd to install NIA's dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" narzedzia\panel.py %*
if errorlevel 1 pause
