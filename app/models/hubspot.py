# app/models/hubspot_models.py

from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal


class HubSpotBaseModel(BaseModel):
  """Base model for HubSpot entities to handle extra fields gracefully."""

  class Config:
    extra = 'allow'  # Allow extra fields from HubSpot API responses


# --- Contact Models ---

class HubSpotContactProperties(BaseModel):
  """Properties for creating/updating a HubSpot contact."""
  email: Optional[EmailStr] = None
  firstname: Optional[str] = None
  lastname: Optional[str] = None
  phone: Optional[str] = None
  company: Optional[str] = None
  city: Optional[str] = None
  zip: Optional[str] = None  # Postal Code
  event_or_job_address: Optional[str] = None  # Custom Address field
  message: Optional[str] = None  # Message from form/email

  # Custom properties (confirm internal names with Kevin)
  stahla_service_needed: Optional[str] = Field(
      None, alias="stahla_service_needed")
  stahla_event_start_date: Optional[str] = Field(
      # Consider date type if HubSpot supports
      None, alias="stahla_event_start_date")
  stahla_event_end_date: Optional[str] = Field(
      None, alias="stahla_event_end_date")  # Consider date type if HubSpot supports
  stahla_text_consent: Optional[bool] = Field(
      None, alias="stahla_text_consent")
  how_many_portable_toilet_stalls_: Optional[int] = Field(
      None, alias="how_many_portable_toilet_stalls_")
  # Add other stall count properties if needed
  # how_many_restroom_stalls_: Optional[int] = Field(None, alias="how_many_restroom_stalls_")
  # how_many_shower_stalls_: Optional[int] = Field(None, alias="how_many_shower_stalls_")
  # ... etc

  # Properties set by our system (optional on create/update)
  stahla_lead_source: Optional[str] = Field(None, alias="stahla_lead_source")
  stahla_lead_type: Optional[str] = Field(
      None, alias="stahla_lead_type")  # Set from classification

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


# --- Deal Models ---

class HubSpotDealProperties(BaseModel):
  """Properties for creating/updating a HubSpot deal."""
  dealname: Optional[str] = None
  pipeline: Optional[str] = None
  dealstage: Optional[str] = None
  # Standard amount - use with caution per call script
  amount: Optional[float] = None
  closedate: Optional[str] = None  # Consider date type
  hubspot_owner_id: Optional[str] = None
  dealtype: Optional[Literal["newbusiness", "existingbusiness"]] = None

  # Standard properties often copied from Contact or set by system
  # Copied from stahla_event_start_date
  start_date: Optional[str] = Field(None, alias="start_date")
  # Copied from stahla_event_end_date
  end_date: Optional[str] = Field(None, alias="end_date")
  # Copied from event_or_job_address
  deal_address: Optional[str] = Field(None, alias="deal_address")

  # Custom properties for classification results & call details
  stahla_lead_source: Optional[str] = Field(
      None, alias="stahla_lead_source")  # Added for consistency
  stahla_ai_lead_type: Optional[str] = Field(None, alias="stahla_ai_lead_type")
  stahla_ai_reasoning: Optional[str] = Field(None, alias="stahla_ai_reasoning")
  stahla_ai_confidence: Optional[float] = Field(
      None, alias="stahla_ai_confidence")
  stahla_ai_routing_suggestion: Optional[str] = Field(
      None, alias="stahla_ai_routing_suggestion")
  stahla_ai_requires_review: Optional[bool] = Field(
      None, alias="stahla_ai_requires_review")
  stahla_ai_is_local: Optional[bool] = Field(None, alias="stahla_ai_is_local")
  stahla_ai_intended_use: Optional[str] = Field(
      None, alias="stahla_ai_intended_use")
  stahla_ai_qualification_notes: Optional[str] = Field(
      None, alias="stahla_ai_qualification_notes")
  stahla_call_recording_url: Optional[str] = Field(
      None, alias="stahla_call_recording_url")  # Store as string URL
  stahla_call_summary: Optional[str] = Field(None, alias="stahla_call_summary")
  stahla_call_duration_seconds: Optional[int] = Field(
      None, alias="stahla_call_duration_seconds")
  stahla_stall_count: Optional[int] = Field(None, alias="stahla_stall_count")
  stahla_event_duration_days: Optional[int] = Field(
      None, alias="stahla_event_duration_days")
  stahla_guest_count: Optional[int] = Field(None, alias="stahla_guest_count")
  stahla_ada_required: Optional[bool] = Field(
      None, alias="stahla_ada_required")
  stahla_power_available: Optional[bool] = Field(
      None, alias="stahla_power_available")
  stahla_water_available: Optional[bool] = Field(
      None, alias="stahla_water_available")
  stahla_ai_estimated_value: Optional[float] = Field(
      # Optional custom field for AI estimate
      None, alias="stahla_ai_estimated_value")

  # Custom properties potentially copied from Contact
  stahla_service_needed: Optional[str] = Field(
      None, alias="stahla_service_needed")
  stahla_event_location: Optional[str] = Field(
      None, alias="stahla_event_location")  # If needed on deal
  stahla_event_type: Optional[str] = Field(
      None, alias="stahla_event_type")  # If needed on deal

  model_config = {
      "populate_by_name": True  # Allows using alias for HubSpot internal names
  }


class HubSpotDealInput(HubSpotBaseModel):
  """Input model for creating/updating a deal via the API endpoint."""
  properties: HubSpotDealProperties
# Associations allow linking the deal to contacts, companies, etc.
# Example: Link to a contact by ID
# associations: Optional[List[Dict[str, Any]]] = None
# e.g., associations = [{"to": {"id": "contact_id"}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]}]


class HubSpotDealResult(HubSpotBaseModel):
  """Model representing a simplified result after deal operation."""
  id: str
  properties: Dict[str, Any]  # Keep it flexible
  created_at: Optional[str] = Field(None, alias="createdAt")
  updated_at: Optional[str] = Field(None, alias="updatedAt")
  archived: Optional[bool] = None


# --- General Result Model ---

class HubSpotApiResult(BaseModel):
  """Generic result structure for HubSpot operations."""
  status: str  # e.g., "success", "error", "updated", "created"
  entity_type: Optional[str] = None  # e.g., "contact", "deal" - Made optional
  hubspot_id: Optional[str] = None
  message: Optional[str] = None
  details: Optional[Any] = None  # For detailed results or errors
