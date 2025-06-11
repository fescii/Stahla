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
      extras_result = await self.quote_service.extras._calculate_extras_cost(
          quote_request=quote_request,
          catalog=catalog
      )

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
