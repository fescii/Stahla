"""
Budget details model definition.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any


class BudgetDetails(BaseModel):
  """Detailed breakdown of costs and budget information."""

  subtotal: float = Field(...,
                          description="Subtotal before taxes or additional fees.")
  estimated_total: float = Field(
      ..., description="Estimated total including taxes and fees if provided.")
  daily_rate_equivalent: Optional[float] = Field(
      None, description="Daily rate equivalent for the rental.")
  weekly_rate_equivalent: Optional[float] = Field(
      None, description="Weekly rate equivalent for the rental.")
  monthly_rate_equivalent: Optional[float] = Field(
      None, description="Monthly rate equivalent for the rental.")
  cost_breakdown: Dict[str, float] = Field(
      default_factory=dict, description="Breakdown of costs by category.")
  is_delivery_free: bool = Field(
      ..., description="Whether delivery is free (no charge).")
  discounts_applied: Optional[List[Dict[str, Any]]] = Field(
      None, description="List of any discounts applied.")
