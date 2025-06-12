# app/api/v1/endpoints/webhooks/models/validation.py

"""
Validation utilities for webhook requests.
Provides common validation patterns and error handling.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, validator
import re


class WebhookRequestBase(BaseModel):
  """Base class for webhook request validation."""

  class Config:
    extra = "forbid"  # Prevent additional fields
    validate_assignment = True


class LocationValidationMixin:
  """Mixin for location-related validation."""

  @validator('delivery_location', pre=True, always=True)
  def validate_delivery_location(cls, v):
    if not v or not isinstance(v, str):
      raise ValueError("delivery_location is required and must be a string")

    # Basic validation for location format
    v = v.strip()
    if len(v) < 3:
      raise ValueError("delivery_location must be at least 3 characters")

    if len(v) > 500:
      raise ValueError("delivery_location must be less than 500 characters")

    return v


class ApiKeyValidation:
  """Validation utilities for API keys."""

  @staticmethod
  def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if format is valid
    """
    if not api_key:
      return False

    # Basic format validation - adjust as needed
    if len(api_key) < 16:
      return False

    # Check for valid characters (alphanumeric + some special chars)
    if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
      return False

    return True


class WebhookRequestValidator:
  """Centralized webhook request validation."""

  @staticmethod
  def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Validate that required fields are present.

    Args:
        data: Request data dictionary
        required_fields: List of required field names

    Returns:
        List of missing field names
    """
    missing_fields = []

    for field in required_fields:
      if field not in data or data[field] is None:
        missing_fields.append(field)
      elif isinstance(data[field], str) and not data[field].strip():
        missing_fields.append(field)

    return missing_fields

  @staticmethod
  def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> List[str]:
    """
    Validate field types.

    Args:
        data: Request data dictionary
        field_types: Dictionary mapping field names to expected types

    Returns:
        List of validation error messages
    """
    errors = []

    for field, expected_type in field_types.items():
      if field in data and data[field] is not None:
        if not isinstance(data[field], expected_type):
          errors.append(f"{field} must be of type {expected_type.__name__}")

    return errors

  @staticmethod
  def sanitize_string_fields(data: Dict[str, Any], string_fields: List[str]) -> Dict[str, Any]:
    """
    Sanitize string fields by trimming whitespace.

    Args:
        data: Request data dictionary
        string_fields: List of string field names to sanitize

    Returns:
        Sanitized data dictionary
    """
    sanitized = data.copy()

    for field in string_fields:
      if field in sanitized and isinstance(sanitized[field], str):
        sanitized[field] = sanitized[field].strip()

    return sanitized
