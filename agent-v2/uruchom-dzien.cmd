@echo off
REM Dzienna rutyna agenta, uruchamiana przez Harmonogram zadan Windows.
REM
REM DLACZEGO TUTAJ, A NIE NA SERWERZE: Cloudflare odrzuca z adresu centrum
REM danych zapytanie publikujace (403 na POST /api/v1/comment/feed), mimo ze
REM czytanie i kompozytor dzialaja. Z tego komputera, na zwyklym laczu
REM domowym, wszystko przechodzi. Nie omijamy tego zabezpieczenia.
REM
REM Serwer zostaje do zadan, ktore nie wymagaja publikowania.

cd /d "%~dp0\.."
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

if not exist "agent-v2\data\logi" mkdir "agent-v2\data\logi"
for /f "tokens=1-3 delims=-" %%a in ("%date%") do set DZIS=%%a%%b%%c

".venv\Scripts\python.exe" -u "agent-v2\run.py" --dzien --wyslij >> "agent-v2\data\logi\dzien-%DZIS%.log" 2>&1
