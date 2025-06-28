# app/api/v1/endpoints/hubspot.py

import os
from datetime import datetime, timezone
from pathlib import Path as PathlibPath
from fastapi import APIRouter, Body, HTTPException, Path as FastAPIPath
from typing import List, Optional, Literal, Dict, Any
import logfire
from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationError

# Import models
from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotContactInput,
    HubSpotLeadProperties,
    HubSpotLeadInput,
    HubSpotApiResult,
    HubSpotContactResult,
    HubSpotLeadResult,
)

# Import common models
from app.models.common import GenericResponse
from app.services.hubspot import hubspot_manager
from app.services.hubspot.properties import PropertySyncManager
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
    # Call the manager method with proper input model
    contact_input = HubSpotContactInput(properties=contact_data)
    result: HubSpotApiResult = await hubspot_manager.create_or_update_contact(
        contact_input
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
    # Call the manager method for creating leads with proper input model
    lead_input = HubSpotLeadInput(properties=lead_data)
    result: HubSpotApiResult = await hubspot_manager.create_lead(lead_input)

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
    "/test/contact/form",
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
      "Received request for /test/contact/form with form data",
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

    # Attempt to create/update the contact in HubSpot with proper input model
    contact_input = HubSpotContactInput(properties=contact_props)
    result: HubSpotApiResult = await hubspot_manager.create_or_update_contact(
        contact_input
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


# Property Sync Endpoints
@router.post(
    "/properties/sync/all",
    response_model=GenericResponse,
    summary="Sync all properties to HubSpot",
    description="Sync all contact and lead properties from JSON files to HubSpot"
)
async def sync_all_properties():
  """
  Sync all properties from contact.json and lead.json to HubSpot.

  This endpoint will:
  - Load property definitions from both contact.json and lead.json
  - Check which properties already exist in HubSpot
  - Create any missing properties
  - Return a summary of the sync operation
  """
  try:
    logfire.info("Starting property sync for all object types")

    # Initialize property sync manager
    property_sync = PropertySyncManager(hubspot_manager)

    # Perform sync
    results = await property_sync.sync_all_properties()

    if results.get("status") == "error":
      return GenericResponse.error(
          message=results.get("error", "Property sync failed"),
          details=results
      )

    logfire.info(
        "Property sync completed successfully",
        summary=results.get("summary", {})
    )

    return GenericResponse(
        data=results
    )

  except Exception as e:
    logfire.exception("Unexpected error during property sync")
    return GenericResponse.error(
        message=f"Property sync failed: {str(e)}",
        status_code=500
    )


@router.post(
    "/properties/sync/contacts",
    response_model=GenericResponse,
    summary="Sync contact properties to HubSpot",
    description="Sync contact properties from contact.json to HubSpot"
)
async def sync_contact_properties():
  """
  Sync contact properties from contact.json to HubSpot.

  This endpoint will:
  - Load property definitions from contact.json
  - Check which properties already exist in HubSpot
  - Create any missing contact properties
  - Return a summary of the sync operation
  """
  try:
    logfire.info("Starting contact property sync")

    # Initialize property sync manager
    property_sync = PropertySyncManager(hubspot_manager)

    # Perform contact sync
    results = await property_sync.sync_contact_properties()

    if results.get("status") == "error":
      return GenericResponse.error(
          message=results.get("error", "Contact property sync failed"),
          details=results
      )

    logfire.info(
        "Contact property sync completed successfully",
        created=len(results.get("created", [])),
        existing=len(results.get("existing", [])),
        failed=len(results.get("failed", []))
    )

    return GenericResponse(
        data=results
    )

  except Exception as e:
    logfire.exception("Unexpected error during contact property sync")
    return GenericResponse.error(
        message=f"Contact property sync failed: {str(e)}",
        status_code=500
    )


@router.post(
    "/properties/sync/leads",
    response_model=GenericResponse,
    summary="Sync lead properties to HubSpot",
    description="Sync lead properties from lead.json to HubSpot"
)
async def sync_lead_properties():
  """
  Sync lead properties from lead.json to HubSpot.

  This endpoint will:
  - Load property definitions from lead.json
  - Check which properties already exist in HubSpot
  - Create any missing lead properties
  - Return a summary of the sync operation
  """
  try:
    logfire.info("Starting lead property sync")

    # Initialize property sync manager
    property_sync = PropertySyncManager(hubspot_manager)

    # Perform lead sync
    results = await property_sync.sync_lead_properties()

    if results.get("status") == "error":
      return GenericResponse.error(
          message=results.get("error", "Lead property sync failed"),
          details=results
      )

    logfire.info(
        "Lead property sync completed successfully",
        created=len(results.get("created", [])),
        existing=len(results.get("existing", [])),
        failed=len(results.get("failed", []))
    )

    return GenericResponse(
        data=results
    )

  except Exception as e:
    logfire.exception("Unexpected error during lead property sync")
    return GenericResponse.error(
        message=f"Lead property sync failed: {str(e)}",
        status_code=500
    )


@router.get(
    "/properties/status/{object_type}",
    response_model=GenericResponse,
    summary="Check property status",
    description="Check the status of specific properties in HubSpot"
)
async def check_property_status(
    object_type: Literal["contacts", "leads"] = FastAPIPath(
        ...,
        description="HubSpot object type to check properties for"
    ),
    property_names: Optional[str] = None
):
  """
  Check the status of specific properties in HubSpot.

  Args:
      object_type: The HubSpot object type (contacts or leads)
      property_names: Comma-separated list of property names to check (optional)

  If no property names are provided, all properties from the corresponding
  JSON file will be checked.
  """
  try:
    logfire.info(f"Checking property status for {object_type}")

    # Initialize property sync manager
    property_sync = PropertySyncManager(hubspot_manager)

    # Determine property names to check
    if property_names:
      names_to_check = [name.strip() for name in property_names.split(",")]
    else:
      # Load property names from JSON file
      filename = "contact.json" if object_type == "contacts" else "lead.json"
      properties_data = await property_sync._load_properties_from_file(filename)
      names_to_check = [prop["name"] for prop in properties_data]

    if not names_to_check:
      return GenericResponse.error(
          message="No properties to check",
          details={"object_type": object_type}
      )

    # Check property status
    results = await property_sync.check_property_status(object_type, names_to_check)

    # Calculate summary
    existing_count = sum(1 for prop in results.values() if prop.get("exists"))
    missing_count = len(results) - existing_count

    summary = {
        "object_type": object_type,
        "total_checked": len(results),
        "existing": existing_count,
        "missing": missing_count,
        "details": results
    }

    logfire.info(
        f"Property status check completed for {object_type}",
        total_checked=len(results),
        existing=existing_count,
        missing=missing_count
    )

    return GenericResponse(
        data=summary
    )

  except Exception as e:
    logfire.exception(
        f"Unexpected error during property status check for {object_type}")
    return GenericResponse.error(
        message=f"Property status check failed: {str(e)}",
        status_code=500
    )
