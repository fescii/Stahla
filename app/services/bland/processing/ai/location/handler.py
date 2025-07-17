"""
Location processing service for extracted data.

Handles location validation and local area detection for voice call processing.
"""

from typing import Dict, Any, Optional
import logfire
from app.services.location.service.location import LocationService


class LocationHandler:
  """
  Processes location information from extracted voice call data.

  Determines if locations are within service area and validates addresses.
  """

  def __init__(self, location_service: Optional[LocationService] = None):
    self.logger = logfire
    self.location_service = location_service

  async def process_location_data(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process location information from extracted data.

    Args:
        extraction_result: Results from field extraction

    Returns:
        Dictionary containing location processing results
    """
    try:
      # Get location data from various sources
      contact_data = extraction_result.get('contact_properties', {})
      lead_data = extraction_result.get('lead_properties', {})
      classification_data = extraction_result.get('classification_data', {})

      # Try different location fields in order of preference
      location_candidates = [
          lead_data.get('service_address'),
          lead_data.get('event_location_description'),
          contact_data.get('address'),
          classification_data.get('location'),
          classification_data.get('delivery_location'),
          self._build_city_state_location(classification_data)
      ]

      # Find the first non-empty location
      location = self._find_best_location(location_candidates)

      if location and self.location_service:
        # Use location service to check if in service area
        distance_result = await self.location_service.get_distance_to_nearest_branch(location)
        is_local = distance_result is not None

        return {
            'location': location,
            'is_local': is_local,
            'distance_result': distance_result,
            'location_source': 'extracted_data',
            'processing_success': True
        }
      elif location:
        return {
            'location': location,
            'is_local': False,  # Default when no location service
            'location_source': 'extracted_data',
            'processing_success': True
        }
      else:
        return {
            'location': None,
            'is_local': False,
            'location_source': 'none_found',
            'processing_success': False
        }

    except Exception as e:
      self.logger.error("Error processing location data",
                        error=str(e), exc_info=True)
      return {
          'location': None,
          'is_local': False,
          'location_error': str(e),
          'processing_success': False
      }

  def _build_city_state_location(self, classification_data: Dict[str, Any]) -> str:
    """
    Build location string from city and state data.

    Args:
        classification_data: Classification data containing city/state

    Returns:
        Combined city, state location string
    """
    city = classification_data.get('city', '').strip()
    state = classification_data.get('state', '').strip()

    if city and state:
      return f"{city}, {state}"
    elif city:
      return city
    elif state:
      return state

    return ""

  def _find_best_location(self, location_candidates: list) -> str:
    """
    Find the best location from a list of candidates.

    Args:
        location_candidates: List of potential location strings

    Returns:
        Best location string or empty string if none found
    """
    for candidate in location_candidates:
      if candidate and isinstance(candidate, str) and candidate.strip():
        cleaned = candidate.strip()
        # Skip generic or invalid locations
        if len(cleaned) > 2 and not cleaned.lower() in ['n/a', 'none', 'unknown']:
          return cleaned

    return ""


# Create handler instance when needed
def create_location_handler(location_service: Optional[LocationService] = None) -> LocationHandler:
  """Create a location handler instance with optional location service."""
  return LocationHandler(location_service)
