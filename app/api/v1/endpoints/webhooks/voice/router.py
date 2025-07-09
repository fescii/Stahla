# app/api/v1/endpoints/webhooks/voice/router.py

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status, Depends
import logfire
from typing import Optional, Dict, Any
from pydantic import BaseModel

# Import models
from app.models.bland import BlandWebhookPayload
from app.models.classification import ClassificationOutput
from app.models.common import GenericResponse

# Import services
from app.services.bland import get_bland_manager
from app.services.classify.classification import classification_manager
from app.services.hubspot import hubspot_manager
from app.services.mongo import MongoService, get_mongo_service

# Import local helpers
from .service import (
    merge_data_sources,
    update_classification_input,
    handle_hubspot_integration
)

# Import shared helpers
from ..util import prepare_classification_input

router = APIRouter()

# Define a response model for the data part of GenericResponse


class VoiceWebhookResponseData(BaseModel):
  status: str
  source: str
  action: str
  classification: Optional[ClassificationOutput] = None
  hubspot_contact_id: Optional[str] = None
  hubspot_lead_id: Optional[str] = None


@router.post(
    "/voice",
    summary="Receive Voice Transcripts from Bland.ai",
    response_model=GenericResponse[VoiceWebhookResponseData]
)
async def webhook_voice(
    payload: BlandWebhookPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    mongo_service: MongoService = Depends(get_mongo_service)
) -> GenericResponse[VoiceWebhookResponseData]:
  """
  Handles incoming webhook submissions containing voice transcripts from Bland.ai.
  Processes the transcript, extracts data, and sends for classification.
  If the call originated from an incomplete HubSpot lead, updates the existing HubSpot deal.
  Otherwise, creates a new contact/deal.
  """
  logfire.info("Received voice webhook payload via API.",
               call_id=payload.call_id)

  # Process transcript
  processing_result = await get_bland_manager().process_incoming_transcript(
      payload
  )

  if processing_result.status == "error":
    logfire.error("Failed to process Bland transcript.",
                  call_id=payload.call_id, message=processing_result.message)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=processing_result.message or "Failed to process voice transcript."
    )

  logfire.info("Bland transcript processed, proceeding to classification.",
               call_id=payload.call_id)

  # Extract data from processing result and payload metadata
  details = processing_result.details or {}
  extracted_data, hubspot_contact_id, hubspot_lead_id = merge_data_sources(
      details.get("extracted_data", {}),
      payload
  )

  # Add call-specific details to extracted data
  extracted_data = {
      **extracted_data,
      "call_recording_url": getattr(payload, 'recording_url', None),
      "call_summary": getattr(payload, 'summary', None),
      "full_transcript": getattr(payload, 'concatenated_transcript', None)
  }

  logfire.info("Final data prepared for classification (Voice)",
               has_email=bool(extracted_data.get('email')),
               email=extracted_data.get('email'),
               merged_data_keys=list(extracted_data.keys()))

  # Prepare ClassificationInput using the enriched extracted_data
  raw_data = payload.model_dump(mode='json')
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

  # Update classification_input with extracted details
  if classification_result.status == "success" and classification_result.classification:
    classification_input = update_classification_input(
        classification_input,
        classification_result.classification.metadata or {}
    )

  # HubSpot Integration (Update or Create)
  final_contact_id, final_lead_id = await handle_hubspot_integration(
      classification_result=classification_result,
      classification_input=classification_input,
      hubspot_contact_id=hubspot_contact_id,
      hubspot_lead_id=hubspot_lead_id,
      background_tasks=background_tasks
  )

  # Return response
  return GenericResponse(
      data=VoiceWebhookResponseData(
          status="received",
          source="voice",
          action="classification_complete",
          classification=classification_result.classification,
          hubspot_contact_id=final_contact_id,
          hubspot_lead_id=final_lead_id
      )
  )
