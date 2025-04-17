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

def geocode_location(location_description: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Convert a location description to coordinates using Nominatim.
    Handles potential errors during geocoding.
    """
    logfire.info(f"Attempting to geocode location description: '{location_description}'")
    try:
        location = geolocator.geocode(location_description, timeout=10) # Add timeout
        if location:
            logfire.info(f"Geocoding successful: Found ({location.latitude}, {location.longitude})")
            return location.latitude, location.longitude
        else:
            logfire.warn(f"Geocoding failed: No location found for '{location_description}'")
            return None, None
    except GeocoderTimedOut:
        logfire.error(f"Geocoding failed: Service timed out for '{location_description}'")
        return None, None
    except GeocoderServiceError as e:
        logfire.error(f"Geocoding failed: Service error for '{location_description}': {e}")
        return None, None
    except Exception as e:
        logfire.exception(f"Unexpected error during geocoding for '{location_description}'")
        return None, None

def determine_locality_from_description(location_description: Optional[str]) -> bool:
    """
    Determine if a location description refers to a local area using geocoding.
    Falls back to keyword matching if geocoding fails or description is missing.
    """
    if not location_description:
        logfire.info("No location description provided, defaulting to local.")
        return True  # Default to local if no description provided

    # Step 1: Try to geocode the location
    lat, lon = geocode_location(location_description)

    if lat is not None and lon is not None:
        # Step 2: If geocoding succeeded, check drive time
        return is_location_local(lat, lon)
    else:
        # Step 3: Fallback to simple keyword matching if geocoding failed
        logfire.warn(f"Geocoding failed for '{location_description}', falling back to keyword matching.")
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
