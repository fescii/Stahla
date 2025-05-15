# app/services/hubspot.py

# Standard library imports
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Literal  # Added Literal
from datetime import datetime, timedelta
from collections import defaultdict

from cachetools import TTLCache
from hubspot import HubSpot
from hubspot.crm.associations.v4.models import (
    AssociationSpec,
    PublicObjectId,
    BatchInputPublicAssociationMultiPost,
    PublicAssociationMultiPost,
    # For basic_api.create response if needed, though not directly used in return type here
    # PublicAssociationsForObject,
)
from hubspot.crm.companies import SimplePublicObjectInput
from hubspot.crm.contacts import (
    SimplePublicObjectInput as ContactSimplePublicObjectInput,
)
from hubspot.crm.deals import SimplePublicObjectInput as DealSimplePublicObjectInput
from hubspot.crm.deals.exceptions import ApiException as DealApiException
from hubspot.crm.objects.exceptions import (
    ApiException as ObjectApiException,
)  # General CRM object API exception
from hubspot.crm.owners import (
    ApiException as OwnersApiException,
)  # Ensure this is imported for check_connection
from hubspot.crm.owners import PublicOwner  # from hubspot.crm.owners.models
from hubspot.crm.pipelines import (
    Pipeline,
    PipelineStage,
)  # from hubspot.crm.pipelines.models

# from hubspot.crm.properties import Property # from hubspot.crm.properties.models - Not directly used in this refactor for Property definition
from pydantic import ValidationError
import logfire  # Ensure logfire is imported

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
    HubSpotObject,  # Added
    HubSpotSearchRequest,  # Added
    HubSpotSearchResponse,  # Added
    HubSpotDealProperties,  # Added (for create/update deals)
    HubSpotTicketProperties,  # Added (for create/update tickets)
    HubSpotPipeline,  # Added
    HubSpotPipelineStage,  # Added
    HubSpotOwner,  # Added
    HubSpotSearchFilter,  # Added
    HubSpotSearchFilterGroup,  # Added
)

# from app.models.quote import LeadCreateSchema # Removed this problematic import

logger = logging.getLogger(__name__)


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

  if isinstance(e, (ObjectApiException, DealApiException)):
    status_code = e.status
    if hasattr(e, "body") and e.body:
      error_details_str = e.body
      try:
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
        f"Unexpected error in {context}{f' for ID {object_id}' if object_id else ''}: {
            e}",
        exc_info=True,
    )

  return {
      "error": error_message,
      "details_raw": error_details_str,
      "details_parsed": parsed_error_details,
      "status_code": status_code,
      "context": context,
      "object_id": object_id,
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

  # --- Contact Methods ---
  async def create_contact(
          self, properties: HubSpotContactProperties
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Creating contact with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      simple_public_object_input = ContactSimplePublicObjectInput(
          properties=properties.model_dump(exclude_none=True)
      )
      api_response = await asyncio.to_thread(
          self.client.crm.contacts.basic_api.create,
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
        f"Updating contact ID: {contact_id} with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    if not properties.model_dump(exclude_none=True, exclude_unset=True):
      logger.warning(
          f"Update contact called for ID {contact_id} with no properties to update. Skipping API call."
      )
      return await self.get_contact(contact_id)  # Return current state

    try:
      simple_public_object_input = ContactSimplePublicObjectInput(
          properties=properties.model_dump(
              exclude_none=True, exclude_unset=True)
      )
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

  # --- Deal Methods ---
  async def create_deal(
          self, properties: HubSpotDealProperties
  ) -> Optional[
          HubSpotObject
  ]:  # Changed HubSpotDealPropertiesCreate to HubSpotDealProperties
    logger.debug(
        f"Creating deal with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      deal_props_dict = properties.model_dump(exclude_none=True)

      if "pipeline" not in deal_props_dict or "dealstage" not in deal_props_dict:
        logger.debug(
            f"Pipeline or dealstage not in input for deal '{deal_props_dict.get('dealname', 'N/A')}'. Attempting to set defaults from '{self.DEFAULT_DEAL_PIPELINE_NAME}'."
        )
        default_pipeline = await self.get_pipeline_by_name(
            object_type="deals", pipeline_name=self.DEFAULT_DEAL_PIPELINE_NAME
        )
        if default_pipeline and default_pipeline.id and default_pipeline.stages:
          deal_props_dict["pipeline"] = default_pipeline.id
          first_stage = min(
              default_pipeline.stages,
              key=lambda s: (
                  s.display_order
                  if s.display_order is not None
                  else float("inf")
              ),
              default=None,
          )
          if first_stage and first_stage.id:
            deal_props_dict["dealstage"] = first_stage.id
            logger.info(
                f"Set deal to pipeline '{default_pipeline.label}' ({default_pipeline.id}) and stage '{first_stage.label}' ({first_stage.id})"
            )
          else:
            logger.warning(
                f"Default deal pipeline '{self.DEFAULT_DEAL_PIPELINE_NAME}' has no stages or first stage ID is missing. Deal stage not set."
            )
        else:
          logger.warning(
              f"Default deal pipeline '{self.DEFAULT_DEAL_PIPELINE_NAME}' not found or has no stages. Pipeline and stage not set for deal."
          )

      simple_public_object_input = DealSimplePublicObjectInput(
          properties=deal_props_dict
      )
      api_response = await asyncio.to_thread(
          self.client.crm.deals.basic_api.create,
          simple_public_object_input=simple_public_object_input
      )
      logger.info(f"Successfully created deal ID: {api_response.id}")
      return HubSpotObject(**api_response.to_dict())
    except DealApiException as e:
      await _handle_api_error(e, "deal creation")
      return None
    except Exception as e:
      await _handle_api_error(e, "deal creation")
      return None

  async def get_deal(
          self, deal_id: str, properties_list: Optional[List[str]] = None
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Getting deal ID: {deal_id} with properties: {properties_list}")
    try:
      fetch_properties = properties_list or [
          "dealname",
          "amount",
          "dealstage",
          "pipeline",
          "closedate",
          "hubspot_owner_id",
          "hs_object_id",
      ]
      api_response = await asyncio.to_thread(
          self.client.crm.deals.basic_api.get_by_id,
          deal_id=deal_id, properties=fetch_properties, archived=False
      )
      return HubSpotObject(**api_response.to_dict())
    except DealApiException as e:
      if e.status == 404:
        logger.info(f"Deal with ID {deal_id} not found.")
      else:
        await _handle_api_error(e, "get deal", deal_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "get deal", deal_id)
      return None

  async def update_deal(
          self, deal_id: str, properties: HubSpotDealProperties
  ) -> Optional[
          HubSpotObject
  ]:  # Changed HubSpotDealPropertiesUpdate to HubSpotDealProperties
    logger.debug(
        f"Updating deal ID: {deal_id} with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    if not properties.model_dump(exclude_none=True, exclude_unset=True):
      logger.warning(
          f"Update deal called for ID {deal_id} with no properties to update. Skipping API call."
      )
      return await self.get_deal(deal_id)
    try:
      simple_public_object_input = DealSimplePublicObjectInput(
          properties=properties.model_dump(
              exclude_none=True, exclude_unset=True)
      )
      api_response = await asyncio.to_thread(
          self.client.crm.deals.basic_api.update,
          deal_id=deal_id, simple_public_object_input=simple_public_object_input
      )
      logger.info(f"Successfully updated deal ID: {deal_id}")
      return HubSpotObject(**api_response.to_dict())
    except DealApiException as e:
      await _handle_api_error(e, "update deal", deal_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "update deal", deal_id)
      return None

  async def delete_deal(self, deal_id: str) -> bool:
    logger.debug(f"Archiving deal ID: {deal_id}")
    try:
      await asyncio.to_thread(self.client.crm.deals.basic_api.archive, deal_id=deal_id)
      logger.info(f"Successfully archived deal ID: {deal_id}")
      return True
    except DealApiException as e:
      if e.status == 404:
        logger.info(f"Deal with ID {deal_id} not found for archiving.")
        return True
      await _handle_api_error(e, "archive deal", deal_id)
      return False
    except Exception as e:
      await _handle_api_error(e, "archive deal", deal_id)
      return False

  # --- Ticket Methods ---
  async def create_ticket(
          self, properties: HubSpotTicketProperties
  ) -> Optional[
          HubSpotObject
  ]:  # Changed HubSpotTicketPropertiesCreate to HubSpotTicketProperties
    logger.debug(
        f"Creating ticket with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      ticket_props_dict = properties.model_dump(exclude_none=True)
      if (
              "hs_pipeline" not in ticket_props_dict
              or "hs_pipeline_stage" not in ticket_props_dict
      ):
        logger.debug(
            f"Pipeline or stage not in input for ticket '{ticket_props_dict.get('subject', 'N/A')}'. Attempting to set defaults from '{self.DEFAULT_TICKET_PIPELINE_NAME}'."
        )
        default_pipeline = await self.get_pipeline_by_name(
            object_type="tickets",
            pipeline_name=self.DEFAULT_TICKET_PIPELINE_NAME,
        )
        if default_pipeline and default_pipeline.id and default_pipeline.stages:
          ticket_props_dict["hs_pipeline"] = default_pipeline.id
          first_stage = min(
              default_pipeline.stages,
              key=lambda s: (
                  s.display_order
                  if s.display_order is not None
                  else float("inf")
              ),
              default=None,
          )
          if first_stage and first_stage.id:
            ticket_props_dict["hs_pipeline_stage"] = first_stage.id
            logger.info(
                f"Set ticket to pipeline '{default_pipeline.label}' ({default_pipeline.id}) and stage '{first_stage.label}' ({first_stage.id})"
            )
          else:
            logger.warning(
                f"Default ticket pipeline '{self.DEFAULT_TICKET_PIPELINE_NAME}' has no stages or first stage ID is missing. Ticket stage not set."
            )
        else:
          logger.warning(
              f"Default ticket pipeline '{self.DEFAULT_TICKET_PIPELINE_NAME}' not found or has no stages. Pipeline and stage not set for ticket."
          )

      simple_public_object_input = SimplePublicObjectInput(
          properties=ticket_props_dict
      )
      api_response = await asyncio.to_thread(
          self.client.crm.tickets.basic_api.create,
          simple_public_object_input=simple_public_object_input
      )
      logger.info(f"Successfully created ticket ID: {api_response.id}")
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      await _handle_api_error(e, "ticket creation")
      return None
    except Exception as e:
      await _handle_api_error(e, "ticket creation")
      return None

  async def get_ticket(
          self, ticket_id: str, properties_list: Optional[List[str]] = None
  ) -> Optional[HubSpotObject]:
    logger.debug(
        f"Getting ticket ID: {ticket_id} with properties: {properties_list}"
    )
    try:
      fetch_properties = properties_list or [
          "subject",
          "content",
          "hs_pipeline",
          "hs_pipeline_stage",
          "hubspot_owner_id",
          "hs_object_id",
      ]
      api_response = await asyncio.to_thread(
          self.client.crm.tickets.basic_api.get_by_id,
          ticket_id=ticket_id, properties=fetch_properties, archived=False
      )
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      if e.status == 404:
        logger.info(f"Ticket with ID {ticket_id} not found.")
      else:
        await _handle_api_error(e, "get ticket", ticket_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "get ticket", ticket_id)
      return None

  async def update_ticket(
          self, ticket_id: str, properties: HubSpotTicketProperties
  ) -> Optional[
          HubSpotObject
  ]:  # Changed HubSpotTicketPropertiesUpdate to HubSpotTicketProperties
    logger.debug(
        f"Updating ticket ID: {ticket_id} with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    if not properties.model_dump(exclude_none=True, exclude_unset=True):
      logger.warning(
          f"Update ticket called for ID {ticket_id} with no properties to update. Skipping API call."
      )
      return await self.get_ticket(ticket_id)
    try:
      simple_public_object_input = SimplePublicObjectInput(
          properties=properties.model_dump(
              exclude_none=True, exclude_unset=True)
      )
      api_response = await asyncio.to_thread(
          self.client.crm.tickets.basic_api.update,
          ticket_id=ticket_id,
          simple_public_object_input=simple_public_object_input,
      )
      logger.info(f"Successfully updated ticket ID: {ticket_id}")
      return HubSpotObject(**api_response.to_dict())
    except ObjectApiException as e:
      await _handle_api_error(e, "update ticket", ticket_id)
      return None
    except Exception as e:
      await _handle_api_error(e, "update ticket", ticket_id)
      return None

  async def delete_ticket(self, ticket_id: str) -> bool:
    logger.debug(f"Archiving ticket ID: {ticket_id}")
    try:
      await asyncio.to_thread(self.client.crm.tickets.basic_api.archive, ticket_id=ticket_id)
      logger.info(f"Successfully archived ticket ID: {ticket_id}")
      return True
    except ObjectApiException as e:
      if e.status == 404:
        logger.info(f"Ticket with ID {ticket_id} not found for archiving.")
        return True
      await _handle_api_error(e, "archive ticket", ticket_id)
      return False
    except Exception as e:
      await _handle_api_error(e, "archive ticket", ticket_id)
      return False

  # --- Pipeline, Stage, Owner Methods ---
  async def get_pipelines(self, object_type: str) -> List[HubSpotPipeline]:
    cache_key = f"pipelines_{object_type}"
    cached_pipelines = self.pipelines_cache.get(cache_key)
    if cached_pipelines is not None:
      logger.debug(f"Returning cached pipelines for {object_type}")
      return cached_pipelines

    logger.debug(f"Fetching pipelines for object type: {object_type}")
    try:
      sdk_object_type = object_type.rstrip("s")
      if sdk_object_type not in ["deal", "ticket"]:
        logger.error(
            f"Unsupported object type for pipelines: {object_type} (sdk type: {sdk_object_type})"
        )
        return []

      api_response = await asyncio.to_thread(
          self.client.crm.pipelines.pipelines_api.get_all,
          object_type=sdk_object_type
      )

      pipelines_data = []
      for p_data in api_response.results:
        stages = await self.get_pipeline_stages(object_type, p_data.id)
        pipeline_model = HubSpotPipeline(**p_data.to_dict(), stages=stages)
        pipelines_data.append(pipeline_model)

      self.pipelines_cache[cache_key] = pipelines_data
      return pipelines_data
    except ObjectApiException as e:
      await _handle_api_error(e, f"{object_type} pipelines retrieval")
      return []
    except Exception as e:
      await _handle_api_error(e, f"{object_type} pipelines retrieval")
      return []

  async def get_pipeline_by_name(
          self, object_type: str, pipeline_name: str
  ) -> Optional[HubSpotPipeline]:
    logger.debug(f"Getting {object_type} pipeline by name: {pipeline_name}")
    pipelines = await self.get_pipelines(object_type)
    for p in pipelines:
      if p.label == pipeline_name:  # 'label' is the human-readable name
        return p
    logger.warning(
        f"{object_type.capitalize()} pipeline with name '{pipeline_name}' not found."
    )
    return None

  async def get_pipeline_stages(
          self, object_type: str, pipeline_id: str
  ) -> List[HubSpotPipelineStage]:
    cache_key = f"stages_{object_type}_{pipeline_id}"
    cached_stages = self.stages_cache.get(cache_key)
    if cached_stages is not None:
      logger.debug(
          f"Returning cached stages for {object_type} pipeline ID: {pipeline_id}"
      )
      return cached_stages

    logger.debug(
        f"Fetching stages for {object_type} pipeline ID: {pipeline_id}")
    try:
      sdk_object_type = object_type.rstrip("s")
      if sdk_object_type not in ["deal", "ticket"]:
        logger.error(
            f"Unsupported object type for pipeline stages: {object_type}"
        )
        return []

      api_response = await asyncio.to_thread(
          self.client.crm.pipelines.pipeline_stages_api.get_all,
          object_type=sdk_object_type, pipeline_id=pipeline_id
      )
      stages = [HubSpotPipelineStage(**s.to_dict())
                for s in api_response.results]
      self.stages_cache[cache_key] = stages
      return stages
    except ObjectApiException as e:
      await _handle_api_error(
          e, f"{object_type} pipeline stages retrieval", pipeline_id
      )
      return []
    except Exception as e:
      await _handle_api_error(
          e, f"{object_type} pipeline stages retrieval", pipeline_id
      )
      return []

  async def get_pipeline_stage_by_name(
          self, object_type: str, pipeline_id: str, stage_name: str
  ) -> Optional[HubSpotPipelineStage]:
    logger.debug(
        f"Getting stage by name: {stage_name} for {object_type} pipeline ID: {pipeline_id}"
    )
    stages = await self.get_pipeline_stages(object_type, pipeline_id)
    for stage in stages:
      if stage.label == stage_name:
        return stage
    logger.warning(
        f"Stage with name '{stage_name}' not found in {object_type} pipeline '{pipeline_id}'."
    )
    return None

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
          from_object_type: str,  # e.g., "deals", "contacts" (plural input)
          from_object_id: str,
          to_object_type: str,  # e.g., "contacts", "companies" (plural input)
          to_object_id: str,
          association_type_id: int,  # Numeric association type ID
  ) -> bool:
    context = f"associating {from_object_type} {from_object_id} to {to_object_type} {to_object_id} (type {association_type_id})"
    logger.debug(f"Attempting to {context}")
    try:
      association_specs = [
          AssociationSpec(
              # Or "USER_DEFINED" if applicable based on ID
              association_category="HUBSPOT_DEFINED",
              association_type_id=int(association_type_id),
          )
      ]

      # Convert plural input object types to singular lowercase for v4 SDK calls
      sdk_from_object_type = from_object_type.lower()
      if sdk_from_object_type == "contacts":
        sdk_from_object_type = "contact"
      elif sdk_from_object_type == "companies":
        sdk_from_object_type = "company"
      elif sdk_from_object_type == "deals":
        sdk_from_object_type = "deal"
      elif sdk_from_object_type == "tickets":
        sdk_from_object_type = "ticket"
      # Add more specific cases if other plural forms are used, or a more general singularizer
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

      # Use basic_api.create for a single labeled association between two specific objects.
      # The SDK method signature is: create(self, from_object_type, from_object_id, to_object_type, to_object_id, association_spec, **kwargs)
      # It expects a list of AssociationSpec for the 'association_spec' parameter.
      await asyncio.to_thread(
          self.client.crm.associations.v4.basic_api.create,
          from_object_type=sdk_from_object_type,
          from_object_id=from_object_id,
          to_object_type=sdk_to_object_type,
          to_object_id=to_object_id,
          association_spec=association_specs,  # Pass the list of AssociationSpec
      )
      logger.info(f"Successfully {context}")
      return True  # If no ApiException, assume success

    except ObjectApiException as e:  # Catch HubSpot specific API errors
      await _handle_api_error(e, context)
      return False
    except (
            ImportError
    ) as ie:  # In case AssociationSpec or other models are not found
      logger.error(
          f"ImportError during association: {ie}. Ensure HubSpot SDK is up-to-date and v4 models are available.",
          exc_info=True,
      )
      return False
    except Exception as e:
      await _handle_api_error(e, context)
      return False

  async def batch_associate_objects(self, inputs: List[Dict[str, Any]]) -> bool:
    """
    Associates objects in batch using HubSpot API v4.
    Each item in 'inputs' should be a dict like:
    {
            "from_object_type": "deals", "from_object_id": "id1",
            "to_object_type": "contacts", "to_object_id": "id2",
            "association_type_id": 123 (numeric)
    }
    """
    if not inputs:
      logger.info("No associations to perform in batch.")
      return True

    logger.debug(f"Batch associating {len(inputs)} pairs.")

    # Group inputs by (from_object_type, to_object_type) as the API call is per pair of object types.
    grouped_inputs: Dict[tuple[str, str],
                         List[PublicAssociationMultiPost]] = {}
    for item in inputs:
      try:
        # Convert plural input object types to singular lowercase for v4 SDK calls
        from_obj_type_plural = item["from_object_type"].lower()
        sdk_from_object_type = from_obj_type_plural
        if from_obj_type_plural == "contacts":
          sdk_from_object_type = "contact"
        elif from_obj_type_plural == "companies":
          sdk_from_object_type = "company"
        elif from_obj_type_plural == "deals":
          sdk_from_object_type = "deal"
        elif from_obj_type_plural == "tickets":
          sdk_from_object_type = "ticket"
        elif from_obj_type_plural.endswith('s'):
          sdk_from_object_type = from_obj_type_plural[:-1]

        to_obj_type_plural = item["to_object_type"].lower()
        sdk_to_object_type = to_obj_type_plural
        if to_obj_type_plural == "contacts":
          sdk_to_object_type = "contact"
        elif to_obj_type_plural == "companies":
          sdk_to_object_type = "company"
        elif to_obj_type_plural == "deals":
          sdk_to_object_type = "deal"
        elif to_obj_type_plural == "tickets":
          sdk_to_object_type = "ticket"
        elif to_obj_type_plural.endswith('s'):
          sdk_to_object_type = to_obj_type_plural[:-1]

        key = (sdk_from_object_type, sdk_to_object_type)

        if key not in grouped_inputs:
          grouped_inputs[key] = []

        assoc_specs = [
            AssociationSpec(
                association_category="HUBSPOT_DEFINED",  # Or "USER_DEFINED"
                association_type_id=int(item["association_type_id"]),
            )
        ]
        grouped_inputs[key].append(
            PublicAssociationMultiPost(
                _from=PublicObjectId(id=item["from_object_id"]),
                to=PublicObjectId(id=item["to_object_id"]),
                types=assoc_specs,
            )
        )
      except KeyError as e:
        logger.error(
            f"Missing key in batch association input item: {item}. Error: {e}",
            exc_info=True,
        )
        # Decide if one bad item fails the whole batch or just skips. For now, skip.
        continue
      except Exception as e:
        logger.error(
            f"Error preparing batch association for item {item}: {e}",
            exc_info=True,
        )
        continue

    all_successful = True
    for (
        from_obj_type_sdk,
        to_obj_type_sdk,
    ), associations_for_pair in grouped_inputs.items():
      if not associations_for_pair:
        continue

      context = f"batch associating {len(associations_for_pair)} pairs from {from_obj_type_sdk} to {to_obj_type_sdk}"
      logger.debug(f"Attempting to {context}")

      batch_input = BatchInputPublicAssociationMultiPost(
          inputs=associations_for_pair
      )
      try:
        api_response = await asyncio.to_thread(
            self.client.crm.associations.v4.batch_api.create,
            # This is the key from grouped_inputs, already singular lowercase
            from_object_type=from_obj_type_sdk,
            # This is the key from grouped_inputs, already singular lowercase
            to_object_type=to_obj_type_sdk,
            batch_input_public_association_multi_post=batch_input,
        )

        if (
                hasattr(api_response, "status")
                and api_response.status == "COMPLETE"
        ):
          logger.info(f"Successfully completed {context}.")
        elif (
                hasattr(api_response, "status")
                and api_response.status == "COMPLETE_WITH_ERRORS"
        ):
          logger.warning(
              f"{context} completed with errors: {api_response.errors if hasattr(api_response, 'errors') else 'N/A'}"
          )
          all_successful = False  # Mark overall as not fully successful
        else:  # FAILED or other status
          logger.error(
              f"{context} failed. Status: {api_response.status if hasattr(api_response, 'status') else 'Unknown'}, Response: {api_response}"
          )
          all_successful = False
      except ObjectApiException as e:
        await _handle_api_error(e, context)
        all_successful = False
      except Exception as e:
        await _handle_api_error(e, context)
        all_successful = False

    return all_successful

  # --- Lead Creation Method ---
  async def create_lead(
          self, lead_data: HubSpotLeadInput
  ) -> HubSpotApiResult:  # Changed return type
    logger.info(
        f"Attempting to create lead with data: {lead_data.model_dump_json(indent=2, exclude_none=True)}"
    )

    response = {
        "success": False,
        "message": "Lead processing initiated.",
        "contact_id": None,
        "company_id": None,
        "deal_id": None,
        "errors": [],
        "association_results": {"total": 0, "succeeded": 0, "failed_details": []},
    }

    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    deal_id: Optional[str] = None

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
              city=getattr(lead_data.lead_properties, 'city', None),
              # Assuming zip might exist on lead_properties
              zip=getattr(lead_data.lead_properties, 'zip', None),
              # Assuming address might exist on lead_properties
              address=getattr(lead_data.lead_properties, 'address', None),
              # Assuming state might exist on lead_properties
              state=getattr(lead_data.lead_properties, 'state', None),

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

      # 3. Create Deal (only if a contact or company was successfully created/found)
      if (
              contact_id or company_id
      ):  # Proceed if we have something to associate the deal with
        deal_name_parts = [
            lead_data.contact_firstname,
            lead_data.contact_lastname,
            lead_data.project_category or "New Lead",
        ]
        deal_name = " - ".join(filter(None, deal_name_parts)
                               ) or "New Lead Deal"

        deal_create_props = HubSpotDealProperties(  # Changed from HubSpotDealPropertiesCreate
            dealname=deal_name,
            amount=(
                lead_data.estimated_value
                if lead_data.estimated_value is not None
                else 0.0
            ),  # Ensure amount is float
            # Add other necessary deal properties from lead_data
            # Example:
                # closedate=lead_data.expected_close_date, # Ensure a format is YYYY-MM-DD
                # hubspot_owner_id=assigned_owner_id, # If owner is determined
                # pipeline=default_deal_pipeline_id, # If a pipeline is determined
                # dealstage=default_deal_stage_id, # If stage is determined
        )

        if lead_data.owner_email:
          owner = await self.get_owner_by_email(lead_data.owner_email)
          if owner and owner.id:
            deal_create_props.hubspot_owner_id = owner.id
            logger.info(
                f"Assigning owner ID {owner.id} ({owner.email}) to the new deal."
            )
          else:
            logger.warning(
                f"Owner with email {lead_data.owner_email} not found. Deal will be unassigned or default assigned."
            )
            response["errors"].append(
                {
                    "step": "owner_assignment",
                    "message": f"Owner '{lead_data.owner_email}' not found.",
                }
            )

        deal = await self.create_deal(deal_create_props)
        if deal and deal.id:
          deal_id = deal.id
          response["deal_id"] = deal_id
          logger.info(
              f"Successfully created deal ID: {deal_id} with name '{deal_name}'"
          )
        else:
          logger.error(f"Failed to create deal for '{deal_name}'.")
          response["errors"].append(
              {
                  "step": "deal_creation",
                  "message": f"Failed to create deal '{deal_name}'.",
              }
          )
      else:
        logger.warning(
            "Skipping deal creation as no contact or company was created/found."
        )
        response["message"] = (
            "Contact and/or company creation failed; deal creation skipped."
        )

      # 4. Create Associations
      associations_to_attempt: List[Dict[str, Any]] = []
      if deal_id:
        if contact_id:
          associations_to_attempt.append(
              {
                  "from_object_type": "deals",
                  "from_object_id": deal_id,
                  "to_object_type": "contacts",
                  "to_object_id": contact_id,
                  "association_type_id": self.DEAL_TO_CONTACT_ASSOCIATION_TYPE_ID,
              }
          )
        if company_id:
          associations_to_attempt.append(
              {
                  "from_object_type": "deals",
                  "from_object_id": deal_id,
                  "to_object_type": "companies",
                  "to_object_id": company_id,
                  "association_type_id": self.DEAL_TO_COMPANY_ASSOCIATION_TYPE_ID,
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
          # Let's assume it for now if batch_success is false, 0 succeeded for this summary.
          response["association_results"][
              "succeeded"
          ] = 0  # Or get a more precise count

      if not response["errors"] and (contact_id or company_id or deal_id):
        response["success"] = True
        response["message"] = "Lead processed successfully."
        if not deal_id and (contact_id or company_id):
          response["message"] = (
              "Contact/Company processed; deal creation failed or was skipped."
          )
      elif not response["errors"] and not any([contact_id, company_id, deal_id]):
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

      primary_hubspot_id = response.get("deal_id") or response.get(
          "contact_id") or response.get("company_id")

      return HubSpotApiResult(
          status=current_status_literal,
          entity_type="lead",
          hubspot_id=primary_hubspot_id,
          message=response.get("message"),
          details={
              "contact_id": response.get("contact_id"),
                      "company_id": response.get("company_id"),
                      "deal_id": response.get("deal_id"),
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
          message=response["message"],
          details={"errors": response["errors"]}
      )
    except (ObjectApiException, DealApiException) as e:
      error_info = await _handle_api_error(e, "lead creation main process")
      logger.error(
          f"HubSpot API error during lead processing: {error_info.get('error', str(e))}",
          exc_info=True
      )
      response["success"] = False
      response["message"] = "A HubSpot API error occurred during lead processing."
      response["errors"].append(
          {"step": "hubspot_api_main", "details": error_info})
      return HubSpotApiResult(
          status="error",
          entity_type="lead",
          message=response["message"],
          details={"errors": response["errors"],
                   "original_error_info": error_info}
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
