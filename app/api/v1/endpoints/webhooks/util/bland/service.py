# app/api/v1/endpoints/webhooks/util/bland/service.py

import logfire
import re
from typing import Dict, Any

# Import models
from app.models.webhook import FormPayload
from app.models.bland import BlandCallbackRequest

# Import services
from app.services.bland import get_bland_manager
from app.core.config import settings


async def trigger_bland_call(payload: FormPayload):
  """
  Triggers a Bland.ai call if the form is incomplete.
  Populates request_data for the AI agent and metadata for tracking.
  """
  if not settings.BLAND_API_KEY:
    logfire.warn("Bland API key not configured, skipping call.")
    return

  phone_number = payload.phone or ""
  if not phone_number:
    logfire.error(
        "Cannot trigger Bland call: Phone number is missing.", email=payload.email)
    return

  first_name = payload.firstname or "Lead"

  # Data for the AI agent
  agent_request_data = {
      "firstname": payload.firstname,
      "lastname": payload.lastname,
      "email": payload.email,
      "phone": payload.phone,
      "product_interest": payload.product_interest,
      "event_location_description": payload.event_location_description,
      "start_date": payload.start_date,
      "company": payload.company,
      "source_url": getattr(payload, 'source_url', None)
  }
  # Filter out None values from agent_request_data
  agent_request_data = {k: v for k,
                        v in agent_request_data.items() if v is not None}

  # Metadata for tracking and webhook context
  # Initialize metadata with everything from agent_request_data
  call_metadata = agent_request_data.copy()
  # Add/overwrite with specific metadata fields
  call_metadata.update({
      "source": "web_form_incomplete",
      # For easier association if contact_id is email
      "form_payload_email": payload.email,
      "form_payload_phone": payload.phone,
      "form_source_url": getattr(payload, 'source_url', None)
  })
  call_metadata = {k: v for k, v in call_metadata.items() if v is not None}

  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhook/voice"

  callback_request = BlandCallbackRequest(
      phone_number=phone_number,
      task=None,  # Assuming pathway/script uses request_data
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental form you submitted. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      max_duration=None,
      transfer_phone_number=None,
      voice=settings.BLAND_VOICE_ID or "1",
      webhook=webhook_url,
      request_data=agent_request_data,
      metadata=call_metadata
  )

  logfire.info(
      f"Triggering Bland call to {phone_number} from form payload.",
      request_data=agent_request_data,
      metadata=call_metadata
  )
  try:
    # contact_id for logging purposes, can be email or a more stable ID if available
    call_contact_id = payload.email or payload.phone or "unknown_form_contact"
    call_result = await get_bland_manager().initiate_callback(
        request_data=callback_request,
        contact_id=call_contact_id,
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


async def trigger_bland_call_for_hubspot_contact(contact_id: str, contact_properties: dict):
  """
  Triggers a Bland.ai call for an incomplete HubSpot contact.
  Includes contact_id in metadata. Uses HubSpot internal property names from contact_properties.
  """
  if not settings.BLAND_API_KEY:
    logfire.warn(
        "Bland API key not configured, skipping call for HubSpot contact.")
    return

  phone_number_raw = contact_properties.get("phone")

  if not phone_number_raw:
    logfire.error(
        "Cannot trigger Bland call for HubSpot contact: Phone number is missing in contact_properties.",
        contact_id=contact_id
    )
    return

  # Phone number formatting
  digits_only = re.sub(r'\\D', '', str(phone_number_raw))
  formatted_phone_number = digits_only
  prefix_to_use = settings.BLAND_PHONE_PREFIX
  if prefix_to_use:
    prefix_digits = re.sub(r'\\D', '', prefix_to_use)
    if digits_only.startswith(prefix_digits):
      if prefix_to_use != prefix_digits:  # e.g. prefix is +1, digits_only starts with 1
        formatted_phone_number = prefix_to_use + \
            digits_only[len(prefix_digits):]
    else:
      formatted_phone_number = prefix_to_use + digits_only

  if not formatted_phone_number:
    logfire.error(
        "Cannot trigger Bland call for HubSpot contact: Formatted phone number is empty.",
        contact_id=contact_id
    )
    return

  first_name = contact_properties.get("firstname", "Lead")

  # Data for the AI agent from HubSpot contact properties
  agent_request_data = {
      "firstname": contact_properties.get("firstname"),
      "lastname": contact_properties.get("lastname"),
      "email": contact_properties.get("email"),
      "phone": phone_number_raw,
      "formatted_phone_to_dial": formatted_phone_number,
      "service_needed": contact_properties.get("what_service_do_you_need_"),
      "event_address": contact_properties.get("event_or_job_address"),
      "event_start_date": contact_properties.get("event_start_date"),
      "event_end_date": contact_properties.get("event_end_date"),
      "company": contact_properties.get("company"),
  }
  agent_request_data = {k: v for k,
                        v in agent_request_data.items() if v is not None}

  # Metadata for tracking and webhook context
  call_metadata = agent_request_data.copy()
  call_metadata.update({
      "source": "hubspot_incomplete_contact",
      "hubspot_contact_id": contact_id,
      "original_email": contact_properties.get("email"),
      "original_phone": phone_number_raw
  })
  call_metadata = {k: v for k, v in call_metadata.items() if v is not None}

  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhook/voice"

  callback_request = BlandCallbackRequest(
      phone_number=formatted_phone_number,
      task=None,
      voice=settings.BLAND_VOICE_ID or "1",
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental inquiry you submitted through our website. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      max_duration=None,
      transfer_phone_number=None,
      webhook=webhook_url,
      request_data=agent_request_data,
      metadata=call_metadata
  )

  logfire.info(
      f"Triggering Bland call for HubSpot contact {contact_id} to {formatted_phone_number}",
      request_data=agent_request_data,
      metadata=call_metadata
  )
  try:
    logfire.debug("Bland callback request data", request_data=callback_request)
    call_result = await get_bland_manager().initiate_callback(
        request_data=callback_request,
        contact_id=contact_id,
        log_retry_of_call_id=None,
        log_retry_reason=None,
    )
    if call_result.status == "success":
      logfire.info("Bland call for HubSpot contact initiated successfully.",
                   call_id=call_result.call_id, contact_id=contact_id)
    else:
      logfire.error("Failed to initiate Bland call for HubSpot contact.",
                    error=call_result.message, details=call_result.details,
                    contact_id=contact_id)
  except Exception as e:
    logfire.exception("Error occurred while triggering Bland call for HubSpot contact",
                      contact_id=contact_id)
