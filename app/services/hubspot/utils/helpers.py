# app/services/hubspot/utils/helpers.py

import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone
from pydantic import ValidationError
import logfire

from hubspot.crm.objects.exceptions import ApiException as ObjectApiException
from hubspot.crm.deals import ApiException as DealApiException
from app.models.hubspot import HubSpotErrorDetail

logger = logging.getLogger(__name__)


def format_contact_for_hubspot(contact_data: Dict[str, Any]) -> Dict[str, Any]:
  """
  Format contact data for HubSpot API.
  Converts standard contact fields to HubSpot property format.
  """
  if not contact_data:
    return {}

  properties = {}

  # Map common fields
  field_mapping = {
      'email': 'email',
      'first_name': 'firstname',
      'last_name': 'lastname',
      'phone': 'phone',
      'company': 'company',
      'job_title': 'jobtitle',
      'website': 'website',
      'city': 'city',
      'state': 'state',
      'country': 'country',
      'postal_code': 'zip'
  }

  for key, hubspot_key in field_mapping.items():
    if key in contact_data and contact_data[key]:
      properties[hubspot_key] = str(contact_data[key])

  return {"properties": properties}


def convert_date_to_timestamp_ms(date_input: Union[str, datetime, None]) -> Optional[int]:
  """
  Convert date input to HubSpot-compatible millisecond Unix timestamp.
  Accepts datetime objects or YYYY-MM-DD date strings.
  """
  if not date_input:
    return None

  try:
    if isinstance(date_input, datetime):
      return int(date_input.timestamp() * 1000)
    elif isinstance(date_input, str):
      return _convert_date_to_timestamp_ms(date_input)
    else:
      logger.warning(f"Unsupported date input type: {type(date_input)}")
      return None
  except Exception as e:
    logger.error(f"Error converting date '{date_input}' to timestamp: {e}")
    return None


def _is_valid_iso_date(date_input: Any) -> bool:
  """Checks if a string is a valid YYYY-MM-DD date."""
  if not isinstance(date_input, str):
    return False
  try:
    datetime.strptime(date_input, "%Y-%m-%d")
    return True
  except ValueError:
    return False


def _convert_date_to_timestamp_ms(date_str: Optional[str]) -> Optional[int]:
  """
  Convert YYYY-MM-DD date string to a HubSpot-compatible millisecond Unix timestamp,
  representing midnight UTC of that date.
  Returns None if the date_str is None, empty, or invalid.
  """
  if not date_str:
    return None
  try:
    # _is_valid_iso_date already checks if date_str is a string and valid "YYYY-MM-DD"
    if _is_valid_iso_date(date_str):
      # Parse the date string to a date object
      date_object = datetime.strptime(date_str, "%Y-%m-%d").date()
      # Create a datetime object for midnight UTC on that date
      dt_midnight_utc = datetime.combine(
          date_object, datetime.min.time(), tzinfo=timezone.utc)
      # Convert to millisecond timestamp
      return int(dt_midnight_utc.timestamp() * 1000)
    else:
      logger.warning(f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")
      return None
  except Exception as e:
    logger.error(f"Error converting date '{date_str}' to timestamp: {e}")
    return None


async def _handle_api_error(
    e: Exception, context: str, object_id: Optional[str] = None
) -> Dict[str, Any]:
  """
  Centralized handler for HubSpot API errors.
  Logs the error and returns a structured error dictionary.
  """
  error_message = f"HubSpot API error in {context}"
  if object_id:
    error_message += f" for ID {object_id}"

  error_details_str = str(e)
  status_code = None
  parsed_error_details = None

  # Check for specific property validation errors
  property_validation_errors = []

  if isinstance(e, (ObjectApiException, DealApiException)):
    status_code = e.status
    if hasattr(e, "body") and e.body:
      error_details_str = e.body

      # Check for property validation error messages in the raw body
      if "Property values were not valid" in error_details_str:
        logfire.error(f"Property validation error detected in HubSpot API response",
                      context=context, object_id=object_id, status_code=status_code, error_body=error_details_str)

      try:
        # Enhanced error parsing for property-related issues
        if "PROPERTY_DOESNT_EXIST" in error_details_str:
          # Extract property name from error message
          import re
          property_match = re.search(
              r'Property \\"([^"]+)\\" does not exist', error_details_str)
          if property_match:
            invalid_property = property_match.group(1)
            logfire.error(f"Invalid HubSpot property name detected",
                          property_name=invalid_property,
                          context=context,
                          object_id=object_id)
            property_validation_errors.append({
                "property_name": invalid_property,
                "error": "Property does not exist in HubSpot"
            })

        # Attempt to parse the HubSpot error body if your HubSpotErrorDetail model is set up
        if HubSpotErrorDetail:  # Check if the model is available
          parsed_error_details = HubSpotErrorDetail.model_validate_json(
              e.body
          ).model_dump()
          logger.error(
              f"{error_message}: Status {status_code}, Parsed Body: {parsed_error_details}",
              exc_info=True,
          )
        else:
          logger.error(
              f"{error_message}: Status {status_code}, Raw Body: {e.body}",
              exc_info=True,
          )
      except (
          ValidationError,
          Exception,
      ) as parse_err:  # Catch Pydantic validation error or other parsing issues
        logger.error(
            f"{error_message}: Status {status_code}, Raw Body: {e.body}. Failed to parse error body: {parse_err}",
            exc_info=True,
        )
    else:
      logger.error(
          f"{error_message}: Status {status_code}, Details: {str(e)} (No body)",
          exc_info=True,
      )
  else:
    logger.error(
        f"Unexpected error occurred in {context}",
        extra={
            "error_message": error_message,
            "object_id": object_id,
            "context": context,
            "exception": str(e),
        },
        exc_info=True,
    )

  return {
      "error": error_message,
      "details_raw": error_details_str,
      "details_parsed": parsed_error_details,
      "status_code": status_code,
      "context": context,
      "object_id": object_id,
      "property_validation_errors": property_validation_errors if property_validation_errors else None,
  }
