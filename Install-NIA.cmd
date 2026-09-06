@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo NIA local setup. Requires Python 3.11+ and an internet connection.
echo Dependencies install into .venv in this folder. Account files are preserved.
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Install Python 3.11 or 3.12 from python.org and enable Add Python to PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt tzdata
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto failed
echo Setup complete. Next time use Start-NIA.cmd.
if /I "%~1"=="--setup-only" exit /b 0
call Start-NIA.cmd
exit /b %errorlevel%
:failed
echo Setup failed. Read the error above and see docs\PANEL.md or docs\PANEL_PL.md.
pause
exit /b 1
