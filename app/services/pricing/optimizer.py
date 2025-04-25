import marvin
import logfire
from app.models.pricing import PricingInput, PriceQuote, QuoteLineItem
from typing import List

# --- Mock Pricing Data (Replace with actual data source/logic/config) ---
# This should ideally be loaded from config or a database
BASE_RATES = {
    "Portable Toilet": {"daily": 50, "weekly": 150, "monthly": 400},
    "Restroom Trailer": {"daily": 400, "weekly": 1200, "monthly": 3500},
    "Shower Trailer": {"daily": 500, "weekly": 1500, "monthly": 4500},
    "ADA Trailer": {"daily": 450, "weekly": 1300, "monthly": 3800},
    "Handwashing Station": {"daily": 30, "weekly": 80, "monthly": 250},
}
DELIVERY_COST = {"local": 150, "non_local": 450, "estimate_factor": 1.2} # Factor if location vague
SERVICE_COST = {"pump_clean": 100, "water_fill": 50}
EXTRAS_COST = {"generator_small": 75, "generator_large": 250, "cord_ramps": 20} # Per day/unit as applicable
# --- End Mock Pricing Data ---

def _calculate_rental_cost(product: str, num_units: int, duration_days: int, usage: str) -> tuple[float, str]:
    """Calculates base rental cost and determines tier."""
    # Simplified tier logic - real logic might be more complex
    tier = f"{usage}_daily"
    rate_period = "daily"
    rate_multiplier = duration_days

    if duration_days >= 28 and 'monthly' in BASE_RATES.get(product, {}):
        tier = f"{usage}_monthly"
        rate_period = "monthly"
        rate_multiplier = duration_days / 30.0 # Approximate months
    elif duration_days >= 7 and 'weekly' in BASE_RATES.get(product, {}):
        tier = f"{usage}_weekly"
        rate_period = "weekly"
        # Calculate weeks and remaining days
        weeks = duration_days // 7
        days = duration_days % 7
        weekly_rate = BASE_RATES[product]['weekly']
        daily_rate = BASE_RATES[product]['daily']
        total_cost = (weekly_rate * weeks + daily_rate * days) * num_units
        return round(total_cost, 2), tier

    unit_rate = BASE_RATES.get(product, {}).get(rate_period, 0)
    if unit_rate == 0: # Fallback if product/rate missing
        unit_rate = BASE_RATES.get("Portable Toilet", {}).get(rate_period, 50) # Default to basic porta potty
        logfire.warn(f"Missing rate for {product}/{rate_period}, using default.")

    total_cost = unit_rate * rate_multiplier * num_units
    return round(total_cost, 2), tier


@marvin.fn
def generate_optimized_quote(data: PricingInput) -> PriceQuote:
    """
    Analyzes the rental request details provided in `data` (derived from SDR call script slots)
    and generates an optimized, itemized price quote based on Stahla's pricing rules.

    **Input Data Mapping (from Call Script Slots):**
    - `product_type`: Slot Product_Type
    - `num_units`: Slot Units_Needed
    - `usage_type`: Slot Customer_Type
    - `rental_duration_days`: Slot Duration
    - `start_date`: Slot Start_Date
    - `delivery_location_description`: Slot Location
    - `is_local`: Determined internally based on location
    - `site_surface`: Slot Surface_Type (PAQ/PBQ)
    - `ground_level`: Slot Ground_Level (PBQ)
    - `obstacles_present`: Slot Obstacles (PAQ/PBQ)
    - `power_available`: Slot Power_Available (PAQ)
    - `water_available`: Slot Water_Available (PAQ)
    - `power_distance_feet`/`water_distance_feet`: From PAQ questions
    - `requires_ada`: Slot ADA_Required
    - `requires_shower`: Slot Shower_Required
    - `requires_handwashing`: Slot Handwashing_Needed
    - `requires_cleaning_service`: From Subflow SB context
    - `attendee_count`: From Units_Needed clarification
    - `other_products_mentioned`: From Subflow SA/SB
    - `decision_timeline`/`quote_needed_by`: From Process PA/PB wrap-up

    **Pricing Considerations & Logic:**
    1.  **Base Rental:** Calculate using `_calculate_rental_cost` based on `product_type`, `num_units`, `rental_duration_days`, and `usage_type`. If `requires_ada` is True, ensure an ADA product is quoted (e.g., 'ADA Trailer' or potentially an ADA porta potty if applicable). If `requires_shower` is True, ensure 'Shower Trailer' is considered.
    2.  **Delivery:** Use `DELIVERY_COST`. Apply `estimate_factor` and add note if `delivery_location_description` is vague (e.g., contains 'TBD', 'Area', lacks specific address/city). Base cost on `is_local`.
    3.  **Services:**
        - Add `pump_clean` (`SERVICE_COST`) if `usage_type` is 'construction'/'facility' AND `requires_cleaning_service` is True. Estimate frequency (e.g., weekly for monthly rentals, bi-weekly for 2-week rentals).
        - Add `pump_clean` if `usage_type` is 'event', `rental_duration_days` > 1, and `event_total_hours` >= 8.
        - Add `water_fill` (`SERVICE_COST`) if `water_available` is False. Estimate frequency based on duration/usage (e.g., every 3-5 days).
    4.  **Add-ons:**
        - Add `generator_small` or `generator_large` (`EXTRAS_COST`, charged per day) if `power_available` is False. Use 'small' for duration < 3 days, 'large' otherwise. Also add if 'generator' is in `other_products_mentioned`.
        - Add `cord_ramps` (`EXTRAS_COST`, flat rate per ramp) if power/water hoses might cross paths (check distances > 50ft or if 'ramp' in `other_products_mentioned`). Estimate quantity (e.g., 2).
        - Add `Handwashing Station` rental if `requires_handwashing` is True, using `_calculate_rental_cost`.
    5.  **Validation & Estimates:** Check for missing mandatory fields (`product_type`, `num_units`, `rental_duration_days`, `delivery_location_description`). If missing, set `is_estimate=True` and add to `missing_info`. Also set `is_estimate=True` if site conditions (`site_surface`, `ground_level`, `obstacles_present`) are unknown/None. Add relevant notes.
    6.  **Output:** Return a `PriceQuote` object with `request_id`, itemized `line_items` (including quantity and unit price where applicable), `subtotal`, `applied_pricing_tier`, relevant `notes`, `is_estimate` flag, and `missing_info` list.
    """
    # --- Marvin AI will generate the implementation based on the instructions ---
    # --- Placeholder logic below for structure ---
    logfire.info(f"Generating quote for request: {data.request_id}", data=data.model_dump())
    line_items: List[QuoteLineItem] = []
    notes: List[str] = []
    missing_info: List[str] = []
    subtotal = 0.0
    is_estimate = False
    applied_tier = None

    # Validation
    if not data.product_type or data.product_type == "Unknown": missing_info.append("Product Type")
    if not data.num_units or data.num_units < 1: missing_info.append("Number of Units")
    if not data.rental_duration_days or data.rental_duration_days < 1: missing_info.append("Rental Duration")
    if not data.delivery_location_description or "Unknown" in data.delivery_location_description or "TBD" in data.delivery_location_description:
        missing_info.append("Specific Delivery Location")
        is_estimate = True # Delivery cost is estimate

    # Site condition checks
    if data.site_surface is None: missing_info.append("Site Surface Type"); is_estimate = True
    if data.ground_level is None and "Toilet" in data.product_type: missing_info.append("Ground Level Check"); is_estimate = True # More critical for PT
    if data.obstacles_present is None: missing_info.append("Obstacle Check"); is_estimate = True
    if data.power_available is None and "Trailer" in data.product_type: missing_info.append("Power Availability"); is_estimate = True
    if data.water_available is None and "Trailer" in data.product_type: missing_info.append("Water Availability"); is_estimate = True

    if missing_info:
        is_estimate = True
        notes.append(f"Quote is an estimate due to missing info: {', '.join(missing_info)}")
        # Optionally, return early if critical info is missing
        if "Product Type" in missing_info or "Rental Duration" in missing_info:
             logfire.warn("Cannot generate quote due to missing critical info.", missing=missing_info)
             return PriceQuote(request_id=data.request_id, line_items=[], subtotal=0.0, notes=notes, is_estimate=True, missing_info=missing_info)

    # --- Start Calculation (Simplified Example) ---
    # 1. Base Rental
    product_to_quote = data.product_type
    num_units_to_quote = data.num_units
    # Handle ADA override
    if data.requires_ada:
        if "Trailer" in product_to_quote:
            product_to_quote = "ADA Trailer" # Assume ADA trailer if trailer requested
        else:
            # Need specific ADA porta potty product name if exists, else flag
            notes.append("ADA requirement noted. Assuming standard ADA unit.")
            # product_to_quote = "ADA Portable Toilet" # If exists in BASE_RATES

    rental_cost, applied_tier = _calculate_rental_cost(product_to_quote, num_units_to_quote, data.rental_duration_days, data.usage_type)
    unit_price_rental = round(rental_cost / num_units_to_quote, 2) if num_units_to_quote > 0 else 0
    line_items.append(QuoteLineItem(
        description=f"{product_to_quote} Rental ({data.rental_duration_days} days)",
        quantity=num_units_to_quote,
        unit_price=unit_price_rental,
        total_amount=rental_cost
    ))
    subtotal += rental_cost

    # Add Handwashing if required
    if data.requires_handwashing:
        hw_product = "Handwashing Station"
        hw_units = max(1, num_units_to_quote // 5) # Example: 1 per 5 units
        hw_cost, _ = _calculate_rental_cost(hw_product, hw_units, data.rental_duration_days, data.usage_type)
        hw_unit_price = round(hw_cost / hw_units, 2) if hw_units > 0 else 0
        line_items.append(QuoteLineItem(
            description=f"{hw_product} ({data.rental_duration_days} days)",
            quantity=hw_units,
            unit_price=hw_unit_price,
            total_amount=hw_cost
        ))
        subtotal += hw_cost

    # 2. Delivery
    delivery_key = "local" if data.is_local else "non_local"
    delivery_cost = DELIVERY_COST[delivery_key]
    if "Specific Delivery Location" in missing_info:
        delivery_cost *= DELIVERY_COST["estimate_factor"]
        notes.append("Delivery cost estimated due to vague location.")
    line_items.append(QuoteLineItem(description="Delivery & Pickup", total_amount=round(delivery_cost, 2)))
    subtotal += delivery_cost

    # 3. Services (Very Simplified)
    if (data.usage_type in ["construction", "facility"] and data.requires_cleaning_service) or \
       (data.usage_type == "event" and data.rental_duration_days > 1 and (data.event_total_hours or 0) >= 8):
        num_services = max(1, data.rental_duration_days // 7) if data.rental_duration_days >= 7 else (1 if data.rental_duration_days > 1 else 0)
        if num_services > 0:
            service_cost = SERVICE_COST["pump_clean"] * num_services
            line_items.append(QuoteLineItem(description="Waste Tank Service", quantity=num_services, unit_price=SERVICE_COST["pump_clean"], total_amount=round(service_cost, 2)))
            subtotal += service_cost
            notes.append(f"Includes {num_services}x cleaning/pumping service.")

    if data.water_available == False:
        num_fills = max(1, data.rental_duration_days // 3)
        water_cost = SERVICE_COST["water_fill"] * num_fills
        line_items.append(QuoteLineItem(description="Fresh Water Fill", quantity=num_fills, unit_price=SERVICE_COST["water_fill"], total_amount=round(water_cost, 2)))
        subtotal += water_cost
        notes.append("Includes fresh water delivery.")

    # 4. Add-ons
    if data.power_available == False or any("generator" in p.lower() for p in data.other_products_mentioned):
        gen_type = "generator_large" if data.rental_duration_days >= 3 else "generator_small"
        gen_cost_per_day = EXTRAS_COST[gen_type]
        gen_total_cost = gen_cost_per_day * data.rental_duration_days
        line_items.append(QuoteLineItem(description=f"Generator Rental ({gen_type.split('_')[1]})", quantity=1, unit_price=gen_cost_per_day, total_amount=round(gen_total_cost, 2)))
        subtotal += gen_total_cost
        notes.append("Includes generator rental.")

    # --- Final Assembly ---
    final_quote = PriceQuote(
        request_id=data.request_id,
        line_items=line_items,
        subtotal=round(subtotal, 2),
        applied_pricing_tier=applied_tier,
        notes=notes,
        is_estimate=is_estimate,
        missing_info=missing_info
    )
    logfire.info(f"Generated quote result: {final_quote.model_dump()}")
    return final_quote
