# app/api/v1/endpoints/webhooks.py

from fastapi import APIRouter, Request, HTTPException, status, Body
from typing import Any # Use specific Pydantic models later
import logfire

# Import Pydantic models
# from app.models.webhook_models import FormPayload # Example for form (Create this model)
from app.models.bland_models import BlandWebhookPayload, BlandApiResult, BlandCallbackRequest # Import Bland models

# Import Services
from app.services.bland_service import bland_manager # Import Bland manager instance
# from app.services.classification_service import classification_manager # Needed for classification step
# from app.models.classification_models import ClassificationInput # Needed for classification step

# Create an APIRouter instance for webhook endpoints
router = APIRouter()

@router.post("/form", summary="Receive Web Form Submissions")
async def webhook_form(
    # TODO: Replace Any with your specific Pydantic model for form data
    # Example: payload: FormPayload = Body(...)
    payload: Dict[str, Any] = Body(...) # Using Dict for now, replace with FormPayload
):
    """
    Handles incoming webhook submissions from the web form.
    Placeholder: Logs the received data.
    Checks if required data is present. If not, triggers a Bland.ai callback.
    If complete, prepares data for classification (TODO).
    """
    logfire.info("Received form webhook payload.", data=payload)

    # --- Example: Trigger callback if data incomplete ---
    # TODO: Implement a real function to check completeness based on Stahla's requirements
    def check_form_completeness(form_data: Dict[str, Any]) -> bool:
        required_fields = ["firstname", "lastname", "email", "phone", "product_interest"] # Example required fields
        return all(form_data.get(field) for field in required_fields)

    is_complete = check_form_completeness(payload)

    if not is_complete:
        logfire.info("Form data incomplete, initiating Bland callback.")
        phone_number = payload.get("phone")
        if not phone_number:
             logfire.error("Cannot initiate callback, phone number missing from form payload.", form_data=payload)
             # Return an error or acknowledge receipt but log failure
             raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Phone number is required in form data to initiate callback.")

        # Construct BlandCallbackRequest data from form payload
        callback_request = BlandCallbackRequest(
            phone_number=phone_number,
            task="Hello, this is Stahla Assistant calling back regarding the web form you submitted. I need to gather a bit more information to help you. [Add specific questions based on missing fields]",
            # TODO: Add other necessary parameters like webhook, metadata etc.
            # It's crucial to set the webhook here if you want the result of this specific
            # callback to hit your /webhook/voice endpoint. Otherwise, Bland might use a default.
            # webhook=str(settings.YOUR_BASE_URL + "/api/v1/webhook/voice"), # Construct your full webhook URL
            metadata={"original_source": "webform", "form_submission_id": payload.get("id", "unknown")} # Example metadata
        )
        callback_result = await bland_manager.initiate_callback(callback_request)

        if callback_result.status == "error":
            # Handle error, maybe return 500 or log and proceed
            logfire.error("Failed to initiate Bland callback for incomplete form.", details=callback_result.details)
            # Decide if this failure should prevent acknowledging the form submission
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate follow-up call: {callback_result.message}")
        else:
            logfire.info("Bland callback initiated successfully.", call_id=callback_result.call_id)
            # Acknowledge receipt and indicate callback was started
            return {"status": "received", "source": "form", "action": "callback_initiated", "call_id": callback_result.call_id}
    else:
        # TODO: Send complete data to classification
        logfire.info("Form data complete, proceeding to classification (TODO).")
        # classification_input_data = {
        #     "source": "webform",
        #     "raw_data": payload,
        #     "extracted_data": payload # Assuming form payload is already structured key-value
        #     # Add specific fields if needed by ClassificationInput model
        # }
        # classification_input = ClassificationInput(**classification_input_data)
        # await classification_manager.classify_lead_data(classification_input)
        # Handle classification result...
        return {"status": "received", "source": "form", "action": "classification_pending"}
    # --- End Example ---


@router.post(
    "/voice",
    summary="Receive Voice Transcripts from Bland.ai",
    response_model=BlandApiResult # Define expected response structure
)
async def webhook_voice(
    # Use the specific Pydantic model for Bland.ai webhook payload
    payload: BlandWebhookPayload = Body(...)
):
    """
    Handles incoming webhook submissions containing voice transcripts from Bland.ai.
    Validates the payload against the BlandWebhookPayload model.
    Passes the payload to the BlandAIManager for processing (extracting info, TODO: classifying).
    """
    logfire.info("Received voice webhook payload via API.", call_id=payload.call_id)

    # Call the manager's method to process the transcript
    result = await bland_manager.process_incoming_transcript(payload)

    # Check the result status and return appropriate response
    if result.status == "error":
        logfire.error("Failed to process Bland transcript.", call_id=payload.call_id, message=result.message)
        # Return 500 Internal Server Error if processing failed
        # Bland might retry if it receives a non-2xx response. Check their docs.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message or "Failed to process voice transcript."
        )

    logfire.info("Bland transcript processed successfully.", call_id=payload.call_id, details=result.details)
    # Return the result from the manager (status: success)
    # Bland typically expects a 2xx response to acknowledge receipt.
    return result


@router.post("/email", summary="Process Incoming Emails")
async def webhook_email(
    # TODO: Replace Any with your specific Pydantic model for email data
    payload: Any = Body(...)
):
    """
    Handles incoming webhook submissions for emails (e.g., from a mail parsing service).
    Placeholder: Logs the received data.
    TODO: Implement data validation with Pydantic model.
    TODO: Create EmailProcessingManager service.
    TODO: Call manager to parse email (potentially calling an LLM service).
    TODO: Implement logic to check for missing fields and trigger auto-reply.
    TODO: Send data to classification service.
    """
    logfire.info("Received email webhook payload.", data=payload)
    # Add actual processing logic here (call EmailProcessingManager)
    return {"status": "received", "source": "email", "data": payload}


"""
This version includes:
* Imports for `BlandWebhookPayload`, `BlandApiResult`, `BlandCallbackRequest`, and `bland_manager`.
* The `/webhook/voice` endpoint now uses `BlandWebhookPayload` for input validation and calls `bland_manager.process_incoming_transcript`.
* The `/webhook/form` endpoint includes an example structure showing how to check for completeness and potentially call `bland_manager.initiate_callback` if data is missing. Remember to replace the placeholder `check_form_completeness` function and customize the `BlandCallbackRequest` parameters.
* The `/webhook/email` endpoint remains a placeholder, indicating the need for an `EmailProcessingManage
"""