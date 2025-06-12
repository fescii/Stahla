# app/services/quote/pricing/delivery/calculator.py

"""
Delivery cost calculation operations.
"""

import logging
from typing import Any, Dict, Optional

from app.models.location import DistanceResult

logger = logging.getLogger(__name__)


class DeliveryCalculator:
  """Handles delivery cost calculations."""

  def __init__(self, manager):
    self.manager = manager

  async def calculate_delivery_cost(
      self,
      distance_result: DistanceResult,
      catalog: Dict[str, Any],
      rate_multiplier: float,
      season_desc: str,
      is_distance_estimated: bool = False,
  ) -> Dict[str, Any]:
    """
    Calculates the delivery cost based on distance and delivery tiers,
    applying seasonal multipliers. Returns a dictionary with detailed cost breakdown.
    """
    # Try multiple potential keys for delivery configuration
    delivery_config = catalog.get(
        "delivery") or catalog.get("delivery_costs") or {}

    if not delivery_config:
      logger.warning("Delivery pricing configuration not found in catalog.")
      await self.manager.mongo_service.log_error_to_db(
          service_name="DeliveryCalculator.calculate_delivery_cost",
          error_type="ConfigurationMissing",
          message="Delivery pricing configuration not found in catalog.",
          details={"catalog_keys": list(catalog.keys())},
      )
      # Use default values instead of returning early
      delivery_config = {
          "free_miles_threshold": 25,
          "base_fee": 80.0,
          "per_mile_rates": {
              "denver": 3.99,
              "omaha_kansas_city": 2.99
          }
      }

    distance_miles = distance_result.distance_miles
    original_free_tier_miles = delivery_config.get("free_miles_threshold", 25)
    original_base_fee = delivery_config.get("base_fee", 0.0)

    # Get the per_mile_rates from the config - handle both flat rates and location-specific rates
    per_mile_rates = delivery_config.get("per_mile_rates", {})
    if isinstance(per_mile_rates, dict):
      # Location-specific rates structure
      branch_name = distance_result.nearest_branch.name.lower()
      if "denver" in branch_name:
        original_per_mile_rate = per_mile_rates.get("denver", 3.99)
      else:
        original_per_mile_rate = per_mile_rates.get("omaha_kansas_city", 2.99)
    else:
      # If it's not a dict, assume it's a single flat rate
      original_per_mile_rate = float(per_mile_rates) if per_mile_rates else 0.0

    cost: Optional[float] = None
    tier_description: str = ""
    applied_per_mile_rate = original_per_mile_rate
    applied_base_fee = original_base_fee

    logger.info(
        f"Calculating delivery: Distance={distance_miles:.2f} mi, Branch={distance_result.nearest_branch.name}, "
        f"OriginalBaseFee=${original_base_fee:.2f}, OriginalPerMile=${original_per_mile_rate:.2f}, "
        f"Multiplier={rate_multiplier:.2f}"
    )

    if distance_miles <= original_free_tier_miles:
      cost = 0.0
      tier_description = f"Free Delivery (<= {original_free_tier_miles} miles)"
      # Seasonal multiplier does not apply to free tier
      seasonal_multiplier_for_calc = 1.0
      applied_per_mile_rate = 0.0  # No per mile charge in free tier
      applied_base_fee = 0.0  # No base fee in free tier
      logger.info(f"Delivery cost (Free Tier): ${cost:.2f}")
    else:
      seasonal_multiplier_for_calc = rate_multiplier  # Apply for paid tiers
      applied_base_fee = original_base_fee * seasonal_multiplier_for_calc
      applied_per_mile_rate = original_per_mile_rate * seasonal_multiplier_for_calc
      cost = applied_base_fee + (distance_miles * applied_per_mile_rate)

      tier_description = f"Standard Rate @ ${original_per_mile_rate:.2f}/mile (Base: ${original_base_fee:.2f}){season_desc}"
      logger.info(
          f"Delivery cost ({distance_miles:.1f} miles @ ${applied_per_mile_rate:.2f}/mile "
          f"+ Base ${applied_base_fee:.2f}) with multiplier {seasonal_multiplier_for_calc:.2f}: ${cost:.2f}"
      )

    result = {
        # Use 0.0 instead of None
        "cost": round(cost, 2) if cost is not None else 0.0,
        "tier_description": tier_description,
        "miles": round(distance_miles, 2),
        "original_per_mile_rate": original_per_mile_rate,
        "original_base_fee": original_base_fee,
        "seasonal_multiplier_applied": (
            # Use 1.0 instead of None
            seasonal_multiplier_for_calc if cost is not None and cost > 0 else 1.0
        ),
        "per_mile_rate_applied": (
            round(applied_per_mile_rate,
                  2) if cost is not None and cost > 0 else 0.0
        ),
        "base_fee_applied": round(applied_base_fee, 2) if cost is not None and cost > 0 else 0.0,
    }

    # Add estimation flag if distance was estimated
    if is_distance_estimated:
      result["is_estimated"] = True
      # Adjust tier description to indicate estimation
      if result["tier_description"]:
        result["tier_description"] += " (Estimated)"

    return result

  def get_delivery_cost_for_distance(
      self,
      distance_miles: float,
      delivery_config: Dict[str, Any],
      branch_name: str = "omaha",
  ) -> float:
    """Calculate delivery cost based on distance and branch location."""
    # Extract the values with fallbacks
    base_fee = delivery_config.get("base_fee", 0.0)
    per_mile_rates = delivery_config.get(
        "per_mile_rates", {"omaha_kansas_city": 2.99, "denver": 3.99}
    )
    free_miles_threshold = delivery_config.get("free_miles_threshold", 25)

    # Determine appropriate rate based on branch name
    per_mile_rate = 3.0  # Default fallback rate
    if isinstance(per_mile_rates, dict):
      if branch_name and "denver" in branch_name.lower():
        per_mile_rate = per_mile_rates.get("denver", 3.99)
      else:  # Omaha or Kansas City or any other branch
        per_mile_rate = per_mile_rates.get("omaha_kansas_city", 2.99)
    elif per_mile_rates:
      # If it's not a dict but has a value, use it as a flat rate
      per_mile_rate = float(per_mile_rates)

    # Calculate billable miles (subtracting free threshold)
    billable_miles = max(0, distance_miles - free_miles_threshold)

    # Calculate total delivery cost
    delivery_cost = base_fee + (billable_miles * per_mile_rate)

    logger.info(
        f"Calculated delivery cost: ${delivery_cost:.2f} "
        f"(Base: ${base_fee:.2f}, Rate: ${per_mile_rate:.2f}/mi, "
        f"Billable Miles: {billable_miles:.2f}, Branch: {branch_name})"
    )

    return delivery_cost if isinstance(delivery_cost, (int, float)) else 0.0
