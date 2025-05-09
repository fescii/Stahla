from pydantic import BaseModel, Field, field_validator, conint, constr
from typing import List, Literal, Optional
import uuid
from datetime import date

# --- Request Models ---

class ExtraInput(BaseModel):
    """Represents an extra item requested with quantity."""
    extra_id: str = Field(..., description="Identifier for the extra item (e.g., 'generator_5kw', 'handwash_station').")
    qty: conint(gt=0) = Field(..., description="Quantity of the extra item needed.")

class QuoteRequest(BaseModel):
    """Input payload for the /v1/webhook/quote endpoint."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this quote request.")
    delivery_location: str = Field(..., description="Full delivery address (Street, City, State, Zip).", example="123 Main St, Anytown, CA 91234")
    trailer_type: str = Field(..., description="Specific Stahla trailer model ID.", example="luxury_2_stall")
    rental_start_date: date = Field(..., description="Rental start date in YYYY-MM-DD format.")
    rental_days: conint(gt=0) = Field(..., description="Total rental duration in days.")
    usage_type: Literal["commercial", "event"] = Field(..., description="Normalized usage type.")
    extras: List[ExtraInput] = Field(default_factory=list, description="List of requested extra items.")

    @field_validator('rental_start_date', mode='before')
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
                    {"extra_id": "attendant_service", "qty": 1}
                ]
            }
        }

# --- Response Models ---

class LineItem(BaseModel):
    """Represents a single line item in the quote response."""
    description: str = Field(..., description="Description of the item or service.")
    unit_price: Optional[float] = Field(None, description="Price per unit (if applicable).")
    quantity: int = Field(..., description="Quantity of the item.")
    total: float = Field(..., description="Total cost for this line item.")

class DeliveryCostDetails(BaseModel):
    """Detailed breakdown of the delivery cost calculation."""
    miles: float = Field(..., description="Distance in miles for the delivery.")
    calculation_reason: str = Field(..., description="Explanation of how the delivery cost was calculated (e.g., tier name, free delivery rule).")
    total_delivery_cost: float = Field(..., description="Total calculated cost for delivery.")
    original_per_mile_rate: Optional[float] = Field(None, description="The original per-mile rate before any multipliers.")
    original_base_fee: Optional[float] = Field(None, description="The original base fee before any multipliers.")
    seasonal_multiplier_applied: Optional[float] = Field(None, description="Seasonal multiplier applied to delivery, if any.")
    per_mile_rate_applied: Optional[float] = Field(None, description="The per-mile rate applied after any multipliers (original_rate * multiplier).")
    base_fee_applied: Optional[float] = Field(None, description="The base fee applied after any multipliers (original_fee * multiplier).")

class QuoteBody(BaseModel):
    """The main body of the quote response."""
    line_items: List[LineItem] = Field(..., description="Detailed list of charges.")
    subtotal: float = Field(..., description="Subtotal before taxes or potential fees.")
    delivery_tier_applied: Optional[str] = Field(None, description="Summary name of the delivery pricing tier applied (e.g., 'Free Tier', 'Standard Rate'). This is often the same as part of calculation_reason in delivery_details.") # Kept for summary, but details are in delivery_details
    delivery_details: Optional[DeliveryCostDetails] = Field(None, description="Detailed breakdown of the delivery cost calculation.") # New field
    notes: Optional[str] = Field(None, description="Additional notes or disclaimers.")

class QuoteResponse(BaseModel):
    """Response payload for the /v1/webhook/quote endpoint."""
    request_id: str = Field(..., description="Original request ID.")
    quote_id: str = Field(default_factory=lambda: f"QT-{uuid.uuid4()}", description="Unique identifier for this generated quote.")
    quote: QuoteBody = Field(..., description="The detailed quote information.")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_abc123",
                "quote_id": "QT-xyz789",
                "quote": {
                    "line_items": [
                        {
                            "description": "Standard 3-Stall ADA Trailer Rental (7 days)",
                            "unit_price": 1500.00,
                            "quantity": 1,
                            "total": 1500.00
                        },
                        {
                            "description": "Delivery & Pickup (55 miles)",
                            "unit_price": 3.50,
                            "quantity": 55,
                            "total": 192.50
                        },
                        {
                            "description": "10kW Generator Rental (7 days)",
                            "unit_price": 300.00,
                            "quantity": 1,
                            "total": 300.00
                        },
                         {
                            "description": "On-site Attendant Service (Event)",
                            "unit_price": 500.00,
                            "quantity": 1,
                            "total": 500.00
                        }
                    ],
                    "subtotal": 2492.50,
                    "delivery_tier_applied": "Standard Rate @ $3.50/mile",
                    "notes": "Quote valid for 14 days. Taxes not included. Final price subject to site conditions."
                }
            }
        }
