# app/utils/latency.py

"""
Utility functions and decorators for adding latency tracking to external API calls
and other operations without modifying existing code extensively.
"""

import time
import functools
import logging
from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable
from fastapi import BackgroundTasks
from app.services.redis.service import RedisService
from app.services.dash.background import record_external_api_latency_bg

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LatencyTracker:
  """Async context manager for tracking operation latency."""

  def __init__(
      self,
      service_type: str,
      redis_service: RedisService,
      background_tasks: BackgroundTasks,
      operation_name: str = "unknown",
      request_id: Optional[str] = None
  ):
    self.service_type = service_type
    self.redis_service = redis_service
    self.background_tasks = background_tasks
    self.operation_name = operation_name
    self.request_id = request_id
    self.start_time = 0.0
    self.end_time = 0.0

  async def __aenter__(self):
    self.start_time = time.perf_counter()
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    self.end_time = time.perf_counter()
    latency_ms = (self.end_time - self.start_time) * 1000

    # Determine success based on whether an exception occurred
    success = exc_type is None
    response_status = 200 if success else 500

    # Record latency in background
    self.background_tasks.add_task(
        record_external_api_latency_bg,
        redis=self.redis_service,
        service_type=self.service_type,
        latency_ms=latency_ms,
        request_id=self.request_id,
        api_endpoint=self.operation_name,
        response_status=response_status
    )

    logger.debug(
        f"Tracked {self.service_type}.{self.operation_name}: "
        f"{latency_ms:.2f}ms (success: {success})"
    )

  def __enter__(self):
    self.start_time = time.perf_counter()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.end_time = time.perf_counter()
    latency_ms = (self.end_time - self.start_time) * 1000

    # Determine success based on whether an exception occurred
    success = exc_type is None
    response_status = 200 if success else 500

    # Record latency in background
    self.background_tasks.add_task(
        record_external_api_latency_bg,
        redis=self.redis_service,
        service_type=self.service_type,
        latency_ms=latency_ms,
        request_id=self.request_id,
        api_endpoint=self.operation_name,
        response_status=response_status
    )

    logger.debug(
        f"Tracked {self.service_type}.{self.operation_name}: "
        f"{latency_ms:.2f}ms (success: {success})"
    )


def track_latency(
    service_type: str,
    operation_name: Optional[str] = None,
    redis_service_attr: str = "redis_service",
    background_tasks_attr: str = "background_tasks"
):
  """
  Decorator to automatically track latency for async methods.

  Args:
      service_type: The service type for latency tracking (e.g., 'gmaps', 'quote', 'location', 'redis')
      operation_name: Optional operation name (defaults to function name)
      redis_service_attr: Attribute name for RedisService on the instance
      background_tasks_attr: Attribute name for BackgroundTasks on the instance
  """
  def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
      # Get the instance (self) - should be first argument
      if not args:
        logger.warning(
            f"No instance found for latency tracking on {func.__name__}")
        return await func(*args, **kwargs)

      instance = args[0]

      # Get required services from instance
      redis_service = getattr(instance, redis_service_attr, None)
      background_tasks = getattr(instance, background_tasks_attr, None)

      if not redis_service or not background_tasks:
        logger.debug(
            f"Missing required services for latency tracking on {func.__name__}: "
            f"redis_service={redis_service is not None}, "
            f"background_tasks={background_tasks is not None}"
        )
        return await func(*args, **kwargs)

      # Use operation name or function name
      op_name = operation_name or func.__name__

      # Track latency
      with LatencyTracker(
          service_type=service_type,
          redis_service=redis_service,
          background_tasks=background_tasks,
          operation_name=op_name
      ):
        return await func(*args, **kwargs)

    return wrapper
  return decorator


def track_external_call_latency(
    service_type: str,
    operation: str,
    redis_service: RedisService,
    background_tasks: BackgroundTasks,
    request_id: Optional[str] = None
) -> LatencyTracker:
  """
  Create a latency tracker for external API calls.

  Usage:
      with track_external_call_latency("gmaps", "distance_matrix", redis, bg_tasks) as tracker:
          result = await some_external_api_call()
  """
  return LatencyTracker(
      service_type=service_type,
      redis_service=redis_service,
      background_tasks=background_tasks,
      operation_name=operation,
      request_id=request_id
  )


def track_redis_operation_latency(
    operation: str,
    redis_service: RedisService,
    background_tasks: BackgroundTasks
) -> LatencyTracker:
  """
  Create a latency tracker specifically for Redis operations.

  Usage:
      with track_redis_operation_latency("get", redis, bg_tasks):
          result = await redis.get(key)
  """
  return LatencyTracker(
      service_type="redis",
      redis_service=redis_service,
      background_tasks=background_tasks,
      operation_name=f"redis.{operation}"
  )
