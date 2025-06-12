"""
Line item model definition.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LineItem(BaseModel):
  """Represents a single line item in the quote response."""

  description: str = Field(...,
                           description="Description of the item or service.")
  unit_price: Optional[float] = Field(
      None, description="Price per unit (if applicable)."
  )
  quantity: int = Field(..., description="Quantity of the item.")
  total: float = Field(..., description="Total cost for this line item.")
