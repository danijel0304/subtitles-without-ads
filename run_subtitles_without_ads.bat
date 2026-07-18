@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 subtitles_without_ads.py
) else (
    python subtitles_without_ads.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The program could not start. Check that Python is installed.
    pause
)
