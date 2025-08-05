@echo off
echo === Fixing pytest Import Error ===
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo Python is installed
    goto :install_pytest
)

py --version >nul 2>&1
if %errorlevel% == 0 (
    echo Python (py launcher) is available
    goto :install_pytest_py
)

echo Python is not installed or not in PATH
echo.
echo === INSTALLATION INSTRUCTIONS ===
echo.
echo Option 1: Install from Microsoft Store (Recommended)
echo 1. Press Windows key + R
echo 2. Type: ms-windows-store://pdp/?ProductId=9NRWMJP3717K
echo 3. Press Enter
echo 4. Click "Install" in the Microsoft Store
echo 5. Wait for installation to complete
echo 6. Restart this script
echo.
echo Option 2: Install from python.org
echo 1. Go to: https://www.python.org/downloads/
echo 2. Download the latest Python version
echo 3. Run the installer
echo 4. IMPORTANT: Check "Add Python to PATH" during installation
echo 5. Restart this script
echo.
echo Option 3: Use Windows Package Manager (if available)
echo winget install Python.Python.3.11
echo.
pause
goto :end

:install_pytest_py
echo Installing pytest using py launcher...
py -m pip install pytest
if %errorlevel% == 0 (
    echo pytest installed successfully
    goto :verify_installation
) else (
    echo Failed to install pytest with py launcher
    goto :manual_install
)

:install_pytest
echo Installing pytest...
python -m pip install pytest
if %errorlevel% == 0 (
    echo pytest installed successfully
    goto :verify_installation
) else (
    echo Failed to install pytest
    goto :manual_install
)

:verify_installation
echo.
echo Verifying installation...
python -c "import pytest; print('pytest imported successfully')" 2>nul
if %errorlevel% == 0 (
    echo pytest is working correctly
    echo.
    echo You can now run tests with:
    echo pytest tests/
    echo.
    goto :end
) else (
    echo pytest verification failed
    goto :manual_install
)

:manual_install
echo.
echo === MANUAL INSTALLATION ===
echo.
echo If automatic installation failed, try these commands manually:
echo.
echo 1. Install pytest:
echo    pip install pytest
echo    python -m pip install pytest
echo    py -m pip install pytest
echo.
echo 2. Install all project dependencies:
echo    pip install -r requirements.txt
echo    python -m pip install -r requirements.txt
echo    py -m pip install -r requirements.txt
echo.
echo 3. Verify installation:
echo    python -c "import pytest; print('pytest works!')"
echo.
echo 4. Run tests:
echo    pytest src/notifications/email_templates.test.py
echo.

:end
echo.
echo === TROUBLESHOOTING ===
echo.
echo If you continue to have issues:
echo 1. Make sure Python is installed and in your PATH
echo 2. Try running PowerShell as Administrator
echo 3. Check the FIX_PYTEST_IMPORT.md file for detailed instructions
echo 4. Use the setup_dev_environment.py script for complete setup
echo.
pause 