# app/services/quote/pricing/seasonal/multiplier.py

"""
Seasonal multiplier calculation.
"""

import logging
from typing import Any, Dict, Tuple
from datetime import date

logger = logging.getLogger(__name__)


class SeasonalMultiplier:
  """Handles seasonal pricing multiplier calculations."""

  def __init__(self, manager):
    self.manager = manager

  def determine_seasonal_multiplier(
      self, rental_start_date: date, seasonal_config: Dict[str, Any]
  ) -> Tuple[float, str]:
    """Determines the seasonal rate multiplier based on the start date."""
    standard_rate = seasonal_config.get("standard", 1.0)
    tiers = seasonal_config.get("tiers", [])

    for tier in tiers:
      try:
        tier_start = date.fromisoformat(tier["start_date"])
        tier_end = date.fromisoformat(tier["end_date"])
        if tier_start <= rental_start_date <= tier_end:
          rate = tier.get("rate", standard_rate)
          name = tier.get("name", "Seasonal")
          logger.info(
              f"Applying seasonal tier '{name}' with rate {rate} for start date {rental_start_date}"
          )
          return rate, f" ({name} Season Rate)"
      except (ValueError, KeyError) as e:
        logger.warning(f"Could not parse seasonal tier {tier}: {e}")
        continue  # Skip invalid tiers

    # Default to standard rate if no tier matches
    logger.info(
        f"Applying standard rate {standard_rate} for start date {rental_start_date}"
    )
    return standard_rate, " (Standard Season Rate)"
