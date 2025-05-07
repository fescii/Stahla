# filepath: /home/femar/AO3/Stahla/app/models/location.py
from pydantic import BaseModel, Field

class BranchLocation(BaseModel):
    """Represents a Stahla branch location."""
    name: str
    address: str

class DistanceResult(BaseModel):
    """Represents the result of a distance calculation."""
    nearest_branch: BranchLocation
    delivery_location: str
    distance_miles: float = Field(..., description="Driving distance in miles")
    distance_meters: int = Field(..., description="Driving distance in meters")
    duration_seconds: int = Field(..., description="Driving duration in seconds")
