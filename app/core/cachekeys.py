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

# ===== LATENCY TRACKING CACHE KEYS =====
# Latency tracking using Redis Sorted Sets (for percentiles) and Streams (for time series)
LATENCY_PREFIX = "latency:"

# Sorted Sets for percentile calculations (score = latency_ms, member = timestamp:request_id)
QUOTE_LATENCY_SORTED_SET = f"{LATENCY_PREFIX}quote:percentiles"
LOCATION_LATENCY_SORTED_SET = f"{LATENCY_PREFIX}location:percentiles"
HUBSPOT_LATENCY_SORTED_SET = f"{LATENCY_PREFIX}hubspot:percentiles"
BLAND_LATENCY_SORTED_SET = f"{LATENCY_PREFIX}bland:percentiles"
GMAPS_LATENCY_SORTED_SET = f"{LATENCY_PREFIX}gmaps:percentiles"
REDIS_LATENCY_SORTED_SET = f"{LATENCY_PREFIX}redis:percentiles"

# Redis Streams for time-series latency data (detailed logging)
QUOTE_LATENCY_STREAM = f"{LATENCY_PREFIX}quote:stream"
LOCATION_LATENCY_STREAM = f"{LATENCY_PREFIX}location:stream"
HUBSPOT_LATENCY_STREAM = f"{LATENCY_PREFIX}hubspot:stream"
BLAND_LATENCY_STREAM = f"{LATENCY_PREFIX}bland:stream"
GMAPS_LATENCY_STREAM = f"{LATENCY_PREFIX}gmaps:stream"
REDIS_LATENCY_STREAM = f"{LATENCY_PREFIX}redis:stream"

# Recent latency averages (simple counters for moving averages)
QUOTE_LATENCY_SUM_KEY = f"{LATENCY_PREFIX}quote:sum"
QUOTE_LATENCY_COUNT_KEY = f"{LATENCY_PREFIX}quote:count"
LOCATION_LATENCY_SUM_KEY = f"{LATENCY_PREFIX}location:sum"
LOCATION_LATENCY_COUNT_KEY = f"{LATENCY_PREFIX}location:count"
HUBSPOT_LATENCY_SUM_KEY = f"{LATENCY_PREFIX}hubspot:sum"
HUBSPOT_LATENCY_COUNT_KEY = f"{LATENCY_PREFIX}hubspot:count"
BLAND_LATENCY_SUM_KEY = f"{LATENCY_PREFIX}bland:sum"
BLAND_LATENCY_COUNT_KEY = f"{LATENCY_PREFIX}bland:count"
GMAPS_LATENCY_SUM_KEY = f"{LATENCY_PREFIX}gmaps:sum"
GMAPS_LATENCY_COUNT_KEY = f"{LATENCY_PREFIX}gmaps:count"
REDIS_LATENCY_SUM_KEY = f"{LATENCY_PREFIX}redis:sum"
REDIS_LATENCY_COUNT_KEY = f"{LATENCY_PREFIX}redis:count"

# Latency thresholds for alerting
LATENCY_THRESHOLD_P95_MS = 500  # Target P95 latency
LATENCY_THRESHOLD_P99_MS = 1000  # Alert threshold

# ===== CACHE TTL SETTINGS =====
DEFAULT_CACHE_TTL = 3600  # 1 hour
SHORT_CACHE_TTL = 300     # 5 minutes
LONG_CACHE_TTL = 86400    # 24 hours
