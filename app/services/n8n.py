# app/services/n8n.py
import httpx
import logfire
from typing import Optional, Dict, Any

from app.core.config import settings
from app.models.classification import ClassificationResult, ClassificationInput
from app.models.hubspot import HubSpotApiResult

# Use a shared httpx client for efficiency
_client = httpx.AsyncClient(timeout=10.0)


async def send_to_n8n_webhook(
    payload: Dict[str, Any],
    webhook_url: Optional[str] = settings.N8N_WEBHOOK_URL,
    api_key: Optional[str] = settings.N8N_API_KEY  # Add api_key parameter
):
  """Sends a payload to the configured n8n webhook URL with header auth."""
  if not webhook_url:
    logfire.warn("N8N_WEBHOOK_URL not configured. Skipping webhook call.")
    return False

  headers = {}
  if api_key:
    # Use the custom header name 'Stahla'
    headers["Stahla"] = api_key
    logfire.info("Using API Key header 'Stahla' for n8n webhook.")
  else:
    logfire.info("No API Key configured for n8n webhook.")

  logfire.info(f"Sending data to n8n webhook.", url=webhook_url,
               payload_keys=list(payload.keys()))
  try:
    # Pass headers to the request
    response = await _client.post(str(webhook_url), json=payload, headers=headers)
    response.raise_for_status()  # Raise exception for 4xx/5xx errors
    logfire.info("Successfully sent data to n8n webhook.",
                 response_status=response.status_code)
    return True
  except httpx.HTTPStatusError as e:
    logfire.error(f"HTTP error sending to n8n webhook: {e.response.status_code}", url=str(
        e.request.url), response=e.response.text)
    return False
  except httpx.RequestError as e:
    logfire.error(
        f"Request error sending to n8n webhook: {e}", url=str(e.request.url))
    return False
  except Exception as e:
    logfire.exception("Unexpected error sending data to n8n webhook.")
    return False


# Updated function signature and logic for Leads
async def trigger_n8n_handoff_automation(
    classification_result: ClassificationResult,
    input_data: ClassificationInput,  # This now contains many fields from call.json
    contact_result: Optional[HubSpotApiResult],
    lead_result: Optional[HubSpotApiResult]
):
  """
  Prepares a structured payload and sends the handoff data to the n8n webhook.
  Pulls data primarily from input_data (ClassificationInput) which reflects call variables.
  """
  logfire.info("Classification result received:",
               classification_result=classification_result)
  logfire.info("Input data received:", input_data=input_data)
  logfire.info("Contact result received:", contact_result=contact_result)
  logfire.info("Lead result received:", lead_result=lead_result)
  if not classification_result.classification:
    logfire.info("No classification output available, skipping n8n handoff.")
    return False

  classification_output = classification_result.classification

  if classification_output.lead_type == "Disqualify":
    logfire.info("Lead classified as Disqualify, skipping n8n handoff.")
    return False

  # --- Determine Team Email (remains the same) ---
  team_email_map = {
      "Stahla Leads Team": ["isfescii@gmail.com", "femar.fredrick@gmail.com"],
      "Stahla Services Sales Team": ["femar.fredrick@gmail.com"],
      "Stahla Logistics Sales Team": ["femar.fredrick@gmail.com"],
  }
  default_email_list = ["isfescii@gmail.com"]  # Fallback email list

  assigned_team = classification_output.metadata.get(
      "assigned_owner_team") if classification_output.metadata else None
  team_email_list = team_email_map.get(
      assigned_team, default_email_list) if assigned_team else default_email_list

  # --- Prepare the structured payload for n8n ---
  # Extract IDs from HubSpotApiResult
  contact_id = contact_result.hubspot_id if contact_result else None
  lead_id = lead_result.hubspot_id if lead_result else None
  portal_id = settings.HUBSPOT_PORTAL_ID

  # Construct URLs if portal_id and object IDs are available
  contact_url = f"https://app.hubspot.com/contacts/{portal_id}/contact/{contact_id}" if portal_id and contact_id else None
  # Assuming 0-5 is the correct objectTypeId for Leads in HubSpot URLs
  lead_url = f"https://app.hubspot.com/contacts/{portal_id}/record/0-5/{lead_id}" if portal_id and lead_id else None

  # Use direct fields from input_data where available, fallback to metadata if needed
  payload = {
      "lead_details": {
          # Use verified/collected data first, fallback to metadata
          "contact_name": input_data.contact_name or f"{input_data.firstname or ''} {input_data.lastname or ''}".strip(),
          "first_name": input_data.firstname,  # Original metadata
          "last_name": input_data.lastname,  # Original metadata
          "email": input_data.contact_email or input_data.email,  # Verified email preferred
          "phone": input_data.phone,  # Original metadata phone
          # Verified company preferred
          "company_name": input_data.company_name or input_data.company,
          "message": None,  # No message field in ClassificationInput
          # From metadata
          "text_consent": input_data.by_submitting_this_form_you_consent_to_receive_texts,
          # Explicit consent from call
          "contact_consent_given": input_data.contact_consent_given
      },
      "event_details": {
          "project_category": input_data.project_category,  # From call
          "product_type_interest": input_data.product_type_interest,  # From call
          "what_service_do_you_need": input_data.what_service_do_you_need_,  # From metadata
          "units_needed": input_data.units_needed,  # From call (string)
          "required_stalls": input_data.required_stalls,  # Parsed number if available
          "how_many_portable_toilets": input_data.how_many_portable_toilet_stalls_,  # From metadata
          "expected_attendance": input_data.expected_attendance,  # From call
          "ada_required": input_data.ada_required,  # From call
          "shower_required": input_data.shower_required,  # From call
          "handwashing_needed": input_data.handwashing_needed,  # From call
          "additional_services_needed": input_data.additional_services_needed,  # From call
          "rental_start_date": input_data.rental_start_date,  # From call
          "rental_end_date": input_data.rental_end_date,  # From call
          "event_start_date_metadata": input_data.start_date,  # Original metadata
          "event_end_date_metadata": input_data.end_date,  # Original metadata
          "duration_days": input_data.duration_days,  # Calculated if available
          "service_address": input_data.service_address,  # From call
          "event_or_job_address_metadata": input_data.event_location_description,  # Original metadata
          "state": input_data.state,  # From call (extracted)
          "city": input_data.event_city,  # From classification input if parsed
          # From classification input if parsed
          "postal_code": input_data.event_postal_code,
          "address_type": input_data.address_type,  # From call
          "site_ground_level": input_data.site_ground_level,  # From call
          "site_ground_type": input_data.site_ground_type,  # From call
          "site_obstacles": input_data.site_obstacles,  # From call
          "power_available": input_data.power_available,  # From call
          # From call (string)
          "power_source_distance": input_data.power_source_distance,
          "power_path_cross": input_data.power_path_cross,  # From call
          "water_available": input_data.water_available,  # From call
          # From call (string)
          "water_source_distance": input_data.water_source_distance,
          "water_path_cross": input_data.water_path_cross,  # From call
          "quote_urgency": input_data.quote_urgency,  # From call
          "decision_timing": input_data.decision_timing,  # From call
          "follow_up_call_scheduled": input_data.follow_up_call_scheduled,  # From call
          "referral_accepted": input_data.referral_accepted  # From call
      },
      "classification": {
          # Fields generated by the classification process
          "lead_type": classification_output.lead_type,
          "routing_suggestion": classification_output.routing_suggestion,
          "confidence": classification_output.confidence,
          "reasoning": classification_output.reasoning,
          "estimated_value": classification_output.metadata.get("estimated_value", 0) if classification_output.metadata else 0,
          "is_local": input_data.is_local,  # Use field from input if available
          "is_in_service_area": input_data.is_in_service_area,  # From call logic
          "intended_use": input_data.intended_use,  # Use field from input if available
          "requires_human_review": classification_output.requires_human_review,
          # Keep original qualification_notes source
          "qualification_notes": classification_output.metadata.get("comments") if classification_output.metadata else None
      },
      "call_details": {
          # Use direct fields if available, fallback to metadata
          "call_summary": input_data.call_summary or (classification_output.metadata.get("call_summary") if classification_output.metadata else None),
          "call_recording_url": str(input_data.call_recording_url) if input_data.call_recording_url else (classification_output.metadata.get("call_recording_url") if classification_output.metadata else None),
          # Assuming this comes from metadata
          "call_duration_seconds": classification_output.metadata.get("call_duration_seconds") if classification_output.metadata else None
      },
      "routing": {
          "assigned_team": assigned_team,
          "team_email": team_email_list
      },
      "hubspot": {
          "contact_id": contact_id,
          "lead_id": lead_id,
          "portal_id": portal_id,
          "contact_url": contact_url,
          "lead_url": lead_url
      }
  }

  # Send the payload to n8n
  await send_to_n8n_webhook(payload=payload)


# Optional: Add a function to close the client gracefully if needed


async def close_n8n_client():
  await _client.aclose()
