# app/api/v1/endpoints/webhooks/util/hubspot/contact.py

import logfire
from typing import Tuple, Optional, Dict, Any

# Import models
from app.models.classification import ClassificationInput, ClassificationResult
from app.models.hubspot import HubSpotContactProperties, HubSpotContactInput, HubSpotApiResult

# Import services
from app.services.hubspot import hubspot_manager
from app.services.n8n import trigger_n8n_handoff_automation


async def handle_hubspot_update(
    classification_result: ClassificationResult,
    input_data: ClassificationInput
) -> Tuple[Optional[str], Optional[str]]:
  """
  Handles creating/updating HubSpot Contact and creating a NEW Lead based on classification.
  Used when no existing lead ID is provided (e.g., initial form, email, or voice call).
  Returns (contact_id, lead_id)
  """
  contact_id = None
  lead_id = None

  logfire.info(
      # Updated log message
      "Entering handle_hubspot_update (Create New Lead Flow)",
      input_email=input_data.email,
      input_firstname=input_data.firstname,
      input_source=input_data.source,
      classification_lead_type=classification_result.classification.lead_type if classification_result.classification else "N/A"
  )

  try:
    classification_output = classification_result.classification
    if not classification_output:
      logfire.warn("Classification output missing, cannot determine lead type for HubSpot.",
                   input_email=input_data.email)
      # Decide if we should proceed without classification? For now, let's assume we might still create a contact.

    # --- Moved Email Check ---
    # 0. Check for Email BEFORE attempting contact creation/update
    if not input_data.email:
      logfire.error("Cannot create/update HubSpot contact: Email is missing in input data.",
                    input_data=input_data.model_dump(exclude_none=True))
      return None, None  # Stop processing if email is missing
    # --- End Moved Email Check ---

    # 1. Create/Update Contact
    logfire.info(
        "Preparing HubSpotContactProperties for create/update",
        email_to_use=input_data.email
    )
    # Use updated field names from properties.csv/hubspot.md for contact
    contact_props = HubSpotContactProperties(
        # Email is guaranteed to be present here
        email=getattr(input_data, 'email', None),
        firstname=getattr(input_data, 'firstname', None),
        lastname=getattr(input_data, 'lastname', None),
        phone=getattr(input_data, 'phone', None),
        event_or_job_address=getattr(input_data, 'event_or_job_address', None),
        what_service_do_you_need_=getattr(
            input_data, 'what_service_do_you_need_', None),
        event_start_date=getattr(input_data, 'event_start_date', None),
        event_end_date=getattr(input_data, 'event_end_date', None),
        by_submitting_this_form_you_consent_to_receive_texts=getattr(
            input_data, 'by_submitting_this_form_you_consent_to_receive_texts', None),
        message=getattr(input_data, 'message', None),
        how_many_portable_toilet_stalls_=getattr(
            input_data, 'how_many_portable_toilet_stalls_', None),
        ada=getattr(input_data, 'ada', None),
        city=getattr(input_data, 'city', None),
        zip=getattr(input_data, 'zip',
                    None),
        address=getattr(input_data, 'address', None),
        state=getattr(input_data, 'state', getattr(
            input_data, 'event_state', None)),
        how_many_restroom_stalls_=getattr(
            input_data, 'how_many_restroom_stalls_', None),
        how_many_shower_stalls_=getattr(
            input_data, 'how_many_shower_stalls_', None),
        how_many_laundry_units_=getattr(
            input_data, 'how_many_laundry_units_', None),
        your_message=getattr(input_data, 'your_message', None),
        do_you_have_water_access_onsite_=getattr(
            input_data, 'do_you_have_water_access_onsite_', None),
        do_you_have_power_access_onsite_=getattr(
            input_data, 'do_you_have_power_access_onsite_', None),

        # AI/Call related properties (if applicable to contact)
        ai_call_summary=classification_output.metadata.get(
            "ai_call_summary") if classification_output and classification_output.metadata else None,
        call_recording_url=classification_output.metadata.get(
            "call_recording_url") if classification_output and classification_output.metadata else None,
        ai_call_sentiment=classification_output.metadata.get(
            "ai_call_sentiment") if classification_output and classification_output.metadata else None,
        call_summary=classification_output.metadata.get(
            "call_summary") if classification_output and classification_output.metadata else None
    )

    # Create a contact input with the properties
    contact_input = HubSpotContactInput(
        properties=contact_props
    )

    # Use the updated service function which returns HubSpotApiResult
    contact_api_result = await hubspot_manager.contact.create_or_update(contact_input)

    if contact_api_result.status != "success" or not contact_api_result.hubspot_id:
      logfire.error(
          "Failed to create or update HubSpot contact.",
          email=input_data.email,
          error=contact_api_result.message,
          details=contact_api_result.details
      )
      return None, None  # Return None for both IDs if contact operation failed

    contact_id = contact_api_result.hubspot_id
    # Extract contact properties from the result details if needed
    contact_properties = contact_api_result.details.get(
        'properties', {}) if contact_api_result.details else {}
    logfire.info("HubSpot contact created/updated successfully.",
                 contact_id=contact_id)

    # Import lead creation logic
    from .lead import create_lead_from_classification
    lead_id = await create_lead_from_classification(
        classification_output=classification_output,
        input_data=input_data,
        contact_api_result=contact_api_result
    )

    # 4. Trigger n8n Handoff (if not disqualified)
    if lead_id and classification_output and classification_output.lead_type != "Disqualify":
      logfire.info("Sending handoff data to n8n for new lead.",  # Updated log message
                   contact_id=contact_id, lead_id=lead_id)
      lead_result = await hubspot_manager.get_lead_by_id(lead_id)
      # Pass the API results for contact and lead
      await trigger_n8n_handoff_automation(
          classification_result,
          input_data,
          contact_api_result,  # Pass the result object
          lead_result  # Pass the result object
      )
    elif not classification_output:
      logfire.warn(
          "Skipping n8n handoff because classification output is missing.")
    elif not lead_id:
      logfire.warn(
          "Skipping n8n handoff because lead creation failed.")
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.")

    return contact_id, lead_id

  except Exception as e:
    logfire.exception(
        # Updated log message
        "Unhandled error during HubSpot update process (new lead flow)")
    return contact_id, lead_id
