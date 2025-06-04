#!/bin/bash

# Stahla Fly.io Unified Deployment Script
# This script deploys the application as a single container with all services

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/femar/A03/Stahla"
FLY_DIR="$PROJECT_ROOT/fly"

echo -e "${BLUE}[INFO]${NC} Starting unified deployment for Stahla..."

# Parse arguments
ORG=""
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --org) ORG="--org $2"; shift ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# Navigate to project root to ensure proper build context
cd "$PROJECT_ROOT"
echo -e "${BLUE}[INFO]${NC} Build context set to: $(pwd)"

# Deploy with explicit build context
echo -e "${YELLOW}[DEPLOY]${NC} Deploying to Fly.io..."
fly deploy --config "$FLY_DIR/fly.toml" $ORG

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS]${NC} Deployment completed successfully!"
    echo -e "${BLUE}[INFO]${NC} Application URL: https://stahla.fly.dev"
    echo -e "${BLUE}[INFO]${NC} Check status: fly status --app stahla"
    echo -e "${BLUE}[INFO]${NC} View logs: fly logs --app stahla"
else
    echo -e "${RED}[ERROR]${NC} Deployment failed!"
fi
