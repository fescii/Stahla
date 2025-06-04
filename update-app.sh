#!/bin/bash
# Script to update codebase and restart the app without full deployment

set -e

echo "===== Starting Stahla Update Process ====="

# 1. Pull latest code changes
echo "Pulling latest code changes..."
git pull

# 2. Install any new dependencies
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt

# 3. Stop running services
echo "Stopping services..."

# Find and kill the uvicorn/FastAPI process
FASTAPI_PID=$(ps aux | grep '[u]vicorn app.main:app' | awk '{print $2}')
if [ ! -z "$FASTAPI_PID" ]; then
  echo "Stopping FastAPI (PID: $FASTAPI_PID)..."
  kill $FASTAPI_PID
  sleep 2
fi

# 4. Start the application again
echo "Starting FastAPI application..."
cd /home/femar/A03/Stahla
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &

# 5. Wait for app to start
echo "Waiting for application to start..."
sleep 5

# 6. Verify the application is running
if curl -s http://localhost:8000/health | grep -q "status"; then
  echo "✓ Application successfully restarted and health check passed"
else
  echo "⚠ Warning: Application may not have started correctly"
  echo "Please check the application logs"
fi

echo "===== Update process completed ====="
