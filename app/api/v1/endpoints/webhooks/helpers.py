# app/api/v1/endpoints/webhooks/helpers.py

from typing import Tuple, Optional, Dict, Any
import logfire
from fastapi import BackgroundTasks  # Added BackgroundTasks

# Import models
from app.models.webhook import FormPayload
from app.models.bland import BlandCallbackRequest
from app.models.classification import ClassificationInput, ClassificationResult, LeadClassificationType
from app.models.hubspot import HubSpotContactProperties, HubSpotDealProperties, HubSpotContactResult, HubSpotDealResult

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
  Based on PRD: phone, email, product_interest, event_location_description, event_type
  """
  required_fields = [
      payload.phone,
      payload.email,
      payload.product_interest,
      payload.event_location_description,
      payload.event_type
  ]
  # Check if all required fields are present and not empty strings
  return all(field is not None and field != "" for field in required_fields)


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


# --- General HubSpot Update Helper (Used by Form, Voice, Email) ---

async def _handle_hubspot_update(
    classification_result: ClassificationResult,
    input_data: ClassificationInput
) -> Tuple[Optional[str], Optional[str]]:
  contact_id = None
  deal_id = None

  logfire.info(
      "Entering _handle_hubspot_update",
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

    logfire.info(
        "Preparing HubSpotContactProperties",
        email_to_use=input_data.email,
        is_email_present=bool(input_data.email)
    )
    contact_props = HubSpotContactProperties(
        email=input_data.email,
        firstname=input_data.firstname,
        lastname=input_data.lastname,
        phone=input_data.phone,
        stahla_lead_source=input_data.source.upper(),
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
                         input_data_dump=input_data.model_dump())
      return None, None

    contact_id = contact_result.id
    logfire.info("HubSpot contact created/updated successfully.",
                 contact_id=contact_id)

    created_at = getattr(contact_result, 'created_at', None)
    updated_at = getattr(contact_result, 'updated_at', None)
    deal_type = "newbusiness"
    logfire.info(f"Setting deal type to {deal_type}",
                 created_at=created_at, updated_at=updated_at)

    deal_name = f"{input_data.firstname or 'Lead'} {input_data.lastname or ''} - {input_data.product_interest[0] if input_data.product_interest else 'Inquiry'}".strip(
    )
    estimated_value = classification_output.metadata.get(
        "estimated_value") if classification_output and classification_output.metadata else None

    deal_props = HubSpotDealProperties(
        dealname=deal_name,
        amount=estimated_value,
        dealtype=deal_type,
        stahla_product_interest=", ".join(
            input_data.product_interest) if input_data.product_interest else None,
        stahla_event_location=input_data.event_location_description,
        stahla_duration=str(
            input_data.duration_days) if input_data.duration_days else None,
        stahla_stall_count=input_data.required_stalls,
        stahla_budget_info=input_data.budget_mentioned,
        stahla_guest_count=input_data.guest_count,
        stahla_event_type=input_data.event_type,
    )

    deal_result = await hubspot_manager.create_deal(deal_props, associated_contact_id=contact_id)

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

    if classification_output and classification_output.lead_type != LeadClassificationType.DISQUALIFY:
      logfire.info("Sending handoff data to n8n.",
                   contact_id=contact_id, deal_id=deal_id)
      await trigger_n8n_handoff_automation(
          classification_result,
          input_data,
          contact_result,
          deal_result
      )
    elif not classification_output:
      logfire.warn(
          "Skipping n8n handoff because classification output is missing.")
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.")

    return contact_id, deal_id

  except Exception as e:
    logfire.exception("Unhandled error during HubSpot update process")
    return contact_id, deal_id


# --- HubSpot Event Webhook Helpers ---

def _is_hubspot_contact_complete(contact_properties: dict) -> bool:
  """
  Check if the HubSpot contact properties contain the minimum required information.
  Adapt required fields based on what's expected from the HubSpot form/lead.
  NOTE: Property names here are HubSpot internal names (e.g., 'stahla_product_interest').
  """
  logfire.debug("Checking HubSpot contact completeness",
                properties=contact_properties)
  required_hubspot_properties = [
      contact_properties.get("phone"),
      contact_properties.get("email"),
      contact_properties.get("stahla_product_interest"),
      contact_properties.get("stahla_event_location"),
      contact_properties.get("stahla_event_type")
  ]
  is_complete = all(prop is not None and prop !=
                    "" for prop in required_hubspot_properties)
  logfire.info(f"HubSpot contact completeness check result: {is_complete}")
  return is_complete


async def _trigger_bland_call_for_hubspot(contact_id: str, deal_id: str, contact_properties: dict):
  """
  Triggers a Bland.ai call for an incomplete HubSpot contact.
  Includes contact_id and deal_id in metadata.
  """
  if not settings.BLAND_API_KEY:
    logfire.warn(
        "Bland API key not configured, skipping call for HubSpot lead.")
    return

  phone_number = contact_properties.get("phone")
  first_name = contact_properties.get("firstname", "Lead")
  product_interest = contact_properties.get(
      "stahla_product_interest", "restroom solutions")
  event_type = contact_properties.get("stahla_event_type", "N/A")
  event_location = contact_properties.get("stahla_event_location", "N/A")

  if not phone_number:
    logfire.error(
        "Cannot trigger Bland call for HubSpot lead: Phone number is missing.",
        contact_id=contact_id,
        deal_id=deal_id
    )
    return

  task_description = f"Follow up with {first_name} regarding their interest in {product_interest}. "
  task_description += f"They submitted a HubSpot form. "
  task_description += f"Key details provided: Event Type: {event_type}, Location: {event_location}. "
  task_description += "Goal is to gather missing details (like duration, guest count, specific needs) and qualify the lead."

  metadata_to_pass = {
      "source": "hubspot_incomplete_lead",
      "hubspot_contact_id": contact_id,
      "hubspot_deal_id": deal_id,
  }

  # NOTE: Ensure the path is correct (/voice, not /webhook/voice)
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
    properties_to_update = {
        "stahla_lead_type": classification_output.lead_type,
        "stahla_estimated_value": classification_output.metadata.get("estimated_value"),
        "stahla_qualification_notes": classification_output.metadata.get("qualification_notes"),
        "stahla_product_interest": ", ".join(input_data.product_interest) if input_data.product_interest else None,
        "stahla_event_location": input_data.event_location_description,
        "stahla_duration": str(input_data.duration_days) if input_data.duration_days else None,
        "stahla_stall_count": input_data.required_stalls,
        "stahla_budget_info": input_data.budget_mentioned,
        "stahla_guest_count": input_data.guest_count,
        "stahla_event_type": input_data.event_type,
        "stahla_call_recording_url": input_data.call_recording_url,
        "stahla_call_summary": input_data.call_summary,
    }
    properties_to_update = {k: v for k,
                            v in properties_to_update.items() if v is not None}

    pipeline_id = settings.HUBSPOT_LEADS_PIPELINE_ID
    stage_id = None
    owner_id = None

    if classification_output.lead_type == LeadClassificationType.HOT_LEAD:
      stage_id = settings.HUBSPOT_HOT_LEAD_STAGE_ID
      owner_id = await hubspot_manager.get_next_owner_id()
    elif classification_output.lead_type == LeadClassificationType.WARM_LEAD:
      stage_id = settings.HUBSPOT_WARM_LEAD_STAGE_ID
      owner_id = await hubspot_manager.get_next_owner_id()
    elif classification_output.lead_type == LeadClassificationType.COLD_LEAD:
      stage_id = settings.HUBSPOT_COLD_LEAD_STAGE_ID
    elif classification_output.lead_type == LeadClassificationType.DISQUALIFY:
      stage_id = settings.HUBSPOT_DISQUALIFIED_STAGE_ID
    else:
      stage_id = settings.HUBSPOT_NEEDS_REVIEW_STAGE_ID

    if pipeline_id and stage_id:
      properties_to_update["pipeline"] = pipeline_id
      properties_to_update["dealstage"] = stage_id
    if owner_id:
      properties_to_update["hubspot_owner_id"] = owner_id

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

    if classification_output.lead_type != LeadClassificationType.DISQUALIFY:
      logfire.info("Sending updated handoff data to n8n.",
                   contact_id=contact_id, deal_id=deal_id)
      contact_result_for_n8n = await hubspot_manager.get_contact_by_id(contact_id)
      deal_result_for_n8n = await hubspot_manager.get_deal_by_id(deal_id)

      if contact_result_for_n8n.status == "success" and deal_result_for_n8n.status == "success":
        if isinstance(deal_result_for_n8n, HubSpotDealResult):
          await trigger_n8n_handoff_automation(
              classification_result,
              input_data,
              contact_result_for_n8n,
              deal_result_for_n8n
          )
        else:
          logfire.error("Failed to fetch updated deal details for n8n notification.",
                        deal_id=deal_id, error=deal_result_for_n8n.message)
      else:
        logfire.error("Failed to fetch updated contact/deal details for n8n notification.",
                      contact_id=contact_id, deal_id=deal_id)
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.", deal_id=deal_id)

  except Exception as e:
    logfire.exception("Unhandled error during HubSpot deal update process",
                      contact_id=contact_id, deal_id=deal_id)
