# app/models/classification_models.py

from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, Dict, Any, Literal, List

# Define the possible classification outcomes based on documentation
LeadClassificationType = Literal["Services",
                                 "Logistics", "Leads", "Disqualify"]

# Define the intended use categories
IntendedUseType = Literal["Small Event", "Large Event",
                          "Construction", "Disaster Relief", "Facility"]

# Define product types
ProductType = Literal["Portable Toilet", "Handicap Accessible (ADA) Portable Toilet",
                      "Handwashing Station", "Restroom Trailer", "Shower Trailer"]


class ClassificationInput(BaseModel):
  """
  Input data for the classification engine.
  This model should encompass all relevant fields gathered from
  web forms, voice calls, and emails that are needed for classification.
  """
  # Metadata
  source: Literal["webform", "voice", "email"]
  raw_data: Dict[str, Any]  # The raw payload received
  extracted_data: Dict[str, Any] = Field(
      default_factory=dict, description="Key information extracted from raw_data")

  # --- Classification Specific Fields ---
  intended_use: Optional[IntendedUseType] = Field(
      None, description="The primary purpose: Small Event, Large Event, Construction, Disaster Relief, or Facility")
  is_local: Optional[bool] = Field(
      None, description="Whether the location is local (≤3 hours from service hubs) or not")
  # Added based on call.json variable
  is_in_service_area: Optional[bool] = Field(
      None, description="Whether the delivery address is within the defined service area.")

  # --- Fields based on PRD & Call Script (including call.json variables) ---
  # Contact Info (often extracted)
  firstname: Optional[str] = Field(
      None, description="Prospect's first name (from metadata)")
  lastname: Optional[str] = Field(
      None, description="Prospect's last name (from metadata)")
  email: Optional[EmailStr] = Field(
      None, description="Prospect's email address (from metadata)")
  phone: Optional[str] = Field(
      None, description="Prospect's phone number (from metadata)")
  company: Optional[str] = Field(
      None, description="Prospect's company name (from metadata)")
  # Added based on call.json variables
  contact_name: Optional[str] = Field(
      None, description="Verified or collected contact name during the call.")
  company_name: Optional[str] = Field(
      None, description="Verified or collected company name during the call.")
  contact_email: Optional[EmailStr] = Field(
      None, description="Verified or collected contact email during the call.")

  # Lead & Product Details
  product_interest: Optional[List[str]] = Field(
      default_factory=list, description="List of products prospect is interested in (e.g., ['Restroom Trailer', 'Porta Potty'])")
  # Added based on call.json variables
  what_service_do_you_need_: Optional[str] = Field(
      None, description="Initial service interest from metadata.")
  product_type_interest: Optional[str] = Field(
      None, description="Primary product type confirmed/collected during call.")
  units_needed: Optional[str] = Field(
      None, description="Number of units/stalls needed or expected attendance (as string).")
  how_many_portable_toilet_stalls_: Optional[int] = Field(
      None, description="Initial number of porta potty stalls from metadata.")
  # Keep existing for potential parsing
  required_stalls: Optional[int] = Field(
      None, description="Parsed number of stalls or units needed.")
  ada_required: Optional[bool] = Field(
      None, description="Is an ADA-compliant unit required?")
  # Added based on call.json variables
  shower_required: Optional[bool] = Field(
      None, description="Is a unit with a shower required?")
  handwashing_needed: Optional[bool] = Field(
      None, description="Are handwashing stations or sinks needed?")
  additional_services_needed: Optional[str] = Field(
      None, description="Other services mentioned (e.g., holding tanks, servicing).")

  # Event/Project Details
  event_type: Optional[str] = Field(
      None, description="Type of event or project (e.g., Wedding, Construction, Festival, Disaster Relief)")
  # Added based on call.json variables
  project_category: Optional[str] = Field(
      None, description="Category of use confirmed/collected during call (e.g., Construction, Special Event).")
  event_location_description: Optional[str] = Field(
      None, description="Delivery address or general location description (from metadata)")
  # Added based on call.json variables
  service_address: Optional[str] = Field(
      None, description="Full delivery address confirmed/collected during call.")
  event_state: Optional[str] = Field(
      None, description="Two-letter state code where the event will take place (e.g., 'NY', 'NE')")
  # Added based on call.json variables
  state: Optional[str] = Field(
      None, description="State extracted from service_address.")
  event_city: Optional[str] = Field(
      None, description="City where the event will take place")
  event_postal_code: Optional[str] = Field(
      None, description="Postal/ZIP code of the event location")
  # Added based on call.json variables
  address_type: Optional[str] = Field(
      None, description="Type of delivery location (e.g., residence, business, event venue).")
  event_location_type: Optional[Literal["business", "residence", "other"]] = Field(
      # Keep existing for potential mapping
      None, description="Type of delivery location")
  delivery_surface: Optional[Literal["cement", "gravel", "dirt", "grass"]] = Field(
      # Keep existing for potential mapping
      None, description="Surface type at placement location")
  # Added based on call.json variables
  site_ground_level: Optional[bool] = Field(
      None, description="Will the unit be placed on level ground?")
  site_ground_type: Optional[str] = Field(
      None, description="Surface type confirmed/collected during call (e.g., grass, gravel).")
  delivery_obstacles: Optional[str] = Field(
      None, description="Description of potential delivery obstacles (e.g., low trees)")
  # Added based on call.json variables
  site_obstacles: Optional[str] = Field(
      None, description="Obstacles confirmed/collected during call.")
  duration_days: Optional[int] = Field(
      None, description="Duration of the rental in days")
  duration_hours_per_day: Optional[float] = Field(
      None, description="Estimated hours of usage per day (if multi-day)")
  start_date: Optional[str] = Field(
      None, description="Ideal delivery/start date (from metadata)")
  end_date: Optional[str] = Field(
      None, description="Ideal pickup/end date (from metadata)")
  # Added based on call.json variables
  rental_start_date: Optional[str] = Field(
      None, description="Rental start date confirmed/collected during call.")
  rental_end_date: Optional[str] = Field(
      None, description="Rental end date confirmed/collected during call.")
  guest_count: Optional[int] = Field(
      None, description="Estimated number of attendees/users")
  # Added based on call.json variables
  expected_attendance: Optional[int] = Field(
      None, description="Expected attendance confirmed/collected during call.")
  other_facilities_available: Optional[bool] = Field(
      None, description="Are other restroom facilities available on site?")
  onsite_contact_different: Optional[bool] = Field(
      None, description="Is the onsite contact different from the main contact?")
  working_hours: Optional[str] = Field(
      None, description="Working hours for construction sites")
  weekend_usage: Optional[bool] = Field(
      None, description="Will units be needed over the weekend (construction)?")

  # Site Requirements
  power_available: Optional[bool] = Field(
      None, description="Is power available on site?")
  power_distance_feet: Optional[int] = Field(
      None, description="Estimated distance to power source in feet")
  # Added based on call.json variables
  power_source_distance: Optional[str] = Field(
      None, description="Distance to power source confirmed/collected during call (as string).")
  power_path_cross: Optional[bool] = Field(
      None, description="Does the power cord need to cross a path?")
  power_cord_ramps_needed: Optional[bool] = Field(
      None, description="Are cord ramps needed for power?")  # Keep existing
  generator_needed: Optional[bool] = Field(
      None, description="Is a generator needed?")  # Keep existing
  water_available: Optional[bool] = Field(
      None, description="Is water available on site (garden hose)?")
  water_distance_feet: Optional[int] = Field(
      None, description="Estimated distance to water source in feet")
  # Added based on call.json variables
  water_source_distance: Optional[str] = Field(
      None, description="Distance to water source confirmed/collected during call (as string).")
  water_path_cross: Optional[bool] = Field(
      None, description="Does the water hose need to cross a path?")
  water_hose_ramps_needed: Optional[bool] = Field(
      None, description="Are hose ramps needed for water?")  # Keep existing

  # Consent & Follow-up
  # Added based on call.json variables
  recording_consent_given: Optional[bool] = Field(
      None, description="Was consent given for recording (implicitly)?")
  contact_consent_given: Optional[bool] = Field(
      None, description="Was explicit consent given for contact/quote?")
  by_submitting_this_form_you_consent_to_receive_texts: Optional[bool] = Field(
      None, description="Consent to receive texts from metadata.")
  follow_up_call_scheduled: Optional[bool] = Field(
      None, description="Was a follow-up call requested/scheduled?")
  referral_accepted: Optional[bool] = Field(
      None, description="Did the user accept the offer for a referral (if OOS)?")

  # Other
  budget_mentioned: Optional[str] = Field(
      None, description="Any budget information provided")
  decision_timeline: Optional[str] = Field(
      None, description="When does the prospect plan to make a decision?")
  # Added based on call.json variables
  decision_timing: Optional[str] = Field(
      None, description="Decision timing confirmed/collected during call.")
  quote_needed_by: Optional[str] = Field(
      None, description="How soon is the quote needed?")
  # Added based on call.json variables
  quote_urgency: Optional[str] = Field(
      None, description="Quote urgency confirmed/collected during call.")
  other_products_needed: Optional[List[str]] = Field(
      default_factory=list, description="Other products needed (e.g., ['Tent', 'Generator'])")
  call_summary: Optional[str] = Field(
      None, description="Summary of the voice call, if applicable")
  call_recording_url: Optional[HttpUrl] = Field(
      None, description="URL to the call recording, if applicable")
  full_transcript: Optional[str] = Field(
      None, description="Full transcript of the voice call, if applicable")

  class Config:
    extra = 'allow'  # Allow extra fields not explicitly defined


class ClassificationOutput(BaseModel):
  """
  Output data from the classification engine.
  """
  lead_type: LeadClassificationType = Field(
      ..., description="The determined classification category.")
  routing_suggestion: Optional[str] = Field(None,
                                            description="Suggested team or pipeline for routing (e.g., 'Services Sales', 'Logistics Ops').")
  confidence: Optional[float] = Field(
      None, description="Confidence score of the classification (0.0 to 1.0).")
  reasoning: Optional[str] = Field(
      None, description="Explanation or justification for the classification.")
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


class ExtractedCallDetails(BaseModel):
  """Structured details extracted from a call summary/transcript by AI."""
  classification: LeadClassificationType = Field(
      ..., description="The overall classification: Services, Logistics, Leads, or Disqualify.")
  product_interest: Optional[List[str]] = Field(
      None, description="Specific products mentioned (e.g., 'Restroom Trailer', 'Porta Potty').")
  service_needed: Optional[str] = Field(
      # Added
      None, description="Specific service mentioned (e.g., 'rental', 'purchase', 'service only').")
  event_type: Optional[str] = Field(
      None, description="Type of event (e.g., 'Wedding', 'Construction', 'Festival').")
  location: Optional[str] = Field(
      None, description="Mentioned event location (full address if possible, otherwise general area).")
  city: Optional[str] = Field(None, description="Mentioned city.")  # Added
  state: Optional[str] = Field(
      # Added
      None, description="Mentioned state (2-letter code if possible).")
  postal_code: Optional[str] = Field(
      None, description="Mentioned postal/ZIP code.")  # Added
  start_date: Optional[str] = Field(
      None, description="Mentioned start date. MUST be formatted as YYYY-MM-DD.")
  end_date: Optional[str] = Field(
      None, description="Mentioned end date. MUST be formatted as YYYY-MM-DD.")
  duration_days: Optional[int] = Field(
      None, description="Mentioned duration in days.")
  guest_count: Optional[int] = Field(
      None, description="Mentioned number of guests or attendees.")
  required_stalls: Optional[int] = Field(
      None, description="Mentioned number of stalls or units needed.")
  ada_required: Optional[bool] = Field(
      None, description="Was an ADA requirement mentioned? (True/False)")
  budget_mentioned: Optional[str] = Field(
      None, description="Any mention of budget (extract amount like '$2500' or 'none').")
  power_available: Optional[bool] = Field(
      # Added
      None, description="Was power availability mentioned? (True/False)")
  water_available: Optional[bool] = Field(
      # Added
      None, description="Was water availability mentioned? (True/False)")
  comments: Optional[str] = Field(
      None, description="Any other specific comments, questions, or key details mentioned.")
  reasoning: Optional[str] = Field(
      None, description="Brief reasoning for the classification based on the rules.")
