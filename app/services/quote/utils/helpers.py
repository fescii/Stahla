# app/services/quote/utils/helpers.py

"""
Utility functions for the quote service.
"""

# Re-export constants for backward compatibility
from .constants import (
    DAYS_PER_MONTH_APPROX,
    MONTHS_2,
    MONTHS_6,
    MONTHS_18,
    SHEET_CONFIG_COLLECTION,
    SHEET_PRODUCTS_COLLECTION,
    SHEET_GENERATORS_COLLECTION,
)

# Import cache keys from centralized location
from app.core.keys import (
    PRICING_CATALOG_CACHE_KEY,
    BRANCH_LIST_CACHE_KEY,
)
