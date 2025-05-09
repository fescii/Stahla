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
from app.services.mongo.mongo import MongoService, get_mongo_service, SHEET_PRODUCTS_COLLECTION, SHEET_GENERATORS_COLLECTION, SHEET_BRANCHES_COLLECTION, SHEET_CONFIG_COLLECTION # Import MongoService and related
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

# Define header to Pydantic field name mappings
PRODUCT_HEADER_MAP = {
    # ID and Name are sourced from 'Primary Column' based on Stahla - products.csv
    'primary column': 'id',
    # 'name' will default to the value from the 'id' field (i.e., 'Primary Column')
    # as there isn't a separate column designated for product name in the CSV.

    # Pricing fields (lowercase header from sheet -> Pydantic field name)
    'weekly pricing (7 day)': 'weekly_7_day',
    '28 day rate': 'rate_28_day',
    '2-5 month rate': 'rate_2_5_month',
    '6+ month pricing': 'rate_6_plus_month',
    '18+ month pricing': 'rate_18_plus_month',
    'event standard (<4 days)': 'event_standard',
    'event premium (<4 days)': 'event_premium',
    'event premium plus (<4 days)': 'event_premium_plus',
    'event premium platinum (<4 days)': 'event_premium_platinum',
}

GENERATOR_HEADER_MAP = {
    # ID and Name are sourced from 'Generator Rental' based on Stahla - generators.csv
    'generator rental': 'id',
    # 'name' will default to the value from the 'id' field (i.e., 'Generator Rental').

    # Pricing fields
    'event (< 3 day rate)': 'rate_event',
    '7 day rate': 'rate_7_day',
    '28 day rate': 'rate_28_day',
}

# List of known extra service headers (lowercase) from 'Stahla - products.csv'
# These will be put into the 'extras' dictionary for products.
KNOWN_PRODUCT_EXTRAS_HEADERS = [
    'pump out waste tank', 
    'fresh water tank fill', 
    'cleaning', 
    'restocking'
]

class SheetSyncService:
    def __init__(self, redis_service: RedisService, mongo_service: MongoService): # Add mongo_service
        self.redis_service = redis_service
        self.mongo_service = mongo_service # Store mongo_service
        logfire.info("SheetSyncService: Initializing (service object will be built asynchronously).")
        self.sheet_service = None # Initialize as None
        self._sync_task: Optional[asyncio.Task] = None

    async def initialize_service(self):
        """Asynchronously initializes the Google Sheets service client by running the synchronous creation function in an executor."""
        logfire.info("SheetSyncService: Attempting to build sheet service via auth.py (in executor)...")
        loop = asyncio.get_running_loop()
        try:
            self.sheet_service = await loop.run_in_executor(
                None, 
                create_sheets_service, 
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
            logfire.info("SheetSyncService: Sheet service built successfully via auth.py (in executor).")
        except Exception as e:
            logfire.error(f"SheetSyncService: CRITICAL - Failed during initialize_service while creating sheet service: {e}", exc_info=True)
            raise

    async def _fetch_sheet_data(self, sheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        """Fetches data from a specific sheet and range."""
        if not self.sheet_service:
            logfire.error("SheetSyncService: Cannot fetch sheet data - Google Sheets service not initialized.")
            return None
            
        try:
            logfire.info(f"SheetSyncService: Attempting to fetch data from GSheet ID '{sheet_id}', range '{range_name}'.")
            sheet = self.sheet_service.spreadsheets()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute
            )
            values = result.get('values', [])
            logfire.info(f"SheetSyncService: Successfully fetched {len(values)} rows from range '{range_name}'")
            logfire.debug(f"SheetSyncService: Fetched data for range '{range_name}': {values}")
            return values
        except Exception as err:
            from googleapiclient.errors import HttpError
            if isinstance(err, HttpError):
                err_reason = err._get_reason() if hasattr(err, '_get_reason') else 'Unknown reason'
                err_status = err.resp.status if hasattr(err, 'resp') and hasattr(err.resp, 'status') else 'N/A'
                logfire.error(f"SheetSyncService: Google Sheets API error fetching range '{range_name}': {err_status} - {err_reason}")
                try:
                    error_details = json.loads(err.content.decode())
                    logfire.error(f"SheetSyncService: Google API Error Details: {error_details}")
                except: 
                    logfire.error(f"SheetSyncService: Google API Raw Error Content: {err.content}")
            else:
                logfire.error(f"SheetSyncService: Unexpected error fetching sheet data for range '{range_name}' - {err}", exc_info=True)
            return None

    def _parse_branches(self, branches_data: List[List[Any]]) -> List[Dict[str, Any]]:
        branches = []
        if not branches_data or len(branches_data) < 2:
            logfire.warning(f"No data or insufficient rows (expected header + data) provided to _parse_branches for range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'. Branch list will be empty.")
            return branches

        data_rows = branches_data[1:]

        for i, row in enumerate(data_rows):
            if len(row) >= 2 and row[0] and row[1]:
                try:
                    branch_name = str(row[0]).strip()
                    branch_address = str(row[1]).strip()
                    branch = BranchLocation(name=branch_name, address=branch_address)
                    branches.append(branch.model_dump())
                except Exception as e:
                    logfire.warning(f"Skipping branch row {i+2} (original sheet row) due to parsing/validation error: {row}. Error: {e}")
            else:
                 logfire.warning(f"Skipping incomplete branch row {i+2} (original sheet row): {row}. Expected at least 2 columns.")
        
        logfire.info(f"SheetSyncService: Parsed {len(branches)} branches from sheet range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'.")
        return branches

    def _parse_delivery_and_config(self, config_data: List[List[Any]]) -> Dict[str, Any]:
        parsed_config = {
            "delivery": {
                "base_fee": 100.0,
                "per_mile_rate": 3.50,
                "free_miles_threshold": 50,
            },
            "seasonal_multipliers": {
                "standard": 1.0,
                "tiers": []
            }
        }

        if not config_data or len(config_data) < 2:
            logfire.warning(f"No data or insufficient rows in config_data for range '{CONFIG_DATA_RANGE}'. Using default delivery/seasonal settings.")
            return parsed_config

        data_rows = config_data
        if str(data_rows[0][0]).strip().lower() == 'key':
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

        parsed_config["delivery"]["base_fee"] = _clean_currency(raw_key_values.get('delivery base fee', parsed_config["delivery"]["base_fee"]))
        parsed_config["delivery"]["per_mile_rate"] = _clean_currency(raw_key_values.get('delivery per mile rate', parsed_config["delivery"]["per_mile_rate"]))
        free_miles_raw = raw_key_values.get('delivery free miles threshold', parsed_config["delivery"]["free_miles_threshold"])
        try:
            parsed_config["delivery"]["free_miles_threshold"] = int(free_miles_raw) if free_miles_raw is not None else parsed_config["delivery"]["free_miles_threshold"]
        except (ValueError, TypeError):
            logfire.warning(f"Could not parse 'delivery free miles threshold': {free_miles_raw}. Using default: {parsed_config['delivery']['free_miles_threshold']}")

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
        
        std_multiplier = _clean_currency(raw_key_values.get('seasonal multiplier standard'))
        if std_multiplier is not None:
            parsed_config["seasonal_multipliers"]["standard"] = std_multiplier

        logfire.info(f"SheetSyncService: Parsed delivery config: {parsed_config['delivery']}")
        logfire.info(f"SheetSyncService: Parsed seasonal multipliers: {parsed_config['seasonal_multipliers']}")
        return parsed_config

    def _parse_pricing_data(self, products_data: List[List[Any]], generators_data: List[List[Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        pricing_catalog = {
            "products": {},
            "generators": {},
            "delivery": config.get("delivery", {}),
            "seasonal_multipliers": config.get("seasonal_multipliers", {})
        }

        # --- Parse Products --- 
        if products_data and len(products_data) > 1:
            product_headers_raw = [str(h).strip() for h in products_data[0]]
            product_headers_lower = [h.lower() for h in product_headers_raw]
            logfire.debug(f"Product headers (raw): {product_headers_raw}")

            id_col_idx = -1
            name_col_idx = -1
            
            for idx, header_l in enumerate(product_headers_lower):
                mapped_field = PRODUCT_HEADER_MAP.get(header_l)
                if mapped_field == 'id':
                    id_col_idx = idx
                elif mapped_field == 'name':
                    name_col_idx = idx
            
            if id_col_idx != -1:
                logfire.info(f"Product 'id' field will be sourced from column '{product_headers_raw[id_col_idx]}' (index {id_col_idx}).")
            else:
                logfire.error("CRITICAL: Product 'id' column not found. PRODUCT_HEADER_MAP must map a sheet column to 'id'. Product parsing will likely fail for all rows.")
            
            if name_col_idx != -1:
                logfire.info(f"Product 'name' field will be sourced from column '{product_headers_raw[name_col_idx]}' (index {name_col_idx}).")
            else:
                logfire.warning("Product 'name' column not mapped in PRODUCT_HEADER_MAP. Product names will default to their IDs.")

            for i, row in enumerate(products_data[1:]):
                if id_col_idx == -1 : 
                    if i == 0: logfire.error("Skipping all product parsing as 'id' column mapping is missing in PRODUCT_HEADER_MAP.")
                    break 

                product_id_value = None
                if len(row) > id_col_idx:
                    product_id_value = str(row[id_col_idx]).strip()
                
                if not product_id_value:
                    logfire.warning(f"Skipping product row {i+2} (sheet row): empty or missing ID from mapped 'id' column ('{product_headers_raw[id_col_idx]}' index {id_col_idx}). Row: {row}")
                    continue
                
                product_name_value = product_id_value 
                if name_col_idx != -1 and len(row) > name_col_idx and str(row[name_col_idx]).strip():
                    product_name_value = str(row[name_col_idx]).strip()
                elif name_col_idx != -1 : 
                     logfire.debug(f"Product {product_id_value}: Mapped 'name' column ('{product_headers_raw[name_col_idx]}') is empty. Name defaults to ID.")
                                
                product_entry = {"id": product_id_value, "name": product_name_value, "extras": {}}

                for col_idx_loop, header_l_loop in enumerate(product_headers_lower):
                    if col_idx_loop >= len(row): # Ensure we don't go out of bounds for the current row
                        continue
                    
                    # 1. Skip if this column was already used for the main 'id' or 'name' fields.
                    if col_idx_loop == id_col_idx:
                        continue 
                    if name_col_idx != -1 and col_idx_loop == name_col_idx:
                        continue

                    # 2. Special handling for a column literally named 'primary column'
                    #    IF it was NOT the source for 'id' or 'name' (already handled by above).
                    if header_l_loop == 'primary column':
                        logfire.debug(f"Product {product_id_value}: Explicitly ignoring data from column '{product_headers_raw[col_idx_loop]}' (header: 'primary column') as it's not the designated id/name source and special handling is requested.")
                        continue
                    
                    value_raw = row[col_idx_loop]
                    pydantic_field = PRODUCT_HEADER_MAP.get(header_l_loop)

                    if pydantic_field:
                        # 'id' and 'name' source columns are skipped by prior 'continue' statements.
                        # Thus, pydantic_field here will be for other attributes.
                        if pydantic_field in ['weekly_7_day', 'rate_28_day', 'rate_2_5_month', 'rate_6_plus_month', 'rate_18_plus_month', 'event_standard', 'event_premium', 'event_premium_plus', 'event_premium_platinum']:
                            product_entry[pydantic_field] = _clean_currency(value_raw)
                        else: 
                            # For any other mapped fields that are not currency (and not id/name)
                            product_entry[pydantic_field] = str(value_raw).strip() if value_raw is not None else None
                    elif header_l_loop in KNOWN_PRODUCT_EXTRAS_HEADERS:
                        extra_key = header_l_loop.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace("<", "").replace(">", "")
                        product_entry["extras"][extra_key] = _clean_currency(value_raw)
                
                if not product_entry.get("name"): # Should be set, but as a final fallback
                    logfire.error(f"Product {product_id_value}: Name field is unexpectedly missing after parsing. Defaulting to ID.")
                    product_entry["name"] = product_id_value

                if not product_entry["extras"]: del product_entry["extras"]
                pricing_catalog["products"][product_id_value] = product_entry
            logfire.info(f"SheetSyncService: Parsed {len(pricing_catalog['products'])} products.")
        else:
            logfire.warning("No product data or only headers found for products.")

        # --- Parse Generators ---
        if generators_data and len(generators_data) > 1:
            gen_headers_raw = [str(h).strip() for h in generators_data[0]]
            gen_headers_lower = [h.lower() for h in gen_headers_raw]
            logfire.debug(f"Generator headers (raw): {gen_headers_raw}")

            id_col_idx_gen = -1
            name_col_idx_gen = -1 

            for idx, header_l in enumerate(gen_headers_lower):
                mapped_field = GENERATOR_HEADER_MAP.get(header_l)
                if mapped_field == 'id':
                    id_col_idx_gen = idx
                elif mapped_field == 'name': 
                    name_col_idx_gen = idx
            
            if id_col_idx_gen != -1:
                logfire.info(f"Generator 'id' field will be sourced from column '{gen_headers_raw[id_col_idx_gen]}' (index {id_col_idx_gen}).")
            else:
                logfire.error("CRITICAL: Generator 'id' column not found. GENERATOR_HEADER_MAP must map a sheet column to 'id'. Generator parsing will fail.")

            if name_col_idx_gen != -1:
                 logfire.info(f"Generator 'name' field will be sourced from column '{gen_headers_raw[name_col_idx_gen]}' (index {name_col_idx_gen}).")
            else:
                logfire.warning("Generator 'name' column not mapped in GENERATOR_HEADER_MAP. Generator names will default to their IDs.")


            for i, row in enumerate(generators_data[1:]):
                if id_col_idx_gen == -1:
                    if i == 0: logfire.error("Skipping all generator parsing as 'id' column mapping is missing in GENERATOR_HEADER_MAP.")
                    break

                generator_id_value = None
                if len(row) > id_col_idx_gen:
                    generator_id_value = str(row[id_col_idx_gen]).strip()

                if not generator_id_value:
                    logfire.warning(f"Skipping generator row {i+2}: empty or missing ID from mapped 'id' column ('{gen_headers_raw[id_col_idx_gen]}' index {id_col_idx_gen}). Row: {row}")
                    continue
                
                generator_name_value = generator_id_value 
                if name_col_idx_gen != -1 and len(row) > name_col_idx_gen and str(row[name_col_idx_gen]).strip():
                    generator_name_value = str(row[name_col_idx_gen]).strip()
                elif name_col_idx_gen != -1:
                    logfire.debug(f"Generator {generator_id_value}: Mapped 'name' column ('{gen_headers_raw[name_col_idx_gen]}') is empty. Name defaults to ID.")

                generator_entry = {"id": generator_id_value, "name": generator_name_value}

                for col_idx_loop, header_l_loop in enumerate(gen_headers_lower):
                    if col_idx_loop >= len(row): # Ensure we don't go out of bounds
                        continue
                    
                    # 1. Skip if this column was already used for the main 'id' or 'name' fields.
                    if col_idx_loop == id_col_idx_gen:
                        continue
                    if name_col_idx_gen != -1 and col_idx_loop == name_col_idx_gen:
                        continue

                    # 2. Special handling for a column literally named 'primary column'
                    #    IF it was NOT the source for 'id' or 'name' for generators.
                    if header_l_loop == 'primary column':
                        logfire.debug(f"Generator {generator_id_value}: Explicitly ignoring data from column '{gen_headers_raw[col_idx_loop]}' (header: 'primary column') as it's not the designated id/name source for generators and special handling is requested.")
                        continue
                    
                    value_raw = row[col_idx_loop]
                    pydantic_field = GENERATOR_HEADER_MAP.get(header_l_loop)

                    if pydantic_field:
                        # 'id' and 'name' source columns are skipped by prior 'continue' statements.
                        if pydantic_field in ['rate_event', 'rate_7_day', 'rate_28_day']:
                            generator_entry[pydantic_field] = _clean_currency(value_raw)
                        else: 
                            # For any other mapped fields that are not currency (and not id/name)
                            generator_entry[pydantic_field] = str(value_raw).strip() if value_raw is not None else None
                
                if not generator_entry.get("name"): # Should be set, but as a final fallback
                    logfire.error(f"Generator {generator_id_value}: Name field is unexpectedly missing after parsing. Defaulting to ID.")
                    generator_entry["name"] = generator_id_value
                
                pricing_catalog["generators"][generator_id_value] = generator_entry
            logfire.info(f"SheetSyncService: Parsed {len(pricing_catalog['generators'])} generators.")
        else:
            logfire.warning("No generator data or only headers found for generators.")
            
        logfire.info(f"SheetSyncService: Successfully parsed pricing catalog. Products: {len(pricing_catalog['products'])}, Generators: {len(pricing_catalog['generators'])}.")
        return pricing_catalog

    async def sync_full_catalog(self, background_tasks: Optional[BackgroundTasks] = None) -> bool:
        logfire.info("SheetSyncService: Starting full sync to Redis & MongoDB (Pricing, Config, Branches) - SEQUENTIAL FETCH.")
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

        for key, range_name in fetch_order:
            logfire.info(f"--- Starting fetch for: {key} ({range_name}) ---")
            try:
                data = await self._fetch_sheet_data(settings.GOOGLE_SHEET_ID, range_name)
                fetched_data[key] = data
                if data is None:
                    logfire.error(f"Fetch for '{key}' returned None.")
                    if key != 'config':
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

        branches_data = fetched_data.get("branches")
        branches_synced_successfully = False
        parsed_branches_for_mongo: List[Dict[str, Any]] = []
        if branches_data is not None:
            try:
                parsed_branches = self._parse_branches(branches_data)
                parsed_branches_for_mongo = parsed_branches
                if await self.redis_service.set_json(BRANCH_LIST_CACHE_KEY, parsed_branches):
                    logfire.info(f"SheetSyncService: BRANCH SYNC SUCCESS (Redis) - Synced {len(parsed_branches)} branches to Redis '{BRANCH_LIST_CACHE_KEY}'.")
                else:
                    error_msg = f"Failed to store branches in Redis key '{BRANCH_LIST_CACHE_KEY}'."
                    logfire.error(f"SheetSyncService: BRANCH SYNC ERROR (Redis) - {error_msg}")
                    if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "RedisStoreError", error_msg, {"key": BRANCH_LIST_CACHE_KEY})
                    critical_fetch_error = True

                if not critical_fetch_error:
                    try:
                        await self.mongo_service.replace_sheet_collection_data(
                            collection_name=SHEET_BRANCHES_COLLECTION,
                            data=parsed_branches_for_mongo,
                            id_field="address"
                        )
                        logfire.info(f"SheetSyncService: BRANCH SYNC SUCCESS (MongoDB) - Synced {len(parsed_branches_for_mongo)} branches to MongoDB collection '{SHEET_BRANCHES_COLLECTION}'.")
                        branches_synced_successfully = True
                    except Exception as mongo_e:
                        error_msg = f"BRANCH SYNC ERROR (MongoDB): Failed to sync branches to MongoDB collection '{SHEET_BRANCHES_COLLECTION}'. Error: {mongo_e}"
                        logfire.error(error_msg, exc_info=True)
                        if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "MongoStoreErrorBranches", str(mongo_e), {"collection": SHEET_BRANCHES_COLLECTION})
                        critical_fetch_error = True
                        branches_synced_successfully = False

            except Exception as e:
                error_msg = f"BRANCH SYNC ERROR: Error processing or caching branches. Redis key '{BRANCH_LIST_CACHE_KEY}' may NOT have been created/updated."
                logfire.exception(error_msg, exc_info=e)
                if background_tasks:
                    background_tasks.add_task(log_error_bg, self.redis_service, "BranchProcessingError", str(e))
                critical_fetch_error = True

        pricing_synced_successfully = False
        parsed_config_for_mongo: Dict[str, Any] = []
        products_to_save_mongo: List[Dict[str, Any]] = []
        generators_to_save_mongo: List[Dict[str, Any]] = []

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
                    logfire.info(f"SheetSyncService: PRICING SYNC SUCCESS (Redis) - Synced pricing catalog to Redis '{PRICING_CATALOG_CACHE_KEY}'.")
                    products_to_save_mongo = list(pricing_catalog.get("products", {}).values())
                    generators_to_save_mongo = list(pricing_catalog.get("generators", {}).values())
                    parsed_config_for_mongo = {
                        "delivery_config": pricing_catalog.get("delivery", {}),
                        "seasonal_multipliers_config": pricing_catalog.get("seasonal_multipliers", {})
                    }

                    mongo_product_sync_ok = False
                    mongo_generator_sync_ok = False
                    mongo_config_sync_ok = False

                    try:
                        await self.mongo_service.replace_sheet_collection_data(
                            collection_name=SHEET_PRODUCTS_COLLECTION,
                            data=products_to_save_mongo,
                            id_field="id" 
                        )
                        logfire.info(f"SheetSyncService: PRICING SYNC SUCCESS (MongoDB Products) - Synced {len(products_to_save_mongo)} products to '{SHEET_PRODUCTS_COLLECTION}'.")
                        mongo_product_sync_ok = True
                    except Exception as mongo_e_prod:
                        error_msg_prod = f"PRICING SYNC ERROR (MongoDB Products): Failed to sync products to '{SHEET_PRODUCTS_COLLECTION}'. Error: {mongo_e_prod}"
                        logfire.error(error_msg_prod, exc_info=True)
                        if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "MongoStoreErrorProducts", str(mongo_e_prod), {"collection": SHEET_PRODUCTS_COLLECTION})
                        critical_fetch_error = True

                    try:
                        await self.mongo_service.replace_sheet_collection_data(
                            collection_name=SHEET_GENERATORS_COLLECTION,
                            data=generators_to_save_mongo,
                            id_field="id"
                        )
                        logfire.info(f"SheetSyncService: PRICING SYNC SUCCESS (MongoDB Generators) - Synced {len(generators_to_save_mongo)} generators to '{SHEET_GENERATORS_COLLECTION}'.")
                        mongo_generator_sync_ok = True
                    except Exception as mongo_e_gen:
                        error_msg_gen = f"PRICING SYNC ERROR (MongoDB Generators): Failed to sync generators to '{SHEET_GENERATORS_COLLECTION}'. Error: {mongo_e_gen}"
                        logfire.error(error_msg_gen, exc_info=True)
                        if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "MongoStoreErrorGenerators", str(mongo_e_gen), {"collection": SHEET_GENERATORS_COLLECTION})
                        critical_fetch_error = True
                    
                    try:
                        await self.mongo_service.upsert_sheet_config_document(
                            document_id="master_config",
                            config_data=parsed_config_for_mongo,
                            config_type="pricing_and_delivery"
                        )
                        logfire.info(f"SheetSyncService: PRICING SYNC SUCCESS (MongoDB Config) - Upserted config to '{SHEET_CONFIG_COLLECTION}'.")
                        mongo_config_sync_ok = True
                    except Exception as mongo_e_conf:
                        error_msg_conf = f"PRICING SYNC ERROR (MongoDB Config): Failed to upsert config to '{SHEET_CONFIG_COLLECTION}'. Error: {mongo_e_conf}"
                        logfire.error(error_msg_conf, exc_info=True)
                        if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "MongoStoreErrorConfig", str(mongo_e_conf), {"collection": SHEET_CONFIG_COLLECTION})
                        critical_fetch_error = True

                    if mongo_product_sync_ok and mongo_generator_sync_ok and mongo_config_sync_ok:
                        pricing_synced_successfully = True
                    else:
                        pricing_synced_successfully = False
                        logfire.error("SheetSyncService: PRICING SYNC FAILED (MongoDB) - One or more parts of pricing data failed to sync to MongoDB.")

                else:
                    error_msg = f"Failed to store pricing catalog in Redis key '{PRICING_CATALOG_CACHE_KEY}'."
                    logfire.error(f"SheetSyncService: PRICING SYNC ERROR (Redis) - {error_msg}")
                    if background_tasks: background_tasks.add_task(log_error_bg, self.redis_service, "RedisStoreError", error_msg, {"key": PRICING_CATALOG_CACHE_KEY})
                    critical_fetch_error = True
            except Exception as e:
                error_msg = "PRICING SYNC ERROR: Error processing or caching pricing catalog"
                logfire.exception(error_msg, exc_info=e)
                if background_tasks:
                     background_tasks.add_task(log_error_bg, self.redis_service, "CatalogProcessingError", str(e))
                critical_fetch_error = True

        final_success = branches_synced_successfully and pricing_synced_successfully
        if final_success:
             await self.redis_service.set("sync:last_successful_timestamp", datetime.now().isoformat())
             logfire.info(f"SheetSyncService: OVERALL SYNC SUCCESS (Redis & MongoDB) - Branches: {branches_synced_successfully}, Pricing: {pricing_synced_successfully}")
        else:
             logfire.error(f"SheetSyncService: OVERALL SYNC FAILED (Redis & MongoDB) - Branches: {branches_synced_successfully}, Pricing: {pricing_synced_successfully}. Check logs.")
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
                await self.sync_full_catalog(background_tasks=bg_tasks) # Renamed method call
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
            initial_sync_success = await self.sync_full_catalog(background_tasks=bg_tasks_for_initial_sync) # Renamed method call
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
        if self._sync_task is None or self._sync_task.done():
            logfire.info("SheetSyncService: Starting background sync loop task.")
            self._sync_task = asyncio.create_task(self._run_sync_loop())
            logfire.info("SheetSyncService: Background sync loop task created and started.")
        else:
            logfire.info("SheetSyncService: Background sync task is already running.")

    async def stop_background_sync(self):
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
    logfire.info(f"Initial sync scheduled to run after {delay_seconds} seconds.")
    await asyncio.sleep(delay_seconds)
    logfire.info("Delay finished, performing initial sync now.")
    await service_instance._perform_initial_sync()

async def lifespan_startup():
    global _sheet_sync_service_instance
    logfire.info("SYNC LIFESPAN: Attempting to start SheetSyncService...")
    if _sheet_sync_service_instance is None:
        try:
            # Get Redis service instance via dependency injector
            redis_service = await get_redis_service()
            mongo_service = await get_mongo_service() # Get Mongo service instance
            
            _sheet_sync_service_instance = SheetSyncService(redis_service, mongo_service) # Pass mongo_service
            # Await the initialization of the service itself (which builds the google client)
            await _sheet_sync_service_instance.initialize_service()
            # Now start the background sync tasks (which run the first sync in the background after delay)
            await _sheet_sync_service_instance.start_background_sync()
            # Schedule the initial sync to run after a delay in the background
            asyncio.create_task(_run_initial_sync_after_delay(_sheet_sync_service_instance, 30))
            logfire.info("SYNC LIFESPAN: SheetSyncService initialized, background loop started, initial sync scheduled with delay.")
        except RuntimeError as e:
            logfire.error(f"SYNC LIFESPAN: CRITICAL - Failed to get required Redis or Mongo service: {e}", exc_info=True) # Updated log
            # Prevent service from being considered initialized if Redis failed
            _sheet_sync_service_instance = None 
        except Exception as e:
            logfire.error(f"SYNC LIFESPAN: CRITICAL - Failed to initialize or start SheetSyncService: {e}", exc_info=True)
            _sheet_sync_service_instance = None
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
