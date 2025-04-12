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
	# Ensure this environment variable is set (e.g., in your .env file)
	HUBSPOT_API_KEY: str = "YOUR_HUBSPOT_API_KEY_HERE"  # Default is just a placeholder
	
	# Bland.ai Configuration (Add if needed)
	# BLAND_API_KEY: str = "YOUR_BLAND_AI_KEY_HERE"
	
	# Logfire Configuration (Token usually set directly via env var LOGFIRE_TOKEN)
	# LOGFIRE_SERVICE_NAME: str = "stahla-ai-sdr-api"
	
	# Add other settings as needed...
	
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
# api_key = settings.HUBSPOT_API_KEY

"""
**Instructions:**
1.  Create a file named `config.py` inside the `app/core/` directory.
2.  Paste this code into it.
3.  **Crucially:** Create a `.env` file in your project's root directory (where `docker-compose.yml` is).
4.  Add your actual HubSpot API key to the `.env` file like this:
    ```
    HUBSPOT_API_KEY=your-real-api-key-xxxx-xxxx-xxxx-xxxx
    LOGFIRE_TOKEN=your-real-logfire-token-if-any
    # Add other secrets here
    ```
5.  Make sure `.env` is added to your `.gitignore` file to avoid committing secrets.
6.  You'll need `pydantic-settings`: Add `pydantic-settings>=2.0.0,<3.0.0` to your `requirements.txt` and reinstall dependencies (`pip install -r requirements.txt` or rebuild your Docker containe
"""
