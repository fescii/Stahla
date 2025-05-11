# app/models/hubspot.py

from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal, Union # Added Union
from datetime import datetime # Added datetime import


class HubSpotBaseModel(BaseModel):
	"""Base model for HubSpot entities to handle extra fields gracefully."""

	class Config:
		extra = 'allow'  # Allow extra fields from HubSpot API responses


# --- HubSpot Error Models ---

class HubSpotErrorItem(BaseModel):
	"""Represents a single error item in a HubSpot API error response."""
	message: str
	in_param: Optional[str] = Field(None, alias="in")
	code: Optional[str] = None
	sub_category: Optional[str] = Field(None, alias="subCategory")
	context_details: Optional[Dict[str, Any]] = Field(None, alias="context") # Context specific to this error item

	class Config:
		populate_by_name = True
		extra = 'allow'

class HubSpotErrorDetail(HubSpotBaseModel):
	"""
	Model to parse detailed error responses from the HubSpot API.
	Inherits from HubSpotBaseModel to allow extra fields.
	"""
	status: Optional[str] = None # e.g., "error"
	message: str # Main error message from HubSpot
	correlation_id: Optional[str] = Field(None, alias="correlationId")
	category: Optional[str] = None # e.g., "VALIDATION_ERROR"
	sub_category: Optional[str] = Field(None, alias="subCategory") # If present at the top level of the error
	errors: Optional[List[HubSpotErrorItem]] = Field(None, description="A list of specific error details.")
	# General context for the error, e.g. {"objectType": ["DEAL"]}
	error_context: Optional[Dict[str, Any]] = Field(None, alias="context")
	links: Optional[Dict[str, HttpUrl]] = Field(None, description="Helpful links related to the error.")

	class Config:
		populate_by_name = True
		# extra = 'allow' is inherited from HubSpotBaseModel


# --- Contact Models ---

class HubSpotContactProperties(BaseModel):
	"""Properties for creating/updating a HubSpot contact based on properties.csv."""
	# Standard fields also listed in properties.csv
	firstname: Optional[str] = Field(None, alias="firstname")
	lastname: Optional[str] = Field(None, alias="lastname")
	phone: Optional[str] = Field(None, alias="phone") # Assuming string for Phone number
	email: Optional[EmailStr] = Field(None, alias="email") # Maps to contact_email from call
	city: Optional[str] = Field(None, alias="city")
	zip: Optional[str] = Field(None, alias="zip") # Postal code
	address: Optional[str] = Field(None, alias="address") # Street Address - Maps to service_address from call?
	state: Optional[str] = Field(None, alias="state") # Added - Maps to state from call
	message: Optional[str] = Field(None, alias="message") # General message field

	# Custom fields from properties.csv
	what_service_do_you_need_: Optional[str] = Field(None, alias="what_service_do_you_need_") # Maps to what_service_do_you_need_ from call metadata
	how_many_restroom_stalls_: Optional[int] = Field(None, alias="how_many_restroom_stalls_") # Number
	how_many_shower_stalls_: Optional[int] = Field(None, alias="how_many_shower_stalls_") # Number
	how_many_laundry_units_: Optional[int] = Field(None, alias="how_many_laundry_units_") # Number
	your_message: Optional[str] = Field(None, alias="your_message") # Multi-line text (separate from general message?)
	do_you_have_water_access_onsite_: Optional[str] = Field(None, alias="do_you_have_water_access_onsite_") # Maps to water_available from call (needs bool->str conversion?)
	do_you_have_power_access_onsite_: Optional[str] = Field(None, alias="do_you_have_power_access_onsite_") # Maps to power_available from call (needs bool->str conversion?)
	ada: Optional[bool] = Field(None, alias="ada") # Single Checkbox - Maps to ada_required from call
	how_many_portable_toilet_stalls_: Optional[int] = Field(None, alias="how_many_portable_toilet_stalls_") # Maps to how_many_portable_toilet_stalls_ from call metadata
	event_or_job_address: Optional[str] = Field(None, alias="event_or_job_address") # Maps to event_or_job_address from call metadata
	event_start_date: Optional[str] = Field(None, alias="event_start_date") # Maps to event_start_date from call metadata
	event_end_date: Optional[str] = Field(None, alias="event_end_date") # Maps to event_end_date from call metadata
	by_submitting_this_form_you_consent_to_receive_texts: Optional[bool] = Field(None, alias="by_submitting_this_form_you_consent_to_receive_texts") # Maps to by_submitting_this_form_you_consent_to_receive_texts from call metadata

	# AI/Call related properties from properties.csv (marked as Needs to be Created)
	ai_call_summary: Optional[str] = Field(None, alias="ai_call_summary") # Multi-line text
	ai_call_sentiment: Optional[str] = Field(None, alias="ai_call_sentiment") # Single line text
	call_recording_url: Optional[HttpUrl] = Field(None, alias="call_recording_url") # Single-line text (URL)
	call_summary: Optional[str] = Field(None, alias="call_summary") # Multi-line text
	# Added based on call.json variables (assuming these exist or will be created in HubSpot)
	contact_consent_given: Optional[bool] = Field(None, alias="contact_consent_given") # Maps to contact_consent_given from call

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
	project_category: Optional[str] = Field(None, alias="project_category") # Maps to project_category from call
	units_needed: Optional[str] = Field(None, alias="units_needed") # Maps to units_needed from call
	expected_attendance: Optional[int] = Field(None, alias="expected_attendance") # Maps to expected_attendance from call
	ada_required: Optional[bool] = Field(None, alias="ada_required") # Maps to ada_required from call
	additional_services_needed: Optional[str] = Field(None, alias="additional_services_needed") # Maps to additional_services_needed from call
	onsite_facilities: Optional[bool] = Field(None, alias="onsite_facilities")
	rental_start_date: Optional[str] = Field(None, alias="rental_start_date") # Maps to rental_start_date from call
	rental_end_date: Optional[str] = Field(None, alias="rental_end_date") # Maps to rental_end_date from call
	site_working_hours: Optional[str] = Field(None, alias="site_working_hours")
	weekend_service_needed: Optional[bool] = Field(None, alias="weekend_service_needed")
	cleaning_service_needed: Optional[bool] = Field(None, alias="cleaning_service_needed")
	onsite_contact_name: Optional[str] = Field(None, alias="onsite_contact_name")
	onsite_contact_phone: Optional[str] = Field(None, alias="onsite_contact_phone") # Phone number
	site_ground_type: Optional[str] = Field(None, alias="site_ground_type") # Maps to site_ground_type from call
	site_obstacles: Optional[str] = Field(None, alias="site_obstacles") # Maps to site_obstacles from call
	water_source_distance: Optional[int] = Field(None, alias="water_source_distance") # Maps to water_source_distance from call (needs str->int conversion?)
	power_source_distance: Optional[int] = Field(None, alias="power_source_distance") # Maps to power_source_distance from call (needs str->int conversion?)
	within_local_service_area: Optional[bool] = Field(None, alias="within_local_service_area") # Maps to is_in_service_area from call
	partner_referral_consent: Optional[bool] = Field(None, alias="partner_referral_consent") # Maps to referral_accepted from call
	needs_human_follow_up: Optional[bool] = Field(None, alias="needs_human_follow_up")
	quote_urgency: Optional[str] = Field(None, alias="quote_urgency") # Maps to quote_urgency from call

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
	# Added based on call.json variables (assuming these exist or will be created in HubSpot)
	decision_timeline: Optional[str] = Field(None, alias="decision_timeline") # Maps to decision_timing from call
	follow_up_call_scheduled: Optional[bool] = Field(None, alias="follow_up_call_scheduled") # Maps to follow_up_call_scheduled from call
	shower_required: Optional[bool] = Field(None, alias="shower_required") # Maps to shower_required from call
	handwashing_needed: Optional[bool] = Field(None, alias="handwashing_needed") # Maps to handwashing_needed from call
	address_type: Optional[str] = Field(None, alias="address_type") # Maps to address_type from call
	site_ground_level: Optional[bool] = Field(None, alias="site_ground_level") # Maps to site_ground_level from call
	power_path_cross: Optional[bool] = Field(None, alias="power_path_cross") # Maps to power_path_cross from call
	water_path_cross: Optional[bool] = Field(None, alias="water_path_cross") # Maps to water_path_cross from call

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
	name: Optional[str] = Field(None, alias="name") # Maps to company_name from call
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


# --- Deal Models ---

class HubSpotDealProperties(BaseModel):
	"""Properties for creating/updating a HubSpot deal."""
	dealname: Optional[str] = Field(None, alias="dealname")
	amount: Optional[float] = Field(None, alias="amount")
	dealstage: Optional[str] = Field(None, alias="dealstage")
	pipeline: Optional[str] = Field(None, alias="pipeline")
	closedate: Optional[str] = Field(None, alias="closedate") # HubSpot expects YYYY-MM-DD or timestamp
	hubspot_owner_id: Optional[str] = Field(None, alias="hubspot_owner_id")
	# Add other relevant deal properties

	model_config = {
		"populate_by_name": True
	}

class HubSpotDealInput(HubSpotBaseModel):
	"""Input model for creating/updating a deal via the API endpoint."""
	properties: HubSpotDealProperties


# --- Ticket Models ---

class HubSpotTicketProperties(BaseModel):
	"""Properties for creating/updating a HubSpot ticket."""
	subject: Optional[str] = Field(None, alias="subject")
	content: Optional[str] = Field(None, alias="content")
	hs_pipeline: Optional[str] = Field(None, alias="hs_pipeline")
	hs_pipeline_stage: Optional[str] = Field(None, alias="hs_pipeline_stage")
	hubspot_owner_id: Optional[str] = Field(None, alias="hubspot_owner_id")
	# Add other relevant ticket properties

	model_config = {
		"populate_by_name": True
	}

class HubSpotTicketInput(HubSpotBaseModel):
	"""Input model for creating/updating a ticket via the API endpoint."""
	properties: HubSpotTicketProperties


# --- Generic HubSpot Object Model ---

class HubSpotObject(HubSpotBaseModel):
	"""Generic model for HubSpot API objects, allowing any properties."""
	id: str
	properties: Dict[str, Any]
	created_at: Optional[datetime] = Field(None, alias="createdAt")
	updated_at: Optional[datetime] = Field(None, alias="updatedAt")
	archived: Optional[bool] = Field(None, alias="archived")
	# Associations might be present
	associations: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None


# --- Search Models ---

class HubSpotSearchFilter(BaseModel):
	propertyName: str
	operator: Literal[
		"EQ", "NEQ", "LT", "LTE", "GT", "GTE",
		"BETWEEN", "IN", "NOT_IN",
		"HAS_PROPERTY", "NOT_HAS_PROPERTY",
		"CONTAINS_TOKEN", "NOT_CONTAINS_TOKEN"
	]
	value: Optional[Any] = None
	values: Optional[List[Any]] = None
	highValue: Optional[Any] = None # For BETWEEN operator

class HubSpotSearchFilterGroup(BaseModel):
	filters: List[HubSpotSearchFilter]

class HubSpotSearchRequest(BaseModel):
	"""Model for HubSpot search API requests."""
	query: Optional[str] = None
	filterGroups: List[HubSpotSearchFilterGroup]
	sorts: Optional[List[Union[str, Dict[str, str]]]] = None # Can be simple strings or dicts like {"propertyName": "createdate", "direction": "DESCENDING"}
	properties: Optional[List[str]] = None
	limit: int = 10
	after: Optional[str] = None


class HubSpotSearchPagingNext(BaseModel):
	after: str
	link: Optional[str] = None

class HubSpotSearchPaging(BaseModel):
	next_val: Optional[HubSpotSearchPagingNext] = Field(None, alias="next")

class HubSpotSearchResponse(BaseModel):
	"""Model for HubSpot search API responses."""
	total: int
	results: List[HubSpotObject]
	paging: Optional[HubSpotSearchPaging] = None


# --- Pipeline & Stage Models ---

class HubSpotPipelineStage(HubSpotBaseModel):
	id: str
	label: str
	display_order: Optional[int] = Field(None, alias="displayOrder")
	metadata: Optional[Dict[str, Any]] = None

class HubSpotPipeline(HubSpotBaseModel):
	id: str
	label: str
	display_order: Optional[int] = Field(None, alias="displayOrder")
	stages: Optional[List[HubSpotPipelineStage]] = None


# --- Owner Models ---

class HubSpotOwner(HubSpotBaseModel):
	id: str
	email: Optional[EmailStr] = None
	first_name: Optional[str] = Field(None, alias="firstName")
	last_name: Optional[str] = Field(None, alias="lastName")
	user_id: Optional[int] = Field(None, alias="userId") # If applicable
	# active: Optional[bool] = None # Not always present in PublicOwner


# --- General Result Model ---

class HubSpotApiResult(BaseModel):
	"""Generic result structure for HubSpot operations."""
	status: str  # e.g., "success", "error", "updated", "created"
	entity_type: Optional[str] = None  # e.g., "contact", "lead" - Updated
	hubspot_id: Optional[str] = None
	message: Optional[str] = None
	details: Optional[Any] = None  # For detailed results or errors
