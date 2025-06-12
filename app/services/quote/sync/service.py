# app/services/quote/sync/service.py

"""
Comprehensive Sheet Sync Service - combines all sync functionality from the original sync.py
"""

import asyncio
import logging
import re
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

import logfire
from fastapi import BackgroundTasks

from app.core.config import settings
from app.services.redis.redis import RedisService, get_redis_service
from app.services.mongo import (
    MongoService,
    get_mongo_service,
    SHEET_PRODUCTS_COLLECTION,
    SHEET_GENERATORS_COLLECTION,
    SHEET_BRANCHES_COLLECTION,
    SHEET_CONFIG_COLLECTION,
    SHEET_STATES_COLLECTION,
)
from app.models.location import BranchLocation
from app.services.dash.background import log_error_bg

# Import modular components
from .sheets.service import SheetsService
from .parsers.branches import BranchParser
from .parsers.states import StatesParser
from .parsers.pricing import PricingParser
from .storage.redis import RedisStorage
from .storage.mongo import MongoStorage
from app.core.cachekeys import (
    PRICING_CATALOG_CACHE_KEY,
    BRANCH_LIST_CACHE_KEY,
    STATES_LIST_CACHE_KEY,
)
from ..utils.constants import (
    SYNC_INTERVAL_SECONDS,
    PRODUCT_HEADER_MAP,
    GENERATOR_HEADER_MAP,
    KNOWN_PRODUCT_EXTRAS_HEADERS,
)

logger = logging.getLogger(__name__)


# Helper function
def _clean_currency(value: Any) -> Optional[float]:
  """Clean currency strings and return float."""
  if value is None:
    return None
  if isinstance(value, (int, float)):
    return float(value)
  if isinstance(value, str):
    normalized_value = value.strip().lower()
    if normalized_value == "n/a" or not normalized_value:
      return None
    # Remove currency symbols and extra spaces
    cleaned = re.sub(r'[$,\s]', '', normalized_value)
    try:
      return float(cleaned)
    except ValueError:
      return None
  return None


class SheetSyncService:
  """
  Complete Sheet Sync Service that handles all Google Sheets synchronization.
  Combines functionality from the original sync.py with new modular architecture.
  """

  def __init__(self):
    self.sheets_service = SheetsService()
    self.branch_parser = BranchParser()
    self.state_parser = StatesParser()
    self.pricing_parser = PricingParser()

    # Storage services - will be initialized later
    self.redis_storage: Optional[RedisStorage] = None
    self.mongo_storage: Optional[MongoStorage] = None

    # Background sync state
    self._sync_task: Optional[asyncio.Task] = None
    self._stop_sync = asyncio.Event()

    # Service instances
    self.redis_service: Optional[RedisService] = None
    self.mongo_service: Optional[MongoService] = None

  async def initialize(self):
    """Initialize all services and dependencies."""
    try:
      await self.sheets_service.initialize_service()
      self.redis_service = await get_redis_service()
      self.mongo_service = await get_mongo_service()

      # Initialize storage services with the required service instances
      self.redis_storage = RedisStorage(self.redis_service)
      self.mongo_storage = MongoStorage(self.mongo_service)

      logfire.info("SheetSyncService initialized successfully")
    except Exception as e:
      logfire.error(f"Failed to initialize SheetSyncService: {e}")
      raise

  async def start_background_sync(self):
    """Start the background sync task."""
    if self._sync_task and not self._sync_task.done():
      logfire.info("Background sync already running")
      return

    try:
      self._stop_sync.clear()
      self._sync_task = asyncio.create_task(self._run_sync_loop())
      logfire.info("Background sync started")
    except Exception as e:
      logfire.error(f"Failed to start background sync: {e}")
      raise

  async def _run_sync_loop(self):
    """Main sync loop that runs continuously."""
    logfire.info("Starting continuous sync loop")

    try:
      while not self._stop_sync.is_set():
        try:
          logfire.info("Running scheduled full catalog sync")
          await self.sync_full_catalog()
          logfire.info("Scheduled sync completed successfully")

        except Exception as e:
          logfire.error(f"Error in sync loop: {e}")
          # Continue the loop even if sync fails

        # Wait for the next sync or stop signal
        try:
          await asyncio.wait_for(
              self._stop_sync.wait(),
              timeout=SYNC_INTERVAL_SECONDS
          )
          break  # Stop signal received
        except asyncio.TimeoutError:
          continue  # Timeout reached, run next sync

    except asyncio.CancelledError:
      logfire.info("Sync loop was cancelled")
      raise
    except Exception as e:
      logfire.error(f"Unexpected error in sync loop: {e}")
      raise
    finally:
      logfire.info("Sync loop ended")

  async def stop_background_sync(self):
    """Stop the background sync task."""
    if self._sync_task:
      self._stop_sync.set()

      try:
        await asyncio.wait_for(self._sync_task, timeout=10.0)
        logfire.info("Background sync stopped gracefully")
      except asyncio.TimeoutError:
        logfire.warning("Background sync did not stop gracefully, cancelling")
        self._sync_task.cancel()
        try:
          await self._sync_task
        except asyncio.CancelledError:
          pass
      except Exception as e:
        logfire.error(f"Error stopping background sync: {e}")

      self._sync_task = None

  async def sync_full_catalog(
      self,
      background_tasks: Optional[BackgroundTasks] = None,
      force_refresh: bool = False
  ) -> Dict[str, Any]:
    """
    Perform a full catalog sync of all data from Google Sheets.

    Args:
        background_tasks: Optional FastAPI BackgroundTasks for async processing
        force_refresh: Whether to force refresh regardless of cache

    Returns:
        Dictionary with sync results and statistics
    """
    sync_start_time = datetime.now(timezone.utc)
    results = {
        "sync_start": sync_start_time.isoformat(),
        "branches": {"success": False, "count": 0, "error": None},
        "states": {"success": False, "count": 0, "error": None},
        "pricing": {"success": False, "count": 0, "error": None},
        "total_duration_seconds": 0,
    }

    logfire.info("Starting full catalog sync", force_refresh=force_refresh)

    try:
      # Initialize services if not already done
      if not self.redis_service or not self.mongo_service:
        await self.initialize()

      # Sync branches
      try:
        branch_result = await self._sync_branches_to_storage(
            background_tasks=background_tasks,
            force_refresh=force_refresh
        )
        results["branches"] = branch_result
        logfire.info(f"Branches sync completed: {branch_result}")
      except Exception as e:
        error_msg = f"Failed to sync branches: {e}"
        logfire.error(error_msg)
        results["branches"]["error"] = error_msg
        if background_tasks and self.redis_service:
          background_tasks.add_task(
              log_error_bg, self.redis_service, "sync_branches", str(e)
          )

      # Sync states
      try:
        states_result = await self._sync_states_to_storage(
            background_tasks=background_tasks,
            force_refresh=force_refresh
        )
        results["states"] = states_result
        logfire.info(f"States sync completed: {states_result}")
      except Exception as e:
        error_msg = f"Failed to sync states: {e}"
        logfire.error(error_msg)
        results["states"]["error"] = error_msg
        if background_tasks and self.redis_service:
          background_tasks.add_task(
              log_error_bg, self.redis_service, "sync_states", str(e)
          )

      # Sync pricing catalog
      try:
        pricing_result = await self._sync_pricing_to_storage(
            background_tasks=background_tasks,
            force_refresh=force_refresh
        )
        results["pricing"] = pricing_result
        logfire.info(f"Pricing sync completed: {pricing_result}")
      except Exception as e:
        error_msg = f"Failed to sync pricing: {e}"
        logfire.error(error_msg)
        results["pricing"]["error"] = error_msg
        if background_tasks and self.redis_service:
          background_tasks.add_task(
              log_error_bg, self.redis_service, "sync_pricing", str(e)
          )

      # Calculate total duration
      sync_end_time = datetime.now(timezone.utc)
      total_duration = (sync_end_time - sync_start_time).total_seconds()
      results["total_duration_seconds"] = total_duration
      results["sync_end"] = sync_end_time.isoformat()

      # Log final results
      success_count = sum(1 for r in [
                          results["branches"], results["states"], results["pricing"]] if r["success"])
      logfire.info(
          f"Full catalog sync completed: {success_count}/3 successful",
          results=results,
          duration_seconds=total_duration
      )

      return results

    except Exception as e:
      error_msg = f"Critical failure in full catalog sync: {e}"
      logfire.error(error_msg)
      results["critical_error"] = error_msg

      if background_tasks and self.redis_service:
        background_tasks.add_task(
            log_error_bg, self.redis_service, "sync_full_catalog", str(e)
        )

      return results

  async def _sync_branches_to_storage(
      self,
      background_tasks: Optional[BackgroundTasks] = None,
      force_refresh: bool = False
  ) -> Dict[str, Any]:
    """Sync branches data to Redis and MongoDB."""
    result = {"success": False, "count": 0, "error": None}

    try:
      # Initialize services if not already done
      if not self.redis_service or not self.mongo_service or not self.redis_storage or not self.mongo_storage:
        await self.initialize()

      # Check cache first unless force refresh
      if not force_refresh and self.redis_storage:
        cached_branches = await self.redis_storage.get_branches_default()
        if cached_branches:
          logfire.info(
              f"Using cached branches data: {len(cached_branches)} branches")
          result["success"] = True
          result["count"] = len(cached_branches)
          result["source"] = "cache"
          return result

      # Fetch from Google Sheets
      logfire.info("Fetching branches from Google Sheets")
      sheet_data = await self.sheets_service.fetch_sheet_data(
          settings.GOOGLE_SHEET_ID,
          settings.GOOGLE_SHEET_BRANCHES_RANGE
      )

      if not sheet_data:
        raise ValueError("No branches data received from Google Sheets")

      # Parse branches
      branches = self.branch_parser.parse_branches(sheet_data)

      if not branches:
        raise ValueError("No valid branches parsed from sheet data")

      # Store in Redis
      if self.redis_storage:
        await self.redis_storage.store_branches_default(branches)

      # Store in MongoDB
      if self.mongo_storage:
        await self.mongo_storage.store_branches_default(branches)

      result["success"] = True
      result["count"] = len(branches)
      result["source"] = "sheets"

      logfire.info(f"Successfully synced {len(branches)} branches to storage")

      return result

    except Exception as e:
      error_msg = f"Failed to sync branches: {e}"
      logfire.error(error_msg)
      result["error"] = error_msg

      if background_tasks and self.redis_service:
        background_tasks.add_task(
            log_error_bg, self.redis_service, "sync_branches_to_storage", str(
                e)
        )

      return result

  async def _sync_states_to_storage(
      self,
      background_tasks: Optional[BackgroundTasks] = None,
      force_refresh: bool = False
  ) -> Dict[str, Any]:
    """Sync states data to Redis and MongoDB."""
    result = {"success": False, "count": 0, "error": None}

    try:
      # Initialize services if not already done
      if not self.redis_service or not self.mongo_service or not self.redis_storage or not self.mongo_storage:
        await self.initialize()

      # Check cache first unless force refresh
      if not force_refresh and self.redis_storage:
        cached_states = await self.redis_storage.get_states_default()
        if cached_states:
          logfire.info(
              f"Using cached states data: {len(cached_states)} states")
          result["success"] = True
          result["count"] = len(cached_states)
          result["source"] = "cache"
          return result

      # Fetch from Google Sheets
      logfire.info("Fetching states from Google Sheets")
      sheet_data = await self.sheets_service.fetch_sheet_data(
          settings.GOOGLE_SHEET_ID,
          settings.GOOGLE_SHEET_STATES_RANGE
      )

      if not sheet_data:
        raise ValueError("No states data received from Google Sheets")

      # Parse states
      states = self.state_parser.parse_states(sheet_data)

      if not states:
        raise ValueError("No valid states parsed from sheet data")

      # Store in Redis
      if self.redis_storage:
        await self.redis_storage.store_states_default(states)

      # Store in MongoDB
      if self.mongo_storage:
        await self.mongo_storage.store_states_default(states)

      result["success"] = True
      result["count"] = len(states)
      result["source"] = "sheets"

      logfire.info(f"Successfully synced {len(states)} states to storage")

      return result

    except Exception as e:
      error_msg = f"Failed to sync states: {e}"
      logfire.error(error_msg)
      result["error"] = error_msg

      if background_tasks and self.redis_service:
        background_tasks.add_task(
            log_error_bg, self.redis_service, "sync_states_to_storage", str(e)
        )

      return result

  async def _sync_pricing_to_storage(
      self,
      background_tasks: Optional[BackgroundTasks] = None,
      force_refresh: bool = False
  ) -> Dict[str, Any]:
    """Sync pricing catalog to Redis and MongoDB."""
    result = {"success": False, "count": 0, "error": None}

    try:
      # Initialize services if not already done
      if not self.redis_service or not self.mongo_service or not self.redis_storage or not self.mongo_storage:
        await self.initialize()

      # Check cache first unless force refresh
      if not force_refresh and self.redis_storage:
        cached_catalog = await self.redis_storage.get_pricing_catalog_default()
        if cached_catalog:
          total_items = len(cached_catalog.get("products", {})) + \
              len(cached_catalog.get("generators", {}))
          logfire.info(
              f"Using cached pricing catalog: {total_items} total items")
          result["success"] = True
          result["count"] = total_items
          result["source"] = "cache"
          return result

      # Fetch products and generators from Google Sheets
      # Use tab names to construct ranges
      logfire.info("Fetching pricing data from Google Sheets")
      products_range = f"{settings.GOOGLE_SHEET_PRODUCTS_TAB_NAME}!A:Z"
      generators_range = f"{settings.GOOGLE_SHEET_GENERATORS_TAB_NAME}!A:Z"

      # Fetch both ranges in parallel
      sheet_ranges = {
          "products": products_range,
          "generators": generators_range
      }

      sheet_data = await self.sheets_service.fetch_multiple_ranges(
          settings.GOOGLE_SHEET_ID,
          list(sheet_ranges.values())
      )

      # Parse the data
      products_data = sheet_data.get(products_range, [])
      generators_data = sheet_data.get(generators_range, [])

      if not products_data and not generators_data:
        raise ValueError("No pricing data received from Google Sheets")

      # Parse pricing data - handle None values
      catalog = self.pricing_parser.parse_catalog(
          products_data or [], generators_data or []
      )

      if not catalog or (not catalog.get("products") and not catalog.get("generators")):
        raise ValueError("No valid pricing data parsed from sheets")

      # Store in Redis
      if self.redis_storage:
        await self.redis_storage.store_pricing_catalog_default(catalog)

      # Store in MongoDB
      if self.mongo_storage:
        await self.mongo_storage.store_pricing_catalog(catalog)

      total_items = len(catalog.get("products", {})) + \
          len(catalog.get("generators", {}))
      result["success"] = True
      result["count"] = total_items
      result["source"] = "sheets"

      logfire.info(
          f"Successfully synced pricing catalog: {total_items} total items")

      return result

    except Exception as e:
      error_msg = f"Failed to sync pricing catalog: {e}"
      logfire.error(error_msg)
      result["error"] = error_msg

      if background_tasks and self.redis_service:
        background_tasks.add_task(
            log_error_bg, self.redis_service, "sync_pricing_to_storage", str(e)
        )

      return result

  # Additional helper methods from original sync.py
  async def get_branches_list(self) -> List[Dict[str, Any]]:
    """Get the list of branch locations."""
    if not self.redis_storage:
      await self.initialize()
    branches = await self.redis_storage.get_branches_default() if self.redis_storage else []
    return branches or []

  async def get_states_list(self) -> List[str]:
    """Get the list of available states."""
    if not self.redis_storage:
      await self.initialize()
    states = await self.redis_storage.get_states_default() if self.redis_storage else []
    # Handle both string lists and dict lists
    if states and isinstance(states[0], dict):
      return [state.get("state", "") for state in states if state.get("state")]
    return states or []

  async def get_pricing_catalog(self) -> Optional[Dict[str, Any]]:
    """Get the pricing catalog."""
    if not self.redis_storage:
      await self.initialize()
    return await self.redis_storage.get_pricing_catalog_default() if self.redis_storage else None

  async def refresh_catalog(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
    """Force refresh of the entire catalog."""
    return await self.sync_full_catalog(background_tasks=background_tasks, force_refresh=True)


# Global service instance management
_sheet_sync_service_instance: Optional[SheetSyncService] = None


async def get_sheet_sync_service() -> SheetSyncService:
  """Get the global SheetSyncService instance."""
  global _sheet_sync_service_instance
  if _sheet_sync_service_instance is None:
    _sheet_sync_service_instance = SheetSyncService()
    await _sheet_sync_service_instance.initialize()
  return _sheet_sync_service_instance


def set_sheet_sync_service(service: SheetSyncService) -> None:
  """Set the global SheetSyncService instance."""
  global _sheet_sync_service_instance
  _sheet_sync_service_instance = service


# Lifespan management functions
async def lifespan_startup():
  """Initialize sync service on application startup."""
  try:
    logfire.info("Initializing SheetSyncService during application startup")
    service = await get_sheet_sync_service()

    # Start background sync
    await service.start_background_sync()

    # Run initial sync after delay
    asyncio.create_task(_run_initial_sync_after_delay(service, 5))

    logfire.info("SheetSyncService startup completed successfully")

  except Exception as e:
    logfire.error(f"Failed to initialize SheetSyncService during startup: {e}")
    raise


async def lifespan_shutdown():
  """Cleanup sync service on application shutdown."""
  global _sheet_sync_service_instance
  if _sheet_sync_service_instance:
    try:
      logfire.info("Shutting down SheetSyncService")
      await _sheet_sync_service_instance.stop_background_sync()
      logfire.info("SheetSyncService shutdown completed")
    except Exception as e:
      logfire.error(f"Error during SheetSyncService shutdown: {e}")


# Helper functions for background tasks
async def _run_initial_sync_after_delay(service: SheetSyncService, delay_seconds: int):
  """Run initial sync after application startup delay."""
  try:
    logfire.info(f"Waiting {delay_seconds} seconds before initial sync")
    await asyncio.sleep(delay_seconds)

    logfire.info("Running initial sync after startup delay")
    result = await service.sync_full_catalog(force_refresh=True)
    logfire.info("Initial sync completed", result=result)

  except Exception as e:
    logfire.error(f"Error in initial sync after delay: {e}")


async def _run_priority_full_sync(service: SheetSyncService, delay_seconds: int):
  """Run a priority full sync after delay."""
  try:
    logfire.info(f"Waiting {delay_seconds} seconds before priority sync")
    await asyncio.sleep(delay_seconds)

    logfire.info("Running priority full sync")
    result = await service.sync_full_catalog(force_refresh=True)
    logfire.info("Priority sync completed", result=result)

  except Exception as e:
    logfire.error(f"Error in priority sync: {e}")
