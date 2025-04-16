# app/api/v1/endpoints/webhooks.py

from fastapi import APIRouter, Request, HTTPException, status, Body
from typing import Any, Dict, List, Literal, Optional # Added Optional
import logfire

# Import Pydantic models
from app.models.webhook import FormPayload
from app.models.bland import BlandWebhookPayload, BlandApiResult, BlandCallbackRequest
from app.models.email import EmailWebhookPayload, EmailProcessingResult
from app.models.classification import ClassificationInput, ClassificationResult, LeadClassificationType
from app.models.hubspot import HubSpotContactProperties, HubSpotDealProperties, HubSpotContactResult, HubSpotDealResult # Added Result models

# Import Services
from app.services.bland import bland_manager
from app.services.email import email_manager
from app.services.classification import classification_manager
from app.services.hubspot import hubspot_manager # Import HubSpot manager
from app.core.config import settings

router = APIRouter()

def _prepare_classification_input(source: Literal["webform", "voice", "email"], raw_data: Dict, extracted_data: Dict) -> ClassificationInput:
    """Helper function to create ClassificationInput model with all required fields for lead classification."""
    # Map extracted data to ClassificationInput fields
    # Extract product_interest from string to list if needed
    product_interest = extracted_data.get("product_interest")
    if isinstance(product_interest, str):
        # Convert comma or semicolon separated string to list
        product_interest = [p.strip() for p in product_interest.split(',')]
    elif not isinstance(product_interest, list):
        product_interest = []
        
    return ClassificationInput(
        source=source,
        raw_data=raw_data,
        extracted_data=extracted_data,
        # --- Map common fields ---
        firstname=extracted_data.get("firstname") or extracted_data.get("first_name"),
        lastname=extracted_data.get("lastname") or extracted_data.get("last_name"),
        email=extracted_data.get("email"),
        phone=extracted_data.get("phone") or extracted_data.get("phone_number"),
        company=extracted_data.get("company"),
        product_interest=product_interest,
        required_stalls=extracted_data.get("required_stalls") or extracted_data.get("stalls"),
        ada_required=extracted_data.get("ada_required"),
        event_type=extracted_data.get("event_type"),
        event_location_description=extracted_data.get("event_location") or extracted_data.get("location"),
        duration_days=extracted_data.get("duration_days"),
        start_date=extracted_data.get("start_date"),
        end_date=extracted_data.get("end_date"),
        guest_count=extracted_data.get("guest_count") or extracted_data.get("attendees"),
        budget_mentioned=extracted_data.get("budget_mentioned"),
        call_summary=extracted_data.get("summary"),
        call_recording_url=extracted_data.get("recording_url"),
        full_transcript=extracted_data.get("full_transcript"),
        
        # Additional fields from the call script
        power_available=extracted_data.get("power_available"),
        water_available=extracted_data.get("water_available"),
        delivery_surface=extracted_data.get("delivery_surface"),
        delivery_obstacles=extracted_data.get("delivery_obstacles"),
        other_facilities_available=extracted_data.get("other_facilities_available"),
        other_products_needed=extracted_data.get("other_products_needed", []),
        decision_timeline=extracted_data.get("decision_timeline"),
        quote_needed_by=extracted_data.get("quote_needed_by"),
        
        # Construction-specific fields
        onsite_contact_different=extracted_data.get("onsite_contact_different"),
        working_hours=extracted_data.get("working_hours"),
        weekend_usage=extracted_data.get("weekend_usage"),
    )

async def _handle_hubspot_update(classification_result: ClassificationResult) -> Tuple[Optional[str], Optional[str]]:
    """Helper function to create/update contact and deal in HubSpot and send notification."""
    if classification_result.status != "success" or not classification_result.classification:
        logfire.warn("Classification failed or no output, skipping HubSpot update.")
        return None, None # Indicate no HubSpot action taken

    output = classification_result.classification
    input_data = classification_result.input_data

    if output.lead_type == "Disqualify":
        logfire.info("Lead classified as Disqualify, skipping HubSpot deal creation.")
        # Optionally, still create/update contact or update a specific property
        # contact_props = HubSpotContactProperties(...) # Prepare contact data
        # await hubspot_manager.create_or_update_contact(contact_props)
        return None, None

    logfire.info("Proceeding with HubSpot contact and deal update.", classification=output.lead_type)

    # 1. Create/Update Contact
    contact_props = HubSpotContactProperties(
        email=input_data.email,
        firstname=input_data.firstname,
        lastname=input_data.lastname,
        phone=input_data.phone,
        stahla_lead_source=input_data.source,
        stahla_lead_type=output.lead_type # Set custom property based on classification
        # Add other relevant contact properties from input_data
    )
    contact_result = await hubspot_manager.create_or_update_contact(contact_props)
    if contact_result.status != "success" or not contact_result.contact_id:
        logfire.error("Failed to create or update HubSpot contact.", email=input_data.email, error=contact_result.message)
        return None, None

    contact_id = contact_result.contact_id
    logfire.info("HubSpot contact created/updated successfully.", contact_id=contact_id)

    # 2. Create Deal
    deal_name = f"{input_data.firstname or 'Lead'} {input_data.lastname or ''} - {input_data.product_interest[0] if input_data.product_interest else 'Inquiry'} ({input_data.source})"

    # --- Get Pipeline and Stage IDs --- #
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None
    default_initial_stage_name = "Lead In" # Initial stage name for newly created deals
    
    # Determine pipeline based on lead classification
    pipeline_name = None
    if output.lead_type == "Services":
        pipeline_name = "Services Pipeline"
    elif output.lead_type == "Logistics":
        pipeline_name = "Logistics Pipeline"
    elif output.lead_type == "Leads":
        pipeline_name = "Leads Pipeline"
    
    if pipeline_name:
        pipeline_id = await hubspot_manager.get_pipeline_id(pipeline_name)
        if pipeline_id:
            # Use the default initial stage name for newly created deals
            stage_id = await hubspot_manager.get_stage_id(pipeline_id, default_initial_stage_name)
            if not stage_id:
                logfire.warn(f"Initial stage '{default_initial_stage_name}' not found in pipeline '{pipeline_name}' ({pipeline_id}). Deal will use pipeline default.")
        else:
            logfire.warn(f"Pipeline '{pipeline_name}' not found. Deal will use HubSpot default.")
    else:
        logfire.warn("No pipeline determined from classification. Deal will use HubSpot default.")
    # --------------------------------- #

    deal_props = HubSpotDealProperties(
        dealname=deal_name,
        pipeline=pipeline_id, # Use fetched ID (or None)
        dealstage=stage_id, # Use fetched ID (or None)
        # --- Map custom properties --- #
        stahla_product_interest=", ".join(input_data.product_interest) if input_data.product_interest else None,
        stahla_event_location=input_data.event_location_description,
        stahla_duration=f"{input_data.duration_days} days" if input_data.duration_days else None,
        stahla_stall_count=input_data.required_stalls,
        stahla_budget_info=input_data.budget_mentioned,
        stahla_call_summary=input_data.call_summary,
        stahla_call_recording_url=str(input_data.call_recording_url) if input_data.call_recording_url else None,
        stahla_guest_count=input_data.guest_count,
        stahla_event_type=input_data.event_type,
        # Additional detailed properties from the call script
        stahla_ada_required="Yes" if input_data.ada_required else "No",
        stahla_power_available="Yes" if input_data.power_available else "No",
        stahla_water_available="Yes" if input_data.water_available else "No",
        stahla_delivery_surface=input_data.delivery_surface,
        stahla_other_facilities=input_data.other_facilities_available,
        stahla_decision_timeline=input_data.decision_timeline,
        stahla_quote_urgency=input_data.quote_needed_by
    )

    deal_result = await hubspot_manager.create_deal(deal_props, associated_contact_id=contact_id)

    if deal_result.status != "success" or not deal_result.deal_id:
        logfire.error("Failed to create HubSpot deal.", deal_name=deal_name, error=deal_result.message)
        # Still send notification about the contact if it was created/updated
        await email_manager.send_handoff_notification(classification_result, contact_result, None)
        return contact_id, None

    deal_id = deal_result.deal_id
    logfire.info("HubSpot deal created successfully.", deal_id=deal_id)

    # 3. Assign Owner based on classification metadata
    assigned_owner_team = output.metadata.get("assigned_owner_team")
    if assigned_owner_team:
        owner_id = await hubspot_manager.get_next_owner_id(assigned_owner_team)
        if owner_id and pipeline_id and stage_id:
            update_result = await hubspot_manager.update_deal_pipeline_and_owner(
                deal_id, pipeline_id, stage_id, owner_id
            )
            if update_result.status == "success":
                logfire.info("Deal owner assigned successfully.", 
                            deal_id=deal_id, team=assigned_owner_team, owner_id=owner_id)
            else:
                logfire.warn("Failed to assign deal owner.", 
                            deal_id=deal_id, team=assigned_owner_team, error=update_result.message)
        else:
            logfire.warn("Could not assign deal owner due to missing ID.", 
                        deal_id=deal_id, team=assigned_owner_team, 
                        has_owner_id=bool(owner_id), has_pipeline_id=bool(pipeline_id), has_stage_id=bool(stage_id))
    else:
        logfire.info("No assigned owner team specified in classification metadata. Using default assignment.")

    # --- Send Handoff Notification --- #
    await email_manager.send_handoff_notification(classification_result, contact_result, deal_result)
    # ------------------------------- #

    return contact_id, deal_id

@router.post("/form", summary="Receive Web Form Submissions")
async def webhook_form(
    payload: FormPayload = Body(...)
):
    """
    Handles incoming webhook submissions from the web form.
    Checks if required data is present. If not, triggers a Bland.ai callback.
    If complete, sends data for classification.
    """
    logfire.info("Received form webhook payload.", data=payload.model_dump())
    payload_dict = payload.model_dump(exclude_none=True)

    # Define required fields for immediate classification (Goal: >=95% completeness)
    # Based on PRD requirements for data completeness
    required_fields_for_classification = [
        "email", "phone", "product_interest", "event_location_description", 
        "event_type", "duration_days", "guest_count", "required_stalls"
    ]

    def check_form_completeness(form_data: Dict[str, Any]) -> bool:
        missing = [field for field in required_fields_for_classification if not form_data.get(field)]
        if missing:
            logfire.info(f"Form data missing required fields for classification: {missing}", form_data=form_data)
            return False
        return True

    is_complete = check_form_completeness(payload_dict)

    if not is_complete:
        logfire.info("Form data incomplete, initiating Bland callback.")
        phone_number = payload.phone
        if not phone_number:
             logfire.error("Cannot initiate callback, phone number missing from form payload.", form_data=payload_dict)
             raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Phone number is required in form data to initiate callback.")

        # Construct the task prompt dynamically based on missing info if possible
        missing_fields = [field for field in required_fields_for_classification if not payload_dict.get(field)]
        
        # Create a tailored prompt based on the missing information
        task_prompt = (
            f"Hello, this is Stahla Assistant calling about the {payload.product_interest or 'restroom solution'} request you submitted on our website. "
            f"To provide you with the best service, I need a few more details about your {payload.event_type or 'upcoming event or project'}. "
        )
        
        # Add specific questions based on missing fields
        if "event_type" in missing_fields:
            task_prompt += "Could you tell me what type of event or project this is for? For example, is it a wedding, construction site, festival, or something else? "
            
        if "event_location_description" in missing_fields:
            task_prompt += "What's the location or address where you would need our services? "
            
        if "duration_days" in missing_fields:
            task_prompt += "How many days would you need our services? "
            
        if "guest_count" in missing_fields:
            task_prompt += "Approximately how many people would be using the facilities? "
            
        if "required_stalls" in missing_fields:
            task_prompt += "How many stalls or units would you need? "
            
        task_prompt += "This information will help us provide an accurate quote quickly."

        # Construct the full webhook URL for Bland to call back to
        voice_webhook_url = f"{settings.APP_BASE_URL.strip('/')}{settings.API_V1_STR}/webhook/voice"

        callback_request = BlandCallbackRequest(
            phone_number=phone_number,
            task=task_prompt,
            voice_id=settings.BLAND_DEFAULT_VOICE_ID, # Use default from settings if set
            wait_for_greeting=True,
            record=True,
            amd=True,
            webhook=voice_webhook_url, # Ensure Bland sends the result back to our voice endpoint
            metadata={
                "original_source": "webform",
                "form_submission_data": payload_dict # Pass original form data
            }
        )
        callback_result = await bland_manager.initiate_callback(callback_request)

        if callback_result.status == "error":
            logfire.error("Failed to initiate Bland callback for incomplete form.", details=callback_result.details)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate follow-up call: {callback_result.message}")
        else:
            logfire.info("Bland callback initiated successfully.", call_id=callback_result.call_id)
            return {"status": "received", "source": "form", "action": "callback_initiated", "call_id": callback_result.call_id}
    else:
        logfire.info("Form data complete, proceeding to classification.")
        classification_input = _prepare_classification_input(
            source="webform",
            raw_data=payload_dict,
            extracted_data=payload_dict
        )
        classification_result = await classification_manager.classify_lead_data(classification_input)
        logfire.info("Classification result received.", result=classification_result.model_dump(exclude={"input_data"}))

        # --- HubSpot Integration --- #
        contact_id, deal_id = await _handle_hubspot_update(classification_result)
        # ------------------------- #

        return {
            "status": "received",
            "source": "form",
            "action": "classification_complete",
            "classification": classification_result.output.model_dump() if classification_result.output else None,
            "hubspot_contact_id": contact_id,
            "hubspot_deal_id": deal_id
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
    contact_id, deal_id = await _handle_hubspot_update(classification_result)
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
        contact_id, deal_id = await _handle_hubspot_update(classification_result)
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


"""
This version includes:
* Imports for `BlandWebhookPayload`, `BlandApiResult`, `BlandCallbackRequest`, and `bland_manager`.
* The `/webhook/voice` endpoint now uses `BlandWebhookPayload` for input validation and calls `bland_manager.process_incoming_transcript`.
* The `/webhook/form` endpoint includes an example structure showing how to check for completeness and potentially call `bland_manager.initiate_callback` if data is missing. Remember to replace the placeholder `check_form_completeness` function and customize the `BlandCallbackRequest` parameters.
* The `/webhook/email` endpoint remains a placeholder, indicating the need for an `EmailProcessingManage
"""