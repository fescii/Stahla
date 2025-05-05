# filepath: /home/femar/AO3/Stahla/app/services/quote/sheet_sync.py
import asyncio
import logging
import re # Import re for cleaning
from typing import Any, Dict, List, Optional
from datetime import datetime # Import datetime for seasonal check

from fastapi import BackgroundTasks # Import BackgroundTasks

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.services.redis.redis import RedisService # Import renamed service
from app.models.location import BranchLocation # Import BranchLocation model
# Import background error logging function
from app.services.dash.background import log_error_bg

logger = logging.getLogger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
PRICING_CATALOG_CACHE_KEY = "pricing:catalog"
BRANCH_LIST_CACHE_KEY = "stahla:branches" # New Redis key for branches list
CONFIG_DATA_RANGE = settings.GOOGLE_SHEET_CONFIG_RANGE # Use setting
SYNC_INTERVAL_SECONDS = 300  # Sync every 5 minutes

# Helper to clean currency strings
def _clean_currency(value: Any) -> Optional[float]:
    # ... (helper function remains the same) ...
    if value is None or value == 'n/a':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove $, commas, and whitespace
        cleaned = re.sub(r'[$,\s]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not convert currency string '{value}' to float.")
            return None
    return None

class SheetSyncService:
    # ... (existing __init__, _get_credentials, _build_sheet_service, _fetch_sheet_data, _parse_branches, _parse_delivery_and_config) ...

    def _parse_pricing_data(self, products_data: List[List[Any]], generators_data: List[List[Any]], config_parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses raw sheet data from 'products' and 'generators' tabs into a structured pricing catalog.
        Incorporates delivery and seasonal config. Branches are handled separately.
        """
        catalog = {"products": {}, "generators": {}}

        # --- Parse Products (Trailers & Extras) --- 
        if products_data and len(products_data) > 0:
            headers = [str(h).strip().lower() for h in products_data[0]]
            logger.debug(f"Products headers: {headers}")
            expected_headers = [
                'primary column', 'weekly pricing (7 day)', '28 day rate', '2-5 month rate',
                '6+ month pricing', '18+ month pricing', 'event standard (<4 days)',
                'event premium (<4 days)', 'event premium plus (<4 days)',
                'event premium platinum (<4 days)', 'pump out waste tank',
                'fresh water tank fill', 'cleaning', 'restocking'
            ]
            if not all(h in headers for h in ['primary column', 'weekly pricing (7 day)', 'event standard (<4 days)']):
                logger.error(f"Missing essential headers in products sheet. Found: {headers}")
            else:
                for row in products_data[1:]: 
                    if len(row) > 0 and row[0] and str(row[0]).strip():
                        product_id = str(row[0]).strip()
                        product_entry = {"id": product_id, "name": product_id}
                        try:
                            # Map headers to data, cleaning currency
                            product_entry['weekly_7_day'] = _clean_currency(row[headers.index('weekly pricing (7 day)')])
                            product_entry['rate_28_day'] = _clean_currency(row[headers.index('28 day rate')])
                            product_entry['rate_2_5_month'] = _clean_currency(row[headers.index('2-5 month rate')])
                            product_entry['rate_6_plus_month'] = _clean_currency(row[headers.index('6+ month pricing')])
                            product_entry['rate_18_plus_month'] = _clean_currency(row[headers.index('18+ month pricing')])
                            product_entry['event_standard'] = _clean_currency(row[headers.index('event standard (<4 days)')])
                            product_entry['event_premium'] = _clean_currency(row[headers.index('event premium (<4 days)')])
                            product_entry['event_premium_plus'] = _clean_currency(row[headers.index('event premium plus (<4 days)')])
                            product_entry['event_premium_platinum'] = _clean_currency(row[headers.index('event premium platinum (<4 days)')])
                            # Store extra service costs associated with this product
                            product_entry['extras'] = {
                                'pump_out': _clean_currency(row[headers.index('pump out waste tank')]),
                                'fresh_water_fill': _clean_currency(row[headers.index('fresh water tank fill')]),
                                'cleaning': _clean_currency(row[headers.index('cleaning')]),
                                'restocking': _clean_currency(row[headers.index('restocking')])
                            }
                            catalog["products"][product_id] = product_entry
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Skipping product row due to parsing error: {row}. Error: {e}")
                        except Exception as e:
                             logger.error(f"Unexpected error parsing product row: {row}. Error: {e}", exc_info=True)
        # --- End Parse Products --- 

        # --- Parse Generators --- 
        if generators_data and len(generators_data) > 1: 
            gen_header_row_index = -1
            for i, row in enumerate(generators_data):
                if len(row) > 1 and str(row[1]).strip().lower() == 'event (< 3 day rate)':
                    gen_header_row_index = i
                    break
            
            if gen_header_row_index == -1:
                 logger.warning("Could not find generator header row in generators sheet data.")
            else:
                headers = [str(h).strip().lower() for h in generators_data[gen_header_row_index]]
                logger.debug(f"Generators headers: {headers}")
                expected_gen_headers = ['event (< 3 day rate)', '7 day rate', '28 day rate']
                if not all(h in headers for h in expected_gen_headers):
                     logger.error(f"Missing essential headers in generators sheet. Found: {headers}")
                else:
                    for row in generators_data[gen_header_row_index + 1:]: 
                        if len(row) > 0 and row[0] and str(row[0]).strip():
                            raw_name = str(row[0]).strip()
                            gen_id_match = re.search(r'\((GEN-\w+)\)', raw_name)
                            gen_id = gen_id_match.group(1) if gen_id_match else raw_name
                            gen_name = raw_name.split('(')[0].strip() if gen_id_match else raw_name

                            generator_entry = {"id": gen_id, "name": gen_name}
                            try:
                                generator_entry['rate_event'] = _clean_currency(row[headers.index('event (< 3 day rate)')])
                                generator_entry['rate_7_day'] = _clean_currency(row[headers.index('7 day rate')])
                                generator_entry['rate_28_day'] = _clean_currency(row[headers.index('28 day rate')])
                                catalog["generators"][gen_id] = generator_entry
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Skipping generator row due to parsing error: {row}. Error: {e}")
                            except Exception as e:
                                logger.error(f"Unexpected error parsing generator row: {row}. Error: {e}", exc_info=True)
        # --- End Parse Generators --- 

        # --- Add Delivery and Seasonal Config --- 
        catalog["delivery"] = config_parsed.get("delivery", {})
        catalog["seasonal_multipliers"] = config_parsed.get("seasonal_multipliers", {})

        logger.info(f"Parsed pricing catalog: {len(catalog.get('products', {}))} products, {len(catalog.get('generators', {}))} generators.")
        return catalog

    # Rename original sync method
    async def sync_full_catalog_to_redis(self, background_tasks: Optional[BackgroundTasks] = None) -> bool: # Add optional background_tasks
        """
        Fetches pricing data, config, and branches from Google Sheets
        and updates the respective Redis caches. Logs errors via background tasks if provided.
        Returns True if all essential syncs were successful, False otherwise.
        """
        logger.info("Starting full sync from Google Sheets (Pricing, Config, Branches)...")
        if not self.sheet_service:
            logger.error("Cannot sync: Google Sheets service not initialized.")
            return False

        # Fetch all required data concurrently
        fetch_tasks = {
            "products": self._fetch_sheet_data(settings.GOOGLE_SHEET_ID, settings.GOOGLE_SHEET_PRODUCTS_TAB_NAME),
            "generators": self._fetch_sheet_data(settings.GOOGLE_SHEET_ID, settings.GOOGLE_SHEET_GENERATORS_TAB_NAME),
            "config": self._fetch_sheet_data(settings.GOOGLE_SHEET_ID, settings.GOOGLE_SHEET_CONFIG_RANGE),
            "branches": self._fetch_sheet_data(settings.GOOGLE_SHEET_ID, settings.GOOGLE_SHEET_BRANCHES_RANGE)
        }
        results = await asyncio.gather(*fetch_tasks.values(), return_exceptions=True)
        
        fetched_data = {}
        critical_fetch_error = False
        for i, key in enumerate(fetch_tasks.keys()):
            if isinstance(results[i], Exception):
                error_msg = f"Error fetching data for '{key}': {results[i]}"
                logger.error(error_msg, exc_info=results[i])
                fetched_data[key] = None
                # Log fetch errors using background task if available
                if background_tasks:
                    background_tasks.add_task(log_error_bg, self.redis_service, f"SheetFetchError_{key}", str(results[i]), {"sheet_id": settings.GOOGLE_SHEET_ID, "range": fetch_tasks[key].cr_frame.f_locals.get('range_name', 'N/A')}) # Attempt to get range
                if key != 'config':
                     critical_fetch_error = True
            else:
                fetched_data[key] = results[i]

        # --- Branch Sync ---
        branches_data = fetched_data.get("branches")
        branches_synced = False
        if branches_data is not None:
            try:
                parsed_branches = self._parse_branches(branches_data)
                branches_synced = await self.redis_service.set_json(BRANCH_LIST_CACHE_KEY, parsed_branches)
                if branches_synced:
                    logger.info(f"Successfully synced {len(parsed_branches)} branches to Redis key '{BRANCH_LIST_CACHE_KEY}'")
                else:
                    error_msg = f"Failed to store branches in Redis key '{BRANCH_LIST_CACHE_KEY}'."
                    logger.error(error_msg)
                    if background_tasks:
                        background_tasks.add_task(log_error_bg, self.redis_service, "RedisStoreError", error_msg, {"key": BRANCH_LIST_CACHE_KEY})
                    critical_fetch_error = True
            except Exception as e:
                error_msg = "Error processing or caching branches"
                logger.exception(error_msg, exc_info=e)
                if background_tasks:
                    background_tasks.add_task(log_error_bg, self.redis_service, "BranchProcessingError", str(e))
                critical_fetch_error = True
        elif not critical_fetch_error:
             error_msg = f"Failed to fetch branch data from Google Sheets range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'. Branch sync aborted."
             logger.error(error_msg)
             # Already logged fetch error above if background_tasks was provided
             critical_fetch_error = True

        # --- Pricing Catalog Sync (Products, Generators, Config) ---
        pricing_synced = False
        if fetched_data["products"] is None or fetched_data["generators"] is None:
            error_msg = "Failed to fetch required product/generator data. Pricing catalog sync aborted."
            logger.error(error_msg)
            # Already logged fetch error above if background_tasks was provided
            critical_fetch_error = True
        elif not critical_fetch_error:
            config_data = fetched_data.get("config", [])
            if config_data is None: config_data = []
            try:
                parsed_config = self._parse_delivery_and_config(config_data)
                pricing_catalog = self._parse_pricing_data(
                    fetched_data["products"], 
                    fetched_data["generators"],
                    parsed_config
                )
                pricing_synced = await self.redis_service.set_json(PRICING_CATALOG_CACHE_KEY, pricing_catalog)
                if pricing_synced:
                    logger.info(f"Successfully synced pricing catalog to Redis key '{PRICING_CATALOG_CACHE_KEY}'")
                else:
                    error_msg = f"Failed to store pricing catalog in Redis key '{PRICING_CATALOG_CACHE_KEY}'."
                    logger.error(error_msg)
                    if background_tasks:
                         background_tasks.add_task(log_error_bg, self.redis_service, "RedisStoreError", error_msg, {"key": PRICING_CATALOG_CACHE_KEY})
                    critical_fetch_error = True
            except Exception as e:
                error_msg = "Error processing or caching pricing catalog"
                logger.exception(error_msg, exc_info=e)
                if background_tasks:
                     background_tasks.add_task(log_error_bg, self.redis_service, "CatalogProcessingError", str(e))
                critical_fetch_error = True

        final_success = branches_synced and pricing_synced
        if final_success:
             # Log successful sync timestamp
             await self.redis_service.set("sync:last_successful_timestamp", datetime.now().isoformat())
        else:
             logger.error(f"Overall sync failed. Branches Synced: {branches_synced}, Pricing Synced: {pricing_synced}")
        return final_success

    async def _run_sync_loop(self):
        """Periodically runs the full sync process."""
        logger.info(f"Starting background sync loop (Interval: {SYNC_INTERVAL_SECONDS}s)")
        while True:
            try:
                # Create BackgroundTasks instance for logging within the loop run
                bg_tasks = BackgroundTasks()
                await self.sync_full_catalog_to_redis(background_tasks=bg_tasks)
                # Note: background tasks are scheduled but not awaited here
            except Exception as e:
                logger.exception("Unhandled exception directly in sync loop runner", exc_info=e)
                # Log this critical loop error if possible (might need direct Redis access)
                try:
                    await log_error_bg(self.redis_service, "SyncLoopError", str(e))
                except Exception as log_e:
                    logger.error(f"Failed to log sync loop error to Redis: {log_e}")

            await asyncio.sleep(SYNC_INTERVAL_SECONDS)

    async def start_background_sync(self):
        """Starts the background sync task if not already running."""
        if self._sync_task is None or self._sync_task.done():
            logger.info("Performing initial sync...")
            bg_tasks = BackgroundTasks()
            initial_sync_success = await self.sync_full_catalog_to_redis(background_tasks=bg_tasks)
            if not initial_sync_success:
                 logger.warning("Initial sync failed. Background sync will still start and retry.")
            self._sync_task = asyncio.create_task(self._run_sync_loop())
            logger.info("Background pricing sync task started.")
        else:
            logger.info("Background pricing sync task already running.")

    async def stop_background_sync(self):
        """Stops the background sync task if running."""
        if self._sync_task and not self._sync_task.done():
            logger.info("Stopping background sync task...")
            self._sync_task.cancel()
            try:
                await self._sync_task
                logger.info("Background sync task stopped gracefully.")
            except Exception as e:
                logger.warning("Background sync task did not stop gracefully: {e}. It may still be running.", exc_info=e)
        else:
            logger.info("No active background sync task to stop.")

# --- Integration with FastAPI Lifespan ---

_sheet_sync_service_instance: Optional[SheetSyncService] = None

async def lifespan_startup(redis_service: RedisService):
    """Lifespan startup event: Initialize and start sheet sync."""
    global _sheet_sync_service_instance
    if _sheet_sync_service_instance is None:
        logger.info("Initializing SheetSyncService during startup...")
        try:
            _sheet_sync_service_instance = SheetSyncService(redis_service)
            # Start the background sync task
            await _sheet_sync_service_instance.start_background_sync()
        except Exception as e:
            logger.exception("Failed to initialize or start SheetSyncService during startup", exc_info=e)
            # Decide if the app should fail to start if sync setup fails
            # raise RuntimeError("Sheet Sync Service failed to start") from e
    else:
        logger.info("SheetSyncService already initialized.")

async def lifespan_shutdown():
    """Lifespan shutdown event: Stop sheet sync."""
    global _sheet_sync_service_instance
    if _sheet_sync_service_instance:
        logger.info("Stopping SheetSyncService during shutdown...")
        # Stop the background sync task
        await _sheet_sync_service_instance.stop_background_sync()
        _sheet_sync_service_instance = None
        logger.info("SheetSyncService stopped.")
    else:
        logger.info("SheetSyncService not initialized or already stopped.")
