# app/core/config.py

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from a .env file if it exists
# Useful for local development
load_dotenv()

class Settings(BaseSettings):
	"""
	Application settings loaded from environment variables.
	Uses pydantic-settings for validation and type hints.
	"""
	# API Information
	PROJECT_NAME: str = "Stahla AI SDR"
	API_V1_STR: str = "/api/v1"
	
	# HubSpot Configuration
	HUBSPOT_API_KEY: str = "YOUR_HUBSPOT_API_KEY_HERE" # Default is just a placeholder
	
	# Bland.ai Configuration
	BLAND_API_KEY: str = "YOUR_BLAND_AI_KEY_HERE" # Add your Bland AI API Key
	BLAND_API_URL: str = "https://api.bland.ai" # Default Bland API base URL
	
	# Logfire Configuration (Token usually set directly via env var LOGFIRE_TOKEN)
	# LOGFIRE_SERVICE_NAME: str = "stahla-ai-sdr-api"
	
	# Add other settings as needed...
	# e.g., N8N_WEBHOOK_URL: str = "YOUR_N8N_WEBHOOK_URL"
	
	class Config:
		# Specifies the prefix for environment variables (optional)
		# env_prefix = ""
		# Specifies the .env file name (default is '.env')
		env_file = ".env"
		env_file_encoding = 'utf-8'
		# Make field names case-insensitive when reading from env vars
		case_sensitive = False

# Use lru_cache to cache the settings instance for performance
# Ensures settings are loaded only once
@lru_cache()
def get_settings() -> Settings:
	"""Returns the cached settings instance."""
	return Settings()

# Create an instance accessible throughout the application
settings = get_settings()

# Example usage:
# from app.core.config import settings
# api_key = settings.BLAND_API_KEY
