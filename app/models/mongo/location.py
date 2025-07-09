# filepath: app/models/mongo/location.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class LocationStatus(str, Enum):
  """Status of location lookup."""
  PENDING = "pending"
  PROCESSING = "processing"
  SUCCESS = "success"
  FAILED = "failed"
  FALLBACK_USED = "fallback_used"
  GEOCODING_FAILED = "geocoding_failed"
  DISTANCE_CALCULATION_FAILED = "distance_calculation_failed"


class LocationDocument(BaseModel):
  """MongoDB document model for location lookups."""

  id: str = Field(..., description="Unique location lookup identifier, used as _id in MongoDB")
  contact_id: Optional[str] = Field(
      None, description="HubSpot contact ID if available")
  lead_id: Optional[str] = Field(
      None, description="HubSpot lead ID if available")

  # Request details
  delivery_location: str = Field(..., description="Delivery address requested")
  original_query: Optional[str] = Field(
      None, description="Original location query string")

  # Lookup results
  status: LocationStatus = Field(
      LocationStatus.PENDING, description="Status of location lookup")
  lookup_successful: bool = Field(
      False, description="Whether lookup was successful")
  fallback_used: bool = Field(
      False, description="Whether fallback method was used")

  # Distance and branch information
  nearest_branch: Optional[str] = Field(
      None, description="Name of nearest branch")
  nearest_branch_address: Optional[str] = Field(
      None, description="Address of nearest branch")
  distance_miles: Optional[float] = Field(
      None, description="Distance in miles")
  distance_meters: Optional[int] = Field(
      None, description="Distance in meters")
  duration_seconds: Optional[int] = Field(
      None, description="Estimated travel time in seconds")

  # Service area determination
  within_service_area: Optional[bool] = Field(
      None, description="Whether location is within service area")
  is_local: Optional[bool] = Field(
      None, description="Whether location is considered local")
  service_area_type: Optional[str] = Field(
      None, description="Type of service area: primary, secondary, extended")

  # Geocoding results
  geocoded_coordinates: Optional[Dict[str, float]] = Field(
      None, description="Geocoded coordinates {lat, lng}")
  geocoding_successful: bool = Field(
      False, description="Whether geocoding was successful")
  is_distance_estimated: bool = Field(
      False, description="Whether distance is estimated")

  # API and method details
  api_method_used: Optional[str] = Field(
      None, description="API method used: google_maps, fallback, cache")
  geocoding_provider: Optional[str] = Field(
      None, description="Geocoding provider used")
  distance_provider: Optional[str] = Field(
      None, description="Distance calculation provider")

  # Error handling
  error_message: Optional[str] = Field(
      None, description="Error message if lookup failed")
  error_type: Optional[str] = Field(
      None, description="Type of error encountered")
  fallback_reason: Optional[str] = Field(
      None, description="Reason fallback was used")

  # Performance metrics
  processing_time_ms: Optional[int] = Field(
      None, description="Processing time in milliseconds")
  api_calls_made: Optional[int] = Field(
      None, description="Number of API calls made")
  cache_hit: bool = Field(False, description="Whether result was from cache")

  # Complete response data
  full_response_data: Optional[Dict[str, Any]] = Field(
      None, description="Complete API response data")

  # Background task tracking
  background_task_id: Optional[str] = Field(
      None, description="ID of background task that processed this lookup")

  # Timestamps
  lookup_completed_at: Optional[datetime] = Field(
      None, description="When lookup was completed")
  created_at: datetime = Field(
      default_factory=datetime.utcnow, description="Creation timestamp")
  updated_at: datetime = Field(
      default_factory=datetime.utcnow, description="Last update timestamp")

  class Config:
    json_schema_extra = {
        "example": {
            "id": "location_uuid_123",
            "contact_id": "hubspot_contact_123",
            "delivery_location": "123 Main St, Kansas City, KS 66101",
            "original_query": "123 Main St, Kansas City, KS",
            "status": "success",
            "lookup_successful": True,
            "fallback_used": False,
            "nearest_branch": "Kansas City",
            "nearest_branch_address": "456 Branch St, Kansas City, KS 66102",
            "distance_miles": 15.5,
            "distance_meters": 24944,
            "duration_seconds": 1200,
            "within_service_area": True,
            "is_local": True,
            "service_area_type": "primary",
            "geocoded_coordinates": {
                "latitude": 39.0997,
                "longitude": -94.5786
            },
            "geocoding_successful": True,
            "is_distance_estimated": False,
            "api_method_used": "google_maps",
            "geocoding_provider": "google_maps",
            "distance_provider": "google_maps",
            "processing_time_ms": 450,
            "api_calls_made": 2,
            "cache_hit": False,
            "lookup_completed_at": "2025-07-09T10:02:00.000Z"
        }
    }
