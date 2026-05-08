@echo off
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON%" (
    echo Python 3.12 environment is missing. Run START_HERE.cmd first.
    exit /b 1
)
"%PYTHON%" -m beat_extractor.cli_contribution import %*
exit /b %ERRORLEVEL%

