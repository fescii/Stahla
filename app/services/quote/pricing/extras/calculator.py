# app/services/quote/pricing/extras/calculator.py

"""
Extras cost calculation operations.
"""

import logging
import math
from typing import Any, Dict, List, Optional

from app.models.quote import ExtraInput, LineItem

logger = logging.getLogger(__name__)


class ExtrasCalculator:
  """Handles extras cost calculations."""

  def __init__(self, manager):
    self.manager = manager

  async def calculate_extras_cost(
      self,
      extras_input: List[ExtraInput],
      trailer_id: str,
      rental_days: int,
      catalog: Dict[str, Any],
  ) -> List[LineItem]:
    """
    Calculates the cost for requested extras (generators, services).
    Uses pricing from generator catalog and service costs from product catalog.
    """
    extra_line_items: List[LineItem] = []
    generators_catalog = catalog.get("generators", {})
    product_info = catalog.get("products", {}).get(trailer_id)
    product_extras = product_info.get("extras", {}) if product_info else {}

    for extra in extras_input:
      extra_id = extra.extra_id
      qty = extra.qty
      item_cost: Optional[float] = None
      description: str = f"{qty}x {extra_id}"
      unit_price: Optional[float] = None

      # Check if it's a generator
      if extra_id in generators_catalog:
        item_cost, unit_price, description = await self._calculate_generator_cost(
            extra_id, qty, rental_days, generators_catalog[extra_id]
        )

      # Check if it's a service from product extras
      elif product_extras:
        item_cost, unit_price, description = await self._calculate_service_cost(
            extra_id, qty, product_extras, trailer_id
        )

      # Unknown item
      else:
        logger.warning(f"Extra item '{extra_id}' not found in catalog")
        await self.manager.mongo_service.log_error_to_db(
            service_name="ExtrasCalculator.calculate_extras_cost",
            error_type="ItemNotFound",
            message=f"Extra item '{extra_id}' not found in pricing catalog.",
            details={"extra_id": extra_id, "trailer_id": trailer_id},
        )
        item_cost = 0.00
        description = f"{qty}x {extra_id} (Unknown Item)"

      # Create line item
      if item_cost is not None and isinstance(item_cost, (int, float)):
        final_total = round(item_cost, 2)
        final_unit_price = round(unit_price, 2) if unit_price and isinstance(
            unit_price, (int, float)) else None

        extra_line_items.append(
            LineItem(
                description=description,
                quantity=qty,
                unit_price=final_unit_price,
                total=final_total,
            )
        )

    return extra_line_items

  async def _calculate_generator_cost(
      self,
      extra_id: str,
      qty: int,
      rental_days: int,
      gen_info: Dict[str, Any],
  ) -> tuple[Optional[float], Optional[float], str]:
    """Calculate cost for generator rentals."""
    gen_name = gen_info.get("name", extra_id)
    rate_event = gen_info.get("rate_event")
    rate_7_day = gen_info.get("rate_7_day")
    rate_28_day = gen_info.get("rate_28_day")

    # Check if this is a large generator where event rates might be N/A
    is_large_generator = "kw generator" in extra_id.lower() and not (
        "3kw" in extra_id.lower() or "7kw" in extra_id.lower()
    )

    item_cost = None
    unit_price = None
    description = f"{qty}x {gen_name}"

    # Event pricing (≤3 days)
    if rental_days <= 3:
      if rate_event is not None and isinstance(rate_event, (int, float)):
        item_cost = rate_event * qty
        unit_price = rate_event
        description = f"{qty}x {gen_name} (Event <= 3 days)"
      elif is_large_generator and rate_7_day is not None and isinstance(rate_7_day, (int, float)):
        # For large generators, use daily rate derived from weekly
        daily_rate = rate_7_day / 3.5
        item_cost = daily_rate * rental_days * qty
        description = f"{qty}x {gen_name} (Event - Daily Rate from Weekly)"
      elif rate_7_day is not None and isinstance(rate_7_day, (int, float)):
        # Fallback to weekly rate
        item_cost = rate_7_day * qty
        unit_price = rate_7_day
        description = f"{qty}x {gen_name} (Event - Weekly Rate Fallback)"

    # Weekly pricing (4-7 days)
    elif rental_days <= 7 and rate_7_day is not None and isinstance(rate_7_day, (int, float)):
      item_cost = rate_7_day * qty
      unit_price = rate_7_day
      description = f"{qty}x {gen_name} (<= 7 days)"

    # 28-day pricing (8-28 days)
    elif rental_days <= 28 and rate_28_day is not None and isinstance(rate_28_day, (int, float)):
      item_cost = rate_28_day * qty
      unit_price = rate_28_day
      description = f"{qty}x {gen_name} (<= 28 days)"

    # Longer than 28 days, prorate 28-day rate
    elif rate_28_day is not None and isinstance(rate_28_day, (int, float)):
      num_periods = rental_days / 28
      item_cost = rate_28_day * num_periods * qty
      description = f"{qty}x {gen_name} ({rental_days} days - Prorated 28 Day Rate)"

    # Fallback: prorate weekly if no 28-day rate
    elif rate_7_day is not None and isinstance(rate_7_day, (int, float)):
      num_weeks = math.ceil(rental_days / 7)
      item_cost = rate_7_day * num_weeks * qty
      description = f"{qty}x {gen_name} ({rental_days} days - Weekly Rate)"

    # No pricing found
    else:
      logger.warning(
          f"Could not determine rate for generator '{extra_id}' ({rental_days} days).")
      item_cost = 0.00
      description = f"{qty}x {gen_name} (Pricing Unavailable)"

    return item_cost, unit_price, description

  async def _calculate_service_cost(
      self,
      extra_id: str,
      qty: int,
      product_extras: Dict[str, Any],
      trailer_id: str,
  ) -> tuple[Optional[float], Optional[float], str]:
    """Calculate cost for service extras."""
    # Try to normalize the extra_id to match available services
    normalized_extra_id = self.normalize_extra_id(extra_id, product_extras)

    if normalized_extra_id and normalized_extra_id in product_extras:
      service_cost = product_extras.get(normalized_extra_id)
      if service_cost is not None:
        item_cost = service_cost * qty
        unit_price = service_cost
        service_name = extra_id.replace("_", " ").title()
        description = f"{qty}x {service_name} Service"
        return item_cost, unit_price, description
      else:
        logger.warning(
            f"Service '{normalized_extra_id}' found but has no price in catalog for trailer {trailer_id}.")
    else:
      logger.warning(f"Service '{extra_id}' not found in product extras.")

    # Service not found or no price
    return 0.00, None, f"{qty}x {extra_id.replace('_', ' ').title()} (Pricing Unavailable)"

  def normalize_extra_id(
      self, extra_id: str, available_extras: Dict[str, Any]
  ) -> Optional[str]:
    """Normalize extra ID for matching against available services."""
    if not extra_id or not available_extras:
      return None

    # Direct match first
    if extra_id in available_extras:
      return extra_id

    # Try some common variations
    variations = [
        extra_id.lower(),
        extra_id.upper(),
        extra_id.replace(" ", "_").lower(),
        extra_id.replace("-", "_").lower(),
        extra_id.replace("_", "").lower(),
    ]

    for variation in variations:
      if variation in available_extras:
        return variation

    # Try partial matching
    extra_lower = extra_id.lower()
    for available_key in available_extras.keys():
      if extra_lower in available_key.lower() or available_key.lower() in extra_lower:
        return available_key

    return None
