# app/models/webhook_models.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict


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
  company: Optional[str] = None  # Optional company name

  # Lead details based on PRD/Script
  product_interest: Optional[str] = Field(
      None, description="Product(s) the prospect is interested in (e.g., Restroom Trailer, Porta Potty)")
  lead_type_guess: Optional[str] = Field(
      None, description="Initial guess about lead type based on form data")
  event_type: Optional[str] = Field(
      None, description="Type of event or project (e.g., Wedding, Construction)")

  # Location information
  event_location_description: Optional[str] = Field(
      None, description="Address or general location of the event/project")
  event_state: Optional[str] = Field(
      None, description="Two-letter state code where the event will take place (e.g., 'NY', 'NE')")
  event_city: Optional[str] = Field(
      None, description="City where the event will take place")
  event_postal_code: Optional[str] = Field(
      None, description="Postal/ZIP code of the event location")

  # Event details
  duration_days: Optional[int] = Field(
      None, description="Duration of the rental in days")
  start_date: Optional[str] = Field(None, description="Start/delivery date")
  end_date: Optional[str] = Field(None, description="End/pickup date")
  guest_count: Optional[int] = Field(
      None, description="Estimated number of attendees/users")
  required_stalls: Optional[int] = Field(
      None, description="Number of stalls or units needed")
  ada_required: Optional[bool] = Field(
      None, description="Whether ADA-compliant facilities are required")
  budget_mentioned: Optional[str] = Field(
      None, description="Any budget information provided")
  comments: Optional[str] = Field(
      None, description="Additional comments or questions from the prospect")

  # Site requirements
  power_available: Optional[bool] = Field(
      None, description="Is power available on site?")
  water_available: Optional[bool] = Field(
      None, description="Is water available on site?")
  other_facilities_available: Optional[bool] = Field(
      None, description="Are other restroom facilities available?")
  other_products_needed: Optional[List[str]] = Field(
      default_factory=list, description="Other products requested")

  # Metadata
  form_id: Optional[str] = Field(
      None, description="Identifier for the specific form submitted")
  submission_timestamp: Optional[str] = Field(
      None, description="Timestamp of form submission")

  class Config:
    extra = 'allow'  # Allow any other fields submitted by the form


class HubSpotWebhookEvent(BaseModel):
  objectId: int
  propertyName: Optional[str] = None  # e.g., 'dealstage'
  propertyValue: Optional[str] = None  # e.g., 'appointmentscheduled'
  changeSource: Optional[str] = None  # e.g., 'CRM'
  eventId: int
  subscriptionId: int
  portalId: int
  appId: Optional[int] = None
  occurredAt: int  # Timestamp (milliseconds)
  subscriptionType: str  # e.g., 'deal.creation', 'deal.propertyChange'
  attemptNumber: int


class HubSpotWebhookPayload(BaseModel):
  # HubSpot sends a list - This model remains for potential future use
  # with standard event webhooks, but is not used by the endpoint anymore.
  events: List[HubSpotWebhookEvent]

  model_config = {
      "populate_by_name": True
  }


# --- New Models for Direct Contact Data Payload ---

class HubSpotPropertyVersion(BaseModel):
  value: Any
  source_type: Optional[str] = Field(None, alias='source-type')
  source_id: Optional[str] = Field(None, alias='source-id')
  source_label: Optional[str] = Field(None, alias='source-label')
  timestamp: int
  # Add other potential fields if needed, allowing extras
  class Config:
      extra = 'allow'
      populate_by_name = True


class HubSpotPropertyDetail(BaseModel):
  value: Any
  versions: List[HubSpotPropertyVersion]
  class Config:
      extra = 'allow'


class HubSpotIdentity(BaseModel):
  type: str
  value: str
  timestamp: int
  is_primary: Optional[bool] = Field(None, alias='is-primary')
  source: Optional[str] = None
  class Config:
      extra = 'allow'
      populate_by_name = True


class HubSpotIdentityProfile(BaseModel):
  vid: int
  identities: List[HubSpotIdentity]
  # Add other potential fields if needed, allowing extras
  class Config:
      extra = 'allow'


class HubSpotAssociatedCompanyPropertyDetail(BaseModel):
    value: Any
    # Simplified for now, assuming we only need the value
    class Config:
        extra = 'allow'

class HubSpotAssociatedCompany(BaseModel):
    company_id: int = Field(..., alias='company-id')
    portal_id: int = Field(..., alias='portal-id')
    properties: Dict[str, HubSpotAssociatedCompanyPropertyDetail]
    class Config:
        extra = 'allow'
        populate_by_name = True


class HubSpotContactDataPayload(BaseModel):
  """
  Pydantic model for the direct contact data payload received.
  """
  vid: int
  canonical_vid: int = Field(..., alias='canonical-vid')
  merged_vids: List[int] = Field(..., alias='merged-vids')
  portal_id: int = Field(..., alias='portal-id')
  is_contact: bool = Field(..., alias='is-contact')
  properties: Dict[str, Optional[HubSpotPropertyDetail]] # Make detail optional as some props might be null
  form_submissions: List[Any] = Field(..., alias='form-submissions')
  list_memberships: List[Any] = Field(..., alias='list-memberships')
  identity_profiles: List[HubSpotIdentityProfile] = Field(..., alias='identity-profiles')
  merge_audits: List[Any] = Field(..., alias='merge-audits')
  associated_company: Optional[HubSpotAssociatedCompany] = Field(None, alias='associated-company')

  class Config:
    extra = 'allow' # Allow fields not explicitly defined
    populate_by_name = True # Allow using aliases like 'portal-id'
