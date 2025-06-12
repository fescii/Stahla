# filepath: app/services/dash/sync/manager.py
import logging
from datetime import datetime
from typing import Optional, List
from app.services.redis.service import RedisService
from app.services.mongo import MongoService
from app.models.dash.dashboard import SyncStatus

logger = logging.getLogger(__name__)


class SyncManager:
  """Handles synchronization operations for dashboard."""

  def __init__(self, redis_service: RedisService, mongo_service: MongoService):
    self.redis = redis_service
    self.mongo = mongo_service

  @property
  def sync_service(self):
    """Dynamically retrieves the global SheetSyncService instance."""
    from app.services.quote.sync import get_sheet_sync_service
    return None  # For now, return None since we can't await in a property

  async def get_sync_service(self):
    """Async method to get the sheet sync service."""
    from app.services.quote.sync import get_sheet_sync_service
    return await get_sheet_sync_service()

  async def get_sync_status(self) -> SyncStatus:
    """Gets the current synchronization status."""
    last_successful_sync_iso = await self.redis.get("sync:last_successful_timestamp")
    is_sync_running = False
    recent_sync_error_messages = []
    current_sync_service = self.sync_service

    if current_sync_service and current_sync_service._sync_task:
      is_sync_running = not current_sync_service._sync_task.done()

    try:
      # Fetch specific sync-related errors from MongoDB
      sync_error_types = [
          "SheetFetchError_products",
          "SheetFetchError_generators",
          "SheetFetchError_config",
          "SheetFetchError_branches",
          "RedisStoreError",
          "BranchProcessingError",
          "CatalogProcessingError",
          "SyncLoopError",
          "InitialSyncError",
      ]

      sync_errors_reports = await self.mongo.get_recent_reports(
          report_type=sync_error_types, limit=5
      )

      for report in sync_errors_reports:
        msg = report.get("message", "Unknown sync error")
        ts = report.get("timestamp")
        ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)
        recent_sync_error_messages.append(f"{ts_str}: {msg}")

    except Exception as e:
      logger.error(
          f"Failed to fetch recent sync errors from MongoDB: {e}", exc_info=True
      )

    return SyncStatus(
        last_successful_sync_timestamp=last_successful_sync_iso,
        is_sync_task_running=is_sync_running,
        recent_sync_errors=recent_sync_error_messages,
    )

  async def trigger_sheet_sync(self) -> bool:
    """Manually triggers a full sync from Google Sheets."""
    logger.info("Attempting to trigger manual sheet sync.")
    current_sync_service = await self.get_sync_service()

    if current_sync_service:
      logger.info("sync_service instance found.")
      try:
        logger.info("Calling current_sync_service.sync_full_catalog()")
        sync_result = await current_sync_service.sync_full_catalog()
        logger.info(
            f"current_sync_service.sync_full_catalog() returned: {sync_result}"
        )

        # Check if the sync was successful
        success = (
            sync_result.get("branches", {}).get("success", False) and
            sync_result.get("states", {}).get("success", False) and
            sync_result.get("pricing", {}).get("success", False)
        )

        logger.info(f"Manual sync trigger result: {success}")
        return success
      except Exception as e:
        logger.exception(
            "Error during manually triggered sync in current_sync_service.sync_full_catalog()",
            exc_info=e,
        )
        return False
    else:
      logger.error(
          "Cannot trigger manual sync: SheetSyncService instance not available at time of call."
      )
      return False
