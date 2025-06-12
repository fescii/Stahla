"""
Core dependency injection module for quote services.
"""

from fastapi import Depends
from app.services.mongo.dependency import MongoService, get_mongo_service
from app.services.location import LocationService
from app.core.dependencies.redis import get_redis_service_dep


async def get_quote_service_dep(
    mongo_service: MongoService = Depends(get_mongo_service),
):
  """
  Get QuoteService with instrumented Redis for automatic latency monitoring.
  Note: BackgroundTasks should be injected directly in endpoints that need them.
  """
  from app.services.quote import QuoteService

  redis_service = await get_redis_service_dep()
  location_service = LocationService(redis_service, mongo_service)

  return QuoteService(
      redis_service=redis_service,
      location_service=location_service,
      mongo_service=mongo_service,
  )
