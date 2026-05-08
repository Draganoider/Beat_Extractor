@echo off
setlocal
cd /d "%~dp0"
echo.
echo Beat Extractor setup and launcher
echo ---------------------------------
echo This will create/update .venv, install dependencies, then start the app.
echo.
call scripts\setup.cmd
if errorlevel 1 (
    echo.
    echo Setup failed. Install Python 3.12 from the Microsoft Store or python.org, then run this file again.
    pause
    exit /b 1
)
echo.
echo Starting the app. Keep this window open while using Beat Extractor.
echo.
call scripts\run_ui.cmd
pause

