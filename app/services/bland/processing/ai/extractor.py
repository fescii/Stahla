# app/services/bland/processing/ai/extractor.py

"""
AI-powered field extraction for Bland voice call transcripts.
This module uses natural language processing to extract specific field values
from voice call transcripts and maps them to HubSpot contact and lead properties.
"""

import marvin
from typing import Dict, Any, Optional, List
from app.models.hubspot import HubSpotContactProperties, HubSpotLeadProperties
from app.models.classification import ClassificationInput
import logfire
from datetime import datetime
import re


@marvin.fn
def extract_contact_properties_from_transcript(
    transcript: str
) -> Dict[str, Any]:
  """
  Extract contact information from a voice call transcript.

  **Instructions:**
  - Extract contact details mentioned in the conversation
  - For phone numbers, format as a clean string without special characters unless standard formatting
  - For email addresses, extract the complete email if mentioned
  - For names, extract first and last name separately if possible
  - For locations, extract city, state, and postal code if mentioned
  - For company information, extract company name and industry if mentioned
  - If information is not mentioned or unclear, leave the field as None
  - **IMPORTANT: All date strings MUST be formatted as 'YYYY-MM-DD'**

  **Input:** Voice call transcript text
  **Output:** Dictionary with contact information fields
  """
  return {}  # Marvin will implement this and return the actual data


@marvin.fn
def extract_lead_properties_from_transcript(
    transcript: str
) -> Dict[str, Any]:
  """
  Extract lead/project information from a voice call transcript.

  **Instructions:**
  - Extract project and service details mentioned in the conversation
  - For dates, format as 'YYYY-MM-DD' 
  - For numeric values, extract as integers where appropriate
  - For boolean fields, determine True/False based on conversation context
  - For categorical fields, match to the closest appropriate category
  - If specific information is not mentioned, leave the field as None
  - **IMPORTANT: All date strings MUST be formatted as 'YYYY-MM-DD'**

  **Project Categories:**
  - Construction
  - Event
  - Emergency/Disaster Relief
  - Facility Management
  - Other

  **Service Types:**
  - Portable Restrooms
  - Restroom Trailers
  - Shower Trailers
  - Handwashing Stations
  - Waste Management
  - Other

  **Input:** Voice call transcript text
  **Output:** Dictionary with lead information fields
  """
  return {}  # Marvin will implement this and return the actual data


@marvin.fn
def extract_structured_call_data(
    transcript: str
) -> Dict[str, Any]:
  """
  Extract structured data from a voice call transcript for classification.

  **Instructions:**
  - Extract key information needed for lead classification
  - Focus on service requirements, location, timing, and project details
  - Return a structured dictionary with extracted values
  - **IMPORTANT: All date strings MUST be formatted as 'YYYY-MM-DD'**

  **Key fields to extract:**
  - product_interest: List of products/services mentioned
  - service_needed: Type of service requested
  - event_type: Type of event or project
  - location: Full address or location description
  - city: City name
  - state: State abbreviation (2 letters)
  - postal_code: ZIP/postal code
  - start_date: Project start date (YYYY-MM-DD)
  - end_date: Project end date (YYYY-MM-DD)
  - duration_days: Number of days for the rental/service
  - guest_count: Number of guests/people expected
  - required_stalls: Number of units/stalls needed
  - ada_required: Whether ADA compliance is needed (True/False)
  - power_available: Whether power is available at site (True/False)
  - water_available: Whether water is available at site (True/False)
  - budget_mentioned: Budget amount mentioned (e.g., '$2500', '$10k') or 'none'
  - comments: Additional important details or requirements

  **Input:** Voice call transcript text
  **Output:** Dictionary with extracted structured data
  """
  return {}  # Marvin will implement this and return the actual data


class AIFieldExtractor:
  """
  AI-powered field extraction service for Bland voice call processing.
  Uses Marvin AI to extract and map transcript data to HubSpot properties.
  """

  def __init__(self):
    self.logger = logfire

  async def extract_contact_data(self, transcript: str) -> Optional[HubSpotContactProperties]:
    """
    Extract contact information from transcript using AI.

    Args:
        transcript: Voice call transcript text

    Returns:
        HubSpotContactProperties object with extracted data or None if extraction fails
    """
    try:
      self.logger.info("Extracting contact data from transcript using AI")

      contact_dict = extract_contact_properties_from_transcript(transcript)

      # Convert dictionary to HubSpotContactProperties object
      contact_data = HubSpotContactProperties(**contact_dict)

      self.logger.info("Contact data extraction successful",
                       extracted_fields=len([k for k, v in contact_data.model_dump().items() if v is not None]))

      return contact_data

    except Exception as e:
      self.logger.error(f"Error extracting contact data: {e}", exc_info=True)
      return None

  async def extract_lead_data(self, transcript: str) -> Optional[HubSpotLeadProperties]:
    """
    Extract lead/project information from transcript using AI.

    Args:
        transcript: Voice call transcript text

    Returns:
        HubSpotLeadProperties object with extracted data or None if extraction fails
    """
    try:
      self.logger.info("Extracting lead data from transcript using AI")

      lead_dict = extract_lead_properties_from_transcript(transcript)

      # Convert dictionary to HubSpotLeadProperties object
      lead_data = HubSpotLeadProperties(**lead_dict)

      self.logger.info("Lead data extraction successful",
                       extracted_fields=len([k for k, v in lead_data.model_dump().items() if v is not None]))

      return lead_data

    except Exception as e:
      self.logger.error(f"Error extracting lead data: {e}", exc_info=True)
      return None

  async def extract_classification_data(self, transcript: str) -> Optional[Dict[str, Any]]:
    """
    Extract structured data for classification from transcript using AI.

    Args:
        transcript: Voice call transcript text

    Returns:
        Dictionary with extracted structured data or None if extraction fails
    """
    try:
      self.logger.info(
          "Extracting classification data from transcript using AI")

      classification_data = extract_structured_call_data(transcript)

      # Validate and clean the extracted data
      cleaned_data = self._validate_and_clean_data(classification_data)

      self.logger.info("Classification data extraction successful",
                       extracted_fields=len([k for k, v in cleaned_data.items() if v is not None]))

      return cleaned_data

    except Exception as e:
      self.logger.error(
          f"Error extracting classification data: {e}", exc_info=True)
      return None

  def _validate_and_clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean extracted data.

    Args:
        data: Raw extracted data dictionary

    Returns:
        Cleaned and validated data dictionary
    """
    cleaned = {}

    for key, value in data.items():
      if value is None:
        continue

      # Clean string values
      if isinstance(value, str):
        value = value.strip()
        if value.lower() in ['none', 'null', 'n/a', '']:
          continue

      # Validate date formats
      if key.endswith('_date') and isinstance(value, str):
        if self._is_valid_date_format(value):
          cleaned[key] = value
        else:
          self.logger.warning(f"Invalid date format for {key}: {value}")
          continue

      # Validate boolean values
      elif key in ['ada_required', 'power_available', 'water_available']:
        if isinstance(value, bool):
          cleaned[key] = value
        elif isinstance(value, str):
          cleaned[key] = value.lower() in ['true', 'yes', '1',
                                           'required', 'available']

      # Validate numeric values
      elif key in ['duration_days', 'guest_count', 'required_stalls']:
        if isinstance(value, (int, float)):
          cleaned[key] = int(value) if value >= 0 else None
        elif isinstance(value, str) and value.isdigit():
          cleaned[key] = int(value)

      # Clean list values
      elif isinstance(value, list):
        cleaned_list = [item.strip() if isinstance(item, str) else item
                        for item in value if item is not None]
        if cleaned_list:
          cleaned[key] = cleaned_list

      else:
        cleaned[key] = value

    return cleaned

  def _is_valid_date_format(self, date_str: str) -> bool:
    """
    Validate that date string is in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid format, False otherwise
    """
    try:
      datetime.strptime(date_str, '%Y-%m-%d')
      return True
    except ValueError:
      return False

  async def extract_comprehensive_data(self, transcript: str) -> Dict[str, Any]:
    """
    Extract all available data from transcript using AI.

    Args:
        transcript: Voice call transcript text

    Returns:
        Dictionary containing contact data, lead data, and classification data
    """
    try:
      self.logger.info(
          "Starting comprehensive data extraction from transcript")

      # Extract all data types in parallel
      contact_task = self.extract_contact_data(transcript)
      lead_task = self.extract_lead_data(transcript)
      classification_task = self.extract_classification_data(transcript)

      # Wait for all extractions to complete
      contact_data = await contact_task
      lead_data = await lead_task
      classification_data = await classification_task

      result = {
          'contact_properties': contact_data.model_dump() if contact_data else None,
          'lead_properties': lead_data.model_dump() if lead_data else None,
          'classification_data': classification_data,
          'extraction_timestamp': datetime.utcnow().isoformat(),
          'transcript_length': len(transcript) if transcript else 0
      }

      self.logger.info("Comprehensive data extraction completed successfully")

      return result

    except Exception as e:
      self.logger.error(
          f"Error in comprehensive data extraction: {e}", exc_info=True)
      return {
          'contact_properties': None,
          'lead_properties': None,
          'classification_data': None,
          'error': str(e),
          'extraction_timestamp': datetime.utcnow().isoformat()
      }


# Create singleton instance
ai_field_extractor = AIFieldExtractor()
