# app/services/quote/pricing/trailer/commercial/rates/tier.py

"""
Rate tier determination for commercial trailer pricing.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from app.services.quote.utils.constants import MONTHS_2, MONTHS_6, MONTHS_18, DAYS_PER_MONTH_APPROX

logger = logging.getLogger(__name__)


class RateTierDeterminer:
  """Determines the appropriate rate tier for commercial pricing."""

  def __init__(self, fallback_helper):
    self.fallback_helper = fallback_helper

  def determine_monthly_rate_tier(
      self,
      rental_days: int,
      product_info: Dict[str, Any],
      trailer_id: str,
  ) -> Tuple[Optional[float], str, str]:
    """
    Determine the appropriate monthly rate tier for the rental period.

    Args:
        rental_days: Number of rental days
        product_info: Product information from catalog
        trailer_id: ID of the trailer (for logging)

    Returns:
        Tuple of (base_monthly_rate, rate_tier_desc, fallback_suffix)
    """
    rental_months = rental_days / DAYS_PER_MONTH_APPROX

    rate_18_plus = product_info.get("rate_18_plus_month")
    rate_6_plus = product_info.get("rate_6_plus_month")
    rate_2_5 = product_info.get("rate_2_5_month")

    base_monthly_rate = None
    rate_tier_desc = ""
    fallback_suffix = ""

    if rental_months >= MONTHS_18:
      if rate_18_plus is not None:
        base_monthly_rate = rate_18_plus
        rate_tier_desc = "18+ Month Rate"
      else:
        # Try fallback for 18+ month rate
        base_monthly_rate, fallback_suffix = self.fallback_helper.get_fallback_price(
            product_info, "rate_18_plus_month", rental_days
        )
        if base_monthly_rate is not None:
          rate_tier_desc = "18+ Month Rate"
          rate_str = f"${base_monthly_rate:.2f}" if isinstance(
              base_monthly_rate, (int, float)) else str(base_monthly_rate)
          logger.info(
              f"Using fallback for 18+ Month Rate for '{trailer_id}': {rate_str} {fallback_suffix}"
          )

    elif rental_months >= MONTHS_6:
      if rate_6_plus is not None:
        base_monthly_rate = rate_6_plus
        rate_tier_desc = "6+ Month Rate"
      else:
        # Try fallback for 6+ month rate
        base_monthly_rate, fallback_suffix = self.fallback_helper.get_fallback_price(
            product_info, "rate_6_plus_month", rental_days
        )
        if base_monthly_rate is not None:
          rate_tier_desc = "6+ Month Rate"
          rate_str = f"${base_monthly_rate:.2f}" if isinstance(
              base_monthly_rate, (int, float)) else str(base_monthly_rate)
          logger.info(
              f"Using fallback for 6+ Month Rate for '{trailer_id}': {rate_str} {fallback_suffix}"
          )

    elif rental_months >= MONTHS_2:
      if rate_2_5 is not None:
        base_monthly_rate = rate_2_5
        rate_tier_desc = "2-5 Month Rate"
      else:
        # Try fallback for 2-5 month rate
        base_monthly_rate, fallback_suffix = self.fallback_helper.get_fallback_price(
            product_info, "rate_2_5_month", rental_days
        )
        if base_monthly_rate is not None:
          rate_tier_desc = "2-5 Month Rate"
          rate_str = f"${base_monthly_rate:.2f}" if isinstance(
              base_monthly_rate, (int, float)) else str(base_monthly_rate)
          logger.info(
              f"Using fallback for 2-5 Month Rate for '{trailer_id}': {rate_str} {fallback_suffix}"
          )

    return base_monthly_rate, rate_tier_desc, fallback_suffix
