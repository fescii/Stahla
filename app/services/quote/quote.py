import logging
import math
import json
import asyncio
import logfire  # Import logfire for enhanced logging
from datetime import date  # Ensure date is imported
from typing import Any, Dict, List, Optional, Tuple, Literal  # Import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.utils.location import geocode_location, SERVICE_HUBS, get_distance_km

from app.models.quote import (
    QuoteRequest,
    QuoteResponse,
    LineItem,
    QuoteBody,
    ExtraInput,
    DeliveryCostDetails,
)
from app.models.location import DistanceResult, BranchLocation
from app.services.redis.redis import RedisService, get_redis_service
from app.services.location.location import LocationService
from app.services.mongo.mongo import (
    MongoService,
    get_mongo_service,
    SHEET_PRODUCTS_COLLECTION,
    SHEET_GENERATORS_COLLECTION,
    SHEET_CONFIG_COLLECTION,
    SHEET_BRANCHES_COLLECTION,
)  # Import MongoDB collection constants
from app.services.quote.sync import (
    PRICING_CATALOG_CACHE_KEY,
    BRANCH_LIST_CACHE_KEY,
)  # Import cache keys
from app.services.dash.background import (
    increment_request_counter_bg,
)  # For dashboard counters
from app.services.dash.dashboard import (
    PRICING_CACHE_HITS_KEY,
    PRICING_CACHE_MISSES_KEY,
)  # Import new keys
from app.core.dependencies import get_location_service_dep

logger = logging.getLogger(__name__)

# Constants for pricing logic
DAYS_PER_MONTH_APPROX = 30.4375  # Average days in a month
MONTHS_2 = 2
MONTHS_6 = 6
MONTHS_18 = 18
# Added constant for config collection
SHEET_CONFIG_COLLECTION = "sheet_config"
SHEET_PRODUCTS_COLLECTION = "products"  # Collection for products
SHEET_GENERATORS_COLLECTION = "generators"  # Collection for generators


class QuoteService:
  """
  Service responsible for calculating price quotes based on cached pricing data
  and calculated delivery distances.
  """

  def __init__(
      self,
      redis_service: RedisService,
      location_service: LocationService,
      mongo_service: MongoService,
  ):  # Added mongo_service
    self.redis_service = redis_service
    self.location_service = location_service
    self.mongo_service = mongo_service  # Store mongo_service

  async def _get_pricing_catalog(self) -> Optional[Dict[str, Any]]:
    """
    Retrieves the pricing catalog from Redis cache.
    If not found or on error, attempts to retrieve from MongoDB as a fallback.
    """
    try:
      catalog = await self.redis_service.get_json(PRICING_CATALOG_CACHE_KEY)

      if catalog:
        logger.debug(
            f"Pricing catalog found in Redis cache ('{PRICING_CATALOG_CACHE_KEY}')."
        )
        await increment_request_counter_bg(
            self.redis_service, PRICING_CACHE_HITS_KEY
        )
        return catalog
      else:
        logger.warning(
            f"Pricing catalog NOT FOUND in Redis cache ('{PRICING_CATALOG_CACHE_KEY}'). Attempting MongoDB fallback."
        )
        await increment_request_counter_bg(
            self.redis_service, PRICING_CACHE_MISSES_KEY
        )
        # Log to MongoDB
        await self.mongo_service.log_error_to_db(
            service_name="QuoteService._get_pricing_catalog",
            error_type="CacheMiss",
            message=f"Pricing catalog not found in Redis cache (key: '{PRICING_CATALOG_CACHE_KEY}'). Trying MongoDB fallback.",
            details={"cache_key": PRICING_CATALOG_CACHE_KEY},
        )

        # Try to get from MongoDB as fallback
        mongo_data = await self._build_catalog_from_mongo()
        if mongo_data:
          logger.info(
              "Successfully retrieved pricing catalog from MongoDB as fallback."
          )
          # Try to update Redis with the MongoDB data for future use
          try:
            await self.redis_service.set_json(
                PRICING_CATALOG_CACHE_KEY, mongo_data
            )
            logger.info(
                f"Updated Redis cache with MongoDB data for '{PRICING_CATALOG_CACHE_KEY}'."
            )
          except Exception as cache_e:
            logger.warning(
                f"Could not update Redis cache with MongoDB data: {cache_e}"
            )

          return mongo_data
        else:
          logger.error(
              "Failed to retrieve pricing catalog from both Redis and MongoDB."
          )
          return None

    except Exception as e:
      logger.error(
          f"Error retrieving pricing catalog from Redis (key: '{PRICING_CATALOG_CACHE_KEY}'): {e}",
          exc_info=True,
      )
      await increment_request_counter_bg(
          self.redis_service, PRICING_CACHE_MISSES_KEY
      )
      # Log to MongoDB
      await self.mongo_service.log_error_to_db(
          service_name="QuoteService._get_pricing_catalog",
          error_type="RedisError",
          message=f"Error retrieving pricing catalog from Redis: {str(e)}. Trying MongoDB fallback.",
          details={
              "cache_key": PRICING_CATALOG_CACHE_KEY,
              "exception_type": type(e).__name__,
          },
      )

      # Try to get from MongoDB as fallback
      mongo_data = await self._build_catalog_from_mongo()
      if mongo_data:
        logger.info(
            "Successfully retrieved pricing catalog from MongoDB as fallback after Redis error."
        )
        return mongo_data
      return None

  async def _get_config_from_mongo(self) -> Optional[Dict[str, Any]]:
    """
    Retrieves the configuration from MongoDB when Redis cache fails.
    Returns the config document or None if not found.
    """
    if not self.mongo_service:
      logger.error(
          "Cannot get config from MongoDB - MongoService not initialized."
      )
      return None

    try:
      db = await self.mongo_service.get_db()
      collection = db[SHEET_CONFIG_COLLECTION]

      config_doc = await collection.find_one({"_id": "master_config"})
      if config_doc:
        logger.info("Retrieved config document from MongoDB.")
        return config_doc
      else:
        logger.warning("Config document not found in MongoDB.")
        return None
    except Exception as e:
      logger.error(
          f"Error retrieving config from MongoDB: {str(e)}", exc_info=True
      )
      return None

  async def _build_catalog_from_mongo(self) -> Optional[Dict[str, Any]]:
    """
    Builds a pricing catalog from MongoDB collections when Redis cache is unavailable.
    This reconstructs the same structure as used in Redis for consistent usage.
    """
    if not self.mongo_service:
      logger.error(
          "Cannot build catalog from MongoDB - MongoService not initialized."
      )
      return None

    try:
      db = await self.mongo_service.get_db()

      # Get config document first
      config_collection = db[SHEET_CONFIG_COLLECTION]
      config_doc = await config_collection.find_one({"_id": "master_config"})

      if not config_doc:
        logger.error("Master config document not found in MongoDB.")
        return None

      # Get products and generators
      products_collection = db[SHEET_PRODUCTS_COLLECTION]
      generators_collection = db[SHEET_GENERATORS_COLLECTION]

      products_cursor = products_collection.find({})
      generators_cursor = generators_collection.find({})

      products_list = await products_cursor.to_list(length=None)
      generators_list = await generators_cursor.to_list(length=None)

      # Convert lists to dictionaries keyed by id for the expected format
      products_dict = {
          product.get("id", f"unknown_{i}"): product
          for i, product in enumerate(products_list)
      }

      generators_dict = {
          generator.get("id", f"unknown_{i}"): generator
          for i, generator in enumerate(generators_list)
      }

      # Build the catalog structure to match what's expected in Redis
      delivery_config = config_doc.get("delivery_config", {})
      seasonal_config = config_doc.get(
          "seasonal_multipliers_config", {"standard": 1.0, "tiers": []}
      )

      catalog = {
          "products": products_dict,
          "generators": generators_dict,
          "delivery": delivery_config,
          "seasonal_multipliers": seasonal_config,
      }

      # Fix potential naming differences between MongoDB and Redis structures
      if "standard_rate" in catalog["seasonal_multipliers"]:
        catalog["seasonal_multipliers"]["standard"] = catalog[
            "seasonal_multipliers"
        ].pop("standard_rate")

      logger.info(
          f"Built catalog from MongoDB. Products: {len(products_dict)}, Generators: {len(generators_dict)}"
      )
      return catalog

    except Exception as e:
      logger.error(f"Error building catalog from MongoDB: {e}", exc_info=True)
      await self.mongo_service.log_error_to_db(
          service_name="QuoteService._build_catalog_from_mongo",
          error_type="MongoDBError",
          message=f"Failed to build catalog from MongoDB: {str(e)}",
          details={"exception_type": type(e).__name__},
      )
      return None

  def _determine_seasonal_multiplier(
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

  def _calculate_trailer_cost(
      self,
      trailer_id: str,
      rental_days: int,
      usage_type: Literal["commercial", "event"],
      rental_start_date: date,
      seasonal_config: Dict[str, Any],
      catalog: Dict[str, Any],
  ) -> Tuple[Optional[float], Optional[str]]:
    """Calculates the base rental cost for a trailer, applying seasonal multipliers."""
    logger.info(
        f"Calculating cost for trailer: {trailer_id}, Days: {rental_days}, Usage: {usage_type}, Start: {rental_start_date}"
    )
    products_catalog = catalog.get("products", {})
    product_info = products_catalog.get(trailer_id)

    if not product_info:
      logger.error(
          f"Trailer type '{trailer_id}' not found in pricing catalog.")
      # Log to MongoDB asynchronously
      if self.mongo_service:
        asyncio.create_task(self.mongo_service.log_error_to_db(
            service_name="QuoteService._calculate_trailer_cost",
            error_type="ItemNotFound",
            message=f"Trailer type '{trailer_id}' not found in pricing catalog.",
            details={"trailer_id": trailer_id}
        ))
      return None, None

    cost: Optional[float] = None
    description_suffix = ""

    # Determine seasonal multiplier first
    rate_multiplier, season_desc = self._determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    # --- Event Pricing (<= 4 days) ---
    if usage_type == "event" and rental_days <= 4:
      # Event pricing uses specific columns, not tiers based on date within the event window
      # We still apply the overall seasonal multiplier determined by the start date
      event_tier_key = "event_standard"  # Default to standard event price
      cost = product_info.get(event_tier_key)

      if cost is None:
        # Try to get fallback price
        cost, fallback_suffix = self._get_fallback_price(
            product_info, event_tier_key, rental_days
        )
        if cost is None:
          logger.error(
              f"Base event price ('{event_tier_key}') not found for trailer '{trailer_id}' and no fallback available. Cannot calculate event price."
          )
          # This will cause build_quote to raise ValueError.
          return None, None
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

      # Apply seasonal multiplier to the determined event cost
      if isinstance(cost, (int, float)) and isinstance(rate_multiplier, (int, float)):
        cost *= rate_multiplier
        description_suffix += season_desc
        # Safe formatting for log
        cost_str = f"${cost:.2f}"
        logger.info(
            f"Applied seasonal multiplier {rate_multiplier}. Final Event cost: {cost_str}"
        )
      else:
        logger.warning(
            f"Cannot apply seasonal multiplier: cost ({type(cost)}) or rate_multiplier ({type(rate_multiplier)}) is not numeric.")

    # --- Longer-term / Commercial Pricing ---
    else:  # Commercial use OR Event > 4 days uses tiered rates
      # Calculate approximate months for tier selection
      rental_months = rental_days / DAYS_PER_MONTH_APPROX

      # Determine applicable base rate based on duration tiers
      rate_18_plus = product_info.get("rate_18_plus_month")
      rate_6_plus = product_info.get("rate_6_plus_month")
      rate_2_5 = product_info.get("rate_2_5_month")
      rate_28_day = product_info.get("rate_28_day")
      rate_weekly = product_info.get("weekly_7_day")

      base_monthly_rate = None
      base_cost = None
      rate_tier_desc = ""
      fallback_suffix = ""

      # Try to determine the appropriate rate for the rental period, with fallbacks
      if rental_months >= MONTHS_18:
        if rate_18_plus is not None:
          base_monthly_rate = rate_18_plus
          rate_tier_desc = "18+ Month Rate"
        else:
          # Try fallback for 18+ month rate
          base_monthly_rate, fallback_suffix = self._get_fallback_price(
              product_info, "rate_18_plus_month", rental_days
          )
          if base_monthly_rate is not None:
            # Safe formatting for log
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
          base_monthly_rate, fallback_suffix = self._get_fallback_price(
              product_info, "rate_6_plus_month", rental_days
          )
          if base_monthly_rate is not None:
            # Safe formatting for log
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
          base_monthly_rate, fallback_suffix = self._get_fallback_price(
              product_info, "rate_2_5_month", rental_days
          )
          if base_monthly_rate is not None:
            # Safe formatting for log
            rate_str = f"${base_monthly_rate:.2f}" if isinstance(
                base_monthly_rate, (int, float)) else str(base_monthly_rate)
            logger.info(
                f"Using fallback for 2-5 Month Rate for '{trailer_id}': {rate_str} {fallback_suffix}"
            )
      elif rental_days >= 28:
        if rate_28_day is not None:
          num_28_day_periods = rental_days / 28
          base_cost = rate_28_day * num_28_day_periods  # Prorate 28-day rate
          rate_tier_desc = "Prorated 28 Day Rate"
          description_suffix = f"({rental_days} days - {rate_tier_desc})"
          # Safe formatting for log
          cost_str = f"${base_cost:.2f}" if isinstance(
              base_cost, (int, float)) else str(base_cost)
          logger.info(
              f"Base rate: {rate_tier_desc} for '{trailer_id}': {cost_str}"
          )
        else:
          # Try fallback for 28-day rate
          fallback_rate, fallback_suffix = self._get_fallback_price(
              product_info, "rate_28_day", rental_days
          )
          if fallback_rate is not None:
            num_28_day_periods = rental_days / 28
            base_cost = fallback_rate * num_28_day_periods
            rate_tier_desc = f"Prorated 28 Day Rate {fallback_suffix}"
            description_suffix = f"({rental_days} days - {rate_tier_desc})"
            # Safe formatting for log
            cost_str = f"${base_cost:.2f}" if isinstance(
                base_cost, (int, float)) else str(base_cost)
            logger.info(
                f"Base rate: Using fallback for 28-Day Rate for '{trailer_id}': {cost_str} {fallback_suffix}"
            )

      else:  # Less than 28 days
        if rate_weekly is not None:
          num_weeks = math.ceil(rental_days / 7)  # Charge full weeks
          base_cost = rate_weekly * num_weeks
          rate_tier_desc = "Weekly Rate"
          description_suffix = (
              f"({rental_days} days / {num_weeks} weeks - {rate_tier_desc})"
          )
          # Safe formatting for log
          cost_str = f"${base_cost:.2f}" if isinstance(
              base_cost, (int, float)) else str(base_cost)
          logger.info(
              f"Base rate: {rate_tier_desc} for '{trailer_id}': {cost_str}"
          )
        else:
          # Try fallback for weekly rate
          fallback_rate, fallback_suffix = self._get_fallback_price(
              product_info, "weekly_7_day", rental_days
          )
          if fallback_rate is not None:
            num_weeks = math.ceil(rental_days / 7)
            base_cost = fallback_rate * num_weeks
            rate_tier_desc = f"Weekly Rate {fallback_suffix}"
            description_suffix = f"({rental_days} days / {num_weeks} weeks - {rate_tier_desc})"
            # Safe formatting for log
            cost_str = f"${base_cost:.2f}" if isinstance(
                base_cost, (int, float)) else str(base_cost)
            logger.info(
                f"Base rate: Using fallback for Weekly Rate for '{trailer_id}': {cost_str} {fallback_suffix}"
            )

      # If we couldn't find any applicable rate or fallback
      if base_monthly_rate is None and base_cost is None:
        logger.warning(
            f"Could not determine applicable base rate for '{trailer_id}' ({rental_days} days). No suitable rate or fallback found."
        )
        return None, None

      # If a monthly rate was selected, calculate prorated base cost
      if (
          base_monthly_rate is not None and base_cost is None
      ):  # Check base_cost is None to avoid overwriting 28-day/weekly calc
        if isinstance(base_monthly_rate, (int, float)) and isinstance(rental_days, (int, float)):
          base_cost = (base_monthly_rate / DAYS_PER_MONTH_APPROX) * rental_days
          description_suffix = f"({rental_days} days - Prorated {rate_tier_desc})"
          # Safe formatting for log
          cost_str = f"${base_cost:.2f}"
          logger.info(
              f"Base rate: Prorated {rate_tier_desc} for '{trailer_id}': {cost_str}"
          )
        else:
          logger.warning(
              f"Cannot calculate prorated cost: base_monthly_rate ({type(base_monthly_rate)}) or rental_days ({type(rental_days)}) is not numeric.")
          return None, None  # Cannot proceed if calculation fails

      # If (
      #     base_cost is None
      # ):  # Should be caught by the 'else' above if no weekly rate
      #   logger.error(
      #       f"Failed to calculate base cost for trailer '{trailer_id}' ({rental_days} days, {usage_type})."
      #   )
      #   return None, None

      # Apply seasonal multiplier to the determined base cost
      if isinstance(base_cost, (int, float)) and isinstance(rate_multiplier, (int, float)):
        cost = base_cost * rate_multiplier
        # Safe formatting for log
        cost_str = f"${cost:.2f}"
        logger.info(
            f"Applied seasonal multiplier {rate_multiplier}. Final cost: {cost_str}"
        )
      else:
        logger.warning(
            f"Cannot apply seasonal multiplier: base_cost ({type(base_cost)}) or rate_multiplier ({type(rate_multiplier)}) is not numeric.")
        # If base_cost was calculated but multiplier fails, maybe return base_cost? Or fail?
        # Let's return None for now to indicate failure.
        return None, None

    # Final check if cost calculation failed
    if cost is None:  # Should be caught by earlier returns if issues occurred
      logger.error(
          f"Cost calculation resulted in None for trailer '{trailer_id}' ({rental_days} days, {usage_type})."
      )
      return None, None

    # Ensure cost is float before rounding
    final_cost = None
    if isinstance(cost, (int, float)):
      final_cost = round(cost, 2)
    else:
      logger.error(
          f"Final cost calculation resulted in non-numeric type: {type(cost)} for trailer \'{trailer_id}\'")
      return None, None  # Return None if cost is not numeric

    return final_cost, description_suffix

  async def _calculate_delivery_cost(
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
    Logs to DB if config is missing.
    """
    delivery_config = catalog.get("delivery")
    if not delivery_config:
      logger.warning("Delivery pricing configuration not found in catalog.")
      await self.mongo_service.log_error_to_db(
          service_name="QuoteService._calculate_delivery_cost",
          error_type="ConfigurationMissing",
          message="Delivery pricing configuration not found in catalog.",
          details={"catalog_keys": list(catalog.keys())},
      )
      return {
          "cost": None,
          "tier_description": "Delivery pricing unavailable",
          "miles": distance_result.distance_miles,
      }  # Return partial info

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

    # Safe formatting for initial log
    dist_str = f"{distance_miles:.2f}" if isinstance(
        distance_miles, (int, float)) else str(distance_miles)
    base_fee_str = f"${original_base_fee:.2f}" if isinstance(
        original_base_fee, (int, float)) else str(original_base_fee)
    per_mile_str = f"${original_per_mile_rate:.2f}" if isinstance(
        original_per_mile_rate, (int, float)) else str(original_per_mile_rate)
    multiplier_str = f"{rate_multiplier:.2f}" if isinstance(
        rate_multiplier, (int, float)) else str(rate_multiplier)

    logger.info(
        f"Calculating delivery: Distance={dist_str} mi, Branch={distance_result.nearest_branch.name}, OriginalBaseFee={base_fee_str}, OriginalPerMile={per_mile_str}, Multiplier={multiplier_str}"
    )

    if distance_miles <= original_free_tier_miles:
      cost = 0.0
      tier_description = f"Free Delivery (<= {original_free_tier_miles} miles)"
      # Seasonal multiplier does not apply to free tier
      seasonal_multiplier_for_calc = 1.0
      applied_per_mile_rate = 0.0  # No per mile charge in free tier
      applied_base_fee = 0.0  # No base fee in free tier
      # Safe formatting for log
      cost_str = f"${cost:.2f}" if isinstance(
          cost, (int, float)) else str(cost)
      logger.info(f"Delivery cost (Free Tier): {cost_str}")
    else:
      seasonal_multiplier_for_calc = rate_multiplier  # Apply for paid tiers
      applied_base_fee = original_base_fee * seasonal_multiplier_for_calc
      applied_per_mile_rate = (
          original_per_mile_rate * seasonal_multiplier_for_calc
      )
      cost = applied_base_fee + (distance_miles * applied_per_mile_rate)

      # Safe formatting for log
      dist_log_str = f"{distance_miles:.1f}" if isinstance(
          distance_miles, (int, float)) else str(distance_miles)
      applied_rate_log_str = f"${applied_per_mile_rate:.2f}" if isinstance(
          applied_per_mile_rate, (int, float)) else str(applied_per_mile_rate)
      orig_rate_log_str = f"${original_per_mile_rate:.2f}" if isinstance(
          original_per_mile_rate, (int, float)) else str(original_per_mile_rate)
      applied_base_log_str = f"${applied_base_fee:.2f}" if isinstance(
          applied_base_fee, (int, float)) else str(applied_base_fee)
      orig_base_log_str = f"${original_base_fee:.2f}" if isinstance(
          original_base_fee, (int, float)) else str(original_base_fee)
      multiplier_log_str = f"{seasonal_multiplier_for_calc:.2f}" if isinstance(
          seasonal_multiplier_for_calc, (int, float)) else str(seasonal_multiplier_for_calc)
      cost_log_str = f"${cost:.2f}" if isinstance(
          cost, (int, float)) else str(cost)

      tier_description = f"Standard Rate @ {orig_rate_log_str}/mile (Base: {orig_base_log_str}){season_desc}"
      logger.info(
          f"Delivery cost ({dist_log_str} miles @ {applied_rate_log_str}/mile (orig: {orig_rate_log_str}) + Base {applied_base_log_str} (orig: {orig_base_log_str})) with multiplier {multiplier_log_str}: {cost_log_str}"
      )

    result = {
        "cost": round(cost, 2) if cost is not None else None,
        "tier_description": tier_description,
        "miles": round(distance_miles, 2),
        "original_per_mile_rate": original_per_mile_rate,
        "original_base_fee": original_base_fee,
        "seasonal_multiplier_applied": (
            seasonal_multiplier_for_calc if cost is not None and cost > 0 else None
        ),  # Only show multiplier if it affected cost
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

    # Ensure cost is numeric before rounding in result
    final_cost = None
    if cost is not None:
      if isinstance(cost, (int, float)):
        final_cost = round(cost, 2)
      else:
        logger.error(
            f"Delivery cost calculation resulted in non-numeric type: {type(cost)}")
        # Update result to reflect error
        result["cost"] = None
        result["tier_description"] = "Error: Calculation failed"
        return result  # Return early

    result["cost"] = final_cost
    return result

  async def _calculate_extras_cost(
      self,
      extras_input: List[ExtraInput],
      trailer_id: str,
      rental_days: int,
      catalog: Dict[str, Any],
  ) -> List[LineItem]:  # Made async
    """
    Calculates the cost for requested extras (generators, services).
    Uses pricing from generator catalog and service costs from product catalog.
    Logs to DB for missing items/rates.
    """
    extra_line_items: List[LineItem] = []
    generators_catalog = catalog.get("generators", {})
    product_info = catalog.get("products", {}).get(
        trailer_id
    )  # For trailer-specific service costs
    product_extras = product_info.get("extras", {}) if product_info else {}

    for extra in extras_input:
      extra_id = extra.extra_id
      qty = extra.qty
      item_cost: Optional[float] = None
      description: str = f"{qty}x {extra_id}"
      unit_price: Optional[float] = None

      # --- Generator Pricing ---
      if extra_id in generators_catalog:
        # ADDED VERBOSE LOGGING
        logger.warning(
            f"Processing generator: {extra_id}. Catalog type: {type(generators_catalog)}. Keys: {list(generators_catalog.keys()) if isinstance(generators_catalog, dict) else 'Not a dict'}")
        gen_info = generators_catalog[extra_id]
        logger.warning(
            f"Generator '{extra_id}' gen_info type: {type(gen_info)}, value: {gen_info}")

        gen_name = gen_info.get("name", extra_id)
        rate_event = gen_info.get("rate_event")
        rate_7_day = gen_info.get("rate_7_day")
        rate_28_day = gen_info.get("rate_28_day")

        # Log the retrieved rates for the specific generator
        logger.warning(
            f"Generator '{extra_id}': Retrieved rate_event: {rate_event} (type: {type(rate_event)}), rate_7_day: {rate_7_day} (type: {type(rate_7_day)}), rate_28_day: {rate_28_day} (type: {type(rate_28_day)})")

        # Check if this is a large generator where event rates might be N/A
        is_large_generator = "kw generator" in extra_id.lower() and not (
            "3kw" in extra_id.lower() or "7kw" in extra_id.lower()
        )

        # For event pricing (≤3 days)
        if rental_days <= 3:
          # Check type
          if rate_event is not None and isinstance(rate_event, (int, float)):
            item_cost = rate_event * qty
            unit_price = rate_event
            description = f"{qty}x {gen_name} (Event <= 3 days)"
          # Check type
          elif is_large_generator and rate_7_day is not None and isinstance(rate_7_day, (int, float)):
            # For large generators (20kW+) that don't have event rates, use daily rate derived from weekly
            daily_rate = rate_7_day / 3.5  # Approx. daily rate from weekly
            item_cost = daily_rate * rental_days * qty
            unit_price = None  # Prorated, unit price is complex
            description = (
                f"{qty}x {gen_name} (Event - Daily Rate from Weekly)"
            )
            # Safe formatting for log
            daily_rate_str = f"${daily_rate:.2f}" if isinstance(
                daily_rate, (int, float)) else str(daily_rate)
            logger.info(
                f"Using derived daily rate ({daily_rate_str}) for large generator \'{extra_id}\' event pricing"
            )
          else:
            # For smaller generators that should have event rates but don't, or if rate_event was not numeric
            # Check type
            if rate_7_day is not None and isinstance(rate_7_day, (int, float)):
              item_cost = (
                  rate_7_day * qty
              )  # Use full weekly rate as fallback
              unit_price = rate_7_day
              description = (
                  f"{qty}x {gen_name} (Event - Weekly Rate Fallback)"
              )
              logger.info(
                  f"Falling back to weekly rate for generator '{extra_id}' for event pricing (event rate missing or invalid)."
              )
            else:
              item_cost = None  # Will be caught below
              logger.warning(
                  f"No valid event or fallback weekly rate for generator '{extra_id}' for event pricing.")

        # For weekly pricing (4-7 days)
        # Check type
        elif rental_days <= 7 and rate_7_day is not None and isinstance(rate_7_day, (int, float)):
          item_cost = rate_7_day * qty
          unit_price = rate_7_day
          description = f"{qty}x {gen_name} (<= 7 days)"

        # For 28-day pricing (8-28 days)
        # Check type
        elif rental_days <= 28 and rate_28_day is not None and isinstance(rate_28_day, (int, float)):
          item_cost = rate_28_day * qty
          unit_price = rate_28_day
          description = f"{qty}x {gen_name} (<= 28 days)"

        # For longer than 28 days, prorate 28-day rate
        # Check type
        elif rate_28_day is not None and isinstance(rate_28_day, (int, float)):
          num_periods = rental_days / 28
          item_cost = rate_28_day * num_periods * qty
          unit_price = None  # Prorated, unit price is complex
          description = (
              f"{qty}x {gen_name} ({rental_days} days - Prorated 28 Day Rate)"
          )

        # Fallback: prorate weekly if no 28-day rate
        # Check type
        elif rate_7_day is not None and isinstance(rate_7_day, (int, float)):
          num_weeks = math.ceil(rental_days / 7)
          item_cost = rate_7_day * num_weeks * qty
          unit_price = None  # Prorated, unit price is complex
          description = (
              f"{qty}x {gen_name} ({rental_days} days - Weekly Rate)"
          )

        # No pricing found
        else:
          logger.warning(
              f"Could not determine rate for generator '{extra_id}' ({rental_days} days)."
          )
          await self.mongo_service.log_error_to_db(
              service_name="QuoteService._calculate_extras_cost",
              error_type="PricingUnavailable",
              message=f"Could not determine rate for generator '{extra_id}'.",
              details={
                  "extra_id": extra_id,
                  "rental_days": rental_days,
                  "trailer_id": trailer_id,
              },
          )
          item_cost = 0.00
          description = f"{qty}x {gen_name} (Pricing Unavailable)"

        # Safe formatting for final log
        cost_str = f"${item_cost:.2f}" if isinstance(
            item_cost, (int, float)) else str(item_cost)
        logger.info(
            f"Calculated generator cost for \'{extra_id}\' (Qty: {qty}, Days: {rental_days}): {cost_str}"
        )

      # --- Service Pricing (Pump out, Water Fill, Cleaning, Restocking) ---
      # Use costs associated with the *trailer* being rented
      elif extra_id in product_extras:
        service_cost = product_extras.get(extra_id)
        if service_cost is not None:
          item_cost = service_cost * qty  # Cost is per service instance
          unit_price = service_cost
          # Make description friendlier
          service_name = extra_id.replace("_", " ").title()
          description = f"{qty}x {service_name} Service"
          # Safe formatting for log
          cost_str = f"${item_cost:.2f}" if isinstance(
              item_cost, (int, float)) else str(item_cost)
          logger.info(
              f"Calculated service cost for \'{extra_id}\' (Qty: {qty}): {cost_str}"
          )
        else:
          logger.warning(
              f"Service '{extra_id}' found but has no price in catalog for trailer {trailer_id}."
          )
          await self.mongo_service.log_error_to_db(
              service_name="QuoteService._calculate_extras_cost",
              error_type="PricingUnavailable",
              message=f"Service '{extra_id}' has no price in catalog for trailer {trailer_id}.",
              details={"extra_id": extra_id, "trailer_id": trailer_id},
          )
          item_cost = 0.00
          description = f"{qty}x {extra_id.replace('_', ' ').title()} (Pricing Unavailable)"

      # --- Add logic for other non-catalog extras if needed ---
      # elif extra_id == 'attendant_service':
      #    item_cost = 500.00 * qty # Example fixed price
      #    unit_price = 500.00
      #    description = f"{qty}x On-site Attendant Service"

      else:
        logger.warning(
            f"Extra item '{extra_id}' not found in pricing catalog or product extras."
        )
        await self.mongo_service.log_error_to_db(
            service_name="QuoteService._calculate_extras_cost",
            error_type="ItemNotFound",
            message=f"Extra item '{extra_id}' not found in pricing catalog or product extras.",
            details={"extra_id": extra_id, "trailer_id": trailer_id},
        )
        item_cost = 0.00
        description = f"{qty}x {extra_id} (Unknown Item)"

      # Ensure item_cost and unit_price are numeric before rounding for LineItem
      final_total = 0.0
      final_unit_price = None
      if item_cost is not None:
        if isinstance(item_cost, (int, float)):
          final_total = round(item_cost, 2)
        else:
          logger.warning(
              f"Item cost for \'{extra_id}\' is not numeric ({type(item_cost)}). Setting total to 0.")
          description += " (Error: Invalid Price)"  # Append error note
      if unit_price is not None:
        if isinstance(unit_price, (int, float)):
          final_unit_price = round(unit_price, 2)
        else:
          logger.warning(
              f"Unit price for \'{extra_id}\' is not numeric ({type(unit_price)}). Setting to None.")

      extra_line_items.append(
          LineItem(
              description=description,
              quantity=qty,
              unit_price=final_unit_price,
              total=final_total,
          )
      )

    return extra_line_items

  def _get_fallback_price(
      self, product_info: Dict[str, Any], needed_field: str, rental_days: int
  ) -> Tuple[Optional[float], str]:
    """
    Attempts to find a fallback price when the primary pricing field is missing.
    Returns the fallback price and a description of which pricing was used.
    """
    logger = logging.getLogger(f"{__name__}.get_fallback_price")

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
          logger.info(
              f"Using \'{fallback_field}\' price ({price_str}) as fallback for missing \'{needed_field}\'"
          )

          # Adjust the price based on duration relationships if needed
          if fallback_field == "weekly_7_day" and needed_field.startswith(
              "rate_"
          ):
            # Adjust weekly rate to monthly equivalent
            adjusted_price = (
                fallback_price * 4.0
            )  # Approximate weekly → monthly
            suffix = f"(Fallback from {fallback_field}, adjusted for {needed_field})"
            return adjusted_price, suffix

          elif (
              fallback_field.startswith("rate_")
              and needed_field == "weekly_7_day"
          ):
            # Adjust monthly rate to weekly equivalent
            adjusted_price = (
                fallback_price / 4.0
            )  # Approximate monthly → weekly
            suffix = f"(Fallback from {fallback_field}, adjusted for {needed_field})"
            return adjusted_price, suffix

          # No adjustment needed
          suffix = f"(Fallback from {fallback_field})"
          return fallback_price, suffix

    # No fallbacks available
    logger.warning(
        f"No fallback price could be found for missing '{needed_field}'")
    # Log to MongoDB asynchronously (Optional, as it's just a warning, but good for tracking)
    # if self.mongo_service:
    #     asyncio.create_task(self.mongo_service.log_error_to_db(
    #         service_name="QuoteService._get_fallback_price",
    #         error_type="FallbackNotFound",
    #         message=f"No fallback price found for field '{needed_field}'.",
    #         details={"needed_field": needed_field, "product_keys": list(product_info.keys())}
    #     ))
    return None, "No price available"

  async def build_quote(
      self, request: QuoteRequest
  ) -> QuoteResponse:  # build_quote is already async
    """
    Builds a complete quote response based on the request.
    """
    logger.info(f"Building quote for request_id: {request.request_id}")
    # ADDED: start_time for internal build_quote timing if needed for more granular logging later
    # build_start_time = time.perf_counter()

    line_items: List[LineItem] = []
    subtotal = 0.0
    delivery_details_for_response: Optional[DeliveryCostDetails] = (
        None  # Initialize
    )
    delivery_tier_summary: Optional[str] = None

    # 1. Get Pricing Catalog from Cache
    catalog = await self._get_pricing_catalog()
    if not catalog:
      # Fallback to MongoDB config if Redis cache fails
      logger.warning(
          "Pricing catalog not found in Redis, attempting to load config from MongoDB."
      )
      config_doc = await self._get_config_from_mongo()
      if config_doc:
        logger.info(
            "Config loaded from MongoDB, but pricing catalog is empty. Please check catalog sync."
        )
        # Here we might want to raise a specific exception for empty catalog
        # or handle it as a special case in the client code.
        # For now, we raise a ValueError to indicate the issue.
        raise ValueError(
            "Pricing catalog is empty. Please check catalog sync.")
      else:
        logger.error(
            "Failed to load pricing catalog from Redis and MongoDB. Request cannot be processed."
        )
        raise ValueError(
            "Pricing data is currently unavailable. Please try again later."
        )

    # 2. Get Delivery Distance
    is_distance_estimated = (
        False  # Initialize flag to track if we're using estimated distances
    )

    distance_result = await self.location_service.get_distance_to_nearest_branch(
        request.delivery_location,
        background_tasks=BackgroundTasks(),  # Pass background tasks for async
    )
    if not distance_result:
      logger.warning(
          f"Could not determine delivery distance via LocationService for: {request.delivery_location}. Attempting fallback estimation."
      )
      await self.mongo_service.log_error_to_db(
          service_name="QuoteService.build_quote",
          error_type="LocationServiceError",
          message="LocationService.get_distance_to_nearest_branch returned None. Trying fallback estimation.",
          details={
              "delivery_location": request.delivery_location
          },
      )

      # Try fallback distance estimation
      distance_result = await self._estimate_distance_when_location_service_fails(
          request.delivery_location
      )

      # If fallback worked, mark this as an estimated distance
      if distance_result:
        logger.info(
            f"Using estimated distance calculation: {distance_result.distance_miles:.2f} miles"
        )
        # Set a flag to indicate this is an estimated distance (will be used in the response)
        is_distance_estimated = True
      else:
        logger.error(
            f"Both primary and fallback distance estimation failed for: {request.delivery_location}."
        )
        raise ValueError(
            f"Could not determine delivery distance for location: {request.delivery_location}"
        )
    # Log the obtained distance result
    logger.info(
        f"Distance result obtained: Branch='{distance_result.nearest_branch.name}', Miles={distance_result.distance_miles:.2f}"
    )

    # 3. Calculate Trailer Rental Cost - Pass start date and seasonal config
    # _calculate_trailer_cost is synchronous. If it returns None, error is raised below.
    # For more granular logging within _calculate_trailer_cost, it would need to become async
    # or use a background task for logging, which is complex to pass down.
    seasonal_config = catalog.get("seasonal_multipliers", {})
    loop = asyncio.get_running_loop()
    trailer_cost_result = await loop.run_in_executor(
        None,  # Use the default ThreadPoolExecutor
        self._calculate_trailer_cost,
        request.trailer_type,
        request.rental_days,
        request.usage_type,
        request.rental_start_date,
        seasonal_config,
        catalog,
    )
    if trailer_cost_result is None or trailer_cost_result[0] is None:
      # Log the specific failure before raising ValueError
      await self.mongo_service.log_error_to_db(
          service_name="QuoteService.build_quote",
          error_type="PricingError",
          message=f"Could not calculate price for trailer type: {request.trailer_type}.",
          details={
              "trailer_type": request.trailer_type,
              "rental_days": request.rental_days,
              "usage_type": request.usage_type,
              "rental_start_date": request.rental_start_date.isoformat(),
              "reason": "Output of _calculate_trailer_cost was None.",
          },
      )
      raise ValueError(
          f"Could not calculate price for trailer type: {request.trailer_type} for {request.rental_days} days ({request.usage_type}). Check catalog and request."
      )

    trailer_cost, trailer_desc_suffix = trailer_cost_result
    trailer_info = catalog.get("products", {}).get(request.trailer_type, {})
    trailer_name = trailer_info.get("name", request.trailer_type)
    # Ensure trailer_cost is not None before using it
    if trailer_cost is not None:
      line_items.append(
          LineItem(
              description=f"{trailer_name} Rental {trailer_desc_suffix}",
              quantity=1,
              unit_price=trailer_cost,
              total=trailer_cost,
          )
      )
      subtotal += trailer_cost

    # 4. Calculate Delivery Cost - Pass seasonal multiplier and description
    # Determine seasonal multiplier for delivery cost calculation
    loop = asyncio.get_running_loop()  # Ensure loop is defined here as well
    rate_multiplier, season_desc = await loop.run_in_executor(
        None,  # Use the default ThreadPoolExecutor
        self._determine_seasonal_multiplier,
        request.rental_start_date,
        seasonal_config
    )

    delivery_calculation_result = (
        await self._calculate_delivery_cost(  # Now awaited
            distance_result,
            catalog,
            rate_multiplier,
            season_desc,
            is_distance_estimated,
        )
    )

    delivery_cost = delivery_calculation_result.get("cost")
    delivery_tier_summary = delivery_calculation_result.get("tier_description")

    if delivery_cost is not None and delivery_tier_summary is not None:
      line_items.append(
          LineItem(
              # Use the tier description from the calculation
              description=delivery_tier_summary,
              quantity=1,
              unit_price=None,  # Delivery cost is a total, not per unit in this context
              total=delivery_cost,
          )
      )
      subtotal += delivery_cost

      # Populate DeliveryCostDetails for the response
      delivery_details_for_response = DeliveryCostDetails(
          miles=delivery_calculation_result["miles"],
          calculation_reason=delivery_tier_summary,  # This is the tier description
          total_delivery_cost=delivery_cost,
          original_per_mile_rate=delivery_calculation_result.get(
              "original_per_mile_rate"
          ),
          original_base_fee=delivery_calculation_result.get(
              "original_base_fee"),
          is_distance_estimated=delivery_calculation_result.get(
              "is_estimated", False
          ),
          seasonal_multiplier_applied=delivery_calculation_result.get(
              "seasonal_multiplier_applied"
          ),
          per_mile_rate_applied=delivery_calculation_result.get(
              "per_mile_rate_applied"
          ),
          base_fee_applied=delivery_calculation_result.get("base_fee_applied"),
      )
    else:
      logger.warning(
          "Could not calculate delivery cost or tier description was missing."
      )
      # Log this specific failure if delivery_cost is None from _calculate_delivery_cost
      # (which already logs if config is missing, this is for other potential None returns)
      if delivery_cost is None:
        await self.mongo_service.log_error_to_db(
            service_name="QuoteService.build_quote",
            error_type="DeliveryPricingError",
            message="Delivery cost calculation failed or returned None.",
            details={
                "distance_miles": distance_result.distance_miles,
                "rate_multiplier": rate_multiplier,
                "reason": "Output of _calculate_delivery_cost was None or tier description missing.",
            },
        )
      delivery_tier_summary = "Delivery cost calculation failed"

    # 5. Calculate Extras Cost
    extra_line_items = await self._calculate_extras_cost(  # Now awaited
        request.extras, request.trailer_type, request.rental_days, catalog
    )
    line_items.extend(extra_line_items)
    subtotal += sum(item.total for item in extra_line_items)

    # 6. Create additional detailed models for enhanced response

    # Get product details (if available) - Corrected lookup
    product_details = None
    # Get the products dictionary
    products_catalog = catalog.get("products", {})
    if isinstance(products_catalog, dict):
      trailer_product = products_catalog.get(
          request.trailer_type)  # Direct lookup by ID
    else:
      logger.warning(
          f"Products catalog is not a dictionary: {type(products_catalog)}. Cannot fetch trailer details.")
      trailer_product = None  # Ensure trailer_product is None if catalog structure is wrong

    # Check if found and is a dict
    if trailer_product and isinstance(trailer_product, dict):
      # Create ProductDetails model
      product_details = {
          "product_id": request.trailer_type,
          "product_name": trailer_product.get("name", "Unknown Product"),
          "product_description": trailer_product.get("description", None),
          "base_rate": trailer_product.get("base_rate", 0.0),
          "adjusted_rate": trailer_cost if trailer_cost is not None else 0.0,  # MODIFIED
          "features": trailer_product.get("features", []),
          "stall_count": trailer_product.get("stalls", None),
          "is_ada_compliant": "ada" in request.trailer_type.lower(),
          "trailer_size_ft": trailer_product.get("dimensions", None),
          "capacity_persons": trailer_product.get("capacity", None)
      }
    elif not trailer_product:
      logger.warning(
          f"Trailer type \'{request.trailer_type}\' not found in products catalog for details.")
    elif not isinstance(trailer_product, dict):
      logger.warning(
          f"Found trailer type \'{request.trailer_type}\' but it\'s not a dictionary: {type(trailer_product)}")

    # Create rental details
    rental_end_date = request.rental_start_date
    if request.rental_days:
      from datetime import timedelta
      rental_end_date = request.rental_start_date + \
          timedelta(days=request.rental_days)

    rental_weeks = request.rental_days // 7 if request.rental_days else None
    rental_months = round(
        request.rental_days / DAYS_PER_MONTH_APPROX, 2) if request.rental_days else None

    pricing_tier = "Daily Rate"
    if request.rental_days >= 28:
      pricing_tier = "Monthly Rate"
    elif request.rental_days >= 7:
      pricing_tier = "Weekly Rate"

    seasonal_rate_name = "Standard Season"  # Default value
    seasonal_multiplier = 1.0
    # Get seasonal info from catalog if available
    seasonal_config = catalog.get("seasonal_multipliers", {})
    current_date = request.rental_start_date
    for season in seasonal_config.get("tiers", []):
      # This is simplified - a real implementation would check date ranges
      if season.get("active", False):
        seasonal_rate_name = season.get("name", "Standard Season")
        seasonal_multiplier = season.get("multiplier", 1.0)
        break

    rental_details = {
        "rental_start_date": request.rental_start_date,
        "rental_end_date": rental_end_date,
        "rental_days": request.rental_days,
        "rental_weeks": rental_weeks,
        "rental_months": rental_months,
        "usage_type": request.usage_type,
        "pricing_tier_applied": pricing_tier,
        "seasonal_rate_name": seasonal_rate_name,
        "seasonal_multiplier": seasonal_multiplier
    }

    # Create budget details
    estimated_total = round(subtotal, 2)  # Total is just the subtotal now

    # Calculate equivalent rates
    daily_rate = round(
        subtotal / request.rental_days if request.rental_days else 0, 2)
    weekly_rate = round(daily_rate * 7, 2) if daily_rate else None
    monthly_rate = round(daily_rate * 30, 2) if daily_rate else None

    # Categorize costs
    cost_breakdown = {}
    for item in line_items:
      category = "other"
      if "Trailer Rental" in item.description:
        category = "trailer_rental"
      elif "Delivery" in item.description:
        category = "delivery"
      elif "Generator" in item.description:
        category = "generator"
      elif "Attendant" in item.description or "Service" in item.description:
        category = "services"

      if category in cost_breakdown:
        cost_breakdown[category] += item.total
      else:
        cost_breakdown[category] = item.total

    # Check if delivery is included (free)
    is_delivery_included = False
    if delivery_details_for_response and delivery_details_for_response.total_delivery_cost == 0:
      is_delivery_included = True

    budget_details = {
        "subtotal": round(subtotal, 2),
        "estimated_total": estimated_total,
        "daily_rate_equivalent": daily_rate,
        "weekly_rate_equivalent": weekly_rate,
        "monthly_rate_equivalent": monthly_rate,
        "cost_breakdown": cost_breakdown,
        "is_delivery_included": is_delivery_included,
        "discounts_applied": None  # Would come from applied discounts
    }

    # Create location details
    location_details = None
    if distance_result:
      geocoded_coords = None
      try:
        # Try to get geocoded coordinates if available
        loop = asyncio.get_running_loop()
        lat, lon = await loop.run_in_executor(None, geocode_location, request.delivery_location)
        if lat is not None and lon is not None:
          geocoded_coords = {
              "latitude": lat,
              "longitude": lon
          }
      except Exception as e:
        logger.warning(f"Failed to geocode location during quote build: {e}")

      # Determine service area type
      service_area_type = "Primary"
      if distance_result.distance_miles > 100:
        service_area_type = "Remote"
      elif distance_result.distance_miles > 50:
        service_area_type = "Secondary"

      location_details = {
          "delivery_address": request.delivery_location,
          "nearest_branch": distance_result.nearest_branch.name,
          "branch_address": distance_result.nearest_branch.address,
          "distance_miles": distance_result.distance_miles,
          "estimated_drive_time_minutes": int(distance_result.duration_seconds / 60) if distance_result.duration_seconds else None,
          "is_estimated_location": is_distance_estimated,
          "geocoded_coordinates": geocoded_coords,
          "service_area_type": service_area_type
      }

    # Create metadata
    from datetime import datetime, timedelta
    generated_at = datetime.now()
    # Quotes typically valid for 14 days
    valid_until = generated_at + timedelta(days=14)

    metadata = {
        "generated_at": generated_at,
        "valid_until": valid_until,
        "version": "1.0",
        "source_system": "Stahla Pricing API",
        "calculation_method": "standard",
        "data_sources": {
            "pricing": f"{datetime.now().strftime('%B %Y')} Rate Sheet",
            "location": "Google Maps API" if not is_distance_estimated else "Fallback Estimation",
            "seasonal_rates": f"{datetime.now().year} Seasonal Calendar"
        },
        "calculation_time_ms": None,  # Would need timing code
        "warnings": ["Delivery distance is estimated."] if is_distance_estimated else []
    }

    # metadata["calculation_time_ms"] = int((time.perf_counter() - build_start_time) * 1000) # If internal timing was added

    # 7. Construct Enhanced Response
    from app.models.quote import RentalDetails, ProductDetails, BudgetDetails

    # Convert dictionaries to proper models - ensure all required fields are present
    try:
      rental_details_model = RentalDetails(
          **rental_details) if rental_details else None
      product_details_model = ProductDetails(
          **product_details) if product_details else None
      budget_details_model = BudgetDetails(
          **budget_details) if budget_details else None
    except Exception as e:
      logger.error(f"Error creating models from dictionaries: {e}")
      # If there's an error in conversion, return None for that model rather than failing
      if 'rental_details' in str(e):
        rental_details_model = None
      if 'product_details' in str(e):
        product_details_model = None
      if 'budget_details' in str(e):
        budget_details_model = None

    quote_body = QuoteBody(
        line_items=line_items,
        subtotal=round(subtotal, 2),
        delivery_tier_applied=delivery_tier_summary,  # The summary string
        delivery_details=delivery_details_for_response,  # The detailed object
        notes="Quote is an estimate. Taxes and environmental fees are not included in this quote. Final price subject to final confirmation.",
        rental_details=rental_details_model,
        product_details=product_details_model,
        budget_details=budget_details_model
    )

    from app.models.quote import LocationDetails, QuoteMetadata

    # Convert dictionaries to proper models with error handling
    location_details_model = None
    try:
      if location_details:
        location_details_model = LocationDetails(**location_details)
    except Exception as e:
      logger.error(f"Error creating LocationDetails model: {e}", exc_info=True)
      # location_details_model is already None

    metadata_model = None
    try:
      if metadata:
        metadata_model = QuoteMetadata(**metadata)
    except Exception as e:
      logger.error(f"Error creating QuoteMetadata model: {e}", exc_info=True)
      # Fallback for metadata if creation fails
      from datetime import datetime
      logger.warning("Creating fallback QuoteMetadata due to error.")
      metadata_model = QuoteMetadata(
          generated_at=datetime.now(),
          version="1.0",  # Consider using a specific version or flag for fallback
          source_system="Stahla Pricing API (Fallback)",
          calculation_method="standard",
          valid_until=None,  # Add missing argument
          calculation_time_ms=None  # Add missing argument
          # Add minimal required fields, avoid complex data that might fail again
      )

    # Ensure metadata_model is never None if required by QuoteResponse
    if metadata_model is None:
      logger.error(
          "Fallback metadata creation also failed or metadata dict was None. Creating minimal fallback.")
      from datetime import datetime
      metadata_model = QuoteMetadata(
          generated_at=datetime.now(),
          version="fallback-error",
          source_system="Stahla Pricing API (Error Fallback)",
          calculation_method="unknown",
          valid_until=None,  # Add missing argument
          calculation_time_ms=None  # Add missing argument
      )

    response = QuoteResponse(
        request_id=request.request_id,
        quote=quote_body,
        location_details=location_details_model,  # Can be None
        metadata=metadata_model  # Should always have a value now
    )

    # Ensure subtotal is numeric before formatting
    try:
        # Attempt conversion only if subtotal is not None
      if quote_body.subtotal is not None:
        subtotal_float = float(quote_body.subtotal)
        subtotal_str = f"${subtotal_float:.2f}"
      else:
        subtotal_str = "$0.00"  # Or handle None case appropriately
    except (ValueError, TypeError):
      # Log as is if conversion fails, avoid float formatting
      subtotal_str = f"${quote_body.subtotal}"

    logger.info(
        f"Enhanced quote built successfully for request_id: {request.request_id}, quote_id: {response.quote_id}, total: {subtotal_str}"
    )
    return response

  def get_delivery_cost_for_distance(
      self, distance_miles: float, branch_name: str, delivery_config: Dict[str, Any]
  ) -> float:
    """Calculate delivery cost based on distance and branch location."""
    # Get delivery rates from config, handling both direct access and nested structures
    if isinstance(delivery_config, dict) and "delivery_config" in delivery_config:
      # If we're getting the full MongoDB document
      config = delivery_config.get("delivery_config", {})
    else:
      # If we're getting just the delivery_config section
      config = delivery_config

    # Extract the values with fallbacks
    base_fee = config.get("base_fee", 0.0)
    per_mile_rates = config.get(
        "per_mile_rates", {"omaha_kansas_city": 2.99, "denver": 3.99}
    )
    free_miles_threshold = config.get("free_miles_threshold", 25)

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

    # Safe formatting for log
    cost_str = f"${delivery_cost:.2f}" if isinstance(
        delivery_cost, (int, float)) else str(delivery_cost)
    base_fee_str = f"${base_fee:.2f}" if isinstance(
        base_fee, (int, float)) else str(base_fee)
    rate_str = f"${per_mile_rate:.2f}" if isinstance(
        per_mile_rate, (int, float)) else str(per_mile_rate)
    # Ensure billable_miles is numeric before formatting
    miles_str = f"{billable_miles:.2f}" if isinstance(
        billable_miles, (int, float)) else str(billable_miles)

    logger.info(
        f"Calculated delivery cost: {cost_str} (Base: {base_fee_str}, Rate: {rate_str}/mi, Billable Miles: {miles_str}, Branch: {branch_name})"
    )

    # Return 0 if calculation failed
    return delivery_cost if isinstance(delivery_cost, (int, float)) else 0.0

  async def get_config_for_quoting(self) -> Dict[str, Any]:
    """
    Get the configuration needed for quoting calculations, first from Redis,
    then falling back to MongoDB if needed.

    Returns:
        A dictionary containing delivery and seasonal multiplier configuration.
    """
    catalog = await self._get_pricing_catalog()
    if catalog:
      return {
          "delivery": catalog.get("delivery", {}),
          "seasonal_multipliers": catalog.get(
              "seasonal_multipliers", {"standard": 1.0, "tiers": []}
          ),
      }

    # If we couldn't get the full catalog, try just getting the config directly
    config = await self._get_config_from_mongo()
    if config:
      return {
          "delivery": config.get("delivery_config", {}),
          "seasonal_multipliers": config.get(
              "seasonal_multipliers_config", {"standard": 1.0, "tiers": []}
          ),
      }

    # If all else fails, return default values
    logger.warning(
        "Using default config values for quoting as no data could be retrieved from Redis or MongoDB"
    )
    return {
        "delivery": {
            "base_fee": 0.0,
            "per_mile_rates": {"omaha_kansas_city": 2.99, "denver": 3.99},
            "free_miles_threshold": 25,
        },
        "seasonal_multipliers": {"standard": 1.0, "tiers": []},
    }

  async def _estimate_distance_when_location_service_fails(
      self, delivery_location_str: str
  ) -> Optional[DistanceResult]:
    """
    Fallback method to estimate distances when the location service fails.
    Uses utilities from utils/location.py to geocode the delivery location
    and estimate distances to the nearest service hub.

    Args:
        delivery_location_str: The delivery location address as a string

    Returns:
        A DistanceResult object with the estimated distance data or None if geocoding fails
    """
    logger.info(
        f"Estimating distance for '{delivery_location_str}' using fallback mechanism"
    )

    # Step 1: Geocode the delivery location
    lat, lon = None, None  # Initialize
    try:
      loop = asyncio.get_running_loop()
      lat, lon = await loop.run_in_executor(None, geocode_location, delivery_location_str)
    except Exception as e:
      logger.error(
          f"Exception during fallback geocoding for '{delivery_location_str}': {e}", exc_info=True)
      # lat, lon will remain None

    if lat is None or lon is None:
      logger.error(
          f"Fallback geocoding failed for location: '{delivery_location_str}' (lat or lon is None after attempt)"
      )
      return None

    # Step 2: Find the nearest service hub
    nearest_hub_name = None
    min_distance_km = float("inf")

    for hub_name, (hub_lat, hub_lon) in SERVICE_HUBS.items():
      distance_km = get_distance_km(lat, lon, hub_lat, hub_lon)
      if distance_km < min_distance_km:
        min_distance_km = distance_km
        nearest_hub_name = hub_name

    if nearest_hub_name is None:
      logger.error("Failed to find nearest hub in fallback calculation")
      return None

    # Step 3: Convert km to miles and create fallback DistanceResult
    hub_description = nearest_hub_name.replace("_", " ").title()

    # Create a branch location object for the nearest hub
    nearest_branch = BranchLocation(
        name=f"{hub_description} (Estimated)",
        # No exact address available in fallback
        address=f"{hub_description}, USA",
    )

    # Convert km to miles (1 km ≈ 0.621371 miles)
    distance_miles = min_distance_km * 0.621371

    # Estimate other required fields
    distance_meters = int(min_distance_km * 1000)  # km to meters
    duration_seconds = int(
        distance_meters / 15
    )  # Rough estimate: 15 meters per second ≈ 33 mph

    logger.info(
        f"Fallback distance calculation complete: {distance_miles:.2f} miles to {nearest_hub_name}"
    )

    # Log to MongoDB for tracking fallback usage
    await self.mongo_service.log_error_to_db(
        service_name="QuoteService._estimate_distance_when_location_service_fails",
        error_type="FallbackLocationUsed",
        message=f"Used fallback location estimation for '{delivery_location_str}'",
        details={
            "delivery_location": delivery_location_str,
            "estimated_distance_miles": distance_miles,
            "nearest_hub": nearest_hub_name,
        },
    )

    return DistanceResult(
        nearest_branch=nearest_branch,
        delivery_location=delivery_location_str,
        distance_miles=distance_miles,
        distance_meters=distance_meters,
        duration_seconds=duration_seconds,
    )


# Dependency injection function
async def get_quote_service(
    redis_service: RedisService = Depends(get_redis_service),
    location_service: LocationService = Depends(get_location_service_dep),
    mongo_service: MongoService = Depends(get_mongo_service),
) -> QuoteService:
  """
  Dependency injection function to create a QuoteService instance.
  This allows for clean dependency injection in FastAPI routes.
  """
  return QuoteService(
      redis_service=redis_service,
      location_service=location_service,
      mongo_service=mongo_service,
  )
