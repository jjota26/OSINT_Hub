@echo off
title NetContactos Server
cd /d "%~dp0"

echo [1/2] Verificando ambiente virtual...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [2/2] Iniciando NetContactos...
"%PYTHON_EXE%" start.py
pause
