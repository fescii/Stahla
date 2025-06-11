# app/services/quote/logging/metrics/counter.py

"""
Metrics counter for quote service operations.
"""

import logging
import asyncio
from typing import Dict, Optional

import logfire

from app.services.redis.redis import RedisService

logger = logging.getLogger(__name__)


class MetricsCounter:
  """Handles metrics counting for quote service operations."""

  def __init__(self, redis_service: RedisService):
    self.redis_service = redis_service

  async def increment_cache_hit(self, cache_type: str = "pricing"):
    """Increment cache hit counter."""
    key = f"metrics:cache_hits:{cache_type}"
    try:
      await self._increment_counter(key)
      logfire.debug(f"Cache hit recorded for {cache_type}")
    except Exception as e:
      logfire.error(f"Failed to increment cache hit counter: {e}")

  async def increment_cache_miss(self, cache_type: str = "pricing"):
    """Increment cache miss counter."""
    key = f"metrics:cache_misses:{cache_type}"
    try:
      await self._increment_counter(key)
      logfire.debug(f"Cache miss recorded for {cache_type}")
    except Exception as e:
      logfire.error(f"Failed to increment cache miss counter: {e}")

  async def increment_quote_request(self, quote_type: str = "standard"):
    """Increment quote request counter."""
    key = f"metrics:quote_requests:{quote_type}"
    try:
      await self._increment_counter(key)
      logfire.debug(f"Quote request recorded for {quote_type}")
    except Exception as e:
      logfire.error(f"Failed to increment quote request counter: {e}")

  async def increment_quote_success(self, quote_type: str = "standard"):
    """Increment successful quote counter."""
    key = f"metrics:quote_success:{quote_type}"
    try:
      await self._increment_counter(key)
      logfire.debug(f"Quote success recorded for {quote_type}")
    except Exception as e:
      logfire.error(f"Failed to increment quote success counter: {e}")

  async def increment_quote_error(self, error_type: str):
    """Increment quote error counter."""
    key = f"metrics:quote_errors:{error_type}"
    try:
      await self._increment_counter(key)
      logfire.debug(f"Quote error recorded for {error_type}")
    except Exception as e:
      logfire.error(f"Failed to increment quote error counter: {e}")

  async def increment_sync_operation(self, operation_type: str):
    """Increment sync operation counter."""
    key = f"metrics:sync_operations:{operation_type}"
    try:
      await self._increment_counter(key)
      logfire.debug(f"Sync operation recorded for {operation_type}")
    except Exception as e:
      logfire.error(f"Failed to increment sync operation counter: {e}")

  async def record_processing_time(self, operation: str, duration_ms: float):
    """Record processing time for an operation."""
    try:
      # Store in a list for later aggregation
      key = f"metrics:processing_time:{operation}"
      client = await self.redis_service.get_client()
      client.lpush(key, str(duration_ms))

      # Keep only last 1000 measurements
      client.ltrim(key, 0, 999)

      logfire.debug(
          f"Processing time recorded for {operation}: {duration_ms}ms")
    except Exception as e:
      logfire.error(f"Failed to record processing time: {e}")

  async def get_metrics_summary(self) -> Dict[str, int]:
    """Get a summary of current metrics."""
    try:
      pattern = "metrics:*"
      keys = await self.redis_service.scan_keys(match=pattern)

      summary = {}
      for key in keys:
        try:
          value = await self.redis_service.get(key)
          if value and value.isdigit():
            summary[key] = int(value)
        except Exception:
          continue

      return summary
    except Exception as e:
      logfire.error(f"Failed to get metrics summary: {e}")
      return {}

  async def _increment_counter(self, key: str, amount: int = 1):
    """Increment a counter in Redis."""
    try:
      await self.redis_service.increment(key, amount)
    except Exception as e:
      logfire.error(f"Failed to increment counter {key}: {e}")
      raise
