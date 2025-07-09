# app/api/v1/endpoints/hubspot/sync.py

from fastapi import APIRouter, Path as FastAPIPath, Depends
from typing import Literal, Optional
import logfire

from app.models.common import GenericResponse
from app.models.user import User
from app.core.security import get_current_user
from app.services.hubspot import hubspot_manager
from app.services.hubspot.properties import PropertySyncManager

router = APIRouter(prefix="/properties/sync", tags=["hubspot-sync"])


@router.post(
    "/all",
    response_model=GenericResponse,
    summary="Sync all properties to HubSpot",
    description="Sync all contact and lead properties from JSON files to HubSpot"
)
async def sync_all_properties(current_user: User = Depends(get_current_user)):
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
    "/contacts",
    response_model=GenericResponse,
    summary="Sync contact properties to HubSpot",
    description="Sync contact properties from contact.json to HubSpot"
)
async def sync_contact_properties(current_user: User = Depends(get_current_user)):
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
    "/leads",
    response_model=GenericResponse,
    summary="Sync lead properties to HubSpot",
    description="Sync lead properties from lead.json to HubSpot"
)
async def sync_lead_properties(current_user: User = Depends(get_current_user)):
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
    "/status/{object_type}",
    response_model=GenericResponse,
    summary="Check property status",
    description="Check the status of specific properties in HubSpot"
)
async def check_property_status(
    object_type: Literal["contacts", "leads"] = FastAPIPath(
        ...,
        description="HubSpot object type to check properties for"
    ),
    property_names: Optional[str] = None,
    current_user: User = Depends(get_current_user)
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
