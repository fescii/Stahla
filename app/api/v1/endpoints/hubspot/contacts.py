# app/api/v1/endpoints/hubspot/contacts.py

from fastapi import APIRouter, Depends, Query
from typing import List, Optional
import logfire
import json

from app.services.hubspot import hubspot_manager
from app.models.hubspot import (
    HubSpotSearchRequest,
    HubSpotSearchFilterGroup,
    HubSpotSearchFilter,
    HubSpotObject
)
from app.models.common import GenericResponse, PaginatedResponse
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/contacts", tags=["hubspot-contacts"])

# Hardcoded pagination limit
PAGINATION_LIMIT = 10


def _load_contact_fields() -> List[str]:
  """Load contact field names from contact.json"""
  try:
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    properties_path = os.path.join(
        current_dir, "..", "..", "..", "..", "properties", "contact.json")
    properties_path = os.path.abspath(properties_path)

    with open(properties_path, 'r') as f:
      data = json.load(f)
      return [field["name"] for field in data.get("inputs", [])]
  except Exception as e:
    logfire.error(f"Error loading contact fields: {e}")
    # Return default fields if JSON loading fails
    return [
        "email", "firstname", "lastname", "phone", "city", "zip", "address", "state",
        "what_service_do_you_need_", "how_many_restroom_stalls_", "how_many_shower_stalls_",
        "how_many_laundry_units_", "event_start_date", "event_end_date", "message",
        "ai_call_summary", "ai_call_sentiment", "call_recording_url", "call_summary",
        "company_size", "createdate", "lastmodifieddate", "hs_object_id"
    ]


@router.get("/recent", response_model=GenericResponse[PaginatedResponse[HubSpotObject]])
async def get_recent_contacts(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(PAGINATION_LIMIT, ge=1, le=100,
                       description="Number of contacts per page"),
    current_user: User = Depends(get_current_user)
):
  """Get recent contacts ordered by creation date (newest first)."""
  try:
    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Get contact fields to fetch
    contact_fields = _load_contact_fields()

    # Create search request for recent contacts
    search_request = HubSpotSearchRequest(
        filterGroups=[],  # No filters, get all contacts
        properties=contact_fields,
        sorts=[{"propertyName": "createdate", "direction": "DESCENDING"}],
        limit=limit,
        after=str(offset) if offset > 0 else None
    )

    # Search contacts using HubSpot manager
    response = await hubspot_manager.search_objects("contacts", search_request)

    # Calculate total and has_more
    total = response.total
    has_more = (offset + limit) < total

    return GenericResponse(
        data=PaginatedResponse(
            items=response.results,
            page=page,
            limit=limit,
            total=total,
            has_more=has_more
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching recent contacts: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch contacts",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/search", response_model=GenericResponse[PaginatedResponse[HubSpotObject]])
async def search_contacts(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(PAGINATION_LIMIT, ge=1, le=100,
                       description="Number of contacts per page"),
    email: Optional[str] = Query(None, description="Filter by email address"),
    firstname: Optional[str] = Query(None, description="Filter by first name"),
    lastname: Optional[str] = Query(None, description="Filter by last name"),
    phone: Optional[str] = Query(None, description="Filter by phone number"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    service_type: Optional[str] = Query(
        None, description="Filter by service type needed"),
    created_after: Optional[str] = Query(
        None, description="Filter contacts created after this date (ISO format)"),
    created_before: Optional[str] = Query(
        None, description="Filter contacts created before this date (ISO format)"),
    current_user: User = Depends(get_current_user)
):
  """Search contacts with various filters and pagination."""
  try:
    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Get contact fields to fetch
    contact_fields = _load_contact_fields()

    # Build filter groups based on provided parameters
    filters = []

    if email:
      filters.append(HubSpotSearchFilter(
          propertyName="email",
          operator="CONTAINS_TOKEN",
          value=email
      ))

    if firstname:
      filters.append(HubSpotSearchFilter(
          propertyName="firstname",
          operator="CONTAINS_TOKEN",
          value=firstname
      ))

    if lastname:
      filters.append(HubSpotSearchFilter(
          propertyName="lastname",
          operator="CONTAINS_TOKEN",
          value=lastname
      ))

    if phone:
      filters.append(HubSpotSearchFilter(
          propertyName="phone",
          operator="CONTAINS_TOKEN",
          value=phone
      ))

    if city:
      filters.append(HubSpotSearchFilter(
          propertyName="city",
          operator="CONTAINS_TOKEN",
          value=city
      ))

    if state:
      filters.append(HubSpotSearchFilter(
          propertyName="state",
          operator="CONTAINS_TOKEN",
          value=state
      ))

    if service_type:
      filters.append(HubSpotSearchFilter(
          propertyName="what_service_do_you_need_",
          operator="EQ",
          value=service_type
      ))

    if created_after:
      filters.append(HubSpotSearchFilter(
          propertyName="createdate",
          operator="GTE",
          value=created_after
      ))

    if created_before:
      filters.append(HubSpotSearchFilter(
          propertyName="createdate",
          operator="LTE",
          value=created_before
      ))

    # Create filter groups (all filters are AND conditions)
    filter_groups = [HubSpotSearchFilterGroup(
        filters=filters)] if filters else []

    # Create search request
    search_request = HubSpotSearchRequest(
        filterGroups=filter_groups,
        properties=contact_fields,
        sorts=[{"propertyName": "createdate", "direction": "DESCENDING"}],
        limit=limit,
        after=str(offset) if offset > 0 else None
    )

    # Search contacts using HubSpot manager
    response = await hubspot_manager.search_objects("contacts", search_request)

    # Calculate total and has_more
    total = response.total
    has_more = (offset + limit) < total

    return GenericResponse(
        data=PaginatedResponse(
            items=response.results,
            page=page,
            limit=limit,
            total=total,
            has_more=has_more
        )
    )
  except Exception as e:
    logfire.error(f"Error searching contacts: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to search contacts",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/{contact_id}", response_model=GenericResponse[HubSpotObject])
async def get_contact_by_id(
    contact_id: str,
    current_user: User = Depends(get_current_user)
):
  """Get a specific contact by ID with all available fields."""
  try:
    # Get contact fields to fetch
    contact_fields = _load_contact_fields()

    # Get contact by ID
    result = await hubspot_manager.get_contact_by_id(contact_id, contact_fields)

    if result.status == "success":
      return GenericResponse(data=result.details)
    elif result.status == "not_found":
      return GenericResponse.error(
          message=f"Contact with ID {contact_id} not found",
          status_code=404
      )
    else:
      return GenericResponse.error(
          message=result.message or "Failed to fetch contact",
          details=result.details,
          status_code=500
      )
  except Exception as e:
    logfire.error(f"Error fetching contact {contact_id}: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch contact",
        details={"error": str(e)},
        status_code=500
    )
