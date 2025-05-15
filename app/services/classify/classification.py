# app/services/classification.py

import logfire
from typing import Optional, Tuple

# Import models
from app.models.classification import (
    ClassificationInput,
    ClassificationOutput,
    ClassificationResult,
    LeadClassificationType,
    IntendedUseType,
    ProductType
)
from app.core.config import settings  # Import settings for threshold
from app.services.classify.rules import classify_lead
from app.services.classify.marvin import marvin_classification_manager
from app.utils.location import determine_locality_from_description


class ClassificationManager:
  """
  Manages the classification of leads based on input data.
  Applies rules defined in the PRD and call script.
  """

  def _determine_locality(self,
                          location_description: Optional[str] = None,
                          state_code: Optional[str] = None,
                          city: Optional[str] = None,
                          postal_code: Optional[str] = None) -> bool:
    """
    Determine if a location is local based on drive time from key service hubs.
    Local is defined as ≤ 3 hours from Omaha NE, Denver CO, or Kansas City KS.

    Args:
        location_description: Text description of the location (e.g., event_address)
        state_code: Two-letter state code (e.g., 'NY', 'CO') if available
        city: City name if available
        postal_code: Postal/ZIP code if available
    """
    # Import enhanced location utils that support all location fields
    from app.utils.location import determine_locality_from_description
    return determine_locality_from_description(
        location_description=location_description,
        state_code=state_code,
        city=city,
        postal_code=postal_code
    )

  def _estimate_deal_value(self, input_data: ClassificationInput) -> float:
    """
    Estimate deal value based on product type, stalls, and duration.
    Used for prioritization and routing decisions.
    NOTE: Call script advises against estimating budget. This estimation is internal.
    """
    value = 0.0

    # Base values by product type
    if input_data.product_interest:
      product_interest_lower = [p.lower() for p in input_data.product_interest]

      # Specialty trailers have higher base values
      if any("trailer" in p for p in product_interest_lower):
        if any("restroom" in p for p in product_interest_lower):
          value += 7500  # Restroom trailer base value
        elif any("shower" in p for p in product_interest_lower):
          value += 8500  # Shower trailer base value
        elif any("ada" in p for p in product_interest_lower):
          value += 9000  # ADA trailer base value
        else:
          value += 7000  # Generic trailer base value

      # Porta potties and handwashing stations have lower base values
      if any("toilet" in p or "potty" in p for p in product_interest_lower):
        value += 500  # Base value for porta potty
      if any("handwashing" in p or "wash" in p for p in product_interest_lower):
        value += 300  # Base value for handwashing station

    # Scale by quantity and duration
    # Use number_of_stalls (which might have been populated by alias stall_count)
    current_stall_count = getattr(
        input_data, 'number_of_stalls', getattr(input_data, 'required_stalls', None))
    if current_stall_count:
      # Higher stall counts increase value proportionally
      if current_stall_count >= 20:
        value *= 2.5  # Significant increase for large quantities
      elif current_stall_count >= 10:
        value *= 1.8  # Moderate increase for medium quantities
      elif current_stall_count >= 5:
        value *= 1.4  # Small increase for smaller quantities

    current_duration_days = getattr(input_data, 'duration_days', None)
    if current_duration_days:
      # Longer durations significantly increase value
      if current_duration_days >= 30:
        value *= 3.0  # Monthly rental factor
      elif current_duration_days >= 14:
        value *= 2.0  # Two-week rental factor
      elif current_duration_days >= 7:
        value *= 1.5  # One-week rental factor
      elif current_duration_days >= 3:
        value *= 1.2  # Weekend rental factor

    logfire.info(f"Estimated deal value: ${value:.2f}",
                 product_interest=getattr(
        input_data, 'product_interest', None),
        stalls=current_stall_count,  # Use the resolved stall count
        duration=current_duration_days)

    return value

  async def classify_lead_data(self, input_data: ClassificationInput) -> ClassificationResult:
    """
    Classifies the lead based on the provided input data using the defined business rules.
    """
    logfire.info("Starting lead classification.",
                 input_source=input_data.source)

    # If intended_use is not explicitly set, try to infer it from what_service_do_you_need_ or event_type
    if not getattr(input_data, 'intended_use', None) and \
       (getattr(input_data, 'what_service_do_you_need_', None) or getattr(input_data, 'event_type', None)):
      source_text = (
          getattr(input_data, 'what_service_do_you_need_', None) or
          getattr(input_data, 'event_type', None) or "").lower()

      # Simple mapping based on keywords (could be more sophisticated)
      if "small" in source_text and "event" in source_text:
        input_data.intended_use = "Small Event"
      elif "large" in source_text and "event" in source_text:
        input_data.intended_use = "Large Event"
      elif "disaster" in source_text or "emergency" in source_text or "relief" in source_text:
        input_data.intended_use = "Disaster Relief"
      elif "construction" in source_text or "job site" in source_text or "work site" in source_text:
        input_data.intended_use = "Construction"
      elif "facility" in source_text or "building" in source_text or "supplement" in source_text:
        input_data.intended_use = "Facility"
      elif "event" in source_text or "wedding" in source_text or "festival" in source_text:
        # Default to Small Event if just "event" is mentioned without size specification
        input_data.intended_use = "Small Event"

    # Determine locality if not already set
    if getattr(input_data, 'is_local', None) is None:  # Check is_local first
      input_data.is_local = self._determine_locality(
          location_description=getattr(input_data, 'service_address', getattr(
              input_data, 'event_location_description', None)),
          state_code=getattr(input_data, 'state', getattr(
              input_data, 'event_state', None)),
          city=getattr(input_data, 'city', getattr(
              input_data, 'event_city', None)),
          postal_code=getattr(input_data, 'zip', getattr(
              input_data, 'event_postal_code', None))
      )

    try:
      # Use Marvin for classification if enabled in settings
      if settings.LLM_PROVIDER.lower() == "marvin" and settings.MARVIN_API_KEY:
        # --- Update call to handle ClassificationOutput ---
        classification_output: ClassificationOutput = await marvin_classification_manager.get_lead_classification(input_data)
        classification = classification_output.lead_type
        reasoning = classification_output.reasoning
        # Extract owner_team from metadata if present
        owner_team = classification_output.metadata.get(
            "assigned_owner_team", "None")
        # --- End Update ---
        logfire.info("Using Marvin for lead classification",
                     classification=classification)
      else:
        # Fall back to rule-based classification if Marvin is not configured
        classification, reasoning, owner_team = classify_lead(input_data)
        logfire.info("Using rule-based classification (Marvin not enabled)",
                     classification=classification)

      # Set pipeline based on classification
      if classification == "Services":
        assigned_pipeline = "Stahla Services Pipeline"
      elif classification == "Logistics":
        assigned_pipeline = "Stahla Logistics Pipeline"
      elif classification == "Leads":
        assigned_pipeline = "Stahla Leads Pipeline"
      else:
        assigned_pipeline = None  # No pipeline for Disqualify

      # Calculate confidence score (could be more sophisticated)
      confidence = 0.95  # High confidence for most cases
      requires_review = False

      # Lower confidence if key fields are missing
      if not input_data.intended_use:
        confidence -= 0.15
        requires_review = True
      if not input_data.product_interest:
        confidence -= 0.15
        requires_review = True

      # Use number_of_stalls (populated by alias stall_count) or fallback to required_stalls
      current_stall_count_for_confidence = getattr(
          input_data, 'number_of_stalls', getattr(input_data, 'required_stalls', None))
      if not current_stall_count_for_confidence:
        confidence -= 0.05

      if not getattr(input_data, 'duration_days', None):
        confidence -= 0.05
      if getattr(input_data, 'is_local', None) is None:
        confidence -= 0.05

      # Estimate deal value (internal use only, not setting HubSpot 'amount')
      estimated_value = self._estimate_deal_value(input_data)

      # Store additional metadata, using HubSpot internal property names where possible
      # or clear, descriptive keys for internal use.
      metadata = {
          # Classification-derived fields
          "assigned_owner_team": owner_team,
          "estimated_value": estimated_value,
          "has_complete_info": confidence > 0.8,
          "qualification_notes": reasoning,

          # Fields from ClassificationInput, mapped to HubSpot internal names or descriptive keys
          "is_local": getattr(input_data, 'is_local', None),
          "within_local_service_area": getattr(input_data, 'is_in_service_area', None),
          "intended_use": getattr(input_data, 'intended_use', None),
          # Mapping from general intended_use
          "ai_intended_use": getattr(input_data, 'intended_use', None),

          # Contact related info
          "firstname": getattr(input_data, 'firstname', None),
          "lastname": getattr(input_data, 'lastname', None),
          "email": getattr(input_data, 'email', None),
          "phone": getattr(input_data, 'phone', None),
          "company": getattr(input_data, 'company', None),

          # Service and Product Details
          "what_service_do_you_need_": getattr(input_data, 'what_service_do_you_need_', None),
          "product_type_interest": getattr(input_data, 'product_type_interest', None),
          "units_needed": getattr(input_data, 'units_needed', None),
          "how_many_portable_toilet_stalls_": getattr(input_data, 'how_many_portable_toilet_stalls_', None),
          "how_many_restroom_stalls_": getattr(input_data, 'how_many_restroom_stalls_', None),
          "how_many_shower_stalls_": getattr(input_data, 'how_many_shower_stalls_', None),
          "how_many_laundry_units_": getattr(input_data, 'how_many_laundry_units_', None),
          "number_of_stalls": getattr(input_data, 'number_of_stalls', getattr(input_data, 'required_stalls', None)),
          "ada_required": getattr(input_data, 'ada_required', None),
          "shower_required": getattr(input_data, 'shower_required', None),
          "handwashing_needed": getattr(input_data, 'handwashing_needed', None),
          "additional_services_needed": getattr(input_data, 'additional_services_needed', None),

          # Event/Project Details
          "project_category": getattr(input_data, 'project_category', getattr(input_data, 'event_type', None)),
          "event_type": getattr(input_data, 'event_type', None),
          "event_or_job_address": getattr(input_data, 'service_address', getattr(input_data, 'event_location_description', None)),
          "service_address": getattr(input_data, 'service_address', None),
          "address": getattr(input_data, 'service_address', getattr(input_data, 'event_location_description', None)),
          "city": getattr(input_data, 'city', getattr(input_data, 'event_city', None)),
          "state": getattr(input_data, 'state', getattr(input_data, 'event_state', None)),
          "zip": getattr(input_data, 'zip', getattr(input_data, 'event_postal_code', None)),
          "address_type": getattr(input_data, 'address_type', None),
          "site_ground_type": getattr(input_data, 'site_ground_type', getattr(input_data, 'delivery_surface', None)),
          "site_ground_level": getattr(input_data, 'site_ground_level', None),
          "site_obstacles": getattr(input_data, 'site_obstacles', getattr(input_data, 'delivery_obstacles', None)),

          # Timing Information
          "event_start_date": getattr(input_data, 'rental_start_date', getattr(input_data, 'start_date', None)),
          "event_end_date": getattr(input_data, 'rental_end_date', getattr(input_data, 'end_date', None)),
          "rental_start_date": getattr(input_data, 'rental_start_date', getattr(input_data, 'start_date', None)),
          "rental_end_date": getattr(input_data, 'rental_end_date', getattr(input_data, 'end_date', None)),
          "event_duration_days": getattr(input_data, 'duration_days', None),

          # Attendance & Usage
          "expected_attendance": getattr(input_data, 'expected_attendance', getattr(input_data, 'guest_count', None)),
          "guest_count_estimate": getattr(input_data, 'guest_count', None),
          "onsite_facilities": getattr(input_data, 'other_facilities_available', None),
          "site_working_hours": getattr(input_data, 'working_hours', None),
          "weekend_service_needed": getattr(input_data, 'weekend_usage', None),

          # Utility Information
          "do_you_have_power_access_onsite_": getattr(input_data, 'power_available', None),
          "do_you_have_water_access_onsite_": getattr(input_data, 'water_available', None),
          "power_source_distance": getattr(input_data, 'power_source_distance', None),
          "water_source_distance": getattr(input_data, 'water_source_distance', None),
          "power_path_cross": getattr(input_data, 'power_path_cross', None),
          "water_path_cross": getattr(input_data, 'water_path_cross', None),

          # Consent & Follow-up
          "by_submitting_this_form_you_consent_to_receive_texts": getattr(input_data, 'by_submitting_this_form_you_consent_to_receive_texts', None),
          "partner_referral_consent": getattr(input_data, 'referral_accepted', None),
          "recording_consent_given": getattr(input_data, 'recording_consent_given', None),
          "contact_consent_given": getattr(input_data, 'contact_consent_given', None),
          "follow_up_call_scheduled": getattr(input_data, 'follow_up_call_scheduled', None),

          # Decision and Quoting
          "quote_urgency": getattr(input_data, 'quote_urgency', getattr(input_data, 'quote_needed_by', None)),
          "decision_timeline": getattr(input_data, 'decision_timeline', getattr(input_data, 'decision_timing', None)),

          # Call Details
          "call_summary": getattr(input_data, 'call_summary', None),
          "call_recording_url": str(getattr(input_data, 'call_recording_url', None)) if getattr(input_data, 'call_recording_url', None) else None,
          "full_transcript": getattr(input_data, 'full_transcript', None),
          "call_duration_seconds": getattr(input_data, 'call_duration_seconds', None),
      }
      # Merge metadata from Marvin classification if it exists and it's enabled
      if settings.LLM_PROVIDER.lower() == "marvin" and settings.MARVIN_API_KEY and classification_output and classification_output.metadata:
        metadata.update(classification_output.metadata)
      # --- End Update ---

      # Prepare output
      output = ClassificationOutput(
          lead_type=classification,
          reasoning=reasoning,
          confidence=confidence,
          routing_suggestion=assigned_pipeline,
          requires_human_review=requires_review,
          metadata=metadata
      )

    except Exception as e:
      # --- Add more specific error logging ---
      error_type = type(e).__name__
      error_message = str(e)
      logfire.error(
          "Error caught during classification process",
          error_type=error_type,
          error_message=error_message,
          exc_info=True,  # Ensure traceback is logged
          input_data_summary={f: getattr(input_data, f, None) for f in [
              'source', 'email', 'phone', 'intended_use', 'is_local',
              'product_interest', 'stall_count', 'duration_days'
          ]}  # Log key input fields
      )  # --- End specific error logging ---

      # Default output on error
      output = ClassificationOutput(
          lead_type="Leads",  # Default to Leads on error for human review
          reasoning=f"Error during classification: {error_message}",
          confidence=0.3,  # Low confidence when error occurs
          routing_suggestion=None,  # Explicitly provide routing_suggestion as None
          requires_human_review=True,
          metadata={"error": error_message, "error_type": error_type}
      )

    logfire.info("Classification complete.",
                 classification=output.lead_type,
                 reasoning=output.reasoning,
                 confidence=output.confidence)

    return ClassificationResult(status="success", classification=output)


# Create a singleton instance of the manager
classification_manager = ClassificationManager()
