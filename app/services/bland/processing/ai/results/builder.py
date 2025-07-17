"""
Result building service for comprehensive voice call processing.

Combines extracted data, location results, and classification into final results.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from app.models.bland import BlandWebhookPayload


class ResultBuilder:
  """
  Builds comprehensive processing results from component outputs.

  Combines data from transcript processing, field extraction, location processing,
  and classification into a unified result format.
  """

  def create_comprehensive_result(
      self,
      webhook_payload: BlandWebhookPayload,
      transcript: str,
      extraction_result: Dict[str, Any],
      location_result: Dict[str, Any],
      classification_result: Dict[str, Any]
  ) -> Dict[str, Any]:
    """
    Create comprehensive processing result combining all data.

    Args:
        webhook_payload: Original webhook payload
        transcript: Extracted transcript
        extraction_result: Field extraction results
        location_result: Location processing results
        classification_result: Classification results

    Returns:
        Comprehensive result dictionary
    """
    return {
        # Original call metadata
        'call_data': self._build_call_data(webhook_payload),

        # AI extraction results
        'extraction': self._build_extraction_data(extraction_result),

        # Location processing results
        'location': location_result,

        # Classification results
        'classification': classification_result,

        # Processing metadata
        'processing': self._build_processing_metadata(webhook_payload, transcript),

        # Full transcript for reference
        'transcript': transcript,

        # Overall status
        'status': 'success',
        'processing_version': 'ai_comprehensive_v1'
    }

  def create_error_result(self, error_message: str, webhook_payload: Optional[BlandWebhookPayload] = None) -> Dict[str, Any]:
    """
    Create a standardized error result.

    Args:
        error_message: Description of the error
        webhook_payload: Optional webhook payload for context

    Returns:
        Error result dictionary
    """
    result = {
        'status': 'error',
        'error': error_message,
        'extraction': {
            'contact_properties': {},
            'lead_properties': {},
            'structured_data': {},
            'extraction_success': False
        },
        'location': {
            'location': None,
            'is_local': False,
            'processing_success': False
        },
        'classification': {
            'lead_type': 'Leads',
            'reasoning': f'Processing failed: {error_message}',
            'requires_human_review': True,
            'routing_suggestion': 'Stahla Leads Team',
            'confidence': 0.0,
            'classification_method': 'error_fallback'
        },
        'transcript': None,
        'processing_version': 'ai_comprehensive_v1'
    }

    # Add call data if webhook payload is available
    if webhook_payload:
      result['call_data'] = self._build_call_data(webhook_payload)

    return result

  def _build_call_data(self, webhook_payload: BlandWebhookPayload) -> Dict[str, Any]:
    """Build call data section from webhook payload."""
    return {
        'call_id': webhook_payload.call_id,
        'phone_number': webhook_payload.from_ or webhook_payload.to,
        'call_duration': webhook_payload.call_length,
        'call_status': webhook_payload.status,
        'completed_at': webhook_payload.completed_at,
        'inbound': webhook_payload.inbound,
        'pathway_id': getattr(webhook_payload, 'pathway_id', None),
        'batch_id': getattr(webhook_payload, 'batch_id', None)
    }

  def _build_extraction_data(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build extraction data section."""
    return {
        'contact_properties': extraction_result.get('contact_properties', {}),
        'lead_properties': extraction_result.get('lead_properties', {}),
        'structured_data': extraction_result.get('classification_data', {}),
        'extraction_success': extraction_result.get('extraction_success', False),
        'extraction_error': extraction_result.get('extraction_error')
    }

  def _build_processing_metadata(self, webhook_payload: BlandWebhookPayload, transcript: str) -> Dict[str, Any]:
    """Build processing metadata section."""
    return {
        'transcript_length': len(transcript) if transcript else 0,
        'transcript_extracted': bool(transcript),
        'processing_timestamp': datetime.now().isoformat(),
        'webhook_completed_at': webhook_payload.completed_at,
        'processing_components': [
            'transcript_extraction',
            'ai_field_extraction',
            'location_processing',
            'classification'
        ]
    }


# Create global instance
result_builder = ResultBuilder()
