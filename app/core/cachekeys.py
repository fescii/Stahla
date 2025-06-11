"""
Cache key constants used across multiple services.
Centralized location to avoid circular imports.
"""

# ===== CORE SYSTEM CACHE KEYS =====
# Pricing and catalog data
PRICING_CATALOG_CACHE_KEY = "stahla:pricing_catalog"
BRANCH_LIST_CACHE_KEY = "stahla:branches"
STATES_LIST_CACHE_KEY = "stahla:states"

# ===== LOCATION SERVICE CACHE KEYS =====
LOCATION_CACHE_PREFIX = "location:"
COORDINATES_CACHE_KEY = f"{LOCATION_CACHE_PREFIX}coordinates"
DISTANCE_CACHE_KEY = f"{LOCATION_CACHE_PREFIX}distance"
ADDRESS_CACHE_KEY = f"{LOCATION_CACHE_PREFIX}address"
VALIDATION_CACHE_KEY = f"{LOCATION_CACHE_PREFIX}validation"

# ===== QUOTE SERVICE CACHE KEYS =====
QUOTE_CACHE_PREFIX = "quote:"
PRICING_CACHE_KEY = f"{QUOTE_CACHE_PREFIX}pricing"
CATALOG_CACHE_KEY = f"{QUOTE_CACHE_PREFIX}catalog"
DELIVERY_CACHE_KEY = f"{QUOTE_CACHE_PREFIX}delivery"

# ===== DASHBOARD SERVICE CACHE KEYS =====
# Request counters
RECENT_REQUESTS_KEY = "dash:recent_requests"
RECENT_ERRORS_KEY = "dash:recent_errors"

# Quote request metrics
TOTAL_QUOTE_REQUESTS_KEY = "dash:requests:quote:total"
SUCCESS_QUOTE_REQUESTS_KEY = "dash:requests:quote:success"
ERROR_QUOTE_REQUESTS_KEY = "dash:requests:quote:error"
TOTAL_LOCATION_LOOKUPS_KEY = "dash:requests:location:total"

# External API metrics
GMAPS_API_CALLS_KEY = "dash:gmaps:calls"
GMAPS_API_ERRORS_KEY = "dash:gmaps:errors"

# Cache performance metrics
PRICING_CACHE_HITS_KEY = "dash:cache:pricing:hits"
PRICING_CACHE_MISSES_KEY = "dash:cache:pricing:misses"
MAPS_CACHE_HITS_KEY = "dash:cache:maps:hits"
MAPS_CACHE_MISSES_KEY = "dash:cache:maps:misses"

# Dashboard recent requests (different from background)
RECENT_REQUESTS_DASHBOARD_KEY = "dash:requests:recent"

# ===== CACHE TTL SETTINGS =====
DEFAULT_CACHE_TTL = 3600  # 1 hour
SHORT_CACHE_TTL = 300     # 5 minutes
LONG_CACHE_TTL = 86400    # 24 hours
