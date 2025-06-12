# Add BackgroundTasks
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
import logfire
# Import QuoteLineItem
from app.models.pricing import PricingInput, PriceQuote, QuoteLineItem
# from app.services.pricing.optimizer import generate_optimized_quote
from datetime import datetime, timezone  # Import datetime
import uuid  # Import uuid
# Add authentication dependency if needed:
# from app.api.dependencies import get_current_user
from app.services.mongo import MongoService  # Import MongoService
from app.core.dependencies import get_mongo_service  # Import get_mongo_service
from app.services.redis.redis import RedisService, get_redis_service  # Added
from app.services.dash.background import (  # Added
    increment_request_counter_bg,
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY
)

router = APIRouter()


@router.post(
    "/quote",
    response_model=PriceQuote,
    summary="Generate Price Quote",
    description="Receives rental requirements and generates an itemized price quote. Currently returns sample data.",  # Updated description
    tags=["Pricing"]
)
async def create_price_quote(
    pricing_input: PricingInput,
    background_tasks: BackgroundTasks,  # Add BackgroundTasks dependency
    mongo_service: MongoService = Depends(
        get_mongo_service),  # Add MongoService dependency
    redis_service: RedisService = Depends(get_redis_service)  # Added
    # current_user: User = Depends(get_current_user) # Example authentication
):
  """
  Generates a price quote based on the provided input details.

  This endpoint takes detailed requirements gathered by the SDR agent (or potentially
  another system) and returns an itemized quote.
  **NOTE:** Currently returns sample data for testing purposes.
  """
  logfire.info(f"Received quote request: {pricing_input.request_id}")
  success = False
  try:
    # --- START SAMPLE DATA ---
    # Simulate quote generation based on input
    logfire.info("Generating sample quote data.")
    sample_total = 500.00  # Base price
    line_items = [
        QuoteLineItem(description="Sample Rental Item", quantity=pricing_input.num_units or 1,
                      unit_price=200.00, total_amount=(pricing_input.num_units or 1) * 200.00),
        QuoteLineItem(description="Sample Delivery Fee",
                      quantity=1, total_amount=100.00)
    ]
    if pricing_input.requires_ada:
      line_items.append(QuoteLineItem(
          description="Sample ADA Add-on", quantity=1, total_amount=50.00))
      sample_total += 50.00

    sample_total = sum(item.total_amount for item in line_items)

    quote = PriceQuote(
        request_id=pricing_input.request_id,
        quote_id=f"QT-SAMPLE-{uuid.uuid4()}",
        line_items=line_items,
        total_amount=sample_total,
        currency="USD",
        notes="This is a sample quote generated for testing purposes.",
        is_estimate=True,
        missing_info=[
            "Sample missing info"] if not pricing_input.power_available else [],
        generated_at=datetime.now(datetime.timezone.utc).isoformat(),
    )
    logfire.info(
        f"Successfully generated sample quote for request: {pricing_input.request_id}")
    success = True
    logfire.info(
        f"EXITING TRY BLOCK: create_price_quote for {pricing_input.request_id}, success={success}")
    return quote
  except Exception as e:
    logfire.error(
        f"EXCEPTION in create_price_quote for {pricing_input.request_id}: {e}", exc_info=True)
    success = False
    logfire.info(
        f"EXITING EXCEPT BLOCK: create_price_quote for {pricing_input.request_id}, success={success}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred while generating the quote."
    )
  finally:
    logfire.info(
        f"FINALLY BLOCK in /api/v1/endpoints/pricing.py: Adding background task for quote request counters, success={success} for request_id: {pricing_input.request_id}")
    if redis_service:
      try:
        # Increment total quote requests counter
        background_tasks.add_task(
            increment_request_counter_bg, redis_service, TOTAL_QUOTE_REQUESTS_KEY)

        if success:
          # Increment successful quote requests counter
          background_tasks.add_task(
              increment_request_counter_bg, redis_service, SUCCESS_QUOTE_REQUESTS_KEY)
        else:
          # Increment error/failed quote requests counter
          background_tasks.add_task(
              increment_request_counter_bg, redis_service, ERROR_QUOTE_REQUESTS_KEY)

        logfire.info(
            f"FINALLY BLOCK in /api/v1/endpoints/pricing.py: Background tasks for quote request counters ADDED for request_id: {pricing_input.request_id}.")
      except Exception as e_bg_task:
        logfire.error(
            f"FINALLY BLOCK in /api/v1/endpoints/pricing.py: Error ADDING background tasks for quote request counters for request_id: {pricing_input.request_id}: {e_bg_task}", exc_info=True)
    else:
      logfire.error(
          f"FINALLY BLOCK in /api/v1/endpoints/pricing.py: redis_service is None. Cannot add background tasks for quote request counters for request_id: {pricing_input.request_id}.")
