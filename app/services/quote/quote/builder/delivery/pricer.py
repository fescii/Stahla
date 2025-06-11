# app/services/quote/quote/builder/delivery/pricer.py

"""
Delivery pricing builder component.
"""

import logging
from typing import Any, Dict

import logfire

logger = logging.getLogger(__name__)


class DeliveryPricer:
  """Handles delivery pricing calculations for quote building."""

  def __init__(self, quote_service):
    self.quote_service = quote_service

  async def calculate_delivery_cost(
      self,
      quote_request: Any,
      catalog: Dict[str, Any],
      distance_result: Any
  ) -> Dict[str, Any]:
    """
    Calculate delivery cost using the dedicated DeliveryCalculator.

    Args:
        quote_request: The quote request object
        catalog: The pricing catalog
        distance_result: The calculated distance

    Returns:
        Dictionary with delivery cost details
    """
    try:
      # Delegate to the dedicated delivery calculator
      delivery_result = await self.quote_service.delivery._calculate_delivery_cost(
          quote_request=quote_request,
          catalog=catalog,
          distance_result=distance_result
      )

      return {
          "delivery_cost": delivery_result.get("delivery_cost", 0.0),
          "delivery_details": delivery_result.get("delivery_details", {}),
          "success": True
      }

    except Exception as e:
      logfire.error(f"Error calculating delivery cost: {e}")
      return {
          "delivery_cost": 0.0,
          "delivery_details": {},
          "success": False,
          "error": str(e)
      }
