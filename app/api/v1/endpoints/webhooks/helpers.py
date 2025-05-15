# app/api/v1/endpoints/webhooks/helpers.py

from typing import Tuple, Optional, Dict, Any
import logfire
from fastapi import BackgroundTasks
import re  # Import regex module

# Import models
from app.models.webhook import FormPayload
from app.models.bland import BlandCallbackRequest
from app.models.classification import ClassificationInput, ClassificationResult, LeadClassificationType
from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotLeadProperties,  # Changed from Deal
    HubSpotLeadInput,  # Added import for HubSpotLeadInput
    HubSpotContactResult,
    HubSpotLeadResult,  # Changed from Deal
    HubSpotApiResult
)

# Import services
from app.services.classify.classification import classification_manager
from app.services.bland import bland_manager
from app.services.hubspot import hubspot_manager
from app.services.n8n import trigger_n8n_handoff_automation
from app.core.config import settings

# Import the prepare_classification_input function
from app.api.v1.endpoints.prepare import prepare_classification_input


# --- Form Webhook Helpers ---

def _is_form_complete(payload: FormPayload) -> bool:
  """
  Check if the form payload contains the minimum required information.
  NEEDS CONFIRMATION FROM KEVIN/CLIENT - using a basic set for now.
  """
  logfire.debug("Checking form completeness", payload=payload.model_dump())
  # Example: Require name, email, phone, service, address, start date
  required_fields = [
      payload.firstname,
      payload.lastname,
      payload.email,
      payload.phone,
      payload.product_interest,  # Correct field from FormPayload
      payload.event_location_description,  # Correct field from FormPayload
      payload.start_date  # Correct field from FormPayload
  ]
  is_complete = all(field is not None and str(field).strip()
                    != "" for field in required_fields)
  logfire.info(f"Form completeness check result: {is_complete}")
  return is_complete


async def _trigger_bland_call(payload: FormPayload):
  """
  Triggers a Bland.ai call if the form is incomplete.
  """
  if not settings.BLAND_API_KEY:
    logfire.warn("Bland API key not configured, skipping call.")
    return

  # Extract necessary info, providing defaults or empty strings if None
  phone_number = payload.phone or ""
  first_name = payload.firstname or "Lead"
  # Create a task description based on available info - Use correct fields from FormPayload
  task_description = f"Follow up with {first_name} regarding their interest in {payload.product_interest or 'restroom solutions'}. "
  task_description += f"They submitted an incomplete form from {getattr(payload, 'source_url', None) or 'the website'}."
  # task_description += f"Key details provided: Event Type: {payload.event_type or 'N/A'}, Location: {payload.event_location_description or 'N/A'}."
  task_description += f"Key details provided: Event Address: {payload.event_location_description or 'N/A'}."
  task_description += "Goal is to gather missing details (like duration, guest count, specific needs) and qualify the lead."

  if not phone_number:
    logfire.error(
        "Cannot trigger Bland call: Phone number is missing.", email=payload.email)
    return

  # Prepare metadata to pass to Bland, including original form data
  # Flatten the payload into the metadata for easier access by the AI script
  metadata_to_pass = payload.model_dump(exclude_none=True)
  metadata_to_pass["source"] = "web_form_incomplete"  # Add source identifier

  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhook/voice"

  callback_request = BlandCallbackRequest(
      phone_number=phone_number,
      task=None,  # Task is now loaded from script in BlandAIManager
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental form you submitted. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      amd=True,
      voice_id=1,
      webhook=webhook_url,
      metadata=metadata_to_pass
  )

  logfire.info(
      # Log the metadata
      f"Triggering Bland call to {phone_number}", metadata=metadata_to_pass)
  try:
    call_result = await bland_manager.initiate_callback(
        callback_request,
        contact_id=payload.email or "unknown_contact",
        log_retry_of_call_id=None,
        log_retry_reason=None,
    )
    if call_result.status == "success":
      logfire.info("Bland call initiated successfully.",
                   call_id=call_result.call_id)
    else:
      logfire.error("Failed to initiate Bland call.",
                    error=call_result.message, details=call_result.details)
  except Exception as e:
    logfire.exception("Error occurred while triggering Bland call")


# --- General HubSpot Update Helper (Used by Form, Voice, Email for NEW leads) ---

async def _handle_hubspot_update(
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
      "Entering _handle_hubspot_update (Create New Lead Flow)",
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
        event_or_job_address=getattr(input_data, 'event_address', None),
        what_service_do_you_need_=getattr(input_data, 'service_needed', None),
        event_start_date=getattr(input_data, 'event_start_date', None),
        event_end_date=getattr(input_data, 'event_end_date', None),
        by_submitting_this_form_you_consent_to_receive_texts=getattr(
            input_data, 'text_consent', None),
        message=getattr(input_data, 'message', None),
        how_many_portable_toilet_stalls_=getattr(input_data, 'stall_count', None) if getattr(
            input_data, 'service_needed', '') == 'Porta Potty' else None,
        # Map ada_required to 'ada' contact property
        ada=getattr(input_data, 'ada_required', None),
        # Add other relevant contact properties from input_data if needed
        # Map relevant fields from properties.csv like city, zip, address if available in input_data
        # Use getattr with fallback
        city=getattr(input_data, 'event_city', None),
        zip=getattr(input_data, 'event_postal_code',
                    None),  # Use getattr with fallback
        # Use getattr with fallback
        address=getattr(input_data, 'event_address', None),
        # Required parameters that were missing
        state=getattr(input_data, 'state', getattr(
            input_data, 'event_state', None)),
        how_many_restroom_stalls_=getattr(
            input_data, 'restroom_stall_count', None),
        how_many_shower_stalls_=getattr(
            input_data, 'shower_stall_count', None),
        how_many_laundry_units_=getattr(
            input_data, 'laundry_unit_count', None),
        your_message=getattr(input_data, 'specific_message',
                             getattr(input_data, 'message', None)),
        do_you_have_water_access_onsite_=getattr(
            input_data, 'water_access', None),
        do_you_have_power_access_onsite_=getattr(
            input_data, 'power_access', None),
        # Default to True if not specified
        contact_consent_given=getattr(input_data, 'consent', True),

        # AI/Call related properties (if applicable to contact)
        ai_call_summary=classification_output.metadata.get(
            "call_summary") if classification_output and classification_output.metadata else None,
        call_recording_url=classification_output.metadata.get(
            "call_recording_url") if classification_output and classification_output.metadata else None,
        ai_call_sentiment=classification_output.metadata.get(
            "call_sentiment") if classification_output and classification_output.metadata else None,
        call_summary=classification_output.metadata.get(
            "call_summary") if classification_output and classification_output.metadata else None
    )
    # Use the updated service function which returns HubSpotApiResult
    contact_api_result = await hubspot_manager.create_or_update_contact(contact_props)

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

    # 2. Create NEW Lead
    # Prepare lead properties using ClassificationInput and ClassificationResult
    lead_props = HubSpotLeadProperties(
        rental_start_date=getattr(input_data, 'event_start_date', None),
        rental_end_date=getattr(input_data, 'event_end_date', None),
        # Map from ClassificationResult (check hubspot.md for Lead property names)
        project_category=classification_output.metadata.get(
            "event_type") if classification_output and classification_output.metadata else None,
        units_needed=getattr(input_data, 'service_needed', None),
        expected_attendance=getattr(input_data, 'guest_count', None),
        ada_required=getattr(input_data, 'ada_required', None),
        # Or map from specific classification field?
        additional_services_needed=getattr(input_data, 'message', None),
        # Add missing required parameters
        onsite_facilities=classification_output.metadata.get(
            "onsite_facilities") if classification_output and classification_output.metadata else None,
        partner_referral_consent=getattr(
            input_data, 'partner_referral_consent', False),
        decision_timeline=classification_output.metadata.get(
            "decision_timeline") if classification_output and classification_output.metadata else None,
        follow_up_call_scheduled=classification_output.metadata.get(
            "follow_up_scheduled") if classification_output and classification_output.metadata else False,
        shower_required=getattr(input_data, 'shower_required', False),
        handwashing_needed=getattr(input_data, 'handwashing_needed', False),
        address_type=classification_output.metadata.get(
            "address_type") if classification_output and classification_output.metadata else None,
        site_ground_level=classification_output.metadata.get(
            "site_ground_level") if classification_output and classification_output.metadata else None,
        power_path_cross=classification_output.metadata.get(
            "power_path_cross") if classification_output and classification_output.metadata else False,
        water_path_cross=classification_output.metadata.get(
            "water_path_cross") if classification_output and classification_output.metadata else False,
        site_working_hours=classification_output.metadata.get(
            "site_working_hours") if classification_output and classification_output.metadata else None,
        weekend_service_needed=classification_output.metadata.get(
            "weekend_service_needed") if classification_output and classification_output.metadata else None,
        cleaning_service_needed=classification_output.metadata.get(
            "cleaning_service_needed") if classification_output and classification_output.metadata else None,
        onsite_contact_name=classification_output.metadata.get(
            "onsite_contact_name") if classification_output and classification_output.metadata else None,
        onsite_contact_phone=classification_output.metadata.get(
            "onsite_contact_phone") if classification_output and classification_output.metadata else None,
        site_ground_type=classification_output.metadata.get(
            "site_ground_type") if classification_output and classification_output.metadata else None,
        site_obstacles=classification_output.metadata.get(
            "site_obstacles") if classification_output and classification_output.metadata else None,
        water_source_distance=classification_output.metadata.get(
            "water_source_distance") if classification_output and classification_output.metadata else None,
        power_source_distance=classification_output.metadata.get(
            "power_source_distance") if classification_output and classification_output.metadata else None,
        within_local_service_area=classification_output.metadata.get(
            "is_local") if classification_output and classification_output.metadata else None,
        needs_human_follow_up=classification_output.requires_human_review if classification_output else True,
        quote_urgency=classification_output.metadata.get(
            "quote_urgency") if classification_output and classification_output.metadata else None,
        # AI properties
        ai_lead_type=classification_output.lead_type if classification_output else None,
        ai_classification_reasoning=classification_output.reasoning if classification_output else None,
        ai_classification_confidence=classification_output.confidence if classification_output else None,
        ai_routing_suggestion=classification_output.routing_suggestion if classification_output else None,
        ai_intended_use=classification_output.metadata.get(
            "intended_use") if classification_output and classification_output.metadata else None,
        ai_qualification_notes=classification_output.metadata.get(
            "qualification_notes") if classification_output and classification_output.metadata else None,
        number_of_stalls=getattr(input_data, 'stall_count', None),
        event_duration_days=getattr(input_data, 'duration_days', None),
        guest_count_estimate=getattr(input_data, 'guest_count', None),
        ai_estimated_value=classification_output.metadata.get(
            "estimated_value") if classification_output and classification_output.metadata else None,
    )

    # Remove None values before sending to HubSpot
    lead_props_dict = lead_props.model_dump(exclude_none=True, by_alias=True)
    lead_props_cleaned = HubSpotLeadProperties(**lead_props_dict)

    # Create a HubSpotLeadInput object with the lead properties
    # HubSpotLeadInput also needs contact information to create a contact first
    lead_input = HubSpotLeadInput(
        properties=lead_props_cleaned,
        email=getattr(input_data, 'email', None),
        phone=getattr(input_data, 'phone', None),
        contact_firstname=getattr(input_data, 'firstname', None),
        contact_lastname=getattr(input_data, 'lastname', None),
        # Optional company info if available
        company_name=getattr(input_data, 'company', None),
        company_domain=None,  # We don't have this in input_data
        # Optional fields
        project_category=classification_output.metadata.get(
            'event_type', None) if classification_output and classification_output.metadata else None,
        estimated_value=classification_output.metadata.get(
            'estimated_value', None) if classification_output and classification_output.metadata else None,
        lead_properties=lead_props_cleaned,
        owner_email=None,  # Set to None as we'll assign owner separately
    )

    # Call create_lead service function
    lead_result = await hubspot_manager.create_lead(lead_input)

    if lead_result.status != "success" or not lead_result.hubspot_id:
      logfire.error(
          "Failed to create HubSpot lead.",  # Updated log message
          lead_properties=lead_props_dict,
          error=lead_result.message,
          details=lead_result.details
      )
      return contact_id, None

    lead_id = lead_result.hubspot_id
    logfire.info("HubSpot lead created successfully.",
                 lead_id=lead_id)  # Updated log message

    # 3. Assign Owner (if applicable for Leads - check HubSpot setup)
    # The concept of pipelines/stages might not apply directly to Leads in the same way as Deals.
    # Owner assignment might still be relevant.
    final_owner_id = None
    if classification_output and classification_output.lead_type != "Disqualify":
      # Assign owner based on logic (e.g., round-robin, specific queue)
      final_owner_id = await hubspot_manager.get_next_owner_id()  # type: ignore
      if final_owner_id:
        logfire.info(f"Assigning owner {final_owner_id} to new lead {lead_id}")
        # Update the lead with the owner ID
        await hubspot_manager.update_lead_properties(lead_id, {"hubspot_owner_id": final_owner_id})
      else:
        logfire.warn(f"Could not determine owner for new lead {lead_id}")

    # 4. Trigger n8n Handoff (if not disqualified)
    if classification_output and classification_output.lead_type != "Disqualify":
      logfire.info("Sending handoff data to n8n for new lead.",  # Updated log message
                   contact_id=contact_id, lead_id=lead_id)
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
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.")

    return contact_id, lead_id

  except Exception as e:
    logfire.exception(
        # Updated log message
        "Unhandled error during HubSpot update process (new lead flow)")
    return contact_id, lead_id


# --- HubSpot Event Webhook Helpers ---

def _is_hubspot_contact_complete(contact_properties: dict) -> bool:
  """
  Check if the HubSpot contact properties contain the minimum required information
  to potentially create a complete Lead after classification/qualification.
  Checks mandatory Contact fields AND derivable mandatory Lead fields.
  Returns False if mandatory lead info (like quote_urgency) is missing,
  forcing the qualification (e.g., Bland call) flow.
  Uses HubSpot internal property names.
  """
  logfire.debug("Checking HubSpot contact completeness for potential lead creation",
                properties=contact_properties)

  # 1. Check Mandatory Contact fields from properties.csv
  mandatory_contact_fields = [
      contact_properties.get("firstname"),
      contact_properties.get("lastname"),
      contact_properties.get("email"),
      contact_properties.get("phone"),
      contact_properties.get("event_or_job_address"),
      contact_properties.get("event_start_date")
  ]
  contact_complete = all(prop is not None and str(prop).strip() !=
                         "" for prop in mandatory_contact_fields)

  if not contact_complete:
    logfire.info(
        "HubSpot contact completeness check failed: Missing mandatory contact fields.")
    return False

  # 2. Check if data for Mandatory Lead fields can be derived
  #    - project_category: Needs 'what_service_do_you_need_'
  #    - units_needed: Needs 'what_service_do_you_need_' and potentially stall counts
  #    - ada_required: Needs 'ada'
  #    - within_local_service_area: Needs address/zip ('event_or_job_address', 'zip') as proxy
  #    - quote_urgency: Cannot be derived from initial contact form.

  derivable_lead_fields_present = (
      contact_properties.get("what_service_do_you_need_") is not None and
      # Check if 'ada' exists, even if False
      contact_properties.get("ada") is not None and
      # Already checked but good for clarity
      contact_properties.get("event_or_job_address") is not None and
      # Check zip for location check proxy
      contact_properties.get("zip") is not None
      # We don't check stall counts explicitly here, assume 'units_needed' can be constructed if service is known.
  )

  # Crucially, 'quote_urgency' is mandatory for a Lead but not available initially.
  # Therefore, for the purpose of creating a lead *immediately*, the data is never complete.
  # Always false due to missing quote_urgency etc.
  can_create_lead_immediately = False

  final_completeness = contact_complete and derivable_lead_fields_present and can_create_lead_immediately

  logfire.info(f"HubSpot contact completeness check result: {final_completeness}",
               contact_fields_ok=contact_complete,
               derivable_lead_fields_ok=derivable_lead_fields_present,
               can_create_lead_immediately=can_create_lead_immediately)

  # This function will now effectively always return False in the context
  # of the initial webhook, forcing the 'incomplete' path.
  return final_completeness


async def _trigger_bland_call_for_hubspot(contact_id: str, contact_properties: dict):
  """
  Triggers a Bland.ai call for an incomplete HubSpot contact.
  Includes contact_id in metadata. Lead ID is no longer passed.
  Uses HubSpot internal property names from contact_properties.
  """
  if not settings.BLAND_API_KEY:
    logfire.warn(
        "Bland API key not configured, skipping call for HubSpot contact.")  # Updated log message
    return

  # Use internal names from contact_properties dict
  phone_number = contact_properties.get("phone")

  # --- ADD CHECK FOR NONE PHONE NUMBER ---
  if not phone_number:
    logfire.error(
        "Cannot trigger Bland call for HubSpot contact: Phone number is missing in contact_properties.",
        contact_id=contact_id
    )
    return
  # --- END CHECK ---

  first_name = contact_properties.get("firstname", "Lead")
  service_needed = contact_properties.get(
      "what_service_do_you_need_", "restroom solutions")
  event_address = contact_properties.get("event_or_job_address", "N/A")

  # --- Format Phone Number using BLAND_PHONE_PREFIX ---
  # Remove non-digit characters
  # Now phone_number is guaranteed to be a string here
  digits_only = re.sub(r'\D', '', phone_number)
  formatted_phone_number = digits_only  # Start with digits
  prefix_to_use = settings.BLAND_PHONE_PREFIX

  if prefix_to_use:
    # Normalize prefix for checking (e.g., remove leading '+')
    prefix_digits = re.sub(r'\D', '', prefix_to_use)
    # Check if the number already starts with the prefix digits
    if digits_only.startswith(prefix_digits):
      logfire.info(
          f"Phone number digits already start with prefix digits '{prefix_digits}'. Using digits only.", contact_id=contact_id)
      # Decide if we should still prepend the original prefix (e.g., with '+')
      # Assuming the goal is E.164 or similar, use the original prefix if it contains non-digits like '+'
      if prefix_to_use != prefix_digits:
        formatted_phone_number = prefix_to_use + \
            digits_only[len(prefix_digits)
                            :]  # Reconstruct with original prefix
      else:
        # Use digits only if prefix was just digits
        formatted_phone_number = digits_only
    else:
      # Prepend the original prefix (e.g., '+1') if it's defined and not already present
      formatted_phone_number = prefix_to_use + digits_only
      logfire.info(
          f"Prepended BLAND_PHONE_PREFIX '{prefix_to_use}' to phone number digits.", contact_id=contact_id)
  else:
    # If no prefix is defined, log a warning
    logfire.warn(
        "BLAND_PHONE_PREFIX not set in environment. Using digits only for phone number.", contact_id=contact_id)
    # Fallback to digits only if no prefix is set
    formatted_phone_number = digits_only

  logfire.info(
      f"Formatted phone number for Bland call: {formatted_phone_number} (from {phone_number})", contact_id=contact_id)
  # --- End Phone Number Formatting ---

  if not formatted_phone_number:
    logfire.error(
        # Updated log message
        "Cannot trigger Bland call for HubSpot contact: Formatted phone number is empty.",
        contact_id=contact_id
    )
    return

  task_description = f"Follow up with {first_name} regarding their interest in {service_needed}. "
  task_description += f"They submitted a HubSpot form. "
  task_description += f"Key details provided: Event Address: {event_address}. "
  task_description += "Goal is to gather missing details (like duration, guest count, quote urgency, specific needs) and qualify the lead."

  # Pass all fetched contact properties as metadata
  metadata_to_pass = contact_properties.copy()  # Start with all contact properties
  # Add source identifier
  metadata_to_pass["source"] = "hubspot_incomplete_contact"
  # Ensure contact ID is included
  metadata_to_pass["hubspot_contact_id"] = contact_id

  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhook/voice"

  callback_request = BlandCallbackRequest(
      phone_number=formatted_phone_number,  # Use formatted number
      task=None,  # Task is now loaded from script in BlandAIManager
      voice_id=1,
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental inquiry you submitted through our website. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      amd=True,
      webhook=webhook_url,
      metadata=metadata_to_pass
  )

  logfire.info(
      # Updated log message
      f"Triggering Bland call for HubSpot contact {contact_id} to {formatted_phone_number}",
      metadata=metadata_to_pass  # Log the full metadata
  )
  try:
    call_result = await bland_manager.initiate_callback(
        callback_request,  # Use the callback request
        contact_id=contact_id,  # Pass contact_id for logging
        log_retry_of_call_id=None,  # No retry ID for new call
        log_retry_reason=None,  # No retry reason for new call
    )
    if call_result.status == "success":
      logfire.info("Bland call for HubSpot contact initiated successfully.",  # Updated log message
                   call_id=call_result.call_id, contact_id=contact_id)
    else:
      logfire.error("Failed to initiate Bland call for HubSpot contact.",  # Updated log message
                    error=call_result.message, details=call_result.details,
                    contact_id=contact_id)
  except Exception as e:
    logfire.exception("Error occurred while triggering Bland call for HubSpot contact",  # Updated log message
                      contact_id=contact_id)


async def _update_hubspot_lead_after_classification(
    classification_result: ClassificationResult,
    input_data: ClassificationInput,
    contact_id: str  # Changed from lead_id
):
  """
  Creates a new HubSpot lead based on classification results, associates it with the contact,
  assigns owner, and triggers n8n handoff. Used after direct classification.
  """
  logfire.info("Entering _update_hubspot_lead_after_classification (Create Lead Flow)",
               contact_id=contact_id)

  classification_output = classification_result.classification
  if not classification_output:
    logfire.error("Classification output missing, cannot create HubSpot lead.",
                  contact_id=contact_id)
    return

  lead_id = None  # Initialize lead_id
  lead_result: Optional[HubSpotApiResult] = None  # Initialize lead_result

  try:
    # 1. Prepare Lead Properties from Classification
    properties_for_creation = {}
    if classification_output:
      extracted_metadata = classification_output.metadata or {}
      # Map classification results to Lead properties (check hubspot.md)
      properties_for_creation = {
          "project_category": extracted_metadata.get("event_type"),
          # Or construct?
          "units_needed": extracted_metadata.get("service_needed"),
          "expected_attendance": extracted_metadata.get("guest_count"),
          "ada_required": extracted_metadata.get("ada_required"),
          # Map comments?
          "additional_services_needed": extracted_metadata.get("comments"),
          "onsite_facilities": extracted_metadata.get("onsite_facilities"),
          "rental_start_date": extracted_metadata.get("start_date"),
          "rental_end_date": extracted_metadata.get("end_date"),
          "site_working_hours": extracted_metadata.get("site_working_hours"),
          "weekend_service_needed": extracted_metadata.get("weekend_service_needed"),
          "cleaning_service_needed": extracted_metadata.get("cleaning_service_needed"),
          "onsite_contact_name": extracted_metadata.get("onsite_contact_name"),
          "onsite_contact_phone": extracted_metadata.get("onsite_contact_phone"),
          "site_ground_type": extracted_metadata.get("site_ground_type"),
          "site_obstacles": extracted_metadata.get("site_obstacles"),
          "water_source_distance": extracted_metadata.get("water_source_distance"),
          "power_source_distance": extracted_metadata.get("power_source_distance"),
          "within_local_service_area": extracted_metadata.get("is_local"),
          "needs_human_follow_up": classification_output.requires_human_review,
          "quote_urgency": extracted_metadata.get("quote_urgency"),
          # AI properties
          "ai_lead_type": classification_output.lead_type,
          "ai_classification_reasoning": classification_output.reasoning,
          "ai_classification_confidence": classification_output.confidence,
          "ai_routing_suggestion": classification_output.routing_suggestion,
          "ai_intended_use": extracted_metadata.get("intended_use"),
          "ai_qualification_notes": extracted_metadata.get("qualification_notes"),
          # Map from metadata if available
          "number_of_stalls": extracted_metadata.get("stall_count"),
          "event_duration_days": extracted_metadata.get("duration_days"),
          "guest_count_estimate": extracted_metadata.get("guest_count"),
          "ai_estimated_value": extracted_metadata.get("estimated_value"),
      }

    # Remove None values before sending to HubSpot
    lead_props_dict = {k: v for k,
                       v in properties_for_creation.items() if v is not None}
    lead_props_model = HubSpotLeadProperties(**lead_props_dict)

    # 2. Create the Lead using HubSpotLeadInput
    logfire.info("Attempting to create HubSpot lead.",
                 contact_id=contact_id, properties=lead_props_dict)

    # Create a lead input object with all required properties
    lead_input = HubSpotLeadInput(
        properties=lead_props_model,
        email=input_data.email if hasattr(
            input_data, 'email') and input_data.email else None,
        phone=getattr(input_data, 'phone', None),
        contact_firstname=getattr(input_data, 'firstname', None),
        contact_lastname=getattr(input_data, 'lastname', None),
        # Other required fields with default values
        company_name=getattr(input_data, 'company', None),
        company_domain=None,
        project_category=extracted_metadata.get('event_type', None),
        estimated_value=extracted_metadata.get('estimated_value', None),
        lead_properties=lead_props_model,
        owner_email=None
    )

    # Call create_lead with the proper input object
    lead_result = await hubspot_manager.create_lead(lead_input)

    if lead_result.status != "success" or not lead_result.hubspot_id:
      logfire.error(
          "Failed to create HubSpot lead after classification.",
          contact_id=contact_id,
          lead_properties=lead_props_dict,
          error=lead_result.message,
          details=lead_result.details
      )
      # Decide if we need to fetch contact details again for n8n or just return
      # Fetching contact details again might be needed if n8n requires it
      # contact_api_result = await hubspot_manager.get_contact_by_id(contact_id)
      # await trigger_n8n_handoff_automation(classification_result, input_data, contact_api_result, None)
      return  # Stop processing if lead creation fails

    lead_id = lead_result.hubspot_id
    logfire.info("HubSpot lead created successfully.",
                 lead_id=lead_id, contact_id=contact_id)

    # 3. Assign Owner (if applicable)
    final_owner_id = None
    if classification_output and classification_output.lead_type != "Disqualify":
      final_owner_id = await hubspot_manager.get_next_owner_id()
      if final_owner_id:
        logfire.info(f"Assigning owner {final_owner_id} to new lead {lead_id}")
        # Update the newly created lead with the owner ID
        owner_update_result = await hubspot_manager.update_lead_properties(lead_id, {"hubspot_owner_id": final_owner_id})
        if owner_update_result.status != "success":
          logfire.warn(
              f"Failed to assign owner {final_owner_id} to lead {lead_id}", details=owner_update_result.details)
      else:
        logfire.warn(f"Could not determine owner for new lead {lead_id}")

    # 4. Trigger n8n Handoff (if not disqualified)
    if classification_output and classification_output.lead_type != "Disqualify":
      logfire.info("Sending handoff data to n8n for new lead.",
                   contact_id=contact_id, lead_id=lead_id)
      # We need the contact details to send to n8n. Fetch them.
      contact_api_result = await hubspot_manager.get_contact_by_id(contact_id)
      if contact_api_result.status != "success":
        logfire.error("Failed to fetch contact details for n8n handoff.",
                      contact_id=contact_id, details=contact_api_result.details)
        # Proceed without contact details? Or handle error?
        # For now, proceed but log the error.
        contact_api_result = None  # Ensure it's None if fetch failed

      await trigger_n8n_handoff_automation(
          classification_result,
          input_data,
          contact_api_result,  # Pass fetched contact result (or None)
          lead_result  # Pass the lead creation result object
      )
    elif not classification_output:
      logfire.warn(
          "Skipping n8n handoff because classification output is missing.")
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.")

  except Exception as e:
    logfire.exception(
        "Unhandled error during HubSpot lead creation/update process",
        contact_id=contact_id, lead_id=lead_id)
