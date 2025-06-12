import logging
from typing import Any, Dict, Optional, List

from fastapi import Depends

from app.services.redis.redis import RedisService
from app.services.mongo import MongoService, get_mongo_service
from app.models.dash.dashboard import (
    DashboardOverview,
    CacheItem,
    CacheSearchResult,
    ErrorLogEntry,
    SheetProductsResponse,
    SheetGeneratorsResponse,
    SheetBranchesResponse,
    SheetStatesResponse,
    SheetConfigResponse,
)

from app.services.dash.overview.generator import OverviewGenerator
from app.services.dash.cache.manager import CacheManager
from app.services.dash.errors.manager import ErrorManager
from app.services.dash.stats.collector import StatsCollector
from app.services.dash.sync.manager import SyncManager
from app.services.dash.sync.trigger import SyncTrigger
from app.services.dash.sheets.fetcher import DataFetcher
from app.services.dash.services.status import StatusFetcher
from app.services.dash.latency.service import LatencyService

logger = logging.getLogger(__name__)


class DashboardService:
  """Main service layer for dashboard operations, orchestrating various specialized managers."""

  def __init__(self, redis_service: RedisService, mongo_service: MongoService):
    self.redis = redis_service
    self.mongo = mongo_service

    # Initialize specialized managers
    self.overview_generator = OverviewGenerator(redis_service, mongo_service)
    self.cache_manager = CacheManager(redis_service)
    self.error_manager = ErrorManager(mongo_service)
    self.stats_collector = StatsCollector(redis_service, mongo_service)
    self.sync_manager = SyncManager(redis_service, mongo_service)
    self.sync_trigger = SyncTrigger()
    self.data_fetcher = DataFetcher(mongo_service)
    self.status_fetcher = StatusFetcher(mongo_service)
    self.latency_service = LatencyService(redis_service)

  # --- Monitoring Features ---

  async def get_dashboard_overview(self) -> DashboardOverview:
    """Gathers data for the main dashboard overview from Redis and MongoDB."""
    return await self.overview_generator.generate_overview()

  # --- Management Features ---

  async def search_cache_keys(self, pattern: str) -> List[CacheSearchResult]:
    """Searches for cache keys matching a pattern and returns preview."""
    return await self.cache_manager.search_cache_keys(pattern)

  async def get_cache_item(self, key: str) -> Optional[CacheItem]:
    """Fetches a specific cache item with its TTL."""
    return await self.cache_manager.get_cache_item(key)

  async def clear_cache_item(self, key: str) -> bool:
    """Clears a specific key from the Redis cache."""
    return await self.cache_manager.clear_cache_item(key)

  async def clear_pricing_catalog_cache(self) -> bool:
    """Clears the main pricing catalog cache key."""
    return await self.cache_manager.clear_pricing_catalog_cache()

  async def clear_maps_location_cache(self, location_pattern: str) -> int:
    """Clears Google Maps cache keys matching a location pattern."""
    return await self.cache_manager.clear_maps_location_cache(location_pattern)

  async def clear_cache_key(self, cache_key: str) -> bool:
    """Clears a specific key in Redis."""
    return await self.cache_manager.clear_cache_key(cache_key)

  async def trigger_sheet_sync(self) -> bool:
    """Manually triggers a full sync from Google Sheets."""
    return await self.sync_trigger.trigger_sheet_sync()

  async def get_error_logs(
      self, report_type: Optional[str] = None, limit: int = 50
  ) -> List[ErrorLogEntry]:
    """Retrieves recent error logs from MongoDB, optionally filtered by type."""
    return await self.error_manager.get_error_logs(report_type, limit)

  # --- Sheet Data Fetching Methods ---

  async def get_sheet_products_data(self) -> SheetProductsResponse:
    """Retrieves all product data from the MongoDB sheet_products collection."""
    return await self.data_fetcher.get_products_data()

  async def get_sheet_generators_data(self) -> SheetGeneratorsResponse:
    """Retrieves all generator data from the MongoDB sheet_generators collection."""
    return await self.data_fetcher.get_generators_data()

  async def get_sheet_branches_data(self) -> SheetBranchesResponse:
    """Retrieves all branch data from the MongoDB sheet_branches collection."""
    return await self.data_fetcher.get_branches_data()

  async def get_sheet_config_data(self) -> SheetConfigResponse:
    """Retrieves the main configuration document from the MongoDB sheet_config collection."""
    return await self.data_fetcher.get_config_data()

  async def get_sheet_states_data(self) -> SheetStatesResponse:
    """Retrieves all states data from the MongoDB sheet_states collection."""
    return await self.data_fetcher.get_states_data()

  async def get_service_statuses(self) -> List[Dict[str, Any]]:
    """Retrieves the latest service status records from MongoDB."""
    return await self.status_fetcher.get_service_statuses()

  # --- Latency Tracking Methods ---

  async def get_latency_overview(self) -> Dict[str, Any]:
    """Get comprehensive latency overview for dashboard."""
    return await self.latency_service.get_dashboard_overview()

  async def get_latency_summary(self, service_type: str) -> Dict[str, Any]:
    """Get latency summary for a specific service."""
    return await self.latency_service.get_service_summary(service_type)

  async def get_latency_alerts(self) -> List[Dict[str, Any]]:
    """Get active latency alerts."""
    return await self.latency_service.check_alerts()

  async def record_latency(
      self,
      service_type: str,
      latency_ms: float,
      request_id: Optional[str] = None,
      endpoint: Optional[str] = None,
      context: Optional[Dict[str, Any]] = None
  ) -> bool:
    """Record latency data for a service."""
    if service_type == "quote":
      return await self.latency_service.record_quote_latency(
          latency_ms, request_id, context.get(
              "quote_type") if context else None,
          context.get("location") if context else None
      )
    elif service_type == "location":
      return await self.latency_service.record_location_latency(
          latency_ms, request_id, context.get(
              "lookup_type") if context else None,
          context.get("address") if context else None
      )
    elif service_type in ["hubspot", "bland", "gmaps"]:
      return await self.latency_service.record_external_api_latency(
          service_type, latency_ms, request_id, endpoint,
          context.get("response_status") if context else None
      )
    else:
      logger.warning(
          f"Unknown service type for latency recording: {service_type}")
      return False


# Dependency injection function
async def get_dashboard_service(
    redis_service: RedisService = Depends(lambda: RedisService()),
    mongo_service: MongoService = Depends(get_mongo_service),
) -> DashboardService:
  """Creates and returns a DashboardService instance with dependencies."""
  return DashboardService(redis_service, mongo_service)
