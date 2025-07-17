# app/api/v1/endpoints/webhooks/voice/router.py

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status, Depends
import logfire
from typing import Optional, Dict, Any
from pydantic import BaseModel
import uuid

# Import models
from app.models.bland import BlandWebhookPayload
from app.models.classification import ClassificationOutput
from app.models.common import GenericResponse

# Import services
from app.services.bland import get_bland_manager
from app.services.classify.classification import classification_manager
from app.services.hubspot import hubspot_manager
from app.services.mongo import MongoService, get_mongo_service

# Import background task for classification
from app.services.background import process_voice_classification_bg

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
  call_id: str
  processing_task_id: Optional[str] = None
  classification: Optional[ClassificationOutput] = None
  hubspot_contact_id: Optional[str] = None
  hubspot_lead_id: Optional[str] = None
  ai_processing_enabled: Optional[bool] = None
  processing_summary: Optional[str] = None


@router.post(
    "/voice",
    summary="Receive Voice Transcripts from Bland.ai",
    response_model=GenericResponse[VoiceWebhookResponseData]
)
async def webhook_voice(
    payload: BlandWebhookPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    mongo_service: MongoService = Depends(get_mongo_service),
    use_ai_processing: bool = True  # New parameter to enable/disable AI processing
) -> GenericResponse[VoiceWebhookResponseData]:
  """
  Handles incoming webhook submissions containing voice transcripts from Bland.ai.

  Enhanced with AI-powered background processing:
  - Responds immediately to webhook with acknowledgment
  - Uses background tasks to process classification with AI enhancement
  - Stores results in MongoDB for later retrieval
  - Maintains backward compatibility with existing pipeline

  Args:
    payload: Bland webhook payload containing call data and transcript
    background_tasks: FastAPI background tasks for async operations
    mongo_service: MongoDB service dependency
    use_ai_processing: Whether to use AI-enhanced processing (default: True)

  Returns:
    GenericResponse with immediate acknowledgment and background task ID
  """
  call_id = payload.call_id or "unknown"
  processing_task_id = str(uuid.uuid4())

  logfire.info("Received voice webhook payload via API - starting background processing",
               call_id=call_id,
               ai_processing_enabled=use_ai_processing,
               processing_task_id=processing_task_id)

  try:
    if use_ai_processing:
      # Add AI-enhanced background classification task
      background_tasks.add_task(
          process_voice_classification_bg,
          webhook_payload=payload,
          use_ai_classification=True,
          background_task_id=processing_task_id
      )

      logfire.info("AI-enhanced classification task queued",
                   call_id=call_id,
                   processing_task_id=processing_task_id)

      # Return immediate acknowledgment
      return GenericResponse(
          data=VoiceWebhookResponseData(
              status="received",
              source="voice",
              action="background_processing_started",
              call_id=call_id,
              processing_task_id=processing_task_id,
              classification=None,
              hubspot_contact_id=None,
              hubspot_lead_id=None,
              ai_processing_enabled=True,
              processing_summary="AI-enhanced classification started in background"
          )
      )

    else:
      # Legacy processing path (still synchronous for backward compatibility)
      logfire.info("Using legacy synchronous processing", call_id=call_id)

      # Process transcript using legacy method
      processing_result = await get_bland_manager().process_incoming_transcript(
          payload
      )

      if processing_result.status == "error":
        logfire.error("Failed to process Bland transcript.",
                      call_id=call_id, message=processing_result.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=processing_result.message or "Failed to process voice transcript."
        )

      logfire.info("Bland transcript processed, proceeding to classification.",
                   call_id=call_id)

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

      # Return legacy response
      return GenericResponse(
          data=VoiceWebhookResponseData(
              status="received",
              source="voice",
              action="classification_complete",
              call_id=call_id,
              processing_task_id=None,
              classification=classification_result.classification,
              hubspot_contact_id=final_contact_id,
              hubspot_lead_id=final_lead_id,
              ai_processing_enabled=False,
              processing_summary="Processed using legacy classification"
          )
      )

  except Exception as e:
    logfire.error(f"Unexpected error in voice webhook processing: {e}",
                  call_id=call_id,
                  exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Internal processing error: {str(e)}"
    )


def _map_classification_to_stage(lead_type: str) -> str:
  """
  Map classification lead type to HubSpot deal stage.

  Args:
    lead_type: Classification result (Services, Logistics, Leads, Disqualify)

  Returns:
    HubSpot deal stage identifier
  """
  stage_mapping = {
      'Services': 'qualified_to_services',
      'Logistics': 'qualified_to_logistics',
      'Leads': 'new_lead',
      'Disqualify': 'disqualified'
  }
  return stage_mapping.get(lead_type, 'new_lead')


@router.get(
    "/health",
    summary="AI Processing Health Check"
)
async def ai_processing_health():
  """
  Health check endpoint for AI processing components.
  """
  try:
    # Import here to avoid circular imports
    from app.services.bland.processing.ai import enhanced_voice_webhook_service

    health_status = await enhanced_voice_webhook_service.get_processing_health_check()
    return GenericResponse(data=health_status)
  except Exception as e:
    return GenericResponse(
        data={'status': 'unhealthy', 'error': str(e)},
        success=False
    )


@router.get(
    "/status/{call_id}",
    summary="Get Classification Status"
)
async def get_classification_status(call_id: str):
  """
  Get the classification status for a specific call.

  Args:
    call_id: Bland call ID to check status for

  Returns:
    Classification status information
  """
  try:
    from app.services.background import get_classification_status_bg

    status_info = await get_classification_status_bg(call_id)

    if not status_info:
      return GenericResponse(
          data={'call_id': call_id, 'status': 'not_found'},
          success=False
      )

    return GenericResponse(data=status_info)

  except Exception as e:
    return GenericResponse(
        data={'call_id': call_id, 'status': 'error', 'error': str(e)},
        success=False
    )
