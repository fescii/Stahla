"""
Classification coordination service for voice call processing.

Coordinates AI and rule-based classification approaches for lead processing.
"""

from typing import Dict, Any, Optional
import logfire
from app.models.classification import ClassificationInput, ClassificationOutput, IntendedUseType
from app.services.classify.classification import ClassificationManager
from app.services.classify.marvin import MarvinClassificationManager


class ClassificationCoordinator:
  """
  Coordinates lead classification using AI or rule-based approaches.

  Handles the creation of classification input data and routing between
  different classification services.
  """

  def __init__(
      self,
      rule_classifier: ClassificationManager,
      marvin_classifier: MarvinClassificationManager
  ):
    self.logger = logfire
    self.rule_classifier = rule_classifier
    self.marvin_classifier = marvin_classifier

  async def perform_classification(
      self,
      transcript: str,
      extraction_result: Dict[str, Any],
      location_result: Dict[str, Any],
      use_ai_classification: bool = True
  ) -> Dict[str, Any]:
    """
    Perform lead classification using AI or rule-based approach.

    Args:
        transcript: Voice call transcript
        extraction_result: Extracted field data
        location_result: Location processing results
        use_ai_classification: Whether to use AI classification

    Returns:
        Dictionary containing classification results
    """
    try:
      self.logger.info("Starting lead classification",
                       use_ai=use_ai_classification,
                       transcript_length=len(transcript))

      # Prepare classification input
      classification_input = self._create_classification_input(
          transcript, extraction_result, location_result
      )

      # Perform classification
      if use_ai_classification:
        classification_output = await self._classify_with_ai(classification_input)
      else:
        classification_output = await self._classify_with_rules(classification_input)

      # Convert to standardized result format
      result = self._format_classification_result(
          classification_output, use_ai_classification
      )

      self.logger.info("Classification completed",
                       lead_type=result.get('lead_type'),
                       confidence=result.get('confidence'))

      return result

    except Exception as e:
      self.logger.error("Error in classification", error=str(e), exc_info=True)
      return self._create_error_result(str(e))

  def _create_classification_input(
      self,
      transcript: str,
      extraction_result: Dict[str, Any],
      location_result: Dict[str, Any]
  ) -> ClassificationInput:
    """
    Create classification input from extracted data.

    Args:
        transcript: Voice call transcript
        extraction_result: Extracted field data
        location_result: Location processing results

    Returns:
        ClassificationInput object
    """
    classification_data = extraction_result.get('classification_data', {})
    contact_data = extraction_result.get('contact_properties', {}) or {}
    lead_data = extraction_result.get('lead_properties', {}) or {}

    # Create summary for raw data
    transcript_summary = transcript[:500] + \
        '...' if len(transcript) > 500 else transcript

    return ClassificationInput(
        # Required core fields
        source="voice",
        raw_data={
            'full_transcript': transcript,
            'summary': transcript_summary,
            'call_data': classification_data
        },
        extracted_data=classification_data,
        intended_use=self._get_intended_use(classification_data, lead_data),
        is_local=location_result.get('is_local', False),
        is_in_service_area=location_result.get('is_local', False),

        # Contact information
        firstname=contact_data.get('firstname'),
        lastname=contact_data.get('lastname'),
        email=contact_data.get('email'),
        phone=contact_data.get('phone'),
        company=contact_data.get('company'),
        contact_name=contact_data.get('firstname'),
        company_name=contact_data.get('company'),
        contact_email=contact_data.get('email'),

        # Service requirements
        what_service_do_you_need_=classification_data.get('service_needed'),
        product_type_interest=classification_data.get('product_interest'),
        units_needed=str(classification_data.get('required_stalls', '')),
        how_many_portable_toilet_stalls_=classification_data.get(
            'required_stalls', 1),
        required_stalls=classification_data.get('required_stalls', 1),
        ada_required=classification_data.get('ada_required', False),
        shower_required=lead_data.get('shower_required', False),
        handwashing_needed=lead_data.get('handwashing_needed', False),
        additional_services_needed=classification_data.get(
            'additional_services', ""),

        # Event/Project details
        event_type=classification_data.get('event_type'),
        project_category=lead_data.get('project_category', "Other"),
        event_location_description=classification_data.get('location'),
        service_address=classification_data.get('location'),
        event_state=classification_data.get('state'),
        state=classification_data.get('state'),
        event_city=classification_data.get('city'),
        event_postal_code=classification_data.get('postal_code', ""),
        address_type=lead_data.get('address_type', "business"),
        event_location_type=lead_data.get('event_location_type', "business"),

        # Timing information
        start_date=classification_data.get('start_date'),
        end_date=classification_data.get('end_date'),
        duration_days=classification_data.get('duration_days'),
        guest_count=classification_data.get('guest_count'),
        expected_attendance=classification_data.get('guest_count', 0),
        rental_start_date=classification_data.get('start_date'),
        rental_end_date=classification_data.get('end_date'),

        # Site details with defaults
        delivery_surface=lead_data.get('delivery_surface', ""),
        site_ground_level=lead_data.get('site_ground_level', ""),
        site_ground_type=lead_data.get('site_ground_type', ""),
        delivery_obstacles=lead_data.get('delivery_obstacles', ""),
        site_obstacles=lead_data.get('site_obstacles', ""),

        # Utility requirements
        power_available=classification_data.get('power_available', False),
        water_available=classification_data.get('water_available', False),
        power_distance_feet=lead_data.get('power_distance_feet', 0),
        power_source_distance=lead_data.get('power_source_distance', ""),
        power_path_cross=lead_data.get('power_path_cross', ""),
        power_cord_ramps_needed=lead_data.get(
            'power_cord_ramps_needed', False),
        generator_needed=lead_data.get('generator_needed', False),
        water_distance_feet=lead_data.get('water_distance_feet', 0),
        water_source_distance=lead_data.get('water_source_distance', ""),
        water_path_cross=lead_data.get('water_path_cross', ""),
        water_hose_ramps_needed=lead_data.get(
            'water_hose_ramps_needed', False),

        # Logistics and facilities
        other_facilities_available=lead_data.get(
            'other_facilities_available', False),
        onsite_contact_different=lead_data.get(
            'onsite_contact_different', False),
        working_hours=lead_data.get('working_hours', ""),
        weekend_usage=lead_data.get('weekend_usage', False),
        duration_hours_per_day=lead_data.get('duration_hours_per_day', 8),

        # Consent and follow-up
        recording_consent_given=lead_data.get('recording_consent_given', True),
        contact_consent_given=lead_data.get('contact_consent_given', True),
        by_submitting_this_form_you_consent_to_receive_texts=lead_data.get(
            'by_submitting_this_form_you_consent_to_receive_texts', True
        ),
        follow_up_call_scheduled=lead_data.get(
            'follow_up_call_scheduled', False),
        referral_accepted=lead_data.get('referral_accepted', False),

        # Decision timeline
        decision_timeline=lead_data.get('decision_timeline', ""),
        decision_timing=lead_data.get('decision_timing', ""),
        quote_needed_by=lead_data.get('quote_needed_by', ""),
        quote_urgency=lead_data.get('quote_urgency', ""),

        # Financial information
        budget_mentioned=classification_data.get('budget_mentioned', "none"),

        # Call metadata
        call_summary=transcript_summary,
        call_recording_url=None,  # Will be set from webhook if available
        full_transcript=transcript
    )

  def _get_intended_use(self, classification_data: Dict[str, Any], lead_data: Dict[str, Any]) -> Optional[IntendedUseType]:
    """Get intended use from available data with fallback."""
    intended_use_value = (
        classification_data.get('intended_use') or
        lead_data.get('project_category')
    )

    # Map to valid IntendedUseType values
    if intended_use_value:
      value_lower = str(intended_use_value).lower()
      if 'small' in value_lower or 'event' in value_lower and 'large' not in value_lower:
        return "Small Event"
      elif 'large' in value_lower and 'event' in value_lower:
        return "Large Event"
      elif 'construction' in value_lower:
        return "Construction"
      elif 'disaster' in value_lower or 'relief' in value_lower:
        return "Disaster Relief"
      elif 'facility' in value_lower:
        return "Facility"

    return None  # Let the system handle default

  async def _classify_with_ai(self, classification_input: ClassificationInput) -> ClassificationOutput:
    """Perform AI-based classification using Marvin."""
    self.logger.info("Using AI classification with Marvin")
    return await self.marvin_classifier.get_lead_classification(classification_input)

  async def _classify_with_rules(self, classification_input: ClassificationInput) -> ClassificationOutput:
    """Perform rule-based classification."""
    self.logger.info("Using rule-based classification")
    classification_result = await self.rule_classifier.classify_lead_data(classification_input)

    if classification_result.status == "success" and classification_result.classification:
      return classification_result.classification
    else:
      # Create fallback classification output
      return ClassificationOutput(
          lead_type="Leads",
          reasoning=classification_result.message or "Rule-based classification failed",
          requires_human_review=True,
          routing_suggestion="Stahla Leads Team",
          confidence=0.0
      )

  def _format_classification_result(
      self,
      classification_output: ClassificationOutput,
      use_ai: bool
  ) -> Dict[str, Any]:
    """Format classification output to standardized dictionary."""
    return {
        'lead_type': classification_output.lead_type,
        'reasoning': classification_output.reasoning,
        'requires_human_review': classification_output.requires_human_review,
        'routing_suggestion': classification_output.routing_suggestion,
        'confidence': classification_output.confidence,
        'metadata': getattr(classification_output, 'metadata', {}),
        'classification_method': 'ai' if use_ai else 'rules'
    }

  def _create_error_result(self, error_message: str) -> Dict[str, Any]:
    """Create standardized error result for classification failures."""
    return {
        'lead_type': 'Leads',
        'reasoning': f'Classification error: {error_message}',
        'requires_human_review': True,
        'routing_suggestion': 'Stahla Leads Team',
        'confidence': 0.0,
        'classification_method': 'error_fallback'
    }


# Factory function for creating coordinator instances
def create_classification_coordinator(
    rule_classifier: ClassificationManager,
    marvin_classifier: MarvinClassificationManager
) -> ClassificationCoordinator:
  """Create a classification coordinator instance."""
  return ClassificationCoordinator(rule_classifier, marvin_classifier)
