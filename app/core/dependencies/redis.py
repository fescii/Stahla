"""
Core dependency injection module for Redis services.
"""

from app.services.redis.service import RedisService
from app.services.redis.factory import get_redis_service


async def get_redis_service_dep() -> RedisService:
  """
  Get Redis service with automatic latency tracking built-in.
  Note: BackgroundTasks should be injected directly in endpoints that need them.
  """
  return await get_redis_service()
