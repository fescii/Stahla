"""
Location details model definition.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LocationDetails(BaseModel):
  """Detailed information about the delivery location and nearest branch."""

  delivery_address: str = Field(
      ..., description="Full delivery address as provided in the request.")
  nearest_branch: str = Field(...,
                              description="Name of the nearest Stahla branch.")
  branch_address: str = Field(...,
                              description="Address of the nearest Stahla branch.")
  distance_miles: float = Field(
      ..., description="Distance in miles between delivery location and nearest branch.")
  estimated_drive_time_minutes: Optional[int] = Field(
      None, description="Estimated drive time in minutes.")
  is_estimated_location: bool = Field(
      False, description="Whether the location details were estimated rather than precisely calculated.")
  geocoded_coordinates: Optional[dict] = Field(
      None, description="Latitude and longitude of the delivery location if available.")
  service_area_type: Optional[str] = Field(
      None, description="Type of service area (e.g., 'Primary', 'Secondary', 'Remote').")
