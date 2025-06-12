"""
Rental details model definition.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class RentalDetails(BaseModel):
  """Detailed information about the rental terms and conditions."""

  rental_start_date: date = Field(...,
                                  description="Start date of the rental period.")
  rental_end_date: date = Field(
      ..., description="End date of the rental period (calculated from start date and rental days).")
  rental_days: int = Field(...,
                           description="Total duration of rental in days.")
  rental_weeks: Optional[int] = Field(
      None, description="Number of full weeks in the rental period.")
  rental_months: Optional[float] = Field(
      None, description="Approximate number of months in the rental period.")
  usage_type: str = Field(...,
                          description="Type of usage (commercial or event).")
  pricing_tier_applied: str = Field(
      ..., description="Pricing tier applied based on duration and usage type.")
  seasonal_rate_name: Optional[str] = Field(
      None, description="Name of the seasonal rate applied if any.")
  seasonal_multiplier: float = Field(
      1.0, description="Seasonal rate multiplier applied to the base price.")
