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
    recent_errors: List[str] = Field(default_factory=list, description="List of recent sync error messages (if available).")

# Redefine ExternalServiceStatus to represent a single service
class ExternalServiceStatus(BaseModel):
    name: str = Field(..., description="Name of the external service (e.g., Google Maps, Bland.ai)")
    status: str = Field("UNKNOWN", description="Current status (e.g., OK, ERROR, UNKNOWN)")
    last_checked: Optional[datetime] = Field(None, description="Timestamp of the last status check.")
    details: Optional[str] = Field(None, description="Additional details or error message.")

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
    report_summary: Dict[str, Any] = Field(default_factory=dict)
    redis_counters: Dict[str, Any] = Field(default_factory=dict)
    recent_errors: List[ErrorLogEntry] = Field(default_factory=list)
    cache_stats: Optional[CacheStats] = None # Make optional or provide default
    external_services: List[ExternalServiceStatus] = Field(default_factory=list)
    sync_status: Optional[SyncStatus] = None # Make optional or provide default

class CacheClearResult(BaseModel):
    key: str = Field(..., description="The cache key targeted for clearing.")
    cleared: bool = Field(..., description="Whether the key was found and cleared.")

class ErrorLogResponse(BaseModel):
    errors: List[ErrorLogEntry]
