# app/api/v1/endpoints/webhooks/email.py

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status
import logfire

# Import models
from app.models.webhook import EmailWebhookPayload, EmailProcessingResult
from app.models.classification import ClassificationInput

# Import services
# Assuming email_manager is the correct instance
from app.services.email import email_manager
from app.services.classify.classification import classification_manager

# Import helpers
from .helpers import _handle_hubspot_update, prepare_classification_input

router = APIRouter()


@router.post("/email", summary="Process Incoming Emails", response_model=EmailProcessingResult)
async def webhook_email(
    payload: EmailWebhookPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
  """
  Handles incoming webhook submissions for emails.
  Calls the EmailManager to parse, check completeness, potentially auto-reply,
  and eventually send for classification.
  HubSpot update runs in the background.
  """
  logfire.info("Received email webhook payload.",
               message_id=payload.message_id)

  # Call the EmailManager service
  processing_result = await email_manager.process_incoming_email(payload)

  if processing_result.status == "error":
    logfire.error("Failed to process email.",
                  message_id=payload.message_id, message=processing_result.message)
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

    classification_input = prepare_classification_input(
        source="email",
        raw_data=raw_data,
        extracted_data=extracted_data
    )

    # Classify
    classification_result = await classification_manager.classify_lead_data(classification_input)
    logfire.info("Classification result received.",
                 result=classification_result.model_dump(exclude={"input_data"}))

    # --- HubSpot Integration (Run in Background) --- #
    async def _run_handle_hubspot_update_in_background():
      c_id, d_id = await _handle_hubspot_update(classification_result, classification_input)
      logfire.info("Background HubSpot update completed (email)",
                   contact_id=c_id, deal_id=d_id)

    background_tasks.add_task(_run_handle_hubspot_update_in_background)
    logfire.info("HubSpot update initiated in background for email.")
    # ---------------------------------------------- #

    # Update the processing result message - HubSpot IDs won't be included here
    processing_result.details = {
        "classification": classification_result.classification.model_dump() if classification_result.classification else None,
        "hubspot_contact_id": None,  # Not available immediately
        "hubspot_deal_id": None     # Not available immediately
    }
    processing_result.message = "Email processed, classification complete, HubSpot update initiated."

  # Return the result from the EmailManager (or updated result after classification/HubSpot)
  return processing_result
