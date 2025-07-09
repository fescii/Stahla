# app/api/v1/endpoints/hubspot/properties.py

from fastapi import APIRouter, Depends
from typing import Dict, Any, List
import logfire
import json
import os

from app.models.common import GenericResponse
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/properties", tags=["hubspot-properties"])


def _load_properties_file(filename: str) -> Dict[str, Any]:
  """Load properties from JSON file"""
  try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    properties_path = os.path.join(
        current_dir, "..", "..", "..", "..", "properties", filename)
    properties_path = os.path.abspath(properties_path)

    with open(properties_path, 'r') as f:
      return json.load(f)
  except Exception as e:
    logfire.error(f"Error loading properties file {filename}: {e}")
    return {"inputs": []}


@router.get("/contacts", response_model=GenericResponse[Dict[str, Any]])
async def get_contact_properties(
    current_user: User = Depends(get_current_user)
):
  """Get all available contact properties from contact.json"""
  try:
    properties_data = _load_properties_file("contact.json")

    # Transform the data for easier consumption
    properties = []
    field_names = []

    for field in properties_data.get("inputs", []):
      properties.append({
          "name": field.get("name"),
          "label": field.get("label"),
          "type": field.get("type"),
          "fieldType": field.get("fieldType"),
          "groupName": field.get("groupName"),
          "description": field.get("description", ""),
          "options": field.get("options", [])
      })
      field_names.append(field.get("name"))

    return GenericResponse(
        data={
            "object_type": "contacts",
            "total_properties": len(properties),
            "field_names": field_names,
            "properties": properties
        }
    )
  except Exception as e:
    logfire.error(f"Error fetching contact properties: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch contact properties",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/leads", response_model=GenericResponse[Dict[str, Any]])
async def get_lead_properties(
    current_user: User = Depends(get_current_user)
):
  """Get all available lead properties from lead.json"""
  try:
    properties_data = _load_properties_file("lead.json")

    # Transform the data for easier consumption
    properties = []
    field_names = []

    for field in properties_data.get("inputs", []):
      properties.append({
          "name": field.get("name"),
          "label": field.get("label"),
          "type": field.get("type"),
          "fieldType": field.get("fieldType"),
          "groupName": field.get("groupName"),
          "description": field.get("description", ""),
          "options": field.get("options", [])
      })
      field_names.append(field.get("name"))

    return GenericResponse(
        data={
            "object_type": "leads",
            "total_properties": len(properties),
            "field_names": field_names,
            "properties": properties
        }
    )
  except Exception as e:
    logfire.error(f"Error fetching lead properties: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch lead properties",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/all", response_model=GenericResponse[Dict[str, Any]])
async def get_all_properties(
    current_user: User = Depends(get_current_user)
):
  """Get all available properties from both contact.json and lead.json"""
  try:
    contact_data = _load_properties_file("contact.json")
    lead_data = _load_properties_file("lead.json")

    # Process contact properties
    contact_properties = []
    contact_field_names = []
    for field in contact_data.get("inputs", []):
      contact_properties.append({
          "name": field.get("name"),
          "label": field.get("label"),
          "type": field.get("type"),
          "fieldType": field.get("fieldType"),
          "groupName": field.get("groupName"),
          "description": field.get("description", ""),
          "options": field.get("options", [])
      })
      contact_field_names.append(field.get("name"))

    # Process lead properties
    lead_properties = []
    lead_field_names = []
    for field in lead_data.get("inputs", []):
      lead_properties.append({
          "name": field.get("name"),
          "label": field.get("label"),
          "type": field.get("type"),
          "fieldType": field.get("fieldType"),
          "groupName": field.get("groupName"),
          "description": field.get("description", ""),
          "options": field.get("options", [])
      })
      lead_field_names.append(field.get("name"))

    return GenericResponse(
        data={
            "contacts": {
                "object_type": "contacts",
                "total_properties": len(contact_properties),
                "field_names": contact_field_names,
                "properties": contact_properties
            },
            "leads": {
                "object_type": "leads",
                "total_properties": len(lead_properties),
                "field_names": lead_field_names,
                "properties": lead_properties
            },
            "summary": {
                "total_contact_properties": len(contact_properties),
                "total_lead_properties": len(lead_properties),
                "total_properties": len(contact_properties) + len(lead_properties)
            }
        }
    )
  except Exception as e:
    logfire.error(f"Error fetching all properties: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch properties",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/fields/contacts", response_model=GenericResponse[List[str]])
async def get_contact_field_names(
    current_user: User = Depends(get_current_user)
):
  """Get just the field names for contacts (useful for API queries)"""
  try:
    properties_data = _load_properties_file("contact.json")
    field_names = [field.get("name") for field in properties_data.get(
        "inputs", []) if field.get("name")]

    return GenericResponse(data=field_names)
  except Exception as e:
    logfire.error(f"Error fetching contact field names: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch contact field names",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/fields/leads", response_model=GenericResponse[List[str]])
async def get_lead_field_names(
    current_user: User = Depends(get_current_user)
):
  """Get just the field names for leads (useful for API queries)"""
  try:
    properties_data = _load_properties_file("lead.json")
    field_names = [field.get("name") for field in properties_data.get(
        "inputs", []) if field.get("name")]

    return GenericResponse(data=field_names)
  except Exception as e:
    logfire.error(f"Error fetching lead field names: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch lead field names",
        details={"error": str(e)},
        status_code=500
    )
