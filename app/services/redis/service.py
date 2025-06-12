# app/services/redis/service.py

"""
Unified Redis service with built-in latency tracking.
This single service handles all Redis operations with automatic instrumentation.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError
from fastapi import BackgroundTasks

from app.core.config import settings
from app.services.background.latency import record_external_api_latency_bg

logger = logging.getLogger(__name__)


class RedisService:
  """
  Unified Redis service with built-in latency tracking.
  Manages connection pool and provides instrumented operations.
  """
  _pool: Optional[ConnectionPool] = None

  def __init__(self):
    self.background_tasks: Optional[BackgroundTasks] = None
    self._connection_tested = False

  def set_background_tasks(self, background_tasks: BackgroundTasks):
    """Set background tasks for latency recording."""
    self.background_tasks = background_tasks

  def _record_latency(self, operation: str, latency_ms: float, success: bool = True):
    """Record latency for a Redis operation."""
    if self.background_tasks:
      self.background_tasks.add_task(
          record_external_api_latency_bg,
          redis=self,
          service_type="redis",
          latency_ms=latency_ms,
          api_endpoint=f"redis.{operation}",
          response_status=200 if success else 500
      )

  async def _ensure_connection(self):
    """Ensure Redis connection is available and tested."""
    if not self._connection_tested:
      try:
        client = await self.get_client()
        await client.ping()
        await client.close()
        self._connection_tested = True
        logger.debug("RedisService connection verified")
      except Exception as e:
        logger.warning(f"Redis connection test failed: {e}")
        self._connection_tested = False

  @classmethod
  async def get_pool(cls) -> ConnectionPool:
    """Gets the Redis connection pool, creating it if necessary."""
    if cls._pool is None:
      logger.info(
          f"Creating Redis connection pool for URL: {settings.REDIS_URL}")
      try:
        cls._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10
        )
      except Exception as e:
        logger.exception("Failed to create Redis connection pool", exc_info=e)
        raise RedisError("Could not connect to Redis") from e
    return cls._pool

  @classmethod
  async def get_client(cls) -> redis.Redis:
    """Gets a Redis client instance from the connection pool."""
    pool = await cls.get_pool()
    return redis.Redis(connection_pool=pool)

  @classmethod
  async def close_pool(cls):
    """Closes the Redis connection pool if it exists."""
    if cls._pool:
      logger.info("Closing Redis connection pool.")
      await cls._pool.disconnect()
      cls._pool = None

  async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Sets a value in Redis with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      await client.set(key, value, ex=ttl)
      logger.debug(f"Set key '{key}' with ttl={ttl}")
      success = True
      return True
    except RedisError as e:
      logger.error(f"Redis error setting key '{key}': {e}", exc_info=True)
      success = False
      return False
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("set", latency_ms, success)

  async def get(self, key: str) -> Optional[str]:
    """Gets a value from Redis with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      value = await client.get(key)
      logger.debug(f"Get key '{key}': {'Found' if value else 'Not found'}")
      success = True
      return value
    except RedisError as e:
      logger.error(f"Redis error getting key '{key}': {e}", exc_info=True)
      success = False
      return None
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("get", latency_ms, success)

  async def mget(self, keys: List[str]) -> List[Optional[str]]:
    """Gets multiple values from Redis with latency tracking."""
    if not keys:
      return []
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      values = await client.mget(keys)
      logger.debug(
          f"MGET for keys '{keys}': Found {len([v for v in values if v is not None])} values.")
      success = True
      return values
    except RedisError as e:
      logger.error(
          f"Redis error during MGET for keys '{keys}': {e}", exc_info=True)
      success = False
      return [None] * len(keys)
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency(f"mget({len(keys)})", latency_ms, success)

  async def set_json(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
    """Serializes data to JSON and sets it in Redis with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      json_data = json.dumps(data)
      success = await self.set(key, json_data, ttl=ttl)
      return success
    except TypeError as e:
      logger.error(
          f"Error serializing data for key '{key}': {e}", exc_info=True)
      success = False
      return False
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("set_json", latency_ms, success)

  async def get_json(self, key: str) -> Optional[Any]:
    """Gets a JSON string from Redis and deserializes it with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      json_data = await self.get(key)
      if json_data:
        result = json.loads(json_data)
        success = True
        return result
      success = True
      return None
    except json.JSONDecodeError as e:
      logger.error(f"Error decoding JSON for key '{key}': {e}", exc_info=True)
      success = False
      return None
    finally:
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("get_json", latency_ms, success)

  async def exists(self, key: str) -> bool:
    """Checks if a key exists in Redis with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      exists = await client.exists(key)
      logger.debug(f"Check existence for key '{key}': {exists > 0}")
      success = True
      return exists > 0
    except RedisError as e:
      logger.error(
          f"Redis error checking existence for key '{key}': {e}", exc_info=True)
      success = False
      return False
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("exists", latency_ms, success)

  async def delete(self, *keys: str) -> int:
    """Deletes one or more keys from Redis with latency tracking."""
    if not keys:
      logger.warning("Delete called with no keys.")
      return 0
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      result = await client.delete(*keys)
      logger.debug(
          f"Delete operation for keys '{keys}' resulted in {result} deletions.")
      success = True
      return result
    except RedisError as e:
      logger.error(f"Redis error deleting keys '{keys}': {e}", exc_info=True)
      success = False
      return 0
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency(f"delete({len(keys)})", latency_ms, success)

  async def increment(self, key: str, amount: int = 1) -> Optional[int]:
    """Increments the integer value of a key with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      new_value = await client.incrby(key, amount)
      logger.debug(
          f"Incremented key '{key}' by {amount}. New value: {new_value}")
      success = True
      return new_value
    except RedisError as e:
      logger.error(f"Redis error incrementing key '{key}': {e}", exc_info=True)
      success = False
      return None
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("increment", latency_ms, success)

  async def scan_keys(self, match: str = "*", count: int = 100) -> List[str]:
    """Scans for keys matching a pattern with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    keys = []
    cursor = 0
    try:
      client = await self.get_client()
      while True:
        cursor, current_keys = await client.scan(cursor=cursor, match=match, count=count)
        keys.extend(current_keys)
        if cursor == 0:
          break
      logger.debug(f"SCAN found {len(keys)} keys matching '{match}'")
      success = True
      return keys
    except RedisError as e:
      logger.error(
          f"Redis error during SCAN for pattern '{match}': {e}", exc_info=True)
      success = False
      return []
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency(f"scan({match})", latency_ms, success)

  async def ping(self) -> bool:
    """Pings the Redis server with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      await client.ping()
      logger.debug("Ping to Redis server successful.")
      success = True
      return True
    except RedisError as e:
      logger.error(f"Redis ping error: {e}", exc_info=True)
      success = False
      return False
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("ping", latency_ms, success)

  async def get_redis_info(self) -> Optional[Dict[str, Any]]:
    """Gets Redis INFO with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      info = await client.info()
      logger.debug("Fetched Redis INFO")
      success = True
      return info
    except RedisError as e:
      logger.error(f"Redis error getting INFO: {e}", exc_info=True)
      success = False
      return None
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("info", latency_ms, success)

  async def get_key_memory_usage(self, key: str) -> Optional[int]:
    """Gets memory usage for a key with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      memory_bytes = await client.execute_command("MEMORY USAGE", key)
      success = True
      if memory_bytes is not None:
        logger.debug(f"Memory usage for key '{key}': {memory_bytes} bytes")
        return int(memory_bytes)
      else:
        logger.debug(f"Key '{key}' not found for memory usage check.")
        return None
    except RedisError as e:
      success = False
      if "unknown command" in str(e).lower() or "wrong number of arguments" in str(e).lower():
        logger.warning(
            f"Redis command 'MEMORY USAGE {key}' not available or error: {e}")
      else:
        logger.error(
            f"Redis error getting memory usage for key '{key}': {e}", exc_info=True)
      return None
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("memory_usage", latency_ms, success)

  async def zremrangebyscore(self, key: str, min_score: int, max_score: int) -> int:
    """Removes elements from sorted set by score range with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      result = await client.zremrangebyscore(key, min_score, max_score)
      logger.debug(
          f"Removed {result} elements from sorted set '{key}' with score range [{min_score}, {max_score}]")
      success = True
      return result
    except RedisError as e:
      logger.error(
          f"Redis error removing range from sorted set '{key}': {e}", exc_info=True)
      success = False
      return 0
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("zremrangebyscore", latency_ms, success)

  async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
    """Adds elements to sorted set with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      result = await client.zadd(key, mapping)
      logger.debug(
          f"Added {result} elements to sorted set '{key}' with mapping {mapping}")
      success = True
      return result
    except RedisError as e:
      logger.error(
          f"Redis error adding to sorted set '{key}': {e}", exc_info=True)
      success = False
      return 0
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("zadd", latency_ms, success)

  async def zrangebyscore(self, key: str, min_score: int, max_score: int) -> List[str]:
    """Gets elements from sorted set by score range with latency tracking."""
    await self._ensure_connection()
    start_time = time.perf_counter()
    try:
      client = await self.get_client()
      result = await client.zrangebyscore(key, min_score, max_score)
      logger.debug(
          f"Retrieved {len(result)} elements from sorted set '{key}' with score range [{min_score}, {max_score}]")
      success = True
      return result
    except RedisError as e:
      logger.error(
          f"Redis error retrieving range from sorted set '{key}': {e}", exc_info=True)
      success = False
      return []
    finally:
      if 'client' in locals() and client:
        await client.close()
      latency_ms = (time.perf_counter() - start_time) * 1000
      self._record_latency("zrangebyscore", latency_ms, success)
