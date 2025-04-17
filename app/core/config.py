# app/core/config.py

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache
from typing import Optional, Literal, Any # Import Any
from pydantic import EmailStr, Field, validator # Import validator
import logfire # Import logfire

# Load environment variables from a .env file if it exists
# Useful for local development
load_dotenv()

class Settings(BaseSettings):
	"""
	Application settings loaded from environment variables.
	Uses pydantic-settings for validation and type hints.
	"""
	# Development Mode
	DEV: bool = False

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

	# Logfire Configuration
	LOGFIRE_TOKEN: Optional[str] = Field(None, validation_alias="LOGFIRE_TOKEN")
	LOGFIRE_IGNORE_NO_CONFIG: bool = Field(False, validation_alias="LOGFIRE_IGNORE_NO_CONFIG")

	# Marvin/LLM Settings
	MARVIN_API_KEY: Optional[str] = Field(None, validation_alias="MARVIN_API_KEY")
	# Add specific provider keys with aliases
	OPENAI_API_KEY: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")
	ANTHROPIC_API_KEY: Optional[str] = Field(None, validation_alias="ANTHROPIC_API_KEY")
	GEMINI_API_KEY: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY") # If you plan to use Gemini

	# Add MODEL_NAME field
	MODEL_NAME: Optional[str] = Field(None, validation_alias="MODEL_NAME") # e.g., gpt-4, claude-3-opus

	MARVIN_OPENAI_MODEL: str = Field("gpt-4o-mini", validation_alias="MARVIN_OPENAI_MODEL") # Specific model for Marvin/OpenAI
	LLM_PROVIDER: str = Field("openai", validation_alias="LLM_PROVIDER") # e.g., "openai", "anthropic", "none"

	# Classification Method
	CLASSIFICATION_METHOD: Literal["rules", "ai"] = Field("rules", validation_alias="CLASSIFICATION_METHOD")

	# Email Service Settings
	RESEND_API_KEY: Optional[str] = Field(None, validation_alias="RESEND_API_KEY")

	# N8N / Orchestration Configuration (Optional)
	N8N_ENABLED: bool = Field(False, validation_alias="N8N_ENABLED")
	N8N_WEBHOOK_URL_CLASSIFICATION_DONE: Optional[str] = Field(None, validation_alias="N8N_WEBHOOK_URL_CLASSIFICATION_DONE")

	# Email Configuration (Optional - if sending auto-replies)
	EMAIL_SENDING_ENABLED: bool = Field(False, validation_alias="EMAIL_SENDING_ENABLED")
	SMTP_HOST: Optional[str] = Field(None, validation_alias="SMTP_HOST")
	SMTP_PORT: Optional[int] = Field(587, validation_alias="SMTP_PORT")
	SMTP_USER: Optional[str] = Field(None, validation_alias="SMTP_USER")
	SMTP_PASSWORD: Optional[str] = Field(None, validation_alias="SMTP_PASSWORD")
	EMAIL_FROM_ADDRESS: Optional[EmailStr] = Field(None, validation_alias="EMAIL_FROM_ADDRESS")

	# Add validator for EMAIL_FROM_ADDRESS
	@validator('EMAIL_FROM_ADDRESS', pre=True)
	def empty_str_to_none(cls, v: Any) -> Optional[str]:
		"""Convert empty string to None before validation."""
		if isinstance(v, str) and v.strip() == '':
			return None
		return v

	# Classification Logic Settings
	LOCAL_DISTANCE_THRESHOLD_MILES: int = Field(180, validation_alias="LOCAL_DISTANCE_THRESHOLD_MILES") # Default 180 miles (approx 3 hours)

	class Config:
		# Specifies the prefix for environment variables (optional)
		# env_prefix = ""
		# Specifies the .env file name (default is '.env')
		env_file = ".env"
		env_file_encoding = 'utf-8'
		# Make field names case-insensitive when reading from env vars
		case_sensitive = False
		# Ignore extra fields read from env instead of erroring
		extra = 'ignore'

# Use lru_cache to cache the settings instance for performance
@lru_cache()
def get_settings() -> Settings:
	"""
	Returns the cached settings instance.
	Relies on pydantic-settings to load from .env and environment variables.
	"""
	logfire.debug("Loading application settings using pydantic-settings.")
	try:
		# Pydantic-settings automatically reads from .env and environment variables
		# based on the Settings class definition and its Config.
		# It handles type conversions and aliases.
		settings_instance = Settings()
		logfire.info("Application settings loaded successfully.")
		# Log a few key settings to verify
		logfire.info(f"LLM Provider: {settings_instance.LLM_PROVIDER}, Classification Method: {settings_instance.CLASSIFICATION_METHOD}")
		return settings_instance
	except Exception as e: # Catch potential validation errors during Settings() init
		logfire.error(f"Failed to initialize Settings object: {e}", exc_info=True)
		raise ValueError(f"Configuration error: {e}") from e

# Create an instance accessible throughout the application
settings = get_settings()

# Example usage:
# from app.core.config import settings
# api_key = settings.BLAND_API_KEY
