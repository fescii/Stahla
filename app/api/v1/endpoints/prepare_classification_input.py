"""Helper function for preparing classification input from various sources."""

from typing import Dict, Any
import logfire
from app.models.classification import ClassificationInput

def prepare_classification_input(source: str, raw_data: Dict[str, Any], extracted_data: Dict[str, Any]) -> ClassificationInput:
    """
    Prepares a ClassificationInput object from various sources of data.
    
    Args:
        source: The source of the data (webform, voice, email)
        raw_data: The raw payload data for context
        extracted_data: Extracted data from the payload, may include nested form_submission_data
        
    Returns:
        A ClassificationInput object with all available data mapped correctly
    """
    try:
        # Process special case: check if form_submission_data exists within extracted_data
        # This typically happens in Bland.ai webhooks where original form data is in metadata
        form_data = extracted_data.get('form_submission_data', {})
        
        # If both main extracted_data and form_data have fields, prioritize extracted_data
        # but use form_data as fallback for missing fields
        combined_data = {**form_data, **extracted_data}
        
        # Debug logging
        logfire.debug("Preparing classification input", 
                    source=source, 
                    has_email=bool(combined_data.get("email")),
                    has_form_data=bool(form_data))
        
        # Build the ClassificationInput object with all available fields
        input_obj = ClassificationInput(
            source=source,
            firstname=combined_data.get("firstname"),
            lastname=combined_data.get("lastname"),
            email=combined_data.get("email"),
            phone=combined_data.get("phone"),
            company=combined_data.get("company"),
            # Ensure product_interest is a list
            product_interest=combined_data.get("product_interest", []) if isinstance(combined_data.get("product_interest"), list) else [combined_data.get("product_interest")] if combined_data.get("product_interest") else [],
            event_type=combined_data.get("event_type"),
            # Map from either specific field name
            event_location_description=combined_data.get("event_location_description", combined_data.get("event_location")),
            duration_days=combined_data.get("duration_days"),
            start_date=combined_data.get("start_date"),
            end_date=combined_data.get("end_date"),
            guest_count=combined_data.get("guest_count"),
            required_stalls=combined_data.get("required_stalls"),
            ada_required=combined_data.get("ada_required"),
            budget_mentioned=combined_data.get("budget_mentioned"),
            comments=combined_data.get("comments"),
            power_available=combined_data.get("power_available"),
            water_available=combined_data.get("water_available"),
            source_url=combined_data.get("source_url"),
            call_recording_url=combined_data.get("call_recording_url"),
            call_summary=combined_data.get("call_summary"),
            raw_data=raw_data,
            extracted_data=combined_data  # Include the full combined data in extracted_data field
        )
        
        # Log success
        logfire.info("Successfully prepared classification input", 
                    email=input_obj.email, 
                    first_name=input_obj.firstname,
                    source=source)
        
        return input_obj
    except Exception as e:
        logfire.error("Error preparing classification input", 
                    exc_info=True, 
                    extracted_data_fields=list(extracted_data.keys()) if extracted_data else None)
        
        # Return a minimal input object to allow classification attempt with partial data
        return ClassificationInput(
            source=source,
            email=extracted_data.get("email") or form_data.get("email") if 'form_data' in locals() else None,
            raw_data=raw_data,
            comments=f"Error preparing input: {e}"  # Add error note
        )
