import logging
from typing import List, Dict, Any

from app.services.mongo import MongoService

logger = logging.getLogger(__name__)


class StatusFetcher:
  """Fetches service status information from MongoDB."""

  def __init__(self, mongo_service: MongoService):
    self.mongo = mongo_service

  async def get_service_statuses(self) -> List[Dict[str, Any]]:
    """
    Retrieves the latest service status records from MongoDB.
    This data is collected by the background service monitor.
    """
    logger.info("Fetching latest service statuses from MongoDB.")

    try:
      # Import the constant from background_check.py
      from app.services.dash.health.checker import SERVICE_STATUS_COLLECTION

      db = await self.mongo.get_db()
      collection = db[SERVICE_STATUS_COLLECTION]

      # Get all unique service names
      service_names = await collection.distinct("service_name")

      if not service_names:
        logger.warning(
            "No service names found in the service_status collection.")
        return []

      latest_statuses = []

      for service_name in service_names:
        # Get the latest record for each service
        latest_record = await collection.find_one(
            {"service_name": service_name}, sort=[("timestamp", -1)]
        )

        if latest_record:
          # Convert ObjectId to string for JSON serialization
          if "_id" in latest_record:
            latest_record["_id"] = str(latest_record["_id"])

          # Ensure details is always a dictionary
          if "details" not in latest_record:
            latest_record["details"] = {}
          elif not isinstance(latest_record["details"], dict):
            latest_record["details"] = {}

          latest_statuses.append(latest_record)

      logger.info(
          f"Retrieved {len(latest_statuses)} service status records from MongoDB.")
      return latest_statuses

    except Exception as e:
      logger.error(
          f"Failed to retrieve service statuses from MongoDB: {e}", exc_info=True)
      return []
