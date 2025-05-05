import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends # Add Depends import

from app.models.quote import QuoteRequest, QuoteResponse, LineItem, QuoteBody, ExtraInput
from app.models.location import DistanceResult
from app.services.redis.redis import RedisService, get_redis_service # Import dependency function
from app.services.location.location import LocationService, get_location_service # Import dependency function
from app.services.quote.sync import PRICING_CATALOG_CACHE_KEY # Import cache key

logger = logging.getLogger(__name__)

# Constants for monthly calculations
DAYS_PER_MONTH_APPROX = 30.44 # Average days per month
MONTHS_2 = 2
MONTHS_5 = 5
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

    def _calculate_trailer_cost(self, trailer_id: str, rental_days: int, usage_type: str, event_tier: str, catalog: Dict[str, Any]) -> Optional[Tuple[float, str]]:
        """
        Calculates the rental cost for the trailer based on duration, usage type, and event tier.
        Returns a tuple: (cost, description_suffix) or (None, None) if invalid.
        """
        product_info = catalog.get("products", {}).get(trailer_id)
        if not product_info:
            logger.warning(f"Trailer type '{trailer_id}' not found in pricing catalog.")
            return None, None

        cost: Optional[float] = None
        description_suffix = f"({rental_days} days)" # Default description part

        # --- Event Pricing (<= 4 days assumed from headers) --- 
        if usage_type == "event" and rental_days <= 4:
            # Use the event_tier passed from the request
            # Map the input tier to the catalog key format
            tier_map = {
                "standard": "event_standard",
                "premium": "event_premium",
                "premium_plus": "event_premium_plus",
                "premium_platinum": "event_premium_platinum"
            }
            event_tier_key = tier_map.get(event_tier, "event_standard") # Default to standard if invalid tier provided
            
            cost = product_info.get(event_tier_key)
            if cost is None:
                 logger.warning(f"Event tier price '{event_tier_key}' not found for trailer '{trailer_id}'. Falling back to standard.")
                 # Fallback to standard if the specified tier price is missing
                 event_tier_key = "event_standard"
                 cost = product_info.get(event_tier_key)

            # Make description reflect the actual tier used
            tier_name = event_tier_key.replace('event_', '').replace('_', ' ').title()
            description_suffix = f"(Event <= 4 days - {tier_name})"
            logger.info(f"Applying Event pricing ({event_tier_key}) for '{trailer_id}': ${cost}")

        # --- Longer-term / Commercial Pricing --- 
        else:
            # Calculate approximate months for tier selection
            rental_months = rental_days / DAYS_PER_MONTH_APPROX

            # Determine applicable rate based on duration tiers
            rate_18_plus = product_info.get('rate_18_plus_month')
            rate_6_plus = product_info.get('rate_6_plus_month')
            rate_2_5 = product_info.get('rate_2_5_month')
            rate_28_day = product_info.get('rate_28_day')
            rate_weekly = product_info.get('weekly_7_day')

            monthly_rate = None
            rate_tier_desc = ""

            if rental_months >= MONTHS_18 and rate_18_plus is not None:
                monthly_rate = rate_18_plus
                rate_tier_desc = "18+ Month Rate"
            elif rental_months >= MONTHS_6 and rate_6_plus is not None:
                monthly_rate = rate_6_plus
                rate_tier_desc = "6+ Month Rate"
            elif rental_months >= MONTHS_2 and rate_2_5 is not None:
                monthly_rate = rate_2_5
                rate_tier_desc = "2-5 Month Rate"
            elif rental_days >= 28 and rate_28_day is not None:
                # Use 28-day rate if it's better than prorated monthly or weekly
                # This logic might need refinement based on exact business rules
                # For simplicity, let's prioritize the explicit 28-day rate if applicable
                num_28_day_periods = rental_days / 28
                cost = rate_28_day * num_28_day_periods # Prorate 28-day rate
                description_suffix = f"({rental_days} days - Prorated 28 Day Rate)"
                logger.info(f"Applying 28 Day Rate (prorated) for '{trailer_id}': ${cost:.2f}")
            elif rate_weekly is not None:
                # Fallback to weekly rate if no monthly/28-day applies or is better
                num_weeks = math.ceil(rental_days / 7) # Charge full weeks
                cost = rate_weekly * num_weeks
                description_suffix = f"({rental_days} days / {num_weeks} weeks - Weekly Rate)"
                logger.info(f"Applying Weekly Rate for '{trailer_id}': ${cost:.2f}")
            else:
                 logger.warning(f"Could not determine applicable rate for '{trailer_id}' ({rental_days} days). No weekly rate found.")
                 return None, None # Cannot price if no weekly rate

            # If a monthly rate was selected, calculate prorated cost
            if monthly_rate is not None and cost is None: # Check cost is None to avoid overwriting 28-day/weekly calc
                cost = (monthly_rate / DAYS_PER_MONTH_APPROX) * rental_days
                description_suffix = f"({rental_days} days - Prorated {rate_tier_desc})"
                logger.info(f"Applying {rate_tier_desc} (prorated) for '{trailer_id}': ${cost:.2f}")

        if cost is None:
            logger.error(f"Failed to calculate cost for trailer '{trailer_id}' ({rental_days} days, {usage_type}).")
            return None, None

        return round(cost, 2), description_suffix

    def _calculate_delivery_cost(self, distance_result: DistanceResult, catalog: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
        """
        Calculates the delivery cost based on distance and delivery tiers.
        *** Placeholder logic - Delivery rules are NOT in the provided sheet. ***
        *** This needs to be defined based on business rules (e.g., config, separate sheet). ***
        Returns (cost, tier_description)
        """
        delivery_config = catalog.get("delivery") # Uses placeholder from sheet_sync
        if not delivery_config:
            logger.warning("Delivery pricing configuration not found in catalog.")
            return None, None

        distance_miles = distance_result.distance_miles

        # --- Placeholder Delivery Logic (Same as before) --- 
        free_tier_miles = delivery_config.get('free_tier_miles', 0)
        per_mile_rate = delivery_config.get('per_mile_rate', 0)
        base_fee = delivery_config.get('base_fee', 0)

        if distance_miles <= free_tier_miles:
            cost = base_fee # Or potentially 0
            tier = f"Free Delivery Tier (up to {free_tier_miles} miles)"
            logger.info(f"Delivery cost (Free Tier): Base fee ${cost:.2f}")
        else:
            cost = base_fee + (distance_miles * per_mile_rate)
            tier = f"Standard Rate @ ${per_mile_rate:.2f}/mile (Base: ${base_fee:.2f})"
            logger.info(f"Delivery cost ({distance_miles:.1f} miles @ ${per_mile_rate:.2f}/mile + Base ${base_fee:.2f}): ${cost:.2f}")

        return cost, tier

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

        # 3. Calculate Trailer Rental Cost - Pass event_tier from request
        trailer_cost_result = self._calculate_trailer_cost(
            request.trailer_type,
            request.rental_days,
            request.usage_type,
            request.event_tier, # Pass the requested event tier
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

        # 4. Calculate Delivery Cost (Using Placeholder Logic)
        delivery_cost, delivery_tier = self._calculate_delivery_cost(distance_result, catalog)
        if delivery_cost is not None:
            line_items.append(LineItem(
                description=f"Delivery & Pickup ({distance_result.distance_miles:.1f} miles)",
                quantity=1, 
                unit_price=None, 
                total=round(delivery_cost, 2)
            ))
            subtotal += delivery_cost
        else:
            logger.warning("Could not calculate delivery cost.")

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
