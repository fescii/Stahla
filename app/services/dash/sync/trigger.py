import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SyncTrigger:
  """Handles manual sync triggering operations."""

  async def trigger_sheet_sync(self) -> bool:
    """Manually triggers a full sync from Google Sheets."""
    logger.info("Attempting to trigger manual sheet sync.")

    try:
      from app.services.quote.sync import get_sheet_sync_service
      sync_service = await get_sheet_sync_service()

      if sync_service:
        logger.info("sync_service instance found.")
        try:
          logger.info("Calling sync_service.sync_full_catalog()")
          sync_result = await sync_service.sync_full_catalog()
          logger.info(
              f"sync_service.sync_full_catalog() returned: {sync_result}")

          # Check if the sync was successful (all 3 components: branches, states, pricing)
          success = (
              sync_result.get("branches", {}).get("success", False) and
              sync_result.get("states", {}).get("success", False) and
              sync_result.get("pricing", {}).get("success", False)
          )

          logger.info(f"Manual sync trigger result: {success}")
          return success
        except Exception as e:
          logger.exception(
              "Error during manually triggered sync in sync_service.sync_full_catalog()",
              exc_info=e,
          )
          return False
      else:
        logger.error(
            "Cannot trigger manual sync: SheetSyncService instance not available at time of call."
        )
        return False
    except ImportError as e:
      logger.error(f"Could not import sync service: {e}")
      return False
