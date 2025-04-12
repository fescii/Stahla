# app/models/hubspot_models.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any


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
# Add other required/custom Stahla properties based on documentation
# e.g., lead_source: Optional[str] = None
# Make sure property names match the *internal* HubSpot property names
# Example custom property:
# stahla_lead_type: Optional[str] = Field(None, alias="stahla_lead_type")


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
	amount: Optional[float] = None  # Deal amount
	closedate: Optional[str] = None  # Deal close date (YYYY-MM-DD)
# Add other required/custom Stahla properties
# e.g., stahla_product_interest: Optional[str] = None
# e.g., stahla_event_location: Optional[str] = None
# e.g., stahla_stall_count: Optional[int] = None


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
	entity_type: str  # e.g., "contact", "deal"
	hubspot_id: Optional[str] = None
	message: Optional[str] = None
	details: Optional[Any] = None  # For detailed results or errors


"""
**Instructions:**
    Create a file named `hubspot_models.py` inside the `app/models/` directory and paste this code into it. You will need to customize the properties (`HubSpotContactProperties`, `HubSpotDealProperties`) to match the exact fields required by Stahla as per the project documentation
"""
