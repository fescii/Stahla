# app/core/config.py

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache
from typing import Optional, Literal
from pydantic import EmailStr
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
	LOGFIRE_TOKEN: Optional[str] = None
	LOGFIRE_IGNORE_NO_CONFIG: bool = False # Added to read from .env
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
    # Process environment variables that need special handling
    logfire.debug("Loading and processing application settings.") # Add log
    
    # For BLAND_DEFAULT_VOICE_ID, convert to int if present and not empty
    bland_voice_id_str = os.getenv("BLAND_DEFAULT_VOICE_ID")
    bland_voice_id = None
    if bland_voice_id_str and bland_voice_id_str.strip():
        try:
            bland_voice_id = int(bland_voice_id_str)
        except ValueError:
            logfire.warn(f"Invalid BLAND_DEFAULT_VOICE_ID: '{bland_voice_id_str}'. Must be an integer. Using None.") # Add log
            bland_voice_id = None
    
    # For EMAIL_FROM_ADDRESS, set to None if empty
    email_from = os.getenv("EMAIL_FROM_ADDRESS")
    if not email_from or not email_from.strip(): # Check if None or empty/whitespace
        email_from = None
    
    # Handle boolean conversion for N8N_ENABLED (in .env it might be "false" as a string)
    n8n_enabled = os.getenv("N8N_ENABLED", "false").lower() == "true"
    
    # Handle boolean conversion for EMAIL_SENDING_ENABLED
    email_sending_enabled = os.getenv("EMAIL_SENDING_ENABLED", "false").lower() == "true"
    
    # Handle SMTP_PORT conversion to int
    smtp_port_str = os.getenv("SMTP_PORT")
    smtp_port = 587 # Default value
    if smtp_port_str and smtp_port_str.strip():
        try:
            smtp_port = int(smtp_port_str)
        except ValueError:
            logfire.warn(f"Invalid SMTP_PORT: '{smtp_port_str}'. Must be an integer. Using default {smtp_port}.") # Add log
            smtp_port = 587 # Ensure default is set on error
            
    # Handle LOCAL_DISTANCE_THRESHOLD_MILES conversion to int
    local_distance_str = os.getenv("LOCAL_DISTANCE_THRESHOLD_MILES", "50")
    local_distance = 50 # Default value
    try:
        local_distance = int(local_distance_str)
    except ValueError:
        logfire.warn(f"Invalid LOCAL_DISTANCE_THRESHOLD_MILES: '{local_distance_str}'. Must be an integer. Using default {local_distance}.") # Add log
        local_distance = 50 # Ensure default is set on error

    # Create Settings instance using processed values
    try:
        settings_instance = Settings(
            # API Information
            PROJECT_NAME=os.getenv("PROJECT_NAME", "Stahla AI SDR"),
            API_V1_STR=os.getenv("API_V1_STR", "/api/v1"),
            APP_BASE_URL=os.getenv("APP_BASE_URL", "http://localhost:8000"),

            # HubSpot Configuration
            HUBSPOT_API_KEY=os.getenv("HUBSPOT_API_KEY", "YOUR_HUBSPOT_API_KEY_HERE"),

            # Bland.ai Configuration
            BLAND_API_KEY=os.getenv("BLAND_API_KEY", "YOUR_BLAND_AI_KEY_HERE"),
            BLAND_API_URL=os.getenv("BLAND_API_URL", "https://api.bland.ai"),
            BLAND_DEFAULT_VOICE_ID=bland_voice_id,

            # Logfire Configuration
            LOGFIRE_TOKEN=os.getenv("LOGFIRE_TOKEN"),

            # LLM Configuration
            LLM_PROVIDER=os.getenv("LLM_PROVIDER", "marvin"),
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY"),
            MARVIN_API_KEY=os.getenv("MARVIN_API_KEY", ""),

            # N8N Configuration
            N8N_ENABLED=n8n_enabled,
            N8N_WEBHOOK_URL_CLASSIFICATION_DONE=os.getenv("N8N_WEBHOOK_URL_CLASSIFICATION_DONE"),

            # Email Configuration
            EMAIL_SENDING_ENABLED=email_sending_enabled,
            SMTP_HOST=os.getenv("SMTP_HOST"),
            SMTP_PORT=smtp_port,
            SMTP_USER=os.getenv("SMTP_USER"),
            SMTP_PASSWORD=os.getenv("SMTP_PASSWORD"),
            EMAIL_FROM_ADDRESS=email_from,

            # Classification Settings
            LOCAL_DISTANCE_THRESHOLD_MILES=local_distance
        )
        logfire.info("Application settings loaded successfully.") # Add log
        return settings_instance
    except Exception as e: # Catch potential validation errors from Pydantic itself
        logfire.error(f"Failed to initialize Settings object: {e}", exc_info=True)
        # Depending on severity, you might want to raise the exception
        # or return a default/partially configured object, or exit.
        # For now, re-raising to prevent startup with invalid config.
        raise ValueError(f"Configuration error: {e}") from e

# Create an instance accessible throughout the application
settings = get_settings()

# Example usage:
# from app.core.config import settings
# api_key = settings.BLAND_API_KEY
