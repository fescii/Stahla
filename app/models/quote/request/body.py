"""
Quote request model definition.
"""

from pydantic import BaseModel, Field, field_validator
import uuid
from datetime import date
from typing import List, Literal

from .extras.input import ExtraInput


class QuoteRequest(BaseModel):
  """Input payload for the /v1/webhook/quote endpoint."""

  request_id: str = Field(
      default_factory=lambda: str(uuid.uuid4()),
      description="Unique identifier for this quote request.",
  )
  delivery_location: str = Field(
      ...,
      description="Full delivery address (Street, City, State, Zip).",
  )
  trailer_type: str = Field(
      ..., description="Specific Stahla trailer model ID."
  )
  rental_start_date: date = Field(
      ..., description="Rental start date in YYYY-MM-DD format."
  )
  rental_days: int = Field(..., gt=0,
                           description="Total rental duration in days.")
  usage_type: Literal["commercial", "event"] = Field(
      ..., description="Normalized usage type."
  )
  extras: List[ExtraInput] = Field(
      default_factory=list, description="List of requested extra items."
  )

  @field_validator("rental_start_date", mode="before")
  @classmethod
  def parse_date(cls, value):
    if isinstance(value, str):
      try:
        return date.fromisoformat(value)
      except ValueError:
        raise ValueError("Invalid date format, expected YYYY-MM-DD")
    return value

  class Config:
    json_schema_extra = {
        "example": {
            "request_id": "req_abc123",
            "delivery_location": "456 Oak Ave, Otherville, CA 95678",
            "trailer_type": "standard_3_stall_ada",
            "rental_start_date": "2025-07-10",
            "rental_days": 7,
            "usage_type": "event",
            "extras": [
                {"extra_id": "generator_10kw", "qty": 1},
                {"extra_id": "attendant_service", "qty": 1},
            ],
        }
    }
