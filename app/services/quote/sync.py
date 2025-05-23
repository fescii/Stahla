# filepath: /home/femar/AO3/Stahla/app/services/quote/sync.py
import asyncio
import logging  # Keep for general logging if needed
import re
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json  # Added for HttpError details

import logfire  # Import logfire directly
from fastapi import BackgroundTasks

from app.core.config import settings
from app.services.redis.redis import (
    RedisService,
    get_redis_service,
)  # Import get_redis_service
from app.services.mongo.mongo import (
    MongoService,
    get_mongo_service,
    SHEET_PRODUCTS_COLLECTION,
    SHEET_GENERATORS_COLLECTION,
    SHEET_BRANCHES_COLLECTION,
    SHEET_CONFIG_COLLECTION,
)  # Import MongoService and related
from app.models.location import BranchLocation
from app.services.dash.background import log_error_bg
from app.services.quote.auth import (
    create_sheets_service,
)  # Import the new service creator

# Constants
# SCOPES is now managed within auth.py
PRICING_CATALOG_CACHE_KEY = "pricing:catalog"
BRANCH_LIST_CACHE_KEY = "stahla:branches"  # New Redis key for branches list
CONFIG_DATA_RANGE = settings.GOOGLE_SHEET_CONFIG_RANGE  # Use setting
SYNC_INTERVAL_SECONDS = 60 * 60 * 24  # Sync every 1 day


# Helper to clean currency strings
def _clean_currency(value: Any) -> Optional[float]:
  if value is None:
    return None
  if isinstance(value, (int, float)):
    return float(value)
  if isinstance(value, str):
    normalized_value = value.strip().lower()
    if normalized_value == "n/a" or not normalized_value:  # Handles empty strings and "n/a"
      return None

    # Remove currency symbols and commas
    cleaned_value = value.replace("$", "").replace(",", "").strip()

    if not cleaned_value:  # Handles cases like value being only "$" or ","
      return None
    try:
      return float(cleaned_value)
    except ValueError:
      logfire.warning(
          f"Could not parse currency string to float. Input: '{value}'")
      return None
  # If value is not None, int, float, or str, it's an unexpected type for currency.
  logfire.warning(
      f"Unexpected type for currency cleaning: {type(value)}, value: '{value}'")
  return None


# Define header to Pydantic field name mappings
PRODUCT_HEADER_MAP = {
    # ID and Name are sourced from 'Primary Column' based on Stahla - products.csv
    "primary column": "id",
    # 'name' will default to the value from the 'id' field (i.e., 'Primary Column')
    # as there isn't a separate column designated for product name in the CSV.
    # Pricing fields (lowercase header from sheet -> Pydantic field name)
    "weekly pricing (7 day)": "weekly_7_day",
    "28 day rate": "rate_28_day",
    "2-5 month rate": "rate_2_5_month",
    "6+ month pricing": "rate_6_plus_month",
    "18+ month pricing": "rate_18_plus_month",
    "event standard (<4 days)": "event_standard",
    "event premium (<4 days)": "event_premium",
    "event premium plus (<4 days)": "event_premium_plus",
    "event premium platinum (<4 days)": "event_premium_platinum",
}

GENERATOR_HEADER_MAP = {
    # ID and Name are sourced from 'Generator Rental' based on Stahla - generators.csv
    "generator rental": "id",
    # 'name' will default to the value from the 'id' field (i.e., 'Generator Rental').
    # Pricing fields
    "event (< 3 day rate)": "rate_event",
    "7 day rate": "rate_7_day",
    "28 day rate": "rate_28_day",
}

# List of known extra service headers (lowercase) from 'Stahla - products.csv'
# These will be put into the 'extras' dictionary for products.
KNOWN_PRODUCT_EXTRAS_HEADERS = [
    "pump out waste tank",
    "fresh water tank fill",
    "cleaning",
    "restocking",
]


class SheetSyncService:
  def __init__(
      self, redis_service: RedisService, mongo_service: MongoService
  ):  # Add mongo_service
    self.redis_service = redis_service
    self.mongo_service = mongo_service  # Store mongo_service
    logfire.info(
        "SheetSyncService: Initializing (service object will be built asynchronously)."
    )
    self.sheet_service = None  # Initialize as None
    self._sync_task: Optional[asyncio.Task] = None

  async def initialize_service(self):
    """Asynchronously initializes the Google Sheets service client by running the synchronous creation function in an executor."""
    logfire.info(
        "SheetSyncService: Attempting to build sheet service via auth.py (in executor)..."
    )
    loop = asyncio.get_running_loop()
    try:
      self.sheet_service = await loop.run_in_executor(
          None, create_sheets_service, settings.GOOGLE_APPLICATION_CREDENTIALS or ""
      )
      logfire.info(
          "SheetSyncService: Sheet service built successfully via auth.py (in executor)."
      )
    except Exception as e:
      logfire.error(
          f"SheetSyncService: CRITICAL - Failed during initialize_service while creating sheet service: {e}",
          exc_info=True,
      )
      raise

  async def _fetch_sheet_data(
      self, sheet_id: str, range_name: str
  ) -> Optional[List[List[Any]]]:
    """Fetches data from a specific sheet and range."""
    if not self.sheet_service:
      logfire.error(
          "SheetSyncService: Cannot fetch sheet data - Google Sheets service not initialized."
      )
      return None

    try:
      logfire.info(
          f"SheetSyncService: Attempting to fetch data from GSheet ID '{sheet_id}', range '{range_name}'."
      )
      sheet = self.sheet_service.spreadsheets()
      loop = asyncio.get_running_loop()
      result = await loop.run_in_executor(
          None,
          sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute,
      )
      values = result.get("values", [])
      logfire.info(
          f"SheetSyncService: Successfully fetched {len(values)} rows from range '{range_name}'"
      )
      logfire.debug(
          f"SheetSyncService: Fetched data for range '{range_name}': {values}"
      )
      return values
    except Exception as err:
      from googleapiclient.errors import HttpError

      if isinstance(err, HttpError):
        err_reason = (
            err._get_reason()
            if hasattr(err, "_get_reason")
            else "Unknown reason"
        )
        err_status = (
            err.resp.status
            if hasattr(err, "resp") and hasattr(err.resp, "status")
            else "N/A"
        )
        logfire.error(
            f"SheetSyncService: Google Sheets API error fetching range '{range_name}': {err_status} - {err_reason}"
        )
        try:
          error_details = json.loads(err.content.decode())
          logfire.error(
              f"SheetSyncService: Google API Error Details: {error_details}"
          )
        except:
          logfire.error(
              f"SheetSyncService: Google API Raw Error Content: {err.content}"
          )
      else:
        logfire.error(
            f"SheetSyncService: Unexpected error fetching sheet data for range '{range_name}' - {err}",
            exc_info=True,
        )
      return None

  def _parse_branches(self, branches_data: List[List[Any]]) -> List[Dict[str, Any]]:
    branches = []
    if not branches_data or len(branches_data) < 2:
      logfire.warning(
          f"No data or insufficient rows (expected header + data) provided to _parse_branches for range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'. Branch list will be empty."
      )
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
          logfire.warning(
              f"Skipping branch row {i+2} (original sheet row) due to parsing/validation error: {row}. Error: {e}"
          )
      else:
        logfire.warning(
            f"Skipping incomplete branch row {i+2} (original sheet row): {row}. Expected at least 2 columns."
        )

    logfire.info(
        f"SheetSyncService: Parsed {len(branches)} branches from sheet range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'."
    )
    return branches

  def _parse_delivery_and_config(
      self, config_data: List[List[Any]]
  ) -> Dict[str, Any]:
    parsed_config = {
        "delivery": {
            "base_fee": 0.0,
            "per_mile_rates": {"omaha_kansas_city": 2.99, "denver": 3.99},
            "free_miles_threshold": 25,
        },
        "seasonal_multipliers": {"standard": 1.0, "tiers": []},
    }

    if not config_data or len(config_data) < 2:
      logfire.warning(
          f"No data or insufficient rows in config_data. Using default delivery/seasonal settings."
      )
      return parsed_config

    data_rows = config_data
    if str(data_rows[0][0]).strip().lower() == "key":
      data_rows = config_data[1:]

    raw_key_values: Dict[str, Any] = {}
    for i, row in enumerate(data_rows):
      if len(row) >= 2 and row[0] and isinstance(row[0], str):
        key = str(row[0]).strip().lower()
        value = row[1]
        raw_key_values[key] = value
      else:
        logfire.warning(
            f"Skipping invalid config row {i+1}: {row}. Expected Key and Value."
        )

    logfire.debug(f"Raw key-values from config sheet: {raw_key_values}")

    # Parse delivery base fee
    parsed_config["delivery"]["base_fee"] = _clean_currency(
        raw_key_values.get("delivery base fee", 0.0)
    )

    # Parse per-mile rates with location-specific rates
    omaha_kc_rate = _clean_currency(
        raw_key_values.get(
            "delivery per mile rate (from omaha or kansas city)", 2.99
        )
    )
    denver_rate = _clean_currency(
        raw_key_values.get("delivery per mile rate (from denver)", 3.99)
    )

    parsed_config["delivery"]["per_mile_rates"] = {
        "omaha_kansas_city": omaha_kc_rate,
        "denver": denver_rate,
    }

    # Parse free miles threshold
    free_miles_raw = raw_key_values.get("delivery free miles threshold", 25)
    try:
      parsed_config["delivery"]["free_miles_threshold"] = (
          int(free_miles_raw) if free_miles_raw is not None else 25
      )
    except (ValueError, TypeError):
      logfire.warning(
          f"Could not parse 'delivery free miles threshold': {free_miles_raw}. Using default: 25"
      )

    # Parse seasonal multipliers using the helper
    tier_configs = self._parse_seasonal_dates(raw_key_values)

    # Convert tier configs to the format expected by the API
    for tier_type, config in tier_configs.items():
      for date_range in config["date_ranges"]:
        parsed_config["seasonal_multipliers"]["tiers"].append(
            {
                "name": config["name"],
                "start_date": date_range["start_date"],
                "end_date": date_range["end_date"],
                "rate": config["rate"],
            }
        )

        logfire.info(
            f"SheetSyncService: Added seasonal multiplier tier {config['name']}: {date_range['start_date']} to {date_range['end_date']} with rate {config['rate']}"
        )

    logfire.info(
        f"SheetSyncService: Parsed delivery config: {parsed_config['delivery']}"
    )
    logfire.info(
        f"SheetSyncService: Parsed seasonal multipliers: {parsed_config['seasonal_multipliers']}"
    )
    return parsed_config

  def _parse_seasonal_dates(
      self, # Add self as the first argument
      raw_key_values: Dict[str, Any],
  ) -> Dict[str, Dict[str, Any]]:
    """
    Parses seasonal date ranges and rates from the config data.
    Returns a structure with all tiers and their date ranges.

    The CSV format has multiple entries for each tier type with format:
    Seasonal Multiplier [Tier] Start, YYYY-MM-DD
    Seasonal Multiplier [Tier] End, YYYY-MM-DD
    """
    tier_configs = {
        "premium": {
            "name": "Premium",
            "rate": 1.1,  # 10% increase
            "date_ranges": [],
        },
        "premium_plus": {
            "name": "Premium Plus",
            "rate": 1.2,  # 20% increase
            "date_ranges": [],
        },
        "premium_platinum": {
            "name": "Premium Platinum",
            "rate": 1.3,  # 30% increase
            "date_ranges": [],
        },
    }

    # Find all key-value pairs with "seasonal multiplier" in the key
    seasonal_keys = [
        (k, v)
        for k, v in raw_key_values.items()
        if "seasonal multiplier" in k.lower()
    ]

    # Process start and end dates for each tier type
    for tier_type in tier_configs.keys():
      search_key = tier_type.replace("_", " ")
      start_dates = []
      end_dates = []

      # Find all start and end dates for this tier
      for key, value in seasonal_keys:
        key_lower = key.lower()
        if f"seasonal multiplier {search_key} start" in key_lower and value:
          start_dates.append(value)
        elif f"seasonal multiplier {search_key} end" in key_lower and value:
          end_dates.append(value)

      # Create date ranges from the paired start and end dates
      for i in range(min(len(start_dates), len(end_dates))):
        try:
          start_date = datetime.strptime(
              str(start_dates[i]), "%Y-%m-%d"
          ).date()
          end_date = datetime.strptime(str(end_dates[i]), "%Y-%m-%d").date()

          tier_configs[tier_type]["date_ranges"].append(
              {
                  "start_date": start_date.isoformat(),
                  "end_date": end_date.isoformat(),
              }
          )

          logfire.info(
              f"Added {search_key} seasonal tier date range: {start_date} to {end_date}"
          )
        except (ValueError, TypeError) as e:
          logfire.warning(
              f"Could not parse '{tier_type}' seasonal tier dates from config: {e}"
          )

    return tier_configs

  def _parse_pricing_data(
      self,
      products_data: List[List[Any]],
      generators_data: List[List[Any]],
      config: Dict[str, Any],
  ) -> Dict[str, Any]:
    """Parses product and generator data from sheet rows into structured dictionaries."""
    pricing_catalog: Dict[str, Any] = {
        "products": {},
        "generators": {},
        "delivery": config.get("delivery", {}),
        "seasonal_multipliers": config.get("seasonal_multipliers", {}),
        "last_updated": datetime.utcnow().isoformat(),
    }

    # --- Parse Products ---
    if products_data and len(products_data) > 1:
      product_headers = [
          str(h).strip().lower() for h in products_data[0]
      ]  # Normalize headers
      product_data_rows = products_data[1:]
      logfire.info(
          f"SheetSyncService: Parsing {len(product_data_rows)} product rows with headers: {product_headers}"
      )

      for i, row_data in enumerate(product_data_rows):
        if not any(row_data):  # Skip entirely empty rows
          logfire.debug(f"Skipping empty product row {i+2}")
          continue

        product_dict: Dict[str, Any] = {"extras": {}}
        # Ensure row_data has enough elements for all headers
        # Map values based on PRODUCT_HEADER_MAP
        for sheet_header, pydantic_field in PRODUCT_HEADER_MAP.items():
          try:
            col_index = product_headers.index(sheet_header)
            raw_value = row_data[col_index] if col_index < len(
                row_data) else None
            # Clean currency for pricing fields, otherwise store raw
            if "rate" in pydantic_field or "weekly" in pydantic_field or "event" in pydantic_field:
              product_dict[pydantic_field] = _clean_currency(raw_value)
            else:
              product_dict[pydantic_field] = str(
                  raw_value).strip() if raw_value is not None else None
          except ValueError:  # Header not found
            logfire.debug(
                f"Header \'{sheet_header}\' not found in product sheet. Field \'{pydantic_field}\' will be None."
            )
            product_dict[pydantic_field] = None
          except IndexError:
            logfire.warning(
                f"Product row {i+2} is shorter than expected. Header \'{sheet_header}\' (index {col_index}) out of bounds. Field \'{pydantic_field}\' will be None."
            )
            product_dict[pydantic_field] = None

        # Default 'name' to 'id' if 'name' wasn't explicitly mapped or is empty
        if not product_dict.get("name") and product_dict.get("id"):
          product_dict["name"] = product_dict["id"]

        # If 'id' is still missing or empty after mapping, skip this product
        if not product_dict.get("id"):
          logfire.warning(
              f"Skipping product row {i+2} due to missing ID (Primary Column)."
          )
          continue

        # Populate 'extras' from known extra service headers
        for extra_header in KNOWN_PRODUCT_EXTRAS_HEADERS:
          try:
            col_index = product_headers.index(extra_header)
            raw_value = row_data[col_index] if col_index < len(
                row_data) else None
            # Extras are also currency values
            product_dict["extras"][extra_header.replace(
                " ", "_")] = _clean_currency(raw_value)
          except ValueError:
            # It's okay if an extra header isn't present for all products
            pass
          except IndexError:
            logfire.warning(
                f"Product row {i+2} is shorter than expected when looking for extra \'{extra_header}\'. It will be skipped for this product."
            )

        product_id = product_dict["id"]
        pricing_catalog["products"][product_id] = product_dict
        logfire.debug(f"Parsed product: {product_id} -> {product_dict}")
    else:
      logfire.warning(
          "No product data or only headers found in products_data.")

    # --- Parse Generators ---
    if generators_data and len(generators_data) > 1:
      generator_headers = [
          str(h).strip().lower() for h in generators_data[0]
      ]  # Normalize headers
      generator_data_rows = generators_data[1:]
      logfire.info(
          f"SheetSyncService: Parsing {len(generator_data_rows)} generator rows with headers: {generator_headers}"
      )

      for i, row_data in enumerate(generator_data_rows):
        if not any(row_data):  # Skip entirely empty rows
          logfire.debug(f"Skipping empty generator row {i+2}")
          continue

        generator_dict: Dict[str, Any] = {}
        # Ensure row_data has enough elements for all headers
        # Map values based on GENERATOR_HEADER_MAP
        for sheet_header, pydantic_field in GENERATOR_HEADER_MAP.items():
          try:
            col_index = generator_headers.index(sheet_header)
            raw_value = row_data[col_index] if col_index < len(
                row_data) else None
            # Apply _clean_currency to all generator rate fields
            if "rate" in pydantic_field:  # Ensures all rate fields are cleaned
              generator_dict[pydantic_field] = _clean_currency(raw_value)
            else:  # For 'id' and 'name' (which defaults to 'id')
              generator_dict[pydantic_field] = str(
                  raw_value).strip() if raw_value is not None else None
          except ValueError:  # Header not found
            logfire.debug(
                f"Header \'{sheet_header}\' not found in generator sheet. Field \'{pydantic_field}\' will be None."
            )
            generator_dict[pydantic_field] = None
          except IndexError:
            logfire.warning(
                f"Generator row {i+2} is shorter than expected. Header \'{sheet_header}\' (index {col_index}) out of bounds. Field \'{pydantic_field}\' will be None."
            )
            generator_dict[pydantic_field] = None

        # Default 'name' to 'id' if 'name' wasn't explicitly mapped or is empty
        if not generator_dict.get("name") and generator_dict.get("id"):
          generator_dict["name"] = generator_dict["id"]

        # If 'id' is still missing or empty after mapping, skip this generator
        if not generator_dict.get("id"):
          logfire.warning(
              f"Skipping generator row {i+2} due to missing ID (Generator Rental)."
          )
          continue

        generator_id = generator_dict["id"]
        pricing_catalog["generators"][generator_id] = generator_dict
        logfire.debug(f"Parsed generator: {generator_id} -> {generator_dict}")
    else:
      logfire.warning(
          "No generator data or only headers found in generators_data.")

    return pricing_catalog

  async def sync_full_catalog(
      self, background_tasks: Optional[BackgroundTasks] = None
  ) -> bool:
    """
    Sync the full catalog of pricing data and branches to Redis and MongoDB.
    This is the main entry point for syncing all data from Google Sheets.
    """
    logfire.info(
        "SheetSyncService: Starting full sync to Redis & MongoDB (Pricing, Config, Branches) - SEQUENTIAL FETCH."
    )
    if not self.sheet_service:
      logfire.error(
          "SheetSyncService: Cannot sync - Google Sheets service not initialized."
      )
      return False

    # Step 1: Fetch all required data
    fetched_data, critical_fetch_error = await self._fetch_and_validate_data(
        background_tasks
    )

    # Step 2: Sync branches
    branches_data = fetched_data.get("branches")
    (
        branches_synced_successfully,
        critical_fetch_error,
        parsed_branches_for_mongo,
    ) = await self._sync_branches_to_storage(branches_data, background_tasks)

    # Step 3: Sync pricing catalog
    pricing_synced_successfully = False
    if not critical_fetch_error:
      pricing_synced_successfully, critical_fetch_error = (
          await self._sync_pricing_to_storage(
              fetched_data, critical_fetch_error, background_tasks
          )
      )

    # Final status update and return
    final_success = branches_synced_successfully and pricing_synced_successfully
    if final_success:
      await self.redis_service.set(
          "sync:last_successful_timestamp", datetime.now().isoformat()
      )
      logfire.info(
          f"SheetSyncService: OVERALL SYNC SUCCESS (Redis & MongoDB) - Branches: {branches_synced_successfully}, Pricing: {pricing_synced_successfully}"
      )
    else:
      logfire.error(
          f"SheetSyncService: OVERALL SYNC FAILED (Redis & MongoDB) - Branches: {branches_synced_successfully}, Pricing: {pricing_synced_successfully}. Check logs."
      )
    return final_success

  async def _fetch_and_validate_data(
      self, background_tasks: Optional[BackgroundTasks] = None
  ) -> Tuple[Dict[str, Any], bool]:
    """
    Fetch all required data sheets and validate the results.
    Returns a tuple of (fetched_data, critical_fetch_error)
    """
    fetched_data = {}
    critical_fetch_error = False
    fetch_order = [
        ("products", settings.GOOGLE_SHEET_PRODUCTS_TAB_NAME),
        ("generators", settings.GOOGLE_SHEET_GENERATORS_TAB_NAME),
        ("config", settings.GOOGLE_SHEET_CONFIG_RANGE),
        ("branches", settings.GOOGLE_SHEET_BRANCHES_RANGE),
    ]

    for key, range_name in fetch_order:
      logfire.info(f"--- Starting fetch for: {key} ({range_name}) ---")
      try:
        data = await self._fetch_sheet_data(
            settings.GOOGLE_SHEET_ID, range_name
        )
        fetched_data[key] = data
        if data is None:
          logfire.error(f"Fetch for '{key}' returned None.")
          if key != "config":
            critical_fetch_error = True
        else:
          logfire.info(f"--- Successfully fetched data for: {key} ---")
      except Exception as e:
        error_msg = f"Exception during fetch for '{key}': {e}"
        logfire.error(error_msg, exc_info=True)
        fetched_data[key] = None
        if background_tasks:
          background_tasks.add_task(
              log_error_bg,
              self.redis_service,
              f"SheetFetchError_{key}",
              str(e),
              {"sheet_id": settings.GOOGLE_SHEET_ID, "range": range_name},
          )
        if key != "config":
          critical_fetch_error = True

    return fetched_data, critical_fetch_error

  async def _sync_branches_to_storage(
      self,
      branches_data: Optional[List[List[Any]]],
      background_tasks: Optional[BackgroundTasks] = None,
  ) -> Tuple[bool, bool, List[Dict[str, Any]]]:
    """
    Sync branch data to Redis and MongoDB.
    Returns a tuple of (branches_synced_successfully, critical_fetch_error, parsed_branches_for_mongo)
    """
    branches_synced_successfully = False
    critical_fetch_error = False
    parsed_branches_for_mongo: List[Dict[str, Any]] = []

    if branches_data is None:
      return (
          branches_synced_successfully,
          critical_fetch_error,
          parsed_branches_for_mongo,
      )

    try:
      parsed_branches = self._parse_branches(branches_data)
      parsed_branches_for_mongo = parsed_branches
      if await self.redis_service.set_json(
          BRANCH_LIST_CACHE_KEY, parsed_branches
      ):
        logfire.info(
            f"SheetSyncService: BRANCH SYNC SUCCESS (Redis) - Synced {len(parsed_branches)} branches to Redis '{BRANCH_LIST_CACHE_KEY}'."
        )
      else:
        error_msg = (
            f"Failed to store branches in Redis key '{BRANCH_LIST_CACHE_KEY}'."
        )
        logfire.error(
            f"SheetSyncService: BRANCH SYNC ERROR (Redis) - {error_msg}"
        )
        if background_tasks:
          background_tasks.add_task(
              log_error_bg,
              self.redis_service,
              "RedisStoreError",
              error_msg,
              {"key": BRANCH_LIST_CACHE_KEY},
          )
        critical_fetch_error = True

      if not critical_fetch_error:
        try:
          await self.mongo_service.replace_sheet_collection_data(
              collection_name=SHEET_BRANCHES_COLLECTION,
              data=parsed_branches_for_mongo,
              id_field="address",
          )
          logfire.info(
              f"SheetSyncService: BRANCH SYNC SUCCESS (MongoDB) - Synced {len(parsed_branches_for_mongo)} branches to MongoDB collection '{SHEET_BRANCHES_COLLECTION}'."
          )
          branches_synced_successfully = True
        except Exception as mongo_e:
          error_msg = f"BRANCH SYNC ERROR (MongoDB): Failed to sync branches to MongoDB collection '{SHEET_BRANCHES_COLLECTION}'. Error: {mongo_e}"
          logfire.error(error_msg, exc_info=True)
          if background_tasks:
            background_tasks.add_task(
                log_error_bg,
                self.redis_service,
                "MongoStoreErrorBranches",
                str(mongo_e),
                {"collection": SHEET_BRANCHES_COLLECTION},
            )
          critical_fetch_error = True
          branches_synced_successfully = False
    except Exception as e:
      error_msg = f"BRANCH SYNC ERROR: Error processing or caching branches. Redis key '{BRANCH_LIST_CACHE_KEY}' may NOT have been created/updated."
      logfire.exception(error_msg, exc_info=e)
      if background_tasks:
        background_tasks.add_task(
            log_error_bg,
            self.redis_service,
            "BranchProcessingError",
            str(e),
        )
      critical_fetch_error = True

    return (
        branches_synced_successfully,
        critical_fetch_error,
        parsed_branches_for_mongo,
    )

  def _prepare_pricing_data_for_mongo(
      self, pricing_catalog: Dict[str, Any]
  ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Prepare pricing data for MongoDB storage.
    Returns a tuple of (parsed_config_for_mongo, products_to_save_mongo, generators_to_save_mongo)
    """
    # Make sure edge cases are handled before storing in MongoDB
    pricing_catalog = self._handle_csv_edge_cases(pricing_catalog)

    products_to_save_mongo = list(pricing_catalog.get("products", {}).values())
    generators_to_save_mongo = list(
        pricing_catalog.get("generators", {}).values())

    # Create an optimized structure for MongoDB storage and quoting calculations
    parsed_config_for_mongo = {
        "delivery_config": {
            "base_fee": pricing_catalog.get("delivery", {}).get("base_fee", 0.0),
            "per_mile_rates": {
                "omaha_kansas_city": pricing_catalog.get("delivery", {})
                .get("per_mile_rates", {})
                .get("omaha_kansas_city", 2.99),
                "denver": pricing_catalog.get("delivery", {})
                .get("per_mile_rates", {})
                .get("denver", 3.99),
            },
            "free_miles_threshold": pricing_catalog.get("delivery", {}).get(
                "free_miles_threshold", 25
            ),
        },
        "seasonal_multipliers_config": {
            "standard_rate": pricing_catalog.get("seasonal_multipliers", {}).get(
                "standard", 1.0
            ),
            "tiers": pricing_catalog.get("seasonal_multipliers", {}).get(
                "tiers", []
            ),
        },
        "last_updated": datetime.utcnow().isoformat(),
        "data_source": "Google Sheets",
    }

    return parsed_config_for_mongo, products_to_save_mongo, generators_to_save_mongo

  async def _sync_pricing_to_storage(
      self,
      fetched_data: Dict[str, Any],
      critical_fetch_error: bool,
      background_tasks: Optional[BackgroundTasks] = None,
  ) -> Tuple[bool, bool]:
    """
    Sync pricing catalog data to Redis and MongoDB.
    Returns a tuple of (pricing_synced_successfully, critical_fetch_error)
    """
    pricing_synced_successfully = False
    parsed_config_for_mongo: Dict[str, Any] = {}
    products_to_save_mongo: List[Dict[str, Any]] = []
    generators_to_save_mongo: List[Dict[str, Any]] = []

    if fetched_data["products"] is None or fetched_data["generators"] is None:
      error_msg = "PRICING SYNC ERROR: Failed to fetch required product/generator data. Pricing catalog sync aborted."
      logfire.error(error_msg)
      critical_fetch_error = True
      return pricing_synced_successfully, critical_fetch_error

    config_data = fetched_data.get("config", [])
    if config_data is None:
      config_data = []
    try:
      parsed_config = self._parse_delivery_and_config(config_data)
      pricing_catalog = self._parse_pricing_data(
          fetched_data["products"], fetched_data["generators"], parsed_config
      )
      if await self.redis_service.set_json(
          PRICING_CATALOG_CACHE_KEY, pricing_catalog
      ):
        logfire.info(
            f"SheetSyncService: PRICING SYNC SUCCESS (Redis) - Synced pricing catalog to Redis '{PRICING_CATALOG_CACHE_KEY}'."
        )

        # Prepare MongoDB data
        (
            parsed_config_for_mongo,
            products_to_save_mongo,
            generators_to_save_mongo,
        ) = self._prepare_pricing_data_for_mongo(pricing_catalog)

        # Sync to MongoDB
        pricing_synced_successfully, critical_fetch_error = (
            await self._sync_pricing_to_mongodb(
                parsed_config_for_mongo,
                products_to_save_mongo,
                generators_to_save_mongo,
                background_tasks,
            )
        )
      else:
        error_msg = f"Failed to store pricing catalog in Redis key '{PRICING_CATALOG_CACHE_KEY}'."
        logfire.error(
            f"SheetSyncService: PRICING SYNC ERROR (Redis) - {error_msg}"
        )
        if background_tasks:
          background_tasks.add_task(
              log_error_bg,
              self.redis_service,
              "RedisStoreError",
              error_msg,
              {"key": PRICING_CATALOG_CACHE_KEY},
          )
        critical_fetch_error = True
    except Exception as e:
      error_msg = (
          "PRICING SYNC ERROR: Error processing or caching pricing catalog"
      )
      logfire.exception(error_msg, exc_info=e)
      if background_tasks:
        background_tasks.add_task(
            log_error_bg,
            self.redis_service,
            "CatalogProcessingError",
            str(e),
        )
      critical_fetch_error = True

    return pricing_synced_successfully, critical_fetch_error

  async def _sync_pricing_to_mongodb(
      self,
      parsed_config_for_mongo: Dict[str, Any],
      products_to_save_mongo: List[Dict[str, Any]],
      generators_to_save_mongo: List[Dict[str, Any]],
      background_tasks: Optional[BackgroundTasks] = None,
  ) -> Tuple[bool, bool]:
    """
    Sync pricing data to MongoDB.
    Returns a tuple of (pricing_synced_successfully, critical_fetch_error)
    """
    mongo_product_sync_ok = False
    mongo_generator_sync_ok = False
    mongo_config_sync_ok = False
    critical_fetch_error = False

    try:
      await self.mongo_service.replace_sheet_collection_data(
          collection_name=SHEET_PRODUCTS_COLLECTION,
          data=products_to_save_mongo,
          id_field="id",
      )
      logfire.info(
          f"SheetSyncService: PRICING SYNC SUCCESS (MongoDB Products) - Synced {len(products_to_save_mongo)} products to '{SHEET_PRODUCTS_COLLECTION}'."
      )
      mongo_product_sync_ok = True
    except Exception as mongo_e_prod:
      error_msg_prod = f"PRICING SYNC ERROR (MongoDB Products): Failed to sync products to '{SHEET_PRODUCTS_COLLECTION}'. Error: {mongo_e_prod}"
      logfire.error(error_msg_prod, exc_info=True)
      if background_tasks:
        background_tasks.add_task(
            log_error_bg,
            self.redis_service,
            "MongoStoreErrorProducts",
            str(mongo_e_prod),
            {"collection": SHEET_PRODUCTS_COLLECTION},
        )
      critical_fetch_error = True

    try:
      await self.mongo_service.replace_sheet_collection_data(
          collection_name=SHEET_GENERATORS_COLLECTION,
          data=generators_to_save_mongo,
          id_field="id",
      )
      logfire.info(
          f"SheetSyncService: PRICING SYNC SUCCESS (MongoDB Generators) - Synced {len(generators_to_save_mongo)} generators to '{SHEET_GENERATORS_COLLECTION}'."
      )
      mongo_generator_sync_ok = True
    except Exception as mongo_e_gen:
      error_msg_gen = f"PRICING SYNC ERROR (MongoDB Generators): Failed to sync generators to '{SHEET_GENERATORS_COLLECTION}'. Error: {mongo_e_gen}"
      logfire.error(error_msg_gen, exc_info=True)
      if background_tasks:
        background_tasks.add_task(
            log_error_bg,
            self.redis_service,
            "MongoStoreErrorGenerators",
            str(mongo_e_gen),
            {"collection": SHEET_GENERATORS_COLLECTION},
        )
      critical_fetch_error = True

    try:
      await self.mongo_service.upsert_sheet_config_document(
          document_id="master_config",
          config_data=parsed_config_for_mongo,
          config_type="pricing_and_delivery",
      )
      logfire.info(
          f"SheetSyncService: PRICING SYNC SUCCESS (MongoDB Config) - Upserted config to '{SHEET_CONFIG_COLLECTION}'."
      )
      mongo_config_sync_ok = True
    except Exception as mongo_e_conf:
      error_msg_conf = f"PRICING SYNC ERROR (MongoDB Config): Failed to upsert config to '{SHEET_CONFIG_COLLECTION}'. Error: {mongo_e_conf}"
      logfire.error(error_msg_conf, exc_info=True)
      if background_tasks:
        background_tasks.add_task(
            log_error_bg,
            self.redis_service,
            "MongoStoreErrorConfig",
            str(mongo_e_conf),
            {"collection": SHEET_CONFIG_COLLECTION},
        )
      critical_fetch_error = True

    pricing_synced_successfully = (
        mongo_product_sync_ok and mongo_generator_sync_ok and mongo_config_sync_ok
    )

    if not pricing_synced_successfully:
      logfire.error(
          "SheetSyncService: PRICING SYNC FAILED (MongoDB) - One or more parts of pricing data failed to sync to MongoDB."
      )

    return pricing_synced_successfully, critical_fetch_error

  def _validate_parsed_data(
      self, pricing_catalog: Dict[str, Any]
  ) -> Dict[str, Dict[str, List[str]]]:
    """
    Validates that all required fields are present in the parsed pricing data.
    Returns a dictionary of validation issues found.
    """
    validation_issues = {"products": {}, "generators": {}}

    # Validate Products
    products = pricing_catalog.get("products", {})
    for product_id, product in products.items():
      missing_fields = []

      # Check for essential pricing fields
      required_fields = [
          "weekly_7_day",
          "rate_28_day",
          "rate_2_5_month",
          "rate_6_plus_month",
          "event_standard",
      ]

      for field in required_fields:
        if product.get(field) is None:
          missing_fields.append(field)

      if missing_fields:
        validation_issues["products"][product_id] = missing_fields

    # Validate Generators
    generators = pricing_catalog.get("generators", {})
    for generator_id, generator in generators.items():
      missing_fields = []

      # Check for essential pricing fields
      required_fields = ["rate_7_day", "rate_28_day"]

      # Determine if this is a large generator (20kW+) where event rate is often N/A
      is_large_generator = "kw generator" in generator_id.lower() and not (
          "3kw" in generator_id.lower() or "7kw" in generator_id.lower()
      )

      # Only require event rate for smaller generators
      if not is_large_generator:
        required_fields.append("rate_event")

      for field in required_fields:
        if generator.get(field) is None:
          # For large generators, we're more lenient about missing event rates
          if field == "rate_event" and is_large_generator:
            logfire.debug(
                f"Generator '{generator_id}': Missing {field} is acceptable for larger generators"
            )
          else:
            missing_fields.append(field)

      if missing_fields:
        validation_issues["generators"][generator_id] = missing_fields

    return validation_issues

  async def _run_sync_loop(self):
    logfire.info(
        f"SheetSyncService: Starting background sync loop (Interval: {SYNC_INTERVAL_SECONDS}s)"
    )
    loop = asyncio.get_running_loop()  # Get loop once for the loop
    while True:
      try:
        logfire.info(
            "SheetSyncService: Re-building sheet service for periodic sync (in executor)..."
        )
        try:
          self.sheet_service = await loop.run_in_executor(
              None, create_sheets_service, settings.GOOGLE_APPLICATION_CREDENTIALS or ""
          )
          logfire.info(
              "SheetSyncService: Sheet service re-built successfully for periodic sync (in executor)."
          )
        except asyncio.CancelledError:
          logfire.info(
              "SheetSyncService: Service build cancelled during sync loop. Exiting loop."
          )
          break  # Exit the main while True loop
        except Exception as build_err:
          logfire.error(
              f"SheetSyncService: Failed to re-build sheet service in loop: {build_err}",
              exc_info=True,
          )
          self.sheet_service = None  # Ensure service is None if build failed

        if self.sheet_service:
          bg_tasks = BackgroundTasks()
          await self.sync_full_catalog(
              background_tasks=bg_tasks
          )  # Renamed method call
        else:
          logfire.warning(
              "SheetSyncService: Skipping sync cycle as sheet service is not available (build failed or was not attempted)."
          )

      except (
          asyncio.CancelledError
      ):  # Catch cancellation during sync_full_catalog or other parts of try
        logfire.info(
            "SheetSyncService: Sync operation cancelled. Exiting loop."
        )
        break  # Exit the main while True loop
      except Exception as e:
        logfire.error(
            f"SheetSyncService: Unhandled exception in sync loop's main logic - {e}",
            exc_info=True,
        )
        try:
          await log_error_bg(self.redis_service, "SyncLoopError", str(e))
        except asyncio.CancelledError:
          logfire.info(
              "SheetSyncService: Logging to Redis was cancelled during error handling. Exiting loop."
          )
          break  # Exit the main while True loop
        except Exception as log_e:
          logfire.error(
              f"SheetSyncService: Failed to log sync loop error to Redis - {log_e}"
          )

      # Sleep part, always subject to cancellation
      try:
        logfire.debug(
            f"SheetSyncService: Sync loop sleeping for {SYNC_INTERVAL_SECONDS} seconds."
        )
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
      except asyncio.CancelledError:
        logfire.info(
            "SheetSyncService: Sync loop's sleep was cancelled. Exiting loop."
        )
        break  # Exit the main while True loop

    logfire.info("SheetSyncService: Background sync loop has finished.")

  async def _perform_initial_sync(self):
    """Wrapper to perform and log the initial sync as a background task."""
    logfire.info("SheetSyncService: Initial sync task started in background.")
    bg_tasks_for_initial_sync = (
        BackgroundTasks()
    )  # For logging within this specific sync run
    try:
      initial_sync_success = await self.sync_full_catalog(
          background_tasks=bg_tasks_for_initial_sync
      )  # Renamed method call
      if not initial_sync_success:
        logfire.warning(
            "SheetSyncService: Initial sync performed in background failed. Subsequent syncs will retry."
        )
      else:
        logfire.info(
            "SheetSyncService: Initial sync performed in background completed successfully."
        )
    except Exception as e:
      logfire.error(
          f"SheetSyncService: Exception during initial background sync: {e}",
          exc_info=True,
      )
      # Optionally log this critical error to Redis as well
      try:
        await log_error_bg(self.redis_service, "InitialSyncError", str(e))
      except Exception as log_e:
        logfire.error(f"Failed to log initial sync error to Redis: {log_e}")

  async def start_background_sync(self):
    if self._sync_task is None or self._sync_task.done():
      logfire.info("SheetSyncService: Starting background sync loop task.")
      self._sync_task = asyncio.create_task(self._run_sync_loop())
      logfire.info(
          "SheetSyncService: Background sync loop task created and started."
      )
    else:
      logfire.info(
          "SheetSyncService: Background sync task is already running.")

  async def stop_background_sync(self):
    if self._sync_task and not self._sync_task.done():
      logfire.info(
          "SheetSyncService: Attempting to stop background sync task...")
      self._sync_task.cancel()
      try:
        await self._sync_task
        # This means the task completed its execution run after cancel() was called,
        # likely because it caught CancelledError internally and exited its loop.
        logfire.info(
            "SheetSyncService: Background sync task finished execution after cancellation request."
        )
      except asyncio.CancelledError:
        # This is the expected exception if the task is cancelled while awaited.
        logfire.info(
            "SheetSyncService: Background sync task was successfully cancelled."
        )
      except Exception as e:
        # For any other unexpected errors during the task's shutdown.
        logfire.error(
            f"SheetSyncService: Background sync task encountered an unexpected error during stop: {e}",
            exc_info=True,
        )
    elif self._sync_task and self._sync_task.done():
      logfire.info(
          "SheetSyncService: Background sync task was already done when stop was requested."
      )
      # Optionally, check if it had an error if it wasn't explicitly cancelled.
      try:
        self._sync_task.result()  # This would re-raise an exception if the task died on its own
      except asyncio.CancelledError:
        logfire.info(
            "SheetSyncService: (Task was already done and had been previously cancelled.)"
        )
      except Exception as e:
        logfire.warning(
            f"SheetSyncService: (Task was already done and had an unhandled error: {e})",
            exc_info=True,
        )
    else:
      logfire.info(
          "SheetSyncService: No active background sync task to stop (or task never started)."
      )

  def _handle_csv_edge_cases(self, pricing_catalog: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle specific edge cases in CSV data such as:
    - Inconsistently formatted currency values
    - Missing required fields that need default values
    - Special handling for specific product or generator types

    Returns the pricing catalog with edge cases handled.
    """
    # Handle products edge cases
    for product_id, product in pricing_catalog.get("products", {}).items():
      # Fill in missing pricing tiers with appropriate defaults when possible
      if product.get("event_standard") is not None:
        # If we have event_standard but missing other event tiers, use the standard price
        for event_tier in [
            "event_premium",
            "event_premium_plus",
            "event_premium_platinum",
        ]:
          if product.get(event_tier) is None:
            product[event_tier] = product["event_standard"]
            logfire.debug(
                f"Product '{product_id}': Added default {event_tier}=${product[event_tier]:.2f} from event_standard"
            )

      # Apply business logic for pricing tiers
      # If 6+ month pricing is not available, use 2-5 month pricing
      if (
          product.get("rate_6_plus_month") is None
          and product.get("rate_2_5_month") is not None
      ):
        product["rate_6_plus_month"] = product["rate_2_5_month"]
        logfire.debug(
            f"Product '{product_id}': Added default rate_6_plus_month=${product['rate_6_plus_month']:.2f} from rate_2_5_month"
        )

      # If 18+ month pricing is not available, use 6+ month pricing
      if (
          product.get("rate_18_plus_month") is None
          and product.get("rate_6_plus_month") is not None
      ):
        product["rate_18_plus_month"] = product["rate_6_plus_month"]
        logfire.debug(
            f"Product '{product_id}': Added default rate_18_plus_month=${product['rate_18_plus_month']:.2f} from rate_6_plus_month"
        )

    # Handle generators edge cases
    for generator_id, generator in pricing_catalog.get("generators", {}).items():
      # Default handling for 'n/a' event rates for larger generators
      if (
          generator.get("rate_event") is None
          and "kw generator" in generator_id.lower()
      ):
        if generator.get("rate_7_day") is not None:
          # For larger generators without event rates, we can calculate a default rate
          # based on the 7-day rate
          pass # Explicitly do nothing if we want to keep None

    return pricing_catalog


# --- Integration with FastAPI Lifespan ---

_sheet_sync_service_instance: Optional[SheetSyncService] = None


async def _run_initial_sync_after_delay(
    service_instance: SheetSyncService, delay_seconds: int
):
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
      mongo_service = await get_mongo_service()  # Get Mongo service instance

      _sheet_sync_service_instance = SheetSyncService(
          redis_service, mongo_service
      )  # Pass mongo_service
      # Await the initialization of the service itself (which builds the google client)
      await _sheet_sync_service_instance.initialize_service()
      # Now start the background sync tasks (which run the first sync in the background after delay)
      await _sheet_sync_service_instance.start_background_sync()
      # Schedule the initial sync to run after a delay in the background
      asyncio.create_task(
          _run_initial_sync_after_delay(_sheet_sync_service_instance, 30)
      )
      logfire.info(
          "SYNC LIFESPAN: SheetSyncService initialized, background loop started, initial sync scheduled with delay."
      )
    except RuntimeError as e:
      logfire.error(
          f"SYNC LIFESPAN: CRITICAL - Failed to get required Redis or Mongo service: {e}",
          exc_info=True,
      )  # Updated log
      # Prevent service from being considered initialized if Redis failed
      _sheet_sync_service_instance = None
    except Exception as e:
      logfire.error(
          f"SYNC LIFESPAN: CRITICAL - Failed to initialize or start SheetSyncService: {e}",
          exc_info=True,
      )
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
    logfire.info(
        "SYNC LIFESPAN: SheetSyncService not running or already stopped.")
