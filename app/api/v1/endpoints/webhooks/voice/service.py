# app/api/v1/endpoints/webhooks/voice/service.py

import logfire
from fastapi import BackgroundTasks
from typing import Dict, Tuple, Optional, Any

# Import models
from app.models.bland import BlandWebhookPayload
from app.models.classification import ClassificationInput, ClassificationResult

# Import shared utilities for HubSpot integration
from ..util.hubspot import update_hubspot_lead_after_classification, handle_hubspot_update


def merge_data_sources(
    extracted_data: Dict[str, Any],
    payload: BlandWebhookPayload
) -> Tuple[Dict[str, Any], Optional[str], Optional[str]]:
  """
  Merges data from extracted_data dictionary with metadata from the payload.
  Returns the merged data dictionary and HubSpot IDs if present.
  """
  hubspot_contact_id: Optional[str] = None
  hubspot_lead_id: Optional[str] = None

  # Check both payload.variables.metadata and payload.metadata
  metadata = {}
  if getattr(payload, 'variables', None) and isinstance(payload.variables, dict) and \
     payload.variables.get('metadata', None) and isinstance(payload.variables['metadata'], dict):
    metadata = payload.variables['metadata']
  elif getattr(payload, 'metadata', None) and isinstance(payload.metadata, dict):
    metadata = payload.metadata

  # Initialize dict for fetched properties
  contact_properties_from_hubspot: Dict[str, Any] = {}

  if metadata:
    hubspot_contact_id = metadata.get("hubspot_contact_id")
    hubspot_lead_id = metadata.get("hubspot_lead_id")
    logfire.info("Found metadata in Bland payload.",
                 contact_id=hubspot_contact_id, lead_id=hubspot_lead_id)

    # --- Fetch HubSpot Contact Details if needed ---
    # This is moved to a separate function if the contact details need to be fetched

    # Merge form_submission_data from metadata if present
    form_data = metadata.get('form_submission_data', {})
    if form_data:
      logfire.info(
          "Merging form_submission_data from metadata into extracted_data")
      # Update extracted_data, giving priority to form_data for common fields
      extracted_data.update(form_data)

  return extracted_data, hubspot_contact_id, hubspot_lead_id


def update_classification_input(
    classification_input: ClassificationInput,
    extracted_metadata: Dict[str, Any]
) -> ClassificationInput:
  """
  Updates the ClassificationInput with data extracted from classification result metadata.
  """
  logfire.info("Updating classification_input with extracted metadata",
               metadata=extracted_metadata)

  # Fields to update from extracted metadata
  fields_to_update = {
      "product_interest": extracted_metadata.get("product_interest"),
      "event_type": extracted_metadata.get("event_type"),
      # Map location to event_address
      "event_address": extracted_metadata.get("location"),
      # Assuming AI extracts state
      "event_state": extracted_metadata.get("state"),
      # Assuming AI extracts city
      "event_city": extracted_metadata.get("city"),
      # Assuming AI extracts postal code
      "event_postal_code": extracted_metadata.get("postal_code"),
      "duration_days": extracted_metadata.get("duration_days"),
      "event_start_date": extracted_metadata.get("start_date"),
      "event_end_date": extracted_metadata.get("end_date"),
      "guest_count": extracted_metadata.get("guest_count"),
      "required_stalls": extracted_metadata.get("required_stalls"),
      "ada_required": extracted_metadata.get("ada_required"),
      "budget_mentioned": extracted_metadata.get("budget_mentioned"),
      "comments": extracted_metadata.get("comments"),  # Map comments
      "power_available": extracted_metadata.get("power_available"),
      "water_available": extracted_metadata.get("water_available"),
  }

  for field, value in fields_to_update.items():
    if value is not None:
      setattr(classification_input, field, value)
      logfire.debug(f"Updated classification_input.{field}", value=value)

  return classification_input


async def handle_hubspot_integration(
    classification_result: ClassificationResult,
    classification_input: ClassificationInput,
    hubspot_contact_id: Optional[str],
    hubspot_lead_id: Optional[str],
    background_tasks: BackgroundTasks
) -> Tuple[Optional[str], Optional[str]]:
  """
  Handles HubSpot integration based on classification results.
  Returns the final contact_id and lead_id.
  """
  final_contact_id: Optional[str] = None
  final_lead_id: Optional[str] = None

  if hubspot_lead_id and hubspot_contact_id:
    logfire.info("Updating existing HubSpot lead via /voice webhook.",
                 contact_id=hubspot_contact_id, lead_id=hubspot_lead_id)
    # Update existing lead in background
    background_tasks.add_task(
        update_hubspot_lead_after_classification,
        classification_result,
        classification_input,  # Pass updated input
        hubspot_contact_id,
        hubspot_lead_id
    )
    final_contact_id = hubspot_contact_id
    final_lead_id = hubspot_lead_id
  else:
    logfire.info(
        "No existing HubSpot lead ID found in metadata, creating new contact/lead.")
    # Create new contact/lead in background

    async def _run_handle_hubspot_update_in_background():
      nonlocal final_contact_id, final_lead_id
      c_id, l_id = await handle_hubspot_update(classification_result, classification_input)
      final_contact_id = c_id
      final_lead_id = l_id
      logfire.info("Background HubSpot update completed (create/update)",
                   contact_id=c_id, lead_id=l_id)

    background_tasks.add_task(_run_handle_hubspot_update_in_background)
    # IDs will be None in the immediate response
    final_contact_id = None
    final_lead_id = None

  return final_contact_id, final_lead_id
