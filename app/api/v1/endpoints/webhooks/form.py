# app/api/v1/endpoints/webhooks/form.py

from fastapi import APIRouter, BackgroundTasks, Body
import logfire
from pydantic import BaseModel  # Added
from typing import Optional, Any  # Added

# Import models
from app.models.webhook import FormPayload
from app.models.classification import ClassificationInput
from app.models.common import GenericResponse  # Added

# Import services
from app.services.classify.classification import classification_manager

# Import helpers from the same directory
from .helpers import _is_form_complete, _trigger_bland_call, _handle_hubspot_update

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
    background_tasks: BackgroundTasks = BackgroundTasks()
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

  # Map FormPayload fields to the updated ClassificationInput fields
  classification_input = ClassificationInput(
      source="webform",
      raw_data=raw_data,
      extracted_data=payload.model_dump(),  # Pass form data as extracted
      # Map fields directly using updated names
      firstname=payload.firstname,
      lastname=payload.lastname,
      email=payload.email,
      phone=payload.phone,
      company=payload.company,
      message=payload.comments,  # Use comments from FormPayload
      # Use correct field
      text_consent=getattr(
          payload, 'by_submitting_this_form_you_consent_to_receive_texts', None),
      product_interest=[
          payload.product_interest] if payload.product_interest else [],
      service_needed=payload.lead_type_guess,  # Use lead_type_guess from FormPayload
      stall_count=payload.required_stalls,  # Use required_stalls from FormPayload
      ada_required=payload.ada_required,
      event_type=payload.event_type,
      # Use event_location_description from FormPayload
      event_address=payload.event_location_description,
      event_state=payload.event_state,
      event_city=payload.event_city,
      event_postal_code=payload.event_postal_code,
      duration_days=payload.duration_days,
      event_start_date=payload.start_date,  # Use start_date from FormPayload
      event_end_date=payload.end_date,  # Use end_date from FormPayload
      guest_count=payload.guest_count,
      # Add other relevant mappings if FormPayload has them
      # ...
  )

  # Trigger classification using the manager
  classification_result = await classification_manager.classify_lead_data(classification_input)
  logfire.info("Classification result received.",
               classification=classification_result.model_dump(exclude_none=True))

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
