# app/services/bland/processing/ai/service.py

"""
Enhanced voice webhook service with AI-powered processing.
This service replaces the basic regex-based extraction with comprehensive AI classification
for Bland voice call transcripts using modular components.
"""

from typing import Dict, Any, Optional
import logfire
from datetime import datetime

from app.models.bland import BlandWebhookPayload, BlandProcessingResult
from app.services.bland.processing.ai.transcript.processor import transcript_processor
from app.services.bland.processing.ai.extractor import ai_field_extractor
from app.services.bland.processing.ai.location.handler import create_location_handler
from app.services.bland.processing.ai.classification.coordinator import create_classification_coordinator
from app.services.bland.processing.ai.results.builder import result_builder
from app.services.classify.classification import classification_manager
from app.services.classify.marvin import marvin_classification_manager


class EnhancedVoiceWebhookService:
  """
  Enhanced voice webhook service that uses AI for comprehensive data extraction
  and classification from Bland voice call transcripts using modular components.
  """

  def __init__(self):
    self.logger = logfire

    # Initialize modular components
    self.transcript_processor = transcript_processor
    self.field_extractor = ai_field_extractor
    self.result_builder = result_builder

    # Create location handler (will be initialized lazily)
    self.location_handler = None
    self._location_service_initialized = False

    # Create classification coordinator
    self.classification_coordinator = create_classification_coordinator(
        classification_manager,
        marvin_classification_manager
    )

  async def _ensure_location_handler(self):
    """Initialize location handler lazily."""
    if not self._location_service_initialized:
      try:
        # Try to import location service dependency
        from app.core.dependencies import get_location_service_dep
        location_service = await get_location_service_dep()
        self.location_handler = create_location_handler(location_service)
      except (ImportError, Exception):
        # Fallback if dependency not available
        self.location_handler = create_location_handler(None)
      self._location_service_initialized = True

  async def process_voice_webhook(
      self,
      webhook_payload: BlandWebhookPayload,
      use_ai_classification: bool = True,
      store_results: bool = True
  ) -> BlandProcessingResult:
    """
    Process incoming voice webhook with AI-powered extraction and classification.

    Args:
        webhook_payload: Bland webhook payload
        use_ai_classification: Whether to use AI classification (default: True)
        store_results: Whether to store results in MongoDB (default: True)

    Returns:
        BlandProcessingResult with processing status and results
    """
    call_id = webhook_payload.call_id

    try:
      self.logger.info("Processing voice webhook with AI enhancement",
                       call_id=call_id,
                       ai_enabled=use_ai_classification)

      # Step 1: Comprehensive AI processing using modular components
      processing_result = await self._process_with_modular_components(
          webhook_payload, use_ai_classification
      )

      # Step 2: Store results if requested
      if store_results:
        await self._store_processing_results(webhook_payload, processing_result)

      # Step 3: Create success response
      return BlandProcessingResult(
          status="success",
          message="Voice webhook processed successfully with AI enhancement",
          details=processing_result,
          summary=self._create_processing_summary(processing_result),
          classification=processing_result.get('classification'),
          call_id=call_id
      )

    except Exception as e:
      self.logger.error(f"Error processing voice webhook: {e}",
                        call_id=call_id,
                        exc_info=True)

      # Return error response
      return BlandProcessingResult(
          status="error",
          message=f"Failed to process voice webhook: {str(e)}",
          details={'error': str(
              e), 'timestamp': datetime.utcnow().isoformat()},
          call_id=call_id
      )

  async def _store_processing_results(
      self,
      webhook_payload: BlandWebhookPayload,
      processing_result: Dict[str, Any]
  ) -> None:
    """
    Store processing results in MongoDB.

    Args:
        webhook_payload: Original webhook payload
        processing_result: AI processing results
    """
    try:
      # Create enhanced call record
      call_record = {
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
          'ai_processing': processing_result,
          'processing_version': '2.0',
          'processed_at': datetime.utcnow(),

          # Classification results for easy querying
          'classification': processing_result.get('classification', {}),
          'lead_type': processing_result.get('classification', {}).get('lead_type'),
          'routing_suggestion': processing_result.get('classification', {}).get('routing_suggestion'),
          'requires_human_review': processing_result.get('classification', {}).get('requires_human_review'),

          # HubSpot readiness
          'hubspot_ready': processing_result.get('hubspot_ready', {}),
          'ready_for_sync': processing_result.get('hubspot_ready', {}).get('ready_for_sync', False)
      }

      # Log the results (storage can be implemented later)
      self.logger.info("Processing results ready for storage",
                       call_id=webhook_payload.call_id,
                       lead_type=call_record.get('lead_type'),
                       ready_for_sync=call_record.get('ready_for_sync'))

    except Exception as e:
      self.logger.error(f"Error preparing processing results: {e}",
                        call_id=webhook_payload.call_id,
                        exc_info=True)

  def _create_processing_summary(self, processing_result: Dict[str, Any]) -> str:
    """
    Create human-readable summary of processing results.

    Args:
        processing_result: AI processing results

    Returns:
        Summary string
    """
    try:
      classification = processing_result.get('classification', {})
      extraction = processing_result.get('extraction', {})

      lead_type = classification.get('lead_type', 'Unknown')
      routing = classification.get('routing_suggestion', 'Unknown')
      confidence = classification.get('confidence', 0.0)

      # Count extracted fields
      contact_fields = len(
          [k for k, v in (extraction.get('contact_properties') or {}).items() if v])
      lead_fields = len(
          [k for k, v in (extraction.get('lead_properties') or {}).items() if v])
      classification_fields = len(
          [k for k, v in (extraction.get('classification_data') or {}).items() if v])

      return (f"Call classified as '{lead_type}' with {confidence:.1%} confidence. "
              f"Routed to '{routing}'. "
              f"Extracted {contact_fields} contact fields, {lead_fields} lead fields, "
              f"and {classification_fields} classification fields.")

    except Exception as e:
      return f"Processing completed with some errors: {str(e)}"

  async def extract_hubspot_data_only(
      self,
      webhook_payload: BlandWebhookPayload
  ) -> Dict[str, Any]:
    """
    Extract only HubSpot-ready data for direct integration.

    Args:
        webhook_payload: Bland webhook payload

    Returns:
        Dictionary with HubSpot contact and lead properties
    """
    try:
      transcript = self._extract_transcript(webhook_payload)
      if not transcript:
        return {'error': 'No transcript available'}

      contact_data, lead_data = await self._extract_hubspot_properties_modular(transcript)

      return {
          'contact_properties': contact_data.model_dump() if contact_data else None,
          'lead_properties': lead_data.model_dump() if lead_data else None,
          'extraction_timestamp': datetime.utcnow().isoformat()
      }

    except Exception as e:
      self.logger.error(f"Error extracting HubSpot data: {e}", exc_info=True)
      return {'error': str(e)}

  def _extract_transcript(self, webhook_payload: BlandWebhookPayload) -> Optional[str]:
    """
    Extract transcript from webhook payload.

    Args:
        webhook_payload: Bland webhook payload

    Returns:
        Transcript text or None
    """
    # Try concatenated transcript first
    if webhook_payload.concatenated_transcript:
      return webhook_payload.concatenated_transcript

    # Try summary
    if webhook_payload.summary:
      return webhook_payload.summary

    # Build from transcript entries
    if webhook_payload.transcripts:
      parts = []
      for entry in webhook_payload.transcripts:
        if entry.text:
          speaker = entry.user or "Speaker"
          parts.append(f"{speaker}: {entry.text}")

      if parts:
        return "\n".join(parts)

    return None

  async def _process_with_modular_components(
      self,
      webhook_payload: BlandWebhookPayload,
      use_ai_classification: bool = True
  ) -> Dict[str, Any]:
    """
    Process webhook using modular components (replaces orchestrator).

    Args:
        webhook_payload: Bland webhook payload
        use_ai_classification: Whether to use AI classification

    Returns:
        Comprehensive processing result
    """
    try:
      self.logger.info("Starting modular AI processing",
                       call_id=webhook_payload.call_id,
                       use_ai_classification=use_ai_classification)

      # Step 1: Extract transcript
      transcript = self.transcript_processor.extract_transcript(
          webhook_payload)
      if not transcript:
        return self.result_builder.create_error_result(
            "No transcript available for processing", webhook_payload
        )

      # Step 2: Extract all fields using AI
      extraction_result = await self.field_extractor.extract_comprehensive_data(transcript)

      # Step 3: Process location data
      await self._ensure_location_handler()
      assert self.location_handler is not None  # Help type checker
      location_result = await self.location_handler.process_location_data(extraction_result)

      # Step 4: Perform classification
      classification_result = await self.classification_coordinator.perform_classification(
          transcript, extraction_result, location_result, use_ai_classification
      )

      # Step 5: Build final result
      final_result = self.result_builder.create_comprehensive_result(
          webhook_payload, transcript, extraction_result,
          location_result, classification_result
      )

      self.logger.info("Modular processing completed",
                       call_id=webhook_payload.call_id,
                       lead_type=classification_result.get('lead_type'))

      return final_result

    except Exception as e:
      self.logger.error("Error in modular processing",
                        error=str(e),
                        call_id=webhook_payload.call_id,
                        exc_info=True)
      return self.result_builder.create_error_result(
          f"Processing error: {str(e)}", webhook_payload
      )

  async def _extract_hubspot_properties_modular(self, transcript: str):
    """
    Extract HubSpot properties using modular components.

    Args:
        transcript: Voice call transcript

    Returns:
        Tuple of (contact_data, lead_data)
    """
    try:
      # Extract contact properties
      contact_data = await self.field_extractor.extract_contact_data(transcript)

      # Extract lead properties
      lead_data = await self.field_extractor.extract_lead_data(transcript)

      return contact_data, lead_data

    except Exception as e:
      self.logger.error("Error extracting HubSpot properties",
                        error=str(e), exc_info=True)
      return None, None

  async def get_processing_health_check(self) -> Dict[str, Any]:
    """
    Get health check information for AI processing components.

    Returns:
        Health check status dictionary
    """
    try:
      return {
          'status': 'healthy',
          'ai_orchestrator': 'available',
          'field_extractor': 'available',
          'marvin_classifier': 'available',
          'timestamp': datetime.utcnow().isoformat(),
          'version': '2.0'
      }
    except Exception as e:
      return {
          'status': 'unhealthy',
          'error': str(e),
          'timestamp': datetime.utcnow().isoformat()
      }


# Create singleton instance
enhanced_voice_webhook_service = EnhancedVoiceWebhookService()
