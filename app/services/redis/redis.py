import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
  """
  Asynchronous Redis service for caching and data storage.
  Manages a connection pool and provides methods for common Redis operations.
  """
  _pool: Optional[ConnectionPool] = None

  @classmethod
  async def get_pool(cls) -> ConnectionPool:
    """Gets the Redis connection pool, creating it if necessary."""
    if cls._pool is None:
      logger.info(
          f"Creating Redis connection pool for URL: {settings.REDIS_URL}")
      try:
        print(f"Creating Redis connection pool for URL: {settings.REDIS_URL}")
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

  async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Sets a value in Redis.

    Args:
        key: The key to set.
        value: The value to store.
        ttl: Optional time-to-live in seconds.

    Returns:
        True if the set operation was successful, False otherwise.
    """
    try:
      client = await self.get_client()
      await client.set(key, value, ex=ttl)
      logger.debug(f"Set key '{key}' with ttl={ttl}")
      return True
    except RedisError as e:
      logger.error(f"Redis error setting key '{key}': {e}", exc_info=True)
      return False
    finally:
      if 'client' in locals() and client:
        await client.close()  # Ensure connection is released

  async def get(self, key: str) -> Optional[str]:
    """
    Gets a value from Redis.

    Args:
        key: The key to get.

    Returns:
        The value as a string if found, otherwise None.
    """
    try:
      client = await self.get_client()
      value = await client.get(key)
      logger.debug(f"Get key '{key}': {'Found' if value else 'Not found'}")
      return value
    except RedisError as e:
      logger.error(f"Redis error getting key '{key}': {e}", exc_info=True)
      return None
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def mget(self, keys: List[str]) -> List[Optional[str]]:
    """
    Gets multiple values from Redis corresponding to the given keys.

    Args:
        keys: A list of keys to get.

    Returns:
        A list of values (as strings or None if a key doesn't exist).
    """
    if not keys:
      return []
    try:
      client = await self.get_client()
      values = await client.mget(keys)
      logger.debug(
          f"MGET for keys '{keys}': Found {len([v for v in values if v is not None])} values.")
      return values
    except RedisError as e:
      logger.error(
          f"Redis error during MGET for keys '{keys}': {e}", exc_info=True)
      return [None] * len(keys)  # Return list of Nones on error
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def set_json(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
    """
    Serializes data to JSON and sets it in Redis.

    Args:
        key: The key to set.
        data: The Python object to serialize and store.
        ttl: Optional time-to-live in seconds.

    Returns:
        True if the operation was successful, False otherwise.
    """
    try:
      json_data = json.dumps(data)
      return await self.set(key, json_data, ttl=ttl)
    except TypeError as e:
      logger.error(
          f"Error serializing data for key '{key}': {e}", exc_info=True)
      return False
    except RedisError:  # Handled in self.set
      return False

  async def get_json(self, key: str) -> Optional[Any]:
    """
    Gets a JSON string from Redis and deserializes it.

    Args:
        key: The key to get.

    Returns:
        The deserialized Python object if found and valid, otherwise None.
    """
    try:
      json_data = await self.get(key)
      if json_data:
        return json.loads(json_data)
      return None
    except json.JSONDecodeError as e:
      logger.error(f"Error decoding JSON for key '{key}': {e}", exc_info=True)
      # Optionally delete the invalid key?
      # await self.delete(key)
      return None
    except RedisError:  # Handled in self.get
      return None

  async def exists(self, key: str) -> bool:
    """
    Checks if a key exists in Redis.

    Args:
        key: The key to check.

    Returns:
        True if the key exists, False otherwise.
    """
    try:
      client = await self.get_client()
      exists = await client.exists(key)
      logger.debug(f"Check existence for key '{key}': {exists > 0}")
      return exists > 0
    except RedisError as e:
      logger.error(
          f"Redis error checking existence for key '{key}': {e}", exc_info=True)
      return False
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def delete(self, *keys: str) -> int:
    """
    Deletes one or more keys from Redis.

    Args:
        *keys: The key(s) to delete.

    Returns:
        The number of keys that were deleted.
    """
    if not keys:
      logger.warning("Delete called with no keys.")
      return 0
    try:
      client = await self.get_client()
      # The redis-py client.delete() method accepts multiple keys
      result = await client.delete(*keys)
      logger.debug(
          f"Delete operation for keys '{keys}' resulted in {result} deletions.")
      return result  # result is the number of keys deleted
    except RedisError as e:
      logger.error(f"Redis error deleting keys '{keys}': {e}", exc_info=True)
      return 0  # Return 0 on error, as no keys were successfully deleted in this attempt
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def get_redis_info(self) -> Optional[Dict[str, Any]]:
    """
    Gets the Redis INFO command output.

    Returns:
        A dictionary containing Redis info if successful, otherwise None.
    """
    try:
      client = await self.get_client()
      info = await client.info()
      logger.debug("Fetched Redis INFO")
      return info
    except RedisError as e:
      logger.error(f"Redis error getting INFO: {e}", exc_info=True)
      return None
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def get_key_memory_usage(self, key: str) -> Optional[int]:
    """
    Gets the memory usage for a specific key in Redis.

    Args:
        key: The key to check.

    Returns:
        The memory usage in bytes if the key exists, otherwise None.
    """
    try:
      client = await self.get_client()
      # The MEMORY USAGE command might not be available in all Redis versions or configurations.
      # It returns None if the key doesn't exist.
      memory_bytes = await client.execute_command("MEMORY USAGE", key)
      if memory_bytes is not None:
        logger.debug(f"Memory usage for key '{key}': {memory_bytes} bytes")
        return int(memory_bytes)
      else:
        logger.debug(f"Key '{key}' not found for memory usage check.")
        return None
    except RedisError as e:
      # Handle cases where MEMORY USAGE might not be supported or other errors
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

  async def scan_keys(self, match: str = "*", count: int = 100) -> List[str]:
    """
    Iteratively scans for keys matching a pattern using SCAN.
    Safer than KEYS for large databases.

    Args:
        match: The glob-style pattern to match keys against.
        count: Approximate number of keys to fetch per iteration.

    Returns:
        A list of matching keys.
    """
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
      return keys
    except RedisError as e:
      logger.error(
          f"Redis error during SCAN for pattern '{match}': {e}", exc_info=True)
      return []  # Return empty list on error
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def increment(self, key: str, amount: int = 1) -> Optional[int]:
    """
    Increments the integer value of a key by the given amount.

    Args:
        key: The key to increment.
        amount: The amount to increment by (default is 1).

    Returns:
        The value of key after the increment, or None if an error occurred.
    """
    try:
      client = await self.get_client()
      # Use incrby for flexibility, defaults to incrementing by 1 if amount is 1
      new_value = await client.incrby(key, amount)
      logger.debug(
          f"Incremented key '{key}' by {amount}. New value: {new_value}")
      return new_value
    except RedisError as e:
      # Handle cases where the key holds a non-integer value
      logger.error(f"Redis error incrementing key '{key}': {e}", exc_info=True)
      return None
    finally:
      if 'client' in locals() and client:
        await client.close()

  @classmethod
  async def close_pool(cls):
    """Closes the Redis connection pool if it exists."""
    if cls._pool:
      logger.info("Closing Redis connection pool.")
      await cls._pool.disconnect()
      cls._pool = None

  # add these methods zremrangebyscore, zadd, zrangebyscore, and ping
  async def zremrangebyscore(self, key: str, min_score: int, max_score: int) -> int:
    """
    Removes elements from a sorted set within the specified score range.

    Args:
        key: The key of the sorted set.
        min_score: The minimum score (inclusive).
        max_score: The maximum score (inclusive).

    Returns:
        The number of elements removed.
    """
    try:
      client = await self.get_client()
      result = await client.zremrangebyscore(key, min_score, max_score)
      logger.debug(
          f"Removed {result} elements from sorted set '{key}' with score range [{min_score}, {max_score}]")
      return result
    except RedisError as e:
      logger.error(
          f"Redis error removing range from sorted set '{key}': {e}", exc_info=True)
      return 0
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
    """
    Adds elements to a sorted set with the specified scores.

    Args:
        key: The key of the sorted set.
        mapping: A dictionary of elements and their scores.

    Returns:
        The number of elements added to the sorted set.
    """
    try:
      client = await self.get_client()
      result = await client.zadd(key, mapping)
      logger.debug(
          f"Added {result} elements to sorted set '{key}' with mapping {mapping}")
      return result
    except RedisError as e:
      logger.error(
          f"Redis error adding to sorted set '{key}': {e}", exc_info=True)
      return 0
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def zrangebyscore(self, key: str, min_score: int, max_score: int) -> List[str]:
    """
    Gets elements from a sorted set within the specified score range.

    Args:
        key: The key of the sorted set.
        min_score: The minimum score (inclusive).
        max_score: The maximum score (inclusive).

    Returns:
        A list of elements within the specified score range.
    """
    try:
      client = await self.get_client()
      result = await client.zrangebyscore(key, min_score, max_score)
      logger.debug(
          f"Retrieved {len(result)} elements from sorted set '{key}' with score range [{min_score}, {max_score}]")
      return result
    except RedisError as e:
      logger.error(
          f"Redis error retrieving range from sorted set '{key}': {e}", exc_info=True)
      return []
    finally:
      if 'client' in locals() and client:
        await client.close()

  async def ping(self) -> bool:
    """
    Pings the Redis server to check connectivity.

    Returns:
        True if the server is reachable, False otherwise.
    """
    try:
      client = await self.get_client()
      await client.ping()
      logger.debug("Ping to Redis server successful.")
      return True
    except RedisError as e:
      logger.error(f"Redis ping error: {e}", exc_info=True)
      return False
    finally:
      if 'client' in locals() and client:
        await client.close()


redis_service_instance: Optional[RedisService] = None


async def startup_redis_service() -> Optional[RedisService]:
  """Creates RedisService instance and establishes connection pool."""
  global redis_service_instance
  if redis_service_instance is not None:
    logger.info("RedisService already initialized.")
    return redis_service_instance

  logger.info("Starting Redis service initialization...")
  instance = RedisService()
  try:
    # Test connection (e.g., by pinging)
    client = await instance.get_client()
    await client.ping()
    await client.close()  # Close the test client connection
    redis_service_instance = instance  # Store instance only on success
    logger.info("Redis service initialization successful.")
    return redis_service_instance
  except Exception as e:
    logger.error(f"Failed during Redis startup sequence: {e}", exc_info=True)
    redis_service_instance = None  # Ensure it's None on failure
    # No pool to close on the instance itself, close the class pool if created
    await RedisService.close_pool()
    return None  # Indicate failure


async def shutdown_redis_service():
  """Closes the Redis connection pool if the service was initialized."""
  global redis_service_instance
  if redis_service_instance:
    logger.info("Shutting down Redis service (closing class pool)...")
    # Close the class-level pool
    await RedisService.close_pool()
    redis_service_instance = None
  else:
    logger.info("Redis service was not initialized, skipping shutdown.")

# Dependency injector using the singleton instance


async def get_redis_service() -> RedisService:
  """Dependency injector to get the initialized RedisService instance."""
  if redis_service_instance is None:
    logger.error("Redis service requested but not available or not connected.")
    raise RuntimeError("Redis service is not available.")
  return redis_service_instance
