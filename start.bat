@echo off
REM ---------------------------------------------------------------------------
REM  Innimmo Activist Screener — one-click runner.
REM  Double-click this file to: refresh live data, then open the dashboard.
REM ---------------------------------------------------------------------------
cd /d "%~dp0"
echo Running the Innimmo activist screener (live data)...
python activist_screener.py
if errorlevel 1 (
  echo.
  echo Something went wrong. Make sure Python and the libraries are installed:
  echo     pip install -r requirements.txt
  pause
  exit /b 1
)
echo.
echo Done. Opening the dashboard...
start "" "dashboard.html"
