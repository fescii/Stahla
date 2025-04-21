# app/api/v1/endpoints/webhooks/voice.py

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status
import logfire
from typing import Optional, Dict, Any

# Import models
from app.models.bland import BlandWebhookPayload
from app.models.classification import ClassificationInput

# Import services
from app.services.bland import bland_manager
from app.services.classify.classification import classification_manager
from app.services.hubspot import hubspot_manager # Added missing import

# Import helpers
from .helpers import (
    _handle_hubspot_update,
    _update_hubspot_deal_after_classification,
    prepare_classification_input
)

router = APIRouter()


@router.post(
    "/voice",
    summary="Receive Voice Transcripts from Bland.ai",
)
async def webhook_voice(
    payload: BlandWebhookPayload = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
  """
  Handles incoming webhook submissions containing voice transcripts from Bland.ai.
  Processes the transcript, extracts data, and sends for classification.
  If the call originated from an incomplete HubSpot lead, updates the existing HubSpot deal.
  Otherwise, creates a new contact/deal.
  """
  logfire.info("Received voice webhook payload via API.",
               call_id=payload.call_id)

  # Process transcript
  processing_result = await bland_manager.process_incoming_transcript(payload)

  if processing_result.status == "error":
    logfire.error("Failed to process Bland transcript.",
                  call_id=payload.call_id, message=processing_result.message)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=processing_result.message or "Failed to process voice transcript."
    )

  logfire.info("Bland transcript processed, proceeding to classification.",
               call_id=payload.call_id)

  extracted_data = processing_result.details.get("extracted_data", {})
  raw_data = payload.model_dump(mode='json')

  # Check for HubSpot IDs in Metadata
  hubspot_contact_id: Optional[str] = None
  hubspot_deal_id: Optional[str] = None
  metadata = {}
  # Check both payload.variables.metadata and payload.metadata
  if getattr(payload, 'variables', None) and isinstance(payload.variables, dict) and \
     payload.variables.get('metadata', None) and isinstance(payload.variables['metadata'], dict):
    metadata = payload.variables['metadata']
  elif getattr(payload, 'metadata', None) and isinstance(payload.metadata, dict):
    metadata = payload.metadata

  contact_properties_from_hubspot: Dict[str, Any] = {} # Initialize dict for fetched properties

  if metadata:
    hubspot_contact_id = metadata.get("hubspot_contact_id")
    hubspot_deal_id = metadata.get("hubspot_deal_id")
    logfire.info("Found metadata in Bland payload.",
                 contact_id=hubspot_contact_id, deal_id=hubspot_deal_id)
    
    # --- Fetch HubSpot Contact Details --- 
    if hubspot_contact_id:
        logfire.info(f"Fetching HubSpot contact details for ID: {hubspot_contact_id}")
        contact_result = await hubspot_manager.get_contact_by_id(hubspot_contact_id)
        if contact_result.status == "success" and contact_result.properties:
            contact_properties_from_hubspot = contact_result.properties
            logfire.info("Successfully fetched HubSpot contact properties.")
        else:
            logfire.warn("Failed to fetch HubSpot contact details from voice webhook.", 
                         contact_id=hubspot_contact_id, error=contact_result.message)
    # --- End Fetch --- 

    form_data = metadata.get('form_submission_data', {})
    if form_data:
      logfire.info(
          "Merging form_submission_data from metadata into extracted_data")
      # Update extracted_data, giving priority to form_data for common fields
      extracted_data.update(form_data)

  # --- Merge Fetched HubSpot Properties --- 
  # Merge fetched properties, giving priority to existing extracted_data (from call/form metadata)
  merged_extracted_data = contact_properties_from_hubspot.copy() # Start with HubSpot data
  merged_extracted_data.update(extracted_data) # Overwrite with call/form data if present
  extracted_data = merged_extracted_data # Use the merged data going forward
  # --- End Merge --- 

  # Add call-specific details (ensure they don't overwrite metadata if already present)
  extracted_data.setdefault(
      "call_recording_url", getattr(payload, 'recording_url', None))
  extracted_data.setdefault("call_summary", getattr(payload, 'summary', None))
  # Ensure full_transcript is also added if needed
  extracted_data.setdefault("full_transcript", getattr(payload, 'concatenated_transcript', None))

  logfire.info("Final data prepared for classification (Voice)",
               has_email=bool(extracted_data.get('email')),
               email=extracted_data.get('email'),
               merged_data_keys=list(extracted_data.keys()))

  # Prepare ClassificationInput using the enriched extracted_data
  classification_input = prepare_classification_input(
      source="voice",
      raw_data=raw_data,
      extracted_data=extracted_data
  )

  logfire.info("Created classification input for voice webhook",
               email=classification_input.email,
               has_email=bool(classification_input.email))

  # Classify
  classification_result = await classification_manager.classify_lead_data(classification_input)
  logfire.info("Classification result received.",
               result=classification_result.model_dump(exclude={"input_data"}))

  # --- Update classification_input with extracted details --- 
  if classification_result.status == "success" and classification_result.classification:
      extracted_metadata = classification_result.classification.metadata or {}
      logfire.info("Updating classification_input with extracted metadata", metadata=extracted_metadata)
      
      # Fields to update from extracted metadata
      fields_to_update = {
          "product_interest": extracted_metadata.get("product_interest"),
          "event_type": extracted_metadata.get("event_type"),
          "event_address": extracted_metadata.get("location"), # Map location to event_address
          "event_state": extracted_metadata.get("state"), # Assuming AI extracts state
          "event_city": extracted_metadata.get("city"), # Assuming AI extracts city
          "event_postal_code": extracted_metadata.get("postal_code"), # Assuming AI extracts postal code
          "duration_days": extracted_metadata.get("duration_days"),
          "event_start_date": extracted_metadata.get("start_date"),
          "event_end_date": extracted_metadata.get("end_date"),
          "guest_count": extracted_metadata.get("guest_count"),
          "required_stalls": extracted_metadata.get("required_stalls"),
          "ada_required": extracted_metadata.get("ada_required"),
          "budget_mentioned": extracted_metadata.get("budget_mentioned"),
          "comments": extracted_metadata.get("comments"), # Map comments
          "power_available": extracted_metadata.get("power_available"),
          "water_available": extracted_metadata.get("water_available"),
          # Add service_needed if AI extracts it, otherwise it remains from initial data
          # "service_needed": extracted_metadata.get("service_needed"), 
      }

      for field, value in fields_to_update.items():
          if value is not None:
              setattr(classification_input, field, value)
              logfire.debug(f"Updated classification_input.{field}", value=value)
  # --- End Update --- 

  # HubSpot Integration (Update or Create)
  # Pass the UPDATED classification_input to the helper functions
  final_contact_id: Optional[str] = None
  final_deal_id: Optional[str] = None

  if hubspot_deal_id and hubspot_contact_id:
    logfire.info("Updating existing HubSpot deal via /voice webhook.",
                 contact_id=hubspot_contact_id, deal_id=hubspot_deal_id)
    # Update existing deal in background
    background_tasks.add_task(
        _update_hubspot_deal_after_classification,
        classification_result,
        classification_input, # Pass updated input
        hubspot_contact_id,
        hubspot_deal_id
    )
    final_contact_id = hubspot_contact_id
    final_deal_id = hubspot_deal_id
  else:
    logfire.info(
        "No existing HubSpot deal ID found in metadata, creating new contact/deal.")
    # Create new contact/deal in background

    async def _run_handle_hubspot_update_in_background():
      nonlocal final_contact_id, final_deal_id
      c_id, d_id = await _handle_hubspot_update(classification_result, classification_input) # Pass updated input
      final_contact_id = c_id
      final_deal_id = d_id
      logfire.info("Background HubSpot update completed (create/update)",
                   contact_id=c_id, deal_id=d_id)

    background_tasks.add_task(_run_handle_hubspot_update_in_background)
    # IDs will be None in the immediate response
    final_contact_id = None
    final_deal_id = None

  # Return response
  # The classification object in the response already comes from classification_result
  return {
      "status": "received",
      "source": "voice",
      "action": "classification_complete",
      "classification": classification_result.classification.model_dump() if classification_result.classification else None,
      "hubspot_contact_id": final_contact_id,  # May be None if backgrounded
      "hubspot_deal_id": final_deal_id      # May be None if backgrounded
  }
