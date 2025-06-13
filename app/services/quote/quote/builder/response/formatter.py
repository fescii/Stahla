# app/services/quote/quote/builder/response/formatter.py

"""
Response formatting builder component.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

import logfire
from app.models.quote import QuoteResponse, QuoteBody, LineItem, QuoteMetadata
from app.models.quote.response.details.location import LocationDetails

logger = logging.getLogger(__name__)


class ResponseFormatter:
  """Handles formatting the final quote response."""

  def __init__(self, quote_service):
    self.quote_service = quote_service

  def _extract_stall_count(self, trailer_type: str) -> Optional[int]:
    """Extract stall count from trailer type name."""
    import re
    # Look for numbers followed by "stall" in the trailer type
    match = re.search(r'(\d+)\s*stall', trailer_type.lower())
    if match:
      return int(match.group(1))
    return None

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

      # Make sure we safely handle any values that might be None
      trailer_cost = trailer_result.get("base_cost", 0.0)
      if trailer_cost is None:
        trailer_cost = 0.0

      delivery_cost = delivery_result.get("delivery_cost", 0.0)
      if delivery_cost is None:
        delivery_cost = 0.0

      extras_cost = extras_result.get("total_cost", 0.0)
      if extras_cost is None:
        extras_cost = 0.0

      total_cost += trailer_cost
      total_cost += delivery_cost
      total_cost += extras_cost

      # Create line items
      line_items = []

      # Add trailer line item
      if trailer_result.get("success") and trailer_result.get("base_cost", 0) > 0:
        # Create description with suffix if available
        description = f"{quote_request.trailer_type} - {quote_request.usage_type}"
        if trailer_result.get("description_suffix"):
          description += f" {trailer_result['description_suffix']}"

        line_items.append(
            LineItem(
                description=description,
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
        # Convert dict line items back to LineItem objects if needed
        for item_data in extras_result["line_items"]:
          if isinstance(item_data, dict):
            line_items.append(LineItem(**item_data))
          else:
            line_items.append(item_data)

      # Create rental details
      from datetime import timedelta
      rental_end_date = quote_request.rental_start_date + \
          timedelta(days=quote_request.rental_days)
      rental_weeks = quote_request.rental_days // 7 if quote_request.rental_days >= 7 else None
      rental_months = round(quote_request.rental_days / 30.4375,
                            2) if quote_request.rental_days >= 30 else None

      # Determine pricing tier
      pricing_tier = "Event Rate"
      if quote_request.usage_type == "commercial":
        if quote_request.rental_days >= 28:
          pricing_tier = "Monthly Rate"
        elif quote_request.rental_days >= 7:
          pricing_tier = "Weekly Rate"
        else:
          pricing_tier = "Daily Rate"

      from app.models.quote.response.details.rental import RentalDetails
      rental_details = RentalDetails(
          rental_start_date=quote_request.rental_start_date,
          rental_end_date=rental_end_date,
          rental_days=quote_request.rental_days,
          rental_weeks=rental_weeks,
          rental_months=rental_months,
          usage_type=quote_request.usage_type,
          pricing_tier_applied=pricing_tier,
          seasonal_rate_name="Standard Season",
          seasonal_multiplier=1.0
      )

      # Create product details
      products_catalog = catalog.get("products", {})
      trailer_info = products_catalog.get(quote_request.trailer_type, {})

      from app.models.quote.response.details.product import ProductDetails
      product_details = ProductDetails(
          product_id=quote_request.trailer_type,
          product_name=trailer_info.get("name", quote_request.trailer_type),
          product_description=trailer_info.get("description"),
          base_rate=trailer_cost,
          adjusted_rate=trailer_cost,
          features=trailer_info.get("features", []),
          stall_count=self._extract_stall_count(quote_request.trailer_type),
          is_ada_compliant="ada" in quote_request.trailer_type.lower(),
          trailer_size_ft=trailer_info.get("size"),
          capacity_persons=trailer_info.get("capacity")
      )

      # Create budget details
      cost_breakdown = {}
      for item in line_items:
        if "trailer" in item.description.lower() or quote_request.trailer_type.lower() in item.description.lower():
          cost_breakdown["trailer_rental"] = item.total
        elif "delivery" in item.description.lower():
          cost_breakdown["delivery"] = item.total
        elif "generator" in item.description.lower():
          cost_breakdown["generator"] = cost_breakdown.get(
              "generator", 0) + item.total
        elif "service" in item.description.lower() or "pump" in item.description.lower() or "cleaning" in item.description.lower():
          cost_breakdown["services"] = cost_breakdown.get(
              "services", 0) + item.total
        else:
          cost_breakdown["other"] = cost_breakdown.get("other", 0) + item.total

      daily_rate = round(total_cost / quote_request.rental_days,
                         2) if quote_request.rental_days > 0 else 0
      weekly_rate = round(daily_rate * 7, 2) if daily_rate > 0 else None
      monthly_rate = round(daily_rate * 30, 2) if daily_rate > 0 else None

      from app.models.quote.response.details.budget import BudgetDetails
      budget_details = BudgetDetails(
          subtotal=total_cost,
          estimated_total=total_cost,  # Could add taxes/fees here in the future
          daily_rate_equivalent=daily_rate,
          weekly_rate_equivalent=weekly_rate,
          monthly_rate_equivalent=monthly_rate,
          cost_breakdown=cost_breakdown,
          is_delivery_free=delivery_cost == 0,
          discounts_applied=None
      )

      # Create quote body
      quote_body = QuoteBody(
          line_items=line_items,
          subtotal=total_cost,
          delivery_tier_applied=delivery_result.get(
              "delivery_details", {}).get("tier_name"),
          delivery_details=delivery_result.get("delivery_details"),
          notes="Quote is an estimate. Final pricing subject to confirmation. Taxes and fees not included.",
          rental_details=rental_details,
          product_details=product_details,
          budget_details=budget_details,
      )

      # Create metadata
      from datetime import timedelta
      metadata = QuoteMetadata(
          generated_at=datetime.now(timezone.utc),
          valid_until=datetime.now(timezone.utc) +
          timedelta(days=14),  # 14 days validity
          version="1.0",
          source_system="Stahla Pricing Engine",  # Keep minimal source system
          calculation_method="standard",
          data_sources={
              "pricing": "Stahla Pricing API",
              "customer_data": "HubSpot",
              "classification": "Marvin AI Classification"
          },
          calculation_time_ms=None,
          warnings=[]
      )

      # Create location details from distance result
      location_details = None
      if distance_result:
        try:
          # Use geocoded coordinates from distance result if available (already cached)
          geocoded_coords = distance_result.geocoded_coordinates if hasattr(
              distance_result, 'geocoded_coordinates') else None

          # Determine service area type based on distance
          service_area_type = "Primary"
          if hasattr(distance_result, 'distance_miles'):
            if distance_result.distance_miles > 100:
              service_area_type = "Remote"
            elif distance_result.distance_miles > 50:
              service_area_type = "Extended"

          location_details = LocationDetails(
              delivery_address=quote_request.delivery_location,
              nearest_branch=distance_result.nearest_branch.name if hasattr(
                  distance_result, 'nearest_branch') and distance_result.nearest_branch else "Unknown",
              branch_address=distance_result.nearest_branch.address if hasattr(
                  distance_result, 'nearest_branch') and distance_result.nearest_branch and hasattr(distance_result.nearest_branch, 'address') else "Unknown",
              distance_miles=distance_result.distance_miles if hasattr(
                  distance_result, 'distance_miles') else 0.0,
              estimated_drive_time_minutes=int(distance_result.duration_seconds / 60) if hasattr(
                  distance_result, 'duration_seconds') and distance_result.duration_seconds else None,
              is_estimated_location=getattr(
                  distance_result, 'is_estimated', False),
              geocoded_coordinates=geocoded_coords,
              service_area_type=service_area_type
          )
        except Exception as e:
          logger.warning(f"Failed to create LocationDetails: {e}")
          location_details = None

      # Create final response
      response = QuoteResponse(
          request_id=quote_request.request_id,
          quote_id=f"QT-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
          quote=quote_body,
          location_details=location_details,
          metadata=metadata
      )

      logfire.info(
          f"Successfully formatted quote response: {response.quote_id}")
      return response

    except Exception as e:
      logfire.error(f"Error formatting quote response: {e}")
      # Return a basic error response
      error_metadata = QuoteMetadata(
          generated_at=datetime.now(timezone.utc),
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
          quote_id=f"ERROR-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
          quote=error_quote_body,
          location_details=None,
          metadata=error_metadata
      )
