# filepath: /home/femar/AO3/Stahla/app/services/quote/sync.py
import asyncio
import logging # Keep for general logging if needed
import re
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import json # Added for HttpError details

import logfire # Import logfire directly
from fastapi import BackgroundTasks

from app.core.config import settings
from app.services.redis.redis import RedisService, get_redis_service # Import get_redis_service
from app.models.location import BranchLocation
from app.services.dash.background import log_error_bg
from app.services.quote.auth import create_sheets_service # Import the new service creator

# Constants
# SCOPES is now managed within auth.py
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
            logfire.warning(f"Could not convert currency string '{value}' to float.")
            return None
    return None

class SheetSyncService:
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        logfire.info("SheetSyncService: Initializing (service object will be built asynchronously).")
        self.sheet_service = None # Initialize as None
        self._sync_task: Optional[asyncio.Task] = None
        # Removed service creation from __init__

    async def initialize_service(self):
        """Asynchronously initializes the Google Sheets service client by running the synchronous creation function in an executor."""
        logfire.info("SheetSyncService: Attempting to build sheet service via auth.py (in executor)...")
        loop = asyncio.get_running_loop()
        try:
            # Run the synchronous create_sheets_service function in the default executor
            self.sheet_service = await loop.run_in_executor(
                None, 
                create_sheets_service, 
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
            logfire.info("SheetSyncService: Sheet service built successfully via auth.py (in executor).")
        except Exception as e:
            logfire.error(f"SheetSyncService: CRITICAL - Failed during initialize_service while creating sheet service: {e}", exc_info=True)
            # Re-raise the exception to ensure startup fails if service creation fails critically here
            raise

    async def _fetch_sheet_data(self, sheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        """Fetches data from a specific sheet and range."""
        if not self.sheet_service:
            logfire.error("SheetSyncService: Cannot fetch sheet data - Google Sheets service not initialized.")
            return None
        # self.sheet_service.http should be the AuthorizedSession instance.
            
        try:
            logfire.info(f"SheetSyncService: Attempting to fetch data from GSheet ID '{sheet_id}', range '{range_name}'.")
            # Removed the check for self.sheet_service.http as it's not reliably populated
            # when using default transport handling but the service still works.

            sheet = self.sheet_service.spreadsheets()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute
            )
            values = result.get('values', [])
            logfire.info(f"SheetSyncService: Successfully fetched {len(values)} rows from range '{range_name}'")
            # Add debug logging for the fetched data itself
            logfire.debug(f"SheetSyncService: Fetched data for range '{range_name}': {values}")
            return values
        except Exception as err: # Catching generic Exception as HttpError might be wrapped
            # Log HttpError specifically if possible, otherwise generic error
            from googleapiclient.errors import HttpError # Local import for type checking
            if isinstance(err, HttpError):
                err_reason = err._get_reason() if hasattr(err, '_get_reason') else 'Unknown reason'
                err_status = err.resp.status if hasattr(err, 'resp') and hasattr(err.resp, 'status') else 'N/A'
                logfire.error(f"SheetSyncService: Google Sheets API error fetching range '{range_name}': {err_status} - {err_reason}")
                try:
                    error_details = json.loads(err.content.decode()) # type: ignore
                    logfire.error(f"SheetSyncService: Google API Error Details: {error_details}")
                except: 
                    logfire.error(f"SheetSyncService: Google API Raw Error Content: {err.content}")
            else:
                logfire.error(f"SheetSyncService: Unexpected error fetching sheet data for range '{range_name}' - {err}", exc_info=True)
            return None

    def _parse_branches(self, branches_data: List[List[Any]]) -> List[Dict[str, Any]]: # Return type matches BranchLocation.model_dump()
        """
        Parses raw sheet data from the 'branches' tab into a structured list of branch locations.
        Assumes the fetched branches_data includes the header row.
        - Column 1 (index 0): Branch Name
        - Column 2 (index 1): Branch Full Address
        """
        branches = []
        if not branches_data or len(branches_data) < 2: # Expect header + at least one data row
            logfire.warning(f"No data or insufficient rows (expected header + data) provided to _parse_branches for range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'. Branch list will be empty.")
            return branches

        # Skip the header row (index 0)
        data_rows = branches_data[1:]

        for i, row in enumerate(data_rows): # Iterate over data rows only
            if len(row) >= 2 and row[0] and row[1]: # Ensure at least two columns with data
                try:
                    branch_name = str(row[0]).strip()
                    branch_address = str(row[1]).strip()
                    # Validate and create BranchLocation before converting to dict
                    branch = BranchLocation(name=branch_name, address=branch_address)
                    branches.append(branch.model_dump()) # Store as dict for JSON serialization
                except Exception as e: # Catch validation errors from BranchLocation or other issues
                    # Log index relative to data_rows (add 1 for 1-based index, add 1 again for skipped header)
                    logfire.warning(f"Skipping branch row {i+2} (original sheet row) due to parsing/validation error: {row}. Error: {e}")
            else:
                 # Log index relative to data_rows (add 1 for 1-based index, add 1 again for skipped header)
                 logfire.warning(f"Skipping incomplete branch row {i+2} (original sheet row): {row}. Expected at least 2 columns.")
        
        logfire.info(f"SheetSyncService: Parsed {len(branches)} branches from sheet range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'.")
        return branches

    def _parse_delivery_and_config(self, config_data: List[List[Any]]) -> Dict[str, Any]:
        """
        Parses raw sheet data from the config tab (expected Key, Value columns)
        into a structured delivery and seasonal config.
        """
        # Default structure
        parsed_config = {
            "delivery": {
                "base_fee": 100.0, # Default
                "per_mile_rate": 3.50, # Default
                "free_miles_threshold": 50, # Default
            },
            "seasonal_multipliers": {
                "standard": 1.0, # Default standard rate
                "tiers": [] # List to hold seasonal tier definitions
            }
        }

        if not config_data or len(config_data) < 2: # Expect header + at least one data row
            logfire.warning(f"No data or insufficient rows in config_data for range '{CONFIG_DATA_RANGE}'. Using default delivery/seasonal settings.")
            return parsed_config

        # Assuming first row is header ("Key", "Value") and is skipped by the sheet range or handled here
        # If range already skips header, use config_data directly. If header is present, slice from 1: config_data[1:]
        data_rows = config_data
        if str(data_rows[0][0]).strip().lower() == 'key': # Check if header is present
            data_rows = config_data[1:]

        raw_key_values: Dict[str, Any] = {}
        for i, row in enumerate(data_rows):
            if len(row) >= 2 and row[0] and isinstance(row[0], str):
                key = str(row[0]).strip().lower()
                value = row[1]
                raw_key_values[key] = value
            else:
                logfire.warning(f"Skipping invalid config row {i+1}: {row}. Expected Key and Value.")
        
        logfire.debug(f"Raw key-values from config sheet: {raw_key_values}")

        # Populate delivery settings
        parsed_config["delivery"]["base_fee"] = _clean_currency(raw_key_values.get('delivery base fee', parsed_config["delivery"]["base_fee"]))
        parsed_config["delivery"]["per_mile_rate"] = _clean_currency(raw_key_values.get('delivery per mile rate', parsed_config["delivery"]["per_mile_rate"]))
        free_miles_raw = raw_key_values.get('delivery free miles threshold', parsed_config["delivery"]["free_miles_threshold"])
        try:
            parsed_config["delivery"]["free_miles_threshold"] = int(free_miles_raw) if free_miles_raw is not None else parsed_config["delivery"]["free_miles_threshold"]
        except (ValueError, TypeError):
             logfire.warning(f"Could not parse 'delivery free miles threshold': {free_miles_raw}. Using default: {parsed_config['delivery']['free_miles_threshold']}")

        # Populate seasonal multipliers
        # Example for 'Premium' tier
        premium_start_str = raw_key_values.get('seasonal multiplier premium start')
        premium_end_str = raw_key_values.get('seasonal multiplier premium end')
        premium_rate = _clean_currency(raw_key_values.get('seasonal multiplier premium rate'))
        if premium_start_str and premium_end_str and premium_rate is not None:
            try:
                start_date = datetime.strptime(str(premium_start_str), '%Y-%m-%d').date()
                end_date = datetime.strptime(str(premium_end_str), '%Y-%m-%d').date()
                parsed_config["seasonal_multipliers"]["tiers"].append({
                    "name": "Premium",
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "rate": premium_rate
                })
            except (ValueError, TypeError) as e:
                logfire.warning(f"Could not parse 'Premium' seasonal tier dates/rate from config: {e}")

        # Example for 'Premium Plus' tier - adapt for other tiers as needed
        pp_start_str = raw_key_values.get('seasonal multiplier premium plus start')
        pp_end_str = raw_key_values.get('seasonal multiplier premium plus end')
        pp_rate = _clean_currency(raw_key_values.get('seasonal multiplier premium plus rate'))
        if pp_start_str and pp_end_str and pp_rate is not None:
            try:
                start_date = datetime.strptime(str(pp_start_str), '%Y-%m-%d').date()
                end_date = datetime.strptime(str(pp_end_str), '%Y-%m-%d').date()
                parsed_config["seasonal_multipliers"]["tiers"].append({
                    "name": "Premium Plus",
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "rate": pp_rate
                })
            except (ValueError, TypeError) as e:
                logfire.warning(f"Could not parse 'Premium Plus' seasonal tier dates/rate from config: {e}")
        
        # Standard multiplier (if defined in sheet, otherwise default is used)
        std_multiplier = _clean_currency(raw_key_values.get('seasonal multiplier standard'))
        if std_multiplier is not None:
            parsed_config["seasonal_multipliers"]["standard"] = std_multiplier

        logfire.info(f"SheetSyncService: Parsed delivery config: {parsed_config['delivery']}")
        logfire.info(f"SheetSyncService: Parsed seasonal multipliers: {parsed_config['seasonal_multipliers']}")
        return parsed_config

    def _parse_pricing_data(self, products_data: List[List[Any]], generators_data: List[List[Any]], config_parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses raw sheet data from 'products' and 'generators' tabs into a structured pricing catalog.
        Incorporates delivery and seasonal config. Branches are handled separately.
        """
        catalog = {"products": {}, "generators": {}}

        # --- Parse Products (Trailers & Extras from Stahla - products.csv) --- 
        if products_data and len(products_data) > 1: # Expect header + data
            headers = [str(h).strip().lower() for h in products_data[0]]
            logfire.debug(f"Products sheet headers: {headers}")
            # Define expected headers based on Stahla - products.csv
            expected_product_headers = [
                'primary column', 'weekly pricing (7 day)', '28 day rate', '2-5 month rate',
                '6+ month pricing', '18+ month pricing', 'event standard (<4 days)',
                'event premium (<4 days)', 'event premium plus (<4 days)',
                'event premium platinum (<4 days)', 'pump out waste tank',
                'fresh water tank fill', 'cleaning', 'restocking'
            ]
            if not all(h in headers for h in ['primary column', 'weekly pricing (7 day)']): # Basic check
                logfire.error(f"Missing essential headers in products sheet. Expected at least 'primary column' and 'weekly pricing (7 day)'. Found: {headers}")
            else:
                for row_idx, row in enumerate(products_data[1:]): # Skip header row
                    if not row or not row[0] or not str(row[0]).strip(): # Check for empty or invalid row
                        logfire.warning(f"Skipping empty or invalid product row at index {row_idx + 1}")
                        continue
                    
                    product_id = str(row[0]).strip() # 'Primary Column' is the ID/Name
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
                    except IndexError:
                        logfire.warning(f"Skipping product row '{product_id}' due to missing columns (IndexError). Row data: {row}")
                    except ValueError as ve:
                        logfire.warning(f"Skipping product row '{product_id}' due to value error: {ve}. Row data: {row}")
                    except Exception as e:
                         logfire.error(f"Unexpected error parsing product row '{product_id}': {e}. Row data: {row}", exc_info=True)
        # --- End Parse Products --- 

        # --- Parse Generators (from Stahla - generators.csv) --- 
        if generators_data and len(generators_data) > 1: # Expect header + data
            headers = [str(h).strip().lower() for h in generators_data[0]]
            logfire.debug(f"Generators sheet headers: {headers}")
            expected_generator_headers = ['generator rental', 'event (< 3 day rate)', '7 day rate', '28 day rate']
            
            if not all(h in headers for h in expected_generator_headers):
                 logfire.error(f"Missing essential headers in generators sheet. Expected: {expected_generator_headers}. Found: {headers}")
            else:
                for row_idx, row in enumerate(generators_data[1:]): # Skip header row
                    if not row or not row[0] or not str(row[0]).strip():
                        logfire.warning(f"Skipping empty or invalid generator row at index {row_idx + 1}")
                        continue

                    raw_name = str(row[headers.index('generator rental')]).strip()
                    # Attempt to extract an ID like (GEN-3KW) if present
                    gen_id_match = re.search(r'\((GEN-\w+)\)', raw_name)
                    gen_id = gen_id_match.group(1) if gen_id_match else raw_name # Use full name as ID if no specific ID found
                    gen_name = raw_name # Keep full name for description

                    generator_entry = {"id": gen_id, "name": gen_name}
                    try:
                        generator_entry['rate_event'] = _clean_currency(row[headers.index('event (< 3 day rate)')])
                        generator_entry['rate_7_day'] = _clean_currency(row[headers.index('7 day rate')])
                        generator_entry['rate_28_day'] = _clean_currency(row[headers.index('28 day rate')])
                        catalog["generators"][gen_id] = generator_entry
                    except IndexError:
                        logfire.warning(f"Skipping generator '{gen_name}' due to missing columns (IndexError). Row data: {row}")
                    except ValueError as ve:
                        logfire.warning(f"Skipping generator '{gen_name}' due to value error: {ve}. Row data: {row}")
                    except Exception as e:
                        logfire.error(f"Unexpected error parsing generator '{gen_name}': {e}. Row data: {row}", exc_info=True)
        # --- End Parse Generators --- 

        # --- Add Delivery and Seasonal Config --- 
        catalog["delivery"] = config_parsed.get("delivery", {})
        catalog["seasonal_multipliers"] = config_parsed.get("seasonal_multipliers", {})

        logfire.info(f"SheetSyncService: Parsed pricing catalog: {len(catalog.get('products', {}))} products, {len(catalog.get('generators', {}))} generators.")
        return catalog

    async def sync_full_catalog_to_redis(self, background_tasks: Optional[BackgroundTasks] = None) -> bool:
        logfire.info("SheetSyncService: Starting full sync to Redis (Pricing, Config, Branches) - SEQUENTIAL FETCH.")
        if not self.sheet_service:
            logfire.error("SheetSyncService: Cannot sync - Google Sheets service not initialized.")
            return False

        fetched_data = {}
        critical_fetch_error = False
        fetch_order = [
            ("products", settings.GOOGLE_SHEET_PRODUCTS_TAB_NAME),
            ("generators", settings.GOOGLE_SHEET_GENERATORS_TAB_NAME),
            ("config", settings.GOOGLE_SHEET_CONFIG_RANGE),
            ("branches", settings.GOOGLE_SHEET_BRANCHES_RANGE)
        ]

        # Fetch data sequentially
        for key, range_name in fetch_order:
            logfire.info(f"--- Starting fetch for: {key} ({range_name}) ---")
            try:
                data = await self._fetch_sheet_data(settings.GOOGLE_SHEET_ID, range_name)
                fetched_data[key] = data
                if data is None:
                    # _fetch_sheet_data already logs errors, but we mark critical if not config
                    logfire.error(f"Fetch for '{key}' returned None.")
                    if key != 'config': # Allow config fetch to fail without blocking others initially
                        critical_fetch_error = True
                else:
                    logfire.info(f"--- Successfully fetched data for: {key} ---")
            except Exception as e:
                error_msg = f"Exception during fetch for '{key}': {e}"
                logfire.error(error_msg, exc_info=True)
                fetched_data[key] = None
                if background_tasks:
                    background_tasks.add_task(log_error_bg, self.redis_service, f"SheetFetchError_{key}", str(e), {"sheet_id": settings.GOOGLE_SHEET_ID, "range": range_name})
                if key != 'config':
                    critical_fetch_error = True
            
            # Optional: Short delay between fetches if needed for rate limiting, though unlikely necessary here
            # await asyncio.sleep(0.1)

        # --- Branch Sync ---
        branches_data = fetched_data.get("branches")
        branches_synced_successfully = False # Changed variable name for clarity
        if branches_data is not None: # Fetch was successful (data might be empty list)
            try:
                parsed_branches = self._parse_branches(branches_data)
                # Attempt to store the parsed list (even if empty) to reflect sheet state
                if await self.redis_service.set_json(BRANCH_LIST_CACHE_KEY, parsed_branches):
                    logfire.info(f"SheetSyncService: BRANCH SYNC SUCCESS - Synced {len(parsed_branches)} branches to Redis '{BRANCH_LIST_CACHE_KEY}'.")
                    branches_synced_successfully = True
                else: # redis.set_json failed
                    error_msg = f"Failed to store branches in Redis key '{BRANCH_LIST_CACHE_KEY}'."
                    logfire.error(f"SheetSyncService: BRANCH SYNC ERROR - {error_msg}")
                    if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "RedisStoreError", error_msg, {"key": BRANCH_LIST_CACHE_KEY})
                    critical_fetch_error = True
            except Exception as e: # Error during _parse_branches or the set_json call itself
                error_msg = f"BRANCH SYNC ERROR: Error processing or caching branches. Redis key '{BRANCH_LIST_CACHE_KEY}' may NOT have been created/updated."
                logfire.exception(error_msg, exc_info=e)
                if background_tasks:
                    background_tasks.add_task(log_error_bg, self.redis_service, "BranchProcessingError", str(e))
                critical_fetch_error = True
        elif not critical_fetch_error: # This means branches_data was None (fetch failed) AND no other critical fetch error occurred before this check
             error_msg = f"BRANCH SYNC ERROR: Failed to fetch branch data from Google Sheets range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'. Branch sync aborted."
             logfire.error(error_msg)
             critical_fetch_error = True
        else: # branches_data was None and some other critical_fetch_error already occurred
            logfire.warning(f"BRANCH SYNC SKIPPED: Due to earlier critical fetch error or failed branch data fetch.")

        # --- Pricing Catalog Sync (Products, Generators, Config) ---
        pricing_synced_successfully = False
        if fetched_data["products"] is None or fetched_data["generators"] is None:
            error_msg = "PRICING SYNC ERROR: Failed to fetch required product/generator data. Pricing catalog sync aborted."
            logfire.error(error_msg)
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
                if await self.redis_service.set_json(PRICING_CATALOG_CACHE_KEY, pricing_catalog):
                    logfire.info(f"SheetSyncService: PRICING SYNC SUCCESS - Synced pricing catalog to Redis '{PRICING_CATALOG_CACHE_KEY}'.")
                    pricing_synced_successfully = True
                else:
                    error_msg = f"Failed to store pricing catalog in Redis key '{PRICING_CATALOG_CACHE_KEY}'."
                    logfire.error(f"SheetSyncService: PRICING SYNC ERROR - {error_msg}")
                    if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "RedisStoreError", error_msg, {"key": PRICING_CATALOG_CACHE_KEY})
                    critical_fetch_error = True
            except Exception as e:
                error_msg = "PRICING SYNC ERROR: Error processing or caching pricing catalog"
                logfire.exception(error_msg, exc_info=e)
                if background_tasks:
                     background_tasks.add_task(log_error_bg, self.redis_service, "CatalogProcessingError", str(e))
                critical_fetch_error = True
        else:
            logfire.warning(f"PRICING SYNC SKIPPED: Due to earlier critical fetch error or failed product/generator data fetch.")

        final_success = branches_synced_successfully and pricing_synced_successfully
        if final_success:
             await self.redis_service.set("sync:last_successful_timestamp", datetime.now().isoformat())
             logfire.info(f"SheetSyncService: OVERALL SYNC SUCCESS - Branches: {branches_synced_successfully}, Pricing: {pricing_synced_successfully}")
        else:
             logfire.error(f"SheetSyncService: OVERALL SYNC FAILED - Branches: {branches_synced_successfully}, Pricing: {pricing_synced_successfully}. Check logs.")
        return final_success

    async def _run_sync_loop(self):
        logfire.info(f"SheetSyncService: Starting background sync loop (Interval: {SYNC_INTERVAL_SECONDS}s)")
        loop = asyncio.get_running_loop() # Get loop once for the loop
        while True:
            try:
                # Re-create the sheet service before each sync attempt in the loop,
                # using an executor to avoid blocking the loop if creation is slow.
                logfire.info("SheetSyncService: Re-building sheet service for periodic sync (in executor)...")
                try:
                    self.sheet_service = await loop.run_in_executor(
                        None,
                        create_sheets_service, 
                        settings.GOOGLE_APPLICATION_CREDENTIALS
                    )
                    logfire.info("SheetSyncService: Sheet service re-built successfully for periodic sync (in executor).")
                except Exception as build_err:
                    logfire.error(f"SheetSyncService: Failed to re-build sheet service in loop: {build_err}", exc_info=True)
                    # Skip this sync cycle if service cannot be built
                    await asyncio.sleep(SYNC_INTERVAL_SECONDS)
                    continue 

                bg_tasks = BackgroundTasks()
                await self.sync_full_catalog_to_redis(background_tasks=bg_tasks)
            except Exception as e:
                logfire.error(f"SheetSyncService: Unhandled exception in sync loop runner - {e}", exc_info=True)
                try:
                    await log_error_bg(self.redis_service, "SyncLoopError", str(e))
                except Exception as log_e:
                    logfire.error(f"SheetSyncService: Failed to log sync loop error to Redis - {log_e}")
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)

    async def _perform_initial_sync(self):
        """Wrapper to perform and log the initial sync as a background task."""
        logfire.info("SheetSyncService: Initial sync task started in background.")
        bg_tasks_for_initial_sync = BackgroundTasks() # For logging within this specific sync run
        try:
            initial_sync_success = await self.sync_full_catalog_to_redis(background_tasks=bg_tasks_for_initial_sync)
            if not initial_sync_success:
                logfire.warning("SheetSyncService: Initial sync performed in background failed. Subsequent syncs will retry.")
            else:
                logfire.info("SheetSyncService: Initial sync performed in background completed successfully.")
        except Exception as e:
            logfire.error(f"SheetSyncService: Exception during initial background sync: {e}", exc_info=True)
            # Optionally log this critical error to Redis as well
            try:
                await log_error_bg(self.redis_service, "InitialSyncError", str(e))
            except Exception as log_e:
                logfire.error(f"Failed to log initial sync error to Redis: {log_e}")

    async def start_background_sync(self):
        """Starts the background sync task if not already running. Initial sync is handled separately."""
        if self._sync_task is None or self._sync_task.done():
            logfire.info("SheetSyncService: Starting background sync loop task.")
            # Removed: Scheduling of initial sync from here. It's now handled in lifespan_startup.

            # Start the periodic background sync loop
            self._sync_task = asyncio.create_task(self._run_sync_loop())
            logfire.info("SheetSyncService: Background sync loop task created and started.")
        else:
            logfire.info("SheetSyncService: Background sync task is already running.")

    async def stop_background_sync(self):
        """Stops the background sync task if running."""
        if self._sync_task and not self._sync_task.done():
            logfire.info("SheetSyncService: Stopping background sync task...")
            self._sync_task.cancel()
            try:
                await self._sync_task
                logfire.info("SheetSyncService: Background sync task stopped gracefully.")
            except Exception as e:
                logfire.warning("SheetSyncService: Background sync task did not stop gracefully: {e}. It may still be running.", exc_info=e)
        else:
            logfire.info("SheetSyncService: No active background sync task to stop.")

# --- Integration with FastAPI Lifespan ---

_sheet_sync_service_instance: Optional[SheetSyncService] = None

async def _run_initial_sync_after_delay(service_instance: SheetSyncService, delay_seconds: int):
    """Helper coroutine to wait and then run the initial sync."""
    logfire.info(f"Initial sync scheduled to run after {delay_seconds} seconds.")
    await asyncio.sleep(delay_seconds)
    logfire.info("Delay finished, performing initial sync now.")
    await service_instance._perform_initial_sync()

async def lifespan_startup(): # Remove redis_service parameter
    """Initializes the SheetSyncService and starts background tasks."""
    global _sheet_sync_service_instance
    logfire.info("SYNC LIFESPAN: Attempting to start SheetSyncService...")
    if _sheet_sync_service_instance is None:
        try:
            # Get Redis service instance via dependency injector
            redis_service = await get_redis_service()
            
            _sheet_sync_service_instance = SheetSyncService(redis_service)
            # Await the initialization of the service itself (which builds the google client)
            await _sheet_sync_service_instance.initialize_service()
            # Now start the background sync tasks (which run the first sync in the background after delay)
            await _sheet_sync_service_instance.start_background_sync()
            # Schedule the initial sync to run after a delay in the background
            asyncio.create_task(_run_initial_sync_after_delay(_sheet_sync_service_instance, 30))
            logfire.info("SYNC LIFESPAN: SheetSyncService initialized, background loop started, initial sync scheduled with delay.")
        except RuntimeError as e:
            logfire.error(f"SYNC LIFESPAN: CRITICAL - Failed to get required Redis service: {e}", exc_info=True)
            # Prevent service from being considered initialized if Redis failed
            _sheet_sync_service_instance = None 
        except Exception as e:
            logfire.error(f"SYNC LIFESPAN: CRITICAL - Failed to initialize or start SheetSyncService: {e}", exc_info=True)
            _sheet_sync_service_instance = None # Ensure instance is None on other errors too
    else:
        logfire.info("SYNC LIFESPAN: SheetSyncService already initialized.")

async def lifespan_shutdown():
    global _sheet_sync_service_instance
    if _sheet_sync_service_instance:
        logfire.info("SYNC LIFESPAN: Stopping SheetSyncService...")
        await _sheet_sync_service_instance.stop_background_sync()
        _sheet_sync_service_instance = None
        logfire.info("SYNC LIFESPAN: SheetSyncService stopped.")
    else:
        logfire.info("SYNC LIFESPAN: SheetSyncService not running or already stopped.")
