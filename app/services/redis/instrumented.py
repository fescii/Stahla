# app/services/redis/instrumented.py

"""
Instrumented Redis service that automatically tracks latency for all operations.
This wrapper adds latency tracking to all Redis operations without modifying existing code.
"""

import time
import logging
from typing import Any, Dict, List, Optional
from app.services.redis.redis import RedisService
from fastapi import BackgroundTasks
from app.services.background.latency import record_external_api_latency_bg

logger = logging.getLogger(__name__)


class InstrumentedRedisService(RedisService):
  """
  Redis service wrapper that automatically tracks latency for all operations.
  This provides transparent latency monitoring at the Redis level.
  """

  def __init__(self):
    super().__init__()
    self.background_tasks = None

  def set_background_tasks(self, background_tasks: BackgroundTasks):
    """Set background tasks for latency recording.
    This should be called by attach_background_tasks utility."""
    self.background_tasks = background_tasks

  def _record_latency(self, operation: str, latency_ms: float, success: bool = True):
    """Record latency for a Redis operation."""
    if self.background_tasks:
      self.background_tasks.add_task(
          record_external_api_latency_bg,
          redis=self,  # Pass the base RedisService for recording
          service_type="redis",
          latency_ms=latency_ms,
          api_endpoint=f"redis.{operation}",
          response_status=200 if success else 500
      )  # The actual latency recording is now handled by the background.latency module

  async def get(self, key: str) -> Optional[str]:
    """Get with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().get(key)
      success = True
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("get", latency_ms, success)

  async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().set(key, value, ttl)
      success = result
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("set", latency_ms, success)

  async def mget(self, keys: List[str]) -> List[Optional[str]]:
    """MGET with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().mget(keys)
      success = True
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency(f"mget({len(keys)})", latency_ms, success)

  async def get_json(self, key: str) -> Optional[Any]:
    """Get JSON with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().get_json(key)
      success = True
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("get_json", latency_ms, success)

  async def set_json(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
    """Set JSON with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().set_json(key, data, ttl)
      success = result
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("set_json", latency_ms, success)

  async def delete(self, *keys: str) -> int:
    """Delete with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().delete(*keys)
      success = True
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency(f"delete({len(keys)})", latency_ms, success)

  async def increment(self, key: str, amount: int = 1) -> Optional[int]:
    """Increment with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().increment(key, amount)
      success = result is not None
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("increment", latency_ms, success)

  async def exists(self, key: str) -> bool:
    """Exists with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().exists(key)
      success = True
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("exists", latency_ms, success)

  async def scan_keys(self, match: str = "*", count: int = 100) -> List[str]:
    """Scan keys with latency tracking."""
    start_time = time.perf_counter()
    try:
      result = await super().scan_keys(match, count)
      success = True
      return result
    except Exception as e:
      success = False
      raise
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency(f"scan({match})", latency_ms, success)


# Dependency injection function for instrumented Redis
async def get_instrumented_redis_service() -> InstrumentedRedisService:
  """Creates and returns an InstrumentedRedisService instance without background tasks.

  Note: BackgroundTasks should be set in the endpoint using service.set_background_tasks()
  """
  return InstrumentedRedisService()
