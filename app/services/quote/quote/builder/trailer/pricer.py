# app/services/quote/quote/builder/trailer/pricer.py

"""
Trailer pricing builder component.
"""

import logging
from typing import Any, Dict

import logfire

logger = logging.getLogger(__name__)


class TrailerPricer:
  """Handles trailer pricing calculations for quote building."""

  def __init__(self, quote_service):
    self.quote_service = quote_service

  async def calculate_trailer_price(
      self,
      quote_request: Any,
      catalog: Dict[str, Any]
  ) -> Dict[str, Any]:
    """
    Calculate trailer pricing using the dedicated TrailerCalculator.

    Args:
        quote_request: The quote request object
        catalog: The pricing catalog

    Returns:
        Dictionary with trailer pricing details
    """
    try:
      # Delegate to the dedicated trailer calculator
      trailer_cost = self.quote_service.trailer._calculate_trailer_cost(
          catalog=catalog,
          product_id=quote_request.product_id,
          rental_type=quote_request.rental_type,
          rental_duration=quote_request.rental_duration,
          rental_duration_unit=quote_request.rental_duration_unit,
          start_date=quote_request.start_date,
      )

      return {
          "base_cost": trailer_cost,
          "success": True,
          "source": "catalog"
      }

    except Exception as e:
      logfire.error(f"Error calculating trailer price: {e}")
      return {
          "base_cost": 0.0,
          "success": False,
          "error": str(e)
      }
