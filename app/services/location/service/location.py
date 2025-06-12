# filepath: app/services/location/service/location.py
from fastapi import BackgroundTasks
from typing import Optional
from app.models.location import DistanceResult
from app.services.redis.redis import RedisService
from app.services.mongo import MongoService
from app.services.location.cache import LocationCacheOperations
from app.services.location.google import GoogleMapsOperations
from app.services.location.areas import ServiceAreaChecker
from app.services.location.distance import DistanceCalculator


class LocationService:
  """
  Service for calculating distances between delivery locations and Stahla branches,
  utilizing Google Maps API and Redis caching. Branches are loaded dynamically from Redis.
  Integrates with MongoService for error logging.
  """

  def __init__(self, redis_service: RedisService, mongo_service: MongoService):
    self.redis_service = redis_service
    self.mongo_service = mongo_service

    # Initialize operation classes
    self.cache_ops = LocationCacheOperations(redis_service, mongo_service)
    self.google_ops = GoogleMapsOperations(redis_service, mongo_service)
    self.area_checker = ServiceAreaChecker(self.cache_ops)
    self.distance_calc = DistanceCalculator(
        self.cache_ops, self.google_ops, self.area_checker)

  async def get_distance_to_nearest_branch(
      self, delivery_location: str
  ) -> Optional[DistanceResult]:
    """
    Finds the nearest Stahla branch to a delivery location.

    Note: Background tasks should be attached using:
    from app.services.background.util import attach_background_tasks
    attach_background_tasks(location_service, background_tasks)
    """
    return await self.distance_calc.get_distance_to_nearest_branch(delivery_location)

  async def prefetch_distance(self, delivery_location: str):
    """
    Triggers the distance calculation and caching in the background.

    Note: Background tasks should be attached using:
    from app.services.background.util import attach_background_tasks
    attach_background_tasks(location_service, background_tasks)
    """
    await self.distance_calc.prefetch_distance(delivery_location)
