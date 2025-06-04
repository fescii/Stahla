#!/bin/bash
# Script to update codebase on Fly.io using proper deployment

set -e

echo "===== Starting Stahla Fly.io Update Process ====="

# Get the app name from fly.toml
APP_NAME=$(grep '^app = ' fly/fly.toml | sed 's/app = "\(.*\)"/\1/')
echo "Using Fly.io app: $APP_NAME"

# 1. Pull latest code changes locally first
echo "Pulling latest code changes..."
git pull

# 2. Deploy the updated code to Fly.io
echo "Deploying updated code to Fly.io..."
fly deploy --config fly/fly.toml

# 3. Verify the application is running
echo "Verifying application health..."
sleep 10
if curl -s https://$APP_NAME.fly.dev/health | grep -q "status"; then
  echo "✓ Application successfully updated and deployed on Fly.io"
else
  echo "⚠ Warning: Application may not have started correctly"
  echo "Run 'fly logs --config fly/fly.toml' to check the application logs"
fi

echo "===== Update process completed ====="
