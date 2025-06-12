import logging
from typing import Optional

from app.services.mongo import (
    MongoService,
    SHEET_PRODUCTS_COLLECTION,
    SHEET_GENERATORS_COLLECTION,
    SHEET_BRANCHES_COLLECTION,
    SHEET_CONFIG_COLLECTION,
    SHEET_STATES_COLLECTION,
)
from app.models.dash.dashboard import (
    SheetProductsResponse,
    SheetGeneratorsResponse,
    SheetBranchesResponse,
    SheetStatesResponse,
    SheetConfigResponse,
    SheetProductEntry,
    SheetGeneratorEntry,
    SheetConfigEntry,
)

logger = logging.getLogger(__name__)


class DataFetcher:
  """Fetches sheet data from MongoDB collections."""

  def __init__(self, mongo_service: MongoService):
    self.mongo = mongo_service

  async def get_products_data(self) -> SheetProductsResponse:
    """Retrieves all product data from the MongoDB sheet_products collection."""
    logger.info(
        "Fetching all products data from MongoDB sheet_products collection.")
    db = await self.mongo.get_db()
    collection = db[SHEET_PRODUCTS_COLLECTION]
    try:
      cursor = collection.find({})
      raw_products = await cursor.to_list(length=None)
      products = [SheetProductEntry(**p) for p in raw_products]
      logger.info(f"Retrieved {len(products)} products from MongoDB.")
      return SheetProductsResponse(count=len(products), data=products)
    except Exception as e:
      logger.error(f"Error fetching products from MongoDB: {e}", exc_info=True)
      return SheetProductsResponse(count=0, data=[])

  async def get_generators_data(self) -> SheetGeneratorsResponse:
    """Retrieves all generator data from the MongoDB sheet_generators collection."""
    logger.info(
        "Fetching all generators data from MongoDB sheet_generators collection.")
    db = await self.mongo.get_db()
    collection = db[SHEET_GENERATORS_COLLECTION]
    try:
      cursor = collection.find({})
      raw_generators = await cursor.to_list(length=None)
      generators = [SheetGeneratorEntry(**g) for g in raw_generators]
      logger.info(f"Retrieved {len(generators)} generators from MongoDB.")
      return SheetGeneratorsResponse(count=len(generators), data=generators)
    except Exception as e:
      logger.error(
          f"Error fetching generators from MongoDB: {e}", exc_info=True)
      return SheetGeneratorsResponse(count=0, data=[])

  async def get_branches_data(self) -> SheetBranchesResponse:
    """Retrieves all branch data from the MongoDB sheet_branches collection."""
    logger.info(
        "Fetching all branches data from MongoDB sheet_branches collection.")
    db = await self.mongo.get_db()
    collection = db[SHEET_BRANCHES_COLLECTION]
    try:
      cursor = collection.find({})
      raw_branches = await cursor.to_list(length=None)
      logger.info(f"Retrieved {len(raw_branches)} branches from MongoDB.")
      return SheetBranchesResponse(count=len(raw_branches), data=raw_branches)
    except Exception as e:
      logger.error(f"Error fetching branches from MongoDB: {e}", exc_info=True)
      return SheetBranchesResponse(count=0, data=[])

  async def get_config_data(self) -> SheetConfigResponse:
    """Retrieves the main configuration document from the MongoDB sheet_config collection."""
    logger.info(
        "Fetching master configuration from MongoDB sheet_config collection.")
    db = await self.mongo.get_db()
    collection = db[SHEET_CONFIG_COLLECTION]
    try:
      config_doc = await collection.find_one({"_id": "master_config"})
      if config_doc:
        parsed_config = SheetConfigEntry(**config_doc)
        logger.info(
            f"Retrieved master configuration from MongoDB: {parsed_config.id}")
        return SheetConfigResponse(data=parsed_config)
      else:
        logger.warning("Master configuration document not found in MongoDB.")
        return SheetConfigResponse(
            data=None, message="Master configuration not found."
        )
    except Exception as e:
      logger.error(
          f"Error fetching master configuration from MongoDB: {e}", exc_info=True)
      return SheetConfigResponse(
          data=None, message=f"Error fetching configuration: {str(e)}"
      )

  async def get_states_data(self) -> SheetStatesResponse:
    """Retrieves all states data from the MongoDB sheet_states collection."""
    logger.info(
        "Fetching all states data from MongoDB sheet_states collection.")
    db = await self.mongo.get_db()
    collection = db[SHEET_STATES_COLLECTION]
    try:
      cursor = collection.find({})
      raw_states = await cursor.to_list(length=None)
      logger.info(f"Retrieved {len(raw_states)} states from MongoDB.")
      return SheetStatesResponse(count=len(raw_states), data=raw_states)
    except Exception as e:
      logger.error(f"Error fetching states from MongoDB: {e}", exc_info=True)
      return SheetStatesResponse(count=0, data=[])
