# app/api/v1/endpoints/webhooks/util/hubspot/validation.py

import logfire


def is_hubspot_contact_complete(contact_properties: dict) -> bool:
  """
  Check if the HubSpot contact properties contain the minimum required information
  to potentially create a complete Lead after classification/qualification.
  Checks mandatory Contact fields AND derivable mandatory Lead fields.
  Returns False if mandatory lead info (like quote_urgency) is missing,
  forcing the qualification (e.g., Bland call) flow.
  Uses HubSpot internal property names.
  """
  logfire.debug("Checking HubSpot contact completeness for potential lead creation",
                properties=contact_properties)

  # 1. Check Mandatory Contact fields from properties.csv
  mandatory_contact_fields = [
      contact_properties.get("firstname"),
      contact_properties.get("lastname"),
      contact_properties.get("email"),
      contact_properties.get("phone"),
      contact_properties.get("event_or_job_address"),
      contact_properties.get("event_start_date")
  ]
  contact_complete = all(prop is not None and str(prop).strip() !=
                         "" for prop in mandatory_contact_fields)

  if not contact_complete:
    logfire.info(
        "HubSpot contact completeness check failed: Missing mandatory contact fields.")
    return False

  # 2. Check if data for Mandatory Lead fields can be derived
  #    - project_category: Needs 'what_service_do_you_need_'
  #    - units_needed: Needs 'what_service_do_you_need_' and potentially stall counts
  #    - ada_required: Needs 'ada'
  #    - within_local_service_area: Needs address/zip ('event_or_job_address', 'zip') as proxy
  #    - quote_urgency: Cannot be derived from initial contact form.

  derivable_lead_fields_present = (
      contact_properties.get("what_service_do_you_need_") is not None and
      # Check if 'ada' exists, even if False
      contact_properties.get("ada") is not None and
      # Already checked but good for clarity
      contact_properties.get("event_or_job_address") is not None and
      # Check zip for location check proxy
      contact_properties.get("zip") is not None
      # We don't check stall counts explicitly here, assume 'units_needed' can be constructed if service is known.
  )

  # Crucially, 'quote_urgency' is mandatory for a Lead but not available initially.
  # Therefore, for the purpose of creating a lead *immediately*, the data is never complete.
  # Always false due to missing quote_urgency etc.
  can_create_lead_immediately = False

  final_completeness = contact_complete and derivable_lead_fields_present and can_create_lead_immediately

  logfire.info(f"HubSpot contact completeness check result: {final_completeness}",
               contact_fields_ok=contact_complete,
               derivable_lead_fields_ok=derivable_lead_fields_present,
               can_create_lead_immediately=can_create_lead_immediately)

  # This function will now effectively always return False in the context
  # of the initial webhook, forcing the 'incomplete' path.
  return final_completeness
