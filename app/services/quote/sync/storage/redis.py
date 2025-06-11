# app/services/quote/sync/storage/redis.py

"""
Redis storage operations for quote sync.
"""

import logging
from typing import Any, Dict, List, Optional

import logfire
from fastapi import BackgroundTasks

from app.services.redis.redis import RedisService
from app.services.mongo.mongo import MongoService
from ...background.tasks.processor import BackgroundTaskHelper

logger = logging.getLogger(__name__)


class RedisStorage:
  """Handles Redis storage operations for quote data."""

  def __init__(self, redis_service: RedisService, mongo_service: Optional[MongoService] = None):
    self.redis_service = redis_service
    self.mongo_service = mongo_service

  async def _handle_error(
      self,
      background_tasks: Optional[BackgroundTasks],
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None
  ):
    """Handle errors with background task logging."""
    if background_tasks and self.mongo_service:
      BackgroundTaskHelper.add_error_logging_task(
          background_tasks,
          self.mongo_service,
          service_name,
          error_type,
          message,
          details
      )
    else:
      # Just log locally if no background tasks or mongo service
      logger.error(f"{service_name} - {error_type}: {message}")

  async def store_pricing_catalog(
      self,
      catalog: Dict[str, Any],
      key: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store pricing catalog in Redis.

    Args:
        catalog: The pricing catalog data
        key: Redis key to store under
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      await self.redis_service.set_json(key, catalog)
      logfire.info(f"Pricing catalog stored in Redis with key: {key}")
      return True
    except Exception as e:
      error_msg = f"Failed to store pricing catalog in Redis with key {key}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "RedisStorage.store_pricing_catalog",
          "StoreError",
          error_msg,
          {"key": key, "catalog_keys": list(
              catalog.keys()) if isinstance(catalog, dict) else None}
      )
      return False

  async def store_branches(
      self,
      branches: List[Dict[str, Any]],
      key: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store branches list in Redis.

    Args:
        branches: The branches data
        key: Redis key to store under
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      await self.redis_service.set_json(key, branches)
      logfire.info(
          f"Branches stored in Redis with key: {key}, count: {len(branches)}")
      return True
    except Exception as e:
      error_msg = f"Failed to store branches in Redis with key {key}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "RedisStorage.store_branches",
          "StoreError",
          error_msg,
          {"key": key, "count": len(branches)}
      )
      return False

  async def store_states(
      self,
      states: List[Any],
      key: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store states list in Redis.

    Args:
        states: The states data (can be strings or dicts)
        key: Redis key to store under
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      await self.redis_service.set_json(key, states)
      logfire.info(
          f"States stored in Redis with key: {key}, count: {len(states)}")
      return True
    except Exception as e:
      error_msg = f"Failed to store states in Redis with key {key}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "RedisStorage.store_states",
          "StoreError",
          error_msg,
          {"key": key, "count": len(states)}
      )
      return False

  async def get_pricing_catalog(self, key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve pricing catalog from Redis.

    Args:
        key: Redis key to retrieve from

    Returns:
        Pricing catalog data or None if not found
    """
    try:
      catalog = await self.redis_service.get_json(key)
      if catalog:
        logfire.debug(f"Pricing catalog retrieved from Redis with key: {key}")
      return catalog
    except Exception as e:
      logfire.error(f"Failed to retrieve pricing catalog from Redis: {e}")
      return None

  async def get_branches(self, key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve branches from Redis.

    Args:
        key: Redis key to retrieve from

    Returns:
        Branches data or None if not found
    """
    try:
      branches = await self.redis_service.get_json(key)
      if branches:
        logfire.debug(f"Branches retrieved from Redis with key: {key}")
      return branches
    except Exception as e:
      logfire.error(f"Failed to retrieve branches from Redis: {e}")
      return None

  async def get_states(self, key: str) -> Optional[List[Any]]:
    """
    Retrieve states from Redis.

    Args:
        key: Redis key to retrieve from

    Returns:
        States data or None if not found
    """
    try:
      states = await self.redis_service.get_json(key)
      if states:
        logfire.debug(f"States retrieved from Redis with key: {key}")
      return states
    except Exception as e:
      logfire.error(f"Failed to retrieve states from Redis: {e}")
      return None

  async def clear_cache(self, key: str) -> bool:
    """
    Clear cached data for a specific key.

    Args:
        key: Redis key to clear

    Returns:
        True if successful, False otherwise
    """
    try:
      await self.redis_service.delete(key)
      logfire.info(f"Cleared Redis cache for key: {key}")
      return True
    except Exception as e:
      logfire.error(f"Failed to clear Redis cache for key {key}: {e}")
      return False

  # Convenience methods with default keys
  async def get_branches_default(self) -> Optional[List[Dict[str, Any]]]:
    """Get branches using the default cache key."""
    from ...utils.constants import BRANCH_LIST_CACHE_KEY
    return await self.get_branches(BRANCH_LIST_CACHE_KEY)

  async def get_states_default(self) -> Optional[List[Any]]:
    """Get states using the default cache key."""
    from ...utils.constants import STATES_LIST_CACHE_KEY
    return await self.get_states(STATES_LIST_CACHE_KEY)

  async def get_pricing_catalog_default(self) -> Optional[Dict[str, Any]]:
    """Get pricing catalog using the default cache key."""
    from ...utils.constants import PRICING_CATALOG_CACHE_KEY
    return await self.get_pricing_catalog(PRICING_CATALOG_CACHE_KEY)

  async def store_branches_default(
      self,
      branches: List[Dict[str, Any]],
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """Store branches using the default cache key."""
    from ...utils.constants import BRANCH_LIST_CACHE_KEY
    return await self.store_branches(branches, BRANCH_LIST_CACHE_KEY, background_tasks)

  async def store_states_default(
      self,
      states: List[Any],
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """Store states using the default cache key."""
    from ...utils.constants import STATES_LIST_CACHE_KEY
    return await self.store_states(states, STATES_LIST_CACHE_KEY, background_tasks)

  async def store_pricing_catalog_default(
      self,
      catalog: Dict[str, Any],
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """Store pricing catalog using the default cache key."""
    from ...utils.constants import PRICING_CATALOG_CACHE_KEY
    return await self.store_pricing_catalog(catalog, PRICING_CATALOG_CACHE_KEY, background_tasks)
