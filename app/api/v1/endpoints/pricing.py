from fastapi import APIRouter, Depends, HTTPException, status
import logfire
from app.models.pricing import PricingInput, PriceQuote
from app.services.pricing.optimizer import generate_optimized_quote
# Add authentication dependency if needed:
# from app.api.dependencies import get_current_user

router = APIRouter()

@router.post(
    "/quote",
    response_model=PriceQuote,
    summary="Generate Price Quote",
    description="Receives rental requirements and generates an itemized price quote using the internal pricing optimizer.",
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
    """
    logfire.info(f"Received quote request: {pricing_input.request_id}")
    try:
        # Call the Marvin function (which might be sync or async depending on Marvin setup)
        # If generate_optimized_quote becomes async: await generate_optimized_quote(pricing_input)
        quote = generate_optimized_quote(pricing_input)

        if not quote.line_items and quote.is_estimate:
             logfire.warn(f"Quote generation failed for {pricing_input.request_id} due to missing info.", missing=quote.missing_info)
             # Return a 400 Bad Request if critical info was missing for any calculation
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail=f"Cannot generate quote. Missing critical information: {', '.join(quote.missing_info)}"
             )

        logfire.info(f"Successfully generated quote for request: {pricing_input.request_id}")
        return quote
    except Exception as e:
        logfire.error(f"Error generating quote for {pricing_input.request_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the quote."
        )
