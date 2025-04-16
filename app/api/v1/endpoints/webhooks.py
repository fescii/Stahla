# app/api/v1/endpoints/webhooks.py

from typing import Tuple, Optional
import logfire
from fastapi import APIRouter, Body, HTTPException, BackgroundTasks, Depends

# Import models
from app.models.webhook import FormPayload # Corrected import
from app.models.bland import BlandWebhookPayload
from app.models.email import EmailWebhookPayload, EmailProcessingResult
from app.models.classification import ClassificationInput, ClassificationResult, LeadClassificationType
from app.models.hubspot import HubSpotContactProperties, HubSpotDealProperties, HubSpotContactResult, HubSpotDealResult

# Import services
from app.services.classification import classify_lead
from app.services.bland import bland_manager
from app.services.hubspot import hubspot_manager
from app.services.email import EmailManager
from app.core.config import settings

router = APIRouter()

# --- Helper Functions ---

def _is_form_complete(payload: FormPayload) -> bool: # Updated type hint
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

async def _trigger_bland_call(payload: FormPayload): # Updated type hint
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
    task_description += f"They submitted an incomplete form from {payload.source_url or 'the website'}. "
    task_description += f"Key details provided: Event Type: {payload.event_type or 'N/A'}, Location: {payload.event_location_description or 'N/A'}. "
    task_description += "Goal is to gather missing details (like duration, guest count, specific needs) and qualify the lead."

    if not phone_number:
        logfire.error("Cannot trigger Bland call: Phone number is missing.", email=payload.email)
        return

    logfire.info(f"Triggering Bland call to {phone_number}")
    try:
        call_result = await bland_manager.make_call(
            phone_number=phone_number,
            task=task_description,
            # Use first name if available for personalization
            first_name=first_name,
            # Add other relevant data to pass to Bland if needed
            # request_data={
            #     "email": payload.email,
            #     "product_interest": payload.product_interest,
            # }
        )
        if call_result.get("status") == "success":
            logfire.info("Bland call initiated successfully.", call_id=call_result.get("call_id"))
        else:
            logfire.error("Failed to initiate Bland call.", error=call_result.get("message"))
    except Exception as e:
        logfire.exception("Error occurred while triggering Bland call")

async def _handle_hubspot_update(
    classification_result: ClassificationResult, 
    input_data: ClassificationInput
) -> Tuple[Optional[str], Optional[str]]:
    email_manager = EmailManager() # Keep this instantiation if EmailManager is not a singleton
    contact_id = None
    deal_id = None

    try:
        # 1. Create/Update Contact
        contact_props = HubSpotContactProperties(
            email=input_data.email,
            firstname=input_data.firstname,
            lastname=input_data.lastname,
            phone=input_data.phone,
            stahla_lead_source=input_data.source.upper(),
            stahla_lead_type=classification_result.classification.lead_type if classification_result.classification else None
        )
        contact_result = await hubspot_manager.create_or_update_contact(contact_props)
        
        if contact_result.status != "success" or not getattr(contact_result, 'id', None):
            logfire.error(
                "Failed to create or update HubSpot contact.", 
                email=input_data.email, 
                error=getattr(contact_result, 'message', 'Unknown error'),
                details=getattr(contact_result, 'details', None)
            )
            return None, None # Exit early if contact fails

        contact_id = contact_result.id 
        logfire.info("HubSpot contact created/updated successfully.", contact_id=contact_id)

        # 2. Create Deal (only if contact succeeded)
        deal_name = f"{input_data.firstname or 'Lead'} {input_data.lastname or ''} - {input_data.product_interest[0] if input_data.product_interest else 'Inquiry'}".strip()
        deal_props = HubSpotDealProperties(
            dealname=deal_name,
            # pipeline=settings.HUBSPOT_LEADS_PIPELINE_ID, # Use ID if configured
            # dealstage=settings.HUBSPOT_NEW_LEAD_STAGE_ID, # Use ID if configured
            amount=classification_result.classification.estimated_deal_value if classification_result.classification else None,
            # closedate=... # Set if applicable
            stahla_product_interest=", ".join(input_data.product_interest) if input_data.product_interest else None,
            stahla_event_location=input_data.event_location_description,
            stahla_duration=str(input_data.duration_days) if input_data.duration_days else None,
            stahla_stall_count=input_data.required_stalls,
            stahla_budget_info=input_data.budget_mentioned,
            stahla_guest_count=input_data.guest_count,
            stahla_event_type=input_data.event_type,
            # Add other relevant deal properties from input_data
        )

        deal_result = await hubspot_manager.create_deal(deal_props, associated_contact_id=contact_id)

        if deal_result.status != "success" or not getattr(deal_result, 'id', None):
            logfire.error(
                "Failed to create HubSpot deal.", 
                deal_name=deal_name, 
                error=getattr(deal_result, 'message', 'Unknown error'),
                details=getattr(deal_result, 'details', None)
            )
            # Don't send notification if deal fails, but return the contact_id
            return contact_id, None # Exit early if deal fails

        deal_id = deal_result.id
        logfire.info("HubSpot deal created successfully.", deal_id=deal_id)

        # 3. Assign Owner (Optional, if applicable)
        # owner_id = classification_result.classification.suggested_owner_id
        # if owner_id:
        #     await hubspot_manager.assign_owner("deal", deal_id, owner_id)
        #     await hubspot_manager.assign_owner("contact", contact_id, owner_id)

        # --- Send Handoff Notification (Only if BOTH contact and deal succeeded) --- #
        logfire.info("Sending handoff notification.", contact_id=contact_id, deal_id=deal_id)
        await email_manager.send_handoff_notification(
            classification_result, 
            contact_result, # Pass the successful contact result object
            deal_result     # Pass the successful deal result object
        )
        # ------------------------------------------------------------------------- #

        return contact_id, deal_id

    except Exception as e:
        logfire.exception("Unhandled error during HubSpot update process")
        # Ensure we return None, None in case of unexpected errors before success
        return contact_id, deal_id # Return whatever IDs were obtained before the error
    finally:
        # Close the email client if it was initialized here
        await email_manager.close_client()
        # Do NOT close the singleton hubspot_manager client here, manage its lifecycle elsewhere (e.g., app startup/shutdown)
        pass

# --- Webhook Endpoints ---

@router.post("/form", summary="Process Form Submissions")
async def webhook_form(
    payload: FormPayload = Body(...), # Updated type hint
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Receives form submission data, checks completeness, triggers classification,
    and updates HubSpot. If incomplete, triggers a Bland.ai call.
    """
    logfire.info("Received form webhook payload.", form_data=payload.model_dump(exclude_none=True))

    # Check if the form has the minimum required data
    if not _is_form_complete(payload):
        logfire.warn("Form data incomplete. Triggering Bland.ai callback.")
        # Trigger Bland.ai call in the background
        background_tasks.add_task(_trigger_bland_call, payload)
        # Return a response indicating the call is being made
        return {"status": "incomplete", "message": "Form incomplete, initiating follow-up call."}

    logfire.info("Form data complete, proceeding to classification.")

    # Convert FormPayload to ClassificationInput
    # Assuming FormPayload fields align well with ClassificationInput
    classification_input = ClassificationInput(
        source="form",
        # Map fields directly
        firstname=payload.firstname,
        lastname=payload.lastname,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        product_interest=[payload.product_interest] if payload.product_interest else [], # Convert to list
        event_type=payload.event_type,
        event_location_description=payload.event_location_description,
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
        # Add any other relevant fields from FormPayload
        source_url=str(payload.Config.extra.get('source_url')) if hasattr(payload.Config, 'extra') and payload.Config.extra.get('source_url') else None # Example for extra field
    )

    # Trigger classification
    classification_result = await classify_lead(classification_input)
    logfire.info("Classification result received.", classification=classification_result.model_dump(exclude_none=True))

    # --- HubSpot Integration --- #
    # Trigger HubSpot update in the background
    background_tasks.add_task(_handle_hubspot_update, classification_result, classification_input)
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
    logfire.info("Received voice webhook payload via API.", call_id=payload.call_id)

    # Call the manager's method to process the transcript (extracts info)
    processing_result = await bland_manager.process_incoming_transcript(payload)

    if processing_result.status == "error":
        logfire.error("Failed to process Bland transcript.", call_id=payload.call_id, message=processing_result.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=processing_result.message or "Failed to process voice transcript."
        )

    logfire.info("Bland transcript processed, proceeding to classification.", call_id=payload.call_id)

    # Prepare data for classification service using extracted data
    extracted_data = processing_result.details.get("extracted_data", {})
    raw_data = payload.model_dump(mode='json')

    # If this call originated from a form, merge original form data from metadata
    original_form_data = payload.metadata.get("form_submission_data", {}) if payload.metadata else {}
    merged_data = {**original_form_data, **extracted_data} # Voice data overrides form data if keys conflict

    classification_input = _prepare_classification_input(
        source="voice",
        raw_data=raw_data,
        extracted_data=merged_data
    )

    classification_result = await classification_manager.classify_lead_data(classification_input)
    logfire.info("Classification result received.", result=classification_result.model_dump(exclude={"input_data"}))

    # --- HubSpot Integration --- #
    # Ensure classification_input is passed here as well
    contact_id, deal_id = await _handle_hubspot_update(classification_result, classification_input)
    # ------------------------- #

    return {
        "status": "received",
        "source": "voice",
        "action": "classification_complete",
        "classification": classification_result.output.model_dump() if classification_result.output else None,
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
    logfire.info("Received email webhook payload.", message_id=payload.message_id)

    # Call the EmailManager service
    processing_result = await email_manager.process_incoming_email(payload)

    if processing_result.status == "error":
        logfire.error("Failed to process email.", message_id=payload.message_id, message=processing_result.message)
        # Decide on error response - 500 might cause retries from the webhook source
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=processing_result.message or "Failed to process email."
        )
    elif processing_result.status == "success" and processing_result.classification_pending:
        logfire.info("Email processed, proceeding to classification.", message_id=payload.message_id)
        # Prepare data for classification service
        extracted_data = processing_result.extracted_data or {}
        raw_data = payload.model_dump(mode='json')

        classification_input = _prepare_classification_input(
            source="email",
            raw_data=raw_data,
            extracted_data=extracted_data
        )

        classification_result = await classification_manager.classify_lead_data(classification_input)
        logfire.info("Classification result received.", result=classification_result.model_dump(exclude={"input_data"}))

        # --- HubSpot Integration --- #
        # Ensure classification_input is passed here as well
        contact_id, deal_id = await _handle_hubspot_update(classification_result, classification_input)
        # ------------------------- #

        # Update the processing result to include classification info and HubSpot IDs
        processing_result.details = {
            "classification": classification_result.output.model_dump() if classification_result.output else None,
            "hubspot_contact_id": contact_id,
            "hubspot_deal_id": deal_id
        }
        processing_result.message = "Email processed, classified, and HubSpot updated."

    # Return the result from the EmailManager (or updated result after classification/HubSpot)
    return processing_result
