# app/services/quote/utils/constants.py

"""
Constants used throughout the quote service.
Excludes cache keys (moved to app.core.keys for centralization).
"""

# Constants for pricing logic
DAYS_PER_MONTH_APPROX = 30.4375  # Average days in a month
MONTHS_2 = 2
MONTHS_6 = 6
MONTHS_18 = 18

# Collection constants
SHEET_CONFIG_COLLECTION = "sheet_config"
SHEET_PRODUCTS_COLLECTION = "products"  # Collection for products
SHEET_GENERATORS_COLLECTION = "generators"  # Collection for generators

# Sync configuration
SYNC_INTERVAL_SECONDS = 60 * 60 * 24  # Sync every 1 day

# Header mappings for sheet parsing (from original sync.py)
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
