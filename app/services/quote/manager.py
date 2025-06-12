# app/services/quote/manager.py

"""
Main QuoteService manager that delegates to specialized operation classes.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Literal
from datetime import date
from fastapi import Depends

from app.models.quote import QuoteRequest, QuoteResponse
from app.models.location import DistanceResult, BranchLocation
from app.services.redis.redis import RedisService, get_redis_service
from app.services.location import LocationService
from app.services.mongo import MongoService, get_mongo_service
from app.utils.location import geocode_location, SERVICE_HUBS, get_distance_km
from app.core.dependencies import get_location_service_dep

from .pricing.catalog.retriever import CatalogRetriever
from .pricing.delivery.calculator import DeliveryCalculator
from .pricing.extras.calculator import ExtrasCalculator
from .pricing.seasonal.multiplier import SeasonalMultiplier
from .pricing.trailer.calculator import TrailerCalculator
from .quote.builder.orchestrator import QuoteBuildingOrchestrator


logger = logging.getLogger(__name__)


class QuoteService:
  """
  Service responsible for calculating price quotes based on cached pricing data
  and calculated delivery distances.
  """

  def __init__(
      self,
      redis_service: RedisService,
      location_service: LocationService,
      mongo_service: MongoService,
  ):
    self.redis_service = redis_service
    self.location_service = location_service
    self.mongo_service = mongo_service

    # Initialize operation handlers
    self.catalog = CatalogRetriever(self)
    self.delivery = DeliveryCalculator(self)
    self.extras = ExtrasCalculator(self)
    self.seasonal = SeasonalMultiplier(self)
    self.trailer = TrailerCalculator(self)

    # Initialize quote building orchestrator
    self.quote_builder = QuoteBuildingOrchestrator(self)

  async def build_quote(
      self,
      quote_request: QuoteRequest,
      background_tasks: Optional[Any] = None,
  ) -> QuoteResponse:
    """Main method to build a complete quote."""
    return await self.quote_builder.build_quote(quote_request, background_tasks)

  async def get_config_for_quoting(self) -> Dict[str, Any]:
    """Get configuration for quoting."""
    return await self.catalog.get_config_for_quoting()

  def get_delivery_cost_for_distance(
      self,
      distance_miles: float,
      delivery_config: Dict[str, Any],
      branch_name: str = "omaha",
  ) -> float:
    """Get delivery cost for a given distance."""
    return self.delivery.get_delivery_cost_for_distance(
        distance_miles, delivery_config, branch_name
    )

  async def _estimate_distance_when_location_service_fails(
      self, delivery_location_str: str
  ) -> Optional[DistanceResult]:
    """
    Fallback method to estimate distances when the location service fails.
    Uses utilities from utils/location.py to geocode the delivery location
    and estimate distances to the nearest service hub.

    Args:
        delivery_location_str: The delivery location address as a string

    Returns:
        A DistanceResult object with the estimated distance data or None if geocoding fails
    """
    logger.info(
        f"Estimating distance for '{delivery_location_str}' using fallback mechanism"
    )

    # Step 1: Geocode the delivery location
    lat, lon = None, None  # Initialize
    try:
      loop = asyncio.get_running_loop()
      lat, lon = await loop.run_in_executor(None, geocode_location, delivery_location_str)
    except Exception as e:
      logger.error(
          f"Exception during fallback geocoding for '{delivery_location_str}': {e}", exc_info=True)
      # lat, lon will remain None

    if lat is None or lon is None:
      logger.error(
          f"Fallback geocoding failed for location: '{delivery_location_str}' (lat or lon is None after attempt)"
      )
      return None

    # Step 2: Find the nearest service hub
    nearest_hub_name = None
    min_distance_km = float("inf")

    for hub_name, (hub_lat, hub_lon) in SERVICE_HUBS.items():
      distance_km = get_distance_km(lat, lon, hub_lat, hub_lon)
      if distance_km < min_distance_km:
        min_distance_km = distance_km
        nearest_hub_name = hub_name

    if nearest_hub_name is None:
      logger.error("Failed to find nearest hub in fallback calculation")
      return None

    # Step 3: Convert km to miles and create fallback DistanceResult
    hub_description = nearest_hub_name.replace("_", " ").title()

    # Create a branch location object for the nearest hub
    nearest_branch = BranchLocation(
        name=f"{hub_description} (Estimated)",
        # No exact address available in fallback
        address=f"{hub_description}, USA",
    )

    # Convert km to miles (1 km ≈ 0.621371 miles)
    distance_miles = min_distance_km * 0.621371

    # Estimate other required fields
    distance_meters = int(min_distance_km * 1000)  # km to meters
    duration_seconds = int(
        distance_meters / 15
    )  # Rough estimate: 15 meters per second ≈ 33 mph

    logger.info(
        f"Fallback distance calculation complete: {distance_miles:.2f} miles to {nearest_hub_name}"
    )

    # Log to MongoDB for tracking fallback usage
    await self.mongo_service.log_error_to_db(
        service_name="QuoteService._estimate_distance_when_location_service_fails",
        error_type="FallbackLocationUsed",
        message=f"Used fallback location estimation for '{delivery_location_str}'",
        details={
            "delivery_location": delivery_location_str,
            "estimated_distance_miles": distance_miles,
            "nearest_hub": nearest_hub_name,
        },
    )

    return DistanceResult(
        nearest_branch=nearest_branch,
        delivery_location=delivery_location_str,
        distance_miles=distance_miles,
        distance_meters=distance_meters,
        duration_seconds=duration_seconds,
        within_service_area=True,  # Assume within service area for fallback
    )


async def get_quote_service(
    redis_service: RedisService = Depends(get_redis_service),
    mongo_service: MongoService = Depends(get_mongo_service),
) -> QuoteService:
  """Factory function to get QuoteService instance."""

  # Create location service dependency
  # Get location service with its required dependencies
  location_service = get_location_service_dep(
      redis_service=redis_service,
      mongo_service=mongo_service
  )

  return QuoteService(
      redis_service=redis_service,
      location_service=location_service,
      mongo_service=mongo_service,
  )
