import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import Depends

from app.services.redis.redis import RedisService
from app.services.mongo import MongoService
from app.models.dash.dashboard import (
    DashboardOverview,
    CacheStats,
    ExternalServiceStatus,
    SyncStatus,
    ErrorLogEntry,
    CacheHitMissRatio,
)
from app.core.cachekeys import (
    PRICING_CATALOG_CACHE_KEY,
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY,
    GMAPS_API_CALLS_KEY,
    GMAPS_API_ERRORS_KEY,
    PRICING_CACHE_HITS_KEY,
    PRICING_CACHE_MISSES_KEY,
    MAPS_CACHE_HITS_KEY,
    MAPS_CACHE_MISSES_KEY,
)

logger = logging.getLogger(__name__)


class OverviewGenerator:
  """Generates dashboard overview data by aggregating from various sources."""

  def __init__(self, redis_service: RedisService, mongo_service: MongoService):
    self.redis = redis_service
    self.mongo = mongo_service

  async def generate_overview(self) -> DashboardOverview:
    """Gathers data for the main dashboard overview from Redis and MongoDB."""
    logger.info("Fetching dashboard overview data from Redis and MongoDB.")

    overview_data = {}

    # --- Fetch Summary from MongoDB ---
    report_summary = await self.mongo.get_report_summary()
    overview_data["report_summary"] = report_summary
    logger.debug(f"MongoDB Report Summary: {report_summary}")

    # --- Fetch Counters from Redis ---
    overview_data["redis_counters"] = await self._fetch_redis_counters()

    # --- Fetch Recent Error Reports/Logs from MongoDB ---
    overview_data["recent_errors"] = await self._fetch_recent_errors()

    # --- Cache Stats ---
    overview_data["cache_stats"] = await self._generate_cache_stats()

    # --- Sync Status ---
    overview_data["sync_status"] = await self._generate_sync_status()

    # --- External Service Status ---
    overview_data["external_services"] = await self._generate_service_status()

    # Update pricing cache last updated in cache stats
    if overview_data.get("cache_stats") and overview_data.get("sync_status"):
      sync_timestamp = overview_data["sync_status"].last_successful_sync_timestamp
      if sync_timestamp:
        overview_data["cache_stats"].pricing_cache_last_updated = sync_timestamp

    # Construct the Pydantic model
    try:
      overview_data.setdefault("report_summary", {})
      overview_data.setdefault("redis_counters", {})
      overview_data.setdefault("recent_errors", [])

      dashboard_model = DashboardOverview(**overview_data)
      logger.info("Dashboard overview data fetched and validated.")
      return dashboard_model
    except Exception as e:
      logger.error(
          f"Failed to create DashboardOverview model: {e}", exc_info=True)
      return DashboardOverview(
          report_summary={},
          redis_counters={},
          recent_errors=[],
          cache_stats=CacheStats(),
          external_services=[],
          sync_status=SyncStatus(),
          quote_requests_total=0,
          quote_requests_successful=0,
          quote_requests_failed=0,
          location_lookups_total=0,
          location_lookups_successful=0,
          location_lookups_failed=0,
      )

  async def _fetch_redis_counters(self) -> Dict[str, Any]:
    """Fetches counters from Redis."""
    try:
      keys_to_fetch = [
          TOTAL_QUOTE_REQUESTS_KEY,
          SUCCESS_QUOTE_REQUESTS_KEY,
          ERROR_QUOTE_REQUESTS_KEY,
          TOTAL_LOCATION_LOOKUPS_KEY,
          GMAPS_API_CALLS_KEY,
          GMAPS_API_ERRORS_KEY,
      ]
      results = await self.redis.mget(keys_to_fetch)

      redis_counters = {}
      for key, value in zip(keys_to_fetch, results):
        short_key = key.split(":")[-1]
        if key.startswith("dash:requests:quote:"):
          group = "quote_requests"
        elif key.startswith("dash:requests:location:"):
          group = "location_lookups"
        elif key.startswith("dash:gmaps:"):
          group = "gmaps_api"
        elif key.startswith("dash:sync:sheets:"):
          group = "sheet_sync_counters"
        else:
          group = "other"

        if group not in redis_counters:
          redis_counters[group] = {}
        redis_counters[group][short_key] = (
            int(value) if value is not None else 0
        )

      logger.debug(f"Redis Counters: {redis_counters}")
      return redis_counters

    except Exception as e:
      logger.error(f"Failed to fetch counters from Redis: {e}", exc_info=True)
      return {}

  async def _fetch_recent_errors(self) -> List[ErrorLogEntry]:
    """Fetches recent error reports from MongoDB."""
    try:
      from app.services.dash.errors.manager import ErrorManager
      error_manager = ErrorManager(self.mongo)
      recent_general_errors = await error_manager.get_error_logs(limit=10)
      logger.debug(
          f"Recent General Errors (MongoDB): {len(recent_general_errors)} fetched")
      return recent_general_errors
    except Exception as e:
      logger.error(
          f"Failed to fetch recent general error reports from MongoDB: {e}", exc_info=True)
      return []

  async def _generate_cache_stats(self) -> CacheStats:
    """Generates cache statistics."""
    total_redis_keys = -1
    redis_memory_used_human = "N/A"
    pricing_catalog_size_bytes = None
    maps_cache_key_count = 0
    pricing_ratio_obj: Optional[CacheHitMissRatio] = None
    maps_ratio_obj: Optional[CacheHitMissRatio] = None

    try:
      redis_info = await self.redis.get_redis_info()
      if redis_info:
        total_redis_keys = redis_info.get("db0", {}).get("keys", -1)
        redis_memory_used_human = redis_info.get("used_memory_human", "N/A")

      pricing_catalog_size_bytes = await self.redis.get_key_memory_usage(
          PRICING_CATALOG_CACHE_KEY
      )

      maps_keys = await self.redis.scan_keys(match="maps:distance:*")
      maps_cache_key_count = len(maps_keys)

      # Calculate cache hit/miss ratios
      pricing_ratio_obj = await self._calculate_cache_ratio(
          PRICING_CACHE_HITS_KEY, PRICING_CACHE_MISSES_KEY
      )
      maps_ratio_obj = await self._calculate_cache_ratio(
          MAPS_CACHE_HITS_KEY, MAPS_CACHE_MISSES_KEY
      )

    except Exception as e:
      logger.error(
          f"Failed to fetch some cache statistics: {e}", exc_info=True)
      if pricing_ratio_obj is None:
        pricing_ratio_obj = CacheHitMissRatio(
            percentage=0.0, hits=0, misses=0, total=0, status="Error fetching data"
        )
      if maps_ratio_obj is None:
        maps_ratio_obj = CacheHitMissRatio(
            percentage=0.0, hits=0, misses=0, total=0, status="Error fetching data"
        )

    return CacheStats(
        total_redis_keys=total_redis_keys,
        redis_memory_used_human=redis_memory_used_human,
        pricing_catalog_size_bytes=pricing_catalog_size_bytes,
        maps_cache_key_count=maps_cache_key_count,
        hit_miss_ratio_pricing=pricing_ratio_obj,
        hit_miss_ratio_maps=maps_ratio_obj,
    )

  async def _calculate_cache_ratio(self, hits_key: str, misses_key: str) -> CacheHitMissRatio:
    """Calculates cache hit/miss ratio for given keys."""
    hits_raw = await self.redis.get(hits_key)
    misses_raw = await self.redis.get(misses_key)
    hits = int(hits_raw) if hits_raw is not None else 0
    misses = int(misses_raw) if misses_raw is not None else 0
    total = hits + misses

    if total > 0:
      percentage = hits / total
      return CacheHitMissRatio(
          percentage=percentage,
          hits=hits,
          misses=misses,
          total=total,
          status=f"{percentage:.2%} ({hits} hits / {misses} misses)",
      )
    else:
      return CacheHitMissRatio(
          percentage=0.0,
          hits=0,
          misses=0,
          total=0,
          status="N/A (No data)"
      )

  async def _generate_sync_status(self) -> SyncStatus:
    """Generates sync status information."""
    last_successful_sync_iso = await self.redis.get("sync:last_successful_timestamp")
    is_sync_running = False
    recent_sync_error_messages = []

    # Check if sync is running
    try:
      from app.services.quote.sync import get_sheet_sync_service
      sync_service = await get_sheet_sync_service()
      if sync_service and sync_service._sync_task:
        is_sync_running = not sync_service._sync_task.done()
    except Exception as e:
      logger.warning(f"Could not check sync service status: {e}")

    # Fetch sync-specific errors
    try:
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
          f"Failed to fetch recent sync errors from MongoDB: {e}", exc_info=True)

    return SyncStatus(
        last_successful_sync_timestamp=last_successful_sync_iso,
        is_sync_task_running=is_sync_running,
        recent_sync_errors=recent_sync_error_messages,
    )

  async def _generate_service_status(self) -> List[ExternalServiceStatus]:
    """Generates external service status information."""
    external_services_status = []

    # Try to get service statuses from the background service monitor
    try:
      from app.services.dash.health.checker import service_status_monitor

      if service_status_monitor:
        latest_statuses = await service_status_monitor.get_latest_service_statuses()

        for service_name, status_data in latest_statuses.items():
          service_display_name = {
              "mongodb": "Mongo",
              "redis": "Redis",
              "bland_ai": "Bland",
              "hubspot": "HubSpot",
              "google_sheets": "Sheet",
          }.get(service_name, service_name.title())

          service_status = status_data.get("status", "UNKNOWN").upper()
          if service_status == "OK":
            service_status = "OK"
          elif service_status == "ERROR":
            service_status = "ERROR"
          else:
            service_status = "DEGRADED"

          external_services_status.append(
              ExternalServiceStatus(
                  name=service_display_name,
                  status=service_status,
                  details=status_data.get(
                      "message", "Status from periodic background check"
                  ),
                  last_checked=status_data.get("timestamp", datetime.now()),
              )
          )

        logger.info(
            f"Retrieved {len(external_services_status)} service statuses from background monitor")

    except (ImportError, Exception) as e:
      logger.warning(f"Could not get statuses from background monitor: {e}")

    # If we couldn't get statuses from background service, fall back to basic checks
    if not external_services_status:
      logger.info("Falling back to basic service status checks")
      external_services_status = await self._generate_fallback_service_status()

    return external_services_status

  async def _generate_fallback_service_status(self) -> List[ExternalServiceStatus]:
    """Generates fallback service status when background monitor is unavailable."""
    external_services_status = []

    # Google Sheets Sync
    g_sheets_status = "UNKNOWN"
    g_sheets_details = "SheetSyncService instance not available."
    try:
      from app.services.quote.sync import get_sheet_sync_service
      sync_service = await get_sheet_sync_service()
      if sync_service and sync_service.sheet_service:
        g_sheets_status = "OK"
        g_sheets_details = "Google Sheets API client initialized."
      else:
        g_sheets_status = "ERROR"
        g_sheets_details = "Google Sheets API client NOT initialized."
    except Exception:
      pass

    external_services_status.append(
        ExternalServiceStatus(
            name="Google Sheets Sync",
            status=g_sheets_status,
            details=g_sheets_details,
            last_checked=datetime.now(),
        )
    )

    # Google Maps API (basic check based on error counters)
    gmaps_api_errors = 0  # Will be populated from redis counters if available
    gmaps_status = "UNKNOWN"
    external_services_status.append(
        ExternalServiceStatus(
            name="Google Maps API",
            status=gmaps_status,
            details=f"{gmaps_api_errors} errors logged via Redis counter.",
            last_checked=datetime.now(),
        )
    )

    # Bland.ai API
    external_services_status.append(
        ExternalServiceStatus(
            name="Bland.ai API",
            status="UNKNOWN",
            details="Status check not implemented in fallback mode.",
            last_checked=datetime.now(),
        )
    )

    # HubSpot API
    external_services_status.append(
        ExternalServiceStatus(
            name="HubSpot API",
            status="UNKNOWN",
            details="Status check not implemented in fallback mode.",
            last_checked=datetime.now(),
        )
    )

    return external_services_status
