"""Transcript processing functionality."""

import logfire
from datetime import datetime, timezone
from app.models.bland import BlandWebhookPayload, BlandProcessingResult
from app.models.blandlog import BlandCallStatus
from app.services.mongo.mongo import MongoService
from ..processing import extract_data_from_transcript


class BlandTranscriptProcessor:
  """Processes incoming transcripts from Bland AI webhooks."""

  def __init__(self, mongo_service: MongoService):
    self.mongo_service = mongo_service

  async def process_incoming_transcript(
      self,
      payload: BlandWebhookPayload
  ) -> BlandProcessingResult:
    """
    Processes the incoming transcript from the Bland.ai webhook.
    Extracts data, logs to MongoDB, and potentially triggers further actions.
    """
    logfire.info(
        f"Processing incoming transcript for call_id: {payload.call_id}"
    )

    # Extract data from the transcript
    # Convert BlandTranscriptEntry objects to dict format for processing
    transcripts_as_dict = []
    if payload.transcripts:
      transcripts_as_dict = [
          transcript.model_dump() if hasattr(transcript, 'model_dump') else dict(transcript)
          for transcript in payload.transcripts
      ]

    processing_result = extract_data_from_transcript(transcripts_as_dict)

    contact_id_from_meta = (
        payload.metadata.get("contact_id") if payload.metadata else None
    )
    if not contact_id_from_meta:
      logfire.error(
          f"Webhook for call_id {payload.call_id} missing 'contact_id' in metadata. Cannot update log.",
          metadata=payload.metadata,
      )
      # Log this as a critical error to a general error log if possible
      # For now, we can't associate it with a specific contact_id log entry.
      return BlandProcessingResult(
          status="error",
          message="Missing contact_id in webhook metadata.",
          details={"extracted_data": {}},
      )

    # Log the processed data and update call status in MongoDB
    # Use the new method name: update_bland_call_log_completion
    # Ensure all required arguments are passed
    update_success = False
    if self.mongo_service is not None:
      update_success = await self.mongo_service.update_bland_call_log_completion(
          contact_id=contact_id_from_meta,
          call_id_bland=payload.call_id or "",
          status=BlandCallStatus.COMPLETED,  # Changed to use existing enum member
          transcript_payload=transcripts_as_dict,  # Pass the converted transcripts
          summary_text=processing_result.summary,
          classification_payload=processing_result.classification,
          full_webhook_payload=payload.model_dump(
              mode='json'),  # Ensure BSON-compatible types
          call_completed_timestamp=(
              payload.completed_at if isinstance(payload.completed_at, datetime)
              else datetime.fromisoformat(payload.completed_at) if isinstance(payload.completed_at, str)
              else datetime.now(timezone.utc)
          ),
          bland_processing_result_payload=processing_result.model_dump(
              mode='json'),  # Ensure BSON-compatible types
          processing_status_message=processing_result.message
      )
    else:
      logfire.error(
          f"MongoService is not available; cannot update MongoDB log for call_id: {payload.call_id}, contact_id: {contact_id_from_meta}."
      )

    if not update_success:
      logfire.warning(
          f"Failed to update MongoDB log for call_id: {payload.call_id}, contact_id: {contact_id_from_meta}."
      )
      # The update_bland_call_log_completion method should log its own errors.
      # We might want to return a specific status if DB update fails but processing was ok.

    if processing_result.status == "success":
      logfire.info(
          f"Successfully processed transcript for call_id: {payload.call_id}"
      )
    else:
      logfire.error(
          f"Error processing transcript for call_id: {payload.call_id}. Message: {processing_result.message}"
      )

    # Placeholder for further actions (e.g., notifying other services)

    return processing_result
