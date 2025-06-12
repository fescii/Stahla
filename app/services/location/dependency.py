# filepath: app/services/location/dependency.py
from fastapi import Depends
from app.services.redis.service import RedisService
from app.services.redis.factory import get_redis_service
from app.services.mongo import MongoService, get_mongo_service
from app.services.location.service import LocationService


async def get_location_service(
    redis_service: RedisService = Depends(get_redis_service),
    mongo_service: MongoService = Depends(get_mongo_service),
) -> LocationService:
  """Dependency for FastAPI to inject LocationService."""
  return LocationService(redis_service, mongo_service)
