#!/bin/bash

echo "========================================"
echo "Password Cracker API v2.0 - Startup"
echo "========================================"
echo ""

# Check if Redis is running
echo "Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "[ERROR] Redis is not running!"
    echo "Please start Redis first:"
    echo "  sudo service redis-server start"
    echo "  OR: redis-server"
    exit 1
fi
echo "[OK] Redis is running"
echo ""

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A celery_app worker --loglevel=info &
CELERY_PID=$!
sleep 3

# Start Flask API
echo "Starting Flask API..."
python app.py

# Cleanup on exit
trap "kill $CELERY_PID" EXIT
