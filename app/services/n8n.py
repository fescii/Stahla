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
  # Example mapping (adjust emails as needed)
  # Store emails as lists
  team_email_map = {
      "Stahla Leads Team": ["isfescii@gmail.com", "femar.fredrick@gmail.com"],
      "Stahla Services Sales Team": ["femar.fredrick@gmail.com"],
      "Stahla Logistics Sales Team": ["femar.fredrick@gmail.com"],
  }
  default_email_list = ["isfescii@gmail.com"]  # Fallback email list

  assigned_team = classification_output.metadata.get(
      "assigned_owner_team") if classification_output.metadata else None
  # Get the list of emails, defaulting to the default_email_list
  team_email_list = team_email_map.get(
      assigned_team, default_email_list) if assigned_team else default_email_list

  # --- Prepare the structured payload for n8n ---
  payload = {
      "lead_details": {
          "first_name": input_data.firstname,
          "last_name": input_data.lastname,
          "email": input_data.email,
          "phone": input_data.phone,
          "company": input_data.company,
          "source_url": str(input_data.source_url) if input_data.source_url else None,
      },
      "event_details": {
          # Join list if product_interest is a list, otherwise use as is
          "product_interest": ', '.join(input_data.product_interest) if isinstance(input_data.product_interest, list) else input_data.product_interest,
          "event_type": input_data.event_type,
          "location": input_data.event_location_description,
          "state": input_data.event_state,
          "duration_days": input_data.duration_days,
          "start_date": str(input_data.start_date) if input_data.start_date else None,
          "end_date": str(input_data.end_date) if input_data.end_date else None,
          "guest_count": input_data.guest_count,
          "required_stalls": input_data.required_stalls,
          "ada_required": input_data.ada_required,
          "budget_mentioned": input_data.budget_mentioned,
          "comments": input_data.comments,
      },
      "classification": {
          "lead_type": classification_output.lead_type,
          "routing_suggestion": classification_output.routing_suggestion,
          "confidence": classification_output.confidence,
          "reasoning": classification_output.reasoning,
          "estimated_value": classification_output.metadata.get("estimated_value") if classification_output.metadata else None,
      },
      "routing": {
          "assigned_team": assigned_team,
          "team_email": team_email_list  # Assign the list directly
      },
      "hubspot": {
          "contact_id": contact_result.id if contact_result else None,
          "deal_id": deal_result.id if deal_result else None,
          "deal_name": deal_result.properties.get("dealname") if deal_result and deal_result.properties else None,
          "portal_id": settings.HUBSPOT_PORTAL_ID  # Add portal ID from settings
      }
  }

  # Remove top-level keys if their value is None (optional, keeps payload cleaner)
  # payload = {k: v for k, v in payload.items() if v is not None}

  logfire.info("Triggering n8n handoff automation with structured payload.")
  return await send_to_n8n_webhook(payload=payload, api_key=settings.N8N_API_KEY)

# Optional: Add a function to close the client gracefully if needed


async def close_n8n_client():
  await _client.aclose()
