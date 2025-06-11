# app/services/quote/shared/constants.py

"""
Shared constants for the quote service and related modules.
"""

# Import shared cache keys
from app.core.cachekeys import (
    PRICING_CATALOG_CACHE_KEY,
    BRANCH_LIST_CACHE_KEY,
    STATES_LIST_CACHE_KEY,
)

# MongoDB collection names
SHEET_CONFIG_COLLECTION = "sheet_config"
SHEET_PRODUCTS_COLLECTION = "products"
SHEET_GENERATORS_COLLECTION = "generators"
SHEET_BRANCHES_COLLECTION = "branches"

# Pricing calculation constants
DAYS_PER_MONTH_APPROX = 30.4375  # Average days in a month
MONTHS_2 = 2
MONTHS_6 = 6
MONTHS_18 = 18
