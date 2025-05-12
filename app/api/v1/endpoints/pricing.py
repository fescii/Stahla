from fastapi import APIRouter, Depends, HTTPException, status
import logfire
from app.models.pricing import PricingInput, PriceQuote, QuoteLineItem # Import QuoteLineItem
# from app.services.pricing.optimizer import generate_optimized_quote
from datetime import datetime # Import datetime
import uuid # Import uuid
# Add authentication dependency if needed:
# from app.api.dependencies import get_current_user

router = APIRouter()

@router.post(
    "/quote",
    response_model=PriceQuote,
    summary="Generate Price Quote",
    description="Receives rental requirements and generates an itemized price quote. Currently returns sample data.", # Updated description
    tags=["Pricing"]
)
async def create_price_quote(
    pricing_input: PricingInput,
    # current_user: User = Depends(get_current_user) # Example authentication
):
    """
    Generates a price quote based on the provided input details.

    This endpoint takes detailed requirements gathered by the SDR agent (or potentially
    another system) and returns an itemized quote.
    **NOTE:** Currently returns sample data for testing purposes.
    """
    logfire.info(f"Received quote request: {pricing_input.request_id}")
    try:
        # --- START SAMPLE DATA --- 
        # Simulate quote generation based on input
        logfire.info("Generating sample quote data.")
        sample_total = 500.00 # Base price
        line_items = [
            QuoteLineItem(description="Sample Rental Item", quantity=pricing_input.num_units or 1, unit_price=200.00, total_amount=(pricing_input.num_units or 1) * 200.00),
            QuoteLineItem(description="Sample Delivery Fee", quantity=1, total_amount=100.00)
        ]
        if pricing_input.requires_ada:
            line_items.append(QuoteLineItem(description="Sample ADA Add-on", quantity=1, total_amount=50.00))
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
            missing_info=["Sample missing info"] if not pricing_input.power_available else [],
            generated_at=datetime.now(datetime.timezone.utc).isoformat(),
        )
        # --- END SAMPLE DATA ---

        # Original logic (commented out for now):
        # quote = generate_optimized_quote(pricing_input)
        # if not quote.line_items and quote.is_estimate:
        #      logfire.warn(f"Quote generation failed for {pricing_input.request_id} due to missing info.", missing=quote.missing_info)
        #      # Return a 400 Bad Request if critical info was missing for any calculation
        #      raise HTTPException(
        #          status_code=status.HTTP_400_BAD_REQUEST,
        #          detail=f"Cannot generate quote. Missing critical information: {', '.join(quote.missing_info)}"
        #      )

        logfire.info(f"Successfully generated sample quote for request: {pricing_input.request_id}")
        return quote
    except Exception as e:
        logfire.error(f"Error generating quote for {pricing_input.request_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the quote."
        )
