@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_auto_determining.ps1" %*
exit /b %ERRORLEVEL%

