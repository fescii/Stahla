# app/services/quote/sync/storage/mongo.py

"""
MongoDB storage operations for quote sync.
"""

import logging
from typing import Any, Dict, List, Optional

import logfire
from fastapi import BackgroundTasks

from app.services.mongo.mongo import MongoService
from app.services.redis.redis import RedisService
from ...background.tasks.processor import BackgroundTaskHelper

logger = logging.getLogger(__name__)


class MongoStorage:
  """Handles MongoDB storage operations for quote data."""

  def __init__(self, mongo_service: MongoService, redis_service=None):
    self.mongo_service = mongo_service
    self.redis_service = redis_service

  async def _handle_error(
      self,
      background_tasks: Optional[BackgroundTasks],
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None
  ):
    """Handle errors with background task logging."""
    if background_tasks:
      BackgroundTaskHelper.add_error_logging_task(
          background_tasks,
          self.mongo_service,
          service_name,
          error_type,
          message,
          details
      )
    else:
      # Immediate logging if no background tasks
      try:
        await self.mongo_service.log_error_to_db(
            service_name=service_name,
            error_type=error_type,
            message=message,
            details=details or {}
        )
      except Exception as log_error:
        logger.error(f"Failed to log error immediately: {log_error}")

  async def store_products(
      self,
      products: List[Dict[str, Any]],
      collection: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store products in MongoDB.

    Args:
        products: List of product data
        collection: MongoDB collection name
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      if not products:
        logfire.warning("No products to store in MongoDB")
        return True

      # Use replace_sheet_collection_data for atomic replacement
      await self.mongo_service.replace_sheet_collection_data(
          collection_name=collection,
          data=products,
          id_field="id"
      )

      logfire.info(
          f"Stored {len(products)} products in MongoDB collection: {collection}")
      return True

    except Exception as e:
      error_msg = f"Failed to store products in {collection}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "MongoStorage.store_products",
          "StoreError",
          error_msg,
          {"collection": collection, "count": len(products)}
      )
      return False

  async def store_generators(
      self,
      generators: List[Dict[str, Any]],
      collection: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store generators in MongoDB.

    Args:
        generators: List of generator data
        collection: MongoDB collection name
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      if not generators:
        logfire.warning("No generators to store in MongoDB")
        return True

      # Use replace_sheet_collection_data for atomic replacement
      await self.mongo_service.replace_sheet_collection_data(
          collection_name=collection,
          data=generators,
          id_field="id"
      )

      logfire.info(
          f"Stored {len(generators)} generators in MongoDB collection: {collection}")
      return True

    except Exception as e:
      error_msg = f"Failed to store generators in {collection}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "MongoStorage.store_generators",
          "StoreError",
          error_msg,
          {"collection": collection, "count": len(generators)}
      )
      return False

  async def store_branches(
      self,
      branches: List[Dict[str, Any]],
      collection: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store branches in MongoDB.

    Args:
        branches: List of branch data
        collection: MongoDB collection name
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      if not branches:
        logfire.warning("No branches to store in MongoDB")
        return True

      # Use replace_sheet_collection_data for atomic replacement
      await self.mongo_service.replace_sheet_collection_data(
          collection_name=collection,
          data=branches,
          id_field="id"
      )

      logfire.info(
          f"Stored {len(branches)} branches in MongoDB collection: {collection}")
      return True

    except Exception as e:
      error_msg = f"Failed to store branches in {collection}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "MongoStorage.store_branches",
          "StoreError",
          error_msg,
          {"collection": collection, "count": len(branches)}
      )
      return False

  async def store_config(
      self,
      config: Dict[str, Any],
      collection: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store configuration in MongoDB.

    Args:
        config: Configuration data
        collection: MongoDB collection name
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      if not config:
        logfire.warning("No config to store in MongoDB")
        return True

      # Use upsert_sheet_config_document for configuration
      await self.mongo_service.upsert_sheet_config_document(
          document_id=f"config_{collection}",
          config_data=config,
          config_type="quote_config"
      )

      logfire.info(f"Stored config in MongoDB collection: {collection}")
      return True

    except Exception as e:
      error_msg = f"Failed to store config in {collection}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "MongoStorage.store_config",
          "StoreError",
          error_msg,
          {"collection": collection}
      )
      return False

  async def get_config(
      self,
      collection: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> Optional[Dict[str, Any]]:
    """
    Retrieve configuration from MongoDB.

    Args:
        collection: MongoDB collection name
        background_tasks: Optional FastAPI background tasks

    Returns:
        Configuration data or None if not found
    """
    try:
      # Access collection directly through the database
      db = await self.mongo_service.get_db()
      collection_obj = db[collection]
      config = await collection_obj.find_one({})

      if config:
        # Remove MongoDB _id field
        config.pop('_id', None)
        logfire.debug(
            f"Retrieved config from MongoDB collection: {collection}")
      return config

    except Exception as e:
      error_msg = f"Failed to retrieve config from {collection}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "MongoStorage.get_config",
          "RetrieveError",
          error_msg,
          {"collection": collection}
      )
      return None

  async def store_states(
      self,
      states: List[Any],
      collection: str,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store states in MongoDB.

    Args:
        states: List of state data
        collection: MongoDB collection name
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      if not states:
        logfire.warning("No states to store in MongoDB")
        return True

      # Convert states to documents if they're just strings
      if states and isinstance(states[0], str):
        state_docs = [{"state": state, "name": state, "id": i}
                      for i, state in enumerate(states)]
      else:
        state_docs = states
        # Ensure each doc has an id field
        for i, doc in enumerate(state_docs):
          if "id" not in doc:
            doc["id"] = i

      await self.mongo_service.replace_sheet_collection_data(
          collection_name=collection,
          data=state_docs,
          id_field="id"
      )

      logfire.info(
          f"Stored {len(states)} states in MongoDB collection: {collection}")
      return True

    except Exception as e:
      error_msg = f"Failed to store states in {collection}: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "MongoStorage.store_states",
          "StoreError",
          error_msg,
          {"collection": collection, "count": len(states)}
      )
      return False

  async def store_pricing_catalog(
      self,
      catalog: Dict[str, Any],
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Store pricing catalog (products and generators) in MongoDB.

    Args:
        catalog: Pricing catalog with 'products' and 'generators' keys
        background_tasks: Optional FastAPI background tasks

    Returns:
        True if successful, False otherwise
    """
    try:
      from app.services.mongo.mongo import (
          SHEET_PRODUCTS_COLLECTION,
          SHEET_GENERATORS_COLLECTION
      )

      success = True

      # Store products
      if catalog.get("products"):
        products_success = await self.store_products(
            catalog["products"],
            SHEET_PRODUCTS_COLLECTION,
            background_tasks
        )
        success = success and products_success

      # Store generators
      if catalog.get("generators"):
        generators_success = await self.store_generators(
            catalog["generators"],
            SHEET_GENERATORS_COLLECTION,
            background_tasks
        )
        success = success and generators_success

      if success:
        logfire.info("Successfully stored pricing catalog in MongoDB")
      else:
        logfire.warning("Partial failure storing pricing catalog in MongoDB")

      return success

    except Exception as e:
      error_msg = f"Failed to store pricing catalog: {str(e)}"
      logfire.error(error_msg)
      await self._handle_error(
          background_tasks,
          "MongoStorage.store_pricing_catalog",
          "StoreError",
          error_msg,
          {"catalog_keys": list(catalog.keys())}
      )
      return False

  # Convenience methods with default collections
  async def store_branches_default(
      self,
      branches: List[Dict[str, Any]],
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """Store branches using the default collection."""
    from app.services.mongo.mongo import SHEET_BRANCHES_COLLECTION
    return await self.store_branches(branches, SHEET_BRANCHES_COLLECTION, background_tasks)

  async def store_states_default(
      self,
      states: List[Any],
      background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """Store states using the default collection."""
    from app.services.mongo.mongo import SHEET_STATES_COLLECTION
    return await self.store_states(states, SHEET_STATES_COLLECTION, background_tasks)
