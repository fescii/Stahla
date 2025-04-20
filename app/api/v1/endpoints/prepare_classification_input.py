"""Helper function for preparing classification input from various sources."""

from typing import Dict, Any
import logfire
from app.models.classification import ClassificationInput


def prepare_classification_input(source: str, raw_data: dict, extracted_data: dict) -> ClassificationInput:
  """Safely prepares ClassificationInput from extracted data."""
  logfire.debug(
      f"Preparing classification input from {source}", extracted_data=extracted_data)
  try:
    # Map extracted fields, providing defaults or None
    input_obj = ClassificationInput(
        source=source,
        raw_data=raw_data,  # Include raw payload for context
        extracted_data=extracted_data,  # Keep extracted data for reference

        # Contact Info
        firstname=extracted_data.get("firstname"),
        lastname=extracted_data.get("lastname"),
        email=extracted_data.get("email"),
        phone=extracted_data.get("phone"),
        company=extracted_data.get("company"),
        message=extracted_data.get("message"),  # Added
        text_consent=extracted_data.get("text_consent"),  # Added

        # Lead & Product Details
        product_interest=extracted_data.get("product_interest", []) if isinstance(extracted_data.get("product_interest"), list) else [
            extracted_data.get("product_interest")] if extracted_data.get("product_interest") else [],
        service_needed=extracted_data.get(
            "service_needed"),  # Renamed from lead_type_guess
        # Renamed from required_stalls
        stall_count=extracted_data.get("stall_count"),
        ada_required=extracted_data.get("ada_required"),

        # Event/Project Details
        event_type=extracted_data.get("event_type"),
        # Renamed from event_location_description
        event_address=extracted_data.get("event_address"),
        event_state=extracted_data.get("event_state"),
        event_city=extracted_data.get("event_city"),
        event_postal_code=extracted_data.get("event_postal_code"),
        event_location_type=extracted_data.get("event_location_type"),
        delivery_surface=extracted_data.get("delivery_surface"),
        delivery_obstacles=extracted_data.get("delivery_obstacles"),
        duration_days=extracted_data.get("duration_days"),
        duration_hours_per_day=extracted_data.get("duration_hours_per_day"),
        event_start_date=extracted_data.get(
            "event_start_date"),  # Renamed from start_date
        event_end_date=extracted_data.get(
            "event_end_date"),  # Renamed from end_date
        guest_count=extracted_data.get("guest_count"),
        other_facilities_available=extracted_data.get(
            "other_facilities_available"),
        onsite_contact_different=extracted_data.get(
            "onsite_contact_different"),
        working_hours=extracted_data.get("working_hours"),
        weekend_usage=extracted_data.get("weekend_usage"),

        # Site Requirements
        power_available=extracted_data.get("power_available"),
        power_distance_feet=extracted_data.get("power_distance_feet"),
        power_cord_ramps_needed=extracted_data.get("power_cord_ramps_needed"),
        generator_needed=extracted_data.get("generator_needed"),
        water_available=extracted_data.get("water_available"),
        water_distance_feet=extracted_data.get("water_distance_feet"),
        water_hose_ramps_needed=extracted_data.get("water_hose_ramps_needed"),

        # Other
        budget_mentioned=extracted_data.get("budget_mentioned"),
        decision_timeline=extracted_data.get("decision_timeline"),
        quote_needed_by=extracted_data.get("quote_needed_by"),
        other_products_needed=extracted_data.get("other_products_needed", []) if isinstance(extracted_data.get("other_products_needed"), list) else [
            extracted_data.get("other_products_needed")] if extracted_data.get("other_products_needed") else [],
        call_summary=extracted_data.get("call_summary"),
        call_recording_url=extracted_data.get("call_recording_url"),
        full_transcript=extracted_data.get("full_transcript"),
        call_duration_seconds=extracted_data.get(
            "call_duration_seconds")  # Added
    )
    return input_obj
  except Exception as e:
    logfire.error("Error preparing classification input",
                  exc_info=True, extracted_data=extracted_data)
    # Return a minimal input object or re-raise depending on desired handling
    # Returning minimal object to allow classification attempt with partial data
    return ClassificationInput(
        source=source,
        raw_data=raw_data,
        extracted_data=extracted_data,
        # Ensure at least email is present if possible
        email=extracted_data.get("email"),
        comments=f"Error preparing input: {e}"  # Add error note
    )
