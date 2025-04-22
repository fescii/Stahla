# app/models/hubspot.py

from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal


class HubSpotBaseModel(BaseModel):
  """Base model for HubSpot entities to handle extra fields gracefully."""

  class Config:
    extra = 'allow'  # Allow extra fields from HubSpot API responses


# --- Contact Models ---

class HubSpotContactProperties(BaseModel):
  """Properties for creating/updating a HubSpot contact based on properties.csv."""
  # Standard fields also listed in properties.csv
  firstname: Optional[str] = Field(None, alias="firstname")
  lastname: Optional[str] = Field(None, alias="lastname")
  phone: Optional[str] = Field(None, alias="phone") # Assuming string for Phone number
  email: Optional[EmailStr] = Field(None, alias="email")
  city: Optional[str] = Field(None, alias="city")
  zip: Optional[str] = Field(None, alias="zip") # Postal code
  address: Optional[str] = Field(None, alias="address") # Street Address
  message: Optional[str] = Field(None, alias="message") # General message field

  # Custom fields from properties.csv
  what_service_do_you_need_: Optional[str] = Field(None, alias="what_service_do_you_need_") # Multiple checkboxes, store as string
  how_many_restroom_stalls_: Optional[int] = Field(None, alias="how_many_restroom_stalls_") # Number
  how_many_shower_stalls_: Optional[int] = Field(None, alias="how_many_shower_stalls_") # Number
  how_many_laundry_units_: Optional[int] = Field(None, alias="how_many_laundry_units_") # Number
  your_message: Optional[str] = Field(None, alias="your_message") # Multi-line text (separate from general message?)
  do_you_have_water_access_onsite_: Optional[str] = Field(None, alias="do_you_have_water_access_onsite_") # Single-line text
  do_you_have_power_access_onsite_: Optional[str] = Field(None, alias="do_you_have_power_access_onsite_") # Single-line text
  ada: Optional[bool] = Field(None, alias="ada") # Single Checkbox
  how_many_portable_toilet_stalls_: Optional[int] = Field(None, alias="how_many_portable_toilet_stalls_") # Number
  event_or_job_address: Optional[str] = Field(None, alias="event_or_job_address") # Single-line text
  event_start_date: Optional[str] = Field(None, alias="event_start_date") # Date Picker, store as string
  event_end_date: Optional[str] = Field(None, alias="event_end_date") # Date Picker, store as string
  by_submitting_this_form_you_consent_to_receive_texts: Optional[bool] = Field(None, alias="by_submitting_this_form_you_consent_to_receive_texts") # Single checkbox

  # AI/Call related properties from properties.csv (marked as Needs to be Created)
  ai_call_summary: Optional[str] = Field(None, alias="ai_call_summary") # Multi-line text
  ai_call_sentiment: Optional[str] = Field(None, alias="ai_call_sentiment") # Single line text
  call_recording_url: Optional[HttpUrl] = Field(None, alias="call_recording_url") # Single-line text (URL)
  call_summary: Optional[str] = Field(None, alias="call_summary") # Multi-line text

  model_config = {
      "populate_by_name": True  # Allows using alias for HubSpot internal names
  }


class HubSpotContactInput(HubSpotBaseModel):
  """Input model for creating/updating a contact via the API endpoint."""
  properties: HubSpotContactProperties


class HubSpotContactResult(HubSpotBaseModel):
  """Model representing a simplified result after contact operation."""
  id: str
  properties: Dict[str, Any]  # Keep it flexible for now
  created_at: Optional[str] = Field(None, alias="createdAt")
  updated_at: Optional[str] = Field(None, alias="updatedAt")
  archived: Optional[bool] = None


# --- Lead Models ---

class HubSpotLeadProperties(BaseModel):
  """Properties for creating/updating a HubSpot lead based on properties.csv."""
  # Removed firstname, lastname, email, phone as they belong to Contact
  # Standard fields (if any applicable to Lead - check properties.csv)
  # Example: lead_status: Optional[str] = Field(None, alias=\"lead_status\") # If you have a status field

  # Custom fields from properties.csv for Lead object
  project_category: Optional[str] = Field(None, alias="project_category")
  units_needed: Optional[str] = Field(None, alias="units_needed")
  expected_attendance: Optional[int] = Field(None, alias="expected_attendance")
  ada_required: Optional[bool] = Field(None, alias="ada_required")
  additional_services_needed: Optional[str] = Field(None, alias="additional_services_needed")
  onsite_facilities: Optional[bool] = Field(None, alias="onsite_facilities")
  rental_start_date: Optional[str] = Field(None, alias="rental_start_date") # Date picker
  rental_end_date: Optional[str] = Field(None, alias="rental_end_date") # Date picker
  site_working_hours: Optional[str] = Field(None, alias="site_working_hours")
  weekend_service_needed: Optional[bool] = Field(None, alias="weekend_service_needed")
  cleaning_service_needed: Optional[bool] = Field(None, alias="cleaning_service_needed")
  onsite_contact_name: Optional[str] = Field(None, alias="onsite_contact_name")
  onsite_contact_phone: Optional[str] = Field(None, alias="onsite_contact_phone") # Phone number
  site_ground_type: Optional[str] = Field(None, alias="site_ground_type")
  site_obstacles: Optional[str] = Field(None, alias="site_obstacles")
  water_source_distance: Optional[int] = Field(None, alias="water_source_distance") # Number (ft)
  power_source_distance: Optional[int] = Field(None, alias="power_source_distance") # Number (ft)
  within_local_service_area: Optional[bool] = Field(None, alias="within_local_service_area")
  partner_referral_consent: Optional[bool] = Field(None, alias="partner_referral_consent")
  needs_human_follow_up: Optional[bool] = Field(None, alias="needs_human_follow_up")
  quote_urgency: Optional[str] = Field(None, alias="quote_urgency")

  # AI related properties from properties.csv (marked as Needs to be Created)
  ai_lead_type: Optional[str] = Field(None, alias="ai_lead_type")
  ai_classification_reasoning: Optional[str] = Field(None, alias="ai_classification_reasoning")
  ai_classification_confidence: Optional[float] = Field(None, alias="ai_classification_confidence") # Number (decimal)
  ai_routing_suggestion: Optional[str] = Field(None, alias="ai_routing_suggestion")
  ai_intended_use: Optional[str] = Field(None, alias="ai_intended_use")
  ai_qualification_notes: Optional[str] = Field(None, alias="ai_qualification_notes")
  number_of_stalls: Optional[int] = Field(None, alias="number_of_stalls") # Number (integer)
  event_duration_days: Optional[int] = Field(None, alias="event_duration_days") # Number (integer)
  guest_count_estimate: Optional[int] = Field(None, alias="guest_count_estimate") # Number (integer)
  ai_estimated_value: Optional[float] = Field(None, alias="ai_estimated_value") # Number (currency)

  model_config = {
      "populate_by_name": True  # Allows using alias for HubSpot internal names
  }


class HubSpotLeadInput(HubSpotBaseModel):
  """Input model for creating/updating a lead via the API endpoint."""
  properties: HubSpotLeadProperties
  # Associations might be needed to link Lead to Contact
  # associations: Optional[List[Dict[str, Any]]] = None


class HubSpotLeadResult(HubSpotBaseModel):
  """Model representing a simplified result after lead operation."""
  id: str
  properties: Dict[str, Any]  # Keep it flexible
  created_at: Optional[str] = Field(None, alias="createdAt")
  updated_at: Optional[str] = Field(None, alias="updatedAt")
  archived: Optional[bool] = None


# --- Company Models ---

class HubSpotCompanyProperties(BaseModel):
    """Properties for creating/updating a HubSpot company."""
    domain: Optional[str] = Field(None, alias="domain")
    name: Optional[str] = Field(None, alias="name")
    # Add other relevant company properties if needed, e.g.:
    # website: Optional[HttpUrl] = Field(None, alias="website")
    # phone: Optional[str] = Field(None, alias="phone")
    # city: Optional[str] = Field(None, alias="city")
    # state: Optional[str] = Field(None, alias="state")
    # zip: Optional[str] = Field(None, alias="zip")
    # address: Optional[str] = Field(None, alias="address")

    model_config = {
        "populate_by_name": True
    }


class HubSpotCompanyInput(HubSpotBaseModel):
    """Input model for creating/updating a company via the API endpoint."""
    properties: HubSpotCompanyProperties


# --- General Result Model ---

class HubSpotApiResult(BaseModel):
  """Generic result structure for HubSpot operations."""
  status: str  # e.g., "success", "error", "updated", "created"
  entity_type: Optional[str] = None  # e.g., "contact", "lead" - Updated
  hubspot_id: Optional[str] = None
  message: Optional[str] = None
  details: Optional[Any] = None  # For detailed results or errors
