# app/services/quote/pricing/catalog/retriever.py

"""
Catalog retrieval operations for managing pricing catalogs.
"""

import logging
from typing import Any, Dict, Optional

from app.core.keys import (
    PRICING_CATALOG_CACHE_KEY,
    PRICING_CACHE_HITS_KEY,
    PRICING_CACHE_MISSES_KEY,
)
from app.services.dash.background import increment_request_counter_bg

logger = logging.getLogger(__name__)


class CatalogRetriever:
  """Handles catalog retrieval operations."""

  def __init__(self, manager):
    self.manager = manager

  async def get_pricing_catalog(self) -> Optional[Dict[str, Any]]:
    """
    Retrieves the pricing catalog from Redis cache.
    If not found or on error, attempts to retrieve from MongoDB as a fallback.
    """
    try:
      catalog = await self.manager.redis_service.get_json(PRICING_CATALOG_CACHE_KEY)

      if catalog:
        logger.debug(
            f"Pricing catalog found in Redis cache ('{PRICING_CATALOG_CACHE_KEY}')."
        )
        await increment_request_counter_bg(
            self.manager.redis_service, PRICING_CACHE_HITS_KEY
        )
        return catalog
      else:
        logger.warning(
            f"Pricing catalog NOT FOUND in Redis cache ('{PRICING_CATALOG_CACHE_KEY}'). Attempting MongoDB fallback."
        )
        await increment_request_counter_bg(
            self.manager.redis_service, PRICING_CACHE_MISSES_KEY
        )
        # Log to MongoDB
        await self.manager.mongo_service.log_error_to_db(
            service_name="CatalogRetriever.get_pricing_catalog",
            error_type="CacheMiss",
            message=f"Pricing catalog not found in Redis cache (key: '{PRICING_CATALOG_CACHE_KEY}'). Trying MongoDB fallback.",
            details={"cache_key": PRICING_CATALOG_CACHE_KEY},
        )

        # Attempt MongoDB fallback
        return await self.build_catalog_from_mongo()

    except Exception as e:
      logger.error(
          f"Error retrieving pricing catalog: {e}. Attempting MongoDB fallback."
      )
      await self.manager.mongo_service.log_error_to_db(
          service_name="CatalogRetriever.get_pricing_catalog",
          error_type="CatalogRetrievalError",
          message=f"Exception during catalog retrieval: {str(e)}",
          details={"error": str(e), "cache_key": PRICING_CATALOG_CACHE_KEY},
      )
      # Attempt MongoDB fallback
      return await self.build_catalog_from_mongo()

  async def get_config_from_mongo(self) -> Optional[Dict[str, Any]]:
    """Get configuration from MongoDB."""
    try:
      from app.services.quote.utils.helpers import SHEET_CONFIG_COLLECTION

      config_docs = await self.manager.mongo_service.find_all(SHEET_CONFIG_COLLECTION)
      if config_docs:
        # Convert list of documents to dictionary
        config = {}
        for doc in config_docs:
          # Remove MongoDB's _id field
          if "_id" in doc:
            del doc["_id"]
          config.update(doc)
        return config
      return None
    except Exception as e:
      logger.error(f"Error retrieving config from MongoDB: {e}")
      await self.manager.mongo_service.log_error_to_db(
          service_name="CatalogRetriever.get_config_from_mongo",
          error_type="MongoConfigError",
          message=f"Failed to retrieve config from MongoDB: {str(e)}",
          details={"error": str(e)},
      )
      return None

  async def build_catalog_from_mongo(self) -> Optional[Dict[str, Any]]:
    """Build catalog from MongoDB collections."""
    try:
      from app.services.quote.utils.helpers import (
          SHEET_PRODUCTS_COLLECTION,
          SHEET_GENERATORS_COLLECTION,
          SHEET_CONFIG_COLLECTION,
      )

      # Fetch all collections
      products = await self.manager.mongo_service.find_all(SHEET_PRODUCTS_COLLECTION)
      generators = await self.manager.mongo_service.find_all(SHEET_GENERATORS_COLLECTION)
      config = await self.manager.mongo_service.find_all(SHEET_CONFIG_COLLECTION)

      if not products or not generators or not config:
        logger.warning(
            "One or more MongoDB collections are empty. Cannot build catalog."
        )
        return None

      # Build catalog structure
      catalog = {
          "products": {},
          "generators": {},
          "delivery_costs": {},
          "seasonal_multipliers": {},
          "config": {},
      }

      # Process products
      for product in products:
        if "_id" in product:
          del product["_id"]
        product_id = product.get("product_id")
        if product_id:
          catalog["products"][product_id] = product

      # Process generators
      for generator in generators:
        if "_id" in generator:
          del generator["_id"]
        generator_id = generator.get("generator_id")
        if generator_id:
          catalog["generators"][generator_id] = generator

      # Process config
      for config_item in config:
        if "_id" in config_item:
          del config_item["_id"]
        catalog["config"].update(config_item)

      # Extract delivery costs and seasonal info from config
      # Store delivery configuration in multiple places to ensure compatibility
      if "delivery_costs" in catalog["config"]:
        catalog["delivery_costs"] = catalog["config"]["delivery_costs"]
        # Add duplicate key for compatibility
        catalog["delivery"] = catalog["config"]["delivery_costs"]
      elif "delivery" in catalog["config"]:
        catalog["delivery"] = catalog["config"]["delivery"]
        # Add duplicate key for compatibility
        catalog["delivery_costs"] = catalog["config"]["delivery"]

      if "seasonal_multipliers" in catalog["config"]:
        catalog["seasonal_multipliers"] = catalog["config"]["seasonal_multipliers"]

      logger.info("Successfully built catalog from MongoDB collections")
      return catalog

    except Exception as e:
      logger.error(f"Error building catalog from MongoDB: {e}")
      await self.manager.mongo_service.log_error_to_db(
          service_name="CatalogRetriever.build_catalog_from_mongo",
          error_type="CatalogBuildError",
          message=f"Failed to build catalog from MongoDB: {str(e)}",
          details={"error": str(e)},
      )
      return None

  async def get_config_for_quoting(self) -> Dict[str, Any]:
    """Get configuration for quoting."""
    catalog = await self.get_pricing_catalog()
    if catalog and "config" in catalog:
      return catalog["config"]

    # Fallback to direct MongoDB config fetch
    config = await self.get_config_from_mongo()
    return config or {}

  async def sync_catalog_to_redis(self) -> bool:
    """
    Synchronize the catalog from MongoDB to Redis cache.
    This can be called periodically or when catalog data is updated.

    Returns:
        bool: True if sync succeeded, False otherwise
    """
    try:
      # Build catalog from MongoDB
      catalog = await self.build_catalog_from_mongo()

      if not catalog:
        logger.error("Failed to build catalog from MongoDB for sync")
        return False

      # Store in Redis
      from app.core.keys import PRICING_CATALOG_CACHE_KEY

      await self.manager.redis_service.set_json(
          PRICING_CATALOG_CACHE_KEY,
          catalog,
          expiration=86400 * 7  # 7 days expiration
      )

      logger.info(
          f"Successfully synchronized catalog from MongoDB to Redis cache")
      # Record sync timestamp
      await self.manager.redis_service.set_value(
          "catalog_last_sync",
          f"{__import__('datetime').datetime.now().isoformat()}"
      )

      return True

    except Exception as e:
      logger.error(f"Error synchronizing catalog from MongoDB to Redis: {e}")
      await self.manager.mongo_service.log_error_to_db(
          service_name="CatalogRetriever.sync_catalog_to_redis",
          error_type="SyncError",
          message=f"Failed to sync catalog from MongoDB to Redis: {str(e)}",
          details={"error": str(e)},
      )
      return False
