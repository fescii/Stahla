# app/api/v1/endpoints/webhooks/form/service.py

import logfire
from typing import Tuple, Optional, Dict, Any
import re

# Import models
from app.models.webhook import FormPayload
from app.models.bland import BlandCallbackRequest
from app.models.classification import ClassificationInput, ClassificationResult

# Import services
from app.services.bland import bland_manager
from app.services.hubspot import hubspot_manager
from app.services.n8n import trigger_n8n_handoff_automation
from app.core.config import settings


def is_form_complete(payload: FormPayload) -> bool:
  """
  Check if the form payload contains the minimum required information.
  NEEDS CONFIRMATION FROM KEVIN/CLIENT - using a basic set for now.
  """
  logfire.debug("Checking form completeness", payload=payload.model_dump())
  # Example: Require name, email, phone, service, address, start date
  required_fields = [
      payload.firstname,
      payload.lastname,
      payload.email,
      payload.phone,
      payload.product_interest,  # Correct field from FormPayload
      payload.event_location_description,  # Correct field from FormPayload
      payload.start_date  # Correct field from FormPayload
  ]
  is_complete = all(field is not None and str(field).strip()
                    != "" for field in required_fields)
  logfire.info(f"Form completeness check result: {is_complete}")
  return is_complete


async def trigger_bland_call(payload: FormPayload):
  """
  Triggers a Bland.ai call if the form is incomplete.
  Populates request_data for the AI agent and metadata for tracking.
  """
  if not settings.BLAND_API_KEY:
    logfire.warn("Bland API key not configured, skipping call.")
    return

  phone_number = payload.phone or ""
  if not phone_number:
    logfire.error(
        "Cannot trigger Bland call: Phone number is missing.", email=payload.email)
    return

  first_name = payload.firstname or "Lead"

  # Data for the AI agent
  agent_request_data = {
      "firstname": payload.firstname,
      "lastname": payload.lastname,
      "email": payload.email,
      "phone": payload.phone,
      "product_interest": payload.product_interest,
      "event_location_description": payload.event_location_description,
      "start_date": payload.start_date,
      "company": payload.company,
      "source_url": getattr(payload, 'source_url', None)
      # Add any other fields from FormPayload that the agent might need
  }
  # Filter out None values from agent_request_data
  agent_request_data = {k: v for k,
                        v in agent_request_data.items() if v is not None}

  # Metadata for tracking and webhook context
  # Initialize metadata with everything from agent_request_data
  call_metadata = agent_request_data.copy()
  # Add/overwrite with specific metadata fields
  call_metadata.update({
      "source": "web_form_incomplete",
      # For easier association if contact_id is email
      "form_payload_email": payload.email,
      "form_payload_phone": payload.phone,
      "form_source_url": getattr(payload, 'source_url', None)
      # Add other specific identifiers if needed, e.g., form_id if available
  })
  call_metadata = {k: v for k, v in call_metadata.items() if v is not None}

  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhook/voice"

  callback_request = BlandCallbackRequest(
      phone_number=phone_number,
      task=None,  # Assuming pathway/script uses request_data
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental form you submitted. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      max_duration=None,  # Assuming no max duration needed
      transfer_phone_number=None,  # Assuming no transfer number needed
      voice=settings.BLAND_VOICE_ID or "1",  # Use configured voice or default "1"
      webhook=webhook_url,
      request_data=agent_request_data,
      metadata=call_metadata
  )

  logfire.info(
      f"Triggering Bland call to {phone_number} from form payload.",
      request_data=agent_request_data,
      metadata=call_metadata
  )
  try:
    # contact_id for logging purposes, can be email or a more stable ID if available
    call_contact_id = payload.email or payload.phone or "unknown_form_contact"
    call_result = await bland_manager.initiate_callback(
        request_data=callback_request,  # Pass the updated callback_request
        contact_id=call_contact_id,
        log_retry_of_call_id=None,
        log_retry_reason=None,
    )
    if call_result.status == "success":
      logfire.info("Bland call initiated successfully.",
                   call_id=call_result.call_id)
    else:
      logfire.error("Failed to initiate Bland call.",
                    error=call_result.message, details=call_result.details)
  except Exception as e:
    logfire.exception("Error occurred while triggering Bland call")


# Use the existing helper from main helpers.py file
async def handle_hubspot_update(
    classification_result: ClassificationResult,
    input_data: ClassificationInput
) -> Tuple[Optional[str], Optional[str]]:
  """
  Handles creating/updating HubSpot Contact and creating a NEW Lead based on classification.
  Used when no existing lead ID is provided (e.g., initial form, email, or voice call).
  Returns (contact_id, lead_id)
  """
  return await handle_hubspot_update(classification_result, input_data)
