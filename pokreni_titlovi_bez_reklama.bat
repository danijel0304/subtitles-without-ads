@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 titlovi_bez_reklama.py
) else (
    python titlovi_bez_reklama.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Program se nije mogao pokrenuti. Provjerite je li Python instaliran.
    pause
)
