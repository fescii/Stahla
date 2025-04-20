# app/api/v1/endpoints/webhooks/helpers.py

from typing import Tuple, Optional, Dict, Any
import logfire
from fastapi import BackgroundTasks  # Added BackgroundTasks

# Import models
from app.models.webhook import FormPayload
from app.models.bland import BlandCallbackRequest
from app.models.classification import ClassificationInput, ClassificationResult, LeadClassificationType
from app.models.hubspot import HubSpotContactProperties, HubSpotDealProperties, HubSpotContactResult, HubSpotDealResult, HubSpotApiResult  # Added HubSpotApiResult

# Import services
from app.services.classify.classification import classification_manager
from app.services.bland import bland_manager
from app.services.hubspot import hubspot_manager
from app.services.n8n import trigger_n8n_handoff_automation
from app.core.config import settings

# Import the prepare_classification_input function if it's defined elsewhere,
# or keep it here if it's only used by webhooks. Assuming it's defined elsewhere for now:
from app.api.v1.endpoints.prepare_classification_input import prepare_classification_input


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
      payload.service_needed,  # Use the field name from the form model
      payload.event_address,  # Use the field name from the form model
      payload.event_start_date  # Use the field name from the form model
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
  # Create a task description based on available info
  task_description = f"Follow up with {first_name} regarding their interest in {payload.product_interest or 'restroom solutions'}. "
  task_description += f"They submitted an incomplete form from {payload.source_url or 'the website'}."
  task_description += f"Key details provided: Event Type: {payload.event_type or 'N/A'}, Location: {payload.event_location_description or 'N/A'}."
  task_description += "Goal is to gather missing details (like duration, guest count, specific needs) and qualify the lead."

  if not phone_number:
    logfire.error(
        "Cannot trigger Bland call: Phone number is missing.", email=payload.email)
    return

  # Prepare metadata to pass to Bland, including original form data
  metadata_to_pass = {
      "form_submission_data": payload.model_dump(exclude_none=True)
  }

  # Create the request object for initiate_callback
  # Build the webhook URL for Bland to call back with results
  # NOTE: Ensure the path is correct (/voice, not /webhook/voice)
  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhooks/voice"

  callback_request = BlandCallbackRequest(
      phone_number=phone_number,
      task=task_description,
      # Pass optional parameters if needed/configured
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental form you submitted. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      amd=True,  # Enable Answering Machine Detection if desired
      webhook=webhook_url,
      metadata=metadata_to_pass
  )

  logfire.info(
      f"Triggering Bland call to {phone_number}", task=task_description)
  try:
    # Use initiate_callback instead of make_call
    call_result = await bland_manager.initiate_callback(callback_request)

    # Check result based on BlandApiResult structure
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
  Handles creating/updating HubSpot Contact and creating a NEW Deal based on classification.
  Used when no existing deal ID is provided (e.g., initial form, email, or voice call).
  """
  contact_id = None
  deal_id = None

  logfire.info(
      "Entering _handle_hubspot_update (Create New Deal Flow)",
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

    # 1. Create/Update Contact
    logfire.info(
        "Preparing HubSpotContactProperties for create/update",
        email_to_use=input_data.email,
        is_email_present=bool(input_data.email)
    )
    contact_props = HubSpotContactProperties(
        email=input_data.email,
        firstname=input_data.firstname,
        lastname=input_data.lastname,
        phone=input_data.phone,
        company=input_data.company,
        # Map relevant fields from ClassificationInput
        event_or_job_address=input_data.event_address,  # Use updated field name
        # Assuming 'service_needed' maps to a custom property like 'stahla_service_needed'
        stahla_service_needed=input_data.service_needed,
        stahla_event_start_date=input_data.event_start_date,
        stahla_event_end_date=input_data.event_end_date,
        stahla_text_consent=input_data.text_consent,
        message=input_data.message,
        # Add stall count if relevant (e.g., how_many_portable_toilet_stalls_)
        how_many_portable_toilet_stalls_=input_data.stall_count if input_data.service_needed == 'Porta Potty' else None,
        # Add other stall counts if needed
        # ...
        # Set lead source based on API input source
        stahla_lead_source=input_data.source.upper(),
        # Set lead type based on classification (if available)
        stahla_lead_type=classification_output.lead_type if classification_output else None
    )
    contact_result = await hubspot_manager.create_or_update_contact(contact_props)

    if contact_result.status != "success" or not getattr(contact_result, 'id', None):
      logfire.error(
          "Failed to create or update HubSpot contact.",
          email=input_data.email,
          error=getattr(contact_result, 'message', 'Unknown error'),
          details=getattr(contact_result, 'details', None)
      )
      if not input_data.email:
        logfire.critical("HubSpot contact failed specifically because input_data.email was missing!",
                         input_data_dump=input_data.model_dump(exclude={"raw_data", "extracted_data"}))
      return None, None

    contact_id = contact_result.id
    logfire.info("HubSpot contact created/updated successfully.",
                 contact_id=contact_id)

    # Determine deal type (New vs Existing Business)
    # This logic might need refinement based on how HubSpot tracks this
    created_at_str = contact_result.properties.get('createdate')
    last_modified_str = contact_result.properties.get('lastmodifieddate')
    deal_type = "newbusiness"  # Default
    if created_at_str and last_modified_str:
      # Simple check: if modified significantly after creation, assume existing
      # This is a basic heuristic, might need adjustment
      try:
        # HubSpot dates are often epoch milliseconds or ISO strings
        # Add robust date parsing here if needed
        pass  # Placeholder for more robust date comparison logic
      except Exception:
        pass  # Ignore parsing errors for now
    logfire.info(f"Setting deal type to {deal_type}")

    # 2. Create NEW Deal
    deal_name = f"{input_data.firstname or 'Lead'} {input_data.lastname or ''} - {input_data.service_needed or 'Inquiry'}".strip()

    # Prepare deal properties using updated ClassificationInput fields
    deal_props = HubSpotDealProperties(
        dealname=deal_name,
        dealtype=deal_type,
        # Copy relevant fields from Contact/ClassificationInput
        start_date=input_data.event_start_date,
        end_date=input_data.event_end_date,
        deal_address=input_data.event_address,
        # Map classification results to custom deal properties
        stahla_ai_lead_type=classification_output.lead_type if classification_output else None,
        stahla_ai_reasoning=classification_output.reasoning if classification_output else None,
        stahla_ai_confidence=classification_output.confidence if classification_output else None,
        stahla_ai_routing_suggestion=classification_output.routing_suggestion if classification_output else None,
        stahla_ai_requires_review=classification_output.requires_human_review if classification_output else True,
        # Map metadata fields
        stahla_ai_is_local=classification_output.metadata.get(
            "is_local") if classification_output else None,
        stahla_ai_intended_use=classification_output.metadata.get(
            "intended_use") if classification_output else None,
        stahla_ai_qualification_notes=classification_output.metadata.get(
            "qualification_notes") if classification_output else None,
        stahla_call_recording_url=classification_output.metadata.get(
            "call_recording_url") if classification_output else None,
        stahla_call_summary=classification_output.metadata.get(
            "call_summary") if classification_output else None,
        stahla_call_duration_seconds=classification_output.metadata.get(
            "call_duration_seconds") if classification_output else None,
        stahla_stall_count=classification_output.metadata.get(
            # Use input if not in metadata
            "stall_count") if classification_output else input_data.stall_count,
        stahla_event_duration_days=classification_output.metadata.get(
            "event_duration_days") if classification_output else input_data.duration_days,
        stahla_guest_count=classification_output.metadata.get(
            "guest_count") if classification_output else input_data.guest_count,
        stahla_ada_required=classification_output.metadata.get(
            "ada_required") if classification_output else input_data.ada_required,
        stahla_power_available=classification_output.metadata.get(
            "power_available") if classification_output else input_data.power_available,
        stahla_water_available=classification_output.metadata.get(
            "water_available") if classification_output else input_data.water_available,
        # Set pipeline/stage based on classification
        # Default or map from routing_suggestion?
        pipeline=settings.HUBSPOT_LEADS_PIPELINE_ID,
        dealstage=settings.HUBSPOT_NEW_LEAD_STAGE_ID  # Default or map?
        # Amount is intentionally omitted based on call script
    )

    # Remove None values before sending to HubSpot
    deal_props_dict = deal_props.model_dump(exclude_none=True, by_alias=True)
    deal_props_cleaned = HubSpotDealProperties(**deal_props_dict)

    deal_result = await hubspot_manager.create_deal(deal_props_cleaned, associated_contact_id=contact_id)

    if deal_result.status != "success" or not getattr(deal_result, 'id', None):
      logfire.error(
          "Failed to create HubSpot deal.",
          deal_name=deal_name,
          error=getattr(deal_result, 'message', 'Unknown error'),
          details=getattr(deal_result, 'details', None)
      )
      return contact_id, None

    deal_id = deal_result.id
    logfire.info("HubSpot deal created successfully.", deal_id=deal_id)

    # 3. Assign Owner & Update Pipeline/Stage (if needed, based on classification)
    # This logic can be combined with the update function or kept separate
    final_pipeline_id = None
    final_stage_id = None
    final_owner_id = None

    if classification_output:
      # Determine target pipeline/stage/owner based on classification
      if classification_output.lead_type == "Services":
        # Assumes you add this to config
        final_pipeline_id = settings.HUBSPOT_SERVICES_PIPELINE_ID
        final_stage_id = settings.HUBSPOT_SERVICES_NEW_STAGE_ID  # Assumes you add this
        # Assign owner based on team/logic
        final_owner_id = await hubspot_manager.get_next_owner_id()  # Example
      elif classification_output.lead_type == "Logistics":
        final_pipeline_id = settings.HUBSPOT_LOGISTICS_PIPELINE_ID  # Assumes you add this
        final_stage_id = settings.HUBSPOT_LOGISTICS_NEW_STAGE_ID  # Assumes you add this
        final_owner_id = await hubspot_manager.get_next_owner_id()  # Example
      elif classification_output.lead_type == "Leads":
        final_pipeline_id = settings.HUBSPOT_LEADS_PIPELINE_ID
        final_stage_id = settings.HUBSPOT_LEADS_NEW_STAGE_ID  # Assumes you add this
        # Maybe assign to a specific lead queue owner?
      elif classification_output.lead_type == "Disqualify":
        # Or a specific disqualified pipeline
        final_pipeline_id = settings.HUBSPOT_LEADS_PIPELINE_ID
        final_stage_id = settings.HUBSPOT_DISQUALIFIED_STAGE_ID

      if final_pipeline_id and final_stage_id:
        logfire.info(f"Updating pipeline/stage for new deal {deal_id}",
                     pipeline=final_pipeline_id, stage=final_stage_id, owner=final_owner_id)
        await hubspot_manager.update_deal_pipeline_and_owner(
            deal_id=deal_id,
            pipeline_id=final_pipeline_id,
            stage_id=final_stage_id,
            owner_id=final_owner_id
        )

    # 4. Trigger n8n Handoff (if not disqualified)
    if classification_output and classification_output.lead_type != LeadClassificationType.DISQUALIFY:
      logfire.info("Sending handoff data to n8n for new deal.",
                   contact_id=contact_id, deal_id=deal_id)
      # Ensure deal_result is the correct type
      if isinstance(deal_result, HubSpotDealResult):
        await trigger_n8n_handoff_automation(
            classification_result,
            input_data,
            contact_result,
            deal_result
        )
      else:
        logfire.error("Deal result was not the expected type for n8n handoff",
                      deal_result_type=type(deal_result))
    elif not classification_output:
      logfire.warn(
          "Skipping n8n handoff because classification output is missing.")
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.")

    return contact_id, deal_id

  except Exception as e:
    logfire.exception(
        "Unhandled error during HubSpot update process (new deal flow)")
    return contact_id, deal_id


# --- HubSpot Event Webhook Helpers ---

def _is_hubspot_contact_complete(contact_properties: dict) -> bool:
  """
  Check if the HubSpot contact properties contain the minimum required information.
  NEEDS CONFIRMATION FROM KEVIN/CLIENT - using a basic set for now.
  Uses HubSpot internal property names.
  """
  logfire.debug("Checking HubSpot contact completeness",
                properties=contact_properties)
  # Example: Require name, email, phone, service, address, start date
  # Use the internal names confirmed/provided by Kevin
  required_hubspot_properties = [
      contact_properties.get("firstname"),
      contact_properties.get("lastname"),
      contact_properties.get("email"),
      contact_properties.get("phone"),
      # Assumes this is the internal name
      contact_properties.get("stahla_service_needed"),
      contact_properties.get("event_or_job_address"),
      # Assumes this is the internal name
      contact_properties.get("stahla_event_start_date")
  ]
  is_complete = all(prop is not None and str(prop).strip() !=
                    "" for prop in required_hubspot_properties)
  logfire.info(f"HubSpot contact completeness check result: {is_complete}")
  return is_complete


async def _trigger_bland_call_for_hubspot(contact_id: str, deal_id: str, contact_properties: dict):
  """
  Triggers a Bland.ai call for an incomplete HubSpot contact/deal.
  Includes contact_id and deal_id in metadata.
  Uses HubSpot internal property names from contact_properties.
  """
  if not settings.BLAND_API_KEY:
    logfire.warn(
        "Bland API key not configured, skipping call for HubSpot lead.")
    return

  # Use internal names from contact_properties dict
  phone_number = contact_properties.get("phone")
  first_name = contact_properties.get("firstname", "Lead")
  # Use the confirmed internal names
  service_needed = contact_properties.get(
      "stahla_service_needed", "restroom solutions")
  event_address = contact_properties.get("event_or_job_address", "N/A")
  # event_type might not be directly on contact, may need fetching from deal or mapping
  # Assuming it exists on contact for now
  event_type = contact_properties.get("stahla_event_type", "N/A")

  if not phone_number:
    logfire.error(
        "Cannot trigger Bland call for HubSpot lead: Phone number is missing.",
        contact_id=contact_id,
        deal_id=deal_id
    )
    return

  task_description = f"Follow up with {first_name} regarding their interest in {service_needed}. "
  task_description += f"They submitted a HubSpot form. "
  # Removed event_type for now
  task_description += f"Key details provided: Event Address: {event_address}. "
  task_description += "Goal is to gather missing details (like duration, guest count, specific needs) and qualify the lead."

  metadata_to_pass = {
      "source": "hubspot_incomplete_lead",
      "hubspot_contact_id": contact_id,
      "hubspot_deal_id": deal_id,
      # Optionally pass specific properties needed for the call context
      # "initial_service_needed": service_needed
  }

  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhooks/voice"

  callback_request = BlandCallbackRequest(
      phone_number=phone_number,
      task=task_description,
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental inquiry you submitted through our website. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      amd=True,
      webhook=webhook_url,
      metadata=metadata_to_pass
  )

  logfire.info(
      f"Triggering Bland call for HubSpot lead {contact_id} to {phone_number}",
      task=task_description,
      deal_id=deal_id
  )
  try:
    call_result = await bland_manager.initiate_callback(callback_request)
    if call_result.status == "success":
      logfire.info("Bland call for HubSpot lead initiated successfully.",
                   call_id=call_result.call_id, contact_id=contact_id, deal_id=deal_id)
    else:
      logfire.error("Failed to initiate Bland call for HubSpot lead.",
                    error=call_result.message, details=call_result.details,
                    contact_id=contact_id, deal_id=deal_id)
  except Exception as e:
    logfire.exception("Error occurred while triggering Bland call for HubSpot lead",
                      contact_id=contact_id, deal_id=deal_id)


async def _update_hubspot_deal_after_classification(
    classification_result: ClassificationResult,
    input_data: ClassificationInput,
    contact_id: str,
    deal_id: str
):
  """
  Updates an *existing* HubSpot deal with classification results, assigns owner/pipeline/stage,
  and triggers n8n handoff. Used by HubSpot Event and Voice webhooks.
  """
  logfire.info("Entering _update_hubspot_deal_after_classification",
               contact_id=contact_id, deal_id=deal_id)

  classification_output = classification_result.classification
  if not classification_output:
    logfire.error("Classification output missing, cannot update HubSpot deal.",
                  contact_id=contact_id, deal_id=deal_id)
    return

  try:
    # 1. Prepare Deal Properties to Update using confirmed/suggested internal names
    properties_to_update = {
        # Map classification results to custom deal properties
        "stahla_ai_lead_type": classification_output.lead_type,
        "stahla_ai_reasoning": classification_output.reasoning,
        "stahla_ai_confidence": classification_output.confidence,
        "stahla_ai_routing_suggestion": classification_output.routing_suggestion,
        "stahla_ai_requires_review": classification_output.requires_human_review,
        # Map metadata fields
        "stahla_ai_is_local": classification_output.metadata.get("is_local"),
        "stahla_ai_intended_use": classification_output.metadata.get("intended_use"),
        "stahla_ai_qualification_notes": classification_output.metadata.get("qualification_notes"),
        "stahla_call_recording_url": classification_output.metadata.get("call_recording_url"),
        "stahla_call_summary": classification_output.metadata.get("call_summary"),
        "stahla_call_duration_seconds": classification_output.metadata.get("call_duration_seconds"),
        "stahla_stall_count": classification_output.metadata.get("stall_count"),
        "stahla_event_duration_days": classification_output.metadata.get("event_duration_days"),
        "stahla_guest_count": classification_output.metadata.get("guest_count"),
        "stahla_ada_required": classification_output.metadata.get("ada_required"),
        "stahla_power_available": classification_output.metadata.get("power_available"),
        "stahla_water_available": classification_output.metadata.get("water_available"),
        # Update standard deal fields if necessary (use with caution)
        # "dealname": f"{input_data.firstname or 'Lead'} ..." # Example: Update deal name
        # "start_date": input_data.event_start_date, # Update if gathered from call
        # "end_date": input_data.event_end_date,
        # "deal_address": input_data.event_address,
    }
    # Remove None values to avoid overwriting existing HubSpot data with null
    properties_to_update = {k: v for k,
                            v in properties_to_update.items() if v is not None}

    # 2. Determine Pipeline/Stage/Owner based on classification
    # ADD LOGIC TO GET ACTUAL PIPELINE/STAGE IDs FROM SETTINGS/HUBSPOT
    # Example: Fetch IDs based on names stored in classification_output.routing_suggestion
    # pipeline_id = await hubspot_manager.get_pipeline_id(classification_output.routing_suggestion)
    # stage_id = await hubspot_manager.get_stage_id(pipeline_id, "New Lead Stage Name") # Replace with actual stage name

    # Placeholder logic using settings - REPLACE with dynamic lookup or confirmed IDs
    final_pipeline_id = None
    final_stage_id = None
    final_owner_id = None

    if classification_output.lead_type == "Services":
      # Assumes you add this to config
      final_pipeline_id = settings.HUBSPOT_SERVICES_PIPELINE_ID
      final_stage_id = settings.HUBSPOT_SERVICES_NEW_STAGE_ID  # Assumes you add this
      final_owner_id = await hubspot_manager.get_next_owner_id()  # Example
    elif classification_output.lead_type == "Logistics":
      final_pipeline_id = settings.HUBSPOT_LOGISTICS_PIPELINE_ID  # Assumes you add this
      final_stage_id = settings.HUBSPOT_LOGISTICS_NEW_STAGE_ID  # Assumes you add this
      final_owner_id = await hubspot_manager.get_next_owner_id()  # Example
    elif classification_output.lead_type == "Leads":
      final_pipeline_id = settings.HUBSPOT_LEADS_PIPELINE_ID
      final_stage_id = settings.HUBSPOT_LEADS_NEW_STAGE_ID  # Assumes you add this
    elif classification_output.lead_type == "Disqualify":
      # Or a specific disqualified pipeline
      final_pipeline_id = settings.HUBSPOT_LEADS_PIPELINE_ID
      final_stage_id = settings.HUBSPOT_DISQUALIFIED_STAGE_ID

    if final_pipeline_id and final_stage_id:
      properties_to_update["pipeline"] = final_pipeline_id
      properties_to_update["dealstage"] = final_stage_id
    if final_owner_id:
      properties_to_update["hubspot_owner_id"] = final_owner_id

    # 3. Update Deal Properties in HubSpot
    if properties_to_update:
      update_result = await hubspot_manager.update_deal_properties(deal_id, properties_to_update)
      if update_result.status == "success":
        logfire.info(
            "HubSpot deal updated successfully with classification data.", deal_id=deal_id)
      else:
        logfire.error("Failed to update HubSpot deal properties.", deal_id=deal_id,
                      error=update_result.message, details=update_result.details)
    else:
      logfire.warn("No properties to update for HubSpot deal.",
                   deal_id=deal_id)

    # 4. Trigger n8n Handoff (if not disqualified)
    if classification_output.lead_type != LeadClassificationType.DISQUALIFY:
      logfire.info("Sending updated handoff data to n8n.",
                   contact_id=contact_id, deal_id=deal_id)
      # Fetch latest contact/deal data for n8n
      contact_result_for_n8n = await hubspot_manager.get_contact_by_id(contact_id)
      deal_result_for_n8n = await hubspot_manager.get_deal_by_id(deal_id)

      if contact_result_for_n8n.status == "success" and isinstance(deal_result_for_n8n, HubSpotDealResult):
        await trigger_n8n_handoff_automation(
            classification_result,
            input_data,
            contact_result_for_n8n,
            deal_result_for_n8n
        )
      else:
        logfire.error("Failed to fetch updated contact/deal details for n8n notification.",
                      contact_id=contact_id, deal_id=deal_id,
                      contact_error=getattr(
                          contact_result_for_n8n, 'message', 'N/A'),
                      deal_error=getattr(deal_result_for_n8n, 'message', 'N/A'))
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.", deal_id=deal_id)

  except Exception as e:
    logfire.exception("Unhandled error during HubSpot deal update process",
                      contact_id=contact_id, deal_id=deal_id)
