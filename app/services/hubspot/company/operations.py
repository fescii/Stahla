# app/services/hubspot/company/operations.py

import asyncio
import logging
from typing import Any, Dict, List, Optional

from hubspot.crm.companies import SimplePublicObjectInput
from hubspot.crm.objects.exceptions import ApiException as ObjectApiException

from app.models.hubspot import (
    HubSpotCompanyInput,
    HubSpotCompanyProperties,
    HubSpotApiResult,
    HubSpotSearchRequest,
    HubSpotSearchResponse,
    HubSpotObject,
)
from app.services.hubspot.utils.helpers import _handle_api_error

logger = logging.getLogger(__name__)


class CompanyOperations:
  def __init__(self, manager):
    self.manager = manager

  async def create(self, company_input: HubSpotCompanyInput) -> HubSpotApiResult:
    """Create a new company in HubSpot."""
    try:
      properties = company_input.properties
      result = await self.create_company(properties)
      if result:
        return HubSpotApiResult(
            status="created",
            entity_type="company",
            hubspot_id=result.id,
            message="Company created successfully"
        )
      else:
        return HubSpotApiResult(
            status="error",
            entity_type="company",
            message="Failed to create company"
        )
    except Exception as e:
      return HubSpotApiResult(
          status="error",
          entity_type="company",
          message=f"Error creating company: {str(e)}"
      )

  async def create_company(
      self, properties: HubSpotCompanyProperties
  ) -> Optional[HubSpotObject]:
    """Create a new company."""
    logger.debug(
        f"Creating company with properties: {properties.model_dump_json(indent=2, exclude_none=True)}"
    )
    try:
      simple_public_object_input = SimplePublicObjectInput(
          properties=properties.model_dump(exclude_none=True)
      )
      api_response = await asyncio.to_thread(
          self.manager.client.crm.companies.basic_api.create,
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

  async def get_by_domain(self, domain: str, properties: Optional[List[str]] = None) -> HubSpotApiResult:
    """Get a company by domain."""
    try:
      # Create search request to find company by domain
      from app.models.hubspot import HubSpotSearchRequest, HubSpotSearchFilterGroup, HubSpotSearchFilter

      search_request = HubSpotSearchRequest(
          filterGroups=[
              HubSpotSearchFilterGroup(
                  filters=[
                      HubSpotSearchFilter(
                          propertyName="domain",
                          operator="EQ",
                          value=domain
                      )
                  ]
              )
          ],
          properties=properties or [
              "hs_object_id", "name", "domain", "phone", "website", "industry"],
          limit=1
      )

      search_result = await self.search(search_request)

      if search_result.total > 0 and search_result.results:
        company = search_result.results[0]
        return HubSpotApiResult(
            status="success",
            entity_type="company",
            hubspot_id=company.id,
            message="Company found by domain",
            details=company.model_dump()
        )
      else:
        return HubSpotApiResult(
            status="not_found",
            entity_type="company",
            message=f"No company found with domain: {domain}"
        )
    except Exception as e:
      return HubSpotApiResult(
          status="error",
          entity_type="company",
          message=f"Error searching for company by domain: {str(e)}"
      )

  async def get_company(
      self, company_id: str, properties_list: Optional[List[str]] = None
  ) -> Optional[HubSpotObject]:
    """Get a company by ID."""
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
          self.manager.client.crm.companies.basic_api.get_by_id,
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

  async def update(self, company_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
    """Update a company's properties."""
    try:
      company_props = HubSpotCompanyProperties(**properties)
      result = await self.update_company(company_id, company_props)
      if result:
        return HubSpotApiResult(
            status="updated",
            entity_type="company",
            hubspot_id=result.id,
            message="Company updated successfully"
        )
      else:
        return HubSpotApiResult(
            status="error",
            entity_type="company",
            message="Failed to update company"
        )
    except Exception as e:
      return HubSpotApiResult(
          status="error",
          entity_type="company",
          message=f"Error updating company: {str(e)}"
      )

  async def update_company(
      self, company_id: str, properties: HubSpotCompanyProperties
  ) -> Optional[HubSpotObject]:
    """Update an existing company."""
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
          self.manager.client.crm.companies.basic_api.update,
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

  async def delete(self, company_id: str) -> bool:
    """Delete (archive) a company."""
    return await self.delete_company(company_id)

  async def delete_company(self, company_id: str) -> bool:
    """Delete (archive) a company."""
    logger.debug(f"Archiving company ID: {company_id}")
    try:
      await asyncio.to_thread(self.manager.client.crm.companies.basic_api.archive, company_id=company_id)
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

  async def search(self, search_request: HubSpotSearchRequest) -> HubSpotSearchResponse:
    """Search for companies."""
    try:
      return await self.manager.search_objects("companies", search_request)
    except Exception as e:
      logger.error(f"Error searching companies: {e}", exc_info=True)
      return HubSpotSearchResponse(total=0, results=[], paging=None)
