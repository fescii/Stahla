# app/services/redis/factory.py

"""
Factory for creating Redis service instances with optional instrumentation.
"""

import logging
from typing import Optional
from fastapi import BackgroundTasks

from .redis import RedisService, redis_service_instance
from .instrumented import InstrumentedRedisService

logger = logging.getLogger(__name__)


async def get_redis_service() -> RedisService:
  """
  Default dependency injector - returns the basic RedisService instance.
  This maintains backward compatibility.
  """
  if redis_service_instance is None:
    logger.error("Redis service requested but not available or not connected.")
    raise RuntimeError("Redis service is not available.")
  return redis_service_instance


async def get_instrumented_redis_service() -> InstrumentedRedisService:
  """
  Dependency injector for instrumented Redis service with latency tracking.

  Returns:
      InstrumentedRedisService instance that wraps the base RedisService

  Note: 
      BackgroundTasks should be set in the endpoint using service.set_background_tasks()
      Don't pass BackgroundTasks to this function.
  """
  if redis_service_instance is None:
    logger.error("Redis service requested but not available or not connected.")
    raise RuntimeError("Redis service is not available.")

  # Create instrumented wrapper around the base service
  instrumented = InstrumentedRedisService()
  # Copy the connection pool from the base service
  instrumented._pool = redis_service_instance._pool
  return instrumented


class RedisServiceFactory:
  """Factory class for creating Redis service instances."""

  @staticmethod
  async def create_basic() -> RedisService:
    """Create a basic RedisService instance."""
    return await get_redis_service()

  @staticmethod
  async def create_instrumented() -> InstrumentedRedisService:
    """Create an instrumented RedisService instance."""
    return await get_instrumented_redis_service()

  @staticmethod
  async def create_for_endpoint(
      enable_instrumentation: bool = True
  ) -> RedisService:
    """
    Create Redis service instance for API endpoints.

    Args:
        enable_instrumentation: Whether to enable latency tracking

    Returns:
        Instrumented or basic RedisService based on configuration

    Note:
        When using the instrumented service, call service.set_background_tasks(background_tasks)
        in your endpoint to enable latency tracking.
    """
    if enable_instrumentation:
      return await get_instrumented_redis_service()
    else:
      return await get_redis_service()
