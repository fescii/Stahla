"""
Enhanced location utilities for determining locality based on drive time from key service hubs.
Supports additional location data fields from web forms.
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

def geocode_location(location_description: Optional[str] = None, 
                    state_code: Optional[str] = None,
                    city: Optional[str] = None,
                    postal_code: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Convert location information to coordinates using Nominatim.
    Handles potential errors during geocoding with multiple fallback strategies.
    
    Args:
        location_description: Text description of the location
        state_code: Two-letter state code (e.g., 'NY', 'CO') if available
        city: City name if available
        postal_code: Postal/ZIP code if available
        
    Returns:
        Tuple containing (latitude, longitude) or (None, None) if geocoding fails
    """
    # Log the geocoding attempt with all available location information
    logfire.info("Attempting to geocode location", 
                location_description=location_description,
                state_code=state_code,
                city=city,
                postal_code=postal_code)
    
    # If we have postal code, prioritize that for geocoding (most specific)
    if postal_code:
        try:
            postal_query = f"{postal_code}, USA"
            if state_code:
                postal_query = f"{postal_code}, {state_code}, USA"
            
            logfire.info(f"Geocoding postal code: '{postal_query}'")
            location = geolocator.geocode(postal_query, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"Postal code geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"Postal code geocoding failed: {str(e)}")
    
    # If we have city and state, try that combination next
    if city and state_code:
        try:
            city_state_query = f"{city}, {state_code}, USA"
            logfire.info(f"Geocoding city/state: '{city_state_query}'")
            location = geolocator.geocode(city_state_query, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"City/state geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"City/state geocoding failed: {str(e)}")
    
    # If we have a full address description and state, try that
    if location_description and state_code:
        try:
            enhanced_query = f"{location_description}, {state_code}, USA"
            logfire.info(f"Geocoding with description and state: '{enhanced_query}'")
            location = geolocator.geocode(enhanced_query, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"Description/state geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"Description/state geocoding failed: {str(e)}")
    
    # Try direct geocoding with just the location description
    if location_description:
        try:
            logfire.info(f"Trying direct geocoding: '{location_description}'")
            location = geolocator.geocode(location_description, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"Direct geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"Direct geocoding failed: {str(e)}")
    
    # If we only have state code
    if state_code and not (location_description or city or postal_code):
        try:
            state_query = f"state {state_code}, USA"
            logfire.info(f"Geocoding state only: '{state_query}'")
            location = geolocator.geocode(state_query, timeout=10, exactly_one=True)
            if location:
                logfire.info(f"State geocoding successful: Found ({location.latitude}, {location.longitude})")
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logfire.warn(f"State geocoding failed: {str(e)}")
    
    # All attempts failed
    logfire.warn("Geocoding failed: No location found with the provided information",
                location_description=location_description,
                state_code=state_code,
                city=city,
                postal_code=postal_code)
    return None, None

def determine_locality_from_description(location_description: Optional[str] = None, 
                                       state_code: Optional[str] = None,
                                       city: Optional[str] = None,
                                       postal_code: Optional[str] = None) -> bool:
    """
    Determine if a location description refers to a local area using geocoding.
    Falls back to keyword matching if geocoding fails or description is missing.
    
    Args:
        location_description: Text description of the location
        state_code: Two-letter state code (e.g., 'NY', 'CO') if available
        city: City name if available
        postal_code: Postal/ZIP code if available
        
    Returns:
        bool: True if local, False if not, defaults to True if no location info provided
    """
    # If we only have state code but no other location info
    if not location_description and not postal_code and not city and state_code:
        state_lower = state_code.lower()
        # Check if state matches any of our service hub states
        if state_lower in ["ne", "co", "ks", "mo"]:
            logfire.info(f"State code '{state_code}' indicates local area.")
            return True
    
    # If we have no location information at all
    if not location_description and not state_code and not city and not postal_code:
        logfire.info("No location information provided, defaulting to local.")
        return True
    
    # Step 1: Try to geocode the location with all available information
    lat, lon = geocode_location(location_description, state_code, city, postal_code)

    if lat is not None and lon is not None:
        # Step 2: If geocoding succeeded, check drive time
        return is_location_local(lat, lon)
    else:
        # Step 3: Fallback to keyword matching if geocoding failed
        logfire.warn("Geocoding failed, falling back to keyword matching",
                    location_description=location_description,
                    state_code=state_code,
                    city=city,
                    postal_code=postal_code)
        
        # Check state code first if available
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
        
        # Check city name if available
        if city:
            city_lower = city.lower()
            local_city_keywords = ["omaha", "denver", "kansas city"]
            if any(keyword in city_lower for keyword in local_city_keywords):
                logfire.info(f"City name '{city}' keyword match indicates local.")
                return True
        
        # Location description matching (if available)
        if location_description:
            location_lower = location_description.lower()
            
            # Check for mentions of the hub cities or states
            local_keywords = ["omaha", "nebraska", "ne", "denver", "colorado", "co",
                            "kansas city", "kansas", "ks", "missouri", "mo"]
            if any(keyword in location_lower for keyword in local_keywords):
                logfire.info("Location description keyword match indicates local.")
                return True

            # Check for explicit mentions of being far away
            non_local_keywords = ["far away", "distant", "remote", "out of state",
                                "not local", "overseas", "international"]
            if any(keyword in location_lower for keyword in non_local_keywords):
                logfire.info("Location description keyword match indicates non-local.")
                return False

        # Default to local if all keyword matching is inconclusive
        logfire.info("All keyword matching inconclusive, defaulting to local.")
        return True
