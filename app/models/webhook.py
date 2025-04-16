# app/models/webhook_models.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class FormPayload(BaseModel):
    """
    Pydantic model for data received from the web form webhook.
    Aligned with the ClassificationInput model fields for easier conversion.
    """
    # Basic contact info
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None # Optional company name

    # Lead details based on PRD/Script
    product_interest: Optional[str] = Field(None, description="Product(s) the prospect is interested in (e.g., Restroom Trailer, Porta Potty)")
    lead_type_guess: Optional[str] = Field(None, description="Initial guess about lead type based on form data")
    event_type: Optional[str] = Field(None, description="Type of event or project (e.g., Wedding, Construction)")
    event_location_description: Optional[str] = Field(None, description="Address or general location of the event/project")
    duration_days: Optional[int] = Field(None, description="Duration of the rental in days")
    start_date: Optional[str] = Field(None, description="Start/delivery date")
    end_date: Optional[str] = Field(None, description="End/pickup date")
    guest_count: Optional[int] = Field(None, description="Estimated number of attendees/users")
    required_stalls: Optional[int] = Field(None, description="Number of stalls or units needed")
    ada_required: Optional[bool] = Field(None, description="Whether ADA-compliant facilities are required")
    budget_mentioned: Optional[str] = Field(None, description="Any budget information provided")
    comments: Optional[str] = Field(None, description="Additional comments or questions from the prospect")
    
    # Site requirements
    power_available: Optional[bool] = Field(None, description="Is power available on site?")
    water_available: Optional[bool] = Field(None, description="Is water available on site?")
    other_facilities_available: Optional[bool] = Field(None, description="Are other restroom facilities available?")
    other_products_needed: Optional[List[str]] = Field(default_factory=list, description="Other products requested")

    # Metadata
    form_id: Optional[str] = Field(None, description="Identifier for the specific form submitted")
    submission_timestamp: Optional[str] = Field(None, description="Timestamp of form submission")

    class Config:
        extra = 'allow' # Allow any other fields submitted by the form
