# app/core/config.py

import os
import logfire  # Added logfire import
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache
# Added Any, List, Dict, Union
from typing import Optional, Literal, Any, List, Dict, Union
from urllib.parse import quote_plus  # Import quote_plus
import json
# Import specific types from pydantic, NOT BaseSettings
from pydantic import EmailStr, HttpUrl, AnyHttpUrl, Field, validator, ValidationInfo


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
  APP_BASE_URL: str = "https://stahla.fly.dev/"

  # HubSpot Configuration
  HUBSPOT_ACCESS_TOKEN: Optional[str] = Field(
      default=None, description="HubSpot Private App Access Token")  # Added
  HUBSPOT_API_KEY: str = "YOUR_HUBSPOT_API_KEY_HERE"  # Default is just a placeholder
  HUBSPOT_CLIENT_SECRET: Optional[str] = None
  HUBSPOT_PORTAL_ID: Optional[str] = None  # Ensure this is defined
  # HubSpot Pipeline/Stage IDs (Replace with your actual IDs)
  HUBSPOT_LEADS_PIPELINE_ID: str = "default"  # Example: Default pipeline ID
  HUBSPOT_NEW_LEAD_STAGE_ID: str = "appointmentscheduled"  # Example: Replace
  HUBSPOT_HOT_LEAD_STAGE_ID: str = "qualifiedtobuy"  # Example: Replace
  HUBSPOT_WARM_LEAD_STAGE_ID: str = "presentationscheduled"  # Example: Replace
  HUBSPOT_COLD_LEAD_STAGE_ID: str = "decisionmakerboughtin"  # Example: Replace
  HUBSPOT_DISQUALIFIED_STAGE_ID: str = "closedlost"  # Example: Replace
  # Example: Stage for manual review
  HUBSPOT_NEEDS_REVIEW_STAGE_ID: str = "appointmentscheduled"
  # --- Add Missing Pipeline/Stage IDs ---
  HUBSPOT_SERVICES_PIPELINE_ID: str = "default"  # Placeholder - Set in .env
  # Placeholder - Set in .env
  HUBSPOT_SERVICES_NEW_STAGE_ID: str = "appointmentscheduled"
  HUBSPOT_LOGISTICS_PIPELINE_ID: str = "default"  # Placeholder - Set in .env
  # Placeholder - Set in .env
  HUBSPOT_LOGISTICS_NEW_STAGE_ID: str = "appointmentscheduled"
  # --- End Add Missing ---

  # HubSpot Association Type IDs (Ensure these are integers and set in your .env file)
  HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_CONTACT: int = Field(
      # Example default, replace with actual ID
      default=1, description="Numeric ID for Deal to Contact association")
  HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_COMPANY: int = Field(
      # Example default, replace with actual ID
      default=2, description="Numeric ID for Deal to Company association")
  HUBSPOT_ASSOCIATION_TYPE_ID_COMPANY_TO_CONTACT: int = Field(
      # Example default, replace with actual ID
      default=3, description="Numeric ID for Company to Contact association")
  HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_CONTACT: int = Field(
      # Example default, replace with actual ID
      default=4, description="Numeric ID for Ticket to Contact association")
  HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_DEAL: int = Field(
      # Example default, replace with actual ID
      default=5, description="Numeric ID for Ticket to Deal association")

  # HubSpot Default Pipeline Names (Can be overridden in .env)
  HUBSPOT_DEFAULT_DEAL_PIPELINE_NAME: str = "Sales Pipeline"
  HUBSPOT_DEFAULT_TICKET_PIPELINE_NAME: str = "Support Pipeline"
  HUBSPOT_DEFAULT_LEAD_LIFECYCLE_STAGE: str = "lead"

  # HubSpot Cache TTLs (in seconds)
  CACHE_TTL_HUBSPOT_PIPELINES: int = Field(
      default=3600, description="Cache TTL for HubSpot pipelines in seconds")  # Added
  CACHE_TTL_HUBSPOT_STAGES: int = Field(
      default=3600, description="Cache TTL for HubSpot pipeline stages in seconds")  # Added
  CACHE_TTL_HUBSPOT_OWNERS: int = Field(
      default=3600, description="Cache TTL for HubSpot owners in seconds")  # Added

  # HUBSPOT_REVIEW_OWNER_ID: Optional[str] = None # Optional: Assign leads needing review to specific owner

  # Bland.ai Configuration
  BLAND_API_KEY: str = "YOUR_BLAND_AI_KEY_HERE"
  BLAND_API_URL: str = "https://api.bland.ai"
  BLAND_PATHWAY_ID: Optional[str] = None
  BLAND_LOCATION_TOOL_ID: Optional[str] = None
  BLAND_QUOTE_TOOL_ID: Optional[str] = None
  # Default voice ID if not set in environment
  BLAND_VOICE_ID: Optional[str] = None
  # Optional phone prefix for Bland calls (e.g., "+1")
  BLAND_PHONE_PREFIX: Optional[str] = None

  # Logfire Configuration
  LOGFIRE_TOKEN: Optional[str] = Field(
      default=None, validation_alias="LOGFIRE_TOKEN")
  # Change type to bool and default to False
  LOGFIRE_IGNORE_NO_CONFIG: bool = Field(
      default=False, validation_alias="LOGFIRE_IGNORE_NO_CONFIG", description="Suppress LogfireNotConfiguredWarning if True"
  )

  # LLM Configuration
  # Select your provider
  LLM_PROVIDER: Literal["openai", "anthropic", "gemini", "marvin"] = "openai"
  # Provide the appropriate API key based on the provider
  OPENAI_API_KEY: Optional[str] = None
  ANTHROPIC_API_KEY: Optional[str] = None
  GEMINI_API_KEY: Optional[str] = None
  MARVIN_API_KEY: Optional[str] = None  # Often uses OPENAI_API_KEY
  # Optionally specify a particular model
  MODEL_NAME: Optional[str] = None  # e.g., "gpt-4", "claude-3-opus-20240229"

  # Marvin Logging Configuration
  MARVIN_LOG_LEVEL: str = "ERROR"  # Control Marvin's logging verbosity
  MARVIN_VERBOSE: str = "false"    # Disable Marvin's verbose console output

  # N8N Configuration
  N8N_WEBHOOK_URL: Optional[str] = None
  N8N_API_KEY: Optional[str] = None

  # Classification Method
  CLASSIFICATION_METHOD: Literal["rules", "ai"] = "ai"

  # N8N / Orchestration Configuration (Optional)
  N8N_ENABLED: bool = Field(default=False, validation_alias="N8N_ENABLED")
  N8N_WEBHOOK_URL_CLASSIFICATION_DONE: Optional[str] = Field(
      default=None, validation_alias="N8N_WEBHOOK_URL_CLASSIFICATION_DONE")

  # Classification Logic Settings
  LOCAL_DISTANCE_THRESHOLD_MILES: int = Field(
      # Default 180 miles (approx 3 hours)
      default=180, validation_alias="LOCAL_DISTANCE_THRESHOLD_MILES")

  # Redis Configuration
  REDIS_URL: str = "redis://localhost:6379/0"

  # Google Maps Configuration
  GOOGLE_MAPS_API_KEY: str = "YOUR_GOOGLE_MAPS_API_KEY_HERE"

  # Pricing Agent Configuration
  PRICING_WEBHOOK_API_KEY: str = "YOUR_PRICING_WEBHOOK_API_KEY_HERE"
  GOOGLE_SHEET_ID: str = "YOUR_GOOGLE_SHEET_ID_HERE"
  GOOGLE_SHEET_PRODUCTS_TAB_NAME: str = "products"
  GOOGLE_SHEET_GENERATORS_TAB_NAME: str = "generators"
  # Add setting for branches range, default assumes 'Locations' tab
  GOOGLE_SHEET_BRANCHES_RANGE: str = "locations"
  # Add setting for config range
  GOOGLE_SHEET_CONFIG_RANGE: str = "config"
  # Add setting for states range
  GOOGLE_SHEET_STATES_RANGE: str = "states"
  # Optional: Path to Google Service Account credentials
  GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

  # MongoDB Configuration (Updated Variable Names)
  MONGO_HOST: str = "localhost"
  MONGO_PORT: int = 27017
  MONGO_DB_NAME: str = "admin"  # Use admin database for unified auth
  # Renamed from MONGO_INITDB_ROOT_USERNAME
  MONGO_ROOT_USER: Optional[str] = None
  # Renamed from MONGO_INITDB_ROOT_PASSWORD
  MONGO_ROOT_PASSWORD: Optional[str] = None
  MONGO_USER: Optional[str] = None  # Renamed from MONGO_APP_USER
  MONGO_PASSWORD: Optional[str] = None  # Renamed from MONGO_APP_PASSWORD
  # Optional: Construct dynamically if needed
  MONGO_CONNECTION_URL: Optional[str] = None

  # Auth Settings
  JWT_SECRET_KEY: str = "default_secret_key_please_change"
  JWT_ALGORITHM: str = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Default 1 hour
  BCRYPT_SALT_ROUNDS: int = 10  # Default salt rounds for bcrypt

  # Initial Superuser (Optional)
  FIRST_SUPERUSER_EMAIL: Optional[str] = None
  FIRST_SUPERUSER_PASSWORD: Optional[str] = None

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
  try:
    settings_instance = Settings()

    # Construct MongoDB URL if not explicitly provided
    if not settings_instance.MONGO_CONNECTION_URL:
      user = quote_plus(
          settings_instance.MONGO_USER) if settings_instance.MONGO_USER else None
      password = quote_plus(
          settings_instance.MONGO_PASSWORD) if settings_instance.MONGO_PASSWORD else None
      host = settings_instance.MONGO_HOST
      port = settings_instance.MONGO_PORT
      db_name = settings_instance.MONGO_DB_NAME
      auth_source = "admin"

      if user and password:
        mongo_url = f"mongodb://{user}:{password}@{host}:{port}/{db_name}?authSource={auth_source}"
      else:
        # Fallback for local/unauthenticated MongoDB
        mongo_url = f"mongodb://{host}:{port}/{db_name}"

      settings_instance.MONGO_CONNECTION_URL = mongo_url
      # Log the dynamically constructed URL for debugging (ensure this is after logfire.configure)
      # logfire.info(f"Dynamically constructed MongoDB URL: {mongo_url}")

    return settings_instance
  except Exception as e:
    # This log might not reach Logfire if configuration itself failed
    # Consider a simple print or standard library logging for critical bootstrap errors
    print(f"CRITICAL: Failed to initialize settings: {e}")
    # logfire.error(f"CRITICAL: Failed to initialize settings: {e}", exc_info=True) # This might not work if logfire isn't configured
    raise  # Re-raise the exception to halt application startup


settings = get_settings()

# Example of using logfire after settings (and thus Logfire) are configured
# This will only be effective if logfire.configure() in main.py has run
logfire.info(
    f"Settings loaded. DEV mode: {settings.DEV}, Project: {settings.PROJECT_NAME}, Logfire Ignore No Config: {settings.LOGFIRE_IGNORE_NO_CONFIG}"
)
# Avoid logging credentials for local default
if settings.MONGO_CONNECTION_URL and "localhost" not in settings.MONGO_CONNECTION_URL:
  # Log only host part if not local
  logfire.info(
      f"MongoDB URL (production-like): {settings.MONGO_CONNECTION_URL.split('@')[-1]}")
else:
  logfire.info(f"MongoDB URL: {settings.MONGO_CONNECTION_URL}")
