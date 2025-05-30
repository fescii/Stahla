# filepath: /home/femar/AO3/Stahla/app/models/location.py
from pydantic import BaseModel, Field
from typing import Optional


# Define the missing request model
class LocationLookupRequest(BaseModel):
  delivery_location: str = Field(
      description="Full delivery address for distance lookup.",
      examples=["1600 Amphitheatre Parkway, Mountain View, CA 94043"],
  )


class BranchLocation(BaseModel):
  """Represents a Stahla branch location."""

  name: str = Field(..., description="Name of the Stahla branch.")
  address: str = Field(..., description="Full address of the Stahla branch.")


class DistanceResult(BaseModel):
  """Represents the result of a distance calculation."""

  nearest_branch: BranchLocation
  delivery_location: str
  distance_miles: float = Field(..., description="Driving distance in miles")
  distance_meters: int = Field(..., description="Driving distance in meters")
  duration_seconds: int = Field(..., description="Driving duration in seconds")
  within_service_area: bool = Field(
      ..., description="Whether the location is within the service area")


class LocationLookupResponse(BaseModel):
  """Response model for synchronous location lookup."""

  distance_result: Optional[DistanceResult] = None
  processing_time_ms: Optional[int] = None
  message: Optional[str] = None  # For errors or other messages
