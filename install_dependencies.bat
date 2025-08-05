@echo off
echo === CPR Scraper Dependency Installation ===
echo.

REM Try to find Python
where python >nul 2>&1
if %errorlevel% == 0 (
    echo Found python in PATH
    python -m pip install -r requirements.txt
    goto :end
)

where py >nul 2>&1
if %errorlevel% == 0 (
    echo Found py launcher
    py -m pip install -r requirements.txt
    goto :end
)

where python3 >nul 2>&1
if %errorlevel% == 0 (
    echo Found python3
    python3 -m pip install -r requirements.txt
    goto :end
)

echo.
echo ERROR: Python not found in PATH
echo.
echo Please ensure Python is installed and added to your PATH
echo You can download Python from: https://www.python.org/downloads/
echo.
echo After installing Python, run this script again.
echo.
pause

:end
echo.
echo Installation completed!
pause 