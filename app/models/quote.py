from pydantic import BaseModel, Field, field_validator, conint, constr
from typing import List, Literal, Optional, Dict, Any
import uuid
from datetime import date, datetime, timedelta

# --- Request Models ---


class ExtraInput(BaseModel):
  """Represents an extra item requested with quantity."""

  extra_id: str = Field(
      ...,
      description="Identifier for the extra item (e.g., 'generator_5kw', 'handwash_station').",
  )
  qty: int = Field(..., gt=0,
                   description="Quantity of the extra item needed.")


class QuoteRequest(BaseModel):
  """Input payload for the /v1/webhook/quote endpoint."""

  request_id: str = Field(
      default_factory=lambda: str(uuid.uuid4()),
      description="Unique identifier for this quote request.",
  )
  delivery_location: str = Field(
      ...,
      description="Full delivery address (Street, City, State, Zip).",
  )
  trailer_type: str = Field(
      ..., description="Specific Stahla trailer model ID."
  )
  rental_start_date: date = Field(
      ..., description="Rental start date in YYYY-MM-DD format."
  )
  rental_days: int = Field(..., gt=0,
                           description="Total rental duration in days.")
  usage_type: Literal["commercial", "event"] = Field(
      ..., description="Normalized usage type."
  )
  extras: List[ExtraInput] = Field(
      default_factory=list, description="List of requested extra items."
  )

  @field_validator("rental_start_date", mode="before")
  @classmethod
  def parse_date(cls, value):
    if isinstance(value, str):
      try:
        return date.fromisoformat(value)
      except ValueError:
        raise ValueError("Invalid date format, expected YYYY-MM-DD")
    return value

  class Config:
    json_schema_extra = {
        "example": {
            "request_id": "req_abc123",
            "delivery_location": "456 Oak Ave, Otherville, CA 95678",
            "trailer_type": "standard_3_stall_ada",
            "rental_start_date": "2025-07-10",
            "rental_days": 7,
            "usage_type": "event",
            "extras": [
                {"extra_id": "generator_10kw", "qty": 1},
                {"extra_id": "attendant_service", "qty": 1},
            ],
        }
    }


# --- Response Models ---


class LineItem(BaseModel):
  """Represents a single line item in the quote response."""

  description: str = Field(...,
                           description="Description of the item or service.")
  unit_price: Optional[float] = Field(
      None, description="Price per unit (if applicable)."
  )
  quantity: int = Field(..., description="Quantity of the item.")
  total: float = Field(..., description="Total cost for this line item.")


class DeliveryCostDetails(BaseModel):
  """Detailed breakdown of the delivery cost calculation."""

  miles: float = Field(..., description="Distance in miles for the delivery.")
  calculation_reason: str = Field(
      ...,
      description="Explanation of how the delivery cost was calculated (e.g., tier name, free delivery rule).",
  )
  total_delivery_cost: float = Field(
      ..., description="Total calculated cost for delivery."
  )
  original_per_mile_rate: Optional[float] = Field(
      None, description="The original per-mile rate before any multipliers."
  )
  original_base_fee: Optional[float] = Field(
      None, description="The original base fee before any multipliers."
  )
  seasonal_multiplier_applied: Optional[float] = Field(
      None, description="Seasonal multiplier applied to delivery, if any."
  )
  per_mile_rate_applied: Optional[float] = Field(
      None,
      description="The per-mile rate applied after any multipliers (original_rate * multiplier).",
  )
  base_fee_applied: Optional[float] = Field(
      None,
      description="The base fee applied after any multipliers (original_fee * multiplier).",
  )
  is_distance_estimated: bool = Field(
      False,
      description="Indicates whether the distance was estimated using fallback calculation.",
  )


class LocationDetails(BaseModel):
  """Detailed information about the delivery location and nearest branch."""

  delivery_address: str = Field(
      ..., description="Full delivery address as provided in the request.")
  nearest_branch: str = Field(...,
                              description="Name of the nearest Stahla branch.")
  branch_address: str = Field(...,
                              description="Address of the nearest Stahla branch.")
  distance_miles: float = Field(
      ..., description="Distance in miles between delivery location and nearest branch.")
  estimated_drive_time_minutes: Optional[int] = Field(
      None, description="Estimated drive time in minutes.")
  is_estimated_location: bool = Field(
      False, description="Whether the location details were estimated rather than precisely calculated.")
  geocoded_coordinates: Optional[dict] = Field(
      None, description="Latitude and longitude of the delivery location if available.")
  service_area_type: Optional[str] = Field(
      None, description="Type of service area (e.g., 'Primary', 'Secondary', 'Remote').")


class RentalDetails(BaseModel):
  """Detailed information about the rental terms and conditions."""

  rental_start_date: date = Field(...,
                                  description="Start date of the rental period.")
  rental_end_date: date = Field(
      ..., description="End date of the rental period (calculated from start date and rental days).")
  rental_days: int = Field(...,
                           description="Total duration of rental in days.")
  rental_weeks: Optional[int] = Field(
      None, description="Number of full weeks in the rental period.")
  rental_months: Optional[float] = Field(
      None, description="Approximate number of months in the rental period.")
  usage_type: str = Field(...,
                          description="Type of usage (commercial or event).")
  pricing_tier_applied: str = Field(
      ..., description="Pricing tier applied based on duration and usage type.")
  seasonal_rate_name: Optional[str] = Field(
      None, description="Name of the seasonal rate applied if any.")
  seasonal_multiplier: float = Field(
      1.0, description="Seasonal rate multiplier applied to the base price.")


class ProductDetails(BaseModel):
  """Detailed information about the quoted product."""

  product_id: str = Field(..., description="Product identifier.")
  product_name: str = Field(..., description="Full name of the product.")
  product_description: Optional[str] = Field(
      None, description="Detailed description of the product.")
  base_rate: float = Field(...,
                           description="Base rate before any adjustments.")
  adjusted_rate: float = Field(...,
                               description="Final rate after all adjustments.")
  features: Optional[List[str]] = Field(
      None, description="List of key features of the product.")
  stall_count: Optional[int] = Field(
      None, description="Number of stalls if applicable.")
  is_ada_compliant: Optional[bool] = Field(
      None, description="Whether the product is ADA compliant.")
  trailer_size_ft: Optional[str] = Field(
      None, description="Size of the trailer in feet.")
  capacity_persons: Optional[int] = Field(
      None, description="Maximum recommended capacity in persons.")


class BudgetDetails(BaseModel):
  """Detailed breakdown of costs and budget information."""

  subtotal: float = Field(...,
                          description="Subtotal before taxes or additional fees.")
  estimated_taxes: Optional[float] = Field(
      None, description="Estimated taxes if applicable.")
  estimated_fees: Optional[float] = Field(
      None, description="Estimated additional fees if applicable.")
  estimated_total: float = Field(
      ..., description="Estimated total including taxes and fees if provided.")
  daily_rate_equivalent: Optional[float] = Field(
      None, description="Daily rate equivalent for the rental.")
  weekly_rate_equivalent: Optional[float] = Field(
      None, description="Weekly rate equivalent for the rental.")
  monthly_rate_equivalent: Optional[float] = Field(
      None, description="Monthly rate equivalent for the rental.")
  cost_breakdown: Dict[str, float] = Field(
      default_factory=dict, description="Breakdown of costs by category.")
  is_delivery_included: bool = Field(
      ..., description="Whether delivery is included in the price.")
  discounts_applied: Optional[List[Dict[str, Any]]] = Field(
      None, description="List of any discounts applied.")


class QuoteBody(BaseModel):
  """The main body of the quote response."""

  line_items: List[LineItem] = Field(...,
                                     description="Detailed list of charges.")
  subtotal: float = Field(...,
                          description="Subtotal before taxes or potential fees.")
  delivery_tier_applied: Optional[str] = Field(
      None,
      description="Summary name of the delivery pricing tier applied (e.g., 'Free Tier', 'Standard Rate'). This is often the same as part of calculation_reason in delivery_details.",
  )  # Kept for summary, but details are in delivery_details
  delivery_details: Optional[DeliveryCostDetails] = Field(
      None, description="Detailed breakdown of the delivery cost calculation."
  )  # New field
  notes: Optional[str] = Field(
      None, description="Additional notes or disclaimers.")
  rental_details: Optional[RentalDetails] = Field(
      None, description="Detailed information about the rental terms and conditions.")
  product_details: Optional[ProductDetails] = Field(
      None, description="Detailed information about the quoted product.")
  budget_details: Optional[BudgetDetails] = Field(
      None, description="Detailed breakdown of costs and budget information.")


class QuoteMetadata(BaseModel):
  """Metadata about the quote generation process."""

  generated_at: datetime = Field(
      default_factory=datetime.now, description="Timestamp when the quote was generated.")
  valid_until: Optional[datetime] = Field(
      None, description="Timestamp until which the quote is valid.")
  version: str = Field("1.0", description="Version of the quote format.")
  source_system: str = Field(
      "Stahla Pricing API", description="System that generated the quote.")
  calculation_method: str = Field(
      "standard", description="Method used to calculate the quote.")
  data_sources: Dict[str, str] = Field(
      default_factory=dict, description="Sources of data used in the calculation.")
  calculation_time_ms: Optional[int] = Field(
      None, description="Time taken to calculate the quote in milliseconds.")
  warnings: List[str] = Field(
      default_factory=list, description="Any warnings generated during quote calculation.")


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
                    "estimated_taxes": 199.40,
                    "estimated_fees": 50.00,
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
                    "is_delivery_included": False,
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
