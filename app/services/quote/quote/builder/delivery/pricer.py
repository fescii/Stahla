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
      # Determine the season from start date
      season_desc = "Standard"  # Default season description

      # Delegate to the dedicated delivery calculator
      delivery_result = await self.quote_service.delivery.calculate_delivery_cost(
          distance_result=distance_result,
          catalog=catalog,
          rate_multiplier=1.0,  # Default multiplier
          season_desc=season_desc,
          is_distance_estimated=distance_result.is_estimated if hasattr(
              distance_result, 'is_estimated') else False
      )

      # Get delivery cost either from delivery_cost or cost key
      delivery_cost = delivery_result.get(
          "delivery_cost", delivery_result.get("cost", 0.0))

      # Always ensure delivery_cost is a number, not None
      if delivery_cost is None:
        delivery_cost = 0.0

      # Ensure delivery details match the expected DeliveryCostDetails model
      delivery_details = {
          "miles": distance_result.distance_miles,
          "calculation_reason": delivery_result.get("tier_description", "Standard delivery rate"),
          "total_delivery_cost": delivery_cost,
          "original_per_mile_rate": delivery_result.get("original_per_mile_rate", 0.0),
          "original_base_fee": delivery_result.get("original_base_fee", 0.0),
          "seasonal_multiplier_applied": delivery_result.get("seasonal_multiplier_applied", 1.0),
          "per_mile_rate_applied": delivery_result.get("per_mile_rate_applied", 0.0),
          "base_fee_applied": delivery_result.get("base_fee_applied", 0.0),
          "is_distance_estimated": delivery_result.get("is_estimated", False),
          "tier_name": delivery_result.get("tier_description", "Standard")
      }

      return {
          "delivery_cost": delivery_cost,
          "delivery_details": delivery_details,
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
