# app/core/config.py

import os
import logfire  # Added logfire import
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache
from typing import Optional, Literal, Any, List, Dict, Union  # Added Any, List, Dict, Union
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
  APP_BASE_URL: str = "http://localhost:8000"

  # HubSpot Configuration
  HUBSPOT_API_KEY: str = "YOUR_HUBSPOT_API_KEY_HERE"  # Default is just a placeholder
  HUBSPOT_CLIENT_SECRET: Optional[str] = None
  HUBSPOT_PORTAL_ID: Optional[str] = None  # Ensure this is defined
  # HubSpot Pipeline/Stage IDs (Replace with your actual IDs)
  HUBSPOT_LEADS_PIPELINE_ID: str = "default" # Example: Default pipeline ID
  HUBSPOT_NEW_LEAD_STAGE_ID: str = "appointmentscheduled"  # Example: Replace
  HUBSPOT_HOT_LEAD_STAGE_ID: str = "qualifiedtobuy"  # Example: Replace
  HUBSPOT_WARM_LEAD_STAGE_ID: str = "presentationscheduled"  # Example: Replace
  HUBSPOT_COLD_LEAD_STAGE_ID: str = "decisionmakerboughtin"  # Example: Replace
  HUBSPOT_DISQUALIFIED_STAGE_ID: str = "closedlost"  # Example: Replace
  # Example: Stage for manual review
  HUBSPOT_NEEDS_REVIEW_STAGE_ID: str = "appointmentscheduled"
  # --- Add Missing Pipeline/Stage IDs ---
  HUBSPOT_SERVICES_PIPELINE_ID: str = "default" # Placeholder - Set in .env
  HUBSPOT_SERVICES_NEW_STAGE_ID: str = "appointmentscheduled" # Placeholder - Set in .env
  HUBSPOT_LOGISTICS_PIPELINE_ID: str = "default" # Placeholder - Set in .env
  HUBSPOT_LOGISTICS_NEW_STAGE_ID: str = "appointmentscheduled" # Placeholder - Set in .env
  # --- End Add Missing --- 
  # HUBSPOT_REVIEW_OWNER_ID: Optional[str] = None # Optional: Assign leads needing review to specific owner

  # Bland.ai Configuration
  BLAND_API_KEY: str = "YOUR_BLAND_AI_KEY_HERE"
  BLAND_API_URL: str = "https://api.bland.ai"
  # Default Bland Voice ID (optional, can be overridden in requests)
  BLAND_DEFAULT_VOICE_ID: Optional[int] = None
  # Add setting for phone prefix
  BLAND_PHONE_PREFIX: Optional[str] = Field(None, validation_alias="BLAND_PHONE_PREFIX")
  # Add setting for Conversation Pathway ID
  BLAND_PATHWAY_ID: Optional[str] = Field(None, validation_alias="BLAND_PATHWAY_ID")

  # Logfire Configuration
  LOGFIRE_TOKEN: Optional[str] = Field(None, validation_alias="LOGFIRE_TOKEN")
  # Change type to int and default to 0
  LOGFIRE_IGNORE_NO_CONFIG: int = Field(
      0, validation_alias="LOGFIRE_IGNORE_NO_CONFIG")

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

  # N8N Configuration
  N8N_WEBHOOK_URL: Optional[str] = None
  N8N_API_KEY: Optional[str] = None

  # Classification Method
  CLASSIFICATION_METHOD: Literal["rules", "ai"] = "ai"

  # Email Service Settings
  RESEND_API_KEY: Optional[str] = Field(
      None, validation_alias="RESEND_API_KEY")

  # N8N / Orchestration Configuration (Optional)
  N8N_ENABLED: bool = Field(False, validation_alias="N8N_ENABLED")
  N8N_WEBHOOK_URL_CLASSIFICATION_DONE: Optional[str] = Field(
      None, validation_alias="N8N_WEBHOOK_URL_CLASSIFICATION_DONE")

  # Email Configuration (Optional - if sending auto-replies)
  EMAIL_SENDING_ENABLED: bool = Field(
      False, validation_alias="EMAIL_SENDING_ENABLED")
  SMTP_HOST: Optional[str] = Field(None, validation_alias="SMTP_HOST")
  SMTP_PORT: Optional[int] = Field(587, validation_alias="SMTP_PORT")
  SMTP_USER: Optional[str] = Field(None, validation_alias="SMTP_USER")
  SMTP_PASSWORD: Optional[str] = Field(None, validation_alias="SMTP_PASSWORD")
  EMAIL_FROM_ADDRESS: Optional[EmailStr] = Field(
      None, validation_alias="EMAIL_FROM_ADDRESS")

  # Add validator for EMAIL_FROM_ADDRESS
  @validator('EMAIL_FROM_ADDRESS', pre=True)
  def empty_str_to_none(cls, v: Any) -> Optional[str]:
    """Convert empty string to None before validation."""
    if isinstance(v, str) and v.strip() == '':
      return None
    return v

  # Classification Logic Settings
  LOCAL_DISTANCE_THRESHOLD_MILES: int = Field(
      # Default 180 miles (approx 3 hours)
      180, validation_alias="LOCAL_DISTANCE_THRESHOLD_MILES")

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
  GOOGLE_SHEET_BRANCHES_RANGE: str = "Locations!A2:B"
  # Add setting for config range
  GOOGLE_SHEET_CONFIG_RANGE: str = "Config!A1:B10"
  # Optional: Path to Google Service Account credentials
  GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

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
    # Pydantic-settings automatically reads from .env and environment variables
    # based on the Settings class definition and its Config.
    # It handles type conversions and aliases.
    settings_instance = Settings()
    # Log a few key settings to verify
    logfire.info(
        f"LLM Provider: {settings_instance.LLM_PROVIDER}, Classification Method: {settings_instance.CLASSIFICATION_METHOD}")
    return settings_instance
  except Exception as e:  # Catch potential validation errors during Settings() init
    logfire.error(f"Failed to initialize Settings object: {e}", exc_info=True)
    raise ValueError(f"Configuration error: {e}") from e


# Create an instance accessible throughout the application
settings = get_settings()

# Example usage:
# from app.core.config import settings
# api_key = settings.BLAND_API_KEY
