from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# --- Request Models ---

class ClearCacheRequest(BaseModel):
    key: str = Field(..., description="The specific cache key to clear.")

class ClearPricingCacheRequest(BaseModel):
    confirm: bool = Field(..., description="Confirmation flag to clear the entire pricing cache.")

# --- Response Models ---

class CacheItem(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = Field(None, description="Remaining time-to-live in seconds, -1 if no expire, -2 if key does not exist.")

class CacheSearchResult(BaseModel):
    key: str
    # Value might be large, optionally omit or truncate in response
    value_preview: Optional[str] = Field(None, description="Preview of the cached value (truncated).")
    ttl: Optional[int] = None

class CacheStats(BaseModel):
    pricing_cache_last_updated: Optional[str] = None
    pricing_cache_size_kb: Optional[float] = None # Approximate
    maps_cache_key_count: int = 0
    # Add hit/miss ratio if tracked (requires more complex implementation)
    hit_miss_ratio_pricing: Optional[str] = "Not Tracked"
    hit_miss_ratio_maps: Optional[str] = "Not Tracked"

class SyncStatus(BaseModel):
    last_successful_sync_timestamp: Optional[str] = None
    is_sync_task_running: Optional[bool] = None
    # TODO: Add recent errors if logged systematically
    recent_errors: List[str] = Field(default_factory=list, description="List of recent sync error messages (if available).")

class ExternalServiceStatus(BaseModel):
    google_maps_api_calls: Optional[int] = Field(None, description="Count of calls made (requires tracking).")
    google_maps_api_errors: Optional[int] = Field(None, description="Count of errors (requires tracking).")
    google_sheet_sync: SyncStatus

class RequestLogEntry(BaseModel):
    timestamp: datetime
    request_id: str
    endpoint: str # e.g., /webhook/quote
    request_payload: Optional[Dict[str, Any]] = None # Store the request body
    response_payload: Optional[Dict[str, Any]] = None # Store the response or error
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None

class ErrorLogEntry(BaseModel):
    timestamp: datetime
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    count: int = 1 # For aggregation

class DashboardOverview(BaseModel):
    # I. Monitoring
    quote_requests_total: Optional[int] = Field(None, description="Total requests to /webhook/quote (requires tracking).")
    quote_requests_success: Optional[int] = Field(None, description="Successful quote requests (requires tracking).")
    quote_requests_error: Optional[int] = Field(None, description="Failed quote requests (requires tracking).")
    quote_latency_p95_ms: Optional[float] = Field(None, description="95th percentile latency for /webhook/quote (requires tracking).")
    location_lookups_total: Optional[int] = Field(None, description="Total requests to /webhook/location_lookup (requires tracking).")
    cache_stats: CacheStats
    external_services: ExternalServiceStatus
    error_summary: List[ErrorLogEntry] = Field(default_factory=list, description="Summary of recent error types and counts.")
    # II. Management Data (for context)
    recent_requests: List[RequestLogEntry] = Field(default_factory=list, description="Last N quote requests/responses.")
