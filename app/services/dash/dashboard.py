import logging
from typing import Any, Dict, Optional, List
from datetime import datetime
import json # For previewing JSON values
from collections import Counter # For error aggregation

from fastapi import Depends

from app.services.redis.redis import RedisService, get_redis_service
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
    RECENT_REQUESTS_KEY, RECENT_ERRORS_KEY, MAX_LOG_ENTRIES,
    TOTAL_QUOTE_REQUESTS_KEY, SUCCESS_QUOTE_REQUESTS_KEY, ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY,
    GMAPS_API_CALLS_KEY, GMAPS_API_ERRORS_KEY # Add maps keys
)

logger = logging.getLogger(__name__)

class DashboardService:
    """Service layer for dashboard operations."""

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.sync_service: Optional[SheetSyncService] = _sheet_sync_service_instance

    # --- Monitoring Features ---

    async def get_dashboard_overview(self) -> DashboardOverview:
        """Gathers data for the main dashboard overview from Redis."""
        logger.info("Fetching dashboard overview data from Redis.")

        # Use pipeline for efficiency
        async with self.redis_service.client.pipeline(transaction=False) as pipe:
            # 1. Cache Stats
            pipe.get(PRICING_CATALOG_CACHE_KEY)
            pipe.get("sync:last_successful_timestamp") # Example key for last sync
            pipe.scan(cursor=0, match="maps:distance:*", count=5000) # Scan for maps keys

            # 2. Counters
            pipe.get(TOTAL_QUOTE_REQUESTS_KEY)
            pipe.get(SUCCESS_QUOTE_REQUESTS_KEY)
            pipe.get(ERROR_QUOTE_REQUESTS_KEY)
            pipe.get(TOTAL_LOCATION_LOOKUPS_KEY)
            # Add Google Maps counters
            pipe.get(GMAPS_API_CALLS_KEY)
            pipe.get(GMAPS_API_ERRORS_KEY)

            # 3. Logs
            pipe.lrange(RECENT_ERRORS_KEY, 0, MAX_LOG_ENTRIES - 1)
            pipe.lrange(RECENT_REQUESTS_KEY, 0, MAX_LOG_ENTRIES - 1)

            # Execute pipeline
            results = await pipe.execute()

        # --- Process Pipeline Results ---
        # Be careful with indices matching the pipeline order
        res_idx = 0

        # 1. Cache Stats
        pricing_catalog_json = results[res_idx]; res_idx += 1
        pricing_last_updated = results[res_idx]; res_idx += 1
        maps_scan_cursor, maps_keys = results[res_idx]; res_idx += 1 # SCAN returns cursor and keys
        # Note: SCAN might require multiple calls for large datasets, this is simplified
        maps_cache_key_count = len(maps_keys)
        pricing_cache_size_kb = len(pricing_catalog_json.encode('utf-8')) / 1024 if pricing_catalog_json else 0

        cache_stats = CacheStats(
            pricing_cache_last_updated=pricing_last_updated,
            pricing_cache_size_kb=round(pricing_cache_size_kb, 2),
            maps_cache_key_count=maps_cache_key_count
        )

        # 2. Counters
        total_quotes_raw = results[res_idx]; res_idx += 1
        success_quotes_raw = results[res_idx]; res_idx += 1
        error_quotes_raw = results[res_idx]; res_idx += 1
        total_lookups_raw = results[res_idx]; res_idx += 1
        # Add Google Maps counters
        gmaps_calls_raw = results[res_idx]; res_idx += 1
        gmaps_errors_raw = results[res_idx]; res_idx += 1

        def safe_int(val: Optional[str]) -> Optional[int]:
            try: return int(val) if val is not None else 0 # Default to 0 if None
            except (ValueError, TypeError): return 0 # Default to 0 on parse error

        total_quotes = safe_int(total_quotes_raw)
        success_quotes = safe_int(success_quotes_raw)
        error_quotes = safe_int(error_quotes_raw)
        total_lookups = safe_int(total_lookups_raw)
        gmaps_calls = safe_int(gmaps_calls_raw)
        gmaps_errors = safe_int(gmaps_errors_raw)

        # 3. External Service Status
        sync_running = False
        if self.sync_service and self.sync_service._sync_task:
            sync_running = not self.sync_service._sync_task.done()
        sync_status = SyncStatus(
            last_successful_sync_timestamp=pricing_last_updated,
            is_sync_task_running=sync_running,
        )
        # Add Maps stats to external services
        external_services = ExternalServiceStatus(
            google_sheet_sync=sync_status,
            google_maps_api_calls=gmaps_calls,
            google_maps_api_errors=gmaps_errors
        )

        # 4. Error Summary (with Aggregation)
        error_log_entries_raw = []
        raw_errors = results[res_idx]; res_idx += 1
        if raw_errors:
             for err_json in raw_errors:
                 try: error_log_entries_raw.append(ErrorLogEntry.model_validate_json(err_json))
                 except Exception as e: logger.warning(f"Failed to parse error log entry from Redis: {e}")
        
        # Aggregate errors by type
        error_summary_aggregated: List[ErrorLogEntry] = []
        if error_log_entries_raw:
            error_counts = Counter(err.error_type for err in error_log_entries_raw)
            # Create aggregated entries using the most recent example of each type
            processed_types = set()
            for entry in sorted(error_log_entries_raw, key=lambda x: x.timestamp, reverse=True):
                if entry.error_type not in processed_types:
                    entry.count = error_counts[entry.error_type]
                    error_summary_aggregated.append(entry)
                    processed_types.add(entry.error_type)
            # Sort aggregated summary by count descending
            error_summary_aggregated.sort(key=lambda x: x.count, reverse=True)

        # 5. Recent Requests
        recent_request_entries = []
        raw_requests = results[res_idx]; res_idx += 1
        if raw_requests:
             for req_json in raw_requests:
                 try: recent_request_entries.append(RequestLogEntry.model_validate_json(req_json))
                 except Exception as e: logger.warning(f"Failed to parse request log entry from Redis: {e}")

        # --- Assemble Overview --- 
        overview = DashboardOverview(
            cache_stats=cache_stats,
            external_services=external_services,
            error_summary=error_summary_aggregated, # Use aggregated list
            recent_requests=recent_request_entries,
            quote_requests_total=total_quotes,
            quote_requests_success=success_quotes,
            quote_requests_error=error_quotes,
            location_lookups_total=total_lookups,
            quote_latency_p95_ms=None, # Requires dedicated tracking
        )
        return overview

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

    async def get_recent_requests(self, limit: int = MAX_LOG_ENTRIES) -> List[RequestLogEntry]:
         """Retrieves the most recent request/response logs from Redis."""
         logs = []
         # Use client directly for simplicity or add lrange to RedisService
         client = await self.redis_service.get_client()
         raw_logs = await client.lrange(RECENT_REQUESTS_KEY, 0, limit - 1)
         await client.aclose()
         if raw_logs:
             for log_json in raw_logs:
                 try:
                     logs.append(RequestLogEntry.model_validate_json(log_json))
                 except Exception as e:
                     logger.warning(f"Failed to parse request log entry from Redis: {e}")
         return logs

# Dependency for FastAPI
async def get_dashboard_service(
    redis_service: RedisService = Depends(get_redis_service)
) -> DashboardService:
    return DashboardService(redis_service)
