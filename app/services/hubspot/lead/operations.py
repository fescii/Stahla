# app/services/hubspot/lead/operations.py

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Literal

from hubspot.crm.objects.models import SimplePublicObjectInput
from hubspot.crm.objects.exceptions import ApiException as ObjectApiException
from pydantic import ValidationError

from app.models.hubspot import (
    HubSpotLeadInput,
    HubSpotLeadProperties,
    HubSpotContactInput,
    HubSpotContactProperties,
    HubSpotCompanyProperties,
    HubSpotApiResult,
    HubSpotSearchRequest,
    HubSpotSearchResponse,
    HubSpotObject,
)
from app.services.hubspot.utils.helpers import _handle_api_error
from app.core.config import settings

logger = logging.getLogger(__name__)


class LeadOperations:
  def __init__(self, manager):
    self.manager = manager

  async def create(self, lead_input: HubSpotLeadInput) -> HubSpotApiResult:
    """Create a new lead in HubSpot."""
    try:
      properties = lead_input.properties
      return await self.create_lead(properties)
    except Exception as e:
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message=f"Error creating lead: {str(e)}"
      )

  async def create_lead(self, lead_data: HubSpotLeadProperties) -> HubSpotApiResult:
    """Create a Lead in HubSpot using the v3 Objects API."""
    logger.info(
        f"Attempting to create lead with data: {lead_data.model_dump_json(indent=2, exclude_none=True)}"
    )

    try:
      # Create Lead directly from the provided properties
      lead_name = f"Lead - {lead_data.project_category or 'New Project'}"
      lead_properties = {
          "hs_lead_name": lead_name,
          "hs_lead_status": "NEW",
      }

      # Add all the lead properties
      for key, value in lead_data.model_dump(exclude_none=True).items():
        if isinstance(value, (str, int, float, bool)):
          lead_properties[key] = str(
              value) if not isinstance(value, str) else value

      try:
        simple_public_object_input = SimplePublicObjectInput(
            properties=lead_properties
        )

        lead_response = await asyncio.to_thread(
            self.manager.client.crm.objects.basic_api.create,
            object_type="leads",
            simple_public_object_input_for_create=simple_public_object_input
        )

        if lead_response and lead_response.id:
          lead_id = lead_response.id
          logger.info(f"Successfully created lead ID: {lead_id}")

          return HubSpotApiResult(
              status="success",
              entity_type="lead",
              hubspot_id=lead_id,
              message="Lead created successfully",
              details={"lead_id": lead_id}
          )
        else:
          return HubSpotApiResult(
              status="error",
              entity_type="lead",
              message="Failed to create lead"
          )
      except Exception as e:
        logger.error(f"Error creating lead: {e}", exc_info=True)
        return HubSpotApiResult(
            status="error",
            entity_type="lead",
            message=f"Failed to create lead: {str(e)}"
        )

    except Exception as e:
      logger.error(f"Unexpected error in lead creation: {e}", exc_info=True)
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message=f"Unexpected error: {str(e)}"
      )

  async def get_by_id(self, lead_id: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    """Get a lead by ID."""
    try:
      fetch_properties = properties or [
          "hs_lead_name",
          "hs_lead_status",
          "hubspot_owner_id",
          "createdate",
          "lastmodifieddate"
      ]

      api_response = await asyncio.to_thread(
          self.manager.client.crm.objects.basic_api.get_by_id,
          object_type="leads",
          object_id=lead_id,
          properties=fetch_properties,
          archived=False
      )

      if api_response:
        lead_object = HubSpotObject(**api_response.to_dict())
        return HubSpotApiResult(
            status="success",
            entity_type="lead",
            hubspot_id=lead_id,
            message="Lead retrieved successfully",
            details={"lead": lead_object.model_dump()}
        )
      else:
        return HubSpotApiResult(
            status="error",
            entity_type="lead",
            message="Lead not found"
        )
    except Exception as e:
      error_info = await _handle_api_error(e, "get lead", lead_id)
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message=error_info.get("error", "Error retrieving lead")
      )

  async def update_properties(self, lead_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
    """Update a lead's properties."""
    try:
      simple_public_object_input = SimplePublicObjectInput(
          properties=properties)

      api_response = await asyncio.to_thread(
          self.manager.client.crm.objects.basic_api.update,
          object_type="leads",
          object_id=lead_id,
          simple_public_object_input=simple_public_object_input
      )

      if api_response:
        return HubSpotApiResult(
            status="updated",
            entity_type="lead",
            hubspot_id=lead_id,
            message="Lead updated successfully"
        )
      else:
        return HubSpotApiResult(
            status="error",
            entity_type="lead",
            message="Failed to update lead"
        )
    except Exception as e:
      error_info = await _handle_api_error(e, "update lead", lead_id)
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message=error_info.get("error", "Error updating lead")
      )

  async def associate_to_contact(self, lead_id: str, contact_id: str) -> bool:
    """Associate a lead to a contact."""
    return await self.manager.association.associate_objects(
        # LEAD_TO_CONTACT_ASSOCIATION_TYPE_ID
        "leads", lead_id, "contacts", contact_id, 15
    )

  async def search(self, search_request: HubSpotSearchRequest) -> HubSpotSearchResponse:
    """Search for leads."""
    try:
      return await self.manager.search_objects("leads", search_request)
    except Exception as e:
      logger.error(f"Error searching leads: {e}", exc_info=True)
      return HubSpotSearchResponse(total=0, results=[], paging=None)

  async def create_or_update_contact_and_lead(self, contact_input: HubSpotContactInput, lead_input: HubSpotLeadInput) -> Tuple[HubSpotApiResult, HubSpotApiResult]:
    """Create or update both contact and lead."""
    # Create contact first
    contact_result = await self.manager.contact.create(contact_input)

    # Create lead
    lead_result = await self.create(lead_input)

    # Associate if both succeeded
    if (contact_result.status == "created" and lead_result.status == "success" and
            contact_result.hubspot_id and lead_result.hubspot_id):
      await self.associate_to_contact(lead_result.hubspot_id, contact_result.hubspot_id)

    return contact_result, lead_result
