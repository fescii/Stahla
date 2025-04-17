# app/api/v1/endpoints/hubspot.py

from fastapi import APIRouter, HTTPException, status, Body # Added Body
from typing import List, Optional # Added Optional
import logfire

# Import models
# Make sure HubSpotContactResult and HubSpotDealResult are imported if needed for type checking
from app.models.hubspot import HubSpotContactProperties, HubSpotDealProperties, HubSpotApiResult, HubSpotContactResult, HubSpotDealResult
# Import the manager
from app.services.hubspot import hubspot_manager

router = APIRouter()

@router.post("/test/contact", response_model=HubSpotApiResult, summary="Test HubSpot Contact Creation/Update", tags=["HubSpot Tests"])
async def test_hubspot_contact(contact_data: HubSpotContactProperties = Body(...)):
    """
    Test endpoint to create or update a HubSpot contact.
    Uses the same logic as the main webhook flow but is callable directly.
    """
    logfire.info("Received request for /test/contact", contact_email=contact_data.email)
    try:
        # Call the manager method which now consistently returns HubSpotContactResult
        result: HubSpotContactResult = await hubspot_manager.create_or_update_contact(contact_data)

        if result.status == "error":
            # Raise HTTPException if the service layer reported an error
            logfire.error("HubSpot contact test failed (service error).", details=result.details, message=result.message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 500 depending on error type
                detail=result.message or "Failed to create or update contact."
            )

        logfire.info("HubSpot contact test successful.", contact_id=result.id)
        # Convert HubSpotContactResult to HubSpotApiResult for response_model
        return HubSpotApiResult(
            status=result.status,
            message=result.message,
            details=result.properties, # Return properties in details
            entity_type="contact",
            entity_id=result.id
        )
    except HTTPException as http_exc:
        # Re-raise HTTPException to let FastAPI handle it
        raise http_exc
    except Exception as e:
        logfire.exception("Unexpected error during HubSpot contact test.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post("/test/deal", response_model=HubSpotApiResult, summary="Test HubSpot Deal Creation", tags=["HubSpot Tests"])
async def test_hubspot_deal(
    deal_data: HubSpotDealProperties = Body(...),
    contact_id: Optional[str] = Body(None, description="Optional HubSpot Contact ID to associate the deal with")
):
    """
    Test endpoint to create a HubSpot deal and optionally associate it with a contact.
    """
    logfire.info("Received request for /test/deal", deal_name=deal_data.dealname, contact_id=contact_id)
    try:
        # Call the manager method which now consistently returns HubSpotDealResult
        result: HubSpotDealResult = await hubspot_manager.create_deal(deal_data, associated_contact_id=contact_id)

        if result.status == "error":
            logfire.error("HubSpot deal test failed (service error).", details=result.details, message=result.message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 500
                detail=result.message or "Failed to create deal."
            )

        logfire.info("HubSpot deal test successful.", deal_id=result.id)
        # Convert HubSpotDealResult to HubSpotApiResult for response_model
        return HubSpotApiResult(
            status=result.status,
            message=result.message,
            details=result.properties, # Return properties in details
            entity_type="deal",
            entity_id=result.id
        )
    except HTTPException as http_exc:
        # Re-raise HTTPException
        raise http_exc
    except Exception as e:
        logfire.exception("Unexpected error during HubSpot deal test.")
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
        # get_owners logs errors internally and returns [] on failure
        owners = await hubspot_manager.get_owners(email=email)
        logfire.info(f"HubSpot owners test successful. Found {len(owners)} owners.")
        return owners
    except Exception as e:
        # Catch any unexpected errors during the call
        logfire.exception("Unexpected error during HubSpot owners test.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
