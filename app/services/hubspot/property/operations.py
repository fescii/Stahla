# app/services/hubspot/property/operations.py

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire

from app.models.hubspot import HubSpotApiResult
from app.services.hubspot.utils.helpers import _handle_api_error

logger = logging.getLogger(__name__)


class PropertyOperations:
  def __init__(self, manager):
    self.manager = manager

  async def create_property(
      self,
      object_type: str,
      property_name: str,
      property_label: str,
      property_type: str = "string",
      group_name: Optional[str] = None
  ) -> HubSpotApiResult:
    """Create a custom property in HubSpot."""
    try:
      property_data = {
          "name": property_name,
          "label": property_label,
          "type": property_type,
          "fieldType": "text" if property_type == "string" else property_type,
          "groupName": group_name or "contactinformation"
      }

      result = await self.create_property_full(object_type, property_data)
      if result:
        return HubSpotApiResult(
            status="created",
            entity_type="property",
            message="Property created successfully"
        )
      else:
        return HubSpotApiResult(
            status="error",
            entity_type="property",
            message="Failed to create property"
        )
    except Exception as e:
      return HubSpotApiResult(
          status="error",
          entity_type="property",
          message=f"Error creating property: {str(e)}"
      )

  async def create_property_full(
      self, object_type: str, property_data: Dict[str, Any]
  ) -> Optional[Dict[str, Any]]:
    """Create a custom property with full property data."""
    try:
      # For leads, we need to discover valid property groups first
      if object_type == "leads":
        # Get existing properties to see what groups are available
        existing_props = await self.get_all_properties(object_type)
        if existing_props:
          # Extract unique group names from existing properties
          valid_groups = set()
          for prop in existing_props:
            if prop.get("groupName"):
              valid_groups.add(prop["groupName"])

          logfire.info(
              f"Found valid property groups for leads: {list(valid_groups)}")

          # Use the first available group or a common one
          if valid_groups:
            group_name = list(valid_groups)[0]  # Use first available group
            logfire.info(
                f"Using property group '{group_name}' for leads property '{property_data['name']}'")
          else:
            # If no existing properties have groups, omit groupName entirely
            group_name = None
            logfire.info(
                f"No property groups found for leads, creating property '{property_data['name']}' without group")
        else:
          # If we can't get existing properties, try without group
          group_name = None
          logfire.info(
              f"Cannot determine valid groups for leads, creating property '{property_data['name']}' without group")
      else:
        # For other object types, use the provided group name with mapping
        group_name = property_data.get("groupName")
        if object_type == "contacts" and group_name == "leadinformation":
          group_name = "contactinformation"

      # Handle field type mappings
      field_type = property_data["fieldType"]
      property_type = property_data["type"]

      # Skip properties with empty options for enumeration types
      if property_type == "enumeration":
        options = property_data.get("options", [])
        if not options:
          logfire.warning(
              f"Skipping property '{property_data['name']}' - enumeration type requires at least one option"
          )
          return None

      # Field type validations and mappings
      if property_type == "bool":
        if field_type not in ["booleancheckbox", "checkbox"]:
          field_type = "booleancheckbox"
      elif property_type == "string":
        if field_type not in ["text", "textarea", "email", "phonenumber"]:
          field_type = "text"
      elif property_type == "enumeration":
        # Handle multi-select/multi-choice enumeration fields
        if field_type == "checkbox":
          # For multi-select checkboxes, ensure proper handling
          field_type = "checkbox"
        elif field_type not in ["select", "radio", "checkbox"]:
          # Default to select for single choice
          field_type = "select"

      # Map to HubSpot format
      hubspot_property = {
          "name": property_data["name"],
          "label": property_data["label"],
          "type": property_type,
          "fieldType": field_type,
          "description": property_data.get("description", ""),
      }

      # Only include groupName if we have a valid one
      if group_name is not None:
        hubspot_property["groupName"] = group_name

      # Add options for enumeration properties
      if property_type == "enumeration" and "options" in property_data:
        hubspot_property["options"] = property_data["options"]
        logfire.info(
            f"Creating enumeration property '{property_data['name']}' with {len(property_data['options'])} options and fieldType '{field_type}'"
        )

      # Make API request
      response = await self.manager._http_client.post(
          f"/crm/v3/properties/{object_type}",
          json=hubspot_property
      )
      response.raise_for_status()

      logfire.info(
          f"Successfully created property '{property_data['name']}' for {object_type}")
      return response.json()

    except httpx.HTTPStatusError as e:
      if e.response.status_code == 409:  # Property already exists
        logfire.info(
            f"Property '{property_data['name']}' already exists for {object_type}")
        return await self.get_property(object_type, property_data["name"])

      try:
        error_response = e.response.json()
        error_message = error_response.get("message", e.response.text)
      except:
        error_message = e.response.text

      logger.error(
          f"Failed to create property '{property_data['name']}' for {object_type}: "
          f"Status {e.response.status_code} - {error_message}"
      )
      return None
    except Exception as e:
      logfire.error(
          "Failed to create property",
          object_type=object_type,
          property_name=property_data["name"],
          error=str(e)
      )
      return None

  async def get_property(
      self, object_type: str, property_name: str
  ) -> Optional[Dict[str, Any]]:
    """Get a specific property definition by name."""
    try:
      response = await self.manager._http_client.get(
          f"/crm/v3/properties/{object_type}/{property_name}"
      )
      response.raise_for_status()
      return response.json()
    except httpx.HTTPStatusError as e:
      if e.response.status_code == 404:
        return None
      logfire.error(
          "Failed to get property",
          object_type=object_type,
          property_name=property_name,
          status_code=e.response.status_code,
          error=e.response.text
      )
      return None
    except Exception as e:
      logfire.error(
          "Failed to get property",
          object_type=object_type,
          property_name=property_name,
          error=str(e)
      )
      return None

  async def get_all_properties(self, object_type: str) -> List[Dict[str, Any]]:
    """Get all properties for the specified object type."""
    try:
      response = await self.manager._http_client.get(
          f"/crm/v3/properties/{object_type}"
      )
      response.raise_for_status()
      result = response.json()
      return result.get("results", [])
    except httpx.HTTPStatusError as e:
      logfire.error(
          "Failed to get all properties",
          object_type=object_type,
          status_code=e.response.status_code,
          error=e.response.text
      )
      return []
    except Exception as e:
      logfire.error(
          "Failed to get all properties",
          object_type=object_type,
          error=str(e)
      )
      return []

  async def batch_create_properties(
      self, object_type: str, properties_data: List[Dict[str, Any]]
  ) -> Dict[str, Any]:
    """Batch create multiple properties."""
    results = {"created": [], "existing": [], "failed": []}

    try:
      # Prepare batch payload
      batch_inputs = []
      for prop_data in properties_data:
        hubspot_property = {
            "name": prop_data["name"],
            "label": prop_data["label"],
            "type": prop_data["type"],
            "fieldType": prop_data["fieldType"],
            "groupName": prop_data["groupName"],
            "description": prop_data.get("description", ""),
        }

        if prop_data["type"] == "enumeration" and "options" in prop_data:
          hubspot_property["options"] = prop_data["options"]

        batch_inputs.append(hubspot_property)

      # Make batch create request
      response = await self.manager._http_client.post(
          f"/crm/v3/properties/{object_type}/batch/create",
          json={"inputs": batch_inputs}
      )
      response.raise_for_status()

      response_data = response.json()
      if "results" in response_data:
        for result in response_data["results"]:
          results["created"].append({
              "name": result["name"],
              "label": result["label"],
              "type": result["type"]
          })

      logfire.info(
          f"Batch created {len(results['created'])} properties for {object_type}")

    except Exception as e:
      # Fall back to individual creation
      logfire.warning(
          f"Batch create failed, falling back to individual creation: {str(e)}")

      for prop_data in properties_data:
        result = await self.create_property_full(object_type, prop_data)
        if result:
          results["created"].append({
              "name": prop_data["name"],
              "label": prop_data["label"],
              "type": prop_data["type"]
          })
        else:
          results["failed"].append({
              "name": prop_data["name"],
              "label": prop_data["label"],
              "error": "Creation failed"
          })

    return results
