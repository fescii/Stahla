# app/api/v1/endpoints/hubspot/leads.py

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

router = APIRouter(prefix="/leads", tags=["hubspot-leads"])

# Hardcoded pagination limit
PAGINATION_LIMIT = 10


def _load_lead_fields() -> List[str]:
  """Load lead field names from lead.json"""
  try:
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    properties_path = os.path.join(
        current_dir, "..", "..", "..", "..", "properties", "lead.json")
    properties_path = os.path.abspath(properties_path)

    with open(properties_path, 'r') as f:
      data = json.load(f)
      return [field["name"] for field in data.get("inputs", [])]
  except Exception as e:
    logfire.error(f"Error loading lead fields: {e}")
    # Return default fields if JSON loading fails
    return [
        "project_category", "ai_intended_use", "units_needed", "expected_attendance",
        "ada_required", "additional_services_needed", "onsite_facilities",
        "rental_start_date", "rental_end_date", "site_working_hours",
        "weekend_service_needed", "cleaning_service_needed", "onsite_contact_name",
        "onsite_contact_phone", "site_ground_type", "site_obstacles",
        "water_source_distance", "power_source_distance", "within_local_service_area",
        "partner_referral_consent", "needs_human_follow_up", "quote_urgency",
        "ai_lead_type", "ai_classification_reasoning", "ai_classification_confidence",
        "ai_routing_suggestion", "ai_qualification_notes", "number_of_stalls",
        "event_duration_days", "guest_count_estimate", "ai_estimated_value",
        "hs_lead_name", "hs_lead_status", "createdate", "lastmodifieddate", "hs_object_id"
    ]


@router.get("/recent", response_model=GenericResponse[PaginatedResponse[HubSpotObject]])
async def get_recent_leads(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(PAGINATION_LIMIT, ge=1, le=100,
                       description="Number of leads per page"),
    current_user: User = Depends(get_current_user)
):
  """Get recent leads ordered by creation date (newest first)."""
  try:
    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Get lead fields to fetch
    lead_fields = _load_lead_fields()

    # Create search request for recent leads
    search_request = HubSpotSearchRequest(
        filterGroups=[],  # No filters, get all leads
        properties=lead_fields,
        sorts=[{"propertyName": "createdate", "direction": "DESCENDING"}],
        limit=limit,
        after=str(offset) if offset > 0 else None
    )

    # Search leads using HubSpot manager
    response = await hubspot_manager.search_objects("leads", search_request)

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
    logfire.error(f"Error fetching recent leads: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch leads",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/search", response_model=GenericResponse[PaginatedResponse[HubSpotObject]])
async def search_leads(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(PAGINATION_LIMIT, ge=1, le=100,
                       description="Number of leads per page"),
    project_category: Optional[str] = Query(
        None, description="Filter by project category"),
    ai_lead_type: Optional[str] = Query(
        None, description="Filter by AI lead type"),
    quote_urgency: Optional[str] = Query(
        None, description="Filter by quote urgency"),
    within_local_service_area: Optional[bool] = Query(
        None, description="Filter by local service area"),
    ada_required: Optional[bool] = Query(
        None, description="Filter by ADA requirement"),
    weekend_service_needed: Optional[bool] = Query(
        None, description="Filter by weekend service needed"),
    needs_human_follow_up: Optional[bool] = Query(
        None, description="Filter by needs human follow-up"),
    lead_status: Optional[str] = Query(
        None, description="Filter by lead status"),
    created_after: Optional[str] = Query(
        None, description="Filter leads created after this date (ISO format)"),
    created_before: Optional[str] = Query(
        None, description="Filter leads created before this date (ISO format)"),
    estimated_value_min: Optional[float] = Query(
        None, description="Filter by minimum estimated value"),
    estimated_value_max: Optional[float] = Query(
        None, description="Filter by maximum estimated value"),
    current_user: User = Depends(get_current_user)
):
  """Search leads with various filters and pagination."""
  try:
    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Get lead fields to fetch
    lead_fields = _load_lead_fields()

    # Build filter groups based on provided parameters
    filters = []

    if project_category:
      filters.append(HubSpotSearchFilter(
          propertyName="project_category",
          operator="EQ",
          value=project_category
      ))

    if ai_lead_type:
      filters.append(HubSpotSearchFilter(
          propertyName="ai_lead_type",
          operator="EQ",
          value=ai_lead_type
      ))

    if quote_urgency:
      filters.append(HubSpotSearchFilter(
          propertyName="quote_urgency",
          operator="EQ",
          value=quote_urgency
      ))

    if within_local_service_area is not None:
      filters.append(HubSpotSearchFilter(
          propertyName="within_local_service_area",
          operator="EQ",
          value="true" if within_local_service_area else "false"
      ))

    if ada_required is not None:
      filters.append(HubSpotSearchFilter(
          propertyName="ada_required",
          operator="EQ",
          value="true" if ada_required else "false"
      ))

    if weekend_service_needed is not None:
      filters.append(HubSpotSearchFilter(
          propertyName="weekend_service_needed",
          operator="EQ",
          value="true" if weekend_service_needed else "false"
      ))

    if needs_human_follow_up is not None:
      filters.append(HubSpotSearchFilter(
          propertyName="needs_human_follow_up",
          operator="EQ",
          value="true" if needs_human_follow_up else "false"
      ))

    if lead_status:
      filters.append(HubSpotSearchFilter(
          propertyName="hs_lead_status",
          operator="EQ",
          value=lead_status
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

    if estimated_value_min is not None:
      filters.append(HubSpotSearchFilter(
          propertyName="ai_estimated_value",
          operator="GTE",
          value=str(estimated_value_min)
      ))

    if estimated_value_max is not None:
      filters.append(HubSpotSearchFilter(
          propertyName="ai_estimated_value",
          operator="LTE",
          value=str(estimated_value_max)
      ))

    # Create filter groups (all filters are AND conditions)
    filter_groups = [HubSpotSearchFilterGroup(
        filters=filters)] if filters else []

    # Create search request
    search_request = HubSpotSearchRequest(
        filterGroups=filter_groups,
        properties=lead_fields,
        sorts=[{"propertyName": "createdate", "direction": "DESCENDING"}],
        limit=limit,
        after=str(offset) if offset > 0 else None
    )

    # Search leads using HubSpot manager
    response = await hubspot_manager.search_objects("leads", search_request)

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
    logfire.error(f"Error searching leads: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to search leads",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/{lead_id}", response_model=GenericResponse[HubSpotObject])
async def get_lead_by_id(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
  """Get a specific lead by ID with all available fields."""
  try:
    # Get lead fields to fetch
    lead_fields = _load_lead_fields()

    # Get lead by ID
    result = await hubspot_manager.get_lead_by_id(lead_id, lead_fields)

    if result.status == "success":
      lead_data = result.details.get("lead") if result.details else None
      return GenericResponse(data=lead_data)
    elif result.status == "not_found":
      return GenericResponse.error(
          message=f"Lead with ID {lead_id} not found",
          status_code=404
      )
    else:
      return GenericResponse.error(
          message=result.message or "Failed to fetch lead",
          details=result.details,
          status_code=500
      )
  except Exception as e:
    logfire.error(f"Error fetching lead {lead_id}: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch lead",
        details={"error": str(e)},
        status_code=500
    )
