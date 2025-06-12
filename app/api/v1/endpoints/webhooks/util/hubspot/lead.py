# app/api/v1/endpoints/webhooks/util/hubspot/lead.py

import logfire
from typing import Optional, Dict, Any

# Import models
from app.models.classification import ClassificationInput, ClassificationResult, ClassificationOutput
from app.models.hubspot import HubSpotLeadProperties, HubSpotLeadInput, HubSpotApiResult

# Import services
from app.services.hubspot import hubspot_manager
from app.services.n8n import trigger_n8n_handoff_automation


async def create_lead_from_classification(
    classification_output: Optional[ClassificationOutput],
    input_data: ClassificationInput,
    contact_api_result: HubSpotApiResult
) -> Optional[str]:
  """
  Creates a lead in HubSpot based on classification output and input data.
  Returns the lead ID if successful, None otherwise.
  """
  if not classification_output:
    logfire.warn("No classification output provided for lead creation.")
    return None

  # 2. Create NEW Lead
  # Prepare lead properties using ClassificationInput and ClassificationResult
  lead_props = HubSpotLeadProperties(
      rental_start_date=getattr(input_data, 'event_start_date', None),
      rental_end_date=getattr(input_data, 'event_end_date', None),
      # Map from ClassificationResult (check hubspot.md for Lead property names)
      project_category=classification_output.metadata.get(
          "event_type") if classification_output and classification_output.metadata else None,
      units_needed=getattr(input_data, 'units_needed', None),
      expected_attendance=getattr(input_data, 'expected_attendance', None),
      ada_required=getattr(input_data, 'ada', None),
      additional_services_needed=getattr(
          input_data, 'additional_services_needed', None),
      onsite_facilities=classification_output.metadata.get(
          "onsite_facilities") if classification_output and classification_output.metadata else None,
      partner_referral_consent=getattr(
          input_data, 'partner_referral_consent', False),
      address_type=classification_output.metadata.get(
          "address_type") if classification_output and classification_output.metadata else None,
      power_source_distance=classification_output.metadata.get(
          "power_source_distance") if classification_output and classification_output.metadata else False,
      water_source_distance=classification_output.metadata.get(
          "water_source_distance") if classification_output and classification_output.metadata else False,
      site_working_hours=classification_output.metadata.get(
          "site_working_hours") if classification_output and classification_output.metadata else None,
      weekend_service_needed=classification_output.metadata.get(
          "weekend_service_needed") if classification_output and classification_output.metadata else None,
      cleaning_service_needed=classification_output.metadata.get(
          "cleaning_service_needed") if classification_output and classification_output.metadata else None,
      onsite_contact_name=classification_output.metadata.get(
          "onsite_contact_name") if classification_output and classification_output.metadata else None,
      onsite_contact_phone=classification_output.metadata.get(
          "onsite_contact_phone") if classification_output and classification_output.metadata else None,
      site_ground_type=classification_output.metadata.get(
          "site_ground_type") if classification_output and classification_output.metadata else None,
      site_obstacles=classification_output.metadata.get(
          "site_obstacles") if classification_output and classification_output.metadata else None,
      within_local_service_area=classification_output.metadata.get(
          "within_local_service_area") if classification_output and classification_output.metadata else None,
      needs_human_follow_up=classification_output.requires_human_review if classification_output else True,
      quote_urgency=classification_output.metadata.get(
          "quote_urgency") if classification_output and classification_output.metadata else None,
      ai_lead_type=classification_output.lead_type if classification_output else None,
      ai_classification_reasoning=classification_output.metadata.get(
          "ai_classification_reasoning") if classification_output and classification_output.metadata else None,
      ai_classification_confidence=classification_output.metadata.get(
          "ai_classification_confidence") if classification_output and classification_output.metadata else None,
      ai_routing_suggestion=classification_output.metadata.get(
          "ai_routing_suggestion") if classification_output and classification_output.metadata else None,
      ai_intended_use=classification_output.metadata.get(
          "ai_intended_use") if classification_output and classification_output.metadata else None,
      ai_qualification_notes=classification_output.metadata.get(
          "qualification_notes") if classification_output and classification_output.metadata else None,
      number_of_stalls=classification_output.metadata.get(
          "number_of_stalls") if classification_output and classification_output.metadata else None,
      event_duration_days=classification_output.metadata.get(
          "event_duration_days") if classification_output and classification_output.metadata else None,
      guest_count_estimate=classification_output.metadata.get(
          "guest_count_estimate") if classification_output and classification_output.metadata else None,
      ai_estimated_value=classification_output.metadata.get(
          "ai_estimated_value") if classification_output and classification_output.metadata else None,
  )

  # Remove None values before sending to HubSpot
  lead_props_dict = lead_props.model_dump(exclude_none=True, by_alias=True)
  lead_props_cleaned = HubSpotLeadProperties(**lead_props_dict)

  # Create a HubSpotLeadInput object with the lead properties
  # HubSpotLeadInput also needs contact information to create a contact first
  lead_input = HubSpotLeadInput(
      properties=lead_props_cleaned,
      email=getattr(input_data, 'email', None),
      phone=getattr(input_data, 'phone', None),
      contact_firstname=getattr(input_data, 'firstname', None),
      contact_lastname=getattr(input_data, 'lastname', None),
      # Optional company info if available
      company_name=getattr(input_data, 'company', None),
      company_domain=None,  # We don't have this in input_data
      # Optional fields
      project_category=classification_output.metadata.get(
          'event_type', None) if classification_output and classification_output.metadata else None,
      estimated_value=classification_output.metadata.get(
          'estimated_value', None) if classification_output and classification_output.metadata else None,
      lead_properties=lead_props_cleaned,
      owner_email=None,  # Set to None as we'll assign owner separately
  )

  # Call create_lead service function
  lead_result = await hubspot_manager.lead.create(lead_input)

  if lead_result.status != "success" or not lead_result.hubspot_id:
    logfire.error(
        "Failed to create HubSpot lead.",  # Updated log message
        lead_properties=lead_props_dict,
        error=lead_result.message,
        details=lead_result.details
    )
    return None

  lead_id = lead_result.hubspot_id
  logfire.info("HubSpot lead created successfully.",
               lead_id=lead_id)  # Updated log message

  # 3. Assign Owner (if applicable for Leads - check HubSpot setup)
  # The concept of pipelines/stages might not apply directly to Leads in the same way as Deals.
  # Owner assignment might still be relevant.
  if classification_output and classification_output.lead_type != "Disqualify":
    # Get active owners and assign one (implementation may vary based on your strategy)
    active_owners = await hubspot_manager.owner.get_active_owners()
    final_owner_id = active_owners[0].id if active_owners else None
    if final_owner_id:
      logfire.info(f"Assigning owner {final_owner_id} to new lead {lead_id}")
      # Update the lead with the owner ID
      await hubspot_manager.update_lead_properties(lead_id, {"hubspot_owner_id": final_owner_id})
    else:
      logfire.warn(f"Could not determine owner for new lead {lead_id}")

  return lead_id


async def update_hubspot_lead_after_classification(
    classification_result: ClassificationResult,
    input_data: ClassificationInput,
    contact_id: str,
    lead_id: Optional[str] = None
):
  """
  Creates a new HubSpot lead based on classification results, associates it with the contact,
  assigns owner, and triggers n8n handoff. Used after direct classification.
  """
  logfire.info("Entering update_hubspot_lead_after_classification (Create Lead Flow)",
               contact_id=contact_id, lead_id=lead_id or "None")

  classification_output = classification_result.classification
  if not classification_output:
    logfire.error("Classification output missing, cannot create HubSpot lead.",
                  contact_id=contact_id)
    return

  try:
    # 1. Prepare Lead Properties from Classification
    properties_for_creation = {}
    if classification_output:
      extracted_metadata = classification_output.metadata or {}
      # Map classification results to Lead properties (check hubspot.md)
      properties_for_creation = {
          "project_category": extracted_metadata.get("event_type"),
          # Or construct?
          "units_needed": extracted_metadata.get("service_needed"),
          "expected_attendance": extracted_metadata.get("guest_count"),
          "ada_required": extracted_metadata.get("ada_required"),
          # Map comments?
          "additional_services_needed": extracted_metadata.get("comments"),
          "onsite_facilities": extracted_metadata.get("onsite_facilities"),
          "rental_start_date": extracted_metadata.get("start_date"),
          "rental_end_date": extracted_metadata.get("end_date"),
          "site_working_hours": extracted_metadata.get("site_working_hours"),
          "weekend_service_needed": extracted_metadata.get("weekend_service_needed"),
          "cleaning_service_needed": extracted_metadata.get("cleaning_service_needed"),
          "onsite_contact_name": extracted_metadata.get("onsite_contact_name"),
          "onsite_contact_phone": extracted_metadata.get("onsite_contact_phone"),
          "site_ground_type": extracted_metadata.get("site_ground_type"),
          "site_obstacles": extracted_metadata.get("site_obstacles"),
          "water_source_distance": extracted_metadata.get("water_source_distance"),
          "power_source_distance": extracted_metadata.get("power_source_distance"),
          "within_local_service_area": extracted_metadata.get("is_local"),
          "needs_human_follow_up": classification_output.requires_human_review,
          "quote_urgency": extracted_metadata.get("quote_urgency"),
          # AI properties
          "ai_lead_type": classification_output.lead_type,
          "ai_classification_reasoning": classification_output.reasoning,
          "ai_classification_confidence": classification_output.confidence,
          "ai_routing_suggestion": classification_output.routing_suggestion,
          "ai_intended_use": extracted_metadata.get("intended_use"),
          "ai_qualification_notes": extracted_metadata.get("qualification_notes"),
          # Map from metadata if available
          "number_of_stalls": extracted_metadata.get("stall_count"),
          "event_duration_days": extracted_metadata.get("duration_days"),
          "guest_count_estimate": extracted_metadata.get("guest_count"),
          "ai_estimated_value": extracted_metadata.get("estimated_value"),
      }

    # Remove None values before sending to HubSpot
    lead_props_dict = {k: v for k,
                       v in properties_for_creation.items() if v is not None}
    lead_props_model = HubSpotLeadProperties(**lead_props_dict)

    result_lead_id = lead_id
    lead_result = None

    # If we already have a lead ID, update it
    if lead_id:
      logfire.info(f"Updating existing lead {lead_id}")
      lead_result = await hubspot_manager.update_lead_properties(lead_id, lead_props_dict)
      if lead_result.status != "success":
        logfire.error(
            f"Failed to update lead {lead_id}",
            error=lead_result.message,
            details=lead_result.details
        )
    # Otherwise create a new lead
    else:
      # 2. Create the Lead using HubSpotLeadInput
      logfire.info("Attempting to create HubSpot lead.",
                   contact_id=contact_id, properties=lead_props_dict)

      # Create a lead input object with all required properties
      lead_input = HubSpotLeadInput(
          properties=lead_props_model,
          email=input_data.email if hasattr(
              input_data, 'email') and input_data.email else None,
          phone=getattr(input_data, 'phone', None),
          contact_firstname=getattr(input_data, 'firstname', None),
          contact_lastname=getattr(input_data, 'lastname', None),
          # Other required fields with default values
          company_name=getattr(input_data, 'company', None),
          company_domain=None,
          project_category=extracted_metadata.get('event_type', None),
          estimated_value=extracted_metadata.get('estimated_value', None),
          lead_properties=lead_props_model,
          owner_email=None
      )

      # Call create_lead with the proper input object
      lead_result = await hubspot_manager.lead.create(lead_input)

      if lead_result.status != "success" or not lead_result.hubspot_id:
        logfire.error(
            "Failed to create HubSpot lead after classification.",
            contact_id=contact_id,
            lead_properties=lead_props_dict,
            error=lead_result.message,
            details=lead_result.details
        )
        return  # Stop processing if lead creation fails

      result_lead_id = lead_result.hubspot_id
      logfire.info("HubSpot lead created successfully.",
                   lead_id=result_lead_id, contact_id=contact_id)

      # 3. Assign Owner (if applicable)
      if classification_output and classification_output.lead_type != "Disqualify":
        # Get active owners and assign one
        active_owners = await hubspot_manager.owner.get_active_owners()
        final_owner_id = active_owners[0].id if active_owners else None
        if final_owner_id:
          logfire.info(
              f"Assigning owner {final_owner_id} to new lead {result_lead_id}")
          # Update the newly created lead with the owner ID
          owner_update_result = await hubspot_manager.update_lead_properties(result_lead_id, {"hubspot_owner_id": final_owner_id})
          if owner_update_result.status != "success":
            logfire.warn(
                f"Failed to assign owner {final_owner_id} to lead {result_lead_id}", details=owner_update_result.details)
        else:
          logfire.warn(
              f"Could not determine owner for new lead {result_lead_id}")

    # 4. Trigger n8n Handoff (if not disqualified)
    if classification_output and classification_output.lead_type != "Disqualify":
      logfire.info("Sending handoff data to n8n for new lead.",
                   contact_id=contact_id, lead_id=result_lead_id)
      # We need the contact details to send to n8n. Fetch them.
      contact_api_result = await hubspot_manager.get_contact_by_id(contact_id)
      if contact_api_result.status != "success":
        logfire.error("Failed to fetch contact details for n8n handoff.",
                      contact_id=contact_id, details=contact_api_result.details)
        # Proceed without contact details? Or handle error?
        # For now, proceed but log the error.
        contact_api_result = None  # Ensure it's None if fetch failed

      await trigger_n8n_handoff_automation(
          classification_result,
          input_data,
          contact_api_result,  # Pass fetched contact result (or None)
          lead_result  # Pass the lead creation result object
      )
    elif not classification_output:
      logfire.warn(
          "Skipping n8n handoff because classification output is missing.")
    else:
      logfire.info(
          "Skipping n8n handoff because lead was disqualified.")

  except Exception as e:
    logfire.exception(
        "Unhandled error during HubSpot lead creation/update process",
        contact_id=contact_id, lead_id=lead_id)
