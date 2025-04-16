"""
Location utilities for determining locality based on drive time from key service hubs.
"""

import math
from typing import Tuple, List, Optional

# Define the key service hubs (latitude, longitude)
SERVICE_HUBS = {
    "omaha_ne": (41.2565, -95.9345),
    "denver_co": (39.7392, -104.9903),
    "kansas_city_ks": (39.1141, -94.6275)
}

# Approximate miles per degree of latitude/longitude (varies by latitude)
# More precise calculations would use a geodesic formula or API service
KM_PER_DEGREE_LAT = 111.0
KM_PER_DEGREE_LON_EQUATOR = 111.321

def km_per_degree_lon(lat: float) -> float:
    """Calculate km per degree of longitude at a given latitude."""
    return KM_PER_DEGREE_LON_EQUATOR * math.cos(math.radians(lat))

def simple_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate approximate distance between two points in kilometers.
    This is a simple calculation and doesn't account for road routes.
    For production use, consider using a geocoding/routing API.
    """
    lat_km = KM_PER_DEGREE_LAT * abs(lat1 - lat2)
    lon_km = km_per_degree_lon((lat1 + lat2) / 2) * abs(lon1 - lon2)
    return math.sqrt(lat_km**2 + lon_km**2)

def simple_drive_time_hours(km_distance: float) -> float:
    """
    Estimate drive time in hours based on distance.
    This is a very rough estimate using an average speed of 80 km/h.
    For production use, consider using a routing API.
    """
    avg_speed_km_per_hour = 80  # Rough estimate for highway driving
    return km_distance / avg_speed_km_per_hour

def is_location_local(lat: Optional[float], lon: Optional[float]) -> bool:
    """
    Determine if a location is considered "local" based on drive time.
    Local is defined as <= 3 hours drive time from any service hub.
    
    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        
    Returns:
        bool: True if location is within 3 hours of any service hub, 
              False if not, defaults to True if coordinates are None
    """
    if lat is None or lon is None:
        return True  # Default to local if no coordinates are provided
    
    for hub_name, hub_coords in SERVICE_HUBS.items():
        hub_lat, hub_lon = hub_coords
        distance_km = simple_distance_km(lat, lon, hub_lat, hub_lon)
        drive_time = simple_drive_time_hours(distance_km)
        
        if drive_time <= 3.0:  # 3 hours or less is considered local
            return True
    
    return False

def geocode_location(location_description: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Placeholder function to convert a location description to coordinates.
    In production, this would use a geocoding API like Google Maps, Mapbox, etc.
    
    Args:
        location_description: Text description of the location
        
    Returns:
        Tuple containing (latitude, longitude) or (None, None) if geocoding fails
    """
    # This is a placeholder. In production, implement an actual geocoding API call.
    # Example with a hypothetical geocoding service:
    # try:
    #     result = geocoding_service.geocode(location_description)
    #     return result.latitude, result.longitude
    # except Exception as e:
    #     logger.error(f"Geocoding failed: {e}")
    #     return None, None
    
    # For now, just return None to indicate geocoding service not implemented
    return None, None

def determine_locality_from_description(location_description: Optional[str]) -> bool:
    """
    Determine if a location description refers to a local area.
    
    Args:
        location_description: Text description of the location
        
    Returns:
        bool: True if local, False if not, defaults to True if description is None
    """
    if not location_description:
        return True  # Default to local if no description provided
    
    # Step 1: Try to geocode the location
    lat, lon = geocode_location(location_description)
    
    if lat is not None and lon is not None:
        # Step 2: If geocoding succeeded, check drive time
        return is_location_local(lat, lon)
    
    # Step 3: Fallback to simple keyword matching if geocoding failed
    location_lower = location_description.lower()
    
    # Check for mentions of the hub cities or states
    local_keywords = ["omaha", "nebraska", "ne", "denver", "colorado", "co", 
                     "kansas city", "kansas", "ks", "missouri", "mo"]
    
    for keyword in local_keywords:
        if keyword in location_lower:
            return True
    
    # Check for explicit mentions of being far away
    non_local_keywords = ["far away", "distant", "remote", "out of state", 
                         "not local", "overseas", "international"]
    
    for keyword in non_local_keywords:
        if keyword in location_lower:
            return False
    
    # Default to local if we can't determine otherwise
    return True
