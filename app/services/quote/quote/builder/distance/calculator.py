# app/services/quote/quote/builder/distance/calculator.py

"""
Distance calculation functionality for quote building.
"""

import logging
from typing import Any, Optional

from fastapi import BackgroundTasks
from app.models.location import DistanceResult

logger = logging.getLogger(__name__)


class DistanceCalculator:
  """Handles distance calculations for quote building."""

  def __init__(self, manager):
    self.manager = manager

  async def calculate_distance(
      self,
      delivery_location: str,
      background_tasks: Optional[Any] = None,
  ) -> DistanceResult:
    """
    Calculate delivery distance to nearest branch.

    Args:
        delivery_location: Location string for delivery
        background_tasks: FastAPI background tasks

    Returns:
        Distance result with nearest branch info

    Raises:
        ValueError: If distance cannot be calculated
    """
    distance_result = await self.manager.location_service.get_distance_to_nearest_branch(
        delivery_location,
        background_tasks=background_tasks or BackgroundTasks(),
    )

    if not distance_result:
      logger.warning(
          f"Could not determine delivery distance via LocationService for: {delivery_location}. Attempting fallback estimation."
      )

      # Log error to database
      if background_tasks and self.manager.mongo_service:
        from app.services.quote.background.tasks.processor import BackgroundTaskHelper
        BackgroundTaskHelper.add_error_logging_task(
            background_tasks,
            self.manager.mongo_service,
            "QuoteService.DistanceCalculator.calculate_distance",
            "LocationServiceError",
            "LocationService.get_distance_to_nearest_branch returned None. Trying fallback estimation.",
            {"delivery_location": delivery_location}
        )

      # Try fallback distance estimation
      distance_result = await self._estimate_distance_fallback(delivery_location)

      if distance_result:
        logger.info(
            f"Using estimated distance calculation: {distance_result.distance_miles:.2f} miles"
        )
      else:
        logger.error(
            f"Both primary and fallback distance estimation failed for: {delivery_location}."
        )
        raise ValueError(
            f"Could not determine delivery distance for location: {delivery_location}"
        )

    # Log the obtained distance result
    logger.info(
        f"Distance result obtained: Branch='{distance_result.nearest_branch.name}', Miles={distance_result.distance_miles:.2f}"
    )

    return distance_result

  async def _estimate_distance_fallback(
      self,
      delivery_location: str
  ) -> Optional[DistanceResult]:
    """
    Fallback distance estimation when primary service fails.

    Args:
        delivery_location: Location string for delivery

    Returns:
        Distance result or None if estimation fails
    """
    try:
      from app.utils.location import geocode_location, SERVICE_HUBS, get_distance_km

      # Geocode the delivery location
      lat, lon = geocode_location(delivery_location)
      if lat is None or lon is None:
        logger.warning(f"Could not geocode location: {delivery_location}")
        return None

      # Find nearest service hub
      min_distance = float('inf')
      nearest_hub_name = None
      nearest_hub_coords = None

      for hub_name, hub_coords in SERVICE_HUBS.items():
        hub_lat, hub_lon = hub_coords  # Unpack tuple

        distance_km = get_distance_km(lat, lon, hub_lat, hub_lon)
        if distance_km < min_distance:
          min_distance = distance_km
          nearest_hub_name = hub_name
          nearest_hub_coords = hub_coords

      if nearest_hub_name and nearest_hub_coords:
        from app.models.location import BranchLocation

        # Create branch location with proper address mapping
        hub_addresses = {
            "omaha_ne": "Omaha, NE",
            "denver_co": "Denver, CO",
            "kansas_city_ks": "Kansas City, KS"
        }

        branch = BranchLocation(
            name=nearest_hub_name.replace("_", " ").title(),
            address=hub_addresses.get(nearest_hub_name, "Unknown")
        )

        # Convert km to miles and meters
        distance_miles = min_distance * 0.621371
        distance_meters = int(min_distance * 1000)

        return DistanceResult(
            nearest_branch=branch,
            delivery_location=delivery_location,
            distance_miles=distance_miles,
            distance_meters=distance_meters,
            # Rough estimate: 1 mile per minute
            duration_seconds=int(distance_miles * 60),
            within_service_area=distance_miles <= 200  # Arbitrary threshold
        )

    except Exception as e:
      logger.error(f"Error in fallback distance estimation: {e}")

    return None
