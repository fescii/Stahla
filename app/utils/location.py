"""
Location utilities for determining locality based on drive time from key service hubs.
"""

import math
import json
import hashlib
import time
from typing import Tuple, List, Optional, Dict, Any
import logfire

# Import geopy
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.distance import geodesic  # For more accurate distance

# Define the key service hubs (latitude, longitude)
SERVICE_HUBS = {
    "omaha_ne": (41.2565, -95.9345),
    "denver_co": (39.7392, -104.9903),
    "kansas_city_ks": (39.1141, -94.6275),
}

# Initialize geocoder with basic configuration
try:
  geolocator = Nominatim(user_agent="stahla_ai_sdr_app/1.0")
  logfire.info("Initialized geocoder with standard configuration")
except Exception as e:
  logfire.error(f"Error initializing geocoder: {e}")
  # Create a placeholder that will gracefully fail
  from unittest.mock import MagicMock
  geolocator = MagicMock()
  geolocator.geocode.return_value = None

# In-memory cache for geocoding results
_GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {}
# Cache expiration time in seconds (24 hours)
_CACHE_EXPIRY = 24 * 60 * 60


def _get_cache_key(query: str) -> str:
  """Generate a cache key for a geocoding query."""
  return hashlib.md5(query.encode('utf-8')).hexdigest()


def _get_cached_geocode(query: str) -> Optional[Tuple[float, float]]:
  """
  Try to get geocoded coordinates from the cache.
  Returns None if not in cache or cache entry expired.
  """
  cache_key = _get_cache_key(query)
  cached_entry = _GEOCODE_CACHE.get(cache_key)

  if cached_entry:
    timestamp = cached_entry.get("timestamp", 0)
    if time.time() - timestamp < _CACHE_EXPIRY:
      coords = cached_entry.get("coords")
      if coords:
        lat, lon = coords
        logfire.info(f"Using cached coordinates for '{query}': ({lat}, {lon})")
        return lat, lon

  return None


def _cache_geocode(query: str, lat: float, lon: float) -> None:
  """Store geocoded coordinates in the cache."""
  cache_key = _get_cache_key(query)
  _GEOCODE_CACHE[cache_key] = {
      "coords": (lat, lon),
      "timestamp": time.time()
  }
  logfire.info(f"Cached coordinates for '{query}': ({lat}, {lon})")

  # Simple cache size management - if cache grows too large, remove oldest entries
  if len(_GEOCODE_CACHE) > 1000:
    # Get oldest 200 items by timestamp
    oldest_keys = sorted(_GEOCODE_CACHE.items(),
                         key=lambda x: x[1].get("timestamp", 0))[:200]
    for key, _ in oldest_keys:
      _GEOCODE_CACHE.pop(key, None)
    logfire.info(
        f"Cleaned {len(oldest_keys)} oldest entries from geocode cache")


def get_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  """Calculate geodesic distance between two points in kilometers."""
  return geodesic((lat1, lon1), (lat2, lon2)).km


def estimate_drive_time_hours(km_distance: float) -> float:
  """
  Estimate drive time in hours based on distance.
  Uses a slightly more conservative average speed (70 km/h).
  """
  avg_speed_km_per_hour = 70  # Adjusted average speed
  if avg_speed_km_per_hour <= 0:
    return float("inf")  # Avoid division by zero
  return km_distance / avg_speed_km_per_hour


def is_location_local(lat: Optional[float], lon: Optional[float]) -> bool:
  """
  Determine if a location is considered "local" based on drive time.
  Local is defined as <= 3 hours drive time from any service hub.
  Uses geodesic distance.
  """
  if lat is None or lon is None:
    logfire.warn(
        "Cannot determine locality: Latitude or longitude is missing.")
    return True  # Default to local if no coordinates

  min_drive_time = float("inf")
  closest_hub = None

  for hub_name, hub_coords in SERVICE_HUBS.items():
    hub_lat, hub_lon = hub_coords
    # Use geodesic distance
    distance_km = get_distance_km(lat, lon, hub_lat, hub_lon)
    drive_time = estimate_drive_time_hours(distance_km)
    logfire.debug(
        f"Calculated drive time to {hub_name}: {drive_time:.2f} hours ({distance_km:.1f} km)",
        location_lat=lat,
        location_lon=lon,
    )

    if drive_time < min_drive_time:
      min_drive_time = drive_time
      closest_hub = hub_name

  is_local = min_drive_time <= 3.0
  logfire.info(
      f"Locality determined: {is_local}",
      min_drive_time_hours=min_drive_time,
      closest_hub=closest_hub,
      location_lat=lat,
      location_lon=lon,
  )
  return is_local


def geocode_location(
    location_description: str, state_code: Optional[str] = None
) -> Tuple[Optional[float], Optional[float]]:
  """
  Convert a location description to coordinates using Nominatim with caching.
  Handles potential errors during geocoding with multiple fallback strategies.

  Args:
      location_description: Text description of the location
      state_code: Two-letter state code (e.g., 'NY', 'CO', 'NE') if available

  Returns:
      Tuple containing (latitude, longitude) or (None, None) if geocoding fails
  """
  logfire.info(
      f"Attempting to geocode location description: '{location_description}'",
      state_code=state_code,
  )

  if not location_description and not state_code:
    logfire.warn("No location description or state code provided")
    return None, None

  # If we only have state code but no description, geocode the state
  if not location_description and state_code:
    state_query = f"state {state_code}, USA"

    # Try cache first
    cached_coords = _get_cached_geocode(state_query)
    if cached_coords:
      return cached_coords

    try:
      logfire.info(f"Geocoding state only: '{state_query}'")
      # Remove type-problematic parameters
      location = geolocator.geocode(state_query, exactly_one=True)

      # Safely extract coordinates
      lat, lon = _extract_coordinates_safely(location)
      if lat is not None and lon is not None:
        _cache_geocode(state_query, lat, lon)
        logfire.info(f"State geocoding successful: Found ({lat}, {lon})")
        return lat, lon
      return None, None
    except Exception as e:
      logfire.warn(f"State geocoding failed: {str(e)}")
      return None, None

  # Try direct geocoding with state code if provided
  if state_code:
    enhanced_query = f"{location_description}, {state_code}, USA"

    # Try cache first
    cached_coords = _get_cached_geocode(enhanced_query)
    if cached_coords:
      return cached_coords

    try:
      logfire.info(f"Trying geocoding with state: '{enhanced_query}'")
      # Remove type-problematic parameters
      location = geolocator.geocode(
          enhanced_query, exactly_one=True)

      # Safely extract coordinates
      lat, lon = _extract_coordinates_safely(location)
      if lat is not None and lon is not None:
        _cache_geocode(enhanced_query, lat, lon)
        logfire.info(
            f"State-enhanced geocoding successful: Found ({lat}, {lon})")
        return lat, lon
      return None, None
    except Exception as e:
      logfire.warn(f"State-enhanced geocoding failed: {str(e)}")

  # Try direct geocoding first (without state)
  # Try cache first
  cached_coords = _get_cached_geocode(location_description)
  if cached_coords:
    return cached_coords

  try:
    logfire.info(f"Trying direct geocoding: '{location_description}'")
    # Remove type-problematic parameters
    location = geolocator.geocode(
        location_description, exactly_one=True)

    # Safely extract coordinates
    lat, lon = _extract_coordinates_safely(location)
    if lat is not None and lon is not None:
      _cache_geocode(location_description, lat, lon)
      logfire.info(f"Direct geocoding successful: Found ({lat}, {lon})")
      return lat, lon
    return None, None
  except Exception as e:
    logfire.warn(f"Initial geocoding attempt failed: {str(e)}")

  # If direct geocoding failed, try with common city contexts
  common_contexts = ["New York, NY", "USA", "United States"]

  for context in common_contexts:
    enhanced_query = f"{location_description}, {context}"

    # Try cache first
    cached_coords = _get_cached_geocode(enhanced_query)
    if cached_coords:
      return cached_coords

    try:
      logfire.info(f"Trying enhanced query: '{enhanced_query}'")
      location = geolocator.geocode(enhanced_query, exactly_one=True)

      # Safely extract coordinates
      lat, lon = _extract_coordinates_safely(location)
      if lat is not None and lon is not None:
        _cache_geocode(enhanced_query, lat, lon)
        logfire.info(
            f"Enhanced geocoding successful: Found ({lat}, {lon})")
        return lat, lon
      return None, None
    except Exception as e:
      logfire.warn(
          f"Enhanced geocoding attempt failed for '{enhanced_query}': {str(e)}")

  # Try with more permissive structured query
  try:
    # Extract likely place name from the description
    place_terms = location_description.split(",")[0].strip()

    # Try cache first
    cached_coords = _get_cached_geocode(place_terms)
    if cached_coords:
      return cached_coords

    logfire.info(f"Trying structured query with place: '{place_terms}'")
    location = geolocator.geocode(
        {"q": place_terms}, exactly_one=False, limit=1)

    # Ensure location is a list before proceeding
    if isinstance(location, list) and len(location) > 0:
      first_match = location[0]

      # Safely extract coordinates
      lat, lon = _extract_coordinates_safely(first_match)
      if lat is not None and lon is not None:
        _cache_geocode(place_terms, lat, lon)
        logfire.info(
            f"Structured geocoding successful: Found ({lat}, {lon})")
        return lat, lon
      return None, None
  except Exception as e:
    logfire.warn(f"Structured geocoding attempt failed: {str(e)}")

  # All attempts failed
  logfire.warn(
      f"Geocoding failed: No location found for '{location_description}'", state_code=state_code)
  return None, None


def _extract_coordinates_safely(location_obj) -> Tuple[Optional[float], Optional[float]]:
  """
  Safely extract latitude and longitude from a location object.

  This function handles potential issues with accessing location attributes,
  including cases where attributes might be coroutines or have unexpected types.

  Args:
      location_obj: A location object from geocoder

  Returns:
      A tuple of (latitude, longitude) or (None, None) if extraction fails
  """
  if not location_obj:
    return None, None

  try:
    # Special handling for coroutine objects (can happen with certain geopy configurations)
    if hasattr(location_obj, "__await__"):
      logfire.warn(
          "Location object is a coroutine, cannot extract coordinates directly")
      return None, None

    if not (hasattr(location_obj, "latitude") and hasattr(location_obj, "longitude")):
      logfire.error(
          f"Location object missing latitude/longitude attributes: {type(location_obj)}")
      return None, None

    lat = getattr(location_obj, "latitude", None)
    lon = getattr(location_obj, "longitude", None)

    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
      return lat, lon
    else:
      logfire.error(
          f"Invalid coordinate types: lat={type(lat)}, lon={type(lon)}")
      return None, None
  except Exception as e:
    logfire.error(f"Error extracting coordinates: {e}")
    return None, None


def determine_locality_from_description(
    location_description: str, state_code: Optional[str] = None,
    city: Optional[str] = None,
    postal_code: Optional[str] = None,
) -> bool:
  """
  Determine if a location description refers to a local area using geocoding.
  Falls back to keyword matching if geocoding fails or description is missing.

  Args:
      location_description: Text description of the location
      state_code: Two-letter state code (e.g., 'NY', 'CO') if available

  Returns:
      bool: True if local, False if not, defaults to True if description is None
  """
  # If we only have state code but no description
  if not location_description and state_code:
    state_lower = state_code.lower()
    # Check if state matches any of our service hub states
    if state_lower in ["ne", "co", "ks", "mo"]:
      logfire.info(f"State code '{state_code}' indicates local area.")
      return True

  if not location_description and not state_code:
    logfire.info(
        "No location description or state code provided, defaulting to local."
    )
    return True  # Default to local if no description provided

  # Ensure location_description is not None before passing to geocode_location
  if location_description is None:
      # This case should ideally be handled by the checks above,
      # but adding for type safety and clarity.
    logfire.warn("Geocoding skipped: location_description is None.")
    # Fallback to keyword matching based on state_code if available
    lat, lon = None, None
  else:
    # Step 1: Try to geocode the location with state information
    lat, lon = geocode_location(location_description, state_code)

  if lat is not None and lon is not None:
    # Step 2: If geocoding succeeded, check drive time
    return is_location_local(lat, lon)
  else:
    # Step 3: Fallback to simple keyword matching if geocoding failed
    logfire.warn(
        f"Geocoding failed for '{location_description}', falling back to keyword matching.",
        state_code=state_code,
    )

    # If we have state code but geocoding failed, use state for determination
    if state_code:
      state_lower = state_code.lower()
      local_state_codes = ["ne", "co", "ks", "mo"]
      if state_lower in local_state_codes:
        logfire.info(
            f"State code '{state_code}' keyword match indicates local."
        )
        return True
      # Non-local states
      non_local_state_codes = [
          "ny",
          "ca",
          "fl",
          "tx",
          "wa",
          "or",
          "az",
          "nm",
          "ut",
          "id",
          "mt",
          "nd",
          "sd",
          "mn",
          "ia",
          "wi",
          "il",
          "in",
          "oh",
          "mi",
          "ky",
          "tn",
          "ms",
          "al",
          "ga",
          "sc",
          "nc",
          "va",
          "wv",
          "md",
          "de",
          "nj",
          "pa",
          "ct",
          "ri",
          "ma",
          "vt",
          "nh",
          "me",
          "ak",
          "hi",
          "dc",
          "pr",
          "vi",
          "gu",
          "mp",
          "as",
          "fm",
          "mh",
          "pw",
      ]
      if (
          state_lower in non_local_state_codes
          and state_lower not in local_state_codes
      ):
        logfire.info(
            f"State code '{state_code}' keyword match indicates non-local."
        )
        return False

    # Location description matching (if available)
    if location_description:
      location_lower = location_description.lower()

      # Check for mentions of the hub cities or states
      local_keywords = [
          "omaha",
          "nebraska",
          "ne",
          "denver",
          "colorado",
          "co",
          "kansas city",
          "kansas",
          "ks",
          "missouri",
          "mo",
      ]
      if any(keyword in location_lower for keyword in local_keywords):
        logfire.info("Keyword match indicates local.")
        return True

      # Check for explicit mentions of being far away
      non_local_keywords = [
          "far away",
          "distant",
          "remote",
          "out of state",
          "not local",
          "overseas",
          "international",
      ]
      if any(keyword in location_lower for keyword in non_local_keywords):
        logfire.info("Keyword match indicates non-local.")
        return False

    # Default to local if keyword matching is inconclusive
    logfire.info("Keyword matching inconclusive, defaulting to local.")
    return True
