@echo off
setlocal enabledelayedexpansion
title Dr Ranganath Creation - SCI Research Platform

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"

cls
echo ==============================================================
echo             DR RANGANATH CREATION
echo       AI-Powered Scientific Research Paper Generator
echo ==============================================================
echo.

if not exist "%PYTHON%" (
    echo [INFO] First time launch detected. Running setup...
    call "%ROOT%launch.bat"
    exit /b
)

echo [INFO] Verifying AI dependencies and applying hotfixes...
"%VENV%\Scripts\pip.exe" install "langchain-core<0.3.0" "qdrant-client" --quiet

cd /d "%ROOT%"
echo Launching the intelligent paper generation wizard...
echo.
"%PYTHON%" run.py

if errorlevel 1 (
    echo.
    echo An error occurred. Please check the logs above.
    pause
)
