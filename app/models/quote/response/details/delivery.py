"""
Delivery cost details model definition.
"""

from pydantic import BaseModel, Field
from typing import Optional


class DeliveryCostDetails(BaseModel):
  """Detailed breakdown of the delivery cost calculation."""

  miles: float = Field(..., description="Distance in miles for the delivery.")
  calculation_reason: str = Field(
      ...,
      description="Explanation of how the delivery cost was calculated (e.g., tier name, free delivery rule).",
  )
  total_delivery_cost: float = Field(
      ..., description="Total calculated cost for delivery."
  )
  original_per_mile_rate: Optional[float] = Field(
      None, description="The original per-mile rate before any multipliers."
  )
  original_base_fee: Optional[float] = Field(
      None, description="The original base fee before any multipliers."
  )
  seasonal_multiplier_applied: Optional[float] = Field(
      None, description="Seasonal multiplier applied to delivery, if any."
  )
  per_mile_rate_applied: Optional[float] = Field(
      None,
      description="The per-mile rate applied after any multipliers (original_rate * multiplier).",
  )
  base_fee_applied: Optional[float] = Field(
      None,
      description="The base fee applied after any multipliers (original_fee * multiplier).",
  )
  is_distance_estimated: bool = Field(
      False,
      description="Indicates whether the distance was estimated using fallback calculation.",
  )
