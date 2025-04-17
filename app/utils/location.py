"""
Location utilities for determining locality based on drive time from key service hubs.
"""

import math
from typing import Tuple, List, Optional
import logfire

# Import geopy
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.distance import geodesic # For more accurate distance

# Define the key service hubs (latitude, longitude)
SERVICE_HUBS = {
    "omaha_ne": (41.2565, -95.9345),
    "denver_co": (39.7392, -104.9903),
    "kansas_city_ks": (39.1141, -94.6275)
}

# Initialize geocoder (Nominatim requires a user agent)
geolocator = Nominatim(user_agent="stahla_ai_sdr_app/1.0")

def get_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance between two points in kilometers."""
    return geodesic((lat1, lon1), (lat2, lon2)).km

def estimate_drive_time_hours(km_distance: float) -> float:
    """
    Estimate drive time in hours based on distance.
    Uses a slightly more conservative average speed (70 km/h).
    """
    avg_speed_km_per_hour = 70 # Adjusted average speed
    if avg_speed_km_per_hour <= 0:
        return float('inf') # Avoid division by zero
    return km_distance / avg_speed_km_per_hour

def is_location_local(lat: Optional[float], lon: Optional[float]) -> bool:
    """
    Determine if a location is considered "local" based on drive time.
    Local is defined as <= 3 hours drive time from any service hub.
    Uses geodesic distance.
    """
    if lat is None or lon is None:
        logfire.warn("Cannot determine locality: Latitude or longitude is missing.")
        return True  # Default to local if no coordinates

    min_drive_time = float('inf')
    closest_hub = None

    for hub_name, hub_coords in SERVICE_HUBS.items():
        hub_lat, hub_lon = hub_coords
        # Use geodesic distance
        distance_km = get_distance_km(lat, lon, hub_lat, hub_lon)
        drive_time = estimate_drive_time_hours(distance_km)
        logfire.debug(f"Calculated drive time to {hub_name}: {drive_time:.2f} hours ({distance_km:.1f} km)", location_lat=lat, location_lon=lon)

        if drive_time < min_drive_time:
            min_drive_time = drive_time
            closest_hub = hub_name

    is_local = min_drive_time <= 3.0
    logfire.info(f"Locality determined: {is_local}", min_drive_time_hours=min_drive_time, closest_hub=closest_hub, location_lat=lat, location_lon=lon)
    return is_local

def geocode_location(location_description: str, state_code: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Convert a location description to coordinates using Nominatim.
    Handles potential errors during geocoding with multiple fallback strategies.
    
    Args:
        location_description: Text description of the location
        state_code: Two-letter state code (e.g., 'NY', 'CO', 'NE') if available
        
    Returns:
        Tuple containing (latitude, longitude) or (None, None) if geocoding fails
    """
    logfire.info(f"Attempting to geocode location description: '{location_description}'", state_code=state_code)
    
    if not location_description and not state_code:
        logfire.warn("No location description or state code provided")
        return None, None
    
    # If we only have state code but no description, geocode the state
    if not location_description and state_code:
        try:
            state_query = f"state {state_code}, USA"
            logfire.info(f"Geocoding state only: '{state_query}'")
            location = geolocator.geocode(state_query, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"State geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"State geocoding failed: {str(e)}")
            return None, None
    
    # Try direct geocoding with state code if provided
    if state_code:
        try:
            enhanced_query = f"{location_description}, {state_code}, USA"
            logfire.info(f"Trying geocoding with state: '{enhanced_query}'")
            location = geolocator.geocode(enhanced_query, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"State-enhanced geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"State-enhanced geocoding failed: {str(e)}")
    
    # Try direct geocoding first (without state)
    try:
        location = geolocator.geocode(location_description, timeout=10, exactly_one=True)
        if location:
            logfire.info(f"Direct geocoding successful: Found ({location.latitude}, {location.longitude})")
            return location.latitude, location.longitude
    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        logfire.warn(f"Initial geocoding attempt failed: {str(e)}")
    
    # If direct geocoding failed, try with common city contexts
    common_contexts = [
        "New York, NY", 
        "USA",
        "United States"
    ]
    
    for context in common_contexts:
        enhanced_query = f"{location_description}, {context}"
        try:
            logfire.info(f"Trying enhanced query: '{enhanced_query}'")
            location = geolocator.geocode(enhanced_query, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"Enhanced geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"Enhanced geocoding attempt failed for '{enhanced_query}': {str(e)}")
    
    # Try with more permissive structured query
    try:
        # Extract likely place name from the description
        place_terms = location_description.split(',')[0].strip()
        logfire.info(f"Trying structured query with place: '{place_terms}'")
        location = geolocator.geocode({"q": place_terms}, timeout=10, exactly_one=False, limit=1)
        
        if location and len(location) > 0:
            first_match = location[0]
            logfire.info(f"Structured geocoding successful: Found ({first_match.latitude}, {first_match.longitude})")
            return first_match.latitude, first_match.longitude
    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        logfire.warn(f"Structured geocoding attempt failed: {str(e)}")
    
    # All attempts failed
    logfire.warn(f"Geocoding failed: No location found for '{location_description}'", state_code=state_code)
    return None, None

def determine_locality_from_description(location_description: Optional[str], state_code: Optional[str] = None) -> bool:
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
        logfire.info("No location description or state code provided, defaulting to local.")
        return True  # Default to local if no description provided
    
    # Step 1: Try to geocode the location with state information
    lat, lon = geocode_location(location_description, state_code)

    if lat is not None and lon is not None:
        # Step 2: If geocoding succeeded, check drive time
        return is_location_local(lat, lon)
    else:
        # Step 3: Fallback to simple keyword matching if geocoding failed
        logfire.warn(f"Geocoding failed for '{location_description}', falling back to keyword matching.", state_code=state_code)
        
        # If we have state code but geocoding failed, use state for determination
        if state_code:
            state_lower = state_code.lower()
            local_state_codes = ["ne", "co", "ks", "mo"]
            if state_lower in local_state_codes:
                logfire.info(f"State code '{state_code}' keyword match indicates local.")
                return True
            # Non-local states
            non_local_state_codes = ["ny", "ca", "fl", "tx", "wa", "or", "az", "nm", "ut", "id", "mt", "nd", "sd", "mn", "ia", "wi", "il", "in", "oh", "mi", "ky", "tn", "ms", "al", "ga", "sc", "nc", "va", "wv", "md", "de", "nj", "pa", "ct", "ri", "ma", "vt", "nh", "me", "ak", "hi", "dc", "pr", "vi", "gu", "mp", "as", "fm", "mh", "pw"]
            if state_lower in non_local_state_codes and state_lower not in local_state_codes:
                logfire.info(f"State code '{state_code}' keyword match indicates non-local.")
                return False
        
        # Location description matching (if available)
        if location_description:
            location_lower = location_description.lower()
            
            # Check for mentions of the hub cities or states
            local_keywords = ["omaha", "nebraska", "ne", "denver", "colorado", "co",
                            "kansas city", "kansas", "ks", "missouri", "mo"]
            if any(keyword in location_lower for keyword in local_keywords):
                logfire.info("Keyword match indicates local.")
                return True

            # Check for explicit mentions of being far away
            non_local_keywords = ["far away", "distant", "remote", "out of state",
                                "not local", "overseas", "international"]
            if any(keyword in location_lower for keyword in non_local_keywords):
                logfire.info("Keyword match indicates non-local.")
                return False

        # Default to local if keyword matching is inconclusive
        logfire.info("Keyword matching inconclusive, defaulting to local.")
        return True
