# app/services/quote/quote/builder/response/formatter.py

"""
Response formatting builder component.
"""

import logging
from typing import Any, Dict
from datetime import datetime

import logfire
from app.models.quote import QuoteResponse, QuoteBody, LineItem, QuoteMetadata

logger = logging.getLogger(__name__)


class ResponseFormatter:
  """Handles formatting the final quote response."""

  def __init__(self, quote_service):
    self.quote_service = quote_service

  def format_quote_response(
      self,
      quote_request: Any,
      catalog: Dict[str, Any],
      distance_result: Any,
      trailer_result: Dict[str, Any],
      delivery_result: Dict[str, Any],
      extras_result: Dict[str, Any],
      background_tasks: Any = None
  ) -> QuoteResponse:
    """
    Format the final quote response.

    Args:
        quote_request: The original quote request
        trailer_result: Trailer pricing results
        delivery_result: Delivery pricing results  
        extras_result: Extras pricing results
        total_cost: Total calculated cost

    Returns:
        Formatted QuoteResponse object
    """
    try:
      # Calculate total cost from individual results
      total_cost = 0.0
      total_cost += trailer_result.get("base_cost", 0.0)
      total_cost += delivery_result.get("delivery_cost", 0.0)
      total_cost += extras_result.get("total_cost", 0.0)

      # Create line items
      line_items = []

      # Add trailer line item
      if trailer_result.get("success") and trailer_result.get("base_cost", 0) > 0:
        line_items.append(
            LineItem(
                description=f"{quote_request.trailer_type} - {quote_request.usage_type}",
                quantity=1,
                unit_price=trailer_result["base_cost"],
                total=trailer_result["base_cost"]
            )
        )

      # Add delivery line item
      if delivery_result.get("success") and delivery_result.get("delivery_cost", 0) > 0:
        line_items.append(
            LineItem(
                description="Delivery",
                quantity=1,
                unit_price=delivery_result["delivery_cost"],
                total=delivery_result["delivery_cost"]
            )
        )

      # Add extras line items
      if extras_result.get("success") and extras_result.get("line_items"):
        line_items.extend(extras_result["line_items"])

      # Create quote body
      quote_body = QuoteBody(
          line_items=line_items,
          subtotal=total_cost,
          delivery_tier_applied=delivery_result.get(
              "delivery_details", {}).get("tier_name"),
          delivery_details=delivery_result.get("delivery_details"),
          notes=None,
          rental_details=None,
          product_details=None,
          budget_details=None,
      )

      # Create metadata
      metadata = QuoteMetadata(
          generated_at=datetime.utcnow(),
          valid_until=None,
          version="1.0",
          source_system="Stahla Pricing API",
          calculation_method="standard",
          data_sources={},
          calculation_time_ms=None,
          warnings=[]
      )

      # Create final response
      response = QuoteResponse(
          request_id=quote_request.request_id,
          quote_id=f"QT-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
          quote=quote_body,
          location_details=None,
          metadata=metadata
      )

      logfire.info(
          f"Successfully formatted quote response: {response.quote_id}")
      return response

    except Exception as e:
      logfire.error(f"Error formatting quote response: {e}")
      # Return a basic error response
      error_metadata = QuoteMetadata(
          generated_at=datetime.utcnow(),
          valid_until=None,
          version="1.0",
          source_system="Stahla Pricing API",
          calculation_method="error",
          data_sources={},
          calculation_time_ms=None,
          warnings=[f"Error formatting response: {str(e)}"]
      )

      error_quote_body = QuoteBody(
          line_items=[],
          subtotal=0.0,
          delivery_tier_applied=None,
          delivery_details=None,
          notes=f"Error generating quote: {str(e)}",
          rental_details=None,
          product_details=None,
          budget_details=None,
      )

      return QuoteResponse(
          request_id=getattr(quote_request, 'request_id', 'unknown'),
          quote_id=f"ERROR-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
          quote=error_quote_body,
          location_details=None,
          metadata=error_metadata
      )
