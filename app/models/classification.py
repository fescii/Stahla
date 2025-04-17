# app/models/classification_models.py

from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, Dict, Any, Literal, List

# Define the possible classification outcomes based on documentation
LeadClassificationType = Literal["Services", "Logistics", "Leads", "Disqualify"]

# Define the intended use categories
IntendedUseType = Literal["Small Event", "Large Event", "Construction", "Disaster Relief", "Facility"]

# Define product types
ProductType = Literal["Portable Toilet", "Handicap Accessible (ADA) Portable Toilet", "Handwashing Station", "Restroom Trailer", "Shower Trailer", "ADA Trailer"]


class ClassificationInput(BaseModel):
    """
    Input data for the classification engine.
    This model should encompass all relevant fields gathered from
    web forms, voice calls, and emails that are needed for classification.
    """
    # Metadata
    source: Literal["webform", "voice", "email"]
    raw_data: Dict[str, Any]  # The raw payload received
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Key information extracted from raw_data")
    
    # --- Classification Specific Fields ---
    intended_use: Optional[IntendedUseType] = Field(None, description="The primary purpose: Small Event, Large Event, Construction, Disaster Relief, or Facility")
    is_local: Optional[bool] = Field(None, description="Whether the location is local (≤3 hours from service hubs) or not")

    # --- Fields based on PRD & Call Script ---
    # Contact Info (often extracted)
    firstname: Optional[str] = Field(None, description="Prospect's first name")
    lastname: Optional[str] = Field(None, description="Prospect's last name")
    email: Optional[EmailStr] = Field(None, description="Prospect's email address")
    phone: Optional[str] = Field(None, description="Prospect's phone number")
    company: Optional[str] = Field(None, description="Prospect's company name")

    # Lead & Product Details
    product_interest: Optional[List[str]] = Field(default_factory=list, description="List of products prospect is interested in (e.g., ['Restroom Trailer', 'Porta Potty'])")
    lead_type_guess: Optional[str] = Field(None, description="Initial guess or statement about why they are contacting (e.g., 'Event', 'Construction')")
    required_stalls: Optional[int] = Field(None, description="Number of stalls or units needed")
    ada_required: Optional[bool] = Field(None, description="Is an ADA-compliant unit required?")

    # Event/Project Details
    event_type: Optional[str] = Field(None, description="Type of event or project (e.g., Wedding, Construction, Festival, Disaster Relief)")
    event_location_description: Optional[str] = Field(None, description="Delivery address or general location description")
    event_state: Optional[str] = Field(None, description="Two-letter state code where the event will take place (e.g., 'NY', 'NE')")
    event_city: Optional[str] = Field(None, description="City where the event will take place")
    event_postal_code: Optional[str] = Field(None, description="Postal/ZIP code of the event location")
    event_location_type: Optional[Literal["business", "residence", "other"]] = Field(None, description="Type of delivery location")
    delivery_surface: Optional[Literal["cement", "gravel", "dirt", "grass"]] = Field(None, description="Surface type at placement location")
    delivery_obstacles: Optional[str] = Field(None, description="Description of potential delivery obstacles (e.g., low trees)")
    duration_days: Optional[int] = Field(None, description="Duration of the rental in days")
    duration_hours_per_day: Optional[float] = Field(None, description="Estimated hours of usage per day (if multi-day)")
    start_date: Optional[str] = Field(None, description="Ideal delivery/start date") # Consider date type
    end_date: Optional[str] = Field(None, description="Ideal pickup/end date") # Consider date type
    guest_count: Optional[int] = Field(None, description="Estimated number of attendees/users")
    other_facilities_available: Optional[bool] = Field(None, description="Are other restroom facilities available on site?")
    onsite_contact_different: Optional[bool] = Field(None, description="Is the onsite contact different from the main contact?")
    working_hours: Optional[str] = Field(None, description="Working hours for construction sites")
    weekend_usage: Optional[bool] = Field(None, description="Will units be needed over the weekend (construction)?")

    # Site Requirements
    power_available: Optional[bool] = Field(None, description="Is power available on site?")
    power_distance_feet: Optional[int] = Field(None, description="Estimated distance to power source in feet")
    power_cord_ramps_needed: Optional[bool] = Field(None, description="Are cord ramps needed for power?")
    generator_needed: Optional[bool] = Field(None, description="Is a generator needed?")
    water_available: Optional[bool] = Field(None, description="Is water available on site (garden hose)?")
    water_distance_feet: Optional[int] = Field(None, description="Estimated distance to water source in feet")
    water_hose_ramps_needed: Optional[bool] = Field(None, description="Are hose ramps needed for water?")

    # Other
    budget_mentioned: Optional[str] = Field(None, description="Any budget information provided") # Use str for flexibility
    decision_timeline: Optional[str] = Field(None, description="When does the prospect plan to make a decision?")
    quote_needed_by: Optional[str] = Field(None, description="How soon is the quote needed?")
    other_products_needed: Optional[List[str]] = Field(default_factory=list, description="Other products needed (e.g., ['Tent', 'Generator'])")
    call_summary: Optional[str] = Field(None, description="Summary of the voice call, if applicable")
    call_recording_url: Optional[HttpUrl] = Field(None, description="URL to the call recording, if applicable")
    full_transcript: Optional[str] = Field(None, description="Full transcript of the voice call, if applicable")


    class Config:
        extra = 'allow'  # Allow extra fields not explicitly defined


class ClassificationOutput(BaseModel):
    """
    Output data from the classification engine.
    """
    lead_type: LeadClassificationType = Field(..., description="The determined classification category.")
    routing_suggestion: Optional[str] = Field(None,
                                              description="Suggested team or pipeline for routing (e.g., 'Services Sales', 'Logistics Ops').")
    confidence: Optional[float] = Field(None, description="Confidence score of the classification (0.0 to 1.0).")
    reasoning: Optional[str] = Field(None, description="Explanation or justification for the classification.")
    # Flag indicating if human review is recommended
    requires_human_review: bool = Field(False,
                                        description="Indicates if the classification is uncertain and needs human review.")
    # Any additional metadata generated during classification
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """Wrapper for the classification result, including status."""
    status: str  # e.g., "success", "error"
    classification: Optional[ClassificationOutput] = None
    message: Optional[str] = None  # For errors or additional info


"""
**Instructions:** Create a file named `classification_models.py` inside the `app/models/` directory and paste this code into it. You'll need to significantly customize `ClassificationInput` with the actual fields Stahla uses to classify learn
"""
