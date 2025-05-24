# app/services/hubspot.py

# Standard library imports
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Literal
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import json

from cachetools import TTLCache
from hubspot import HubSpot
from hubspot.crm.associations.v4.models import (
    AssociationSpec,
    PublicObjectId,
    BatchInputPublicAssociationMultiPost,
    PublicAssociationMultiPost,
)
from hubspot.crm.associations.models import (
    BatchInputPublicAssociation,
    PublicAssociation,
)
from hubspot.crm.companies import SimplePublicObjectInput
from hubspot.crm.contacts import (
    SimplePublicObjectInput as ContactSimplePublicObjectInput,
    ApiException as ContactApiException
)
from hubspot.crm.deals import (
    SimplePublicObjectInput as DealSimplePublicObjectInput,
    ApiException as DealApiException
)
from hubspot.crm.objects.exceptions import (
    ApiException as ObjectApiException,
)
from hubspot.crm.owners import (
    ApiException as OwnersApiException,
)
from hubspot.crm.owners import PublicOwner
from hubspot.crm.pipelines import (
    Pipeline,
    PipelineStage,
)
from pydantic import ValidationError
import logfire

from app.core.config import settings
from app.models.hubspot import (
    HubSpotContactProperties,
    HubSpotLeadProperties,
    HubSpotCompanyProperties,
    HubSpotCompanyInput,
    HubSpotContactInput,
    HubSpotLeadInput,
    HubSpotErrorDetail,
    HubSpotApiResult,
    HubSpotObject,
    HubSpotSearchRequest,
    HubSpotSearchResponse,
    HubSpotPipeline,
    HubSpotPipelineStage,
    HubSpotOwner,
    HubSpotSearchFilter,
    HubSpotSearchFilterGroup,
)

logger = logging.getLogger(__name__)


def _is_valid_iso_date(date_input: Any) -> bool:
  """Checks if a string is a valid YYYY-MM-DD date."""
  if not isinstance(date_input, str):
    return False
  try:
    datetime.strptime(date_input, "%Y-%m-%d")
    return True
  except ValueError:
    return False


async def _handle_api_error(
    e: Exception, context: str, object_id: Optional[str] = None
) -> Dict[str, Any]:
  """
  Centralized handler for HubSpot API errors.
  Logs the error and returns a structured error dictionary.
  """
  error_message = f"HubSpot API error in {context}"
  if object_id:
    error_message += f" for ID {object_id}"

  error_details_str = str(e)
  status_code = None
  parsed_error_details = None

  # Check for specific property validation errors
  property_validation_errors = []

  if isinstance(e, (ObjectApiException, DealApiException)):
    status_code = e.status
    if hasattr(e, "body") and e.body:
      error_details_str = e.body

      # Check for property validation error messages in the raw body
      if "Property values were not valid" in error_details_str:
        logfire.error(f"Property validation error detected in HubSpot API response",
                      context=context, object_id=object_id, status_code=status_code, error_body=error_details_str)

      try:
        # Enhanced error parsing for property-related issues
        if "PROPERTY_DOESNT_EXIST" in error_details_str:
          # Extract property name from error message
          import re
          property_match = re.search(
              r'Property \\"([^"]+)\\" does not exist', error_details_str)
          if property_match:
            invalid_property = property_match.group(1)
            logfire.error(f"Invalid HubSpot property name detected",
                          property_name=invalid_property,
                          context=context,
                          object_id=object_id)
            property_validation_errors.append({
                "property_name": invalid_property,
                "error": "Property does not exist in HubSpot"
            })

        # Attempt to parse the HubSpot error body if your HubSpotErrorDetail model is set up
        if HubSpotErrorDetail:  # Check if the model is available
          parsed_error_details = HubSpotErrorDetail.model_validate_json(
              e.body
          ).model_dump()
          logger.error(
              f"{error_message}: Status {status_code}, Parsed Body: {parsed_error_details}",
              exc_info=True,
          )
        else:
          logger.error(
              f"{error_message}: Status {status_code}, Raw Body: {e.body}",
              exc_info=True,
          )
      except (
          ValidationError,
          Exception,
      ) as parse_err:  # Catch Pydantic validation error or other parsing issues
        logger.error(
            f"{error_message}: Status {status_code}, Raw Body: {e.body}. Failed to parse error body: {parse_err}",
            exc_info=True,
        )
    else:
      logger.error(
          f"{error_message}: Status {status_code}, Details: {str(e)} (No body)",
          exc_info=True,
      )
  else:
    logger.error(
        f"Unexpected error occurred in {context}",
        extra={
            "error_message": error_message,
            "object_id": object_id,
            "context": context,
            "exception": str(e),
        },
        exc_info=True,
    )

  return {
      "error": error_message,
      "details_raw": error_details_str,
      "details_parsed": parsed_error_details,
      "status_code": status_code,
      "context": context,
      "object_id": object_id,
      "property_validation_errors": property_validation_errors if property_validation_errors else None,
  }


class HubSpotManager:
  def __init__(self, access_token: Optional[str] = None):
    self.access_token = access_token or settings.HUBSPOT_ACCESS_TOKEN
    if not self.access_token:
      logger.error("HubSpot access token is not configured.")
      raise ValueError("HubSpot access token is not configured.")
    try:
      self.client = HubSpot(access_token=self.access_token)
      # Test client connectivity (optional, but good for early failure detection)
      # self.client.crm.contacts.basic_api.get_page(limit=1) # Example call
      logger.info("HubSpot client initialized successfully.")
    except Exception as e:
      logger.error(f"Failed to initialize HubSpot client: {e}", exc_info=True)
      raise ValueError(f"Failed to initialize HubSpot client: {e}")

    self.pipelines_cache = TTLCache(
        maxsize=100, ttl=settings.CACHE_TTL_HUBSPOT_PIPELINES
    )
    self.stages_cache = TTLCache(
        maxsize=500, ttl=settings.CACHE_TTL_HUBSPOT_STAGES)
    self.owners_cache = TTLCache(
        maxsize=100, ttl=settings.CACHE_TTL_HUBSPOT_OWNERS)

    self.DEFAULT_DEAL_PIPELINE_NAME = (
        settings.HUBSPOT_DEFAULT_DEAL_PIPELINE_NAME or "Sales Pipeline"
    )
    self.DEFAULT_TICKET_PIPELINE_NAME = (
        settings.HUBSPOT_DEFAULT_TICKET_PIPELINE_NAME or "Support Pipeline"
    )

    # Ensure these are numeric IDs from your HubSpot settings/environment
    self.DEAL_TO_CONTACT_ASSOCIATION_TYPE_ID = int(
        settings.HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_CONTACT
    )
    self.DEAL_TO_COMPANY_ASSOCIATION_TYPE_ID = int(
        settings.HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_COMPANY
    )
    self.COMPANY_TO_CONTACT_ASSOCIATION_TYPE_ID = int(
        settings.HUBSPOT_ASSOCIATION_TYPE_ID_COMPANY_TO_CONTACT
    )
    self.TICKET_TO_CONTACT_ASSOCIATION_TYPE_ID = int(
        settings.HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_CONTACT
    )
    self.TICKET_TO_DEAL_ASSOCIATION_TYPE_ID = int(
        settings.HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_DEAL
    )

  @staticmethod
  def _convert_date_to_timestamp_ms(date_str: Optional[str]) -> Optional[int]:
    """
    Convert YYYY-MM-DD date string to a HubSpot-compatible millisecond Unix timestamp,
    representing midnight UTC of that date.
    Returns None if the date_str is None, empty, or invalid.
    """
    if not date_str:
      return None
    try:
      # _is_valid_iso_date already checks if date_str is a string and valid "YYYY-MM-DD"
      if _is_valid_iso_date(date_str):
        # Parse the date string to a date object
        date_object = datetime.strptime(date_str, "%Y-%m-%d").date()
        # Create a datetime object for midnight UTC on that date
        dt_midnight_utc = datetime.combine(
            date_object, datetime.min.time(), tzinfo=timezone.utc)
        # Convert to millisecond timestamp
        timestamp_ms = int(dt_midnight_utc.timestamp() * 1000)
        logger.debug(
            f"Converted date string '{date_str}' to midnight UTC timestamp {timestamp_ms}")
        return timestamp_ms
      else:
        # This case should ideally not be hit if called after _is_valid_iso_date check,
        # but kept for robustness if called directly with an invalid format.
        logger.warning(
            f"Invalid date format passed to _convert_date_to_timestamp_ms: '{date_str}'. Expected YYYY-MM-DD.")
        return None
    except ValueError as e:  # Catch errors from strptime or timestamp conversion
      logger.warning(
          f"Error converting date string '{date_str}' to timestamp in _convert_date_to_timestamp_ms: {e}")
      return None

  async def search_objects(
      self,
      object_type: str,
      search_request: HubSpotSearchRequest,
  ) -> HubSpotSearchResponse:
    """
    Generic method to search HubSpot objects (contacts, companies, deals, tickets).
    """
    logger.debug(
        f"Searching {object_type} with request: {search_request.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      search_request_dict = search_request.model_dump(exclude_none=True)

      api_client_map = {
          "contacts": self.client.crm.contacts.search_api,
          "companies": self.client.crm.companies.search_api,
          "deals": self.client.crm.deals.search_api,
          "tickets": self.client.crm.tickets.search_api,  # Ensure tickets API is similar
      }

      if object_type not in api_client_map:
        logger.error(f"Unsupported object type for search: {object_type}")
        return HubSpotSearchResponse(total=0, results=[])

      api_response = await asyncio.to_thread(
          api_client_map[object_type].do_search,
          public_object_search_request=search_request_dict
      )

      results = [HubSpotObject(**obj.to_dict())
                 for obj in api_response.results]
      paging_dict = (
          api_response.paging.to_dict()
          if api_response.paging and hasattr(api_response.paging, "to_dict")
          else None
      )

      return HubSpotSearchResponse(
          total=api_response.total,
          results=results,
          paging=paging_dict,
      )
    except (ObjectApiException, DealApiException) as e:
      await _handle_api_error(e, f"{object_type} search")
      return HubSpotSearchResponse(total=0, results=[])
    except Exception as e:
      await _handle_api_error(e, f"{object_type} search")
      return HubSpotSearchResponse(total=0, results=[])

  async def search_leads(self, search_request: HubSpotSearchRequest) -> HubSpotSearchResponse:
    """
    Searches for leads based on provided search criteria using the v3 Objects API Search endpoint.

    Args:
                    search_request: A HubSpotSearchRequest object with filterGroups and other search parameters

    Returns:
                    HubSpotSearchResponse with search results
    """
    logger.debug(
        f"Searching leads with request: {search_request.model_dump_json(indent=2, exclude_none=True)}"
    )

    try:
      search_request_dict = search_request.model_dump(exclude_none=True)

      # Use the objects API for searching leads
      api_response = await asyncio.to_thread(
          self.client.crm.objects.search_api.do_search,
          object_type="leads",  # Specify leads as the object type
          public_object_search_request=search_request_dict
      )

      results = [HubSpotObject(**obj.to_dict())
                 for obj in api_response.results]  # type ignore
      paging_dict = (
          api_response.paging.to_dict()
          if api_response.paging and hasattr(api_response.paging, "to_dict")
          else None
      )

      return HubSpotSearchResponse(
          total=api_response.total,
          results=results,
          paging=paging_dict,
      )
    except ObjectApiException as e:
      await _handle_api_error(e, "leads search")
      return HubSpotSearchResponse(total=0, results=[])
    except Exception as e:
      await _handle_api_error(e, "leads search")
      return HubSpotSearchResponse(total=0, results=[])

  # --- Contact Methods ---
  async def create_contact(
      self, properties: HubSpotContactProperties
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Creating contact with raw properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      props_dict = properties.model_dump(exclude_none=True)

      # Convert date strings to timestamps
      props_dict['event_start_date'] = self._convert_date_to_timestamp_ms(
          props_dict.get('event_start_date'))
      props_dict['event_end_date'] = self._convert_date_to_timestamp_ms(
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
          self.client.crm.contacts.basic_api.create,
          simple_public_object_input_for_create=simple_public_object_input
      )
      logger.info(f"Successfully created contact ID: {api_response.id}")
      return HubSpotObject(**api_response.to_dict())
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

      await _handle_api_error(e, "contact creation")
      return None
    except Exception as e:
      logger.error(f"Unexpected error during contact creation: {str(e)}",
                   extra={'contact_properties': properties.model_dump(
                       exclude_none=True)},
                   exc_info=True)
      await _handle_api_error(e, "contact creation")
      return None

  async def get_contact(
      self, contact_id: str, properties_list: Optional[List[str]] = None
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Getting contact ID: {contact_id} with properties: {properties_list}"
    )
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
          self.client.crm.contacts.basic_api.get_by_id,
          contact_id=contact_id,
          properties=fetch_properties,
          archived=False,  # Explicitly fetch non-archived
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

  async def update_contact(
      self, contact_id: str, properties: HubSpotContactProperties
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Updating contact ID: {contact_id} with raw properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )

    props_dict_for_update = properties.model_dump(
        exclude_none=True, exclude_unset=True)

    if not props_dict_for_update:
      logger.warning(
          f"Update contact called for ID {contact_id} with no properties to update. Skipping API call."
      )
      return await self.get_contact(contact_id)  # Return current state

    try:
      # Normalize date fields to midnight UTC timestamps
      logger.debug(
          f"Original properties for contact update {contact_id}: {props_dict_for_update}")

      processed_props = {}
      for key, value in props_dict_for_update.items():
        if key in ['event_start_date', 'event_end_date']:  # Add other known date fields if any
          if value is None:
            logger.debug(
                f"Date field '{key}' is None. Skipping update for this field.")
            # If HubSpot requires sending an empty string to clear a date, add: processed_props[key] = ""
            continue

          final_midnight_utc_timestamp = None
          if isinstance(value, str):
            if _is_valid_iso_date(value):  # Handles "YYYY-MM-DD"
              final_midnight_utc_timestamp = self._convert_date_to_timestamp_ms(
                  value)  # This method should already ensure midnight UTC
            else:  # Attempt to parse as a stringified integer timestamp
              try:
                ms_timestamp = int(value)
                # Convert to datetime, normalize to midnight UTC, then back to timestamp
                dt_obj_utc = datetime.fromtimestamp(
                    ms_timestamp / 1000, tz=timezone.utc)
                dt_midnight_utc = dt_obj_utc.replace(
                    hour=0, minute=0, second=0, microsecond=0)
                final_midnight_utc_timestamp = int(
                    dt_midnight_utc.timestamp() * 1000)
              except ValueError:
                logger.warning(
                    f"Date string '{value}' for key '{key}' is not 'YYYY-MM-DD' and not a parsable integer timestamp. Field will not be sent.")
                continue  # Skip this field if format is unrecognized
          elif isinstance(value, int):  # Handles integer timestamps
            ms_timestamp = value
            # Convert to datetime, normalize to midnight UTC, then back to timestamp
            dt_obj_utc = datetime.fromtimestamp(
                ms_timestamp / 1000, tz=timezone.utc)
            dt_midnight_utc = dt_obj_utc.replace(
                hour=0, minute=0, second=0, microsecond=0)
            final_midnight_utc_timestamp = int(
                dt_midnight_utc.timestamp() * 1000)
          elif isinstance(value, datetime):  # Handles datetime objects
            dt_obj = value
            # Ensure datetime is UTC
            dt_obj_utc = dt_obj.astimezone(
                timezone.utc) if dt_obj.tzinfo else dt_obj.replace(tzinfo=timezone.utc)
            # Normalize to midnight UTC
            dt_midnight_utc = dt_obj_utc.replace(
                hour=0, minute=0, second=0, microsecond=0)
            final_midnight_utc_timestamp = int(
                dt_midnight_utc.timestamp() * 1000)
          else:
            if value is not None:  # Log only if value was not None initially
              logger.warning(
                  f"Unexpected type for date field '{key}': {type(value)}. Value: '{value}'. Field will not be sent.")
            continue  # Skip this field if type is unrecognized

          if final_midnight_utc_timestamp is not None:
            processed_props[key] = final_midnight_utc_timestamp
            logger.info(
                f"Normalized date field '{key}': original value '{value}', sent as timestamp {final_midnight_utc_timestamp}")
          elif value is not None:  # Original value was not None, but conversion failed
            logger.warning(
                f"Could not convert value '{value}' for date field '{key}' to a midnight UTC timestamp. Field will not be sent.")
        else:  # Not a date field
          processed_props[key] = value

      if not processed_props:
        logger.info(
            f"No properties to update for contact {contact_id} after processing.")
        return await self.get_contact(contact_id)

      logger.debug(
          f"Processed contact properties for HubSpot update: {processed_props}")

      simple_public_object_input = ContactSimplePublicObjectInput(
          properties=processed_props)
      logger.debug(
          f"Attempting to update contact {contact_id} with processed properties: {simple_public_object_input.properties}")

      api_response = await asyncio.to_thread(
          self.client.crm.contacts.basic_api.update,
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
    logger.debug(f"Archiving contact ID: {contact_id}")
    try:
      await asyncio.to_thread(self.client.crm.contacts.basic_api.archive, contact_id=contact_id)
      logger.info(f"Successfully archived contact ID: {contact_id}")
      return True
    except ObjectApiException as e:
      if e.status == 404:  # Not found, considered "deleted" or "already archived"
        logger.info(
            f"Contact with ID {contact_id} not found for archiving (already archived or never existed)."
        )
        return True  # Or False, depending on desired idempotency interpretation
      await _handle_api_error(e, "archive contact", contact_id)
      return False
    except Exception as e:
      await _handle_api_error(e, "archive contact", contact_id)
      return False

  async def create_or_update_contact(
      self, properties: HubSpotContactProperties
  ) -> HubSpotApiResult:
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
      # 1. Search for existing contact by email
      contact_email_str = str(properties.email)  # Ensure email is a string

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
          # hs_object_id is often the HubSpot ID
          properties=["hs_object_id", "email"],
          limit=1
      )
      existing_contacts_response = await self.search_objects(
          object_type="contacts", search_request=search_request
      )

      existing_contact_id = None
      if existing_contacts_response and existing_contacts_response.results:
        # Ensure results[0] exists and has an id attribute
        if existing_contacts_response.results[0] and hasattr(existing_contacts_response.results[0], 'id'):
          existing_contact_id = existing_contacts_response.results[0].id
          logger.info(
              f"Found existing contact ID: {existing_contact_id} for email: {contact_email_str}")

      if existing_contact_id:
        # 2. Update existing contact
        # Check if there are any actual properties to update
        props_to_update = properties.model_dump(
            exclude_none=True, exclude_unset=True)

        updated_contact = await self.update_contact(existing_contact_id, properties)
        if updated_contact and updated_contact.id:
          if not props_to_update:  # No new properties were provided for update
            message = f"Contact {existing_contact_id} found, no new properties provided for update."
            status = "success"  # Or "no_change" if that's more appropriate
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
          # update_contact returned None, indicating failure
          return HubSpotApiResult(
              status="error",
              entity_type="contact",
              hubspot_id=existing_contact_id,
              message=f"Failed to update contact {existing_contact_id}.",
          )
      else:
        # 3. Create new contact
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
          # create_contact returned None, indicating failure
          return HubSpotApiResult(
              status="error",
              entity_type="contact",
              message="Failed to create contact.",
          )
    except Exception as e:
      logger.error(
          f"Unexpected error in create_or_update_contact for email {properties.email if properties and properties.email else 'N/A'}: {e}", exc_info=True)
      # Use _handle_api_error for consistent error structure if it's an API exception
      # For other exceptions, provide a generic message
      error_details_dict = await _handle_api_error(e, "create_or_update_contact")
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          message=error_details_dict.get(
              "error", f"An unexpected error occurred: {str(e)}"),
          details=error_details_dict
      )

  async def get_contact_by_id(self, contact_id: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    """
    Retrieves a contact by its HubSpot ID.
    Returns a HubSpotApiResult.
    """
    logfire.info(f"Attempting to get contact by ID: {contact_id}")
    default_properties = [
        "email", "firstname", "lastname", "phone", "lifecyclestage",
        "hs_lead_status", "company", "website", "jobtitle", "hubspot_owner_id"
    ]
    fetch_properties = properties if properties is not None else default_properties

    try:
      contact_obj = await asyncio.to_thread(
          self.client.crm.contacts.basic_api.get_by_id,
          contact_id=contact_id,
          properties=fetch_properties,
          archived=False
      )
      if contact_obj and contact_obj.id:
        logfire.info(f"Successfully fetched contact ID: {contact_obj.id}")
        return HubSpotApiResult(
            status="success",
            entity_type="contact",
            hubspot_id=contact_obj.id,
            message="Contact fetched successfully.",
            details=contact_obj.to_dict()  # Convert HubSpot model to dict
        )
      else:  # Should not happen if get_by_id returns without error and has an ID
        logfire.warn(
            f"Contact ID {contact_id} fetched but object or ID is None/empty.")
        return HubSpotApiResult(
            status="error",
            entity_type="contact",
            hubspot_id=contact_id,
            message="Contact fetched but object or ID was missing."
        )

    except ObjectApiException as e:
      logfire_extras = {"contact_id": contact_id,
                        "status_code": e.status if hasattr(e, 'status') else None}
      if hasattr(e, 'body') and e.body:
        logfire_extras["error_body"] = e.body

      if e.status == 404:
        logfire.info(
            f"Contact with ID {contact_id} not found.", **logfire_extras)
        return HubSpotApiResult(
            status="not_found",
            entity_type="contact",
            hubspot_id=contact_id,
            message=f"Contact with ID {contact_id} not found."
        )
      else:
        logfire.error(
            f"HubSpot API error getting contact ID {contact_id}: {e}", exc_info=True, **logfire_extras)
        error_details_dict = await _handle_api_error(e, "get_contact_by_id", contact_id)
        return HubSpotApiResult(
            status="error",
            entity_type="contact",
            hubspot_id=contact_id,
            message=error_details_dict.get(
                "error", f"API error fetching contact: {str(e)}"),
            details=error_details_dict
        )
    except Exception as e:
      logfire.error(
          f"Unexpected error getting contact ID {contact_id}: {e}", exc_info=True, contact_id=contact_id)
      error_details_dict = await _handle_api_error(e, "get_contact_by_id", contact_id)
      return HubSpotApiResult(
          status="error",
          entity_type="contact",
          hubspot_id=contact_id,
          message=error_details_dict.get(
              "error", f"Unexpected error fetching contact: {str(e)}"),
          details=error_details_dict
      )

  # --- Company Methods ---
  async def create_company(
      self, properties: HubSpotCompanyProperties
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Creating company with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      simple_public_object_input = SimplePublicObjectInput(
          properties=properties.model_dump(exclude_none=True)
      )
      api_response = await asyncio.to_thread(
          self.client.crm.companies.basic_api.create,
          simple_public_object_input=simple_public_object_input
      )
      logger.info(f"Successfully created company ID: {api_response.id}")
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      await _handle_api_error(e, "company creation")
      return None
    except Exception as e:
      await _handle_api_error(e, "company creation")
      return None

  async def get_company(
      self, company_id: str, properties_list: Optional[List[str]] = None
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Getting company ID: {company_id} with properties: {properties_list}"
    )
    try:
      fetch_properties = properties_list or [
          "name",
          "domain",
          "phone",
          "website",
          "industry",
          "hs_object_id",
      ]
      api_response = await asyncio.to_thread(
          self.client.crm.companies.basic_api.get_by_id,
          company_id=company_id, properties=fetch_properties, archived=False
      )
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      if e.status == 404:
        logger.info(f"Company with ID {company_id} not found.")
      else:
        await _handle_api_error(e, "get company", company_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "get company", company_id)
      return None

  async def update_company(
      self, company_id: str, properties: HubSpotCompanyProperties
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Updating company ID: {company_id} with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    if not properties.model_dump(exclude_none=True, exclude_unset=True):
      logger.warning(
          f"Update company called for ID {company_id} with no properties to update. Skipping API call."
      )
      return await self.get_company(company_id)

    try:
      simple_public_object_input = SimplePublicObjectInput(
          properties=properties.model_dump(
              exclude_none=True, exclude_unset=True)
      )
      api_response = await asyncio.to_thread(
          self.client.crm.companies.basic_api.update,
          company_id=company_id,
          simple_public_object_input=simple_public_object_input,
      )
      logger.info(f"Successfully updated company ID: {company_id}")
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      await _handle_api_error(e, "update company", company_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "update company", company_id)
      return None

  async def delete_company(self, company_id: str) -> bool:
    logger.debug(f"Archiving company ID: {company_id}")
    try:
      await asyncio.to_thread(self.client.crm.companies.basic_api.archive, company_id=company_id)
      logger.info(f"Successfully archived company ID: {company_id}")
      return True
    except ObjectApiException as e:
      if e.status == 404:
        logger.info(f"Company with ID {company_id} not found for archiving.")
        return True
      await _handle_api_error(e, "archive company", company_id)
      return False
    except Exception as e:
      await _handle_api_error(e, "archive company", company_id)
      return False

  async def create_or_update_contact_and_lead(
      self,
      contact_properties: HubSpotContactProperties,
      lead_properties: HubSpotLeadProperties,
      company_properties: Optional[HubSpotCompanyProperties] = None,
      lead_owner_email: Optional[str] = None
  ) -> HubSpotApiResult:
    """
    Creates or updates a contact, then creates a new lead object and associates them.
    Optionally creates/updates and associates a company.

    This method uses the v3 Objects API for creating Leads (not deals) and the
    v4 Associations API for creating relationships between objects, providing more 
    flexibility and control over the associations.
    """
    logfire.info(
        f"Starting create/update process. Contact email: {contact_properties.email}",
        contact_props_input=contact_properties.model_dump(exclude_none=True),
        lead_props_input=lead_properties.model_dump(exclude_none=True),
        company_props_input=company_properties.model_dump(
            exclude_none=True) if company_properties else None
    )

    contact_result = await self.create_or_update_contact(contact_properties)

    if contact_result.status not in ["created", "updated", "success"] or not contact_result.hubspot_id:
      logfire.error(
          f"Failed to create or update contact: {contact_result.message}", details=contact_result.details)
      return HubSpotApiResult(
          status="error",
          entity_type="process_contact_failed",
          message=f"Contact operation failed: {contact_result.message}",
          details={"contact_result": contact_result.model_dump(
              exclude_none=True)}
      )

    contact_id = contact_result.hubspot_id
    logfire.info(
        f"Contact operation successful (ID: {contact_id}). Proceeding with company/deal operations.")

    company_id: Optional[str] = None
    company_processed_successfully = True  # Assume success unless an error occurs

    if company_properties and company_properties.name:
      logfire.info(f"Processing company: {company_properties.name}")
      existing_company_id: Optional[str] = None
      # Try to find company by domain first
      if company_properties.domain:
        search_domain_req = HubSpotSearchRequest(
            filterGroups=[HubSpotSearchFilterGroup(filters=[
                HubSpotSearchFilter(propertyName="domain", operator="EQ", value=str(company_properties.domain))])],
            # Added name to properties
            properties=["hs_object_id", "name"], limit=1)
        domain_search_res = await self.search_objects("companies", search_domain_req)
        if domain_search_res.results and domain_search_res.results[0].id:
          existing_company_id = domain_search_res.results[0].id
          logfire.info(
              f"Found existing company by domain '{company_properties.domain}': ID {existing_company_id}, Name: {domain_search_res.results[0].properties.get('name')}")

      # If not found by domain, or no domain provided, try by name
      if not existing_company_id and company_properties.name:
        search_name_req = HubSpotSearchRequest(
            filterGroups=[HubSpotSearchFilterGroup(filters=[
                HubSpotSearchFilter(propertyName="name", operator="EQ", value=str(company_properties.name))])],
            properties=["hs_object_id", "domain"], limit=1)  # Added domain
        name_search_res = await self.search_objects("companies", search_name_req)
        if name_search_res.results and name_search_res.results[0].id:
          existing_company_id = name_search_res.results[0].id
          logfire.info(
              f"Found existing company by name '{company_properties.name}': ID {existing_company_id}, Domain: {name_search_res.results[0].properties.get('domain')}")

      if existing_company_id:
        company_id = existing_company_id
        logfire.info(f"Updating existing company ID: {company_id}")
        updated_company = await self.update_company(company_id, company_properties)
        if not (updated_company and updated_company.id):
          logfire.warn(
              f"Failed to update company ID {company_id}. Proceeding with existing ID, but marking as partial success.")
          # Mark company processing as not fully successful
          company_processed_successfully = False
      else:
        logfire.info(f"Creating new company: {company_properties.name}")
        created_company = await self.create_company(company_properties)
        if created_company and created_company.id:
          company_id = created_company.id
          logfire.info(
              f"Company '{company_properties.name}' created with ID {company_id}.")
        else:
          logfire.error(
              f"Failed to create company '{company_properties.name}'.")
          company_processed_successfully = False  # Mark company processing as failed

      if company_id and contact_id:  # Ensure both exist before associating
        logfire.info(
            f"Associating contact {contact_id} to company {company_id}.")
        assoc_contact_company = await self.associate_objects(
            from_object_type="contacts", from_object_id=contact_id,
            to_object_type="companies", to_object_id=company_id,
            association_type_id=self.COMPANY_TO_CONTACT_ASSOCIATION_TYPE_ID,
            association_category="HUBSPOT_DEFINED"
        )
        if not assoc_contact_company:
          logfire.warn(
              f"Failed to associate contact {contact_id} to company {company_id}.")
          # Decide if this failure should halt the process or just be noted.
          # For now, we'll note it and continue with deal creation.
          company_processed_successfully = False

    # Prepare Lead Properties using the v3 Objects API for Leads
    # Assign owner if provided
    lead_name_parts = [
        lead_properties.contact_firstname,
        lead_properties.contact_lastname,
        lead_properties.project_category or "New Lead",
    ]
    lead_name = " - ".join(filter(None, lead_name_parts)) or "New Lead"

    # Create properties dictionary for the lead
    lead_props_dict = lead_properties.model_dump(exclude_none=True)
    lead_props_dict["hs_lead_name"] = lead_name

    if lead_owner_email:
      owner = await self.get_owner_by_email(lead_owner_email)
      if owner and owner.id:
        lead_props_dict["hubspot_owner_id"] = owner.id
        logfire.info(
            f"Assigning lead owner: {lead_owner_email} (ID: {owner.id})")
      else:
        logfire.warn(
            f"Could not find HubSpot owner with email: {lead_owner_email}. Lead will be unassigned or default assigned.")

    # Create lead using objects API
    try:
      from hubspot.crm.objects.models import SimplePublicObjectInputForCreate

      # Process any date fields that need conversion to timestamps
      for key, value in lead_props_dict.items():
        if key in ['rental_start_date', 'rental_end_date', 'event_start_date', 'event_end_date']:
          if value and isinstance(value, str) and _is_valid_iso_date(value):
            lead_props_dict[key] = self._convert_date_to_timestamp_ms(value)

      simple_lead_input = SimplePublicObjectInputForCreate(
          properties=lead_props_dict
      )

      logfire.info(
          f"Creating lead with properties: {json.dumps(lead_props_dict, default=str)}")

      lead_response = await asyncio.to_thread(
          self.client.crm.objects.basic_api.create,
          object_type="leads",
          simple_public_object_input_for_create=simple_lead_input
      )

      if not (lead_response and lead_response.id):
        logfire.error(f"Failed to create lead for contact {contact_id}.")
        return HubSpotApiResult(
            status="error",
            entity_type="process_lead_failed",
            message="Lead creation failed after contact operation.",
            details={
                "contact_result": contact_result.model_dump(exclude_none=True),
                "company_id": company_id,
                "lead_creation_props": lead_props_dict
            }
        )

      lead_id = lead_response.id
      logfire.info(
          f"Lead ID {lead_id} created successfully for contact {contact_id}.")

    except Exception as e:
      logfire.error(f"Error creating lead: {str(e)}", exc_info=True)
      return HubSpotApiResult(
          status="error",
          entity_type="process_lead_failed",
          message=f"Lead creation failed: {str(e)}",
          details={
              "contact_result": contact_result.model_dump(exclude_none=True),
              "company_id": company_id,
              "error": str(e)
          }
      )

    # Associations for the Lead using the v3 Associations API
    lead_associations_summary = {
        "contact_to_lead": False, "company_to_lead": False}

    # Define association type IDs for leads
    # Using standard v3 association type IDs (numeric IDs)
    # Standard association types in HubSpot v3 API
    # Standard Lead to Contact association type ID
    LEAD_TO_CONTACT_ASSOCIATION_TYPE_ID = 280
    # Standard Lead to Company association type ID
    LEAD_TO_COMPANY_ASSOCIATION_TYPE_ID = 281

    assoc_lead_contact = await self.associate_objects(
        from_object_type="leads", from_object_id=lead_id,
        to_object_type="contacts", to_object_id=contact_id,
        association_type_id=LEAD_TO_CONTACT_ASSOCIATION_TYPE_ID,
        association_category="HUBSPOT_DEFINED"
    )
    lead_associations_summary["contact_to_lead"] = assoc_lead_contact
    if not assoc_lead_contact:
      logfire.warn(
          f"Failed to associate lead {lead_id} with contact {contact_id}.")

    if company_id:  # Only associate lead to company if company was processed
      assoc_lead_company = await self.associate_objects(
          from_object_type="leads", from_object_id=lead_id,
          to_object_type="companies", to_object_id=company_id,
          association_type_id=LEAD_TO_COMPANY_ASSOCIATION_TYPE_ID,
          association_category="HUBSPOT_DEFINED"
      )
      lead_associations_summary["company_to_lead"] = assoc_lead_company
      if not assoc_lead_company:
        logfire.warn(
            f"Failed to associate lead {lead_id} with company {company_id}.")

    final_status = "success"
    if not company_processed_successfully or not assoc_lead_contact or (company_id and not lead_associations_summary["company_to_lead"]):
      final_status = "success_with_errors"

    return HubSpotApiResult(
        status=final_status,
        entity_type="process_contact_and_lead",
        message="Contact and Lead processed.",
        hubspot_id=lead_id,  # Primary ID for this operation is the lead
        details={
            "contact_id": contact_id,
            "contact_status": contact_result.status,
            "company_id": company_id,
            "company_processed_successfully": company_processed_successfully,
            "lead_id": lead_id,
            "associations_summary": lead_associations_summary
        }
    )

  # Added default limit
  async def get_owners(self, limit: int = 100) -> List[HubSpotOwner]:
    # Caching strategy: cache the full list if fetched.
    # If called frequently with different limits, this might not be optimal.
    # For now, assumes one primary call to get all owners.
    full_list_cache_key = "all_owners_complete_list"
    if full_list_cache_key in self.owners_cache:
      logger.debug("Returning full cached list of owners")
      return self.owners_cache[full_list_cache_key]

    logger.debug(f"Fetching all owners (paginating with limit: {limit})")
    all_owners_list = []
    current_after = None

    try:
      while True:
        api_response = await asyncio.to_thread(
            self.client.crm.owners.owners_api.get_page,
            limit=limit, after=current_after
        )
        owners_page = [
            HubSpotOwner(**owner.to_dict()) for owner in api_response.results
        ]
        all_owners_list.extend(owners_page)

        if (
            api_response.paging
            and api_response.paging.next
            and api_response.paging.next.after
        ):
          current_after = api_response.paging.next.after
          logger.debug(
              f"Fetching next page of owners, after: {current_after}"
          )
        else:
          break

      self.owners_cache[full_list_cache_key] = all_owners_list
      logger.info(f"Fetched and cached {len(all_owners_list)} owners.")
      return all_owners_list
    except ObjectApiException as e:
      await _handle_api_error(e, "owners retrieval")
      return []
    except Exception as e:
      await _handle_api_error(e, "owners retrieval")
      return []

  async def get_owner_by_email(self, email: str) -> Optional[HubSpotOwner]:
    logger.debug(f"Getting owner by email: {email}")
    cache_key = f"owner_email_{email.lower()}"  # Normalize email for cache key
    cached_owner = self.owners_cache.get(cache_key)
    if cached_owner:
      logger.debug(f"Returning cached owner for email: {email}")
      return cached_owner

    try:
      api_response = await asyncio.to_thread(
          self.client.crm.owners.owners_api.get_page,
          email=email, limit=1
      )
      if api_response.results:
        owner_data = HubSpotOwner(**api_response.results[0].to_dict())
        self.owners_cache[cache_key] = owner_data
        logger.info(
            f"Found owner by email via API: {email} -> ID {owner_data.id}"
        )
        return owner_data
      else:
        logger.warning(
            f"Owner with email '{email}' not found via direct API query. Consider checking all owners if necessary."
        )
        # Optional: Fallback to searching in all owners (can be slow)
        # all_owners = await self.get_owners()
        # for owner in all_owners:
        #     if owner.email and owner.email.lower() == email.lower():
        #         self.owners_cache[cache_key] = owner
        #         logger.info(f"Found owner by email '{email}' after searching all owners.")
        #         return owner
        # logger.warning(f"Owner with email '{email}' not found even after checking all owners.")
        return None
    except ObjectApiException as e:
      await _handle_api_error(e, "get owner by email", email)
    except Exception as e:
      await _handle_api_error(e, "get owner by email", email)

    return None

  # --- Association Methods (Using API v4) ---
  async def associate_objects(
      self,
      # e.g., "deals", "contacts", "leads" (plural input)
      from_object_type: str,
      from_object_id: str,
      # e.g., "contacts", "companies" (plural input)
      to_object_type: str,
      to_object_id: str,
      association_type_id: int,  # Numeric association type ID
      association_category: str = "HUBSPOT_DEFINED"  # Used in v4 API
  ) -> bool:
    """
    Associates two HubSpot objects using the v4 Associations API.

    This implementation uses the v4 Associations API which provides more flexibility
    and control over the association creation.

    Args:
                    from_object_type: The source object type (e.g., "leads", "contacts", "companies")
                    from_object_id: The ID of the source object
                    to_object_type: The target object type (e.g., "contacts", "companies")
                    to_object_id: The ID of the target object
                    association_type_id: The numeric ID of the association type
                    association_category: Either "HUBSPOT_DEFINED" or "USER_DEFINED"

    Returns:
                    Boolean indicating success or failure
    """
    context = f"associating {from_object_type} {from_object_id} to {to_object_type} {to_object_id} (type {association_type_id})"
    logger.debug(f"Attempting to {context}")

    # Convert plural input object types to singular lowercase for v4 API calls
    sdk_from_object_type = from_object_type.lower()
    if sdk_from_object_type == "contacts":
      sdk_from_object_type = "contact"
    elif sdk_from_object_type == "companies":
      sdk_from_object_type = "company"
    elif sdk_from_object_type == "deals":
      sdk_from_object_type = "deal"
    elif sdk_from_object_type == "tickets":
      sdk_from_object_type = "ticket"
    elif sdk_from_object_type.endswith('s'):
      sdk_from_object_type = sdk_from_object_type[:-1]

    sdk_to_object_type = to_object_type.lower()
    if sdk_to_object_type == "contacts":
      sdk_to_object_type = "contact"
    elif sdk_to_object_type == "companies":
      sdk_to_object_type = "company"
    elif sdk_to_object_type == "deals":
      sdk_to_object_type = "deal"
    elif sdk_to_object_type == "tickets":
      sdk_to_object_type = "ticket"
    elif sdk_to_object_type.endswith('s'):
      sdk_to_object_type = sdk_to_object_type[:-1]

    try:
      # Prepare the request payload following v4 Associations API format
      association_payload = [
          {
              "associationCategory": association_category,
              "associationTypeId": int(association_type_id)
          }
      ]

      # Create from/to object IDs
      from_object = PublicObjectId(id=from_object_id)
      to_object = PublicObjectId(id=to_object_id)

      # Create the association post object
      association = PublicAssociationMultiPost(
          _from=from_object,
          to=to_object,
          types=association_payload
      )

      # Create batch input for the association
      batch_input = BatchInputPublicAssociationMultiPost(inputs=[association])

      # Call the API
      await asyncio.to_thread(
          self.client.crm.associations.v4.batch_api.create,
          from_object_type=sdk_from_object_type,
          to_object_type=sdk_to_object_type,
          batch_input_public_association_multi_post=batch_input
      )

      logger.info(f"Successfully {context}")
      return True
    except Exception as e:
      logger.error(f"Error {context}: {e}", exc_info=True)
      return False

  async def batch_associate_objects(
      self,
      from_object_type: str,
      from_object_id: str,
      to_object_type: str,
      to_object_ids: list[str],
      association_type_id: int,
      association_category: str = "HUBSPOT_DEFINED"
  ) -> bool:
    """
    Associates one object with multiple objects in batch using v4 Associations API.

    This implementation uses the v4 Associations API which provides more flexibility
    and control over the association creation.

    Args:
                    from_object_type: The source object type (e.g., "leads", "contacts", "companies")
                    from_object_id: The ID of the source object
                    to_object_type: The target object type (e.g., "contacts", "companies")
                    to_object_ids: List of IDs of the target objects
                    association_type_id: The numeric ID of the association type
                    association_category: Either "HUBSPOT_DEFINED" or "USER_DEFINED"

    Returns:
                    Boolean indicating success or failure
    """
    context = f"batch associating {from_object_type} {from_object_id} to {len(to_object_ids)} {to_object_type} (type {association_type_id})"
    logger.debug(f"Attempting to {context}")

    if not to_object_ids:
      logger.warning(
          f"No target objects to associate with {from_object_type} {from_object_id}")
      return True

    # Convert plural input object types to singular lowercase for v4 API calls
    sdk_from_object_type = from_object_type.lower()
    if sdk_from_object_type == "contacts":
      sdk_from_object_type = "contact"
    elif sdk_from_object_type == "companies":
      sdk_from_object_type = "company"
    elif sdk_from_object_type == "deals":
      sdk_from_object_type = "deal"
    elif sdk_from_object_type == "tickets":
      sdk_from_object_type = "ticket"
    elif sdk_from_object_type.endswith('s'):
      sdk_from_object_type = sdk_from_object_type[:-1]

    sdk_to_object_type = to_object_type.lower()
    if sdk_to_object_type == "contacts":
      sdk_to_object_type = "contact"
    elif sdk_to_object_type == "companies":
      sdk_to_object_type = "company"
    elif sdk_to_object_type == "deals":
      sdk_to_object_type = "deal"
    elif sdk_to_object_type == "tickets":
      sdk_to_object_type = "ticket"
    elif sdk_to_object_type.endswith('s'):
      sdk_to_object_type = sdk_to_object_type[:-1]

    try:
      # Prepare the association type for all associations
      association_payload = [
          {
              "associationCategory": association_category,
              "associationTypeId": int(association_type_id)
          }
      ]

      # Create association inputs for each target object
      associations = []
      for to_id in to_object_ids:
        from_object = PublicObjectId(id=from_object_id)
        to_object = PublicObjectId(id=to_id)

        associations.append(
            PublicAssociationMultiPost(
                _from=from_object,
                to=to_object,
                types=association_payload
            )
        )

      # Create batch input for associations
      batch_input = BatchInputPublicAssociationMultiPost(inputs=associations)

      # Call the API
      await asyncio.to_thread(
          self.client.crm.associations.v4.batch_api.create,
          from_object_type=sdk_from_object_type,
          to_object_type=sdk_to_object_type,
          batch_input_public_association_multi_post=batch_input
      )

      logger.info(f"Successfully {context}")
      return True
    except Exception as e:
      logger.error(f"Error {context}: {e}", exc_info=True)
      return False

  # --- Lead Methods (Using v3 Objects API) ---
  async def create_lead(
      self, lead_data: HubSpotLeadProperties
  ) -> HubSpotApiResult:
    """
    Creates a Lead in HubSpot using the v3 Objects API.
    Unlike the previous implementation that created a deal, this directly uses
    the Leads object type as per HubSpot documentation.

    Args:
                    lead_data: Properties for the lead

    Returns:
                    HubSpotApiResult with status and details
    """
    logger.info(
        f"Attempting to create lead with data: {lead_data.model_dump_json(indent=2, exclude_none=True)}"
    )

    response = {
        "success": False,
        "message": "Lead processing initiated.",
        "contact_id": None,
        "company_id": None,
        "lead_id": None,  # Changed from deal_id to lead_id
        "errors": [],
        "association_results": {"total": 0, "succeeded": 0, "failed_details": []},
    }

    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    lead_id: Optional[str] = None  # Changed from deal_id to lead_id

    try:
      # 1. Create Contact (or find existing - simplified to create for now)
      # More robust: search by email first. If exists, use ID, maybe update.
      # search_req_contact = HubSpotSearchRequest(filters=[{"propertyName": "email", "operator": "EQ", "value": lead_data.email}], limit=1, properties=["hs_object_id", "email"])
      # existing_contacts = await self.search_objects("contacts", search_req_contact)
      # if existing_contacts.results:
      #     contact_id = existing_contacts.results[0].id
      #     response["contact_id"] = contact_id
      #     logger.info(f"Found existing contact ID: {contact_id} for email: {lead_data.email}")
      #     # Optionally, update the existing contact here
      #     # contact_update_props = HubSpotContactPropertiesUpdate(phone=lead_data.phone, ...)
      #     # await self.update_contact(contact_id, contact_update_props)
      # else:
      # Create new contact
      contact_create_props = (
          HubSpotContactProperties(  # Changed from HubSpotContactPropertiesCreate
              firstname=lead_data.contact_firstname,
              lastname=lead_data.contact_lastname,
              email=lead_data.email,
              phone=lead_data.phone,
              lifecyclestage=settings.HUBSPOT_DEFAULT_LEAD_LIFECYCLE_STAGE
              or "lead",

              # Explicitly passing other Optional fields to satisfy Pylance
              # Mapping from lead_data.lead_properties where a reasonable counterpart exists
              # Assuming city might exist on lead_properties
              city=getattr(
                  lead_data.lead_properties, 'city', None),
              # Assuming zip might exist on lead_properties
              zip=getattr(
                  lead_data.lead_properties, 'zip', None),
              # Assuming address might exist on lead_properties
              address=getattr(
                  lead_data.lead_properties, 'address', None),
              # Assuming state might exist on lead_properties
              state=getattr(
                  lead_data.lead_properties, 'state', None),

              message=(", ".join(lead_data.lead_properties.additional_services_needed)
                       if lead_data.lead_properties and
                       lead_data.lead_properties.additional_services_needed and
                       isinstance(
                  lead_data.lead_properties.additional_services_needed, list)
                  else getattr(lead_data.lead_properties, 'additional_services_needed', None)),

              # No direct counterpart in HubSpotLeadProperties for list of ServiceType
              what_service_do_you_need_=None,

              # Individual stall counts are not directly in HubSpotLeadProperties (it has number_of_stalls for total)
              how_many_restroom_stalls_=None,
              how_many_shower_stalls_=None,
              how_many_laundry_units_=None,
              how_many_portable_toilet_stalls_=None,

              # Using ai_qualification_notes as a potential source
              your_message=getattr(lead_data.lead_properties,
                                   'ai_qualification_notes', None),

              # These specific questions are not directly in HubSpotLeadProperties
              do_you_have_water_access_onsite_=None,
              do_you_have_power_access_onsite_=None,

              ada=lead_data.lead_properties.ada_required if lead_data.lead_properties else None,

              # HubSpotLeadProperties has rental_start_date etc., but not a single event_or_job_address string
              event_or_job_address=None,

              event_start_date=lead_data.lead_properties.rental_start_date if lead_data.lead_properties else None,
              event_end_date=lead_data.lead_properties.rental_end_date if lead_data.lead_properties else None,

              # Not in HubSpotLeadProperties
              by_submitting_this_form_you_consent_to_receive_texts=None,

              # AI properties for Contact, mapping from lead_properties where sensible
              # Re-using for summary
              ai_call_summary=getattr(
                  lead_data.lead_properties, 'ai_qualification_notes', None),
              # HubSpotLeadProperties has ai_lead_type, not sentiment directly for contact
              ai_call_sentiment=None,
              call_recording_url=None,  # Not in HubSpotLeadProperties
              # Re-using for summary
              call_summary=getattr(lead_data.lead_properties,
                                   'ai_qualification_notes', None)
          )
      )
      contact = await self.create_contact(contact_create_props)
      if contact and contact.id:
        contact_id = contact.id
        response["contact_id"] = contact_id
        logger.info(f"Successfully created contact ID: {contact_id}")
      else:
        logger.error(f"Failed to create contact for email: {lead_data.email}")
        response["errors"].append(
            {"step": "contact_creation", "message": "Failed to create contact."}
        )

      # 2. Create Company (or find existing - simplified to create for now)
      if lead_data.company_name:
        # More robust: search by domain first.
        # Search_req_company = HubSpotSearchRequest(filters=[{"propertyName": "domain", "operator": "EQ", "value": lead_data.company_domain}], limit=1, properties=["hs_object_id", "name"])
        # existing_companies = await self.search_objects("companies", search_req_company)
        # if existing_companies.results:
        #    company_id = existing_companies.results[0].id
        #    response["company_id"] = company_id
        #    logger.info(f"Found existing company ID: {company_id} for domain: {lead_data.company_domain}")
        # else:
        company_create_props = HubSpotCompanyProperties(  # Changed from HubSpotCompanyPropertiesCreate
            name=lead_data.company_name,
            domain=lead_data.company_domain,  # Assuming domain might be available or derived
        )
        company = await self.create_company(company_create_props)
        if company and company.id:
          company_id = company.id
          response["company_id"] = company_id
          logger.info(
              f"Successfully created company ID: {company_id} for '{lead_data.company_name}'"
          )
        else:
          logger.warning(
              f"Failed to create company: {lead_data.company_name}"
          )
          response["errors"].append(
              {
                  "step": "company_creation",
                  "message": f"Failed to create company '{lead_data.company_name}'.",
              }
          )

      # 3. Create Lead (only if a contact or company was successfully created/found)
      if (
          contact_id or company_id
      ):  # Proceed if we have something to associate the lead with
        lead_name_parts = [
            lead_data.contact_firstname,
            lead_data.contact_lastname,
            lead_data.project_category or "New Lead",
        ]
        lead_name = " - ".join(filter(None, lead_name_parts)) or "New Lead"

        # Convert lead data to properties dictionary for the Create Lead API
        lead_properties = {
            "hs_lead_name": lead_name,
            "hs_lead_status": lead_data.status or settings.HUBSPOT_DEFAULT_LEAD_STATUS or "NEW",
        }

        # Add any custom lead properties from the input
        if hasattr(lead_data, 'lead_properties') and lead_data.lead_properties:
          for key, value in lead_data.lead_properties.model_dump(exclude_none=True).items():
            # Skip complex values that aren't directly usable as properties
            if not isinstance(value, (str, int, float, bool, type(None))):
              continue
            lead_properties[key] = value

        # Add estimated value if available
        if lead_data.estimated_value is not None:
          lead_properties["hs_lead_value"] = lead_data.estimated_value

        # Handle owner assignment
        if lead_data.owner_email:
          owner = await self.get_owner_by_email(lead_data.owner_email)
          if owner and owner.id:
            lead_properties["hubspot_owner_id"] = owner.id
            logger.info(
                f"Assigning owner ID {owner.id} ({owner.email}) to the new lead."
            )
          else:
            logger.warning(
                f"Owner with email {lead_data.owner_email} not found. Lead will be unassigned or default assigned."
            )
            response["errors"].append(
                {
                    "step": "owner_assignment",
                    "message": f"Owner '{lead_data.owner_email}' not found.",
                }
            )

        # Create lead using the Objects API v3 for Leads
        try:
          # Prepare the SimplePublicObjectInput for lead creation
          from hubspot.crm.objects.models import SimplePublicObjectInput

          simple_public_object_input = SimplePublicObjectInput(
              properties=lead_properties
          )

          # Create the lead object - Note: The objectType "leads" is used with the v3 API
          lead_response = await asyncio.to_thread(
              self.client.crm.objects.basic_api.create,
              object_type="leads",  # Using string name for readability as recommended
              simple_public_object_input_for_create=simple_public_object_input
          )

          if lead_response and lead_response.id:
            lead_id = lead_response.id
            response["lead_id"] = lead_id
            logger.info(
                f"Successfully created lead ID: {lead_id} with name '{lead_name}'"
            )
          else:
            logger.error(f"Failed to create lead for '{lead_name}'.")
            response["errors"].append(
                {
                    "step": "lead_creation",
                    "message": f"Failed to create lead '{lead_name}'.",
                }
            )
        except Exception as e:
          logger.error(f"Error creating lead: {e}", exc_info=True)
          response["errors"].append(
              {
                  "step": "lead_creation",
                  "message": f"Failed to create lead: {str(e)}",
              }
          )
      else:
        logger.warning(
            "Skipping deal creation as no contact or company was created/found."
        )
        response["message"] = (
            "Contact and/or company creation failed; deal creation skipped."
        )

      # 4. Create Associations using the v4 Associations API
      associations_to_attempt: List[Dict[str, Any]] = []
      # Define association type IDs for leads
      # You should replace these constants with your actual lead association type IDs
      # Replace with your actual ID from HubSpot settings
      LEAD_TO_CONTACT_ASSOCIATION_TYPE_ID = 15
      # Replace with your actual ID from HubSpot settings
      LEAD_TO_COMPANY_ASSOCIATION_TYPE_ID = 16

      if lead_id:
        if contact_id:
          associations_to_attempt.append(
              {
                  "from_object_type": "leads",
                  "from_object_id": lead_id,
                  "to_object_type": "contacts",
                  "to_object_id": contact_id,
                  "association_type_id": LEAD_TO_CONTACT_ASSOCIATION_TYPE_ID,
              }
          )
        if company_id:
          associations_to_attempt.append(
              {
                  "from_object_type": "leads",
                  "from_object_id": lead_id,
                  "to_object_type": "companies",
                  "to_object_id": company_id,
                  "association_type_id": LEAD_TO_COMPANY_ASSOCIATION_TYPE_ID,
              }
          )
      if company_id and contact_id:  # Also associate company to contact
        associations_to_attempt.append(
            {
                "from_object_type": "companies",
                "from_object_id": company_id,
                "to_object_type": "contacts",
                "to_object_id": contact_id,
                "association_type_id": self.COMPANY_TO_CONTACT_ASSOCIATION_TYPE_ID,
            }
        )

      response["association_results"]["total"] = len(associations_to_attempt)
      if associations_to_attempt:
        # Using individual associate_objects calls for clarity here,
        # but batch_associate_objects could be used if all associations are of the same from/to types.
        # Since they are mixed, individual calls or a more complex batch grouping is needed.
        # The current batch_associate_objects handles grouping, so it can be used.

        batch_success = await self.batch_associate_objects(
            associations_to_attempt
        )
        if batch_success:
          response["association_results"]["succeeded"] = len(
              associations_to_attempt
          )
          logger.info(
              f"Successfully created {len(associations_to_attempt)} associations for lead."
          )
        else:
          # Batch method logs errors internally. Here we just note overall failure.
          # For more granular success/failure, iterate and call associate_objects individually.
          logger.warning(
              "One or more associations failed during batch processing for lead. Check previous logs."
          )
          response["errors"].append(
              {
                  "step": "associations",
                  "message": "One or more associations failed during batch processing.",
              }
          )
          # To get exact counts if batch_associate_objects doesn't return it:
          # You'd need to modify batch_associate_objects or do individual calls here and count.
          # For now, assuming batch_success means all or nothing for this simplified response.
          # A more robust batch_associate_objects could return a count of successes.
          response["association_results"][
              "succeeded"
          ] = 0  # Or get a more precise count

      if not response["errors"] and (contact_id or company_id or lead_id):
        response["success"] = True
        response["message"] = "Lead processed successfully."
        if not lead_id and (contact_id or company_id):
          response["message"] = (
              "Contact/Company processed; lead creation failed or was skipped."
          )
      elif not response["errors"] and not any([contact_id, company_id, lead_id]):
        response["success"] = True
        response["message"] = (
            "Lead data processed, but no new HubSpot entities were created..."
        )
      else:  # Errors occurred or success was not explicitly set to True
        response["success"] = False  # Ensure success is false if errors exist
        # if message wasn't set by error path
        if not response.get("message") or response.get("success"):
          final_error_messages = [err.get("message", "Unknown error")
                                  for err in response.get("errors", [])]
          response["message"] = f"Lead processing encountered errors: {'; '.join(final_error_messages)}" if final_error_messages else "Lead processing failed."

      # At the end of the try block, before returning:
      logger.info(
          f"Lead creation process completed. Original response dict: {response}")

      current_status_literal: Literal["success", "error", "no_change"]
      if response.get("errors"):
        current_status_literal = "error"
        # if success was true but errors exist, it's an error
        if response.get("success") is True:
          response["success"] = False
      elif response.get("success"):  # success is a boolean
        current_status_literal = "success"  # Simplification for now
      else:
        # Default to error if not explicitly success and no errors (should have message)
        current_status_literal = "error"
        if not response.get("message"):
          response["message"] = "Lead processing failed with an undetermined status."

      primary_hubspot_id = response.get("lead_id") or response.get(
          "contact_id") or response.get("company_id")

      return HubSpotApiResult(
          status=current_status_literal,
          entity_type="lead",
          hubspot_id=primary_hubspot_id,
          message=response.get("message"),
          details={
              "contact_id": response.get("contact_id"),
              "company_id": response.get("company_id"),
              # Changed from deal_id to lead_id
              "lead_id": response.get("lead_id"),
              "errors": response.get("errors", []),
              "association_results": response.get("association_results"),
          }
      )

    except ValidationError as ve:
      logger.error(
          f"Input validation error for lead creation: {ve.errors()}",
          exc_info=True,
      )
      # Ensure response dict is populated for error case
      response["success"] = False
      response["message"] = "Input data validation failed."
      response["errors"].append(
          {"step": "input_validation", "details": ve.errors()})

      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message="Input data validation failed",
          details={"validation_errors": ve.errors()}
      )
    except (ObjectApiException) as e:  # Removed DealApiException as we're using leads now
      error_info = await _handle_api_error(e, "lead creation main process")
      response["errors"].append(
          {"step": "hubspot_api_main", "details": error_info})
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message=error_info.get(
              "error", "A HubSpot API error occurred during lead creation.")
      )
    except Exception as e:
      logger.error(
          f"Unexpected error during lead creation: {e}", exc_info=True)
      response["success"] = False
      response["message"] = "An unexpected error occurred during lead processing."
      response["errors"].append({"step": "unexpected_main", "details": str(e)})
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message=response["message"],
          details={"errors": response["errors"]}
      )

  async def get_lead_by_id(self, lead_id: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    """
    Retrieves a lead by its HubSpot ID using the v3 Objects API.

    Args:
                    lead_id: The ID of the lead to retrieve
                    properties: Optional list of properties to fetch. If None, default properties will be used.

    Returns:
                    HubSpotApiResult with the lead data or error information
    """
    logfire.info(f"Attempting to get lead by ID: {lead_id}")

    default_properties = [
        "hs_lead_name", "hs_lead_status", "hs_lead_label", "createdate"
    ]
    fetch_properties = properties if properties is not None else default_properties

    try:
      lead_response = await asyncio.to_thread(
          self.client.crm.objects.basic_api.get_by_id,
          object_type="leads",
          object_id=lead_id,
          properties=fetch_properties,
          archived=False
      )

      if lead_response and lead_response.id:
        logfire.info(f"Successfully fetched lead ID: {lead_response.id}")
        return HubSpotApiResult(
            status="success",
            entity_type="lead",
            hubspot_id=lead_response.id,
            message="Lead fetched successfully.",
            details=lead_response.to_dict()
        )
      else:
        logfire.warn(f"Lead ID {lead_id} fetched but object or ID is missing.")
        return HubSpotApiResult(
            status="error",
            entity_type="lead",
            hubspot_id=lead_id,
            message="Lead fetched but object or ID was missing."
        )
    except Exception as e:
      error_details = await _handle_api_error(e, "get_lead_by_id", lead_id)
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          hubspot_id=lead_id,
          message=f"Error fetching lead: {str(e)}",
          details=error_details
      )

  async def update_lead_properties(
      self, lead_id: str, properties: Dict[str, Any]
  ) -> HubSpotApiResult:
    """
    Update specific properties of a HubSpot lead using the v3 Objects API.

    Args:
                    lead_id: The HubSpot ID of the lead to update
                    properties: Dictionary of property keys and values to update

    Returns:
                    HubSpotApiResult with status information
    """
    if not lead_id:
      logger.error("Cannot update lead: Missing lead ID.")
      return HubSpotApiResult(
          status="error",
          message="Cannot update lead: Missing lead ID.",
          hubspot_id=None,
          details={"error": "Missing lead ID"}
      )

    if not properties:
      logger.warning(
          f"Update lead called for ID {lead_id} with no properties to update. Skipping API call.")
      return HubSpotApiResult(
          status="success",
          message="No properties to update, operation skipped.",
          hubspot_id=lead_id,
          details={"warning": "No properties provided for update"}
      )

    try:
      # Process any date properties if needed
      processed_props = {}
      for key, value in properties.items():
        # Add other known date fields for leads if any
        if key in ['rental_start_date', 'rental_end_date']:
          if value and isinstance(value, str) and _is_valid_iso_date(value):
            processed_props[key] = self._convert_date_to_timestamp_ms(value)
          else:
            processed_props[key] = value
        else:
          processed_props[key] = value

      # Use the generic objects API for leads
      from hubspot.crm.objects.models import SimplePublicObjectInput

      simple_public_object_input = SimplePublicObjectInput(
          properties=processed_props
      )

      api_response = await asyncio.to_thread(
          self.client.crm.objects.basic_api.update,
          object_type="leads",
          object_id=lead_id,
          simple_public_object_input=simple_public_object_input,
      )
      logger.info(f"Successfully updated lead ID: {lead_id}")
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      await _handle_api_error(e, "update lead", lead_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "update lead", lead_id)
      return None

  async def associate_lead_to_contact(
      self, lead_id: str, contact_id: str
  ) -> bool:
    """
    Associates a lead with a contact using the v4 Associations API.

    Args:
                    lead_id: The ID of the lead
                    contact_id: The ID of the contact

    Returns:
                    Boolean indicating success or failure
    """
    # Using the standard lead-to-contact association type (numeric ID 280)
    # This is the same as "Lead to Contact" in the HubSpot UI
    return await self.associate_objects(
        from_object_type="leads",
        from_object_id=lead_id,
        to_object_type="contacts",
        to_object_id=contact_id,
        association_type_id=280
    )

  async def check_connection(self) -> str:
    """Checks the connection to HubSpot by trying to list owners."""
    if not self.client:
      # Use logfire for consistency if desired, or keep standard logger
      logfire.warning("HubSpot client not initialized for health check.")
      return "error: client not initialized"
    try:
      await asyncio.to_thread(self.client.crm.owners.owners_api.get_page, limit=1)
      logfire.debug("HubSpot connection check successful.")
      return "ok"
    except OwnersApiException as e:  # Specific exception for owners API
      logfire.error(
          "HubSpot connection check failed: Owners API Exception",
          status_code=e.status,
          reason=e.reason,
      )  # Use logfire.error
      return f"error: Owners API Exception {e.status}"
    except Exception as e:  # Catch any other exceptions
      logfire.error(
          "HubSpot connection check failed: Unexpected error",
          error_message=str(e),
          exc_info=True,  # Keep exc_info for unexpected errors
      )
      status = getattr(e, "status", "Unknown")
      reason = getattr(e, "reason", "Unknown")
      if status != "Unknown" or reason != "Unknown":
        return f"error: API-like Exception Status {status}, Reason {reason}, Details: {str(e)}"
      return f"error: Unexpected error: {str(e)}"

  async def close(self):
    """Placeholder close method for HubSpotManager if needed by a shutdown sequence."""
    # The HubSpot client typically doesn't require explicit closing for stateless API calls.
    # If there were specific resources to release (e.g., a persistent connection pool
    # not managed by the underlying HTTP library), they would be handled here.
    logger.info(
        "HubSpotManager close called. No specific resources to release for the default client."
    )
    pass


# Instantiate the manager for global use, ensuring settings are loaded
# This allows other modules to import hubspot_manager directly.
# Ensure app.core.config.settings are available when this module is imported.
try:
  hubspot_manager = HubSpotManager()
except ValueError as e:
  logger.critical(
      f"Failed to initialize HubSpotManager at module level: {e}", exc_info=True
  )
  # Depending on the application's desired behavior for a critical setup failure,
  # you might raise the error further or exit, or allow a None object
  # For now, we'll let it be None and dependent services should handle this.
  hubspot_manager = None
  # We're setting hubspot_manager to None, so we don't need to raise an error here.
  # Dependent services should check if hubspot_manager is None before using it.
  # raise RuntimeError(f"HubSpotManager initialization failed: {e}")
