# filepath: app/services/dash/cache/manager.py
import json
import logging
from typing import List, Optional
from app.services.redis.service import RedisService
from app.models.dash.dashboard import CacheItem, CacheSearchResult
from app.core.keys import PRICING_CATALOG_CACHE_KEY

logger = logging.getLogger(__name__)


class CacheManager:
  """Handles cache management operations for dashboard."""

  def __init__(self, redis_service: RedisService):
    self.redis = redis_service

  async def search_cache_keys(self, pattern: str) -> List[CacheSearchResult]:
    """Searches for cache keys matching a pattern and returns preview."""
    logger.info(f"Searching cache keys matching pattern: {pattern}")
    keys = await self.redis.scan_keys(match=pattern, count=1000)
    results = []

    if not keys:
      return results

    # Limit to 100 keys for performance
    keys_to_process = keys[:100]
    redis_client = None

    try:
      redis_client = await self.redis.get_client()

      # Use a more robust approach: process each key individually if pipeline fails
      pipeline_results = []
      try:
        async with redis_client.pipeline(transaction=False) as pipe:
          for key_to_fetch in keys_to_process:
            pipe.type(key_to_fetch)
            pipe.ttl(key_to_fetch)
          pipeline_results = await pipe.execute()

        # Verify we got the expected number of results
        expected_count = len(keys_to_process) * 2
        if len(pipeline_results) != expected_count:
          logger.warning(
              f"Pipeline results count mismatch. Expected {expected_count}, got {len(pipeline_results)}. "
              f"Processing keys individually for reliability."
          )
          raise ValueError("Pipeline results count mismatch")

      except Exception as pipe_error:
        logger.warning(
            f"Pipeline operation failed: {pipe_error}. Processing keys individually.")
        # Fallback: process each key individually
        pipeline_results = []
        for key_to_fetch in keys_to_process:
          try:
            key_type = await redis_client.type(key_to_fetch)
            ttl = await redis_client.ttl(key_to_fetch)
            pipeline_results.extend([key_type, ttl])
          except Exception as individual_error:
            logger.warning(
                f"Failed to get info for key '{key_to_fetch}': {individual_error}")
            # Add placeholder values to maintain index alignment
            pipeline_results.extend([b'string', -1])

      # Process results
      idx = 0
      for key_in_loop in keys_to_process:
        if idx + 1 < len(pipeline_results):
          key_type = pipeline_results[idx]
          ttl = pipeline_results[idx + 1]
          idx += 2

          preview = await self._get_key_preview(key_in_loop, key_type, redis_client)
          results.append(
              CacheSearchResult(
                  key=key_in_loop, value_preview=preview, ttl=ttl)
          )
        else:
          logger.warning(
              f"Insufficient pipeline results for key '{key_in_loop}'. "
              f"Expected index {idx+1}, but only {len(pipeline_results)} results available."
          )
          break

    except Exception as e:
      logger.error(
          f"Error during Redis pipeline operation in search_cache_keys: {e}",
          exc_info=True,
      )
    finally:
      if redis_client:
        await redis_client.close()

    return results

  async def _get_key_preview(self, key: str, key_type: bytes, redis_client=None) -> Optional[str]:
    """Get a preview of the key's value based on its Redis data type."""
    try:
      if key_type == b'string':
        # Use the redis service method for string operations
        value = await self.redis.get(key)
        if value:
          try:
            # Attempt to parse as JSON
            json_val = json.loads(value)
            return str(json_val)
          except json.JSONDecodeError:
            # If not JSON, return the full string value
            return str(value)
        return "Empty string"
      elif key_type == b'list':
        # For other types, provide basic info without complex operations
        return f"List data type (use dedicated Redis tools for detailed inspection)"
      elif key_type == b'hash':
        return f"Hash data type (use dedicated Redis tools for detailed inspection)"
      elif key_type == b'set':
        return f"Set data type (use dedicated Redis tools for detailed inspection)"
      elif key_type == b'zset':
        return f"Sorted Set data type (use dedicated Redis tools for detailed inspection)"
      else:
        return f"Data type: {key_type.decode() if isinstance(key_type, bytes) else str(key_type)}"
    except Exception as e:
      logger.warning(f"Error getting preview for key '{key}': {e}")
      return f"Error: {str(e)}"

  async def get_cache_item(self, key: str) -> Optional[CacheItem]:
    """Fetches a specific cache item with its TTL."""
    logger.info(f"Fetching cache item with TTL: {key}")

    value_from_pipe = None
    ttl_from_pipe = None
    redis_client = None
    try:
      redis_client = await self.redis.get_client()
      async with redis_client.pipeline(transaction=False) as pipe:
        pipe.get(key)
        pipe.ttl(key)
        pipe_results = await pipe.execute()
        if pipe_results and len(pipe_results) == 2:
          value_from_pipe = pipe_results[0]
          ttl_from_pipe = pipe_results[1]
        else:
          logger.warning(
              f"Unexpected pipeline results for get_cache_item key '{key}': {pipe_results}"
          )
    except Exception as e:
      logger.error(
          f"Error during Redis pipeline operation in get_cache_item for key '{key}': {e}",
          exc_info=True,
      )
    finally:
      if redis_client:
        await redis_client.close()

    if value_from_pipe is None:
      logger.warning(
          f"Cache key '{key}' not found or error fetching its value from pipeline."
      )
      return None

    parsed_value = None
    try:
      # Ensure value is string before json.loads
      if isinstance(value_from_pipe, bytes):
        value_from_pipe = value_from_pipe.decode("utf-8")

      if isinstance(value_from_pipe, str):
        parsed_value = json.loads(value_from_pipe)
      else:
        parsed_value = value_from_pipe

    except (json.JSONDecodeError, TypeError):
      parsed_value = value_from_pipe
    return CacheItem(key=key, value=parsed_value, ttl=ttl_from_pipe)

  async def clear_cache_item(self, key: str) -> bool:
    """Clears a specific key from the Redis cache."""
    logger.info(f"Clearing cache item: {key}")
    deleted_count = await self.redis.delete(key)
    if deleted_count == 0:
      logger.warning(f"Cache key not found or already expired: {key}")
      return False
    return True

  async def clear_pricing_catalog_cache(self) -> bool:
    """Clears the main pricing catalog cache key."""
    logger.warning(
        f"Clearing ENTIRE pricing catalog cache: {PRICING_CATALOG_CACHE_KEY}"
    )
    return await self.clear_cache_item(PRICING_CATALOG_CACHE_KEY)

  async def clear_maps_location_cache(self, location_pattern: str) -> int:
    """Clears Google Maps cache keys matching a location pattern."""
    pattern = f"maps:distance:*:{location_pattern}"
    logger.warning(
        f"Clearing Google Maps cache keys matching pattern: {pattern}")
    keys_to_delete = await self.redis.scan_keys(match=pattern)
    if not keys_to_delete:
      logger.info("No matching maps cache keys found to clear.")
      return 0
    deleted_count = await self.redis.delete(*keys_to_delete)
    logger.info(f"Cleared {deleted_count} maps cache keys matching pattern.")
    return deleted_count

  async def clear_cache_key(self, cache_key: str) -> bool:
    """Clears a specific key in Redis."""
    try:
      deleted_count = await self.redis.delete(cache_key)
      return deleted_count > 0
    except Exception as e:
      logger.error(
          f"Failed to clear Redis cache key '{cache_key}': {e}", exc_info=True
      )
      return False
