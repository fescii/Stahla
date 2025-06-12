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
      # Unpacking the tuple returned by calculate_trailer_cost
      trailer_cost, description_suffix = self.quote_service.trailer.calculate_trailer_cost(
          trailer_id=quote_request.trailer_type,  # Using trailer_type as the product ID
          rental_days=quote_request.rental_days,  # Using the correct field name
          usage_type=quote_request.usage_type,    # Using the correct field name
          rental_start_date=quote_request.rental_start_date,  # Using the correct field name
          seasonal_config={},  # This will use defaults from catalog
          catalog=catalog,
      )

      return {
          "base_cost": trailer_cost,
          "description_suffix": description_suffix,
          "success": True,
          "source": "catalog"
      }

    except Exception as e:
      logfire.error(f"Error calculating trailer price: {e}")
      return {
          "base_cost": 0.0,
          "description_suffix": "",
          "success": False,
          "error": str(e)
      }
