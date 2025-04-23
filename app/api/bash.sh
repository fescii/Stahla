#!/bin/bash

# Assumes current directory is: ../api/

# Create folders and files from this point downward and upward
mkdir -p v1/endpoints/webhooks
touch __init__.py
touch v1/__init__.py
echo "# API router aggregation for v1" > v1/api.py
touch v1/endpoints/__init__.py
touch v1/endpoints/classify.py
touch v1/endpoints/hubspot.py
touch v1/endpoints/health.py
touch v1/endpoints/prepare.py # Added prepare.py
touch v1/endpoints/webhooks/__init__.py
touch v1/endpoints/webhooks/form.py
touch v1/endpoints/webhooks/helpers.py
touch v1/endpoints/webhooks/hubspot.py
touch v1/endpoints/webhooks/voice.py


# Go up to app/ level
cd ../

# Create main app files and folders
touch __init__.py
echo "# Main FastAPI application instance" > main.py

mkdir -p core models services utils assets

# Core
touch core/__init__.py
echo "# Configuration loading (e.g., API keys)" > core/config.py

# Models
touch models/__init__.py
touch models/common.py
touch models/bland.py
touch models/classification.py
touch models/email.py
touch models/hubspot.py
touch models/webhook.py


# Services
touch services/__init__.py
touch services/bland.py
touch services/email.py
touch services/hubspot.py
touch services/n8n.py
mkdir -p services/classify
touch services/classify/__init__.py
touch services/classify/classification.py
touch services/classify/marvin.py
touch services/classify/rules.py

# Utils
touch utils/__init__.py
touch utils/location_enhanced.py
touch utils/location.py

# Assets
touch assets/call_script.md


# Go up to project root
cd ../

# Create root-level folders and files
mkdir -p tests docs info rest
touch tests/.keep
touch docs/.keep
touch info/.keep
touch rest/form.http
touch .env.example
touch .gitignore
touch Dockerfile
touch docker-compose.yml
touch requirements.txt
touch README.md

echo "✅ Structure created relative to api/ directory"
