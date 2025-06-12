"""
Core dependency injection module for location services.
"""

from fastapi import Depends
from app.services.mongo.dependency import MongoService, get_mongo_service
from app.services.location import LocationService
from app.core.dependencies.redis import get_redis_service_dep


async def get_location_service_dep(
    mongo_service: MongoService = Depends(get_mongo_service),
) -> LocationService:
  """
  Get LocationService with instrumented Redis for automatic latency monitoring.
  Note: BackgroundTasks should be injected directly in endpoints that need them.
  """
  redis_service = await get_redis_service_dep()
  return LocationService(redis_service, mongo_service)
