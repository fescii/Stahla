from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
import uuid

class PricingInput(BaseModel):
    """Inputs required to generate a price quote for Stahla rentals, gathered during the SDR interaction."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this pricing request.")
    # Core Product/Service Details
    product_type: str = Field(..., description="Primary product type requested (e.g., 'Restroom Trailer', 'Portable Toilet', 'Shower Trailer', 'ADA Trailer'). Derived from Slot: Product_Type.")
    num_units: int = Field(..., ge=1, description="Number of units or stalls requested. Derived from Slot: Units_Needed.")
    usage_type: Literal["event", "construction", "facility", "disaster_relief", "other"] = Field(..., description="The intended use case for the rental. Derived from Slot: Customer_Type.")
    rental_duration_days: int = Field(..., ge=1, description="Total number of days the rental is needed. Derived from Slot: Duration.")
    start_date: Optional[str] = Field(None, description="Approximate start date (ISO 8601 format if possible). Derived from Slot: Start_Date.")
    event_total_hours: Optional[int] = Field(None, description="For multi-day events, the total estimated hours of active use. Relevant for service calculation.")

    # Location & Site Details (Mandatory for Quote)
    delivery_location_description: str = Field(..., description="Delivery address or city/state. Derived from Slot: Location.")
    is_local: bool = Field(..., description="Whether the location is considered 'local' based on proximity to hubs (e.g., within 3 hours drive time). Determined internally.")
    site_surface: Optional[Literal["cement", "gravel", "dirt", "grass"]] = Field(None, description="Surface type at the placement location. Derived from Slot: Surface_Type (PAQ/PBQ).")
    ground_level: Optional[bool] = Field(None, description="Is the ground level/flat? Derived from Slot: Ground_Level (PBQ).")
    obstacles_present: Optional[bool] = Field(None, description="Are there low branches or obstacles? Derived from Slot: Obstacles (PAQ/PBQ).")
    power_available: Optional[bool] = Field(None, description="Is adequate power available at the placement site? Derived from Slot: Power_Available (PAQ).")
    water_available: Optional[bool] = Field(None, description="Is a water hookup (garden hose) available at the placement site? Derived from Slot: Water_Available (PAQ).")
    power_distance_feet: Optional[int] = Field(None, description="Estimated distance to power source in feet. Derived from PAQ.")
    water_distance_feet: Optional[int] = Field(None, description="Estimated distance to water source in feet. Derived from PAQ.")

    # Specific Requirements
    requires_ada: bool = Field(default=False, description="Does the request specifically require ADA-compliant units? Derived from Slot: ADA_Required.")
    requires_shower: bool = Field(default=False, description="Are shower facilities required? Derived from Slot: Shower_Required.")
    requires_handwashing: bool = Field(default=False, description="Are separate handwashing stations required? Derived from Slot: Handwashing_Needed.")
    requires_cleaning_service: bool = Field(default=False, description="Is regular cleaning/restocking service requested (primarily for non-event use)? Derived from Subflow SB.")

    # Context & Intent
    attendee_count: Optional[int] = Field(None, description="Estimated number of attendees/users for capacity planning. Derived from Slot: Units_Needed clarification.")
    other_products_mentioned: Optional[List[str]] = Field(default_factory=list, description="Other products mentioned (e.g., ['Tent', 'Generator']). Derived from Subflow SA/SB.")
    decision_timeline: Optional[str] = Field(None, description="When does the prospect plan to make a decision? Derived from Process PA/PB.")
    quote_needed_by: Optional[str] = Field(None, description="How soon is the quote needed? Derived from Process PA/PB.")
    call_summary: Optional[str] = Field(None, description="Summary of the voice call, if applicable.") # From ClassificationInput
    full_transcript: Optional[str] = Field(None, description="Full transcript of the voice call, if applicable.") # From ClassificationInput

    class Config:
        extra = 'ignore' # Ignore fields not defined here if passed from broader context
        json_schema_extra = {
            "example": {
                "product_type": "Restroom Trailer",
                "num_units": 2,
                "usage_type": "event",
                "rental_duration_days": 3,
                "start_date": "2025-08-15",
                "delivery_location_description": "Central Park, Fort Collins CO",
                "is_local": True,
                "site_surface": "grass",
                "ground_level": True,
                "obstacles_present": False,
                "power_available": False,
                "water_available": True,
                "water_distance_feet": 75,
                "requires_ada": True,
                "attendee_count": 500,
                "other_products_mentioned": ["generator", "fencing"],
                "quote_needed_by": "End of week",
                "decision_timeline": "Next month"
            }
        }


class QuoteLineItem(BaseModel):
    """A single line item in the generated quote."""
    description: str = Field(..., description="Description of the charge (e.g., '2x Restroom Trailer Rental (3 days)', 'Delivery & Pickup', 'Generator Rental').")
    quantity: int = Field(default=1, description="Number of units for this line item.")
    unit_price: Optional[float] = Field(None, description="Price per unit, if applicable.")
    total_amount: float = Field(..., description="Total cost for this line item (quantity * unit_price or fixed amount).")

class PriceQuote(BaseModel):
    """The generated price quote details."""
    request_id: str = Field(..., description="Unique identifier echoed from the pricing request.")
    line_items: List[QuoteLineItem] = Field(..., description="Itemized list of costs.")
    subtotal: float = Field(..., description="Total cost before any taxes or fees not included.")
    applied_pricing_tier: Optional[str] = Field(None, description="Pricing tier applied (e.g., 'event_daily', 'construction_monthly').")
    notes: List[str] = Field(default_factory=list, description="Explanatory notes regarding the quote (e.g., 'Delivery calculated for Fort Collins', 'Includes weekly service', 'Generator required due to no site power').")
    is_estimate: bool = Field(default=False, description="Indicates if the quote is an estimate due to missing critical information (e.g., exact location, site conditions).")
    missing_info: List[str] = Field(default_factory=list, description="List of critical pieces of information missing that prevent a firm quote.")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "line_items": [
                    {"description": "2x Restroom Trailer Rental (3 days)", "quantity": 2, "unit_price": 1200.00, "total_amount": 2400.00},
                    {"description": "1x ADA Trailer Rental (3 days)", "quantity": 1, "unit_price": 1350.00, "total_amount": 1350.00},
                    {"description": "Delivery & Pickup (Local)", "quantity": 1, "total_amount": 150.00},
                    {"description": "Generator Rental (Small)", "quantity": 1, "unit_price": 75.00, "total_amount": 225.00}
                ],
                "subtotal": 4125.00,
                "applied_pricing_tier": "event_daily",
                "notes": [
                    "Delivery calculated for Fort Collins.",
                    "Generator required due to no site power.",
                    "Quote assumes level grass surface with adequate access."
                ],
                "is_estimate": False,
                "missing_info": []
            }
        }
