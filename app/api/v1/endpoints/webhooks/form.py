# app/api/v1/endpoints/webhooks/form.py

from fastapi import APIRouter, BackgroundTasks, Body, Depends
import logfire
import uuid
from pydantic import BaseModel  # Added
from typing import Optional, Any  # Added

# Import models
from app.models.webhook import FormPayload
from app.models.classification import ClassificationInput
from app.models.mongo.classify import ClassifyStatus  # Add this import
from app.models.common import GenericResponse  # Added

# Import services
from app.services.classify.classification import classification_manager
from app.services.mongo import MongoService, get_mongo_service  # Added import

# Import helpers from the same directory
from .helpers import _is_form_complete, _trigger_bland_call, _handle_hubspot_update, prepare_classification_input

# Import background tasks
from app.services.background.mongo.tasks import (
    log_quote_bg,
    log_classify_bg,
    log_location_bg,
    log_email_bg
)

router = APIRouter()


# Define a response model for the data part of GenericResponse
class FormWebhookResponseData(BaseModel):
  status: str
  message: str
  # Using Any for now, can be more specific
  classification_result: Optional[Any] = None
  hubspot_update_status: Optional[str] = None


# Updated response_model
@router.post("/form", summary="Process Form Submissions", response_model=GenericResponse[FormWebhookResponseData])
async def webhook_form(
    payload: FormPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    mongo_service: MongoService = Depends(get_mongo_service)
) -> GenericResponse[FormWebhookResponseData]:  # Updated return type hint
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
    return GenericResponse(
        data=FormWebhookResponseData(
            status="incomplete",
            message="Form incomplete, initiating follow-up call."
        )
    )

  logfire.info("Form data complete, proceeding to classification.")

  # Correctly access potential extra fields like 'source_url' before creating ClassificationInput
  source_url_value = getattr(payload, 'source_url', None)
  source_url_for_input = str(
      source_url_value) if source_url_value is not None else None

  # Convert FormPayload to ClassificationInput
  raw_data = payload.model_dump(mode='json')

  # Map FormPayload fields using the helper function
  classification_input = prepare_classification_input(
      source="webform",
      raw_data=raw_data,
      extracted_data=payload.model_dump()
  )

  # Trigger classification using the manager
  classification_result = await classification_manager.classify_lead_data(classification_input)
  logfire.info("Classification result received.",
               classification=classification_result.model_dump(exclude_none=True))

  # Log classification to MongoDB in background
  if classification_result.classification:
    classify_data = {
        "id": str(uuid.uuid4()),
        "source": "webform",
        "status": ClassifyStatus.COMPLETED if classification_result.status == "success" else ClassifyStatus.FAILED,
        "lead_type": classification_result.classification.lead_type,
        "routing_suggestion": classification_result.classification.routing_suggestion,
        "confidence": classification_result.classification.confidence,
        "reasoning": classification_result.classification.reasoning,
        "requires_human_review": classification_result.classification.requires_human_review,
        "classification_results": classification_result.classification.model_dump(),
        "input_data": classification_input.model_dump(),
        "processing_time": 0
    }
    background_tasks.add_task(
        log_classify_bg,
        mongo_service=mongo_service,
        classify_data=classify_data
    )

  # --- HubSpot Integration --- #
  classification_output = classification_result.classification
  if classification_output and not (
      classification_output.metadata and
      classification_output.metadata.get("error_type")
  ):
    # Trigger HubSpot update (create contact/deal) in the background
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
  return GenericResponse(
      data=FormWebhookResponseData(
          status="success",
          message="Form processed and classification initiated.",
          classification_result=classification_result.model_dump(
              exclude_none=True),
          hubspot_update_status=hubspot_status
      )
  )
