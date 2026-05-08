@echo off
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON%" (
    echo Python 3.12 environment is missing. Run scripts\setup.cmd after installing Python 3.12 from python.org.
    exit /b 1
)
"%PYTHON%" -m auto_determining.cli %*
exit /b %ERRORLEVEL%

