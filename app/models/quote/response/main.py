"""
Main quote response model definition.
"""

import uuid
from pydantic import BaseModel, Field
from typing import Optional

from .body import QuoteBody
from .meta.data import QuoteMetadata
from .details.location import LocationDetails


class QuoteResponse(BaseModel):
  """Response payload for the /v1/webhook/quote endpoint."""

  request_id: str = Field(..., description="Original request ID.")
  quote_id: str = Field(
      default_factory=lambda: f"QT-{uuid.uuid4()}",
      description="Unique identifier for this generated quote.",
  )
  quote: QuoteBody = Field(..., description="The detailed quote information.")
  location_details: Optional[LocationDetails] = Field(
      None, description="Detailed information about the delivery location.")
  metadata: QuoteMetadata = Field(...,
                                  description="Metadata about the quote generation process.")

  class Config:
    json_schema_extra = {
        "example": {
            "request_id": "req_abc123",
            "quote_id": "QT-xyz789",
            "quote": {
                "line_items": [
                    {
                        "description": "Standard 3-Stall ADA Trailer Rental (7 days - Weekly Rate)",
                        "unit_price": 1500.00,
                        "quantity": 1,
                        "total": 1500.00,
                    },
                    {
                        "description": "Delivery & Pickup (55 miles)",
                        "unit_price": 3.50,
                        "quantity": 55,
                        "total": 192.50,
                    },
                    {
                        "description": "10kW Generator Rental (7 days)",
                        "unit_price": 300.00,
                        "quantity": 1,
                        "total": 300.00,
                    },
                    {
                        "description": "On-site Attendant Service (Event)",
                        "unit_price": 500.00,
                        "quantity": 1,
                        "total": 500.00,
                    },
                ],
                "subtotal": 2492.50,
                "delivery_tier_applied": "Standard Rate @ $3.50/mile",
                "delivery_details": {
                    "miles": 55.0,
                    "calculation_reason": "Standard Rate @ $3.50/mile (Standard Season Rate)",
                    "total_delivery_cost": 192.50,
                    "original_per_mile_rate": 3.50,
                    "original_base_fee": 0.00,
                    "seasonal_multiplier_applied": 1.0,
                    "per_mile_rate_applied": 3.50,
                    "base_fee_applied": 0.00,
                    "is_distance_estimated": False
                },
                "notes": "Quote valid for 14 days. Taxes not included. Final price subject to site conditions.",
                "product_details": {
                    "product_id": "standard_3_stall_ada",
                    "product_name": "Standard 3-Stall ADA Restroom Trailer",
                    "product_description": "Spacious 3-stall restroom trailer with ADA-compliant features",
                    "base_rate": 1500.00,
                    "adjusted_rate": 1500.00,
                    "features": ["ADA Compliant", "Handwashing Station", "Climate Control", "Vanity Mirror"],
                    "stall_count": 3,
                    "is_ada_compliant": True,
                    "trailer_size_ft": "16 x 8",
                    "capacity_persons": 250
                },
                "rental_details": {
                    "rental_start_date": "2025-07-10",
                    "rental_end_date": "2025-07-17",
                    "rental_days": 7,
                    "rental_weeks": 1,
                    "rental_months": 0.23,
                    "usage_type": "event",
                    "pricing_tier_applied": "Weekly Rate",
                    "seasonal_rate_name": "Standard Season",
                    "seasonal_multiplier": 1.0
                },
                "budget_details": {
                    "subtotal": 2492.50,
                    "estimated_total": 2741.90,
                    "daily_rate_equivalent": 356.07,
                    "weekly_rate_equivalent": 2492.50,
                    "monthly_rate_equivalent": 10680.00,
                    "cost_breakdown": {
                        "trailer_rental": 1500.00,
                        "delivery": 192.50,
                        "generator": 300.00,
                        "services": 500.00
                    },
                    "is_delivery_free": False,
                    "discounts_applied": [
                        {
                            "name": "First-time customer",
                            "amount": 50.00,
                            "type": "fixed"
                        }
                    ]
                }
            },
            "location_details": {
                "delivery_address": "456 Oak Ave, Otherville, CA 95678",
                "nearest_branch": "Sacramento",
                "branch_address": "123 Branch St, Sacramento, CA 95814",
                "distance_miles": 55.0,
                "estimated_drive_time_minutes": 65,
                "is_estimated_location": False,
                "geocoded_coordinates": {
                    "latitude": 38.5816,
                    "longitude": -121.4944
                },
                "service_area_type": "Primary"
            },
            "metadata": {
                "generated_at": "2025-05-13T14:32:10.123456",
                "valid_until": "2025-05-27T14:32:10.123456",
                "version": "1.0",
                "source_system": "Stahla Pricing API",
                "calculation_method": "standard",
                "data_sources": {
                    "pricing": "May 2025 Rate Sheet",
                    "location": "Google Maps API",
                    "seasonal_rates": "2025 Seasonal Calendar"
                },
                "calculation_time_ms": 234,
                "warnings": []
            }
        }
    }
