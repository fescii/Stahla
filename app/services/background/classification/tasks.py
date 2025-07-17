# app/services/background/classification/tasks.py

"""
Background tasks for voice classification processing.
This module handles AI-powered classification of voice webhooks
in the background to avoid blocking webhook responses.
"""

import logging
import uuid
from typing import Any, Optional, Dict
from datetime import datetime, timezone

from app.models.bland import BlandWebhookPayload
from app.models.classification import ClassificationOutput

logger = logging.getLogger(__name__)


async def process_voice_classification_bg(
    webhook_payload: BlandWebhookPayload,
    use_ai_classification: bool = True,
    background_task_id: Optional[str] = None
) -> None:
  """
  Background task to process voice webhook with AI-powered classification.

  Args:
      webhook_payload: Bland webhook payload containing call data
      use_ai_classification: Whether to use AI classification (default: True)
      background_task_id: Optional background task ID for tracking
  """
  call_id = webhook_payload.call_id
  task_id = background_task_id or str(uuid.uuid4())

  try:
    logger.info(f"Starting background voice classification for call {call_id}",
                extra={'task_id': task_id, 'call_id': call_id})

    # Import locally to avoid circular imports
    from app.services.bland.processing.ai import enhanced_voice_webhook_service

    # Step 1: Process with AI enhancement
    processing_result = await enhanced_voice_webhook_service.process_voice_webhook(
        webhook_payload=webhook_payload,
        use_ai_classification=use_ai_classification,
        store_results=False  # We'll handle storage here
    )

    # Step 2: Store processing results
    await _store_classification_results(
        webhook_payload, processing_result, task_id
    )

    # Step 3: Handle HubSpot integration if ready
    if processing_result.status == "success":
      await _handle_hubspot_integration_bg(
          webhook_payload, processing_result, task_id
      )

    logger.info(f"Background voice classification completed successfully for call {call_id}",
                extra={'task_id': task_id, 'call_id': call_id,
                       'lead_type': processing_result.details.get('classification', {}).get('lead_type') if processing_result.details else None})

  except Exception as e:
    logger.error(f"Error in background voice classification for call {call_id}: {e}",
                 extra={'task_id': task_id, 'call_id': call_id},
                 exc_info=True)

    # Store error result
    await _store_error_result(webhook_payload, str(e), task_id)


async def _store_classification_results(
    webhook_payload: BlandWebhookPayload,
    processing_result: Any,
    task_id: str
) -> None:
  """
  Store classification results in MongoDB.

  Args:
      webhook_payload: Original webhook payload
      processing_result: AI processing results
      task_id: Background task ID
  """
  try:
    # Import locally to avoid circular imports
    from app.services.mongo import get_mongo_service

    mongo_service = await get_mongo_service()

    # Create enhanced call record
    call_record = {
        'id': str(uuid.uuid4()),
        'background_task_id': task_id,

        # Original webhook data
        'call_id': webhook_payload.call_id,
        'phone_number': webhook_payload.from_ or webhook_payload.to,
        'call_duration': webhook_payload.call_length,
        'call_status': webhook_payload.status,
        'completed_at': webhook_payload.completed_at,
        'inbound': webhook_payload.inbound,
        'transcript': webhook_payload.concatenated_transcript or webhook_payload.summary,
        'recording_url': str(webhook_payload.recording_url) if webhook_payload.recording_url else None,

        # AI processing results
        'ai_processing': processing_result.details if hasattr(processing_result, 'details') else {},
        'processing_version': '2.0',
        'processed_at': datetime.utcnow(),
        'processing_status': processing_result.status if hasattr(processing_result, 'status') else 'unknown',

        # Classification results for easy querying
        'classification': processing_result.details.get('classification', {}) if hasattr(processing_result, 'details') and processing_result.details else {},
        'lead_type': processing_result.details.get('classification', {}).get('lead_type') if hasattr(processing_result, 'details') and processing_result.details else None,
        'routing_suggestion': processing_result.details.get('classification', {}).get('routing_suggestion') if hasattr(processing_result, 'details') and processing_result.details else None,
        'requires_human_review': processing_result.details.get('classification', {}).get('requires_human_review') if hasattr(processing_result, 'details') and processing_result.details else True,

        # HubSpot readiness
        'hubspot_ready': processing_result.details.get('hubspot_ready', {}) if hasattr(processing_result, 'details') and processing_result.details else {},
        'ready_for_sync': processing_result.details.get('hubspot_ready', {}).get('ready_for_sync', False) if hasattr(processing_result, 'details') and processing_result.details else False
    }

    # Store in MongoDB
    result = await mongo_service.create_call(call_record)
    if result:
      logger.info(f"Classification results stored successfully: {result}",
                  extra={'task_id': task_id, 'call_id': webhook_payload.call_id})
    else:
      logger.error("Failed to store classification results",
                   extra={'task_id': task_id, 'call_id': webhook_payload.call_id})

  except Exception as e:
    logger.error(f"Error storing classification results: {e}",
                 extra={'task_id': task_id, 'call_id': webhook_payload.call_id},
                 exc_info=True)


async def _handle_hubspot_integration_bg(
    webhook_payload: BlandWebhookPayload,
    processing_result: Any,
    task_id: str
) -> None:
  """
  Handle HubSpot integration in background if data is ready.

  Args:
      webhook_payload: Original webhook payload
      processing_result: AI processing results
      task_id: Background task ID
  """
  try:
    call_id = webhook_payload.call_id

    # Check if HubSpot data is ready for sync
    if not hasattr(processing_result, 'details') or not processing_result.details:
      logger.info("No processing details available for HubSpot sync",
                  extra={'task_id': task_id, 'call_id': call_id})
      return

    hubspot_ready = processing_result.details.get('hubspot_ready', {})
    if not hubspot_ready.get('ready_for_sync', False):
      logger.info("Data not ready for HubSpot sync",
                  extra={'task_id': task_id, 'call_id': call_id})
      return

    extraction_data = processing_result.details.get('extraction', {})
    contact_props = extraction_data.get('contact_properties', {}) or {}
    lead_props = extraction_data.get('lead_properties', {}) or {}

    # Check if we have minimum required data
    has_email = bool(contact_props.get('email'))
    has_phone = bool(contact_props.get('phone'))

    if not (has_email or has_phone):
      logger.info("Insufficient contact data for HubSpot sync (no email or phone)",
                  extra={'task_id': task_id, 'call_id': call_id})
      return

    logger.info("Creating HubSpot contact and deal from AI-extracted data",
                extra={'task_id': task_id, 'call_id': call_id,
                       'has_email': has_email, 'has_phone': has_phone})

    # Note: Actual HubSpot integration would be implemented here
    # For now, we'll log the intent and structure
    logger.info("HubSpot integration ready - contact and deal creation would proceed",
                extra={'task_id': task_id, 'call_id': call_id,
                       'contact_fields': len([k for k, v in contact_props.items() if v]),
                       'lead_fields': len([k for k, v in lead_props.items() if v])})

  except Exception as e:
    logger.error(f"Error in HubSpot integration: {e}",
                 extra={'task_id': task_id, 'call_id': webhook_payload.call_id},
                 exc_info=True)


async def _store_error_result(
    webhook_payload: BlandWebhookPayload,
    error_message: str,
    task_id: str
) -> None:
  """
  Store error result when background processing fails.

  Args:
      webhook_payload: Original webhook payload
      error_message: Error message
      task_id: Background task ID
  """
  try:
    # Import locally to avoid circular imports
    from app.services.mongo import get_mongo_service

    mongo_service = await get_mongo_service()

    error_record = {
        'id': str(uuid.uuid4()),
        'background_task_id': task_id,
        'call_id': webhook_payload.call_id,
        'phone_number': webhook_payload.from_ or webhook_payload.to,
        'transcript': webhook_payload.concatenated_transcript or webhook_payload.summary,
        'processing_status': 'error',
        'error_message': error_message,
        'processed_at': datetime.utcnow(),
        'processing_version': '2.0'
    }

    await mongo_service.create_call(error_record)
    logger.info(f"Error result stored for call {webhook_payload.call_id}",
                extra={'task_id': task_id, 'call_id': webhook_payload.call_id})

  except Exception as e:
    logger.error(f"Failed to store error result: {e}",
                 extra={'task_id': task_id, 'call_id': webhook_payload.call_id},
                 exc_info=True)


async def get_classification_status_bg(call_id: str) -> Optional[Dict[str, Any]]:
  """
  Get classification status for a specific call.

  Args:
      call_id: Bland call ID

  Returns:
      Classification status dictionary or None if not found
  """
  try:
    # Import locally to avoid circular imports
    from app.services.mongo import get_mongo_service

    mongo_service = await get_mongo_service()

    # Query for the call record
    call_record = await mongo_service.get_call_by_id(call_id)

    if not call_record:
      return None

    return {
        'call_id': call_id,
        'processing_status': getattr(call_record, 'processing_status', 'unknown'),
        'lead_type': getattr(call_record, 'lead_type', None),
        'routing_suggestion': getattr(call_record, 'routing_suggestion', None),
        'requires_human_review': getattr(call_record, 'requires_human_review', None),
        'ready_for_sync': getattr(call_record, 'ready_for_sync', False),
        'processed_at': getattr(call_record, 'processed_at', None),
        'background_task_id': getattr(call_record, 'background_task_id', None)
    }

  except Exception as e:
    logger.error(f"Error getting classification status for call {call_id}: {e}",
                 exc_info=True)
    return None
