@echo off
echo ========================================
echo Password Cracker API v2.0 - Startup
echo ========================================
echo.

echo Checking Redis connection...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Redis is not running!
    echo Please start Redis first:
    echo   - Download from: https://github.com/microsoftarchive/redis/releases
    echo   - Or use Docker: docker run -d -p 6379:6379 redis
    pause
    exit /b 1
)
echo [OK] Redis is running
echo.

echo Starting Celery worker in new window...
start "Celery Worker" cmd /k "celery -A celery_app worker --loglevel=info --pool=solo"
timeout /t 3 >nul

echo Starting Flask API...
python app.py

pause
