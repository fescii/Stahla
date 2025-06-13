# app/services/quote/quote/builder/extras/pricer.py

"""
Extras pricing builder component.
"""

import logging
from typing import Any, Dict

import logfire

logger = logging.getLogger(__name__)


class ExtrasPricer:
  """Handles extras pricing calculations for quote building."""

  def __init__(self, quote_service):
    self.quote_service = quote_service

  async def calculate_extras_cost(
      self,
      quote_request: Any,
      catalog: Dict[str, Any]
  ) -> Dict[str, Any]:
    """
    Calculate extras cost using the dedicated ExtrasCalculator.

    Args:
        quote_request: The quote request object
        catalog: The pricing catalog

    Returns:
        Dictionary with extras cost details
    """
    try:
      # Delegate to the dedicated extras calculator
      extras_items = await self.quote_service.extras.calculate_extras_cost(
          extras_input=quote_request.extras if hasattr(
              quote_request, 'extras') and quote_request.extras else [],
          trailer_id=quote_request.trailer_type,  # Using trailer_type as the product ID
          rental_days=quote_request.rental_days,  # Using the correct field name
          catalog=catalog
      )

      # Calculate total extras cost
      extras_cost = sum(
          item.total for item in extras_items if hasattr(item, 'total'))

      # Prepare result structure
      extras_result = {
          "extras_cost": extras_cost,
          "line_items": [item.model_dump() for item in extras_items]
      }

      return {
          "extras_cost": extras_result.get("extras_cost", 0.0),
          "line_items": extras_result.get("line_items", []),
          "success": True
      }

    except Exception as e:
      logfire.error(f"Error calculating extras cost: {e}")
      return {
          "extras_cost": 0.0,
          "line_items": [],
          "success": False,
          "error": str(e)
      }
