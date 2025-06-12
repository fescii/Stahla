# app/services/quote/sync/storage/redis.py

"""
Redis storage operations for quote sync.
"""

import logging
from typing import Any, Dict, List, Optional

import logfire

from app.services.redis.service import RedisService
from app.services.quote.background.tasks.processor import log_error_to_db, BackgroundTaskHelper
from app.core.cachekeys import (
    PRICING_CATALOG_CACHE_KEY,
    BRANCH_LIST_CACHE_KEY,
    STATES_LIST_CACHE_KEY,
)
from app.services.dash.background import log_error_bg

logger = logging.getLogger(__name__)


class RedisStorage:
  """Handles Redis storage operations for quote data."""

  def __init__(self, redis_service: RedisService, mongo_service=None, background_tasks=None):
    self.redis_service = redis_service
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks

  async def _log_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Log error with background task if available."""
    if self.background_tasks and self.mongo_service:
      BackgroundTaskHelper.add_error_logging_task(
          self.background_tasks,
          self.mongo_service,
          "RedisStorage",
          error_type,
          message,
          details or {}
      )

  async def store_pricing_catalog(self, catalog: Dict[str, Any], key: str) -> bool:
    """
    Store pricing catalog in Redis.

    Args:
        catalog: The pricing catalog data
        key: Redis key to store under

    Returns:
        True if successful, False otherwise
    """
    try:
      await self.redis_service.set_json(key, catalog)
      logfire.info(f"Pricing catalog stored in Redis with key: {key}")
      return True
    except Exception as e:
      logfire.error(f"Failed to store pricing catalog in Redis: {e}")
      await self._log_error(
          "store_pricing_catalog_failed",
          f"Failed to store pricing catalog in Redis: {e}",
          {"key": key, "catalog_size": len(catalog) if catalog else 0}
      )
      return False

  async def store_branches(self, branches: List[Dict[str, Any]], key: str) -> bool:
    """
    Store branches list in Redis.

    Args:
        branches: The branches data
        key: Redis key to store under

    Returns:
        True if successful, False otherwise
    """
    try:
      await self.redis_service.set_json(key, branches)
      logfire.info(
          f"Branches stored in Redis with key: {key}, count: {len(branches)}")
      return True
    except Exception as e:
      logfire.error(f"Failed to store branches in Redis: {e}")
      await self._log_error(
          "store_branches_failed",
          f"Failed to store branches in Redis: {e}",
          {"key": key, "branches_count": len(branches) if branches else 0}
      )
      return False

  async def store_states(self, states: List[Any], key: str) -> bool:
    """
    Store states list in Redis.

    Args:
        states: The states data (can be strings or dicts)
        key: Redis key to store under

    Returns:
        True if successful, False otherwise
    """
    try:
      await self.redis_service.set_json(key, states)
      logfire.info(
          f"States stored in Redis with key: {key}, count: {len(states)}")
      return True
    except Exception as e:
      logfire.error(f"Failed to store states in Redis: {e}")
      await self._log_error(
          "store_states_failed",
          f"Failed to store states in Redis: {e}",
          {"key": key, "states_count": len(states) if states else 0}
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
      await self._log_error(
          "get_pricing_catalog_failed",
          f"Failed to retrieve pricing catalog from Redis: {e}",
          {"key": key}
      )
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
      await self._log_error(
          "get_branches_failed",
          f"Failed to retrieve branches from Redis: {e}",
          {"key": key}
      )
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
      await self._log_error(
          "get_states_failed",
          f"Failed to retrieve states from Redis: {e}",
          {"key": key}
      )
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
      await self._log_error(
          "clear_cache_failed",
          f"Failed to clear Redis cache for key {key}: {e}",
          {"key": key}
      )
      return False

  # Convenience methods with default keys
  async def get_branches_default(self) -> Optional[List[Dict[str, Any]]]:
    """Get branches using the default cache key."""
    return await self.get_branches(BRANCH_LIST_CACHE_KEY)

  async def get_states_default(self) -> Optional[List[Any]]:
    """Get states using the default cache key."""
    return await self.get_states(STATES_LIST_CACHE_KEY)

  async def get_pricing_catalog_default(self) -> Optional[Dict[str, Any]]:
    """Get pricing catalog using the default cache key."""
    return await self.get_pricing_catalog(PRICING_CATALOG_CACHE_KEY)

  async def store_branches_default(self, branches: List[Dict[str, Any]]) -> bool:
    """Store branches using the default cache key."""
    return await self.store_branches(branches, BRANCH_LIST_CACHE_KEY)

  async def store_states_default(self, states: List[Any]) -> bool:
    """Store states using the default cache key."""
    return await self.store_states(states, STATES_LIST_CACHE_KEY)

  async def store_pricing_catalog_default(self, catalog: Dict[str, Any]) -> bool:
    """Store pricing catalog using the default cache key."""
    return await self.store_pricing_catalog(catalog, PRICING_CATALOG_CACHE_KEY)
