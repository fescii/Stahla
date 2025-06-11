# app/services/hubspot/contact/operations.py

import asyncio
import logging
from typing import Any, Dict, List, Optional
import json
from datetime import datetime, timezone

from hubspot.crm.contacts import (
    SimplePublicObjectInput as ContactSimplePublicObjectInput,
    ApiException as ContactApiException
)
from hubspot.crm.objects.exceptions import ApiException as ObjectApiException
import logfire

from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotContactInput,
    HubSpotApiResult,
    HubSpotObject,
    HubSpotSearchRequest,
    HubSpotSearchResponse,
    HubSpotSearchFilter,
    HubSpotSearchFilterGroup,
)
from ..utils.helpers import _handle_api_error, _is_valid_iso_date

logger = logging.getLogger(__name__)


class ContactOperations:
  def __init__(self, manager):
    self.manager = manager

  async def create(self, contact_input: HubSpotContactInput) -> HubSpotApiResult:
    """Create a new contact in HubSpot."""
    if hasattr(contact_input, 'properties'):
      properties = contact_input.properties
    else:
      # contact_input might be the properties directly
      properties = contact_input

    logger.debug(
        f"Creating contact with raw properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      props_dict = properties.model_dump(exclude_none=True)

      # Convert date strings to timestamps
      props_dict['event_start_date'] = self.manager._convert_date_to_timestamp_ms(
          props_dict.get('event_start_date'))
      props_dict['event_end_date'] = self.manager._convert_date_to_timestamp_ms(
          props_dict.get('event_end_date'))

      # Filter out None values that resulted from failed conversion or were already None
      final_props = {k: v for k, v in props_dict.items() if v is not None}

      logger.debug(f"Processed contact properties for HubSpot: {final_props}")

      simple_public_object_input = ContactSimplePublicObjectInput(
          properties=final_props
      )

      # Additional debugging before API call
      logger.info(
          f"About to call HubSpot API with contact properties: {json.dumps(final_props)}")

      api_response = await asyncio.to_thread(
          self.manager.client.crm.contacts.basic_api.create,
          simple_public_object_input_for_create=simple_public_object_input
      )
      logger.info(f"Successfully created contact ID: {api_response.id}")
      hubspot_object = HubSpotObject(**api_response.to_dict())

      return HubSpotApiResult(
          status="created",
          entity_type="contact",
          hubspot_id=api_response.id,
          message=f"Contact created successfully with ID: {api_response.id}",
          details=hubspot_object.model_dump(exclude_none=True)
      )
    except ObjectApiException as e:
      # Enhanced error logging for HubSpot API errors
      error_details = {}
      if hasattr(e, 'status'):
        error_details['status_code'] = e.status
      if hasattr(e, 'body'):
        error_details['response_body'] = e.body
      if hasattr(e, 'reason'):
        error_details['reason'] = e.reason

      logger.error(f"HubSpot API error during contact creation: {str(e)}",
                   extra={'error_details': error_details,
                          'contact_properties': properties.model_dump(exclude_none=True)})

      error_result = await _handle_api_error(e, "contact creation")
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=f"Failed to create contact: {str(e)}",
          details=error_result
      )
    except Exception as e:
      logger.error(f"Unexpected error during contact creation: {str(e)}",
                   extra={'contact_properties': properties.model_dump(
                       exclude_none=True)},
                   exc_info=True)
      error_result = await _handle_api_error(e, "contact creation")
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=f"Unexpected error during contact creation: {str(e)}",
          details=error_result
      )

  async def get_by_email(self, email: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    """Get a contact by email address."""
    logger.debug(f"Getting contact by email: {email}")

    # Search for contact by email
    search_request = HubSpotSearchRequest(
        filterGroups=[
            HubSpotSearchFilterGroup(
                filters=[
                    HubSpotSearchFilter(
                        propertyName="email",
                        operator="EQ",
                        value=email
                    )
                ]
            )
        ],
        properties=properties or ["hs_object_id", "email",
                                  "firstname", "lastname", "phone", "lifecyclestage"],
        limit=1
    )

    try:
      search_response = await self.search(search_request)
      if search_response.results:
        contact = search_response.results[0]
        return HubSpotApiResult(
            status="success",
            entity_type="contact",
            hubspot_id=contact.id,
            message=f"Contact found with email: {email}",
            details=contact.model_dump(exclude_none=True)
        )
      else:
        return HubSpotApiResult(
            status="not_found",
            entity_type="contact",
            message=f"No contact found with email: {email}"
        )
    except Exception as e:
      logger.error(
          f"Error searching for contact by email {email}: {str(e)}", exc_info=True)
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=f"Error searching for contact: {str(e)}"
      )

  async def get_by_id(self, contact_id: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    """Get a contact by ID."""
    logger.debug(
        f"Getting contact ID: {contact_id} with properties: {properties}"
    )
    try:
      fetch_properties = properties or [
          "email",
          "firstname",
          "lastname",
          "phone",
          "lifecyclestage",
          "hs_object_id",
      ]
      api_response = await asyncio.to_thread(
          self.manager.client.crm.contacts.basic_api.get_by_id,
          contact_id=contact_id,
          properties=fetch_properties,
          archived=False,  # Explicitly fetch non-archived
      )
      hubspot_object = HubSpotObject(**api_response.to_dict())
      return HubSpotApiResult(
          status="success",
          entity_type="contact",
          hubspot_id=contact_id,
          message=f"Contact retrieved successfully",
          details=hubspot_object.model_dump(exclude_none=True)
      )
    except ObjectApiException as e:
      if e.status == 404:
        logger.info(f"Contact with ID {contact_id} not found.")
        return HubSpotApiResult(
            status="not_found",
            entity_type="contact",
            message=f"Contact with ID {contact_id} not found"
        )
      else:
        error_result = await _handle_api_error(e, "get contact", contact_id)
        return HubSpotApiResult(
            status="error",
            entity_type="contact",
            message=f"Error retrieving contact {contact_id}: {str(e)}",
            details=error_result
        )
    except Exception as e:
      error_result = await _handle_api_error(e, "get contact", contact_id)
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=f"Unexpected error retrieving contact {contact_id}: {str(e)}",
          details=error_result
      )

  async def update_contact(
      self, contact_id: str, properties: HubSpotContactProperties
  ) -> Optional[HubSpotObject]:
    """Update an existing contact."""
    logger.debug(
        f"Updating contact ID: {contact_id} with raw properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )

    props_dict_for_update = properties.model_dump(
        exclude_none=True, exclude_unset=True)

    if not props_dict_for_update:
      logger.warning(
          f"Update contact called for ID {contact_id} with no properties to update. Skipping API call."
      )
      return await self.get_contact(contact_id)

    try:
      # Process date fields
      processed_props = {}
      for key, value in props_dict_for_update.items():
        if key in ['event_start_date', 'event_end_date']:
          if value is None:
            continue

          final_timestamp = None
          if isinstance(value, str) and _is_valid_iso_date(value):
            final_timestamp = self.manager._convert_date_to_timestamp_ms(value)
          elif isinstance(value, int):
            final_timestamp = value
          elif isinstance(value, datetime):
            dt_utc = value.astimezone(
                timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
            dt_midnight_utc = dt_utc.replace(
                hour=0, minute=0, second=0, microsecond=0)
            final_timestamp = int(dt_midnight_utc.timestamp() * 1000)

          if final_timestamp is not None:
            processed_props[key] = final_timestamp
        else:
          processed_props[key] = value

      if not processed_props:
        logger.info(
            f"No properties to update for contact {contact_id} after processing.")
        return await self.get_contact(contact_id)

      simple_public_object_input = ContactSimplePublicObjectInput(
          properties=processed_props)

      api_response = await asyncio.to_thread(
          self.manager.client.crm.contacts.basic_api.update,
          contact_id=contact_id,
          simple_public_object_input=simple_public_object_input,
      )
      logger.info(f"Successfully updated contact ID: {contact_id}")
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      await _handle_api_error(e, "update contact", contact_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "update contact", contact_id)
      return None

  async def delete_contact(self, contact_id: str) -> bool:
    """Delete (archive) a contact."""
    logger.debug(f"Archiving contact ID: {contact_id}")
    try:
      await asyncio.to_thread(self.manager.client.crm.contacts.basic_api.archive, contact_id=contact_id)
      logger.info(f"Successfully archived contact ID: {contact_id}")
      return True
    except ObjectApiException as e:
      if e.status == 404:
        logger.info(f"Contact with ID {contact_id} not found for archiving.")
        return True
      await _handle_api_error(e, "archive contact", contact_id)
      return False
    except Exception as e:
      await _handle_api_error(e, "archive contact", contact_id)
      return False

  async def create_or_update_contact(
      self, properties: HubSpotContactProperties
  ) -> HubSpotApiResult:
    """Create or update a contact based on email address."""
    logger.debug(
        f"Attempting to create or update contact for email: {properties.email}")

    if not properties.email:
      logger.error("Email is required to create or update a contact.")
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message="Email is required to create or update a contact.",
      )

    try:
      # Search for existing contact by email
      contact_email_str = str(properties.email)

      search_request = HubSpotSearchRequest(
          filterGroups=[
              HubSpotSearchFilterGroup(
                  filters=[
                      HubSpotSearchFilter(
                          propertyName="email",
                          operator="EQ",
                          value=contact_email_str
                      )
                  ]
              )
          ],
          properties=["hs_object_id", "email"],
          limit=1
      )
      existing_contacts_response = await self.manager.search_objects(
          object_type="contacts", search_request=search_request
      )

      existing_contact_id = None
      if existing_contacts_response and existing_contacts_response.results:
        if existing_contacts_response.results[0] and hasattr(existing_contacts_response.results[0], 'id'):
          existing_contact_id = existing_contacts_response.results[0].id
          logger.info(
              f"Found existing contact ID: {existing_contact_id} for email: {contact_email_str}")

      if existing_contact_id:
        # Update existing contact
        props_to_update = properties.model_dump(
            exclude_none=True, exclude_unset=True)
        updated_contact = await self.update_contact(existing_contact_id, properties)

        if updated_contact and updated_contact.id:
          if not props_to_update:
            message = f"Contact {existing_contact_id} found, no new properties provided for update."
            status = "success"
          else:
            message = f"Contact {existing_contact_id} updated successfully."
            status = "updated"

          return HubSpotApiResult(
              status=status,
              entity_type="contact",
              hubspot_id=updated_contact.id,
              message=message,
              details=updated_contact.model_dump(exclude_none=True)
          )
        else:
          return HubSpotApiResult(
              status="error",
              entity_type="contact",
              hubspot_id=existing_contact_id,
              message=f"Failed to update contact {existing_contact_id}.",
          )
      else:
        # Create new contact
        created_contact = await self.create_contact(properties)
        if created_contact and created_contact.id:
          return HubSpotApiResult(
              status="created",
              entity_type="contact",
              hubspot_id=created_contact.id,
              message="Contact created successfully.",
              details=created_contact.model_dump(exclude_none=True)
          )
        else:
          return HubSpotApiResult(
              status="error",
              entity_type="contact",
              message="Failed to create contact.",
          )
    except Exception as e:
      logger.error(
          f"Unexpected error in create_or_update_contact for email {properties.email}: {e}", exc_info=True)
      error_details_dict = await _handle_api_error(e, "create_or_update_contact")
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=error_details_dict.get(
              "error", f"An unexpected error occurred: {str(e)}"),
          details=error_details_dict
      )

  async def search(self, search_request: HubSpotSearchRequest) -> HubSpotSearchResponse:
    """Search for contacts."""
    try:
      return await self.manager.search_objects("contacts", search_request)
    except Exception as e:
      logger.error(f"Error searching contacts: {e}", exc_info=True)
      return HubSpotSearchResponse(total=0, results=[], paging=None)

  async def get_contact(
      self, contact_id: str, properties_list: Optional[List[str]] = None
  ) -> Optional[HubSpotObject]:
    """Get a contact by ID and return as HubSpotObject."""
    logger.debug(
        f"Getting contact ID: {contact_id} with properties: {properties_list}")
    try:
      fetch_properties = properties_list or [
          "email",
          "firstname",
          "lastname",
          "phone",
          "lifecyclestage",
          "hs_object_id",
      ]
      api_response = await asyncio.to_thread(
          self.manager.client.crm.contacts.basic_api.get_by_id,
          contact_id=contact_id,
          properties=fetch_properties,
          archived=False,
      )
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      if e.status == 404:
        logger.info(f"Contact with ID {contact_id} not found.")
      else:
        await _handle_api_error(e, "get contact", contact_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "get contact", contact_id)
      return None

  async def create_contact(
      self, properties: HubSpotContactProperties
  ) -> Optional[HubSpotObject]:
    """Create a new contact and return as HubSpotObject."""
    logger.debug(
        f"Creating contact with raw properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      props_dict = properties.model_dump(exclude_none=True)

      # Convert date strings to timestamps
      if hasattr(self.manager, '_convert_date_to_timestamp_ms'):
        props_dict['event_start_date'] = self.manager._convert_date_to_timestamp_ms(
            props_dict.get('event_start_date'))
        props_dict['event_end_date'] = self.manager._convert_date_to_timestamp_ms(
            props_dict.get('event_end_date'))

      # Filter out None values
      final_props = {k: v for k, v in props_dict.items() if v is not None}

      simple_public_object_input = ContactSimplePublicObjectInput(
          properties=final_props
      )

      api_response = await asyncio.to_thread(
          self.manager.client.crm.contacts.basic_api.create,
          simple_public_object_input_for_create=simple_public_object_input
      )
      logger.info(f"Successfully created contact ID: {api_response.id}")
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      await _handle_api_error(e, "contact creation")
      return None
    except Exception as e:
      await _handle_api_error(e, "contact creation")
      return None

  async def update(self, contact_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
    """Update a contact's properties."""
    try:
      contact_props = HubSpotContactProperties(**properties)
      result = await self.update_contact(contact_id, contact_props)
      if result:
        return HubSpotApiResult(
            status="updated",
            entity_type="contact",
            hubspot_id=result.id,
            message="Contact updated successfully"
        )
      else:
        return HubSpotApiResult(
            status="error",
            entity_type="contact",
            message="Failed to update contact"
        )
    except Exception as e:
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=f"Error updating contact: {str(e)}"
      )

  async def delete(self, contact_id: str) -> bool:
    """Delete (archive) a contact."""
    return await self.delete_contact(contact_id)

  async def create_or_update(self, contact_input: HubSpotContactInput) -> HubSpotApiResult:
    """Create or update a contact based on email."""
    try:
      properties = contact_input.properties
      return await self.create_or_update_contact(properties)
    except Exception as e:
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=f"Error in create_or_update: {str(e)}"
      )
