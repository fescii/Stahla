# app/api/v1/endpoints/hubspot/operations.py

from fastapi import APIRouter, Body, Depends
from typing import List, Optional
import logfire

from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotContactInput,
    HubSpotLeadProperties,
    HubSpotLeadInput,
    HubSpotApiResult,
)
from app.models.common import GenericResponse
from app.models.user import User
from app.core.security import get_current_user
from app.services.hubspot import hubspot_manager

router = APIRouter(prefix="/operations", tags=["hubspot-operations"])


@router.post(
    "/contact",
    response_model=GenericResponse[HubSpotApiResult],
    summary="Create or Update HubSpot Contact",
)
async def create_or_update_contact(
    contact_data: HubSpotContactProperties = Body(...),
    current_user: User = Depends(get_current_user)
):
  """
  Create or update a HubSpot contact.
  Uses the same logic as the main webhook flow but is callable directly.
  """
  logfire.info("Received request for contact creation/update",
               contact_email=contact_data.email)
  try:
    # Call the manager method with proper input model
    contact_input = HubSpotContactInput(properties=contact_data)
    result: HubSpotApiResult = await hubspot_manager.create_or_update_contact(
        contact_input
    )

    if result.status == "error":
      logfire.error(
          "HubSpot contact operation failed (service error).",
          details=result.details,
          message=result.message,
      )
      return GenericResponse.error(
          message=result.message or "Failed to create or update contact.",
          details=result.details,
      )

    logfire.info("HubSpot contact operation successful.",
                 contact_id=result.hubspot_id)
    return GenericResponse(data=result)
  except Exception as e:
    logfire.exception("Unexpected error during HubSpot contact operation.")
    return GenericResponse.error(
        message=f"An unexpected error occurred: {str(e)}", status_code=500
    )


@router.post(
    "/lead",
    response_model=GenericResponse[HubSpotApiResult],
    summary="Create HubSpot Lead",
)
async def create_lead(
    lead_data: HubSpotLeadProperties = Body(...),
    contact_id: Optional[str] = Body(
        None, description="Optional HubSpot Contact ID to associate the lead with"
    ),
    current_user: User = Depends(get_current_user)
):
  """
  Create a HubSpot lead and optionally associate it with a contact.
  """
  logfire.info(
      "Received request for lead creation",
      lead_properties=lead_data.model_dump(exclude_none=True),
      contact_id=contact_id,
  )
  try:
    # Call the manager method for creating leads with proper input model
    lead_input = HubSpotLeadInput(properties=lead_data)
    result: HubSpotApiResult = await hubspot_manager.create_lead(lead_input)

    if result.status == "error":
      logfire.error(
          "HubSpot lead creation failed (service error).",
          details=result.details,
          message=result.message,
      )
      return GenericResponse.error(
          message=result.message or "Failed to create lead.",
          details=result.details,
      )

    logfire.info(
        "HubSpot lead creation successful.", lead_id=result.hubspot_id
    )
    return GenericResponse(data=result)
  except Exception as e:
    logfire.exception("Unexpected error during HubSpot lead creation.")
    return GenericResponse.error(
        message=f"An unexpected error occurred: {str(e)}", status_code=500
    )


@router.get(
    "/owners",
    response_model=GenericResponse[List[dict]],
    summary="Get HubSpot Owners",
)
async def get_owners(
    email: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
  """
  Fetch owners from HubSpot.
  """
  logfire.info("Received request for owners", email=email)
  try:
    owners = await hubspot_manager.get_owners(limit=10)
    logfire.info(
        f"HubSpot owners fetch successful. Found {len(owners)} owners.")
    return GenericResponse(data=owners)
  except Exception as e:
    logfire.exception("Unexpected error during HubSpot owners fetch.")
    return GenericResponse.error(
        message=f"An unexpected error occurred: {str(e)}", status_code=500
    )
