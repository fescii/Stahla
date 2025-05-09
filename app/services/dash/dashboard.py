import logging
import json # For previewing JSON values
from typing import Any, Dict, Optional, List
from collections import Counter # For error aggregation
from datetime import datetime # For timestamping external service checks

from fastapi import Depends

from app.services.redis.redis import RedisService 
from app.services.mongo.mongo import MongoService, get_mongo_service, SHEET_PRODUCTS_COLLECTION, SHEET_GENERATORS_COLLECTION, SHEET_BRANCHES_COLLECTION, SHEET_CONFIG_COLLECTION # Import Mongo and collection names
from app.services.quote.sync import SheetSyncService, PRICING_CATALOG_CACHE_KEY, BRANCH_LIST_CACHE_KEY, _sheet_sync_service_instance
# Access the running SheetSyncService instance (use with caution)

# Import dashboard models
from app.models.dash.dashboard import (
    DashboardOverview, CacheStats, ExternalServiceStatus, SyncStatus, # Import needed models
    CacheItem, CacheSearchResult, RequestLogEntry, ErrorLogEntry, CacheHitMissRatio, # Ensure ErrorLogEntry and CacheHitMissRatio are imported
    SheetProductsResponse, SheetGeneratorsResponse, SheetBranchesResponse, SheetConfigResponse, # Added sheet response models
    SheetProductEntry, SheetGeneratorEntry, SheetConfigEntry # Added sheet entry models
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
    GMAPS_API_ERRORS_KEY
)

# New Redis keys for cache hit/miss tracking
PRICING_CACHE_HITS_KEY = "dash:cache:pricing:hits"
PRICING_CACHE_MISSES_KEY = "dash:cache:pricing:misses"
MAPS_CACHE_HITS_KEY = "dash:cache:maps:hits"
MAPS_CACHE_MISSES_KEY = "dash:cache:maps:misses"

logger = logging.getLogger(__name__)

# Placeholder constants to resolve NameError - Review if these Redis keys/limits are still needed
MAX_LOG_ENTRIES = 100 
RECENT_REQUESTS_KEY = "dash:requests:recent" 

class DashboardService:
    """Service layer for dashboard operations."""

    def __init__(self, redis_service: RedisService, mongo_service: MongoService): # Add mongo_service
        self.redis = redis_service
        self.mongo = mongo_service # Store mongo_service

    @property
    def sync_service(self) -> Optional[SheetSyncService]:
        """Dynamically retrieves the global SheetSyncService instance."""
        from app.services.quote.sync import _sheet_sync_service_instance as global_sync_service
        return global_sync_service

    # --- Monitoring Features ---

    async def get_dashboard_overview(self) -> DashboardOverview:
        """Gathers data for the main dashboard overview from Redis and MongoDB."""
        logger.info("Fetching dashboard overview data from Redis and MongoDB.")

        overview_data = {}

        # --- Fetch Summary from MongoDB --- 
        report_summary = await self.mongo.get_report_summary()
        overview_data['report_summary'] = report_summary
        logger.debug(f"MongoDB Report Summary: {report_summary}")

        # --- Fetch Counters from Redis ---
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
                GMAPS_API_ERRORS_KEY
            ]
            results = await self.redis.mget(keys_to_fetch)
            
            redis_counters = {}
            for key, value in zip(keys_to_fetch, results):
                short_key = key.split(':')[-1] # e.g., 'total', 'success', 'error'
                if key.startswith("dash:requests:quote:"):
                    group = "quote_requests"
                elif key.startswith("dash:requests:location:"):
                    group = "location_lookups"
                elif key.startswith("dash:gmaps:"):
                    group = "gmaps_api"
                elif key.startswith("dash:sync:sheets:"): # Should not be here, sync status is separate
                    group = "sheet_sync_counters" # Renamed to avoid clash
                else:
                    group = "other"
                
                if group not in redis_counters:
                    redis_counters[group] = {}
                redis_counters[group][short_key] = int(value) if value is not None else 0

            overview_data['redis_counters'] = redis_counters
            logger.debug(f"Redis Counters: {redis_counters}")

        except Exception as e:
            logger.error(f"Failed to fetch counters from Redis: {e}", exc_info=True)
            overview_data['redis_counters'] = {}

        # --- Fetch Recent Error Reports/Logs from MongoDB (general errors) --- 
        try:
            # Fetch last 10 error reports of any type for general overview
            # These are ErrorLogEntry models from get_error_logs
            recent_general_errors = await self.get_error_logs(limit=10)
            overview_data['recent_errors'] = recent_general_errors # This expects List[ErrorLogEntry]
            logger.debug(f"Recent General Errors (MongoDB): {len(recent_general_errors)} fetched")
            
        except Exception as e:
            logger.error(f"Failed to fetch recent general error reports from MongoDB: {e}", exc_info=True)
            overview_data['recent_errors'] = []

        # --- Cache Stats ---
        total_redis_keys = -1
        redis_memory_used_human = "N/A"
        pricing_catalog_size_bytes = None
        pricing_cache_last_updated_timestamp = None # Store actual datetime or None
        maps_cache_key_count = 0
        # Initialize with default CacheHitMissRatio objects or None
        pricing_ratio_obj: Optional[CacheHitMissRatio] = None
        maps_ratio_obj: Optional[CacheHitMissRatio] = None

        try:
            redis_info = await self.redis.get_redis_info()
            if redis_info:
                total_redis_keys = redis_info.get('db0', {}).get('keys', -1) # Example for db0
                redis_memory_used_human = redis_info.get('used_memory_human', "N/A")
            
            pricing_catalog_size_bytes = await self.redis.get_key_memory_usage(PRICING_CATALOG_CACHE_KEY)
            
            if await self.redis.exists(PRICING_CATALOG_CACHE_KEY):
                 pass 

            maps_keys = await self.redis.scan_keys(match="maps:distance:*")
            maps_cache_key_count = len(maps_keys)

            # Calculate Pricing Cache Hit/Miss Ratio
            pricing_hits_raw = await self.redis.get(PRICING_CACHE_HITS_KEY)
            pricing_misses_raw = await self.redis.get(PRICING_CACHE_MISSES_KEY)
            pricing_hits = int(pricing_hits_raw) if pricing_hits_raw is not None else 0
            pricing_misses = int(pricing_misses_raw) if pricing_misses_raw is not None else 0
            pricing_total = pricing_hits + pricing_misses
            
            if pricing_total > 0:
                pricing_percentage = pricing_hits / pricing_total
                pricing_ratio_obj = CacheHitMissRatio(
                    percentage=pricing_percentage,
                    hits=pricing_hits,
                    misses=pricing_misses,
                    total=pricing_total,
                    status=f"{pricing_percentage:.2%} ({pricing_hits} hits / {pricing_misses} misses)" # You might want to adjust this status string or remove it
                )
            else:
                pricing_ratio_obj = CacheHitMissRatio(status="N/A (No data)")

            # Calculate Maps Cache Hit/Miss Ratio
            maps_hits_raw = await self.redis.get(MAPS_CACHE_HITS_KEY)
            maps_misses_raw = await self.redis.get(MAPS_CACHE_MISSES_KEY)
            maps_hits = int(maps_hits_raw) if maps_hits_raw is not None else 0
            maps_misses = int(maps_misses_raw) if maps_misses_raw is not None else 0
            maps_total = maps_hits + maps_misses

            if maps_total > 0:
                maps_percentage = maps_hits / maps_total
                maps_ratio_obj = CacheHitMissRatio(
                    percentage=maps_percentage,
                    hits=maps_hits,
                    misses=maps_misses,
                    total=maps_total,
                    status=f"{maps_percentage:.2%} ({maps_hits} hits / {maps_misses} misses)" # Adjust status string as needed
                )
            else:
                maps_ratio_obj = CacheHitMissRatio(status="N/A (No data)")

        except Exception as e:
            logger.error(f"Failed to fetch some cache statistics: {e}", exc_info=True)
            # Ensure defaults if error occurs mid-process
            if pricing_ratio_obj is None:
                pricing_ratio_obj = CacheHitMissRatio(status="Error fetching data")
            if maps_ratio_obj is None:
                maps_ratio_obj = CacheHitMissRatio(status="Error fetching data")
        
        overview_data['cache_stats'] = CacheStats(
            total_redis_keys=total_redis_keys,
            redis_memory_used_human=redis_memory_used_human,
            pricing_catalog_size_bytes=pricing_catalog_size_bytes,
            maps_cache_key_count=maps_cache_key_count,
            hit_miss_ratio_pricing=pricing_ratio_obj,
            hit_miss_ratio_maps=maps_ratio_obj,
        )
        logger.debug(f"Partial Cache Stats: {overview_data['cache_stats']}")

        # --- Sync Status ---
        last_successful_sync_iso = await self.redis.get("sync:last_successful_timestamp")
        is_sync_running = False
        recent_sync_error_messages = []
        current_sync_service = self.sync_service # Use the property
        if current_sync_service and current_sync_service._sync_task:
            is_sync_running = not current_sync_service._sync_task.done()
        
        try:
            # Fetch specific sync-related errors from MongoDB
            sync_error_types = ["SheetFetchError_products", "SheetFetchError_generators", "SheetFetchError_config", "SheetFetchError_branches", "RedisStoreError", "BranchProcessingError", "CatalogProcessingError", "SyncLoopError", "InitialSyncError"]
            # Limiting to last 5 sync-specific errors
            sync_errors_reports = await self.mongo.get_recent_reports(report_type=sync_error_types, limit=5)

            for report in sync_errors_reports:
                # Ensure 'message' and 'timestamp' fields exist, format as needed
                msg = report.get("message", "Unknown sync error")
                ts = report.get("timestamp")
                # Convert timestamp to string if it's a datetime object
                ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)
                recent_sync_error_messages.append(f"{ts_str}: {msg}")

        except Exception as e:
            logger.error(f"Failed to fetch recent sync errors from MongoDB: {e}", exc_info=True)

        current_sync_status = SyncStatus(
            last_successful_sync_timestamp=last_successful_sync_iso,
            is_sync_task_running=is_sync_running,
            recent_sync_errors=recent_sync_error_messages
        )
        overview_data['sync_status'] = current_sync_status
        logger.debug(f"Sync Status: {current_sync_status}")

        # Now update pricing_cache_last_updated in cache_stats
        if overview_data.get('cache_stats') and last_successful_sync_iso:
             overview_data['cache_stats'].pricing_cache_last_updated = last_successful_sync_iso


        # --- External Service Status ---
        external_services_status = []
        
        # Google Sheets Sync
        g_sheets_status = "UNKNOWN"
        g_sheets_details = "SheetSyncService instance not available."
        if current_sync_service:
            if current_sync_service.sheet_service:
                g_sheets_status = "OK" # Assuming OK if service object is initialized
                g_sheets_details = "Google Sheets API client initialized."
            else:
                g_sheets_status = "ERROR"
                g_sheets_details = "Google Sheets API client NOT initialized."
        external_services_status.append(ExternalServiceStatus(name="Google Sheets Sync", status=g_sheets_status, details=g_sheets_details, last_checked=datetime.now()))

        # Google Maps API
        # TODO: Implement a more robust check for Google Maps API (e.g., test call or check recent error rates)
        gmaps_api_errors = overview_data.get('redis_counters', {}).get('gmaps_api', {}).get('errors', 0)
        gmaps_status = "UNKNOWN"
        if overview_data.get('redis_counters', {}).get('gmaps_api'): # If we have some counters
            gmaps_status = "OK" if gmaps_api_errors == 0 else "DEGRADED" # Basic check
        external_services_status.append(ExternalServiceStatus(name="Google Maps API", status=gmaps_status, details=f"{gmaps_api_errors} errors logged via Redis counter.", last_checked=datetime.now()))

        # Bland.ai API
        # TODO: Implement Bland.ai API status check (requires BlandAIManager access or shared status)
        external_services_status.append(ExternalServiceStatus(name="Bland.ai API", status="UNKNOWN", details="Status check not implemented.", last_checked=datetime.now()))

        # HubSpot API
        # TODO: Implement HubSpot API status check (requires HubSpotManager access or shared status)
        external_services_status.append(ExternalServiceStatus(name="HubSpot API", status="UNKNOWN", details="Status check not implemented.", last_checked=datetime.now()))
        
        overview_data['external_services'] = external_services_status
        logger.debug(f"External Services Status: {external_services_status}")

        # Construct the Pydantic model
        try:
            # Ensure all expected keys for DashboardOverview are present with defaults if necessary
            overview_data.setdefault('report_summary', {})
            overview_data.setdefault('redis_counters', {})
            overview_data.setdefault('recent_errors', []) # Already populated with ErrorLogEntry
            # cache_stats is already an object or default
            # external_services is already a list of objects
            # sync_status is already an object or default
            
            dashboard_model = DashboardOverview(**overview_data)
            logger.info("Dashboard overview data fetched and validated.")
            return dashboard_model
        except Exception as e:
            logger.error(f"Failed to create DashboardOverview model: {e}", exc_info=True)
            # Return a default/empty model or raise an error
            return DashboardOverview( # Ensure this matches the model definition
                report_summary={}, 
                redis_counters={}, 
                recent_errors=[],
                cache_stats=CacheStats(), # Use default CacheStats
                external_services=[],
                sync_status=SyncStatus() # Use default SyncStatus
            )

    # --- Management Features ---

    async def search_cache_keys(self, pattern: str) -> List[CacheSearchResult]:
        """Searches for cache keys matching a pattern and returns preview."""
        logger.info(f"Searching cache keys matching pattern: {pattern}")
        keys = await self.redis.scan_keys(match=pattern, count=1000) 
        results = []
        
        if not keys:
            return results

        pipeline_results_list = [] 
        redis_client = None 
        try:
            redis_client = await self.redis.get_client() 
            async with redis_client.pipeline(transaction=False) as pipe:
                for key_to_fetch in keys[:100]: 
                    pipe.get(key_to_fetch)
                    pipe.ttl(key_to_fetch)
                executed_pipe_results = await pipe.execute()
                if executed_pipe_results is not None:
                    pipeline_results_list = executed_pipe_results
        except Exception as e: 
            logger.error(f"Error during Redis pipeline operation in search_cache_keys: {e}", exc_info=True)
        finally:
            if redis_client:
                await redis_client.close()

        idx = 0
        for key_in_loop in keys[:100]: 
            if idx + 1 < len(pipeline_results_list): 
                value_raw = pipeline_results_list[idx]
                ttl = pipeline_results_list[idx+1]
                idx += 2

                preview = None
                if value_raw: # value_raw should be a string due to decode_responses=True in RedisService pool
                    try:
                        # Attempt to parse as JSON
                        json_val = json.loads(value_raw)
                        # If successful, use the parsed JSON object as the preview
                        # This allows the frontend to render it as a structured object
                        preview = json_val 
                    except json.JSONDecodeError:
                        # If not JSON, or if there's an error, fall back to truncated string
                        preview = str(value_raw)[:200] + "..."
                results.append(CacheSearchResult(key=key_in_loop, value_preview=preview, ttl=ttl))
            else:
                # Provide more context in the warning
                current_key_for_log = key_in_loop if keys and idx < len(keys) else "N/A"
                logger.warning(f"Pipeline results for search_cache_keys are shorter than expected. Expected at least {idx+2} items for key '{current_key_for_log}' (iterating over {len(keys[:100])} keys), got {len(pipeline_results_list)} total pipeline results. Stopping further processing of these results.")
                break 
        return results


    async def get_cache_item(self, key: str) -> Optional[CacheItem]:
        """Fetches a specific cache item with its TTL."""
        logger.info(f"Fetching cache item with TTL: {key}")
        
        value_from_pipe = None
        ttl_from_pipe = None
        redis_client = None
        try:
            redis_client = await self.redis.get_client()
            async with redis_client.pipeline(transaction=False) as pipe:
                pipe.get(key)
                pipe.ttl(key)
                pipe_results = await pipe.execute()
                if pipe_results and len(pipe_results) == 2:
                    value_from_pipe = pipe_results[0]
                    ttl_from_pipe = pipe_results[1]
                else:
                   logger.warning(f"Unexpected pipeline results for get_cache_item key '{key}': {pipe_results}")
        except Exception as e:
            logger.error(f"Error during Redis pipeline operation in get_cache_item for key '{key}': {e}", exc_info=True)
        finally:
            if redis_client:
                await redis_client.close()

        if value_from_pipe is None:
             logger.warning(f"Cache key '{key}' not found or error fetching its value from pipeline.")
             return None

        parsed_value = None
        try:
            # Ensure value is string before json.loads, as decode_responses=True should handle bytes.
            # This is a defensive check.
            if isinstance(value_from_pipe, bytes):
                value_from_pipe = value_from_pipe.decode('utf-8')
            
            if isinstance(value_from_pipe, str):
                parsed_value = json.loads(value_from_pipe)
            else: # If it's not a string (e.g. already a dict/list if somehow parsed earlier, or int/float)
                parsed_value = value_from_pipe

        except (json.JSONDecodeError, TypeError): 
            # If JSON decoding fails or type is unsuitable for loads (e.g. already parsed),
            # keep the original value_from_pipe.
            parsed_value = value_from_pipe 
        return CacheItem(key=key, value=parsed_value, ttl=ttl_from_pipe)

    async def clear_cache_item(self, key: str) -> bool:
        """Clears a specific key from the Redis cache."""
        logger.info(f"Clearing cache item: {key}")
        deleted_count = await self.redis.delete(key) # delete returns number of keys deleted
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
        keys_to_delete = await self.redis.scan_keys(match=pattern)
        if not keys_to_delete:
            logger.info("No matching maps cache keys found to clear.")
            return 0
        deleted_count = await self.redis.delete(*keys_to_delete) # Pass keys as args
        logger.info(f"Cleared {deleted_count} maps cache keys matching pattern.")
        return deleted_count


    async def trigger_sheet_sync(self) -> bool:
        """Manually triggers a full sync from Google Sheets."""
        logger.info("Attempting to trigger manual sheet sync.")
        current_sync_service = self.sync_service # Use the property to get the instance
        if current_sync_service:
            logger.info("sync_service instance found.")
            try:
                logger.info("Calling current_sync_service.sync_full_catalog()")
                success = await current_sync_service.sync_full_catalog()
                logger.info(f"current_sync_service.sync_full_catalog() returned: {success}")
                logger.info(f"Manual sync trigger result: {success}")
                return success
            except Exception as e:
                logger.exception("Error during manually triggered sync in current_sync_service.sync_full_catalog()", exc_info=e)
                return False
        else:
            logger.error("Cannot trigger manual sync: SheetSyncService instance not available at time of call.")
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

    async def get_error_logs(self, report_type: Optional[str] = None, limit: int = 50) -> List[ErrorLogEntry]:
        """Retrieves recent error logs from MongoDB, optionally filtered by type."""
        logger.info(f"Fetching error logs from MongoDB. Type: {report_type}, Limit: {limit}")
        try:
            raw_reports = await self.mongo.get_recent_reports(report_type=report_type, limit=limit)
            
            # Log the raw data received from MongoDB before filtering
            logger.debug(f"Raw reports received from MongoDB for get_error_logs: {raw_reports}")
            
            # Filter for errors (success=False) and parse into ErrorLogEntry model
            error_logs = []
            for report in raw_reports:
                # Check if 'success' field exists and is explicitly False
                if "success" in report and report["success"] is False:
                    try:
                        # Add _id conversion if not already done in mongo service
                        report['_id'] = str(report.get('_id'))
                        error_logs.append(ErrorLogEntry(**report))
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse MongoDB report into ErrorLogEntry: {report}. Error: {parse_error}")
                # else: # Optional: Log reports being skipped by the filter
                #    logger.debug(f"Skipping non-error report: {report.get('report_type')} - Success: {report.get('success')}")

            logger.info(f"Retrieved {len(error_logs)} error logs after filtering.")
            return error_logs
        except Exception as e:
            logger.error(f"Failed to retrieve error logs from MongoDB: {e}", exc_info=True)
            return []

    # --- Sheet Data Fetching Methods ---

    async def get_sheet_products_data(self) -> SheetProductsResponse:
        """Retrieves all product data from the MongoDB sheet_products collection."""
        logger.info("Fetching all products data from MongoDB sheet_products collection.")
        db = await self.mongo.get_db()
        collection = db[SHEET_PRODUCTS_COLLECTION]
        try:
            cursor = collection.find({})
            raw_products = await cursor.to_list(length=None) # Fetch all
            products = [SheetProductEntry(**p) for p in raw_products]
            logger.info(f"Retrieved {len(products)} products from MongoDB.")
            return SheetProductsResponse(count=len(products), data=products)
        except Exception as e:
            logger.error(f"Error fetching products from MongoDB: {e}", exc_info=True)
            return SheetProductsResponse(count=0, data=[])

    async def get_sheet_generators_data(self) -> SheetGeneratorsResponse:
        """Retrieves all generator data from the MongoDB sheet_generators collection."""
        logger.info("Fetching all generators data from MongoDB sheet_generators collection.")
        db = await self.mongo.get_db()
        collection = db[SHEET_GENERATORS_COLLECTION]
        try:
            cursor = collection.find({})
            raw_generators = await cursor.to_list(length=None) # Fetch all
            generators = [SheetGeneratorEntry(**g) for g in raw_generators]
            logger.info(f"Retrieved {len(generators)} generators from MongoDB.")
            return SheetGeneratorsResponse(count=len(generators), data=generators)
        except Exception as e:
            logger.error(f"Error fetching generators from MongoDB: {e}", exc_info=True)
            return SheetGeneratorsResponse(count=0, data=[])

    async def get_sheet_branches_data(self) -> SheetBranchesResponse:
        """Retrieves all branch data from the MongoDB sheet_branches collection."""
        logger.info("Fetching all branches data from MongoDB sheet_branches collection.")
        db = await self.mongo.get_db()
        collection = db[SHEET_BRANCHES_COLLECTION]
        try:
            cursor = collection.find({})
            # Assuming BranchLocation model is compatible or data is stored as dicts
            # If BranchLocation is used, ensure it's imported and used for parsing
            # from app.models.location import BranchLocation
            # branches = [BranchLocation(**b) for b in raw_branches]
            raw_branches = await cursor.to_list(length=None) # Fetch all
            logger.info(f"Retrieved {len(raw_branches)} branches from MongoDB.")
            return SheetBranchesResponse(count=len(raw_branches), data=raw_branches)
        except Exception as e:
            logger.error(f"Error fetching branches from MongoDB: {e}", exc_info=True)
            return SheetBranchesResponse(count=0, data=[])

    async def get_sheet_config_data(self) -> SheetConfigResponse:
        """Retrieves the main configuration document from the MongoDB sheet_config collection."""
        logger.info("Fetching master configuration from MongoDB sheet_config collection.")
        db = await self.mongo.get_db()
        collection = db[SHEET_CONFIG_COLLECTION]
        try:
            # Assuming there's a single config document, e.g., with _id="master_config"
            config_doc = await collection.find_one({"_id": "master_config"})
            if config_doc:
                # Convert ObjectId to string if necessary, though SheetConfigEntry handles _id alias
                # config_doc["_id"] = str(config_doc["_id"])
                parsed_config = SheetConfigEntry(**config_doc)
                logger.info(f"Retrieved master configuration from MongoDB: {parsed_config.id}")
                return SheetConfigResponse(data=parsed_config)
            else:
                logger.warning("Master configuration document not found in MongoDB.")
                return SheetConfigResponse(data=None, message="Master configuration not found.")
        except Exception as e:
            logger.error(f"Error fetching master configuration from MongoDB: {e}", exc_info=True)
            return SheetConfigResponse(data=None, message=f"Error fetching configuration: {str(e)}")

    # Commenting out Redis-specific method - replace with MongoDB query if needed
    # async def get_recent_requests(self, limit: int = MAX_LOG_ENTRIES) -> List[RequestLogEntry]:
    #     ...
