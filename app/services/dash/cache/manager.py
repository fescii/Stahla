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

    # Limit to 100 keys for performance and filter to ensure they match the pattern
    # Filter out any None/empty keys
    keys_to_process = [key for key in keys[:100] if key]

    if not keys_to_process:
      return results

    pipeline_results_list = []
    redis_client = None
    try:
      redis_client = await self.redis.get_client()

      # Process in smaller batches to avoid pipeline issues
      batch_size = 20
      for i in range(0, len(keys_to_process), batch_size):
        batch_keys = keys_to_process[i:i + batch_size]

        try:
          async with redis_client.pipeline(transaction=False) as pipe:
            for key_to_fetch in batch_keys:
              pipe.get(key_to_fetch)
              pipe.ttl(key_to_fetch)
            batch_results = await pipe.execute()
            if batch_results is not None:
              pipeline_results_list.extend(batch_results)
        except Exception as batch_error:
          logger.warning(
              f"Batch pipeline failed for keys {batch_keys}: {batch_error}")
          # Fallback: process each key individually for this batch
          for key_to_fetch in batch_keys:
            try:
              # First check the key type to handle different Redis data types
              key_type = await redis_client.type(key_to_fetch)
              ttl = await redis_client.ttl(key_to_fetch)

              if key_type == 'string':
                value = await redis_client.get(key_to_fetch)
              elif key_type == 'list':
                # For lists, get the length as a preview
                length = redis_client.llen(key_to_fetch)
                value = f"List with {length} items"
              elif key_type == 'hash':
                # For hashes, get the field count as a preview
                length = redis_client.hlen(key_to_fetch)
                value = f"Hash with {length} fields"
              elif key_type == 'set':
                # For sets, get the member count as a preview
                length = redis_client.scard(key_to_fetch)
                value = f"Set with {length} members"
              elif key_type == 'zset':
                # For sorted sets, get the member count as a preview
                length = redis_client.zcard(key_to_fetch)
                value = f"Sorted set with {length} members"
              elif key_type == 'none':
                value = None
              else:
                value = f"Redis type: {key_type}"

              pipeline_results_list.extend([value, ttl])
            except Exception as individual_error:
              logger.warning(
                  f"Failed to fetch key '{key_to_fetch}': {individual_error}")
              # Add None values to maintain alignment
              pipeline_results_list.extend([None, -1])

    except Exception as e:
      logger.error(
          f"Error during Redis pipeline operation in search_cache_keys: {e}",
          exc_info=True,
      )
    finally:
      if redis_client:
        await redis_client.close()

    # Process results
    idx = 0
    for key_in_loop in keys_to_process:
      if idx + 1 < len(pipeline_results_list):
        value_raw = pipeline_results_list[idx]
        ttl = pipeline_results_list[idx + 1]
        idx += 2

        preview = None
        if value_raw:
          try:
            # Attempt to parse as JSON
            json_val = json.loads(value_raw)
            preview = json_val
          except json.JSONDecodeError:
            # If not JSON, return the full string value
            preview = str(value_raw)

        results.append(
            CacheSearchResult(key=key_in_loop, value_preview=preview, ttl=ttl)
        )
      else:
        logger.warning(
            f"Pipeline results for search_cache_keys are shorter than expected. "
            f"Expected at least {idx+2} items for key '{key_in_loop}', "
            f"got {len(pipeline_results_list)} total pipeline results."
        )
        break

    return results

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
