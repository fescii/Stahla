# app/services/n8n.py
import httpx
import logfire
from typing import Optional, Dict, Any

from app.core.config import settings
# Import ClassificationInput
from app.models.classification import ClassificationResult, ClassificationInput
from app.models.hubspot import HubSpotContactResult, HubSpotDealResult

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


async def trigger_n8n_handoff_automation(
    classification_result: ClassificationResult,
    input_data: ClassificationInput,
    contact_result: Optional[HubSpotContactResult],
    deal_result: Optional[HubSpotDealResult]
):
  """
  Prepares a structured payload and sends the handoff data to the n8n webhook.
  """
  if not classification_result.classification:
    logfire.info("No classification output available, skipping n8n handoff.")
    return False

  classification_output = classification_result.classification

  if classification_output.lead_type == "Disqualify":
    logfire.info("Lead classified as Disqualify, skipping n8n handoff.")
    return False

  # --- Determine Team Email ---
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
  extracted_metadata = classification_output.metadata or {}
  contact_id = contact_result.id if contact_result else None
  deal_id = deal_result.id if deal_result else None
  portal_id = settings.HUBSPOT_PORTAL_ID

  # Construct URLs if portal_id and object IDs are available
  contact_url = f"https://app.hubspot.com/contacts/{portal_id}/contact/{contact_id}" if portal_id and contact_id else None
  deal_url = f"https://app.hubspot.com/contacts/{portal_id}/deal/{deal_id}" if portal_id and deal_id else None

  payload = {
      "lead_details": {
          "first_name": input_data.firstname,
          "last_name": input_data.lastname,
          "email": input_data.email,
          "phone": input_data.phone,
          "company": input_data.company,
          "message": input_data.message,
          "text_consent": input_data.text_consent
      },
      "event_details": {
          # Consistently use extracted_metadata from AI classification
          "product_interest": extracted_metadata.get("product_interest"),
          "service_needed": extracted_metadata.get("service_needed"), # Use extracted value if available
          "event_type": extracted_metadata.get("event_type"),
          "location": extracted_metadata.get("location"),
          "state": extracted_metadata.get("state"), # Use extracted value if available
          "city": extracted_metadata.get("city"), # Use extracted value if available
          "postal_code": extracted_metadata.get("postal_code"), # Use extracted value if available
          "duration_days": extracted_metadata.get("duration_days"),
          "start_date": extracted_metadata.get("start_date"),
          "end_date": extracted_metadata.get("end_date"),
          "guest_count": extracted_metadata.get("guest_count"),
          "required_stalls": extracted_metadata.get("required_stalls"),
          "ada_required": extracted_metadata.get("ada_required"),
          "budget_mentioned": extracted_metadata.get("budget_mentioned"),
          "comments": extracted_metadata.get("comments"),
          "power_available": extracted_metadata.get("power_available"),
          "water_available": extracted_metadata.get("water_available")
      },
      "classification": {
          "lead_type": classification_output.lead_type,
          "routing_suggestion": classification_output.routing_suggestion,
          "confidence": classification_output.confidence,
          "reasoning": classification_output.reasoning,
          "estimated_value": extracted_metadata.get("estimated_value", 0),
          "is_local": extracted_metadata.get("is_local"),
          "intended_use": extracted_metadata.get("intended_use"),
          "requires_human_review": classification_output.requires_human_review,
          "qualification_notes": extracted_metadata.get("comments")
      },
      "call_details": {
          "call_summary": extracted_metadata.get("call_summary"),
          "call_recording_url": extracted_metadata.get("call_recording_url"),
          "call_duration_seconds": extracted_metadata.get("call_duration_seconds")
      },
      "routing": {
          "assigned_team": assigned_team,
          "team_email": team_email_list
      },
      "hubspot": {
          "contact_id": contact_id,
          "deal_id": deal_id,
          "deal_name": deal_result.properties.get("dealname") if deal_result and deal_result.properties else None,
          "portal_id": portal_id,
          "contact_url": contact_url,
          "deal_url": deal_url
      }
  }

  # Send the payload to n8n
  await send_to_n8n_webhook(payload=payload)


# Optional: Add a function to close the client gracefully if needed


async def close_n8n_client():
  await _client.aclose()
