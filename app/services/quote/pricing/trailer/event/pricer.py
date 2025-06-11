# app/services/quote/pricing/trailer/event/pricer.py

"""
Event pricing logic for trailers (≤ 4 days).
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class EventPricer:
  """Handles event pricing for short-term trailer rentals."""

  def __init__(self, fallback_helper):
    self.fallback_helper = fallback_helper

  def calculate_event_price(
      self,
      trailer_id: str,
      rental_days: int,
      product_info: Dict[str, Any],
  ) -> Tuple[Optional[float], str]:
    """
    Calculate event pricing for trailers rented for 4 days or less.

    Args:
        trailer_id: ID of the trailer
        rental_days: Number of rental days
        product_info: Product information from catalog

    Returns:
        Tuple of (cost, description_suffix)
    """
    if rental_days > 4:
      return None, ""

    event_tier_key = "event_standard"  # Default to standard event price
    cost = product_info.get(event_tier_key)
    description_suffix = ""

    if cost is None:
      # Try to get fallback price
      cost, fallback_suffix = self.fallback_helper.get_fallback_price(
          product_info, event_tier_key, rental_days
      )
      if cost is None:
        logger.error(
            f"Base event price ('{event_tier_key}') not found for trailer '{trailer_id}' and no fallback available. Cannot calculate event price."
        )
        return None, ""

      tier_name = (
          event_tier_key.replace("event_", "").replace("_", " ").title()
      )
      description_suffix = (
          f"(Event <= 4 days - {tier_name}) {fallback_suffix}"
      )

      # Safe formatting for log
      cost_str = f"${cost:.2f}" if isinstance(
          cost, (int, float)) else str(cost)
      logger.info(
          f"Using fallback price for '{event_tier_key}' for trailer '{trailer_id}': {cost_str} {fallback_suffix}"
      )
    else:
      tier_name = (
          event_tier_key.replace("event_", "").replace("_", " ").title()
      )
      description_suffix = f"(Event <= 4 days - {tier_name})"

      # Safe formatting for log
      cost_str = f"${cost:.2f}" if isinstance(
          cost, (int, float)) else str(cost)
      logger.info(
          f"Base Event pricing ({event_tier_key}) for '{trailer_id}': {cost_str}"
      )

    return cost, description_suffix
