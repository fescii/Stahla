# app/services/quote/background/tasks/processor.py

"""
Background task utilities using FastAPI BackgroundTasks.
"""

import logging
from typing import Any, Callable, Dict, Optional

import logfire
from fastapi import BackgroundTasks

from app.services.redis.service import RedisService

logger = logging.getLogger(__name__)


class BackgroundTaskHelper:
  """Helper for managing background tasks using FastAPI BackgroundTasks."""

  @staticmethod
  def add_error_logging_task(
      background_tasks: BackgroundTasks,
      mongo_service,
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None
  ):
    """Add error logging task to FastAPI background tasks."""
    background_tasks.add_task(
        log_error_to_db,
        mongo_service,
        service_name,
        error_type,
        message,
        details or {}
    )

  @staticmethod
  def add_metrics_task(
      background_tasks: BackgroundTasks,
      redis_service: RedisService,
      metric_type: str,
      key: str,
      increment: int = 1
  ):
    """Add metrics increment task to FastAPI background tasks."""
    background_tasks.add_task(
        increment_counter_bg,
        redis_service,
        key,
        increment
    )

  @staticmethod
  def add_cache_hit_task(
      background_tasks: BackgroundTasks,
      redis_service: RedisService,
      cache_type: str = "pricing"
  ):
    """Add cache hit increment task."""
    from app.core.keys import PRICING_CACHE_HITS_KEY
    key = PRICING_CACHE_HITS_KEY if cache_type == "pricing" else f"cache_hits:{cache_type}"
    BackgroundTaskHelper.add_metrics_task(
        background_tasks, redis_service, "cache_hit", key)

  @staticmethod
  def add_cache_miss_task(
      background_tasks: BackgroundTasks,
      redis_service: RedisService,
      cache_type: str = "pricing"
  ):
    """Add cache miss increment task."""
    from app.core.keys import PRICING_CACHE_MISSES_KEY
    key = PRICING_CACHE_MISSES_KEY if cache_type == "pricing" else f"cache_misses:{cache_type}"
    BackgroundTaskHelper.add_metrics_task(
        background_tasks, redis_service, "cache_miss", key)


async def log_error_to_db(
    mongo_service,
    service_name: str,
    error_type: str,
    message: str,
    details: Dict[str, Any]
):
  """Background task function to log errors to database."""
  try:
    await mongo_service.log_error_to_db(
        service_name=service_name,
        error_type=error_type,
        message=message,
        details=details
    )
    logfire.debug(f"Error logged to database: {service_name}.{error_type}")
  except Exception as e:
    logfire.error(f"Failed to log error to database: {e}")


async def increment_counter_bg(
    redis_service: RedisService,
    key: str,
    increment: int = 1
):
  """Background task function to increment counters."""
  try:
    # Use the actual increment method from dash.background
    from app.services.dash.background import increment_request_counter_bg
    await increment_request_counter_bg(redis_service, key)
    logfire.debug(f"Counter incremented: {key}")
  except Exception as e:
    logfire.error(f"Failed to increment counter {key}: {e}")
