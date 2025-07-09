# app/api/v1/endpoints/webhooks/hubspot.py

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Depends
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
from app.services.mongo import MongoService, get_mongo_service  # Added import

# Import helpers
from .helpers import (
    _is_hubspot_contact_complete,
    _trigger_bland_call_for_hubspot,
    _update_hubspot_lead_after_classification,
    prepare_classification_input
)

# Import background tasks
from app.services.background.mongo.tasks import (
    log_classify_bg,
    log_email_bg
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
      # Or handle as needed if property exists but detail is null
      simple_props[key] = None
  return simple_props


@router.post("/hubspot", summary="Handle HubSpot Direct Contact Data Webhook", response_model=GenericResponse[HubSpotWebhookResponseData])
async def webhook_hubspot(
    # Use the updated payload model
    payload: HubSpotContactDataPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    mongo_service: MongoService = Depends(get_mongo_service)
) -> GenericResponse[HubSpotWebhookResponseData]:
  """
  Receives direct contact data payload from HubSpot (e.g., via Workflow).
  Processes the direct data from the webhook.
  If complete: Classifies data, creates/updates lead, notifies n8n.
  If incomplete: Creates a basic lead, triggers Bland.ai call.
  """
  logfire.info("Received HubSpot direct contact data payload.")

  # Convert the payload to a dict to process
  contact_properties = payload.model_dump()

  # Extract the contact ID if present
  contact_id = str(contact_properties.get("contact_id", "unknown"))
  logfire.info(f"Processing direct data for contact ID: {contact_id}")

  # Check if we have the essential data to process
  if not payload.email:
    logfire.error("Received payload missing email.", contact_id=contact_id)
    raise HTTPException(status_code=400, detail="Payload missing email")

  # 2. Check if Contact Data is Complete
  is_complete = _is_hubspot_contact_complete(contact_properties)

  # 3. Handle based on completeness
  if is_complete:
    logfire.info("HubSpot contact data is complete. Proceeding with classification.",
                 contact_id=contact_id)

    # Convert payload to FormPayload if needed
    form_payload = payload.convert_to_form_payload()

    # Prepare ClassificationInput using the extracted properties
    classification_input = prepare_classification_input(
        source="hubspot_webhook_direct",  # Indicate the source
        # Store raw payload if needed
        raw_data={"hubspot_contact_payload": contact_properties},
        extracted_data={
            "firstname": payload.firstname,
            "lastname": payload.lastname,
            "email": payload.email,
            "phone": str(payload.phone) if payload.phone else None,
            "message": payload.message,
            "service_needed": payload.what_service_do_you_need_,
            "stall_count": payload.how_many_portable_toilet_stalls_,
            "event_address": payload.event_or_job_address,
            "event_city": payload.city,
            "event_postal_code": str(payload.zip) if payload.zip else None,
            "event_start_date": payload.event_start_date,
            "event_end_date": payload.event_end_date,
        }
    )

    # Classify
    classification_result = await classification_manager.classify_lead_data(classification_input)
    logfire.info("Classification result received for HubSpot contact.",
                 contact_id=contact_id,
                 classification=classification_result.model_dump(exclude={"input_data"}))

    # Log classification to MongoDB in background
    if classification_result.classification:
      classify_data = {
          "id": f"classify_hubspot_{contact_id}",
          "contact_id": contact_id,
          "source": "hubspot",
          "status": "COMPLETED" if classification_result.status == "success" else "FAILED",
          "lead_type": classification_result.classification.lead_type,
          "routing_suggestion": classification_result.classification.routing_suggestion,
          "confidence": classification_result.classification.confidence,
          "reasoning": classification_result.classification.reasoning,
          "requires_human_review": classification_result.classification.requires_human_review,
          "classification_results": classification_result.classification.model_dump(),
          "input_data": classification_input.model_dump(),
          "processing_time": 0
      }
      background_tasks.add_task(
          log_classify_bg,
          mongo_service=mongo_service,
          classify_data=classify_data
      )

    # Create Lead, Update Lead, and Notify n8n (background)
    background_tasks.add_task(
        _update_hubspot_lead_after_classification,
        classification_result,
        classification_input,
        contact_id
    )

  else:  # Incomplete
    logfire.warn("HubSpot contact data incomplete. Triggering Bland.ai call.",
                 contact_id=contact_id)

    # Trigger Bland call (background)
    background_tasks.add_task(
        _trigger_bland_call_for_hubspot,
        contact_id,
        contact_properties
    )

  return GenericResponse(data=HubSpotWebhookResponseData(status="received", message="HubSpot direct contact data processed. Lead creation deferred."))
