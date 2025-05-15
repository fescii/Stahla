import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
from redis.exceptions import RedisError

from app.services.bland import BlandAIManager
from app.services.hubspot import hubspot_manager
from app.services.mongo.mongo import MongoService
from app.services.redis.redis import RedisService
from app.services.quote.sync import SheetSyncService

# Constants
SERVICE_STATUS_COLLECTION = "service_status"
CHECK_INTERVAL_HOURS = 12  # Run every 12 hours
INITIAL_DELAY_SECONDS = 60  # Wait 60 seconds after startup before first check
STATUS_TTL_DAYS = 7  # Keep status records for 7 days

logger = logging.getLogger(__name__)


class ServiceStatusMonitor:
  """
  A background service that periodically checks the status of external services
  and stores the results in MongoDB for dashboard retrieval.
  """

  def __init__(
      self,
      mongo_service: MongoService,
      redis_service: RedisService,
      bland_ai_manager: BlandAIManager,
      sheet_sync_service: Optional[SheetSyncService] = None,
  ):
    self.mongo_service = mongo_service
    self.redis_service = redis_service
    self.bland_ai_manager = bland_ai_manager
    self.sheet_sync_service = sheet_sync_service
    self.running = False
    self.task = None

  async def start_monitoring(self):
    """Start the periodic monitoring service."""
    if self.running:
      logger.warning("Service status monitoring is already running.")
      return

    self.running = True
    self.task = asyncio.create_task(self._monitoring_loop())
    logger.info("Started service status monitoring background task.")

  async def stop_monitoring(self):
    """Stop the periodic monitoring service."""
    if not self.running:
      logger.warning("Service status monitoring is not running.")
      return

    self.running = False
    if self.task:
      self.task.cancel()
      try:
        await self.task
      except asyncio.CancelledError:
        logger.info("Service status monitoring task was cancelled.")
      self.task = None
    logger.info("Stopped service status monitoring background task.")

  async def _monitoring_loop(self):
    """Main loop that runs checks periodically."""
    try:
      # Initial delay to allow system to start up properly
      await asyncio.sleep(INITIAL_DELAY_SECONDS)

      while self.running:
        logger.info("Running periodic service status checks...")
        try:
          await self.check_all_services()
          logger.info("Service status checks completed successfully.")
        except Exception as e:
          logger.error(
              f"Error during service status checks: {e}", exc_info=True
          )

        # Wait for next check interval
        check_interval_seconds = CHECK_INTERVAL_HOURS * 3600
        logger.info(
            f"Next service status check in {CHECK_INTERVAL_HOURS} hours."
        )
        await asyncio.sleep(check_interval_seconds)

    except asyncio.CancelledError:
      logger.info("Service status monitoring loop cancelled.")
      raise
    except Exception as e:
      logger.error(
          f"Unexpected error in service status monitoring loop: {e}",
          exc_info=True,
      )
      self.running = False
      raise

  async def check_all_services(self):
    """Check all external services and store results in MongoDB."""
    timestamp = datetime.now()

    # Perform checks concurrently
    services_to_check = [
        self._check_mongodb_status(),
        self._check_redis_status(),
        self._check_hubspot_status(),
        self._check_blandai_status(),
        self._check_sheets_status(),
    ]

    results = await asyncio.gather(*services_to_check, return_exceptions=True)

    service_statuses = []
    for result in results:
      if isinstance(result, Exception):
        logger.error(f"Error during service check: {result}", exc_info=True)
        continue

      if result:  # If result is not None
        service_name, status_data = result
        service_status = {
            "service_name": service_name,
            "timestamp": timestamp,
            "status": status_data.get("status", "unknown"),
            "details": (
                status_data.get("details", {})
                if isinstance(status_data.get("details"), dict)
                else {}
            ),
            "message": status_data.get("message", ""),
        }
        service_statuses.append(service_status)

    # Store results in MongoDB
    await self._store_service_statuses(service_statuses)

    # Clean up old status records
    await self._cleanup_old_records()

    return service_statuses

  async def _check_mongodb_status(self) -> Tuple[str, Dict[str, Any]]:
    """Check MongoDB connection status."""
    service_name = "mongodb"
    try:
      status_str = await self.mongo_service.check_connection()
      if status_str.startswith("ok"):
        return service_name, {
            "status": "ok",
            "message": "MongoDB connection successful",
            "details": {},
        }
      else:
        error_message = (
            status_str.split("error: ", 1)[1]
            if "error: " in status_str
            else status_str
        )
        return service_name, {
            "status": "error",
            "message": error_message,
            "details": {},
        }
    except Exception as e:
      logger.error(f"Error checking MongoDB status: {e}", exc_info=True)
      return service_name, {"status": "error", "message": str(e), "details": {}}

  async def _check_redis_status(self) -> Tuple[str, Dict[str, Any]]:
    """Check Redis connection status."""
    service_name = "redis"
    redis_client = None
    try:
      redis_client = await self.redis_service.get_client()
      await redis_client.ping()
      return service_name, {
          "status": "ok",
          "message": "Redis connection successful",
          "details": {},
      }
    except RedisError as e:
      return service_name, {
          "status": "error",
          "message": f"RedisError: {str(e)}",
          "details": {},
      }
    except Exception as e:
      logger.error(f"Error checking Redis status: {e}", exc_info=True)
      return service_name, {"status": "error", "message": str(e), "details": {}}
    finally:
      if redis_client:
        try:
          await redis_client.close()
        except Exception as e_close:
          logger.error(
              f"Error closing Redis client: {str(e_close)}", exc_info=True
          )

  async def _check_hubspot_status(self) -> Tuple[str, Dict[str, Any]]:
    """Check HubSpot connection status."""
    service_name = "hubspot"
    try:
      hubspot_status_str = await hubspot_manager.check_connection()
      if hubspot_status_str.startswith("ok"):
        return service_name, {
            "status": "ok",
            "message": "HubSpot connection successful",
            "details": {},
        }
      else:
        error_message = (
            hubspot_status_str.split("error: ", 1)[1]
            if "error: " in hubspot_status_str
            else hubspot_status_str
        )
        return service_name, {
            "status": "error",
            "message": error_message,
            "details": {},
        }
    except Exception as e:
      logger.error(f"Error checking HubSpot status: {e}", exc_info=True)
      return service_name, {"status": "error", "message": str(e), "details": {}}

  async def _check_blandai_status(self) -> Tuple[str, Dict[str, Any]]:
    """Check BlandAI connection status."""
    service_name = "bland_ai"
    try:
      bland_status_dict = await self.bland_ai_manager.check_connection()
      if (
          isinstance(bland_status_dict, dict)
          and bland_status_dict.get("status") == "success"
      ):
        return service_name, {
            "status": "ok",
            "message": bland_status_dict.get(
                "message", "BlandAI connection successful"
            ),
            "details": bland_status_dict.get("details", {}),
        }
      elif isinstance(bland_status_dict, dict):
        return service_name, {
            "status": "error",
            "message": bland_status_dict.get(
                "message", "Unknown error from Bland AI check"
            ),
            "details": bland_status_dict.get("details", {}),
        }
      else:
        return service_name, {
            "status": "error",
            "message": "BlandAI check returned unexpected response type",
        }
    except Exception as e:
      logger.error(f"Error checking BlandAI status: {e}", exc_info=True)
      return service_name, {"status": "error", "message": str(e), "details": {}}

  async def _check_sheets_status(self) -> Tuple[str, Dict[str, Any]]:
    """Check Google Sheets API connection status."""
    service_name = "google_sheets"
    if not self.sheet_sync_service:
      return service_name, {
          "status": "unknown",
          "message": "SheetSyncService instance not available",
          "details": {},
      }

    try:
      if self.sheet_sync_service.sheet_service:
        # Simple check to see if the service is initialized
        return service_name, {
            "status": "ok",
            "message": "Google Sheets API client initialized",
            "details": {},
        }
      else:
        return service_name, {
            "status": "error",
            "message": "Google Sheets API client NOT initialized",
            "details": {},
        }
    except Exception as e:
      logger.error(f"Error checking Google Sheets status: {e}", exc_info=True)
      return service_name, {"status": "error", "message": str(e), "details": {}}

  async def _store_service_statuses(self, service_statuses: List[Dict[str, Any]]):
    """Store service status data in MongoDB."""
    if not service_statuses:
      logger.warning("No service statuses to store in MongoDB.")
      return

    # Ensure each status record has a proper details field that's a dictionary
    for status in service_statuses:
      if "details" not in status:
        status["details"] = {}
      elif not isinstance(status["details"], dict):
        status["details"] = {}

    db = await self.mongo_service.get_db()
    collection = db[SERVICE_STATUS_COLLECTION]

    try:
      result = await collection.insert_many(service_statuses)
      logger.info(
          f"Stored {len(result.inserted_ids)} service status records in MongoDB."
      )
    except Exception as e:
      logger.error(
          f"Failed to store service statuses in MongoDB: {e}", exc_info=True
      )

  async def _cleanup_old_records(self):
    """Remove old status records to prevent excessive storage usage."""
    cutoff_date = datetime.now() - timedelta(days=STATUS_TTL_DAYS)

    db = await self.mongo_service.get_db()
    collection = db[SERVICE_STATUS_COLLECTION]

    try:
      delete_result = await collection.delete_many(
          {"timestamp": {"$lt": cutoff_date}}
      )
      if delete_result.deleted_count > 0:
        logger.info(
            f"Cleaned up {delete_result.deleted_count} old service status records."
        )
    except Exception as e:
      logger.error(
          f"Failed to clean up old service status records: {e}", exc_info=True
      )

  async def get_latest_service_statuses(self) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve the latest status for each service from MongoDB.
    Returns a dictionary with service names as keys and their status data as values.
    """
    db = await self.mongo_service.get_db()
    collection = db[SERVICE_STATUS_COLLECTION]

    latest_statuses = {}

    try:
      # Get all unique service names
      service_names = await collection.distinct("service_name")

      for service_name in service_names:
        # Get the latest record for each service
        latest_record = await collection.find_one(
            {"service_name": service_name}, sort=[("timestamp", -1)]
        )

        if latest_record:
          # Convert ObjectId to string for JSON serialization
          latest_record["_id"] = str(latest_record["_id"])
          latest_statuses[service_name] = latest_record

      return latest_statuses

    except Exception as e:
      logger.error(
          f"Failed to retrieve latest service statuses: {e}", exc_info=True
      )
      return {}


# Global instance
service_status_monitor: Optional[ServiceStatusMonitor] = None


async def initialize_service_monitor(
    mongo_service: MongoService,
    redis_service: RedisService,
    bland_ai_manager: BlandAIManager,
    sheet_sync_service: Optional[SheetSyncService] = None,
):
  """Initialize the service status monitor."""
  global service_status_monitor

  if service_status_monitor is None:
    service_status_monitor = ServiceStatusMonitor(
        mongo_service=mongo_service,
        redis_service=redis_service,
        bland_ai_manager=bland_ai_manager,
        sheet_sync_service=sheet_sync_service,
    )
    await service_status_monitor.start_monitoring()
    logger.info("Service status monitor initialized and started.")
  else:
    logger.warning("Service status monitor already initialized.")


async def shutdown_service_monitor():
  """Shutdown the service status monitor."""
  global service_status_monitor

  if service_status_monitor:
    await service_status_monitor.stop_monitoring()
    service_status_monitor = None
    logger.info("Service status monitor stopped and cleaned up.")
  else:
    logger.warning("Service status monitor was not running.")
