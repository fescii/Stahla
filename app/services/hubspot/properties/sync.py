# app/services/hubspot/properties/sync.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import logfire

from app.models.hubspot import HubSpotApiResult
from app.services.hubspot.property.operations import PropertyOperations

logger = logging.getLogger(__name__)


class PropertySyncManager:
  """Manages synchronization of properties from JSON files to HubSpot."""

  def __init__(self, manager):
    """Initialize with HubSpot manager instance."""
    self.manager = manager
    self.property_ops = PropertyOperations(manager)
    self.properties_path = Path(
        __file__).parent.parent.parent.parent / "properties"

  async def sync_all_properties(self) -> Dict[str, Any]:
    """
    Sync all properties from contact.json and lead.json to HubSpot.

    Returns:
        Dict containing sync results for each object type
    """
    try:
      logfire.info("Starting property sync for all object types")

      results = {
          "contacts": await self._sync_properties_for_object("contacts", "contact.json"),
          "leads": await self._sync_properties_for_object("leads", "lead.json"),
          "summary": {}
      }

      # Generate summary
      total_created = sum(len(r.get("created", []))
                          for r in results.values() if isinstance(r, dict))
      total_existing = sum(len(r.get("existing", []))
                           for r in results.values() if isinstance(r, dict))
      total_failed = sum(len(r.get("failed", []))
                         for r in results.values() if isinstance(r, dict))

      results["summary"] = {
          "total_created": total_created,
          "total_existing": total_existing,
          "total_failed": total_failed,
          "status": "completed"
      }

      logfire.info(
          "Property sync completed",
          created=total_created,
          existing=total_existing,
          failed=total_failed
      )

      return results

    except Exception as e:
      logger.error(f"Error during property sync: {str(e)}")
      logfire.error("Property sync failed", error=str(e))
      return {
          "error": f"Property sync failed: {str(e)}",
          "status": "error"
      }

  async def sync_contact_properties(self) -> Dict[str, Any]:
    """
    Sync properties from contact.json to HubSpot contacts.

    Returns:
        Dict containing sync results
    """
    return await self._sync_properties_for_object("contacts", "contact.json")

  async def sync_lead_properties(self) -> Dict[str, Any]:
    """
    Sync properties from lead.json to HubSpot leads.

    Returns:
        Dict containing sync results
    """
    return await self._sync_properties_for_object("leads", "lead.json")

  async def _sync_properties_for_object(
      self,
      object_type: str,
      filename: str
  ) -> Dict[str, Any]:
    """
    Sync properties for a specific HubSpot object type.

    Args:
        object_type: HubSpot object type (e.g., 'contacts', 'leads')
        filename: JSON file containing property definitions

    Returns:
        Dict containing sync results
    """
    try:
      logfire.info(f"Starting property sync for {object_type}")

      # Load property definitions from JSON file
      properties_data = await self._load_properties_from_file(filename)
      if not properties_data:
        return {
            "error": f"No properties found in {filename}",
            "status": "error"
        }

      # Get existing properties from HubSpot
      existing_properties = await self._get_existing_properties(object_type)
      existing_property_names = {prop["name"] for prop in existing_properties}

      # Filter properties that don't exist yet
      properties_to_create = []
      existing_props = []

      for prop in properties_data:
        if prop["name"] in existing_property_names:
          existing_props.append({
              "name": prop["name"],
              "label": prop["label"],
              "type": prop["type"]
          })
        else:
          properties_to_create.append(prop)

      logfire.info(
          f"Properties analysis for {object_type}",
          total_properties=len(properties_data),
          existing_properties=len(existing_props),
          properties_to_create=len(properties_to_create)
      )

      # Create missing properties
      created_props = []
      failed_props = []

      if properties_to_create:
        for prop in properties_to_create:
          try:
            # Preprocess property before creation
            processed_prop = self._preprocess_property(prop)

            # Add detailed logging for debugging
            logfire.info(
                f"Creating property '{processed_prop['name']}' for {object_type}",
                property_type=processed_prop["type"],
                field_type=processed_prop["fieldType"],
                group_name=processed_prop.get("groupName"),
                has_options=bool(processed_prop.get("options"))
            )

            result = await self.property_ops.create_property_full(object_type, processed_prop)
            if result:
              created_props.append({
                  "name": prop["name"],
                  "label": prop["label"],
                  "type": prop["type"]
              })
            else:
              failed_props.append({
                  "name": prop["name"],
                  "label": prop["label"],
                  "error": "Creation failed"
              })
          except Exception as e:
            failed_props.append({
                "name": prop["name"],
                "label": prop["label"],
                "error": str(e)
            })

      return {
          "object_type": object_type,
          "created": created_props,
          "existing": existing_props,
          "failed": failed_props,
          "status": "completed"
      }

    except Exception as e:
      logger.error(f"Error syncing properties for {object_type}: {str(e)}")
      logfire.error(f"Property sync failed for {object_type}", error=str(e))
      return {
          "object_type": object_type,
          "error": f"Sync failed: {str(e)}",
          "status": "error"
      }

  async def _load_properties_from_file(self, filename: str) -> List[Dict[str, Any]]:
    """
    Load property definitions from JSON file.

    Args:
        filename: Name of the JSON file in the properties folder

    Returns:
        List of property definitions
    """
    try:
      file_path = self.properties_path / filename
      if not file_path.exists():
        logger.error(f"Properties file not found: {file_path}")
        return []

      with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

      properties = data.get("inputs", [])
      if not properties:
        logger.warning(f"No 'inputs' key found in {filename}")
        return []

      # Validate and clean property definitions
      validated_properties = []
      for prop in properties:
        if self._validate_property_definition(prop):
          validated_properties.append(prop)
        else:
          logger.warning(
              f"Invalid property definition skipped: {prop.get('name', 'unknown')}")

      logfire.info(
          f"Loaded {len(validated_properties)} properties from {filename}")
      return validated_properties

    except json.JSONDecodeError as e:
      logger.error(f"Invalid JSON in {filename}: {str(e)}")
      return []
    except Exception as e:
      logger.error(f"Error loading properties from {filename}: {str(e)}")
      return []

  def _validate_property_definition(self, prop: Dict[str, Any]) -> bool:
    """
    Validate a property definition.

    Args:
        prop: Property definition dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["name", "label", "type", "fieldType"]

    # Check required fields
    for field in required_fields:
      if field not in prop or not prop[field]:
        logger.warning(f"Property missing required field '{field}': {prop}")
        return False

    # Validate enumeration properties have options
    if prop["type"] == "enumeration":
      options = prop.get("options", [])
      if not options or not isinstance(options, list):
        logger.warning(
            f"Enumeration property '{prop['name']}' missing options")
        return False

      # Validate each option has required fields
      for option in options:
        if not isinstance(option, dict) or "label" not in option or "value" not in option:
          logger.warning(
              f"Enumeration property '{prop['name']}' has invalid option: {option}")
          return False

    # Validate field type compatibility
    property_type = prop["type"]
    field_type = prop["fieldType"]

    if property_type == "enumeration" and field_type == "checkbox":
      # Multi-select checkbox enumeration - ensure it's properly formatted
      logfire.info(
          f"Multi-select enumeration property detected: {prop['name']}")
    elif property_type == "bool" and field_type not in ["booleancheckbox", "checkbox"]:
      logger.warning(
          f"Boolean property '{prop['name']}' should use booleancheckbox or checkbox fieldType")
    elif property_type == "number" and field_type != "number":
      logger.warning(
          f"Number property '{prop['name']}' should use number fieldType")

    return True

  def _preprocess_property(self, prop: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocess a property definition before creation.

    Args:
        prop: Property definition dictionary

    Returns:
        Preprocessed property definition
    """
    processed_prop = prop.copy()

    # Handle property group mapping for different object types
    group_name = processed_prop.get("groupName", "")
    if group_name == "leadinformation":
      # Keep leadinformation for leads object - it's a valid group
      # Don't change the group name, let PropertyOperations handle the mapping
      logfire.info(
          f"Property group 'leadinformation' will be used for property: {processed_prop['name']}")

    # Handle multi-select enumeration properties
    if (processed_prop["type"] == "enumeration" and
            processed_prop["fieldType"] == "checkbox"):

      logfire.info(
          f"Processing multi-select property: {processed_prop['name']}")

      # Ensure options are properly formatted for multi-select
      options = processed_prop.get("options", [])
      if options:
        # Validate and clean options
        cleaned_options = []
        for i, option in enumerate(options):
          if isinstance(option, dict) and "label" in option and "value" in option:
            cleaned_option = {
                "label": str(option["label"]),
                "value": str(option["value"]),
                "displayOrder": option.get("displayOrder", i + 1)
            }
            cleaned_options.append(cleaned_option)
          else:
            logger.warning(
                f"Skipping invalid option in property '{processed_prop['name']}': {option}")

        processed_prop["options"] = cleaned_options

    # Handle boolean checkbox properties
    elif processed_prop["type"] == "bool":
      # Ensure proper fieldType for boolean
      if processed_prop["fieldType"] not in ["booleancheckbox", "checkbox"]:
        processed_prop["fieldType"] = "booleancheckbox"
        logfire.info(
            f"Corrected fieldType for boolean property: {processed_prop['name']}")

    # Handle number properties
    elif processed_prop["type"] == "number":
      # Ensure proper fieldType for numbers
      if processed_prop["fieldType"] != "number":
        processed_prop["fieldType"] = "number"
        logfire.info(
            f"Corrected fieldType for number property: {processed_prop['name']}")

    # Add currency display hint for number properties if specified
    if (processed_prop["type"] == "number" and
            processed_prop.get("numberDisplayHint") == "CURRENCY"):
      # This is handled by HubSpot natively, just log it
      logfire.info(
          f"Currency number property detected: {processed_prop['name']}")

    return processed_prop

  async def _get_existing_properties(self, object_type: str) -> List[Dict[str, Any]]:
    """
    Get existing properties from HubSpot for the specified object type.

    Args:
        object_type: HubSpot object type

    Returns:
        List of existing property definitions
    """
    try:
      return await self.property_ops.get_all_properties(object_type)
    except Exception as e:
      logger.error(
          f"Error getting existing properties for {object_type}: {str(e)}")
      return []

  async def check_property_status(
      self,
      object_type: str,
      property_names: List[str]
  ) -> Dict[str, Dict[str, Any]]:
    """
    Check the status of specific properties in HubSpot.

    Args:
        object_type: HubSpot object type
        property_names: List of property names to check

    Returns:
        Dict mapping property names to their status
    """
    try:
      results = {}

      for prop_name in property_names:
        try:
          prop_data = await self.property_ops.get_property(object_type, prop_name)
          if prop_data:
            results[prop_name] = {
                "exists": True,
                "type": prop_data.get("type"),
                "label": prop_data.get("label"),
                "fieldType": prop_data.get("fieldType"),
                "groupName": prop_data.get("groupName")
            }
          else:
            results[prop_name] = {
                "exists": False,
                "error": "Property not found"
            }
        except Exception as e:
          results[prop_name] = {
              "exists": False,
              "error": str(e)
          }

      return results

    except Exception as e:
      logger.error(f"Error checking property status: {str(e)}")
      return {prop_name: {"exists": False, "error": str(e)} for prop_name in property_names}
