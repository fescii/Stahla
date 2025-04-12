#!/bin/bash

# Assumes current directory is: ../api/

# Create folders and files from this point downward and upward
mkdir -p v1/endpoints
touch __init__.py
touch v1/__init__.py
echo "# API router aggregation for v1" > v1/api.py
touch v1/endpoints/__init__.py
touch v1/endpoints/webhooks.py
touch v1/endpoints/classify.py
touch v1/endpoints/hubspot.py
touch v1/endpoints/health.py

# Go up to app/ level
cd ../

# Create main app files and folders
touch __init__.py
echo "# Main FastAPI application instance" > main.py

mkdir -p core models services

# Core
touch core/__init__.py
echo "# Configuration loading (e.g., API keys)" > core/config.py

# Models
touch models/__init__.py
touch models/common.py
touch models/webhook_models.py
touch models/hubspot_models.py

# Services
touch services/__init__.py
touch services/classification_service.py
touch services/hubspot_service.py

# Go up to project root
cd ../

# Create root-level folders and files
mkdir -p tests
touch tests/.keep
touch .env.example
touch .gitignore
touch Dockerfile
touch docker-compose.yml
touch requirements.txt

echo "✅ Structure created relative to api/ directory"
