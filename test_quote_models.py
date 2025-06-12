"""
Simple test script to verify the refactored quote models.
"""

from app.models.quote import (
    ExtraInput,
    QuoteRequest,
    LineItem,
    DeliveryCostDetails,
    LocationDetails,
    RentalDetails,
    ProductDetails,
    BudgetDetails,
    QuoteBody,
    QuoteMetadata,
    QuoteResponse
)
import sys
from datetime import date
from pprint import pprint

# Add parent directory to path for importing
sys.path.append('/home/femar/A03/Stahla')

# Import the refactored models


def test_models():
  """Test creating instances of the refactored models."""

  # Create ExtraInput
  extra = ExtraInput(extra_id="generator_10kw", qty=1)
  print(f"Extra: {extra.model_dump()}")

  # Create QuoteRequest
  request = QuoteRequest(
      delivery_location="456 Oak Ave, Otherville, CA 95678",
      trailer_type="standard_3_stall_ada",
      rental_start_date=date(2025, 7, 10),
      rental_days=7,
      usage_type="event",
      extras=[extra]
  )
  print(f"Request ID: {request.request_id}")
  print(f"Request: {request.model_dump()}")

  # Create LineItem
  line_item = LineItem(
      description="Standard 3-Stall ADA Trailer Rental (7 days - Weekly Rate)",
      unit_price=1500.00,
      quantity=1,
      total=1500.00
  )
  print(f"Line Item: {line_item.model_dump()}")

  # Create detailed quote response
  response = QuoteResponse(
      request_id=request.request_id,
      quote=QuoteBody(
          line_items=[line_item],
          subtotal=1500.00,
          delivery_tier_applied="Standard Rate @ $3.50/mile",
          notes="Quote is an estimate.",
          delivery_details=None,  # These can be None
          rental_details=None,
          product_details=None,
          budget_details=None
      ),
      location_details=None,  # This can be None
      metadata=QuoteMetadata(
          valid_until=None,  # These can be None
          calculation_time_ms=None,
          version="1.0",  # Use defaults for required fields
          source_system="Stahla Pricing API",
          calculation_method="standard"
      )
  )

  print(f"Quote ID: {response.quote_id}")
  print("Quote Response created successfully!")


if __name__ == "__main__":
  try:
    test_models()
    print("\nTEST SUCCEEDED: All models imported and instantiated correctly!")
  except Exception as e:
    print(f"\nTEST FAILED: {e}")
    import traceback
    traceback.print_exc()
