# app/services/redis/factory.py

"""
Factory for creating Redis service instances.
Simple factory that creates unified instrumented Redis services.
"""

import logging
from .service import RedisService

logger = logging.getLogger(__name__)


async def get_redis_service() -> RedisService:
  """
  Create a new Redis service instance with built-in latency tracking.
  Each call creates a fresh instance that manages its own connections.
  """
  service = RedisService()
  return service


class RedisServiceFactory:
  """Factory class for creating Redis service instances."""

  @staticmethod
  async def create() -> RedisService:
    """Create a Redis service instance."""
    return await get_redis_service()

  @staticmethod
  async def create_for_endpoint() -> RedisService:
    """
    Create Redis service instance for API endpoints.
    Note: Call service.set_background_tasks(background_tasks) in your endpoint
    to enable latency tracking.
    """
    return await get_redis_service()
