# app/services/quote/pricing/trailer/fallback/helper.py

"""
Fallback pricing helper for trailer pricing.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class FallbackHelper:
  """Handles fallback pricing logic when primary rates are not available."""

  def get_fallback_price(
      self,
      product_info: Dict[str, Any],
      needed_field: str,
      rental_days: int
  ) -> Tuple[Optional[float], str]:
    """
    Attempts to find a fallback price when the primary pricing field is missing.
    Returns the fallback price and a description of which pricing was used.

    Args:
        product_info: Product information from catalog
        needed_field: The field that was not found
        rental_days: Number of rental days

    Returns:
        Tuple of (fallback_price, fallback_description)
    """
    fallback_logger = logging.getLogger(f"{__name__}.get_fallback_price")

    # Define fallback hierarchies for different pricing fields
    fallback_mappings = {
        # Event pricing fallbacks
        "event_standard": ["event_premium", "weekly_7_day"],
        "event_premium": ["event_standard", "event_premium_plus", "weekly_7_day"],
        "event_premium_plus": ["event_premium", "event_standard", "weekly_7_day"],
        "event_premium_platinum": [
            "event_premium_plus",
            "event_premium",
            "weekly_7_day",
        ],
        # Weekly/monthly pricing fallbacks
        "weekly_7_day": ["rate_28_day", "event_standard"],
        "rate_28_day": ["weekly_7_day", "rate_2_5_month"],
        "rate_2_5_month": ["rate_28_day", "rate_6_plus_month"],
        "rate_6_plus_month": ["rate_2_5_month", "rate_18_plus_month"],
        "rate_18_plus_month": ["rate_6_plus_month", "rate_2_5_month"],
    }

    # Try fallback fields based on the hierarchy
    if needed_field in fallback_mappings:
      for fallback_field in fallback_mappings[needed_field]:
        fallback_price = product_info.get(fallback_field)
        if fallback_price is not None:
          # Safe formatting for log
          price_str = f"${fallback_price:.2f}" if isinstance(
              fallback_price, (int, float)) else str(fallback_price)
          fallback_logger.info(
              f"Using '{fallback_field}' price ({price_str}) as fallback for missing '{needed_field}'"
          )

          # Adjust the price based on duration relationships if needed
          if fallback_field == "weekly_7_day" and needed_field.startswith("rate_"):
            # Adjust weekly rate to monthly equivalent
            adjusted_price = fallback_price * 4.0  # Approximate weekly → monthly
            suffix = f"(Fallback from {fallback_field}, adjusted for {needed_field})"
            return adjusted_price, suffix

          elif fallback_field.startswith("rate_") and needed_field == "weekly_7_day":
            # Adjust monthly rate to weekly equivalent
            adjusted_price = fallback_price / 4.0  # Approximate monthly → weekly
            suffix = f"(Fallback from {fallback_field}, adjusted for {needed_field})"
            return adjusted_price, suffix

          # No adjustment needed
          suffix = f"(Fallback from {fallback_field})"
          return fallback_price, suffix

    # No fallbacks available
    fallback_logger.warning(
        f"No fallback price could be found for missing '{needed_field}'"
    )

    return None, "No price available"
