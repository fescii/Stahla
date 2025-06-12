from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional, Literal, Union
import uuid
import re  # Import regex

# Helper function to parse numeric values from strings


def parse_numeric(value: Optional[Union[str, int, float]]) -> Optional[int]:
  if value is None:
    return None
  if isinstance(value, (int, float)):
    return int(value)
  if isinstance(value, str):
    # Extract numbers from string (e.g., "5 units", "100-200 feet")
    numbers = re.findall(r'\d+', value)
    if numbers:
      # Use the first number found
      return int(numbers[0])
  return None

# Helper function to parse boolean values from strings


def parse_boolean(value: Optional[Union[str, bool]]) -> Optional[bool]:
  if value is None:
    return None
  if isinstance(value, bool):
    return value
  if isinstance(value, str):
    lower_val = value.lower()
    if lower_val in ['true', 'yes', 'y', '1']:
      return True
    if lower_val in ['false', 'no', 'n', '0']:
      return False
    # Handle descriptive strings for obstacles
    if 'obstacle' in lower_val or 'narrow' in lower_val or 'tight' in lower_val or 'steep' in lower_val:
      return True  # Assume presence if described
  return None

# Helper function to parse list from string


def parse_list_from_string(value: Optional[Union[str, List[str]]]) -> List[str]:
  if value is None:
    return []
  if isinstance(value, list):
    return value
  if isinstance(value, str):
    # Simple split by comma, could be more sophisticated
    return [item.strip() for item in value.split(',') if item.strip()]
  return []


class PricingInput(BaseModel):
  """Inputs required to generate a price quote for Stahla rentals, gathered during the SDR interaction."""
  request_id: str = Field(default_factory=lambda: str(
      uuid.uuid4()), description="Unique identifier for this pricing request.")
  # Core Product/Service Details
  product_type: Optional[str] = Field(
      None, description="Primary product type requested (e.g., 'Restroom Trailer', 'Portable Toilet'). Derived from Slot: Product_Type.")
  num_units: Optional[int] = Field(
      None, description="Number of units or stalls requested. Derived from Slot: Units_Needed.")
  usage_type: Optional[Literal["event", "construction", "facility", "disaster_relief", "other"]] = Field(
      None, description="The intended use case for the rental. Derived from Slot: Customer_Type.")
  rental_duration_days: Optional[int] = Field(
      None, description="Total number of days the rental is needed. Derived from Slot: Duration.")
  start_date: Optional[str] = Field(
      None, description="Approximate start date (ISO 8601 format if possible). Derived from Slot: Start_Date.")
  event_total_hours: Optional[int] = Field(
      None, description="For multi-day events, the total estimated hours of active use. Relevant for service calculation.")

  # Location & Site Details (Mandatory for Quote)
  delivery_location_description: Optional[str] = Field(
      None, description="Delivery address or city/state. Derived from Slot: Location.")
  is_local: Optional[bool] = Field(
      None, description="Whether the location is considered 'local' based on proximity to hubs. Determined internally or from call script.")
  site_surface: Optional[Literal["cement", "gravel", "dirt", "grass", "asphalt", "concrete"]] = Field(
      None, description="Surface type at the placement location. Derived from Slot: Surface_Type.")
  ground_level: Optional[bool] = Field(
      None, description="Is the ground level/flat? Derived from Slot: Ground_Level.")
  obstacles_present: Optional[bool] = Field(
      None, description="Are there low branches or obstacles? Derived from Slot: Obstacles.")
  power_available: Optional[bool] = Field(
      None, description="Is adequate power available at the placement site? Derived from Slot: Power_Available.")
  water_available: Optional[bool] = Field(
      None, description="Is a water hookup (garden hose) available at the placement site? Derived from Slot: Water_Available.")
  power_distance_feet: Optional[int] = Field(
      None, description="Estimated distance to power source in feet. Derived from PAQ.")
  water_distance_feet: Optional[int] = Field(
      None, description="Estimated distance to water source in feet. Derived from PAQ.")

  # Specific Requirements
  requires_ada: Optional[bool] = Field(
      None, description="Does the request specifically require ADA-compliant units? Derived from Slot: ADA_Required.")
  requires_shower: Optional[bool] = Field(
      None, description="Are shower facilities required? Derived from Slot: Shower_Required.")
  requires_handwashing: Optional[bool] = Field(
      None, description="Are separate handwashing stations required? Derived from Slot: Handwashing_Needed.")
  requires_cleaning_service: Optional[bool] = Field(
      None, description="Is regular cleaning/restocking service requested? Derived from Subflow SB.")

  # Context & Intent
  attendee_count: Optional[int] = Field(
      None, description="Estimated number of attendees/users for capacity planning. Derived from Slot: Units_Needed clarification.")
  other_products_mentioned: List[str] = Field(
      default_factory=list, description="Other products mentioned (e.g., ['Tent', 'Generator']). Derived from Subflow SA/SB.")
  decision_timeline: Optional[str] = Field(
      None, description="When does the prospect plan to make a decision? Derived from Process PA/PB.")
  quote_needed_by: Optional[str] = Field(
      None, description="How soon is the quote needed? Derived from Process PA/PB.")
  call_summary: Optional[str] = Field(
      # From ClassificationInput
      None, description="Summary of the voice call, if applicable.")
  full_transcript: Optional[str] = Field(
      # From ClassificationInput
      None, description="Full transcript of the voice call, if applicable.")

  # --- Validators to handle potential string inputs from Bland ---
  @validator('num_units', 'rental_duration_days', 'event_total_hours', 'power_distance_feet', 'water_distance_feet', 'attendee_count', pre=True, always=True)
  def validate_numeric_fields(cls, v):
    return parse_numeric(v)

  @validator('is_local', 'ground_level', 'obstacles_present', 'power_available', 'water_available', 'requires_ada', 'requires_shower', 'requires_handwashing', 'requires_cleaning_service', pre=True, always=True)
  def validate_boolean_fields(cls, v):
    return parse_boolean(v)

  @validator('other_products_mentioned', pre=True, always=True)
  def validate_list_field(cls, v):
    return parse_list_from_string(v)

  @validator('usage_type', pre=True, always=True)
  def validate_usage_type(cls, v):
    if isinstance(v, str):
      v_lower = v.lower()
      if 'event' in v_lower:
        return 'event'
      if 'construction' in v_lower:
        return 'construction'
      if 'facility' in v_lower or 'building' in v_lower:
        return 'facility'
      if 'disaster' in v_lower or 'relief' in v_lower:
        return 'disaster_relief'
      if v_lower:
        return 'other'  # Default to other if not empty and not matched
    return None  # Return None if input is None or not a string

  @validator('site_surface', pre=True, always=True)
  def validate_site_surface(cls, v):
    if isinstance(v, str):
      v_lower = v.lower()
      if 'cement' in v_lower or 'concrete' in v_lower:
        return 'concrete'  # Consolidate
      if 'gravel' in v_lower:
        return 'gravel'
      if 'dirt' in v_lower:
        return 'dirt'
      if 'grass' in v_lower:
        return 'grass'
      if 'asphalt' in v_lower:
        return 'asphalt'
    return None  # Return None if input is None, not a string, or not matched

  class Config:
    extra = 'ignore'  # Ignore fields not defined here if passed from broader context
    json_schema_extra = {
        "example": {
            "request_id": "call_12345",
            "product_type": "Restroom Trailer",
            "num_units": "2 units",  # Example string input
            "usage_type": "Special Event",  # Example string input
            "rental_duration_days": "3",  # Example string input
            "start_date": "2025-08-15",
            "delivery_location_description": "Central Park, Fort Collins CO 80525",
            "is_local": "true",  # Example string input
            "site_surface": "Grass",  # Example string input
            "ground_level": "Yes",  # Example string input
            "obstacles_present": "No obstacles mentioned",  # Example string input
            "power_available": False,
            "water_available": True,
            "water_distance_feet": "75 feet",  # Example string input
            "requires_ada": "Yes",  # Example string input
            "attendee_count": "Around 500",  # Example string input
            "other_products_mentioned": "generator, fencing",  # Example string input
            "quote_needed_by": "End of week",
            "decision_timeline": "Next month"
        }
    }


class QuoteLineItem(BaseModel):
  """A single line item in the generated quote."""
  description: str = Field(..., description="Description of the charge (e.g., '2x Restroom Trailer Rental (3 days)', 'Delivery & Pickup', 'Generator Rental').")
  quantity: int = Field(
      default=1, description="Number of units for this line item.")
  unit_price: Optional[float] = Field(
      None, description="Price per unit, if applicable.")
  total_amount: float = Field(
      ..., description="Total cost for this line item (quantity * unit_price or fixed amount).")


class PriceQuote(BaseModel):
  """The generated price quote details."""
  request_id: str = Field(...,
                          description="Identifier linking back to the PricingInput request.")
  quote_id: str = Field(
      default_factory=lambda: f"QT-{uuid.uuid4()}", description="Unique identifier for this generated quote.")
  line_items: List[QuoteLineItem] = Field(
      default_factory=list, description="List of itemized charges.")
  total_amount: float = Field(..., description="The total estimated price.")
  currency: str = Field(default="USD", description="Currency code.")
  notes: Optional[str] = Field(
      None, description="Additional notes, disclaimers, or explanations about the quote.")
  is_estimate: bool = Field(
      default=True, description="Indicates if this is a preliminary estimate or a firm quote.")
  missing_info: List[str] = Field(
      default_factory=list, description="List of critical information missing that prevented a firm quote.")
  generated_at: str = Field(default_factory=lambda: datetime.now(
      timezone.utc).isoformat(), description="Timestamp when the quote was generated.")

  class Config:
    json_schema_extra = {
        "example": {
            "request_id": "call_12345",
            "quote_id": "QT-a1b2c3d4-e5f6-7890-1234-567890abcdef",
            "line_items": [
                {
                    "description": "2x Luxury Restroom Trailer Rental (3 days)",
                    "quantity": 2,
                    "unit_price": 1200.00,
                    "total_amount": 2400.00
                },
                {
                    "description": "Delivery & Pickup (Fort Collins Area)",
                    "quantity": 1,
                    "total_amount": 350.00
                },
                {
                    "description": "ADA Compliance Add-on",
                    "quantity": 1,
                    "total_amount": 150.00
                }
            ],
            "total_amount": 2900.00,
            "currency": "USD",
            "notes": "Quote is an estimate based on provided details. Final price may vary based on site inspection and final requirements. Includes standard servicing.",
            "is_estimate": True,
            "missing_info": ["Confirmation of power source type"],
            "generated_at": "2025-04-30T12:00:00Z"
        }
    }
