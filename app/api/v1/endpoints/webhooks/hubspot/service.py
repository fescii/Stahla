# app/api/v1/endpoints/webhooks/hubspot/service.py

import logfire
import re
from typing import Dict, Any
from datetime import datetime

# Import models
from app.models.bland import BlandCallbackRequest
from app.models.classification import ClassificationInput, ClassificationResult

# Import services
from app.services.bland import get_bland_manager
from app.core.config import settings

# Import shared utilities
from ..util.hubspot import is_hubspot_contact_complete, update_hubspot_lead_after_classification


def is_contact_complete(contact_properties: dict) -> bool:
  """
  Check if the HubSpot contact properties contain the minimum required information
  to potentially create a complete Lead after classification/qualification.
  """
  return is_hubspot_contact_complete(contact_properties)


def convert_hubspot_timestamp(timestamp: str) -> str:
  """
  Convert HubSpot timestamp to a human-readable format.
  This is a placeholder function; implement as needed.
  """
  # timestamp input is usually: 1748131200000
  # Convert milliseconds to seconds
  timestamp_in_seconds = int(timestamp) / 1000
  # Format as a human-readable string
  return datetime.fromtimestamp(timestamp_in_seconds).strftime('%Y-%m-%d %H:%M:%S')


async def trigger_bland_call_for_contact(contact_id: str, contact_properties: dict):
  """
  Triggers a Bland.ai call for an incomplete HubSpot contact.
  Includes contact_id in metadata. Lead ID is no longer passed.
  Uses HubSpot internal property names from contact_properties.
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

  # Phone number formatting (ensure this logic is robust for your needs)
  digits_only = re.sub(r'\\D', '', str(phone_number_raw))
  formatted_phone_number = digits_only
  prefix_to_use = settings.BLAND_PHONE_PREFIX
  if prefix_to_use:
    prefix_digits = re.sub(r'\\D', '', prefix_to_use)
    if digits_only.startswith(prefix_digits):
      if prefix_to_use != prefix_digits:  # e.g. prefix is +1, digits_only starts with 1
        formatted_phone_number = prefix_to_use + \
            digits_only[len(prefix_digits):]
      # else: formatted_phone_number is already correct (digits_only)
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
      "source": "hubspot_incomplete_contact",
      "hubspot_contact_id": contact_id,
      "firstname": contact_properties.get("firstname"),
      "lastname": contact_properties.get("lastname"),
      "email": contact_properties.get("email"),
      "phone": phone_number_raw,  # Original phone for agent context if needed
      "formatted_phone_to_dial": formatted_phone_number,  # Actual number dialed
      "service_needed": contact_properties.get("what_service_do_you_need_"),
      "event_address": contact_properties.get("event_or_job_address"),
      "event_start_date": convert_hubspot_timestamp(contact_properties["event_start_date"]) if contact_properties.get("event_start_date") is not None else None,
      "event_end_date": convert_hubspot_timestamp(contact_properties["event_end_date"]) if contact_properties.get("event_end_date") is not None else None,
      "company": contact_properties.get("company"),
      # Add other relevant HubSpot properties for the agent
  }
  agent_request_data = {k: v for k,
                        v in agent_request_data.items() if v is not None}

  # Metadata for tracking and webhook context
  # Initialize metadata with everything from agent_request_data
  call_metadata = agent_request_data.copy()
  # Add/overwrite with specific metadata fields
  call_metadata.update({
      "source": "hubspot_incomplete_contact",
      "hubspot_contact_id": contact_id,
      # Include a few key original properties if useful for webhook processing
      # These might already be in agent_request_data, update ensures they are set if different or adds them
      "original_email": contact_properties.get("email"),
      # phone_number_raw is from contact_properties.get("phone")
      "original_phone": phone_number_raw
  })
  call_metadata = {k: v for k, v in call_metadata.items() if v is not None}

  webhook_url = f"{settings.APP_BASE_URL}{settings.API_V1_STR}/webhook/voice"

  callback_request = BlandCallbackRequest(
      phone_number=formatted_phone_number,
      task=None,  # Assuming pathway/script uses request_data
      voice=settings.BLAND_VOICE_ID or "1",  # Use configured voice or default "1"
      first_sentence=f"Hi {first_name}, this is Stahla Assistant calling about the restroom rental inquiry you submitted through our website. Is now a good time?",
      wait_for_greeting=True,
      record=True,
      max_duration=None,  # Assuming no max duration needed
      transfer_phone_number=None,  # Assuming no transfer number needed
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
    # print request data for debugging
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


async def update_lead_after_classification(
    classification_result: ClassificationResult,
    input_data: ClassificationInput,
    contact_id: str
):
  """
  Creates a new HubSpot lead based on classification results, associates it with the contact,
  assigns owner, and triggers n8n handoff. Used after direct classification.
  """
  await update_hubspot_lead_after_classification(classification_result, input_data, contact_id)
