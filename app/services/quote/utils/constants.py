# app/services/quote/utils/constants.py

"""
Constants used throughout the quote service.
Excludes cache keys (moved to app.core.cachekeys for centralization).
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

# Header mappings for sheet parsing
PRODUCT_HEADER_MAP = {
    "product_id": "product_id",
    "name": "name",
    "description": "description",
    "base_rate": "base_rate",
    "weekly_7_day": "weekly_7_day",
    "rate_28_day": "rate_28_day",
    "rate_2_5_month": "rate_2_5_month",
    "rate_6_plus_month": "rate_6_plus_month",
    "rate_18_plus_month": "rate_18_plus_month",
    "event_standard": "event_standard",
    "event_premium": "event_premium",
    "event_premium_plus": "event_premium_plus",
    "event_premium_platinum": "event_premium_platinum"
}

GENERATOR_HEADER_MAP = {
    "generator_id": "generator_id",
    "name": "name",
    "description": "description",
    "daily_rate": "daily_rate",
    "weekly_rate": "weekly_rate",
    "monthly_rate": "monthly_rate"
}

KNOWN_PRODUCT_EXTRAS_HEADERS = [
    "attendant_service",
    "delivery_setup",
    "cleaning_fee",
    "damage_waiver",
    "weekend_premium"
]
