# app/services/quote/pricing/trailer/commercial/period/calculator.py

"""
Period-based pricing calculator for 28-day and weekly rates.
"""

import logging
import math
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class PeriodCalculator:
  """Handles period-based pricing calculations for 28-day and weekly rates."""

  def __init__(self, fallback_helper):
    self.fallback_helper = fallback_helper

  def calculate_28_day_rate(
      self,
      rental_days: int,
      product_info: Dict[str, Any],
      trailer_id: str,
  ) -> Tuple[Optional[float], str]:
    """
    Calculate cost using 28-day rate periods.

    Args:
        rental_days: Number of rental days
        product_info: Product information from catalog
        trailer_id: ID of the trailer (for logging)

    Returns:
        Tuple of (base_cost, description_suffix)
    """
    if rental_days < 28:
      return None, ""

    rate_28_day = product_info.get("rate_28_day")

    if rate_28_day is not None:
      num_28_day_periods = rental_days / 28
      base_cost = rate_28_day * num_28_day_periods  # Prorate 28-day rate
      rate_tier_desc = "Prorated 28 Day Rate"
      description_suffix = f"({rental_days} days - {rate_tier_desc})"

      cost_str = f"${base_cost:.2f}" if isinstance(
          base_cost, (int, float)) else str(base_cost)
      logger.info(
          f"Base rate: {rate_tier_desc} for '{trailer_id}': {cost_str}"
      )

      return base_cost, description_suffix
    else:
      # Try fallback for 28-day rate
      fallback_rate, fallback_suffix = self.fallback_helper.get_fallback_price(
          product_info, "rate_28_day", rental_days
      )
      if fallback_rate is not None:
        num_28_day_periods = rental_days / 28
        base_cost = fallback_rate * num_28_day_periods
        rate_tier_desc = f"Prorated 28 Day Rate {fallback_suffix}"
        description_suffix = f"({rental_days} days - {rate_tier_desc})"

        cost_str = f"${base_cost:.2f}" if isinstance(
            base_cost, (int, float)) else str(base_cost)
        logger.info(
            f"Base rate: Using fallback for 28-Day Rate for '{trailer_id}': {cost_str} {fallback_suffix}"
        )

        return base_cost, description_suffix

    return None, ""

  def calculate_weekly_rate(
      self,
      rental_days: int,
      product_info: Dict[str, Any],
      trailer_id: str,
  ) -> Tuple[Optional[float], str]:
    """
    Calculate cost using weekly rates.

    Args:
        rental_days: Number of rental days
        product_info: Product information from catalog
        trailer_id: ID of the trailer (for logging)

    Returns:
        Tuple of (base_cost, description_suffix)
    """
    rate_weekly = product_info.get("weekly_7_day")

    if rate_weekly is not None:
      num_weeks = math.ceil(rental_days / 7)  # Charge full weeks
      base_cost = rate_weekly * num_weeks
      rate_tier_desc = "Weekly Rate"
      description_suffix = (
          f"({rental_days} days / {num_weeks} weeks - {rate_tier_desc})"
      )

      cost_str = f"${base_cost:.2f}" if isinstance(
          base_cost, (int, float)) else str(base_cost)
      logger.info(
          f"Base rate: {rate_tier_desc} for '{trailer_id}': {cost_str}"
      )

      return base_cost, description_suffix
    else:
      # Try fallback for weekly rate
      fallback_rate, fallback_suffix = self.fallback_helper.get_fallback_price(
          product_info, "weekly_7_day", rental_days
      )
      if fallback_rate is not None:
        num_weeks = math.ceil(rental_days / 7)
        base_cost = fallback_rate * num_weeks
        rate_tier_desc = f"Weekly Rate {fallback_suffix}"
        description_suffix = f"({rental_days} days / {num_weeks} weeks - {rate_tier_desc})"

        cost_str = f"${base_cost:.2f}" if isinstance(
            base_cost, (int, float)) else str(base_cost)
        logger.info(
            f"Base rate: Using fallback for Weekly Rate for '{trailer_id}': {cost_str} {fallback_suffix}"
        )

        return base_cost, description_suffix

    return None, ""
