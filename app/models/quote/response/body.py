"""
Quote body model definition.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

from ..response.line.item import LineItem
from ..response.details.delivery import DeliveryCostDetails
from ..response.details.rental import RentalDetails
from ..response.details.product import ProductDetails
from ..response.details.budget import BudgetDetails


class QuoteBody(BaseModel):
  """The main body of the quote response."""

  line_items: List[LineItem] = Field(...,
                                     description="Detailed list of charges.")
  subtotal: float = Field(...,
                          description="Subtotal before taxes or potential fees.")
  delivery_tier_applied: Optional[str] = Field(
      None,
      description="Summary name of the delivery pricing tier applied (e.g., 'Free Tier', 'Standard Rate'). This is often the same as part of calculation_reason in delivery_details.",
  )  # Kept for summary, but details are in delivery_details
  delivery_details: Optional[DeliveryCostDetails] = Field(
      None, description="Detailed breakdown of the delivery cost calculation."
  )  # New field
  notes: Optional[str] = Field(
      None, description="Additional notes or disclaimers.")
  rental_details: Optional[RentalDetails] = Field(
      None, description="Detailed information about the rental terms and conditions.")
  product_details: Optional[ProductDetails] = Field(
      None, description="Detailed information about the quoted product.")
  budget_details: Optional[BudgetDetails] = Field(
      None, description="Detailed breakdown of costs and budget information.")
