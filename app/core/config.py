# app/core/config.py

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache
from typing import Optional, Literal
from pydantic import EmailStr

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
	# Base URL for constructing webhook URLs, needed for Bland callbacks etc.
	# Example: http://localhost:8000 or https://your-deployed-domain.com
	APP_BASE_URL: str = "http://localhost:8000"

	# HubSpot Configuration
	HUBSPOT_API_KEY: str = "YOUR_HUBSPOT_API_KEY_HERE" # Default is just a placeholder

	# Bland.ai Configuration
	BLAND_API_KEY: str = "YOUR_BLAND_AI_KEY_HERE" # Add your Bland AI API Key
	BLAND_API_URL: str = "https://api.bland.ai" # Default Bland API base URL
	# Default Bland Voice ID (optional, can be overridden in requests)
	BLAND_DEFAULT_VOICE_ID: Optional[int] = None

	# Logfire Configuration (Token usually set directly via env var LOGFIRE_TOKEN)
	# LOGFIRE_SERVICE_NAME: str = "stahla-ai-sdr-api"

	# LLM Configuration (Optional - if using LLM for parsing/classification)
	LLM_PROVIDER: Optional[Literal["openai", "anthropic", "gemini", "marvin", "none"]] = "marvin"
	OPENAI_API_KEY: Optional[str] = None
	ANTHROPIC_API_KEY: Optional[str] = None
	MARVIN_API_KEY: str = os.getenv("MARVIN_API_KEY", "")
	# Add other LLM provider keys/settings as needed

	# N8N / Orchestration Configuration (Optional)
	N8N_ENABLED: bool = False
	N8N_WEBHOOK_URL_CLASSIFICATION_DONE: Optional[str] = None # Example: URL to notify N8N after classification

	# Email Configuration (Optional - if sending auto-replies)
	EMAIL_SENDING_ENABLED: bool = False
	SMTP_HOST: Optional[str] = None
	SMTP_PORT: Optional[int] = 587
	SMTP_USER: Optional[str] = None
	SMTP_PASSWORD: Optional[str] = None
	EMAIL_FROM_ADDRESS: Optional[EmailStr] = None

	# Classification Logic Settings
	LOCAL_DISTANCE_THRESHOLD_MILES: int = 50 # For defining "Local" vs "Not Local"

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
