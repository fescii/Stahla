import logging
import json # For previewing JSON values
from typing import Any, Dict, Optional, List
from collections import Counter # For error aggregation

from fastapi import Depends

from app.services.redis.redis import RedisService, get_redis_service
from app.services.mongo.mongo import MongoService, get_mongo_service # Import Mongo
from app.services.quote.sync import SheetSyncService, PRICING_CATALOG_CACHE_KEY, BRANCH_LIST_CACHE_KEY
# Access the running SheetSyncService instance (use with caution)
from app.services.quote.sync import _sheet_sync_service_instance

# Import dashboard models
from app.models.dash.dashboard import (
    DashboardOverview, CacheStats, ExternalServiceStatus, SyncStatus,
    CacheItem, CacheSearchResult, RequestLogEntry, ErrorLogEntry
)
# Import quote models for recent requests
from app.models.quote import QuoteRequest, QuoteResponse

# Import background task constants
from app.services.dash.background import (
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY,
    GMAPS_API_CALLS_KEY,
    GMAPS_API_ERRORS_KEY,
    SHEET_SYNC_SUCCESS_KEY, # Add missing import
    SHEET_SYNC_ERRORS_KEY   # Add missing import
)

logger = logging.getLogger(__name__)

# Placeholder constants to resolve NameError - Review if these Redis keys/limits are still needed
MAX_LOG_ENTRIES = 100 
RECENT_REQUESTS_KEY = "dash:requests:recent" 

class DashboardService:
    """Service layer for dashboard operations."""

    def __init__(self, redis_service: RedisService, mongo_service: MongoService): # Add mongo_service
        self.redis = redis_service
        self.mongo = mongo_service # Store mongo_service
        self.sync_service: Optional[SheetSyncService] = _sheet_sync_service_instance

    # --- Monitoring Features ---

    async def get_dashboard_overview(self) -> DashboardOverview:
        """Gathers data for the main dashboard overview from Redis and MongoDB."""
        logger.info("Fetching dashboard overview data from Redis and MongoDB.")

        overview_data = {}

        # --- Fetch Summary from MongoDB --- 
        report_summary = await self.mongo.get_report_summary()
        overview_data['report_summary'] = report_summary
        logger.debug(f"MongoDB Report Summary: {report_summary}")

        # --- Fetch Counters from Redis (Optional - can be derived from Mongo summary too) ---
        # Decide whether to keep Redis counters or rely solely on MongoDB aggregation.
        # Keeping Redis counters can be faster for very high frequency increments.
        # Relying on MongoDB simplifies logic but aggregation might be slower under extreme load.
        # Example: Fetching from Redis
        try:
            keys_to_fetch = [
                TOTAL_QUOTE_REQUESTS_KEY,
                SUCCESS_QUOTE_REQUESTS_KEY,
                ERROR_QUOTE_REQUESTS_KEY,
                TOTAL_LOCATION_LOOKUPS_KEY,
                GMAPS_API_CALLS_KEY,
                GMAPS_API_ERRORS_KEY,
                SHEET_SYNC_SUCCESS_KEY,
                SHEET_SYNC_ERRORS_KEY
            ]
            results = await self.redis.mget(keys_to_fetch)
            
            # Process Redis results (handle None values)
            redis_counters = {}
            for key, value in zip(keys_to_fetch, results):
                # Use short key names for the model
                short_key = key.split(':')[-1] # e.g., 'total', 'success', 'error'
                if key.startswith("dash:requests:quote:"):
                    group = "quote_requests"
                elif key.startswith("dash:requests:location:"):
                    group = "location_lookups"
                elif key.startswith("dash:gmaps:"):
                    group = "gmaps_api"
                elif key.startswith("dash:sync:sheets:"):
                    group = "sheet_sync"
                else:
                    group = "other"
                
                if group not in redis_counters:
                    redis_counters[group] = {}
                redis_counters[group][short_key] = int(value) if value is not None else 0

            overview_data['redis_counters'] = redis_counters
            logger.debug(f"Redis Counters: {redis_counters}")

        except Exception as e:
            logger.error(f"Failed to fetch counters from Redis: {e}", exc_info=True)
            overview_data['redis_counters'] = {} # Default to empty if Redis fails

        # --- Fetch Recent Reports/Logs from MongoDB --- 
        try:
            # Fetch last 10 error reports of any type
            recent_errors = await self.mongo.get_recent_reports(limit=10) # Fetch all types, rely on success=False implicitly if needed or adjust get_recent_reports
            overview_data['recent_errors'] = recent_errors
            logger.debug(f"Recent Errors (MongoDB): {len(recent_errors)} fetched")
            
        except Exception as e:
            logger.error(f"Failed to fetch recent reports from MongoDB: {e}", exc_info=True)
            overview_data['recent_errors'] = []

        # Construct the Pydantic model
        # Adapt DashboardOverview model if necessary based on fetched data structure
        try:
            # Ensure all expected keys for DashboardOverview are present
            overview_data.setdefault('report_summary', {})
            overview_data.setdefault('redis_counters', {})
            overview_data.setdefault('recent_errors', [])
            
            dashboard_model = DashboardOverview(**overview_data)
            logger.info("Dashboard overview data fetched and validated.")
            return dashboard_model
        except Exception as e:
            logger.error(f"Failed to create DashboardOverview model: {e}", exc_info=True)
            # Return a default/empty model or raise an error
            return DashboardOverview(report_summary={}, redis_counters={}, recent_errors=[])

    # --- Management Features ---

    async def search_cache_keys(self, pattern: str) -> List[CacheSearchResult]:
        """Searches for cache keys matching a pattern and returns preview."""
        logger.info(f"Searching cache keys matching pattern: {pattern}")
        keys = await self.redis_service.scan_keys(match=pattern, count=1000) # Limit scan count
        results = []
        # Use pipeline for efficiency if fetching many values/ttls
        async with self.redis_service.client.pipeline(transaction=False) as pipe:
            for key in keys[:100]: # Limit results returned
                pipe.get(key)
                pipe.ttl(key)
            pipeline_results = await pipe.execute()

        idx = 0
        for key in keys[:100]:
            value_raw = pipeline_results[idx]
            ttl = pipeline_results[idx+1]
            idx += 2

            preview = None
            if value_raw:
                try:
                    # Attempt JSON decode for preview
                    json_val = json.loads(value_raw)
                    preview = json.dumps(json_val, indent=2)[:200] + "..." # Truncated JSON preview
                except json.JSONDecodeError:
                    preview = value_raw[:200] + "..." # Truncated string preview
            results.append(CacheSearchResult(key=key, value_preview=preview, ttl=ttl))

        return results


    async def get_cache_item(self, key: str) -> Optional[CacheItem]:
        """Fetches a specific cache item with its TTL."""
        logger.info(f"Fetching cache item with TTL: {key}")
        async with self.redis_service.client.pipeline(transaction=False) as pipe:
            pipe.get(key)
            pipe.ttl(key)
            results = await pipe.execute()

        value = results[0]
        ttl = results[1]

        if value is None:
             logger.warning(f"Cache key not found: {key}")
             return None

        # Try to decode JSON
        try:
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            parsed_value = value # Keep as string if not JSON

        return CacheItem(key=key, value=parsed_value, ttl=ttl)

    async def clear_cache_item(self, key: str) -> bool:
        """Clears a specific key from the Redis cache."""
        logger.info(f"Clearing cache item: {key}")
        deleted_count = await self.redis_service.delete(key) # delete returns number of keys deleted
        if deleted_count == 0:
            logger.warning(f"Cache key not found or already expired: {key}")
            return False
        return True

    async def clear_pricing_catalog_cache(self) -> bool:
        """Clears the main pricing catalog cache key."""
        logger.warning(f"Clearing ENTIRE pricing catalog cache: {PRICING_CATALOG_CACHE_KEY}")
        return await self.clear_cache_item(PRICING_CATALOG_CACHE_KEY)

    async def clear_maps_location_cache(self, location_pattern: str) -> int:
        """Clears Google Maps cache keys matching a location pattern."""
        pattern = f"maps:distance:*:{location_pattern}" # Assumes normalized key structure
        logger.warning(f"Clearing Google Maps cache keys matching pattern: {pattern}")
        keys_to_delete = await self.redis_service.scan_keys(match=pattern)
        if not keys_to_delete:
            logger.info("No matching maps cache keys found to clear.")
            return 0
        deleted_count = await self.redis_service.delete(*keys_to_delete) # Pass keys as args
        logger.info(f"Cleared {deleted_count} maps cache keys matching pattern.")
        return deleted_count


    async def trigger_sheet_sync(self) -> bool:
        """Manually triggers a full sync from Google Sheets."""
        logger.info("Attempting to trigger manual sheet sync.")
        if self.sync_service:
            try:
                # Call the sync method directly
                success = await self.sync_service.sync_full_catalog_to_redis()
                logger.info(f"Manual sync trigger result: {success}")
                return success
            except Exception as e:
                logger.exception("Error during manually triggered sync", exc_info=e)
                return False
        else:
            logger.error("Cannot trigger manual sync: SheetSyncService instance not available.")
            return False

    # --- Cache Clearing Method (Example) ---
    async def clear_cache_key(self, cache_key: str) -> bool:
        """Clears a specific key in Redis."""
        try:
            deleted_count = await self.redis.delete(cache_key)
            return deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to clear Redis cache key '{cache_key}': {e}", exc_info=True)
            return False

    # Commenting out Redis-specific method - replace with MongoDB query if needed
    # async def get_recent_requests(self, limit: int = MAX_LOG_ENTRIES) -> List[RequestLogEntry]:
    #     ...

# Dependency for FastAPI
async def get_dashboard_service(
    redis_service: RedisService = Depends(get_redis_service),
    mongo_service: MongoService = Depends(get_mongo_service) # Add mongo dependency
) -> DashboardService:
    return DashboardService(redis_service, mongo_service)
