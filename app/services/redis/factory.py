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


async def get_instrumented_redis_service(
    background_tasks: Optional[BackgroundTasks] = None
) -> InstrumentedRedisService:
  """
  Dependency injector for instrumented Redis service with latency tracking.

  Args:
      background_tasks: Optional BackgroundTasks for recording latency

  Returns:
      InstrumentedRedisService instance that wraps the base RedisService
  """
  if redis_service_instance is None:
    logger.error("Redis service requested but not available or not connected.")
    raise RuntimeError("Redis service is not available.")

  # Create instrumented wrapper around the base service
  instrumented = InstrumentedRedisService(background_tasks)
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
  async def create_instrumented(
      background_tasks: Optional[BackgroundTasks] = None
  ) -> InstrumentedRedisService:
    """Create an instrumented RedisService instance."""
    return await get_instrumented_redis_service(background_tasks)

  @staticmethod
  async def create_for_endpoint(
      background_tasks: BackgroundTasks,
      enable_instrumentation: bool = True
  ) -> RedisService:
    """
    Create Redis service instance for API endpoints.

    Args:
        background_tasks: BackgroundTasks from FastAPI endpoint
        enable_instrumentation: Whether to enable latency tracking

    Returns:
        Instrumented or basic RedisService based on configuration
    """
    if enable_instrumentation:
      return await get_instrumented_redis_service(background_tasks)
    else:
      return await get_redis_service()
