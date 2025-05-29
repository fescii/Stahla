# app/api/v1/endpoints/hubspot.py

import os
from datetime import datetime
from pathlib import Path as PathlibPath
from fastapi import APIRouter, Body, HTTPException, Path as FastAPIPath
from typing import List, Optional, Literal, Dict, Any
import logfire
from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationError

# Import models
from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotLeadProperties,
    HubSpotApiResult,
    HubSpotContactResult,
    HubSpotLeadResult,
    HubSpotLeadInput,
)

# Import common models
from app.models.common import GenericResponse
from app.services.hubspot import hubspot_manager
from app.utils.hubspot import to_hubspot_midnight_unix

router = APIRouter()


class SampleContactForm(BaseModel):
  what_service_do_you_need_: Optional[str] = Field(
      None, alias="What service do you need?"
  )

  @field_validator('what_service_do_you_need_')
  @classmethod
  def validate_service_type(cls, v):
    valid_services = [
        "Restroom Trailer",
        "Shower Trailer",
        "Laundry Trailer",
        "Porta Potty",
        "Trailer Repair / Pump Out",
        "Other"
    ]
    if v is not None and v not in valid_services:
      raise ValueError(
          f"Invalid service type. Must be one of: {', '.join(valid_services)}")
    return v
  how_many_portable_toilet_stalls_: Optional[int] = Field(
      None, alias="How Many Portable Toilet Stalls?"
  )
  event_or_job_address: Optional[str] = Field(
      None, alias="Event or Job Address")
  zip: Optional[str] = Field(None, alias="Postal code")
  city: Optional[str] = Field(None, alias="City")
  event_start_date: Optional[str] = Field(
      None, alias="Event start date"
  )  # Keep as string for now
  event_end_date: Optional[str] = Field(
      None, alias="Event end date"
  )  # Keep as string for now
  firstname: str = Field(..., alias="First name")
  lastname: str = Field(..., alias="Last name")
  phone: str = Field(..., alias="Phone number")
  email: EmailStr = Field(..., alias="Email")
  by_submitting_this_form_you_consent_to_receive_texts: Optional[bool] = Field(
      None, alias="I consent to receive texts on the phone number provided"
  )

  model_config = {
      "populate_by_name": True,
      "extra": "ignore",  # Ignore extra fields that might be in a real form submission
  }


@router.post(
    "/test/contact",
    response_model=GenericResponse[HubSpotApiResult],
    summary="Test HubSpot Contact Creation/Update",
    tags=["HubSpot Tests"],
)
async def test_hubspot_contact(contact_data: HubSpotContactProperties = Body(...)):
  """
  Test endpoint to create or update a HubSpot contact.
  Uses the same logic as the main webhook flow but is callable directly.
  """
  logfire.info("Received request for /test/contact",
               contact_email=contact_data.email)
  try:
    # Call the manager method which now returns HubSpotApiResult
    result: HubSpotApiResult = await hubspot_manager.create_or_update_contact(
        contact_data
    )

    if result.status == "error":
      logfire.error(
          "HubSpot contact test failed (service error).",
          details=result.details,
          message=result.message,
      )
      return GenericResponse.error(
          message=result.message or "Failed to create or update contact.",
          details=result.details,
      )

    logfire.info("HubSpot contact test successful.",
                 contact_id=result.hubspot_id)
    # Return the result wrapped in GenericResponse
    return GenericResponse(data=result)
  except Exception as e:
    logfire.exception("Unexpected error during HubSpot contact test.")
    return GenericResponse.error(
        message=f"An unexpected error occurred: {str(e)}", status_code=500
    )


# Renamed endpoint and updated logic for Leads
@router.post(
    "/test/lead",
    response_model=GenericResponse[HubSpotApiResult],
    summary="Test HubSpot Lead Creation",
    tags=["HubSpot Tests"],
)
async def test_hubspot_lead(
    lead_data: HubSpotLeadProperties = Body(...),
    contact_id: Optional[str] = Body(
        None, description="Optional HubSpot Contact ID to associate the lead with"
    ),
):
  """
  Test endpoint to create a HubSpot lead and optionally associate it with a contact.
  """
  logfire.info(
      "Received request for /test/lead",
      lead_properties=lead_data.model_dump(exclude_none=True),
      contact_id=contact_id,
  )  # Updated log
  try:
    # Call the manager method for creating leads
    lead_input = HubSpotLeadInput(properties=lead_data)  # Wrap lead_data
    # Removed contact_id
    result: HubSpotApiResult = await hubspot_manager.create_lead(lead_input.properties)

    if result.status == "error":
      logfire.error(
          "HubSpot lead test failed (service error).",
          details=result.details,
          message=result.message,
      )  # Updated log
      return GenericResponse.error(
          message=result.message or "Failed to create lead.",
          details=result.details,
      )

    logfire.info(
        "HubSpot lead test successful.", lead_id=result.hubspot_id
    )  # Updated log
    # Return the result wrapped in GenericResponse
    return GenericResponse(data=result)
  except Exception as e:
    logfire.exception(
        "Unexpected error during HubSpot lead test.")  # Updated log
    return GenericResponse.error(
        message=f"An unexpected error occurred: {str(e)}", status_code=500
    )


@router.get(
    "/test/owners",
    response_model=GenericResponse[List[dict]],
    summary="Test Fetching HubSpot Owners",
    tags=["HubSpot Tests"],
)
async def test_get_owners(email: Optional[str] = None):
  """
  Test endpoint to fetch owners from HubSpot.
  """
  logfire.info("Received request for /test/owners", email=email)
  try:
    owners = await hubspot_manager.get_owners(limit=10)
    logfire.info(
        f"HubSpot owners test successful. Found {len(owners)} owners.")
    return GenericResponse(data=owners)
  except Exception as e:
    logfire.exception("Unexpected error during HubSpot owners test.")
    return GenericResponse.error(
        message=f"An unexpected error occurred: {str(e)}", status_code=500
    )


# Modified endpoint to accept form data in request body
@router.post(
    "/test/contact",
    response_model=GenericResponse[HubSpotApiResult],
    summary="Create HubSpot Contact from Form Data",
    tags=["HubSpot Tests"],
)
async def create_contact_from_form_data(form_data: SampleContactForm = Body(...)):
  """
  Creates a HubSpot contact using data provided in the request body,
  validated against the SampleContactForm model.
  Useful for triggering the contact creation flow manually with specific data.
  """
  logfire.info(
      "Received request for /test/contact with form data",
      form_email=form_data.email,
      service_type=form_data.what_service_do_you_need_,
  )

  # Map validated form data to HubSpotContactProperties
  # Note: Field names in SampleContactForm match the aliases in HubSpotContactProperties where applicable
  hubspot_props_data = {
      "what_service_do_you_need_": form_data.what_service_do_you_need_,
      "how_many_portable_toilet_stalls_": form_data.how_many_portable_toilet_stalls_,
      "event_or_job_address": form_data.event_or_job_address,
      "zip": form_data.zip,
      "city": form_data.city,
      "event_start_date": to_hubspot_midnight_unix(form_data.event_start_date),
      "event_end_date": to_hubspot_midnight_unix(form_data.event_end_date),
      "firstname": form_data.firstname,
      "lastname": form_data.lastname,
      "phone": form_data.phone,
      "email": form_data.email,
      "by_submitting_this_form_you_consent_to_receive_texts": form_data.by_submitting_this_form_you_consent_to_receive_texts,
  }

  # Enhanced logging of the mapped properties before creating the model
  logfire.info("Mapped form data to HubSpot properties",
               mapped_properties=hubspot_props_data)

  try:
    # Filter out None values and create the model
    filtered_props = {k: v for k,
                      v in hubspot_props_data.items() if v is not None}
    logfire.info("Creating HubSpotContactProperties with filtered properties",
                 filtered_props=filtered_props)

    # Create the HubSpotContactProperties object
    contact_props = HubSpotContactProperties(**filtered_props)

    # Log the model after creation for verification
    logfire.info(
        "HubSpotContactProperties model created",
        model_properties=contact_props.model_dump(exclude_none=True),
        email=contact_props.email,
    )

    # Attempt to create/update the contact in HubSpot
    result: HubSpotApiResult = await hubspot_manager.create_or_update_contact(
        contact_props
    )

    if result.status == "error":
      logfire.error(
          "HubSpot contact creation from form data failed (service error).",
          details=result.details,
          message=result.message,
      )
      return GenericResponse.error(
          message=result.message
          or "Failed to create or update contact from form data.",
          details=result.details,
      )

    logfire.info(
        "HubSpot contact creation from form data successful.",
        contact_id=result.hubspot_id,
    )
    return GenericResponse(data=result)

  except Exception as e:
    logfire.exception(
        "Unexpected error during HubSpot contact creation from form data."
    )

    # Check for ValidationError from Pydantic models
    if isinstance(e, ValidationError):
      validation_errors = e.errors()
      logfire.error("Validation error in HubSpot contact form data",
                    validation_errors=validation_errors)
      return GenericResponse.error(
          message="Validation error in form data",
          details={"validation_errors": validation_errors},
          status_code=422
      )

    # Check for Hubspot API specific errors
    if "PROPERTY_DOESNT_EXIST" in str(e):
      import re
      property_match = re.search(r'Property "([^"]+)" does not exist', str(e))
      if property_match:
        invalid_property = property_match.group(1)
        return GenericResponse.error(
            message=f"HubSpot property validation error: '{invalid_property}' does not exist in HubSpot",
            details={"invalid_property": invalid_property},
            status_code=400
        )

    return GenericResponse.error(
        message=f"An unexpected error occurred: {str(e)}", status_code=500
    )


class PropertySyncRequest(BaseModel):
  sync_contacts: bool = Field(
      True, description="Whether to sync contact properties")
  sync_leads: bool = Field(True, description="Whether to sync lead properties")
  force_recreate: bool = Field(
      False, description="Force recreation of existing properties")


class PropertySyncResult(BaseModel):
  object_type: str
  created: List[Dict[str, Any]]
  existing: List[Dict[str, Any]]
  failed: List[Dict[str, Any]]
  total_processed: int


class PropertySyncResponse(BaseModel):
  success: bool
  message: str
  results: List[PropertySyncResult]
  total_created: int
  total_existing: int
  total_failed: int


@router.post(
    "/sync",
    response_model=GenericResponse[PropertySyncResponse],
    summary="Sync HubSpot Properties from JSON Files",
    tags=["HubSpot Properties"],
)
async def sync_hubspot_properties(sync_request: PropertySyncRequest = Body(...)):
  """
  Bulk sync HubSpot properties for contacts and leads from predefined JSON files.

  This endpoint loads property definitions from the JSON files in the info/ directory
  and creates them in HubSpot if they don't already exist.

  - **sync_contacts**: Enable/disable syncing contact properties
  - **sync_leads**: Enable/disable syncing lead properties  
  - **force_recreate**: Force recreation of existing properties (not implemented yet)
  """
  logfire.info("Starting HubSpot property sync",
               sync_request=sync_request.model_dump())

  if not hubspot_manager:
    raise HTTPException(
        status_code=500,
        detail="HubSpot manager not available"
    )

  results = []
  total_created = 0
  total_existing = 0
  total_failed = 0

  # Get the project root directory
  project_root = PathlibPath(__file__).parent.parent.parent.parent.parent
  info_dir = project_root / "info"

  try:
    # Sync contact properties
    if sync_request.sync_contacts:
      contact_json_path = info_dir / "contact_properties_payload.json"

      if not contact_json_path.exists():
        logfire.error(
            f"Contact properties JSON file not found: {contact_json_path}")
        results.append(PropertySyncResult(
            object_type="contacts",
            created=[],
            existing=[],
            failed=[{"error": f"JSON file not found: {contact_json_path}"}],
            total_processed=0
        ))
        total_failed += 1
      else:
        logfire.info(f"Syncing contact properties from {contact_json_path}")
        contact_result = await hubspot_manager.sync_properties_from_json(
            "contacts", str(contact_json_path)
        )

        results.append(PropertySyncResult(
            object_type="contacts",
            created=contact_result["created"],
            existing=contact_result["existing"],
            failed=contact_result["failed"],
            total_processed=len(contact_result["created"]) +
            len(contact_result["existing"]) +
            len(contact_result["failed"])
        ))

        total_created += len(contact_result["created"])
        total_existing += len(contact_result["existing"])
        total_failed += len(contact_result["failed"])

    # Sync lead properties
    if sync_request.sync_leads:
      lead_json_path = info_dir / "lead_properties_payload.json"

      if not lead_json_path.exists():
        logfire.error(f"Lead properties JSON file not found: {lead_json_path}")
        results.append(PropertySyncResult(
            object_type="leads",
            created=[],
            existing=[],
            failed=[{"error": f"JSON file not found: {lead_json_path}"}],
            total_processed=0
        ))
        total_failed += 1
      else:
        # Sync lead properties (will be mapped to contacts in HubSpot)
        logfire.info(
            f"Syncing lead properties from {lead_json_path} (will be mapped to contacts)")

        try:
          lead_result = await hubspot_manager.sync_properties_from_json(
              "leads", str(lead_json_path)
          )
        except Exception as e:
          logfire.error(f"Failed to sync lead properties: {str(e)}")
          lead_result = {
              "created": [],
              "existing": [],
              "failed": [{"error": f"Sync failed: {str(e)}"}]
          }

        results.append(PropertySyncResult(
            object_type="leads",
            created=lead_result["created"],
            existing=lead_result["existing"],
            failed=lead_result["failed"],
            total_processed=len(lead_result["created"]) +
            len(lead_result["existing"]) +
            len(lead_result["failed"])
        ))

        total_created += len(lead_result["created"])
        total_existing += len(lead_result["existing"])
        total_failed += len(lead_result["failed"])

    # Build response
    success = total_failed == 0
    message = f"Property sync completed. Created: {total_created}, Existing: {total_existing}, Failed: {total_failed}"

    if not success:
      message += f" (Some properties failed to sync)"

    sync_response = PropertySyncResponse(
        success=success,
        message=message,
        results=results,
        total_created=total_created,
        total_existing=total_existing,
        total_failed=total_failed
    )

    logfire.info("HubSpot property sync completed",
                 total_created=total_created,
                 total_existing=total_existing,
                 total_failed=total_failed)

    return GenericResponse(data=sync_response)

  except Exception as e:
    logfire.exception("Unexpected error during HubSpot property sync")
    raise HTTPException(
        status_code=500,
        detail=f"An unexpected error occurred during property sync: {str(e)}"
    )


@router.get(
    "/properties/{object_type}",
    response_model=GenericResponse[List[Dict[str, Any]]],
    summary="Get All Properties for Object Type",
    tags=["HubSpot Properties"],
)
async def get_hubspot_properties(
    object_type: str = FastAPIPath(...,
                                   description="Object type (contacts, leads, companies, etc.)")
):
  """
  Retrieve all properties for the specified HubSpot object type.

  This endpoint fetches all custom and standard properties from HubSpot
  for the given object type.
  """
  logfire.info(f"Fetching all properties for object type: {object_type}")

  if not hubspot_manager:
    raise HTTPException(
        status_code=500,
        detail="HubSpot manager not available"
    )

  try:
    properties = await hubspot_manager.get_all_properties(object_type)

    logfire.info(f"Retrieved {len(properties)} properties for {object_type}")

    return GenericResponse(data=properties)

  except Exception as e:
    logfire.exception(f"Error retrieving properties for {object_type}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to retrieve properties for {object_type}: {str(e)}"
    )


@router.get(
    "/properties/{object_type}/{property_name}",
    response_model=GenericResponse[Dict[str, Any]],
    summary="Get Specific Property Definition",
    tags=["HubSpot Properties"],
)
async def get_hubspot_property(
    object_type: str = FastAPIPath(...,
                                   description="Object type (contacts, leads, companies, etc.)"),
    property_name: str = FastAPIPath(...,
                                     description="Internal name of the property")
):
  """
  Retrieve a specific property definition from HubSpot.

  Returns the complete property definition including type, options, etc.
  """
  logfire.info(
      f"Fetching property '{property_name}' for object type: {object_type}")

  if not hubspot_manager:
    raise HTTPException(
        status_code=500,
        detail="HubSpot manager not available"
    )

  try:
    property_def = await hubspot_manager.get_property(object_type, property_name)

    if property_def is None:
      raise HTTPException(
          status_code=404,
          detail=f"Property '{property_name}' not found for object type '{object_type}'"
      )

    logfire.info(f"Retrieved property definition for '{property_name}'")

    return GenericResponse(data=property_def)

  except HTTPException:
    raise
  except Exception as e:
    logfire.exception(
        f"Error retrieving property '{property_name}' for {object_type}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to retrieve property '{property_name}' for {object_type}: {str(e)}"
    )
