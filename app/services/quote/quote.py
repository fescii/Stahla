import logging
import math
from datetime import date # Ensure date is imported
from typing import Any, Dict, List, Optional, Tuple, Literal # Import Literal

from fastapi import Depends # Add Depends import

from app.models.quote import QuoteRequest, QuoteResponse, LineItem, QuoteBody, ExtraInput
from app.models.location import DistanceResult
from app.services.redis.redis import RedisService, get_redis_service # Import dependency function
from app.services.location.location import LocationService, get_location_service # Import dependency function
from app.services.quote.sync import PRICING_CATALOG_CACHE_KEY # Import cache key

logger = logging.getLogger(__name__)

# Constants for pricing logic
DAYS_PER_MONTH_APPROX = 30.4375 # Average days in a month
MONTHS_2 = 2
MONTHS_6 = 6
MONTHS_18 = 18

class QuoteService:
    """
    Service responsible for calculating price quotes based on cached pricing data
    and calculated delivery distances.
    """

    def __init__(self, redis_service: RedisService, location_service: LocationService):
        self.redis_service = redis_service
        self.location_service = location_service

    async def _get_pricing_catalog(self) -> Optional[Dict[str, Any]]:
        """Retrieves the pricing catalog from Redis cache."""
        catalog = await self.redis_service.get_json(PRICING_CATALOG_CACHE_KEY)
        if not catalog:
            logger.error(f"Pricing catalog not found in Redis cache (key: '{PRICING_CATALOG_CACHE_KEY}'). Run sheet sync.")
            return None
        # TODO: Add validation for the catalog structure if needed
        return catalog

    def _determine_seasonal_multiplier(self, rental_start_date: date, seasonal_config: Dict[str, Any]) -> Tuple[float, str]:
        """Determines the seasonal rate multiplier based on the start date."""
        standard_rate = seasonal_config.get('standard', 1.0)
        tiers = seasonal_config.get('tiers', [])
        
        for tier in tiers:
            try:
                tier_start = date.fromisoformat(tier['start_date'])
                tier_end = date.fromisoformat(tier['end_date'])
                if tier_start <= rental_start_date <= tier_end:
                    rate = tier.get('rate', standard_rate)
                    name = tier.get('name', 'Seasonal')
                    logger.info(f"Applying seasonal tier '{name}' with rate {rate} for start date {rental_start_date}")
                    return rate, f" ({name} Season Rate)"
            except (ValueError, KeyError) as e:
                logger.warning(f"Could not parse seasonal tier {tier}: {e}")
                continue # Skip invalid tiers
                
        # Default to standard rate if no tier matches
        logger.info(f"Applying standard rate {standard_rate} for start date {rental_start_date}")
        return standard_rate, " (Standard Season Rate)"

    def _calculate_trailer_cost(
        self,
        trailer_id: str,
        rental_days: int,
        usage_type: Literal["commercial", "event"],
        rental_start_date: date,      # Changed from event_tier
        seasonal_config: Dict[str, Any], # Added seasonal_config
        catalog: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[str]]:
        """Calculates the base rental cost for a trailer, applying seasonal multipliers."""
        logger.info(f"Calculating cost for trailer: {trailer_id}, Days: {rental_days}, Usage: {usage_type}, Start: {rental_start_date}")
        products_catalog = catalog.get("products", {})
        product_info = products_catalog.get(trailer_id)

        if not product_info:
            logger.error(f"Trailer type '{trailer_id}' not found in pricing catalog.")
            return None, None

        cost: Optional[float] = None
        description_suffix = ""
        
        # Determine seasonal multiplier first
        rate_multiplier, season_desc = self._determine_seasonal_multiplier(rental_start_date, seasonal_config)

        # --- Event Pricing (<= 4 days) --- 
        if usage_type == "event" and rental_days <= 4:
            # Event pricing uses specific columns, not tiers based on date within the event window
            # We still apply the overall seasonal multiplier determined by the start date
            event_tier_key = "event_standard" # Default to standard event price
            cost = product_info.get(event_tier_key)
            
            if cost is None:
                 logger.error(f"Base event price ('{event_tier_key}') not found for trailer '{trailer_id}'. Cannot calculate event price.")
                 return None, None # Cannot price if base event price missing

            tier_name = event_tier_key.replace('event_', '').replace('_', ' ').title()
            description_suffix = f"(Event <= 4 days - {tier_name})"
            logger.info(f"Base Event pricing ({event_tier_key}) for '{trailer_id}': ${cost:.2f}")
            
            # Apply seasonal multiplier to the determined event cost
            cost *= rate_multiplier
            description_suffix += season_desc
            logger.info(f"Applied seasonal multiplier {rate_multiplier}. Final Event cost: ${cost:.2f}")

        # --- Longer-term / Commercial Pricing --- 
        else: # Commercial use OR Event > 4 days uses tiered rates
            # Calculate approximate months for tier selection
            rental_months = rental_days / DAYS_PER_MONTH_APPROX

            # Determine applicable base rate based on duration tiers
            rate_18_plus = product_info.get('rate_18_plus_month')
            rate_6_plus = product_info.get('rate_6_plus_month')
            rate_2_5 = product_info.get('rate_2_5_month')
            rate_28_day = product_info.get('rate_28_day')
            rate_weekly = product_info.get('weekly_7_day')

            base_monthly_rate = None
            base_cost = None
            rate_tier_desc = ""

            if rental_months >= MONTHS_18 and rate_18_plus is not None:
                base_monthly_rate = rate_18_plus
                rate_tier_desc = "18+ Month Rate"
            elif rental_months >= MONTHS_6 and rate_6_plus is not None:
                base_monthly_rate = rate_6_plus
                rate_tier_desc = "6+ Month Rate"
            elif rental_months >= MONTHS_2 and rate_2_5 is not None:
                base_monthly_rate = rate_2_5
                rate_tier_desc = "2-5 Month Rate"
            elif rental_days >= 28 and rate_28_day is not None:
                num_28_day_periods = rental_days / 28
                base_cost = rate_28_day * num_28_day_periods # Prorate 28-day rate
                rate_tier_desc = "Prorated 28 Day Rate"
                description_suffix = f"({rental_days} days - {rate_tier_desc})"
                logger.info(f"Base rate: {rate_tier_desc} for '{trailer_id}': ${base_cost:.2f}")
            elif rate_weekly is not None:
                num_weeks = math.ceil(rental_days / 7) # Charge full weeks
                base_cost = rate_weekly * num_weeks
                rate_tier_desc = "Weekly Rate"
                description_suffix = f"({rental_days} days / {num_weeks} weeks - {rate_tier_desc})"
                logger.info(f"Base rate: {rate_tier_desc} for '{trailer_id}': ${base_cost:.2f}")
            else:
                 logger.warning(f"Could not determine applicable base rate for '{trailer_id}' ({rental_days} days). No weekly rate found.")
                 return None, None # Cannot price if no weekly rate

            # If a monthly rate was selected, calculate prorated base cost
            if base_monthly_rate is not None and base_cost is None: # Check base_cost is None to avoid overwriting 28-day/weekly calc
                base_cost = (base_monthly_rate / DAYS_PER_MONTH_APPROX) * rental_days
                description_suffix = f"({rental_days} days - Prorated {rate_tier_desc})"
                logger.info(f"Base rate: Prorated {rate_tier_desc} for '{trailer_id}': ${base_cost:.2f}")

            if base_cost is None:
                 logger.error(f"Failed to calculate base cost for trailer '{trailer_id}' ({rental_days} days, {usage_type}).")
                 return None, None

            # Apply seasonal multiplier to the determined base cost
            cost = base_cost * rate_multiplier
            description_suffix += season_desc
            logger.info(f"Applied seasonal multiplier {rate_multiplier}. Final cost: ${cost:.2f}")

        # Final check if cost calculation failed
        if cost is None:
            logger.error(f"Cost calculation resulted in None for trailer '{trailer_id}' ({rental_days} days, {usage_type}).")
            return None, None

        return round(cost, 2), description_suffix

    def _calculate_delivery_cost(
        self, 
        distance_result: DistanceResult, 
        catalog: Dict[str, Any],
        rate_multiplier: float, # Added
        season_desc: str        # Added
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Calculates the delivery cost based on distance and delivery tiers,
        applying seasonal multipliers.
        """
        delivery_config = catalog.get("delivery")
        if not delivery_config:
            logger.warning("Delivery pricing configuration not found in catalog.")
            return None, None

        distance_miles = distance_result.distance_miles
        free_tier_miles = delivery_config.get('free_miles_threshold', 25) # Default to 25 if not in config
        per_mile_rate = delivery_config.get('per_mile_rate', 0)
        base_fee = delivery_config.get('base_fee', 0)

        if distance_miles <= free_tier_miles:
            cost = 0.0 # Free if within threshold
            tier = f"Free Delivery (<= {free_tier_miles} miles)"
            logger.info(f"Delivery cost (Free Tier): ${cost:.2f}")
            # Note: Seasonal multiplier typically doesn't apply to free services, but confirm business rule.
            # Assuming multiplier does NOT apply if cost is 0.
        else:
            # Apply seasonal multiplier to base fee and per-mile rate components
            calculated_base_fee = base_fee * rate_multiplier
            calculated_per_mile_rate = per_mile_rate * rate_multiplier
            cost = calculated_base_fee + (distance_miles * calculated_per_mile_rate)
            # Add season description to the tier info
            tier = f"Standard Rate @ ${per_mile_rate:.2f}/mile (Base: ${base_fee:.2f}){season_desc}"
            logger.info(f"Delivery cost ({distance_miles:.1f} miles @ ${per_mile_rate:.2f}/mile + Base ${base_fee:.2f}) * Multiplier {rate_multiplier:.2f}: ${cost:.2f}")

        # Return cost rounded to 2 decimal places
        return round(cost, 2), tier

    def _calculate_extras_cost(self, extras_input: List[ExtraInput], trailer_id: str, rental_days: int, catalog: Dict[str, Any]) -> List[LineItem]:
        """
        Calculates the cost for requested extras (generators, services).
        Uses pricing from generator catalog and service costs from product catalog.
        """
        extra_line_items: List[LineItem] = []
        generators_catalog = catalog.get("generators", {})
        product_info = catalog.get("products", {}).get(trailer_id) # For trailer-specific service costs
        product_extras = product_info.get("extras", {}) if product_info else {}

        for extra in extras_input:
            extra_id = extra.extra_id
            qty = extra.qty
            item_cost: Optional[float] = None
            description: str = f"{qty}x {extra_id}"
            unit_price: Optional[float] = None

            # --- Generator Pricing --- 
            if extra_id in generators_catalog:
                gen_info = generators_catalog[extra_id]
                gen_name = gen_info.get('name', extra_id)
                rate_event = gen_info.get('rate_event')
                rate_7_day = gen_info.get('rate_7_day')
                rate_28_day = gen_info.get('rate_28_day')

                if rental_days <= 3 and rate_event is not None:
                    item_cost = rate_event * qty
                    unit_price = rate_event
                    description = f"{qty}x {gen_name} (Event <= 3 days)"
                elif rental_days <= 7 and rate_7_day is not None:
                    item_cost = rate_7_day * qty
                    unit_price = rate_7_day
                    description = f"{qty}x {gen_name} (<= 7 days)"
                elif rental_days <= 28 and rate_28_day is not None:
                    # Use 28 day rate if <= 28 days and it exists
                    item_cost = rate_28_day * qty
                    unit_price = rate_28_day
                    description = f"{qty}x {gen_name} (<= 28 days)"
                elif rate_28_day is not None: # Longer than 28 days, prorate 28 day rate
                    num_periods = rental_days / 28
                    item_cost = rate_28_day * num_periods * qty
                    unit_price = None # Prorated, unit price is complex
                    description = f"{qty}x {gen_name} ({rental_days} days - Prorated 28 Day Rate)"
                elif rate_7_day is not None: # Fallback: prorate weekly if no 28 day rate
                    num_weeks = math.ceil(rental_days / 7)
                    item_cost = rate_7_day * num_weeks * qty
                    unit_price = None # Prorated, unit price is complex
                    description = f"{qty}x {gen_name} ({rental_days} days - Weekly Rate)"
                else:
                    logger.warning(f"Could not determine rate for generator '{extra_id}' ({rental_days} days).")
                    item_cost = 0.00 # Or handle as error
                    description = f"{qty}x {gen_name} (Pricing Unavailable)"

                logger.info(f"Calculated generator cost for '{extra_id}' (Qty: {qty}, Days: {rental_days}): ${item_cost:.2f}")

            # --- Service Pricing (Pump out, Water Fill, Cleaning, Restocking) --- 
            # Use costs associated with the *trailer* being rented
            elif extra_id in product_extras:
                service_cost = product_extras.get(extra_id)
                if service_cost is not None:
                    item_cost = service_cost * qty # Cost is per service instance
                    unit_price = service_cost
                    # Make description friendlier
                    service_name = extra_id.replace('_', ' ').title()
                    description = f"{qty}x {service_name} Service"
                    logger.info(f"Calculated service cost for '{extra_id}' (Qty: {qty}): ${item_cost:.2f}")
                else:
                    logger.warning(f"Service '{extra_id}' found but has no price in catalog for trailer {trailer_id}.")
                    item_cost = 0.00
                    description = f"{qty}x {extra_id.replace('_', ' ').title()} (Pricing Unavailable)"
            
            # --- Add logic for other non-catalog extras if needed --- 
            # elif extra_id == 'attendant_service':
            #    item_cost = 500.00 * qty # Example fixed price
            #    unit_price = 500.00
            #    description = f"{qty}x On-site Attendant Service"

            else:
                logger.warning(f"Extra item '{extra_id}' not found in pricing catalog or product extras.")
                item_cost = 0.00 # Default to 0 if unknown
                description = f"{qty}x {extra_id} (Unknown Item)"

            if item_cost is not None:
                extra_line_items.append(
                    LineItem(
                        description=description,
                        quantity=qty,
                        unit_price=round(unit_price, 2) if unit_price is not None else None,
                        total=round(item_cost, 2)
                    )
                )

        return extra_line_items

    async def build_quote(self, request: QuoteRequest) -> QuoteResponse:
        """
        Builds a complete quote response based on the request.
        """
        logger.info(f"Building quote for request_id: {request.request_id}")
        line_items: List[LineItem] = []
        subtotal = 0.0

        # 1. Get Pricing Catalog from Cache
        catalog = await self._get_pricing_catalog()
        if not catalog:
            raise ValueError("Pricing data is currently unavailable. Please try again later.")

        # 2. Get Delivery Distance
        distance_result = await self.location_service.get_distance_to_nearest_branch(request.delivery_location)
        if not distance_result:
            raise ValueError(f"Could not determine delivery distance for location: {request.delivery_location}")

        # 3. Calculate Trailer Rental Cost - Pass start date and seasonal config
        seasonal_config = catalog.get("seasonal_multipliers", {})
        trailer_cost_result = self._calculate_trailer_cost(
            request.trailer_type,
            request.rental_days,
            request.usage_type,
            request.rental_start_date, # Pass start date
            seasonal_config,         # Pass seasonal config
            catalog
        )
        if trailer_cost_result is None or trailer_cost_result[0] is None:
            raise ValueError(f"Could not calculate price for trailer type: {request.trailer_type} for {request.rental_days} days ({request.usage_type}). Check catalog and request.")
        
        trailer_cost, trailer_desc_suffix = trailer_cost_result
        trailer_info = catalog.get("products", {}).get(request.trailer_type, {})
        trailer_name = trailer_info.get('name', request.trailer_type)
        line_items.append(LineItem(
            description=f"{trailer_name} Rental {trailer_desc_suffix}",
            quantity=1,
            unit_price=trailer_cost, 
            total=trailer_cost
        ))
        subtotal += trailer_cost

        # 4. Calculate Delivery Cost - Pass seasonal multiplier and description
        delivery_cost, delivery_tier = self._calculate_delivery_cost(
            distance_result, 
            catalog,
            trailer_cost_result[0], # Pass multiplier determined for trailer
            trailer_desc_suffix      # Pass season description determined for trailer
        )
        if delivery_cost is not None and delivery_tier is not None:
            line_items.append(LineItem(
                description=delivery_tier, # Use the tier description from the calculation
                quantity=1, 
                unit_price=None, # Keep as None as it's a calculated total
                total=round(delivery_cost, 2)
            ))
            subtotal += delivery_cost
        else:
            logger.warning("Could not calculate delivery cost or tier description was missing.")

        # 5. Calculate Extras Cost
        extra_line_items = self._calculate_extras_cost(
            request.extras, 
            request.trailer_type, 
            request.rental_days, 
            catalog
        )
        line_items.extend(extra_line_items)
        subtotal += sum(item.total for item in extra_line_items)

        # 6. Construct Response
        quote_body = QuoteBody(
            line_items=line_items,
            subtotal=round(subtotal, 2),
            delivery_tier_applied=delivery_tier,
            notes="Quote is an estimate. Taxes not included. Final price subject to final confirmation."
        )

        response = QuoteResponse(
            request_id=request.request_id,
            quote=quote_body
        )

        logger.info(f"Quote built successfully for request_id: {request.request_id}, quote_id: {response.quote_id}, total: ${quote_body.subtotal:.2f}")
        return response

# Dependency for FastAPI
async def get_quote_service(
    redis_service: RedisService = Depends(get_redis_service),
    location_service: LocationService = Depends(get_location_service)
) -> QuoteService:
    return QuoteService(redis_service, location_service)
