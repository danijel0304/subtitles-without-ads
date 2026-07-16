@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo.
echo Building Titlovi Bez Reklama.exe
echo.

py --version >nul 2>&1
if errorlevel 1 (
    echo Python launcher "py" nije dostupan. Instaliraj Python za Windows i ukljuci ga u PATH.
    pause
    exit /b 1
)

py -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instaliram PyInstaller...
    py -m pip install pyinstaller
    if errorlevel 1 (
        echo PyInstaller instalacija nije uspjela.
        pause
        exit /b 1
    )
)

py -m PyInstaller --clean --noconfirm titlovi_bez_reklama.spec
if errorlevel 1 (
    echo Build nije uspio.
    pause
    exit /b 1
)

echo.
echo Gotovo. EXE je u folderu: dist
echo Datoteka: dist\Titlovi Bez Reklama.exe
echo.
pause
