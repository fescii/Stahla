# app/services/quote/pricing/trailer/calculator.py

"""
Main trailer cost calculation orchestrator.
"""

import asyncio
import logging
from datetime import date
from typing import Any, Dict, Optional, Tuple, Literal

from .event.pricer import EventPricer
from .commercial.rates.tier import RateTierDeterminer
from .commercial.period.calculator import PeriodCalculator
from .commercial.monthly.calculator import MonthlyCalculator
from .fallback.helper import FallbackHelper

logger = logging.getLogger(__name__)


class TrailerCalculator:
  """Main orchestrator for trailer cost calculations."""

  def __init__(self, manager):
    self.manager = manager

    # Initialize component calculators
    self.fallback_helper = FallbackHelper()
    self.event_pricer = EventPricer(self.fallback_helper)
    self.rate_tier_determiner = RateTierDeterminer(self.fallback_helper)
    self.period_calculator = PeriodCalculator(self.fallback_helper)
    self.monthly_calculator = MonthlyCalculator()

  def calculate_trailer_cost(
      self,
      trailer_id: str,
      rental_days: int,
      usage_type: Literal["commercial", "event"],
      rental_start_date: date,
      seasonal_config: Dict[str, Any],
      catalog: Dict[str, Any],
  ) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculates the base rental cost for a trailer, applying seasonal multipliers.

    Args:
        trailer_id: ID of the trailer
        rental_days: Number of rental days
        usage_type: Type of usage (commercial or event)
        rental_start_date: Start date of rental
        seasonal_config: Seasonal pricing configuration
        catalog: Pricing catalog

    Returns:
        Tuple of (final_cost, description_suffix)
    """
    logger.info(
        f"Calculating cost for trailer: {trailer_id}, Days: {rental_days}, Usage: {usage_type}, Start: {rental_start_date}"
    )

    products_catalog = catalog.get("products", {})
    product_info = products_catalog.get(trailer_id)

    if not product_info:
      logger.error(
          f"Trailer type '{trailer_id}' not found in pricing catalog.")
      # Log to MongoDB asynchronously
      if self.manager.mongo_service:
        asyncio.create_task(self.manager.mongo_service.log_error_to_db(
            service_name="QuoteService.TrailerCalculator.calculate_trailer_cost",
            error_type="ItemNotFound",
            message=f"Trailer type '{trailer_id}' not found in pricing catalog.",
            details={"trailer_id": trailer_id}
        ))
      return None, None

    # Determine seasonal multiplier first
    rate_multiplier, season_desc = self.manager.seasonal.determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    cost = None
    description_suffix = ""

    # Route to appropriate pricing logic
    if usage_type == "event" and rental_days <= 4:
      cost, description_suffix = self._calculate_event_pricing(
          trailer_id, rental_days, product_info
      )
    else:
      cost, description_suffix = self._calculate_commercial_pricing(
          trailer_id, rental_days, product_info
      )

    if cost is None:
      logger.error(
          f"Cost calculation resulted in None for trailer '{trailer_id}' ({rental_days} days, {usage_type})."
      )
      return None, None

    # Apply seasonal multiplier
    if isinstance(cost, (int, float)) and isinstance(rate_multiplier, (int, float)):
      cost *= rate_multiplier
      description_suffix += season_desc
      cost_str = f"${cost:.2f}"
      logger.info(
          f"Applied seasonal multiplier {rate_multiplier}. Final cost: {cost_str}")
    else:
      logger.warning(
          f"Cannot apply seasonal multiplier: cost ({type(cost)}) or rate_multiplier ({type(rate_multiplier)}) is not numeric."
      )
      return None, None

    # Ensure cost is float before rounding
    if isinstance(cost, (int, float)):
      final_cost = round(cost, 2)
    else:
      logger.error(
          f"Final cost calculation resulted in non-numeric type: {type(cost)} for trailer '{trailer_id}'"
      )
      return None, None

    return final_cost, description_suffix

  def _calculate_event_pricing(
      self,
      trailer_id: str,
      rental_days: int,
      product_info: Dict[str, Any],
  ) -> Tuple[Optional[float], str]:
    """Calculate event pricing using the event pricer."""
    return self.event_pricer.calculate_event_price(
        trailer_id, rental_days, product_info
    )

  def _calculate_commercial_pricing(
      self,
      trailer_id: str,
      rental_days: int,
      product_info: Dict[str, Any],
  ) -> Tuple[Optional[float], str]:
    """Calculate commercial/long-term pricing using tiered rates."""
    # Try monthly rate tiers first
    base_monthly_rate, rate_tier_desc, fallback_suffix = (
        self.rate_tier_determiner.determine_monthly_rate_tier(
            rental_days, product_info, trailer_id
        )
    )

    base_cost = None
    description_suffix = ""

    if base_monthly_rate is not None:
      # Calculate prorated monthly cost
      base_cost, description_suffix = (
          self.monthly_calculator.calculate_prorated_monthly_cost(
              base_monthly_rate, rental_days, rate_tier_desc, trailer_id
          )
      )
      if fallback_suffix:
        description_suffix += f" {fallback_suffix}"
    else:
      # Try 28-day rate if >= 28 days
      if rental_days >= 28:
        base_cost, description_suffix = (
            self.period_calculator.calculate_28_day_rate(
                rental_days, product_info, trailer_id
            )
        )

      # Try weekly rate if no 28-day rate or < 28 days
      if base_cost is None:
        base_cost, description_suffix = (
            self.period_calculator.calculate_weekly_rate(
                rental_days, product_info, trailer_id
            )
        )

    if base_cost is None:
      logger.warning(
          f"Could not determine applicable base rate for '{trailer_id}' ({rental_days} days). No suitable rate or fallback found."
      )

    return base_cost, description_suffix
