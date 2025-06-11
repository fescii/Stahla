# app/services/quote/quote/builder/catalog/loader.py

"""
Catalog loading functionality for quote building.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CatalogLoader:
  """Handles loading pricing catalogs for quote building."""

  def __init__(self, manager):
    self.manager = manager

  async def load_catalog(self) -> Dict[str, Any]:
    """
    Load pricing catalog from Redis cache or fallback to MongoDB.

    Returns:
        Pricing catalog dictionary

    Raises:
        ValueError: If catalog cannot be loaded
    """
    # Try to get catalog from cache first
    catalog = await self.manager.catalog.get_pricing_catalog()

    if catalog:
      return catalog

    # Fallback to MongoDB config if Redis cache fails
    logger.warning(
        "Pricing catalog not found in Redis, attempting to load config from MongoDB."
    )

    config_doc = await self.manager.catalog.get_config_from_mongo()

    if config_doc:
      logger.info(
          "Config loaded from MongoDB, but pricing catalog is empty. Please check catalog sync."
      )
      raise ValueError(
          "Pricing catalog is empty. Please check catalog sync."
      )
    else:
      logger.error(
          "Failed to load pricing catalog from Redis and MongoDB. Request cannot be processed."
      )
      raise ValueError(
          "Pricing data is currently unavailable. Please try again later."
      )
