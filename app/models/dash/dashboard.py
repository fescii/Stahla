from pydantic import BaseModel, Field, validator  # Add validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone

# --- Request Models ---


class ClearCacheRequest(BaseModel):
  key: str = Field(..., description="The specific cache key to clear.")


class ClearPricingCacheRequest(BaseModel):
  confirm: bool = Field(...,
                        description="Confirmation flag to clear the entire pricing cache.")

# --- Response Models ---


class CacheItem(BaseModel):
  key: str
  value: Any
  ttl: Optional[int] = Field(
      None, description="Remaining time-to-live in seconds, -1 if no expire, -2 if key does not exist.")


class CacheSearchResult(BaseModel):
  key: str
  # Value might be large, store parsed JSON preview if possible, or truncated string.
  value_preview: Optional[Any] = Field(
      None, description="Preview of the cached value (parsed JSON subset or truncated string).")
  ttl: Optional[int] = None


class CacheHitMissRatio(BaseModel):
  percentage: Optional[float] = Field(
      None, description="Cache hit percentage (0.0 to 1.0).")
  hits: int = Field(0, description="Number of cache hits.")
  misses: int = Field(0, description="Number of cache misses.")
  total: int = Field(0, description="Total attempts (hits + misses).")
  status: str = Field(
      "Not Tracked", description="Overall status message, e.g., Not Tracked, N/A (No data).")


class CacheStats(BaseModel):
  total_redis_keys: Optional[int] = None
  redis_memory_used_human: Optional[str] = None
  pricing_cache_last_updated: Optional[str] = None  # Kept as string for now
  pricing_catalog_size_bytes: Optional[int] = None
  maps_cache_key_count: int = 0
  hit_miss_ratio_pricing: Optional[CacheHitMissRatio] = None
  hit_miss_ratio_maps: Optional[CacheHitMissRatio] = None


class SyncStatus(BaseModel):
  last_successful_sync_timestamp: Optional[str] = None  # Kept as string
  is_sync_task_running: bool = False
  recent_sync_errors: List[str] = Field(
      default_factory=list, description="List of recent sync error messages.")

# Redefine ExternalServiceStatus to represent a single service


class ExternalServiceStatus(BaseModel):
  name: str = Field(...,
                    description="Name of the external service (e.g., Google Maps, Bland.ai)")
  status: str = Field(
      "UNKNOWN", description="Current status (e.g., OK, ERROR, UNKNOWN)")
  last_checked: Optional[datetime] = Field(
      None, description="Timestamp of the last status check.")
  details: Optional[str] = Field(
      None, description="Additional details or error message.")


class RequestLogEntry(BaseModel):
  timestamp: datetime
  request_id: str
  endpoint: str  # e.g., /webhook/quote
  request_payload: Optional[Dict[str, Any]] = None  # Store the request body
  # Store the response or error
  response_payload: Optional[Dict[str, Any]] = None
  status_code: Optional[int] = None
  latency_ms: Optional[float] = None


class ErrorLogEntry(BaseModel):
  timestamp: datetime
  error_type: str
  message: str
  details: Optional[Dict[str, Any]] = None
  count: int = 1  # For aggregation


class DashboardOverview(BaseModel):
  report_summary: Dict[str, Any] = Field(default_factory=dict)
  redis_counters: Dict[str, Any] = Field(default_factory=dict)
  recent_errors: List[ErrorLogEntry] = Field(default_factory=list)
  cache_stats: Optional[CacheStats] = None  # Make optional or provide default
  external_services: List[ExternalServiceStatus] = Field(default_factory=list)
  sync_status: Optional[SyncStatus] = None  # Make optional or provide default

  # Fields for quote request stats
  quote_requests_total: int = Field(
      0, description="Total quote requests processed.")
  quote_requests_successful: int = Field(
      0, description="Number of successful quote requests.")
  quote_requests_failed: int = Field(
      0, description="Number of failed quote requests.")

  # Fields for location lookup stats (assuming these might already exist or be part of redis_counters)
  # If they are not explicitly defined, add them. If they are part of redis_counters, ensure mapping.
  location_lookups_total: int = Field(
      0, description="Total location lookups processed.")
  location_lookups_successful: int = Field(
      0, description="Number of successful location lookups.")
  location_lookups_failed: int = Field(
      0, description="Number of failed location lookups.")


class CacheClearResult(BaseModel):
  key: str = Field(..., description="The cache key targeted for clearing.")
  cleared: bool = Field(...,
                        description="Whether the key was found and cleared.")


class ErrorLogResponse(BaseModel):
  errors: List[ErrorLogEntry]

# --- Sheet Data Models ---


class SheetProductEntry(BaseModel):
  id: str = Field(..., description="Product ID from the sheet.")
  name: str = Field(..., description="Product Name from the sheet.")
  weekly_7_day: Optional[float] = None
  rate_28_day: Optional[float] = None
  rate_2_5_month: Optional[float] = None
  rate_6_plus_month: Optional[float] = None
  rate_18_plus_month: Optional[float] = None
  event_standard: Optional[float] = None
  event_premium: Optional[float] = None
  event_premium_plus: Optional[float] = None
  event_premium_platinum: Optional[float] = None
  extras: Optional[Dict[str, Optional[float]]] = Field(
      default_factory=dict, description="Extra service costs like pump_out, fresh_water_fill, etc.")


class SheetGeneratorEntry(BaseModel):
  id: str = Field(..., description="Generator ID from the sheet.")
  name: str = Field(..., description="Generator Name from the sheet.")
  rate_event: Optional[float] = None
  rate_7_day: Optional[float] = None
  rate_28_day: Optional[float] = None

  @validator("rate_event", "rate_7_day", "rate_28_day", pre=True, always=True)
  def parse_empty_string_as_none(cls, v):
    if v == "":
      return None
    return v


class SheetStateEntry(BaseModel):
  state: str = Field(..., description="State name from the sheet.")
  code: str = Field(..., description="State code from the sheet.")

  @validator("state", "code", pre=True, always=True)
  def strip_whitespace(cls, v):
    if isinstance(v, str):
      return v.strip()
    return v


class SheetDeliveryConfig(BaseModel):
  base_fee: Optional[float] = None
  per_mile_rate: Optional[float] = None
  free_miles_threshold: Optional[int] = None


class SheetSeasonalTier(BaseModel):
  name: str
  start_date: str  # ISO date string
  end_date: str  # ISO date string
  rate: float


class SheetSeasonalMultipliersConfig(BaseModel):
  standard: Optional[float] = None
  tiers: List[SheetSeasonalTier] = Field(default_factory=list)


class SheetConfigEntry(BaseModel):
  # Alias for _id
  id: str = Field(..., alias="_id",
                  description="Document ID in MongoDB, e.g., 'master_config'.")
  config_type: Optional[str] = None
  delivery_config: Optional[SheetDeliveryConfig] = None
  seasonal_multipliers_config: Optional[SheetSeasonalMultipliersConfig] = None
  last_updated_mongo: Optional[datetime] = None

  class Config:
    populate_by_name = True  # Allows using alias _id for id field
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }

# --- Generic Sheet Data Response Models ---


class SheetProductsResponse(BaseModel):
  count: int
  data: List[SheetProductEntry]


class SheetGeneratorsResponse(BaseModel):
  count: int
  data: List[SheetGeneratorEntry]


class SheetBranchesResponse(BaseModel):
  count: int
  data: List[Any]  # Using Any for now, ideally List[BranchLocation]
  # from app.models.location import BranchLocation
  # data: List[BranchLocation] # If BranchLocation is confirmed to be used directly


class SheetStatesResponse(BaseModel):
  count: int
  data: List[SheetStateEntry]


class SheetConfigResponse(BaseModel):
  data: Optional[SheetConfigEntry] = None  # Config is a single document
  message: Optional[str] = None  # For status like 'not found'
