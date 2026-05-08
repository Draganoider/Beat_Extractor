@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0train_model.ps1" %*
exit /b %ERRORLEVEL%

