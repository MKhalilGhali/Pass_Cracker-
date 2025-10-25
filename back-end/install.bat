@echo off
echo ========================================
echo Password Cracker API v2.0 - Installation
echo ========================================
echo.

echo Installing Python dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [OK] Dependencies installed successfully!
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Choose your mode:
echo.
echo 1. SIMPLE MODE (Recommended for testing)
echo    - No Redis required
echo    - Run: python app_simple.py
echo.
echo 2. FULL MODE (Recommended for production)
echo    - Requires Redis
echo    - Install Redis: https://github.com/microsoftarchive/redis/releases
echo    - Run: start.bat
echo.
echo See README.md for detailed instructions
echo.
pause
