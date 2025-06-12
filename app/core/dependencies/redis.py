"""
Core dependency injection module for Redis services.
"""

from typing import Optional
from app.services.redis.instrumented import InstrumentedRedisService
from app.services.redis.factory import get_instrumented_redis_service


async def get_redis_service_dep() -> InstrumentedRedisService:
  """
  Get instrumented Redis service with automatic latency tracking.
  This is the default Redis service for all application components.
  Note: BackgroundTasks should be injected directly in endpoints that need them.
  """
  return await get_instrumented_redis_service()
