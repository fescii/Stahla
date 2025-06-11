# app/services/quote/pricing/trailer/commercial/monthly/calculator.py

"""
Monthly rate calculation and prorating logic.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from app.services.quote.utils.constants import DAYS_PER_MONTH_APPROX

logger = logging.getLogger(__name__)


class MonthlyCalculator:
  """Handles monthly rate calculations and prorating."""

  def calculate_prorated_monthly_cost(
      self,
      base_monthly_rate: float,
      rental_days: int,
      rate_tier_desc: str,
      trailer_id: str,
  ) -> Tuple[Optional[float], str]:
    """
    Calculate prorated cost from monthly rate.

    Args:
        base_monthly_rate: Monthly rate to prorate
        rental_days: Number of rental days
        rate_tier_desc: Description of the rate tier
        trailer_id: ID of the trailer (for logging)

    Returns:
        Tuple of (base_cost, description_suffix)
    """
    if not isinstance(base_monthly_rate, (int, float)) or not isinstance(rental_days, (int, float)):
      logger.warning(
          f"Cannot calculate prorated cost: base_monthly_rate ({type(base_monthly_rate)}) or rental_days ({type(rental_days)}) is not numeric."
      )
      return None, ""

    base_cost = (base_monthly_rate / DAYS_PER_MONTH_APPROX) * rental_days
    description_suffix = f"({rental_days} days - Prorated {rate_tier_desc})"

    cost_str = f"${base_cost:.2f}"
    logger.info(
        f"Base rate: Prorated {rate_tier_desc} for '{trailer_id}': {cost_str}"
    )

    return base_cost, description_suffix
