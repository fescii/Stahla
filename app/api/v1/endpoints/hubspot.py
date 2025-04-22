# app/api/v1/endpoints/hubspot.py

from fastapi import APIRouter, HTTPException, status, Body
from typing import List, Optional
import logfire
from pydantic import BaseModel, EmailStr, Field

# Import models
from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotLeadProperties,
    HubSpotApiResult,
    HubSpotContactResult,
    HubSpotLeadResult
)
# Import the manager
from app.services.hubspot import hubspot_manager

router = APIRouter()

# Define a Pydantic model for the sample form input
class SampleContactForm(BaseModel):
    what_service_do_you_need_: Optional[str] = Field(None, alias="What service do you need?")
    how_many_portable_toilet_stalls_: Optional[int] = Field(None, alias="How Many Portable Toilet Stalls?")
    event_or_job_address: Optional[str] = Field(None, alias="Event or Job Address")
    zip: Optional[str] = Field(None, alias="Postal code")
    city: Optional[str] = Field(None, alias="City")
    event_start_date: Optional[str] = Field(None, alias="Event start date") # Keep as string for now
    event_end_date: Optional[str] = Field(None, alias="Event end date") # Keep as string for now
    firstname: str = Field(..., alias="First name")
    lastname: str = Field(..., alias="Last name")
    phone: str = Field(..., alias="Phone number")
    email: EmailStr = Field(..., alias="Email")
    by_submitting_this_form_you_consent_to_receive_texts: Optional[bool] = Field(None, alias="I consent to receive texts on the phone number provided")

    model_config = {
        "populate_by_name": True,
        "extra": 'ignore' # Ignore extra fields that might be in a real form submission
    }

@router.post("/test/contact", response_model=HubSpotApiResult, summary="Test HubSpot Contact Creation/Update", tags=["HubSpot Tests"])
async def test_hubspot_contact(contact_data: HubSpotContactProperties = Body(...)):
    """
    Test endpoint to create or update a HubSpot contact.
    Uses the same logic as the main webhook flow but is callable directly.
    """
    logfire.info("Received request for /test/contact", contact_email=contact_data.email)
    try:
        # Call the manager method which now returns HubSpotApiResult
        result: HubSpotApiResult = await hubspot_manager.create_or_update_contact(contact_data)

        if result.status == "error":
            logfire.error("HubSpot contact test failed (service error).", details=result.details, message=result.message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 500 depending on error type
                detail=result.message or "Failed to create or update contact."
            )

        logfire.info("HubSpot contact test successful.", contact_id=result.hubspot_id)
        # Return the result directly as it matches HubSpotApiResult
        return result
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logfire.exception("Unexpected error during HubSpot contact test.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# Renamed endpoint and updated logic for Leads
@router.post("/test/lead", response_model=HubSpotApiResult, summary="Test HubSpot Lead Creation", tags=["HubSpot Tests"])
async def test_hubspot_lead(
    lead_data: HubSpotLeadProperties = Body(...),
    contact_id: Optional[str] = Body(None, description="Optional HubSpot Contact ID to associate the lead with")
):
    """
    Test endpoint to create a HubSpot lead and optionally associate it with a contact.
    """
    logfire.info("Received request for /test/lead", lead_properties=lead_data.model_dump(exclude_none=True), contact_id=contact_id) # Updated log
    try:
        # Call the manager method for creating leads
        result: HubSpotApiResult = await hubspot_manager.create_lead(lead_data, associated_contact_id=contact_id)

        if result.status == "error":
            logfire.error("HubSpot lead test failed (service error).", details=result.details, message=result.message) # Updated log
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 500
                detail=result.message or "Failed to create lead." # Updated message
            )

        logfire.info("HubSpot lead test successful.", lead_id=result.hubspot_id) # Updated log
        # Return the result directly as it matches HubSpotApiResult
        return result
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logfire.exception("Unexpected error during HubSpot lead test.") # Updated log
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/test/owners", response_model=List[dict], summary="Test Fetching HubSpot Owners", tags=["HubSpot Tests"])
async def test_get_owners(email: Optional[str] = None):
    """
    Test endpoint to fetch owners from HubSpot.
    """
    logfire.info("Received request for /test/owners", email=email)
    try:
        owners = await hubspot_manager.get_owners(email=email)
        logfire.info(f"HubSpot owners test successful. Found {len(owners)} owners.")
        return owners
    except Exception as e:
        logfire.exception("Unexpected error during HubSpot owners test.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# Modified endpoint to accept form data in request body
@router.post("/test/create-sample-contact", response_model=HubSpotApiResult, summary="Create HubSpot Contact from Form Data", tags=["HubSpot Tests"])
async def create_contact_from_form_data(form_data: SampleContactForm = Body(...)):
    """
    Creates a HubSpot contact using data provided in the request body,
    validated against the SampleContactForm model.
    Useful for triggering the contact creation flow manually with specific data.
    """
    logfire.info("Received request for /test/create-sample-contact with form data", form_email=form_data.email)

    # Map validated form data to HubSpotContactProperties
    # Note: Field names in SampleContactForm match the aliases in HubSpotContactProperties where applicable
    hubspot_props_data = {
        "what_service_do_you_need_": form_data.what_service_do_you_need_,
        "how_many_portable_toilet_stalls_": form_data.how_many_portable_toilet_stalls_,
        "event_or_job_address": form_data.event_or_job_address,
        "zip": form_data.zip,
        "city": form_data.city,
        "event_start_date": form_data.event_start_date, # Consider date conversion if needed by HubSpot
        "event_end_date": form_data.event_end_date, # Consider date conversion if needed by HubSpot
        "firstname": form_data.firstname,
        "lastname": form_data.lastname,
        "phone": form_data.phone,
        "email": form_data.email,
        "by_submitting_this_form_you_consent_to_receive_texts": form_data.by_submitting_this_form_you_consent_to_receive_texts,
        # Add mappings for other HubSpotContactProperties if they can be derived from the form
        # e.g., "address": form_data.event_or_job_address, # If address is same as event address
    }

    try:
        # Create the HubSpotContactProperties object, excluding None values
        contact_props = HubSpotContactProperties(**{k: v for k, v in hubspot_props_data.items() if v is not None})

        logfire.info("Attempting to create/update contact from form data", email=contact_props.email)
        result: HubSpotApiResult = await hubspot_manager.create_or_update_contact(contact_props)

        if result.status == "error":
            logfire.error("HubSpot contact creation from form data failed (service error).", details=result.details, message=result.message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message or "Failed to create or update contact from form data."
            )

        logfire.info("HubSpot contact creation from form data successful.", contact_id=result.hubspot_id)
        return result

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logfire.exception("Unexpected error during HubSpot contact creation from form data.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
