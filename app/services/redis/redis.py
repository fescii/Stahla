import json
import logging
from typing import Any, List, Optional

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
            logger.info(f"Creating Redis connection pool for URL: {settings.REDIS_URL}")
            try:
                cls._pool = ConnectionPool.from_url(
                    settings.REDIS_URL,
                    decode_responses=True, # Decode responses to strings
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
               await client.close() # Ensure connection is released

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
            logger.error(f"Error serializing data for key '{key}': {e}", exc_info=True)
            return False
        except RedisError: # Handled in self.set
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
        except RedisError: # Handled in self.get
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
            logger.error(f"Redis error checking existence for key '{key}': {e}", exc_info=True)
            return False
        finally:
            if 'client' in locals() and client:
               await client.close()

    async def delete(self, key: str) -> bool:
        """
        Deletes a key from Redis.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted, False otherwise.
        """
        try:
            client = await self.get_client()
            result = await client.delete(key)
            logger.debug(f"Deleted key '{key}': {result > 0}")
            return result > 0
        except RedisError as e:
            logger.error(f"Redis error deleting key '{key}': {e}", exc_info=True)
            return False
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
        cursor = '0'
        try:
            client = await self.get_client()
            while cursor != 0:
                cursor, current_keys = await client.scan(cursor=cursor, match=match, count=count)
                keys.extend(current_keys)
            logger.debug(f"SCAN found {len(keys)} keys matching '{match}'")
            return keys
        except RedisError as e:
            logger.error(f"Redis error during SCAN for pattern '{match}': {e}", exc_info=True)
            return [] # Return empty list on error
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

# Optional: Dependency for FastAPI
async def get_redis_service() -> RedisService:
    # You might want to manage the lifecycle differently,
    # but returning an instance works for dependency injection.
    return RedisService()

# Optional: Add lifespan event handlers in main.py to manage the pool
# @app.on_event("startup")
# async def startup_event():
#     await RedisService.get_pool() # Initialize pool on startup

# @app.on_event("shutdown")
# async def shutdown_event():
#     await RedisService.close_pool() # Close pool on shutdown

