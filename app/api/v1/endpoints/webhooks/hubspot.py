# app/api/v1/endpoints/webhooks/hubspot.py

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException
import logfire
from typing import Optional, Dict, Any
from pydantic import BaseModel

# Import models
# Use the new model for the payload
from app.models.webhook import HubSpotContactDataPayload, HubSpotPropertyDetail
from app.models.hubspot import HubSpotLeadProperties, HubSpotLeadResult, HubSpotApiResult
from app.models.classification import ClassificationInput
from app.models.common import GenericResponse

# Import services
from app.services.hubspot import hubspot_manager
from app.services.classify.classification import classification_manager

# Import helpers
from .helpers import (
    _is_hubspot_contact_complete,
    _trigger_bland_call_for_hubspot,
    _update_hubspot_lead_after_classification,
    prepare_classification_input
)

router = APIRouter()


# Define a response model for the data part of GenericResponse
class HubSpotWebhookResponseData(BaseModel):
    status: str
    message: str


def _extract_simple_properties(properties: Dict[str, Optional[HubSpotPropertyDetail]]) -> Dict[str, Any]:
    """Helper to extract simple key-value pairs from the detailed properties."""
    simple_props = {}
    for key, detail in properties.items():
        if detail:
            simple_props[key] = detail.value
        else:
            simple_props[key] = None # Or handle as needed if property exists but detail is null
    return simple_props


@router.post("/hubspot", summary="Handle HubSpot Direct Contact Data Webhook", response_model=GenericResponse[HubSpotWebhookResponseData])
async def webhook_hubspot(
    payload: HubSpotContactDataPayload = Body(...), # Use the new payload model
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> GenericResponse[HubSpotWebhookResponseData]:
  """
  Receives direct contact data payload from HubSpot (e.g., via Workflow).
  Checks completeness.
  If complete: Classifies data, creates/updates lead, notifies n8n.
  If incomplete: Creates a basic lead, triggers Bland.ai call with lead_id.
  """
  logfire.info("Received HubSpot direct contact data payload.",
               contact_vid=payload.vid)

  # --- Process the received contact data directly --- 
  contact_id = str(payload.vid)
  logfire.info(f"Processing direct data for contact ID: {contact_id}")

  # 1. Extract Contact Properties from Payload
  # No need to fetch, data is in the payload
  if not payload.properties:
      logfire.error("Received payload has no properties.", contact_id=contact_id)
      # Consider returning an error response if appropriate
      raise HTTPException(status_code=400, detail="Payload missing properties")

  # Convert the detailed properties structure to a simple key-value dict
  contact_properties = _extract_simple_properties(payload.properties)
  logfire.info("Extracted contact properties from payload.",
                 contact_id=contact_id)

  # 2. Check if Contact Data is Complete
  is_complete = _is_hubspot_contact_complete(contact_properties)

  # --- Lead creation is now deferred until after classification or Bland call ---
  # REMOVED: Immediate lead creation block

  # 4. Handle based on completeness
  if is_complete:
    logfire.info("HubSpot contact data is complete. Proceeding with classification.",
                 contact_id=contact_id)

    # Prepare ClassificationInput using the extracted properties
    classification_input = prepare_classification_input(
        source="hubspot_webhook_direct", # Indicate the source
        raw_data={"hubspot_contact_payload": payload.model_dump(mode='json')}, # Store raw payload if needed
        extracted_data={
            "firstname": contact_properties.get("firstname"),
            "lastname": contact_properties.get("lastname"),
            "email": contact_properties.get("email"),
            "phone": contact_properties.get("phone"),
            "company": contact_properties.get("company"),
            "message": contact_properties.get("message"), # Ensure 'message' exists or handle None
            "text_consent": contact_properties.get("by_submitting_this_form_you_consent_to_receive_texts"),
            "service_needed": contact_properties.get("what_service_do_you_need_"),
            "stall_count": contact_properties.get("how_many_portable_toilet_stalls_"),
            "ada_required": contact_properties.get("ada"), # Ensure 'ada' exists or handle None
            "event_address": contact_properties.get("event_or_job_address"),
            "event_city": contact_properties.get("city"),
            "event_postal_code": contact_properties.get("zip"),
            "event_start_date": contact_properties.get("event_start_date"),
            "event_end_date": contact_properties.get("event_end_date"),
            # Add any other relevant fields from contact_properties
        }
    )

    # Classify
    classification_result = await classification_manager.classify_lead_data(classification_input)
    logfire.info("Classification result received for HubSpot contact.", # Removed lead_id
                 contact_id=contact_id,
                 classification=classification_result.model_dump(exclude={"input_data"}))

    # Create Lead, Update Lead, and Notify n8n (background)
    # Pass contact_id instead of lead_id
    background_tasks.add_task(
        _update_hubspot_lead_after_classification,
        classification_result,
        classification_input,
        contact_id # Pass contact_id
        # Removed lead_id
    )

  else:  # Incomplete
    logfire.warn("HubSpot contact data incomplete. Triggering Bland.ai call.",
                 contact_id=contact_id) # Removed lead_id

    # Trigger Bland call (background)
    # Pass contact_id instead of lead_id
    background_tasks.add_task(
        _trigger_bland_call_for_hubspot,
        contact_id, # Pass contact_id
        # Removed lead_id
        contact_properties # Pass the extracted simple properties
    )

  # Removed the loop and event-specific logic

  return GenericResponse(data=HubSpotWebhookResponseData(status="received", message="HubSpot direct contact data processed. Lead creation deferred."))
