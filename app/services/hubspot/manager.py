# app/services/hubspot/manager.py

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Literal
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import json

import httpx
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
from .utils.helpers import _is_valid_iso_date, _handle_api_error
from .contact.operations import ContactOperations
from .company.operations import CompanyOperations
from .lead.operations import LeadOperations
from .owner.operations import OwnerOperations
from .pipeline.operations import PipelineOperations
from .association.operations import AssociationOperations
from .property.operations import PropertyOperations

logger = logging.getLogger(__name__)


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

    # Initialize httpx client for direct API calls
    self._http_client = httpx.AsyncClient(
        base_url="https://api.hubapi.com",
        headers={
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        },
        timeout=30.0
    )

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

    # Initialize operation handlers
    self.contact = ContactOperations(self)
    self.company = CompanyOperations(self)
    self.lead = LeadOperations(self)
    self.owner = OwnerOperations(self)
    self.pipeline = PipelineOperations(self)
    self.association = AssociationOperations(self)
    self.property = PropertyOperations(self)

  def _convert_date_to_timestamp_ms(self, date_str: Optional[str]) -> Optional[int]:
    """
    Convert YYYY-MM-DD date string to a HubSpot-compatible millisecond Unix timestamp,
    representing midnight UTC of that date.
    Returns None if the date_str is None, empty, or invalid.
    """
    if not date_str:
      return None
    try:
      if _is_valid_iso_date(date_str):
        date_object = datetime.strptime(date_str, "%Y-%m-%d").date()
        dt_midnight_utc = datetime.combine(
            date_object, datetime.min.time(), tzinfo=timezone.utc)
        return int(dt_midnight_utc.timestamp() * 1000)
      else:
        logger.warning(
            f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")
        return None
    except Exception as e:
      logger.error(f"Error converting date '{date_str}' to timestamp: {e}")
      return None

  async def close(self):
    """Close the HTTP client and any other resources."""
    if hasattr(self, '_http_client'):
      await self._http_client.aclose()

  async def check_connection(self) -> str:
    """Check HubSpot API connection by making a simple API call."""
    try:
      # Use the HubSpot client directly for a simple API test
      # This will test authentication and basic connectivity
      if hasattr(self, 'client') and self.client:
        # Try to access the contact properties endpoint which requires minimal permissions
        response = self.client.crm.properties.core_api.get_all(
            object_type="contacts",
            archived=False
        )
        return "ok: HubSpot API connection successful"
      else:
        return "error: HubSpot client not initialized"
    except Exception as e:
      return f"error: {str(e)}"

  # Legacy method delegations for backward compatibility
  async def search_leads(self, search_request: HubSpotSearchRequest) -> HubSpotSearchResponse:
    """Search leads in HubSpot."""
    return await self.lead.search(search_request)

  # Contact methods
  async def create_contact(self, contact_input: HubSpotContactInput) -> HubSpotApiResult:
    return await self.contact.create(contact_input)

  async def get_contact(self, email: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    return await self.contact.get_by_email(email, properties)

  async def update_contact(self, contact_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
    return await self.contact.update(contact_id, properties)

  async def delete_contact(self, contact_id: str) -> bool:
    return await self.contact.delete(contact_id)

  async def create_or_update_contact(self, contact_input: HubSpotContactInput) -> HubSpotApiResult:
    return await self.contact.create_or_update(contact_input)

  async def get_contact_by_id(self, contact_id: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    return await self.contact.get_by_id(contact_id, properties)

  # Company methods
  async def create_company(self, company_input: HubSpotCompanyInput) -> HubSpotApiResult:
    return await self.company.create(company_input)

  async def get_company(self, domain: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    return await self.company.get_by_domain(domain, properties)

  async def update_company(self, company_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
    return await self.company.update(company_id, properties)

  async def delete_company(self, company_id: str) -> bool:
    return await self.company.delete(company_id)

  # Lead methods
  async def create_lead(self, lead_input: HubSpotLeadInput) -> HubSpotApiResult:
    return await self.lead.create(lead_input)

  async def get_lead_by_id(self, lead_id: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    return await self.lead.get_by_id(lead_id, properties)

  async def update_lead_properties(self, lead_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
    return await self.lead.update_properties(lead_id, properties)

  async def associate_lead_to_contact(self, lead_id: str, contact_id: str) -> bool:
    return await self.lead.associate_to_contact(lead_id, contact_id)

  # Complex operation that uses multiple object types
  async def create_or_update_contact_and_lead(self, contact_input: HubSpotContactInput, lead_input: HubSpotLeadInput) -> Tuple[HubSpotApiResult, HubSpotApiResult]:
    return await self.lead.create_or_update_contact_and_lead(contact_input, lead_input)

  # Owner methods
  async def get_owners(self, limit: int = 100) -> List[HubSpotOwner]:
    return await self.owner.get_all(limit)

  async def get_owner_by_email(self, email: str) -> Optional[HubSpotOwner]:
    return await self.owner.get_by_email(email)

  # Association methods
  async def associate_objects(self, from_object_type: str, from_object_id: str, to_object_type: str, to_object_id: str, association_type_id: int) -> bool:
    return await self.association.associate_objects(from_object_type, from_object_id, to_object_type, to_object_id, association_type_id)

  # Pipeline methods
  async def get_pipelines(self, object_type: str, archived: bool = False) -> List[HubSpotPipeline]:
    return await self.pipeline.get_pipelines(object_type, archived)

  async def get_pipeline_stages(self, pipeline_id: str, object_type: str, archived: bool = False) -> List[HubSpotPipelineStage]:
    return await self.pipeline.get_pipeline_stages(pipeline_id, object_type, archived)

  # Property methods
  async def create_property(self, object_type: str, property_name: str, property_label: str, property_type: str = "string", group_name: Optional[str] = None) -> HubSpotApiResult:
    return await self.property.create_property(object_type, property_name, property_label, property_type, group_name)

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
          "tickets": self.client.crm.tickets.search_api,
          "leads": self.client.crm.objects.search_api,
      }

      if object_type not in api_client_map:
        logger.error(f"Unsupported object type for search: {object_type}")
        return HubSpotSearchResponse(total=0, results=[])

      if object_type == "leads":
        # For leads, use the objects API with object_type parameter
        api_response = await asyncio.to_thread(
            self.client.crm.objects.search_api.do_search,
            object_type="leads",
            public_object_search_request=search_request_dict
        )
      else:
        api_response = await asyncio.to_thread(
            api_client_map[object_type].do_search,
            public_object_search_request=search_request_dict
        )

      results = []
      paging_dict = None
      total = 0

      if api_response and hasattr(api_response, 'results'):
        results = [HubSpotObject(**obj.to_dict())
                   for obj in getattr(api_response, 'results', [])]

      if api_response and hasattr(api_response, 'paging'):
        paging = getattr(api_response, 'paging', None)
        if paging and hasattr(paging, 'to_dict'):
          paging_dict = paging.to_dict()

      if api_response and hasattr(api_response, 'total'):
        total = getattr(api_response, 'total', 0)

      return HubSpotSearchResponse(
          total=total,
          results=results,
          paging=paging_dict,
      )
    except ObjectApiException as e:
      await _handle_api_error(e, f"{object_type} search")
      return HubSpotSearchResponse(total=0, results=[])
    except Exception as e:
      await _handle_api_error(e, f"{object_type} search")
      return HubSpotSearchResponse(total=0, results=[])
