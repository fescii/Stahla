# app/api/v1/endpoints/webhooks/util/prepare/service.py

from typing import Dict, Any, Optional, List

from app.models.classification import ClassificationInput


def prepare_classification_input(
    source: str,
    raw_data: Dict[str, Any],
    extracted_data: Dict[str, Any]
) -> ClassificationInput:
  """
  Prepares a ClassificationInput object from source, raw_data, and extracted_data.
  Maps common field names from extracted_data to ClassificationInput model fields.
  """
  # Create a base input dictionary with the required fields
  input_dict = {
      "source": source,
      "raw_data": raw_data,
      "extracted_data": extracted_data,

      # Initialize all required fields with None or empty defaults
      "intended_use": None,
      "is_local": None,
      "is_in_service_area": None,
      "firstname": None,
      "lastname": None,
      "email": None,
      "phone": None,
      "company": None,
      "contact_name": None,
      "company_name": None,
      "contact_email": None,
      "what_service_do_you_need_": None,
      "product_type_interest": None,
      "units_needed": None,
      "how_many_portable_toilet_stalls_": None,
      "required_stalls": None,
      "ada_required": None,
      "shower_required": None,
      "handwashing_needed": None,
      "additional_services_needed": None,
      "event_type": None,
      "project_category": None,
      "event_location_description": None,
      "service_address": None,
      "event_state": None,
      "state": None,
      "event_city": None,
      "event_postal_code": None,
      "address_type": None,
      "event_location_type": None,
      "delivery_surface": None,
      "site_ground_level": None,
      "site_ground_type": None,
      "delivery_obstacles": None,
      "site_obstacles": None,
      "duration_days": None,
      "duration_hours_per_day": None,
      "start_date": None,
      "end_date": None,
      "rental_start_date": None,
      "rental_end_date": None,
      "guest_count": None,
      "expected_attendance": None,
      "other_facilities_available": None,
      "onsite_contact_different": None,
      "working_hours": None,
      "weekend_usage": None,
      "power_available": None,
      "power_distance_feet": None,
      "power_source_distance": None,
      "power_path_cross": None,
      "power_cord_ramps_needed": None,
      "generator_needed": None,
      "water_available": None,
      "water_distance_feet": None,
      "water_source_distance": None,
      "water_path_cross": None,
      "water_hose_ramps_needed": None,
      "recording_consent_given": None,
      "contact_consent_given": None,
      "by_submitting_this_form_you_consent_to_receive_texts": None,
      "follow_up_call_scheduled": None,
      "referral_accepted": None,
      "budget_mentioned": None,
      "decision_timeline": None,
      "decision_timing": None,
      "quote_needed_by": None,
      "quote_urgency": None,
      "call_summary": None,
      "call_recording_url": None,
      "full_transcript": None,
      "product_interest": []
  }

  classification_input = ClassificationInput(**input_dict)

  # Map fields from extracted_data to ClassificationInput fields
  field_mapping = {
      # Basic contact fields
      "firstname": "firstname",
      "lastname": "lastname",
      "email": "email",
      "phone": "phone",
      "company": "company",
      "company_name": "company",
      "message": "message",
      "comments": "message",

      # Service and product interest fields
      "product_interest": "product_interest",
      "service_needed": "service_needed",
      "what_service_do_you_need_": "what_service_do_you_need_",

      # Location fields
      "event_address": "event_address",
      "event_or_job_address": "event_address",
      "service_address": "service_address",
      "event_city": "event_city",
      "city": "event_city",
      "event_state": "event_state",
      "state": "event_state",
      "event_postal_code": "event_postal_code",
      "zip": "event_postal_code",

      # Event information fields
      "event_type": "event_type",
      "guest_count": "guest_count",
      "expected_attendance": "guest_count",
      "event_start_date": "event_start_date",
      "start_date": "event_start_date",
      "event_end_date": "event_end_date",
      "end_date": "event_end_date",
      "rental_start_date": "rental_start_date",
      "rental_end_date": "rental_end_date",
      "duration_days": "duration_days",

      # Equipment fields
      "required_stalls": "required_stalls",
      "how_many_portable_toilet_stalls_": "how_many_portable_toilet_stalls_",
      "stall_count": "stall_count",
      "ada_required": "ada_required",
      "ada": "ada",

      # Site condition fields
      "power_available": "power_available",
      "water_available": "water_available",
      "site_obstacles": "site_obstacles",

      # Consent fields
      "text_consent": "by_submitting_this_form_you_consent_to_receive_texts",
      "by_submitting_this_form_you_consent_to_receive_texts": "by_submitting_this_form_you_consent_to_receive_texts",

      # Call-specific fields
      "call_recording_url": "call_recording_url",
      "call_summary": "call_summary",
      "full_transcript": "full_transcript",

      # Additional information
      "budget_mentioned": "budget_mentioned",
      "quote_urgency": "quote_urgency",
  }

  # Apply the mapping, copying values from extracted_data to classification_input
  for extracted_field, class_field in field_mapping.items():
    if extracted_field in extracted_data and extracted_data[extracted_field] is not None:
      # Use setattr to set the attribute on the object
      # This handles both direct attributes and those that would be set through __init__
      setattr(classification_input, class_field,
              extracted_data[extracted_field])

  # Convert product_interest to list if it's a string
  if hasattr(classification_input, 'product_interest') and isinstance(classification_input.product_interest, str):
    classification_input.product_interest = [
        classification_input.product_interest]

  return classification_input
