# filepath: app/services/location/areas/checker.py
import re
import logfire
from typing import List, Dict, Any
from app.services.location.cache import LocationCacheOperations
from app.services.location.parsing import extract_location_components


class ServiceAreaChecker:
  """Handles service area validation for location service."""

  def __init__(self, cache_ops: LocationCacheOperations):
    self.cache_ops = cache_ops

  async def check_service_area(self, delivery_location: str) -> bool:
    """
    Checks if the delivery location is within the service area by extracting the state
    from the address and comparing it against the cached states data.
    Enhanced to handle complex address formats.
    """
    try:
      # Get states data from cache or MongoDB
      states_data = await self.cache_ops.get_states_from_cache_or_mongo()
      if not states_data:
        logfire.warning("No states data available for service area check")
        return False

      # Create sets of valid states and state codes for fast lookup
      valid_states = set()
      valid_codes = set()

      for state_entry in states_data:
        if isinstance(state_entry, dict):
          state_name = state_entry.get("state", "").strip().lower()
          state_code = state_entry.get("code", "").strip().upper()

          if state_name:
            valid_states.add(state_name)
          if state_code:
            valid_codes.add(state_code)

      # Extract structured components from the address
      components = extract_location_components(delivery_location)

      # Check state component first (most reliable)
      if components["state"] and components["state"].upper() in valid_codes:
        logfire.info(
            f"Location '{delivery_location}' is in service area (extracted state code: {components['state']})")
        return True

      # Extract state information from delivery location using multiple approaches
      location_upper = delivery_location.upper()
      location_lower = delivery_location.lower()

      # Check for state codes (e.g., "CA", "TX", "NY") - enhanced pattern
      state_code_pattern = r'\b([A-Z]{2})\b'
      code_matches = re.findall(state_code_pattern, location_upper)

      for code in code_matches:
        if code in valid_codes:
          logfire.info(
              f"Location '{delivery_location}' is in service area (found state code: {code})")
          return True

      # Check for full state names (with word boundaries)
      for state in valid_states:
        # Use word boundary regex for more accurate matching
        state_pattern = r'\b' + re.escape(state) + r'\b'
        if re.search(state_pattern, location_lower):
          logfire.info(
              f"Location '{delivery_location}' is in service area (found state name: {state})")
          return True

      # Additional checks for abbreviated address parts
      address_parts = [part.strip() for part in delivery_location.split(',')]
      for part in address_parts:
        part_upper = part.upper().strip()
        part_lower = part.lower().strip()

        # Check if any part is exactly a state code
        if part_upper in valid_codes:
          logfire.info(
              f"Location '{delivery_location}' is in service area (address part state code: {part_upper})")
          return True

        # Check if any part contains a state name
        if part_lower in valid_states:
          logfire.info(
              f"Location '{delivery_location}' is in service area (address part state name: {part_lower})")
          return True

      logfire.info(f"Location '{delivery_location}' is NOT in service area")
      return False

    except Exception as e:
      logfire.error(
          f"Error checking service area for '{delivery_location}': {e}", exc_info=True)
      await self.cache_ops.mongo_service.log_error_to_db(
          service_name="ServiceAreaChecker.check_service_area",
          error_type="ServiceAreaCheckError",
          message=f"Failed to check service area: {str(e)}",
          details={
              "delivery_location": delivery_location,
              "exception_type": type(e).__name__,
          },
      )
      # Return False on error for safety
      return False
