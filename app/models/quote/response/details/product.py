"""
Product details model definition.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ProductDetails(BaseModel):
  """Detailed information about the quoted product."""

  product_id: str = Field(..., description="Product identifier.")
  product_name: str = Field(..., description="Full name of the product.")
  product_description: Optional[str] = Field(
      None, description="Detailed description of the product.")
  base_rate: float = Field(...,
                           description="Base rate before any adjustments.")
  adjusted_rate: float = Field(...,
                               description="Final rate after all adjustments.")
  features: Optional[List[str]] = Field(
      None, description="List of key features of the product.")
  stall_count: Optional[int] = Field(
      None, description="Number of stalls if applicable.")
  is_ada_compliant: Optional[bool] = Field(
      None, description="Whether the product is ADA compliant.")
  trailer_size_ft: Optional[str] = Field(
      None, description="Size of the trailer in feet.")
  capacity_persons: Optional[int] = Field(
      None, description="Maximum recommended capacity in persons.")
