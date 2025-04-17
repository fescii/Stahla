# app/api/v1/endpoints/webhooks.py

from typing import Tuple, Optional
import logfire
from fastapi import APIRouter, Body, HTTPException, BackgroundTasks, Depends

# Import models
from app.models.webhook import FormPayload  # Corrected import
# Import BlandCallbackRequest
from app.models.bland import BlandWebhookPayload, BlandCallbackRequest
from app.models.email import EmailWebhookPayload, EmailProcessingResult
from app.models.classification import ClassificationInput, ClassificationResult, LeadClassificationType
from app.models.hubspot import HubSpotContactProperties, HubSpotDealProperties, HubSpotContactResult, HubSpotDealResult

# Import services
# Import the manager
from app.services.classify.classification import classification_manager
from app.services.bland import bland_manager
from app.services.hubspot import hubspot_manager
# Keep import for type hinting if needed
from app.services.email import EmailManager
from app.services.email import email_manager  # Import the singleton instance
from app.core.config import settings

# Import the new helper function
from app.api.v1.endpoints.prepare_classification_input import prepare_classification_input

router = APIRouter()

# --- Helper Functions ---


def _is_form_complete(payload: FormPayload) -> bool:  # Updated type hint
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


async def _trigger_bland_call(payload: FormPayload):  # Updated type hint
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
  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhook/voice"

  callback_request = BlandCallbackRequest(
      phone_number=phone_number,
      task=task_description,
      # Pass optional parameters if needed/configured
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental form you submitted. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      amd=True,  # Enable Answering Machine Detection if desired
      webhook=webhook_url,  # Explicitly set the webhook URL to our ngrok address
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


def _prepare_classification_input(source: str, raw_data: dict, extracted_data: dict) -> ClassificationInput:
  """Safely prepares ClassificationInput from extracted data."""
  logfire.debug(
      f"Preparing classification input from {source}", extracted_data=extracted_data)
  try:
    # Map extracted fields, providing defaults or None
    input_obj = ClassificationInput(
        source=source,
        firstname=extracted_data.get("firstname"),
        lastname=extracted_data.get("lastname"),
        email=extracted_data.get("email"),
        phone=extracted_data.get("phone"),
        company=extracted_data.get("company"),
        # Ensure product_interest is a list
        product_interest=extracted_data.get("product_interest", []) if isinstance(extracted_data.get("product_interest"), list) else [
            extracted_data.get("product_interest")] if extracted_data.get("product_interest") else [],
        event_type=extracted_data.get("event_type"),
        event_location_description=extracted_data.get(
            "event_location"),  # Map from 'event_location'
        duration_days=extracted_data.get("duration_days"),
        start_date=extracted_data.get("start_date"),
        end_date=extracted_data.get("end_date"),
        guest_count=extracted_data.get("guest_count"),
        required_stalls=extracted_data.get("required_stalls"),
        ada_required=extracted_data.get("ada_required"),
        budget_mentioned=extracted_data.get("budget_mentioned"),
        # May come from form metadata or voice extraction
        comments=extracted_data.get("comments"),
        power_available=extracted_data.get("power_available"),
        water_available=extracted_data.get("water_available"),
        # May come from form metadata
        source_url=extracted_data.get("source_url"),
        call_recording_url=extracted_data.get(
            "call_recording_url"),  # Specific to voice
        call_summary=extracted_data.get("call_summary"),  # Specific to voice
        raw_data=raw_data  # Include raw payload for context
    )
    return input_obj
  except Exception as e:
    logfire.error("Error preparing classification input",
                  exc_info=True, extracted_data=extracted_data)
    # Return a minimal input object or re-raise depending on desired handling
    # Returning minimal object to allow classification attempt with partial data
    return ClassificationInput(
        source=source,
        # Ensure at least email is present if possible
        email=extracted_data.get("email"),
        raw_data=raw_data,
        comments=f"Error preparing input: {e}"  # Add error note
    )


async def _handle_hubspot_update(
    classification_result: ClassificationResult,
    input_data: ClassificationInput
) -> Tuple[Optional[str], Optional[str]]:
  contact_id = None
  deal_id = None

  # --- Add detailed logging here ---
  logfire.info(
      "Entering _handle_hubspot_update",
      input_email=input_data.email,
      input_firstname=input_data.firstname,
      input_source=input_data.source,
      classification_lead_type=classification_result.classification.lead_type if classification_result.classification else "N/A"
  )
  # ---------------------------------

  try:
    # Check if classification actually happened
    classification_output = classification_result.classification
    if not classification_output:
      logfire.warn("Classification output missing, cannot determine lead type for HubSpot.",
                   input_email=input_data.email)
      # Decide how to handle - maybe skip deal creation or create with default type?
      # For now, let's proceed but log the warning. stahla_lead_type will be None.

    # 1. Create/Update Contact
    # --- Add logging right before creating contact props ---
    logfire.info(
        "Preparing HubSpotContactProperties",
        email_to_use=input_data.email,
        is_email_present=bool(input_data.email)
    )
    # -----------------------------------------------------
    contact_props = HubSpotContactProperties(
        email=input_data.email,
        firstname=input_data.firstname,
        lastname=input_data.lastname,
        phone=input_data.phone,
        stahla_lead_source=input_data.source.upper(),
        # Safely access lead_type
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
      # --- Add specific log for email missing error ---
      if not input_data.email:
        logfire.critical("HubSpot contact failed specifically because input_data.email was missing!",
                         input_data_dump=input_data.model_dump())
      # ----------------------------------------------
      return None, None  # Exit early if contact fails

    contact_id = contact_result.id
    logfire.info("HubSpot contact created/updated successfully.",
                 contact_id=contact_id)

    # Check if this is an existing contact or new contact based on timestamps
    # Use the presence of created_at and updated_at fields to determine if it's a new or existing contact
    # If created_at and updated_at are very close in time, it's likely a new contact
    # Otherwise, if updated_at is significantly later than created_at, it's an existing contact
    created_at = getattr(contact_result, 'created_at', None)
    updated_at = getattr(contact_result, 'updated_at', None)

    # Use the internal name values that HubSpot expects: "newbusiness" or "existingbusiness"
    deal_type = "newbusiness"  # Default to "newbusiness"
    logfire.info(f"Setting deal type to {deal_type}",
                 created_at=created_at, updated_at=updated_at)

    # 2. Create Deal (only if contact succeeded)
    deal_name = f"{input_data.firstname or 'Lead'} {input_data.lastname or ''} - {input_data.product_interest[0] if input_data.product_interest else 'Inquiry'}".strip(
    )
    # Safely access estimated_deal_value from classification metadata
    estimated_value = classification_output.metadata.get(
        "estimated_value") if classification_output and classification_output.metadata else None

    deal_props = HubSpotDealProperties(
        dealname=deal_name,
        # pipeline=settings.HUBSPOT_LEADS_PIPELINE_ID, # Use ID if configured
        # dealstage=settings.HUBSPOT_NEW_LEAD_STAGE_ID, # Use ID if configured
        amount=estimated_value,  # Use safely accessed value
        # closedate=... # Set if applicable
        dealtype=deal_type,  # Set to "Existing Business" or "New Business" based on contact status
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
      return contact_id, None  # Exit early if deal fails

    deal_id = deal_result.id
    logfire.info("HubSpot deal created successfully.", deal_id=deal_id)

    # 3. Assign Owner (Optional, if applicable)
    # owner_id = classification_result.classification.suggested_owner_id
    # if owner_id:
    #     await hubspot_manager.assign_owner("deal", deal_id, owner_id)
    #     await hubspot_manager.assign_owner("contact", contact_id, owner_id)

    # --- Send Handoff Notification (Only if BOTH contact and deal succeeded) --- #
    # Ensure classification_output exists before sending notification
    if classification_output and classification_output.lead_type != "Disqualify":
      logfire.info("Sending handoff notification.",
                   contact_id=contact_id, deal_id=deal_id)
      # Use the singleton email_manager instance
      await email_manager.send_handoff_notification(
          classification_result,
          contact_result,  # Pass the successful contact result object
          deal_result     # Pass the successful deal result object
      )
    elif not classification_output:
      logfire.warn(
          "Skipping handoff notification because classification output is missing.")
    else:  # Disqualified
      logfire.info(
          "Skipping handoff notification because lead was disqualified.")
    # ------------------------------------------------------------------------- #

    return contact_id, deal_id

  except Exception as e:
    logfire.exception("Unhandled error during HubSpot update process")
    # Ensure we return None, None in case of unexpected errors before success
    return contact_id, deal_id  # Return whatever IDs were obtained before the error

# --- Webhook Endpoints ---


@router.post("/form", summary="Process Form Submissions")
async def webhook_form(
    payload: FormPayload = Body(...),  # Updated type hint
    background_tasks: BackgroundTasks = BackgroundTasks()
):
  """
  Receives form submission data, checks completeness, triggers classification,
  and updates HubSpot. If incomplete, triggers a Bland.ai call.
  """
  logfire.info("Received form webhook payload.",
               form_data=payload.model_dump(exclude_none=True))

  # Check if the form has the minimum required data
  if not _is_form_complete(payload):
    logfire.warn("Form data incomplete. Triggering Bland.ai callback.")
    # Trigger Bland.ai call in the background
    background_tasks.add_task(_trigger_bland_call, payload)
    # Return a response indicating the call is being made
    return {"status": "incomplete", "message": "Form incomplete, initiating follow-up call."}

  logfire.info("Form data complete, proceeding to classification.")

  # Correctly access potential extra fields like 'source_url' before creating ClassificationInput
  source_url_value = getattr(payload, 'source_url', None)
  source_url_for_input = str(
      source_url_value) if source_url_value is not None else None

  # Convert FormPayload to ClassificationInput
  # Assuming FormPayload fields align well with ClassificationInput
  # Include raw data from the payload
  raw_data = payload.model_dump(mode='json')

  classification_input = ClassificationInput(
      source="webform",  # Must be one of: "webform", "voice", or "email"
      raw_data=raw_data,  # Include required raw_data field
      # Map fields directly
      firstname=payload.firstname,
      lastname=payload.lastname,
      email=payload.email,
      phone=payload.phone,
      company=payload.company,
      # Convert to list
      product_interest=[
          payload.product_interest] if payload.product_interest else [],
      event_type=payload.event_type,
      event_location_description=payload.event_location_description,
      event_state=payload.event_state,
      duration_days=payload.duration_days,
      start_date=payload.start_date,
      end_date=payload.end_date,
      guest_count=payload.guest_count,
      required_stalls=payload.required_stalls,
      ada_required=payload.ada_required,
      budget_mentioned=payload.budget_mentioned,
      comments=payload.comments,
      power_available=payload.power_available,
      water_available=payload.water_available,
      # Pass the extracted source_url
      source_url=source_url_for_input
  )

  # Trigger classification using the manager
  classification_result = await classification_manager.classify_lead_data(classification_input)
  logfire.info("Classification result received.",
               classification=classification_result.model_dump(exclude_none=True))

  # --- HubSpot Integration --- #
  # Only call HubSpot if classification was successful and no error was detected
  classification_output = classification_result.classification
  if classification_output and not (
      classification_output.metadata and
      classification_output.metadata.get("error_type")
  ):
    # Trigger HubSpot update in the background
    background_tasks.add_task(_handle_hubspot_update,
                              classification_result, classification_input)
    hubspot_status = "initiated"
  else:
    logfire.warn(
        "Skipping HubSpot update due to classification errors or missing data",
        errors=classification_output.metadata if classification_output else None,
        input_email=classification_input.email
    )
    hubspot_status = "skipped"
  # ------------------------- #

  # Return classification result (or a success message)
  return {
      "status": "success",
      "message": "Form processed and classification initiated.",
      "classification_result": classification_result.model_dump(exclude_none=True)
  }


@router.post(
    "/voice",
    summary="Receive Voice Transcripts from Bland.ai",
    # response_model=BlandApiResult # Keep response flexible for now
)
async def webhook_voice(
    payload: BlandWebhookPayload = Body(...)
):
  """
  Handles incoming webhook submissions containing voice transcripts from Bland.ai.
  Processes the transcript, extracts data, and sends for classification.
  """
  logfire.info("Received voice webhook payload via API.",
               call_id=payload.call_id)

  # Call the manager's method to process the transcript (extracts info)
  processing_result = await bland_manager.process_incoming_transcript(payload)

  if processing_result.status == "error":
    logfire.error("Failed to process Bland transcript.",
                  call_id=payload.call_id, message=processing_result.message)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=processing_result.message or "Failed to process voice transcript."
    )

  logfire.info("Bland transcript processed, proceeding to classification.",
               call_id=payload.call_id)

  # Prepare data for classification service using extracted data
  extracted_data = processing_result.details.get("extracted_data", {})
  raw_data = payload.model_dump(mode='json')

  # Debug what's available in the payload
  logfire.info(
      "Examining Bland.ai webhook payload structure",
      has_metadata=bool(getattr(payload, 'metadata', None)),
      has_variables=bool(getattr(payload, 'variables', None)),
      metadata_keys=list(payload.metadata.keys()) if getattr(
          payload, 'metadata', None) else [],
      variables_keys=list(payload.variables.keys()) if getattr(
          payload, 'variables', None) else []
  )

  # Extract email from ALL possible locations (both direct metadata and variables.metadata)
  # Prioritize metadata form data OVER transcript extracted data for fields like email
  merged_data = {}

  # 1. Start with extracted data from transcript processing
  merged_data.update(extracted_data)
  logfire.info("Initial merged_data from transcript extraction",
               data_keys=list(merged_data.keys()))

  # 2. Check variables.metadata.form_submission_data (nested path) - OVERWRITE if present
  if getattr(payload, 'variables', None) and isinstance(payload.variables, dict):
    if payload.variables.get('metadata', None) and isinstance(payload.variables['metadata'], dict):
      nested_form_data = payload.variables['metadata'].get(
          'form_submission_data', {})
      if nested_form_data:
        logfire.info("Found form_submission_data in variables.metadata, updating merged_data",
                     has_email=bool(nested_form_data.get('email')),
                     nested_form_data_keys=list(nested_form_data.keys()))
        # Update, potentially overwriting transcript data
        merged_data.update(nested_form_data)

  # 3. Check metadata.form_submission_data (direct path) - OVERWRITE if present (Highest priority)
  if getattr(payload, 'metadata', None) and isinstance(payload.metadata, dict):
    form_data = payload.metadata.get('form_submission_data', {})
    if form_data:
      logfire.info("Found form_submission_data in metadata, updating merged_data",
                   has_email=bool(form_data.get('email')),
                   form_data_keys=list(form_data.keys()))
      # Update, potentially overwriting transcript & variables data
      merged_data.update(form_data)

  # Add call-specific details to merged_data if available in payload
  # Ensure these don't overwrite critical fields if keys conflict (unlikely for these keys)
  merged_data.setdefault("call_recording_url",
                         getattr(payload, 'recording_url', None))
  merged_data.setdefault("call_summary", getattr(payload, 'summary', None))

  # Log the final data we're about to classify
  logfire.info("Final data prepared for classification",
               has_email=bool(merged_data.get('email')),
               email=merged_data.get('email'),  # Log the actual email value
               merged_data_keys=list(merged_data.keys()))

  # Use the prepare_classification_input function
  classification_input = prepare_classification_input(
      source="voice",
      raw_data=raw_data,
      extracted_data=merged_data
  )

  # Log the email to debug AFTER prepare_classification_input
  logfire.info("Created classification input for voice webhook",
               email=classification_input.email,
               has_email=bool(classification_input.email))

  # Use the singleton classification_manager instance
  classification_result = await classification_manager.classify_lead_data(classification_input)
  logfire.info("Classification result received.",
               result=classification_result.model_dump(exclude={"input_data"}))

  # --- HubSpot Integration --- #
  # Ensure classification_input is passed here as well
  contact_id, deal_id = await _handle_hubspot_update(classification_result, classification_input)
  # ------------------------- #

  return {
      "status": "received",
      "source": "voice",
      "action": "classification_complete",
      "classification": classification_result.classification.model_dump() if classification_result.classification else None,
      "hubspot_contact_id": contact_id,
      "hubspot_deal_id": deal_id
  }


@router.post("/email", summary="Process Incoming Emails", response_model=EmailProcessingResult)
async def webhook_email(
    payload: EmailWebhookPayload = Body(...)
):
  """
  Handles incoming webhook submissions for emails.
  Calls the EmailManager to parse, check completeness, potentially auto-reply,
  and eventually send for classification.
  """
  logfire.info("Received email webhook payload.",
               message_id=payload.message_id)

  # Call the EmailManager service
  processing_result = await email_manager.process_incoming_email(payload)

  if processing_result.status == "error":
    logfire.error("Failed to process email.",
                  message_id=payload.message_id, message=processing_result.message)
    # Decide on error response - 500 might cause retries from the webhook source
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=processing_result.message or "Failed to process email."
    )
  elif processing_result.status == "success" and processing_result.classification_pending:
    logfire.info("Email processed, proceeding to classification.",
                 message_id=payload.message_id)
    # Prepare data for classification service
    extracted_data = processing_result.extracted_data or {}
    raw_data = payload.model_dump(mode='json')

    # Use the new prepare_classification_input function instead of _prepare_classification_input
    classification_input = prepare_classification_input(
        source="email",
        raw_data=raw_data,
        extracted_data=extracted_data
    )

    # Use the singleton classification_manager instance
    classification_result = await classification_manager.classify_lead_data(classification_input)
    logfire.info("Classification result received.",
                 result=classification_result.model_dump(exclude={"input_data"}))

    # --- HubSpot Integration --- #
    # Ensure classification_input is passed here as well
    contact_id, deal_id = await _handle_hubspot_update(classification_result, classification_input)
    # ------------------------- #

    # Update the processing result to include classification info and HubSpot IDs
    processing_result.details = {
        "classification": classification_result.classification.model_dump() if classification_result.classification else None,
        "hubspot_contact_id": contact_id,
        "hubspot_deal_id": deal_id
    }
    processing_result.message = "Email processed, classified, and HubSpot updated."

  # Return the result from the EmailManager (or updated result after classification/HubSpot)
  return processing_result
