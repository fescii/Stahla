# app/api/v1/endpoints/webhooks/voice.py

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status
import logfire
from typing import Optional

# Import models
from app.models.bland import BlandWebhookPayload
from app.models.classification import ClassificationInput

# Import services
from app.services.bland import bland_manager
from app.services.classify.classification import classification_manager

# Import helpers
from .helpers import (
    _handle_hubspot_update,
    _update_hubspot_deal_after_classification,
    prepare_classification_input
)

router = APIRouter()


@router.post(
    "/voice",
    summary="Receive Voice Transcripts from Bland.ai",
)
async def webhook_voice(
    payload: BlandWebhookPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
  """
  Handles incoming webhook submissions containing voice transcripts from Bland.ai.
  Processes the transcript, extracts data, and sends for classification.
  If the call originated from an incomplete HubSpot lead, updates the existing HubSpot deal.
  Otherwise, creates a new contact/deal.
  """
  logfire.info("Received voice webhook payload via API.",
               call_id=payload.call_id)

  # Process transcript
  processing_result = await bland_manager.process_incoming_transcript(payload)

  if processing_result.status == "error":
    logfire.error("Failed to process Bland transcript.",
                  call_id=payload.call_id, message=processing_result.message)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=processing_result.message or "Failed to process voice transcript."
    )

  logfire.info("Bland transcript processed, proceeding to classification.",
               call_id=payload.call_id)

  extracted_data = processing_result.details.get("extracted_data", {})
  raw_data = payload.model_dump(mode='json')

  # Check for HubSpot IDs in Metadata
  hubspot_contact_id: Optional[str] = None
  hubspot_deal_id: Optional[str] = None
  metadata = {}
  # Check both payload.variables.metadata and payload.metadata
  if getattr(payload, 'variables', None) and isinstance(payload.variables, dict) and \
     payload.variables.get('metadata', None) and isinstance(payload.variables['metadata'], dict):
    metadata = payload.variables['metadata']
  elif getattr(payload, 'metadata', None) and isinstance(payload.metadata, dict):
    metadata = payload.metadata

  if metadata:
    hubspot_contact_id = metadata.get("hubspot_contact_id")
    hubspot_deal_id = metadata.get("hubspot_deal_id")
    logfire.info("Found metadata in Bland payload.",
                 contact_id=hubspot_contact_id, deal_id=hubspot_deal_id)
    form_data = metadata.get('form_submission_data', {})
    if form_data:
      logfire.info(
          "Merging form_submission_data from metadata into extracted_data")
      # Update extracted_data, giving priority to form_data for common fields
      extracted_data.update(form_data)

  # Add call-specific details (ensure they don't overwrite metadata if already present)
  extracted_data.setdefault(
      "call_recording_url", getattr(payload, 'recording_url', None))
  extracted_data.setdefault("call_summary", getattr(payload, 'summary', None))

  logfire.info("Final data prepared for classification (Voice)",
               has_email=bool(extracted_data.get('email')),
               email=extracted_data.get('email'),
               merged_data_keys=list(extracted_data.keys()))

  # Prepare ClassificationInput
  classification_input = prepare_classification_input(
      source="voice",
      raw_data=raw_data,
      extracted_data=extracted_data
  )

  logfire.info("Created classification input for voice webhook",
               email=classification_input.email,
               has_email=bool(classification_input.email))

  # Classify
  classification_result = await classification_manager.classify_lead_data(classification_input)
  logfire.info("Classification result received.",
               result=classification_result.model_dump(exclude={"input_data"}))

  # HubSpot Integration (Update or Create)
  final_contact_id: Optional[str] = None
  final_deal_id: Optional[str] = None

  if hubspot_deal_id and hubspot_contact_id:
    logfire.info("Updating existing HubSpot deal via /voice webhook.",
                 contact_id=hubspot_contact_id, deal_id=hubspot_deal_id)
    # Update existing deal in background
    background_tasks.add_task(
        _update_hubspot_deal_after_classification,
        classification_result,
        classification_input,
        hubspot_contact_id,
        hubspot_deal_id
    )
    final_contact_id = hubspot_contact_id
    final_deal_id = hubspot_deal_id
  else:
    logfire.info(
        "No existing HubSpot deal ID found in metadata, creating new contact/deal.")
    # Create new contact/deal in background

    async def _run_handle_hubspot_update_in_background():
      nonlocal final_contact_id, final_deal_id
      c_id, d_id = await _handle_hubspot_update(classification_result, classification_input)
      final_contact_id = c_id
      final_deal_id = d_id
      logfire.info("Background HubSpot update completed (create/update)",
                   contact_id=c_id, deal_id=d_id)

    background_tasks.add_task(_run_handle_hubspot_update_in_background)
    # IDs will be None in the immediate response
    final_contact_id = None
    final_deal_id = None

  # Return response
  return {
      "status": "received",
      "source": "voice",
      "action": "classification_complete",
      "classification": classification_result.classification.model_dump() if classification_result.classification else None,
      "hubspot_contact_id": final_contact_id,  # May be None if backgrounded
      "hubspot_deal_id": final_deal_id      # May be None if backgrounded
  }
