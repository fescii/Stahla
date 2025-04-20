# app/api/v1/endpoints/webhooks/hubspot.py

from fastapi import APIRouter, BackgroundTasks, Body
import logfire
from typing import Optional

# Import models
from app.models.webhook import HubSpotWebhookPayload
from app.models.hubspot import HubSpotDealProperties, HubSpotDealResult
from app.models.classification import ClassificationInput

# Import services
from app.services.hubspot import hubspot_manager
from app.services.classify.classification import classification_manager

# Import helpers
from .helpers import (
    _is_hubspot_contact_complete,
    _trigger_bland_call_for_hubspot,
    _update_hubspot_deal_after_classification,
    prepare_classification_input  # Assuming this is in helpers or imported there
)

router = APIRouter()


@router.post("/hubspot", summary="Handle HubSpot Webhook Events (e.g., Contact Creation)")
async def webhook_hubspot(
    payload: HubSpotWebhookPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
  """
  Receives webhook events from HubSpot.
  Specifically handles 'contact.creation' events.
  Fetches contact details, checks completeness.
  If complete: Classifies data, creates/updates deal, notifies n8n.
  If incomplete: Creates a basic deal, triggers Bland.ai call with deal_id.
  """
  logfire.info("Received HubSpot webhook payload.",
               events_count=len(payload.events))

  for event in payload.events:
    logfire.info(f"Processing HubSpot event: {event.subscriptionType}",
                 event_id=event.eventId, object_id=event.objectId)

    # --- Focus on Contact Creation events ---
    if event.subscriptionType == "contact.creation":
      contact_id = str(event.objectId)
      logfire.info(
          f"Handling contact.creation event for contact ID: {contact_id}")

      # 1. Fetch Contact Details from HubSpot
      contact_result = await hubspot_manager.get_contact_by_id(contact_id)

      if contact_result.status != "success" or not contact_result.properties:
        logfire.error("Failed to fetch HubSpot contact details.",
                      contact_id=contact_id, error=contact_result.message)
        continue  # Process next event if any

      contact_properties = contact_result.properties
      logfire.info("Successfully fetched contact details.",
                   contact_id=contact_id)

      # 2. Check if Contact Data is Complete
      is_complete = _is_hubspot_contact_complete(contact_properties)

      # 3. Create a Deal immediately
      deal_name = f"{contact_properties.get('firstname', 'Lead')} {contact_properties.get('lastname', '')} - HubSpot Lead".strip()
      initial_deal_props = HubSpotDealProperties(
          dealname=deal_name,
          stahla_lead_source="HUBSPOT_FORM",
          stahla_product_interest=contact_properties.get(
              "stahla_product_interest"),
          stahla_event_location=contact_properties.get(
              "stahla_event_location"),
          stahla_event_type=contact_properties.get("stahla_event_type"),
      )
      deal_result = await hubspot_manager.create_deal(initial_deal_props, associated_contact_id=contact_id)

      deal_id: Optional[str] = None
      if deal_result.status == "success" and isinstance(deal_result, HubSpotDealResult) and deal_result.id:
        deal_id = deal_result.id
        logfire.info("Successfully created initial HubSpot deal.",
                     deal_id=deal_id, contact_id=contact_id)
      else:
        error_message = getattr(deal_result, 'message',
                                'Unknown error during deal creation')
        error_details = getattr(deal_result, 'details', None)
        logfire.error("Failed to create initial HubSpot deal for contact.",
                      contact_id=contact_id, error=error_message, details=error_details)

      # 4. Handle based on completeness
      if is_complete:
        logfire.info("HubSpot contact data is complete. Proceeding with classification.",
                     contact_id=contact_id, deal_id=deal_id)
        if not deal_id:
          logfire.error(
              "Cannot proceed with classification as initial deal creation failed.", contact_id=contact_id)
          continue

        # Prepare ClassificationInput using updated field names
        classification_input = prepare_classification_input(
            source="hubspot_form",  # Or "hubspot_deal" if handling deal.creation
            raw_data={"hubspot_contact": contact_properties,
                      "hubspot_deal_id": deal_id},  # Include context
            # Map HubSpot properties to ClassificationInput fields
            # Use the confirmed internal names from Kevin
            extracted_data={
                "firstname": contact_properties.get("firstname"),
                "lastname": contact_properties.get("lastname"),
                "email": contact_properties.get("email"),
                "phone": contact_properties.get("phone"),
                "company": contact_properties.get("company"),
                "message": contact_properties.get("message"),  # Added
                # Added
                "text_consent": contact_properties.get("stahla_text_consent"),
                # Assuming service_needed is stored on contact
                # Renamed
                "service_needed": contact_properties.get("stahla_service_needed"),
                # Assuming stall count is stored on contact
                # Renamed
                "stall_count": contact_properties.get("how_many_portable_toilet_stalls_"),
                # ada_required might need specific mapping
                # Assuming custom field
                "ada_required": contact_properties.get("stahla_ada_required"),
                # Assuming custom field
                "event_type": contact_properties.get("stahla_event_type"),
                # Renamed
                "event_address": contact_properties.get("event_or_job_address"),
                "event_city": contact_properties.get("city"),
                "event_postal_code": contact_properties.get("zip"),
                # Renamed
                "event_start_date": contact_properties.get("stahla_event_start_date"),
                # Renamed
                "event_end_date": contact_properties.get("stahla_event_end_date"),
                # Add other relevant mappings based on your HubSpot properties
                # guest_count, power_available etc. might come from Deal or later calls
            }
        )

        # Classify
        classification_result = await classification_manager.classify_lead_data(classification_input)
        logfire.info("Classification result received for HubSpot lead.",
                     contact_id=contact_id, deal_id=deal_id,
                     classification=classification_result.model_dump(exclude={"input_data"}))

        # Update Deal and Notify n8n (background)
        background_tasks.add_task(
            _update_hubspot_deal_after_classification,
            classification_result,
            classification_input,
            contact_id,
            deal_id
        )

      else:  # Incomplete
        logfire.warn("HubSpot contact data incomplete. Triggering Bland.ai call.",
                     contact_id=contact_id, deal_id=deal_id)
        if deal_id:
          # Trigger Bland call (background)
          background_tasks.add_task(
              _trigger_bland_call_for_hubspot,
              contact_id,
              deal_id,
              contact_properties
          )
        else:
          logfire.error(
              "Skipping Bland call because initial deal creation failed.", contact_id=contact_id)

    else:
      logfire.debug(
          f"Ignoring HubSpot event type: {event.subscriptionType}", object_id=event.objectId)

  return {"status": "received", "message": "HubSpot events processed."}
