# app/services/quote/location/distance.py

"""
Distance calculation utilities for quote service.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

import logfire

from app.utils.location import geocode_location, SERVICE_HUBS, get_distance_km
from app.models.location import DistanceResult, BranchLocation

logger = logging.getLogger(__name__)


class DistanceCalculator:
  """Handles distance calculations for quote service."""

  def __init__(self, location_service):
    self.location_service = location_service

  async def calculate_delivery_distance(
      self,
      delivery_address: str,
      service_hubs: Optional[Dict] = None
  ) -> Optional[DistanceResult]:
    """
    Calculate delivery distance to the nearest service hub.

    Args:
        delivery_address: The delivery address
        service_hubs: Dictionary of service hubs (defaults to SERVICE_HUBS)

    Returns:
        DistanceResult with distance information or None if calculation failed
    """
    if not delivery_address:
      logfire.warning("No delivery address provided for distance calculation")
      return None

    try:
      # Use provided hubs or default
      hubs = service_hubs or SERVICE_HUBS

      # Try location service first
      result = await self.location_service.get_distance(delivery_address)
      if result and hasattr(result, 'distance_miles') and result.distance_miles is not None:
        logfire.info(
            f"Distance calculated via location service: {result.distance_miles} miles"
        )
        return result

      # Fallback to direct geocoding
      logfire.info("Location service failed, using fallback geocoding")
      return await self._calculate_distance_fallback(delivery_address, hubs)

    except Exception as e:
      logfire.error(f"Error calculating delivery distance: {e}")
      return None

  async def _calculate_distance_fallback(
      self,
      delivery_address: str,
      service_hubs: Dict[str, Tuple[float, float]]
  ) -> Optional[DistanceResult]:
    """
    Fallback distance calculation using direct geocoding.

    Args:
        delivery_address: The delivery address
        service_hubs: Dictionary of service hubs with lat/lng tuples

    Returns:
        DistanceResult or None if calculation failed
    """
    try:
      # Geocode delivery address (not async)
      loop = asyncio.get_running_loop()
      delivery_coords = await loop.run_in_executor(
          None, geocode_location, delivery_address
      )

      if not delivery_coords or None in delivery_coords:
        logfire.warning(
            f"Failed to geocode delivery address: {delivery_address}")
        return None

      delivery_lat, delivery_lon = delivery_coords

      # Ensure we have valid coordinates
      if delivery_lat is None or delivery_lon is None:
        logfire.warning(
            f"Invalid coordinates for delivery address: {delivery_address}")
        return None

      # Find nearest hub
      min_distance = float('inf')
      nearest_hub_name = None
      nearest_hub_coords = None

      for hub_name, hub_coords in service_hubs.items():
        hub_lat, hub_lon = hub_coords
        distance = get_distance_km(
            delivery_lat, delivery_lon, hub_lat, hub_lon)

        if distance < min_distance:
          min_distance = distance
          nearest_hub_name = hub_name
          nearest_hub_coords = hub_coords

      if nearest_hub_name is None:
        logfire.warning("No nearest hub found")
        return None

      # Convert km to miles and other required values
      distance_miles = min_distance * 0.621371  # km to miles conversion
      distance_meters = int(min_distance * 1000)  # km to meters
      # Rough estimate: 15 m/s ≈ 33 mph
      duration_seconds = int(distance_meters / 15)

      # Create branch location
      nearest_branch = BranchLocation(
          name=nearest_hub_name.replace("_", " ").title(),
          address=f"{nearest_hub_name.replace('_', ' ').title()}, USA"
      )

      # Determine if within service area (assuming 100 miles max)
      within_service_area = distance_miles <= 100.0

      result = DistanceResult(
          nearest_branch=nearest_branch,
          delivery_location=delivery_address,
          distance_miles=distance_miles,
          distance_meters=distance_meters,
          duration_seconds=duration_seconds,
          within_service_area=within_service_area
      )

      logfire.info(
          f"Fallback distance calculated: {distance_miles:.2f} miles to {nearest_hub_name}"
      )
      return result

    except Exception as e:
      logfire.error(f"Error in fallback distance calculation: {e}")
      return None

  async def get_estimated_distance(
      self,
      delivery_address: str,
      fallback_distance: float = 50.0
  ) -> DistanceResult:
    """
    Get estimated distance when precise calculation fails.

    Args:
        delivery_address: The delivery address
        fallback_distance: Default distance in miles

    Returns:
        DistanceResult with estimated values
    """
    # Create estimated branch location
    nearest_branch = BranchLocation(
        name="Estimated Hub",
        address="Service Area, USA"
    )

    # Convert to required units
    distance_meters = int(fallback_distance * 1609.34)  # miles to meters
    duration_seconds = int(distance_meters / 15)  # Rough estimate

    return DistanceResult(
        nearest_branch=nearest_branch,
        delivery_location=delivery_address,
        distance_miles=fallback_distance,
        distance_meters=distance_meters,
        duration_seconds=duration_seconds,
        within_service_area=fallback_distance <= 100.0
    )

  def is_within_service_area(
      self,
      distance_result: DistanceResult,
      max_distance_miles: float = 100.0
  ) -> bool:
    """
    Check if location is within service area.

    Args:
        distance_result: DistanceResult object
        max_distance_miles: Maximum service distance in miles

    Returns:
        True if within service area, False otherwise
    """
    is_within_area = distance_result.distance_miles <= max_distance_miles

    if not is_within_area:
      logfire.info(
          f"Location outside service area: "
          f"({distance_result.distance_miles}mi > {max_distance_miles}mi limit)"
      )

    return is_within_area
