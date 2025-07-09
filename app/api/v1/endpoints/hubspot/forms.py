# app/api/v1/endpoints/hubspot/forms.py

from fastapi import APIRouter, Body, Depends
from typing import Optional
import logfire
import re
from pydantic import ValidationError

from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotContactInput,
    HubSpotApiResult,
)
from app.models.common import GenericResponse
from app.models.user import User
from app.core.security import get_current_user
from app.services.hubspot import hubspot_manager
from app.utils.hubspot import to_hubspot_midnight_unix
from .models import SampleContactForm

router = APIRouter(prefix="/forms", tags=["hubspot-forms"])


@router.post(
    "/contact",
    response_model=GenericResponse[HubSpotApiResult],
    summary="Create HubSpot Contact from Form Data",
)
async def create_contact_from_form_data(
    form_data: SampleContactForm = Body(...),
    current_user: User = Depends(get_current_user)
):
  """
  Creates a HubSpot contact using data provided in the request body,
  validated against the SampleContactForm model.
  Useful for triggering the contact creation flow manually with specific data.
  """
  logfire.info(
      "Received request for form contact creation",
      form_email=form_data.email,
      service_type=form_data.what_service_do_you_need_,
  )

  # Map validated form data to HubSpotContactProperties
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
