# app/models/hubspot_models.py

from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, Dict, Any, List


class HubSpotBaseModel(BaseModel):
	"""Base model for HubSpot entities to handle extra fields gracefully."""
	
	class Config:
		extra = 'allow'  # Allow extra fields from HubSpot API responses


# --- Contact Models ---

class HubSpotContactProperties(HubSpotBaseModel):
	"""Properties for creating or updating a HubSpot contact."""
	email: Optional[EmailStr] = None
	firstname: Optional[str] = None
	lastname: Optional[str] = None
	phone: Optional[str] = None
	# --- Stahla Custom Properties (Replace with actual internal names) ---
	stahla_lead_source: Optional[str] = Field(None, alias="stahla_lead_source", description="Source of the lead (e.g., Webform, Phone, Email)") # Example standard field
	stahla_lead_type: Optional[str] = Field(None, alias="stahla_lead_type", description="Classification result (Services, Logistics, Leads, Disqualify)")
	# Add other relevant contact properties if needed


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

class HubSpotDealProperties(HubSpotBaseModel):
	"""Properties for creating or updating a HubSpot deal."""
	dealname: Optional[str] = None
	pipeline: Optional[str] = None  # ID or name of the pipeline
	dealstage: Optional[str] = None  # ID or name of the stage
	amount: Optional[float] = None  # Deal amount (might be estimated initially)
	closedate: Optional[str] = None  # Deal close date (YYYY-MM-DD)
	# --- Stahla Custom Properties (Replace with actual internal names) ---
	stahla_product_interest: Optional[str] = Field(None, alias="stahla_product_interest", description="Product(s) interested in (comma-separated string or specific property)")
	stahla_event_location: Optional[str] = Field(None, alias="stahla_event_location", description="Delivery location details")
	stahla_duration: Optional[str] = Field(None, alias="stahla_duration", description="Rental duration (e.g., '3 days', '2 weeks')")
	stahla_stall_count: Optional[int] = Field(None, alias="stahla_stall_count", description="Number of stalls/units required")
	stahla_budget_info: Optional[str] = Field(None, alias="stahla_budget_info", description="Budget information provided by prospect")
	stahla_call_summary: Optional[str] = Field(None, alias="stahla_call_summary", description="Summary of the intake call")
	stahla_call_recording_url: Optional[HttpUrl] = Field(None, alias="stahla_call_recording_url", description="Link to the call recording")
	# Add other relevant deal properties (e.g., guest count, event type)
	stahla_guest_count: Optional[int] = Field(None, alias="stahla_guest_count")
	stahla_event_type: Optional[str] = Field(None, alias="stahla_event_type")


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
