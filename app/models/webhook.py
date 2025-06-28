# app/models/webhook_models.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone


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


# --- HubSpot Models for Direct Contact Data Payload ---

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
  Pydantic model for the direct contact data payload received from HubSpot webhooks.
  """
  # Contact identifiers
  contact_id: Optional[int] = None

  # Basic contact info
  firstname: Optional[str] = None
  lastname: Optional[str] = None
  email: Optional[EmailStr] = None
  phone: Optional[int] = None

  # Location information
  zip: Optional[int] = None
  city: Optional[str] = None
  event_or_job_address: Optional[str] = None

  # Event details
  event_start_date: Optional[int] = None  # Timestamp in milliseconds
  event_end_date: Optional[int] = None    # Timestamp in milliseconds
  message: Optional[str] = None

  # Service details
  what_service_do_you_need_: Optional[str] = None
  how_many_portable_toilet_stalls_: Optional[int] = None

  # Consent
  by_submitting_this_form_you_consent_to_receive_texts: Optional[bool] = None

  class Config:
    extra = 'allow'  # Allow fields not explicitly defined
    populate_by_name = True  # Allow using aliases

  def convert_to_form_payload(self) -> FormPayload:
    """
    Converts HubSpot contact data to the internal FormPayload model
    """
    # Convert millisecond timestamps to dates if present
    start_date = None
    end_date = None
    if self.event_start_date:
      start_date = datetime.fromtimestamp(
          self.event_start_date / 1000).strftime('%Y-%m-%d')
    if self.event_end_date:
      end_date = datetime.fromtimestamp(
          self.event_end_date / 1000).strftime('%Y-%m-%d')

    return FormPayload(
        firstname=self.firstname,
        lastname=self.lastname,
        email=self.email,
        phone=str(self.phone) if self.phone else None,
        company=None,
        product_interest=self.what_service_do_you_need_,
        lead_type_guess=None,
        event_type=None,
        event_location_description=self.event_or_job_address,
        event_state=None,
        event_city=self.city,
        event_postal_code=str(self.zip) if self.zip else None,
        duration_days=None,
        start_date=start_date,
        end_date=end_date,
        guest_count=None,
        required_stalls=self.how_many_portable_toilet_stalls_,
        ada_required=None,
        budget_mentioned=None,
        comments=self.message,
        power_available=None,
        water_available=None,
        other_facilities_available=None,
        other_products_needed=[],
        form_id=None,
        submission_timestamp=None
    )
