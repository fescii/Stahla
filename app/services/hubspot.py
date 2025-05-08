# app/services/hubspot.py

import httpx
import logfire
from typing import Optional, Dict, Any, List
import itertools
import asyncio  # For locking

# Import models
from app.models.hubspot import (
    HubSpotContactInput,
    HubSpotContactResult,
    HubSpotLeadInput,
    HubSpotLeadResult,
    HubSpotApiResult,
    HubSpotContactProperties,
    HubSpotLeadProperties,
    HubSpotCompanyProperties, # Add Company model
    HubSpotCompanyInput # Add Company model
)
from app.models.classification import ClassificationOutput  # Needed for deal creation
from app.core.config import settings


class HubSpotManager:
    """
    Manages interactions with the HubSpot API.
    Handles creating/updating contacts and leads.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
        # Use httpx.AsyncClient for asynchronous requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Initialize the client with base URL and headers
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=15.0  # Slightly longer timeout for external API
        )
        self._owner_iterator: Optional[itertools.cycle] = None
        self._owner_list: List[Dict[str, Any]] = []
        self._owner_lock = asyncio.Lock()
        self._owners_last_fetched: Optional[float] = None
        self._owner_cache_ttl = 3600  # Cache owners for 1 hour
        logfire.info("HubSpotManager initialized.")

    async def close_client(self):
        """Gracefully closes the HTTP client."""
        await self._client.aclose()
        logfire.info("HubSpot HTTP client closed.")

    async def close(self):
        """Closes the underlying HTTPX client."""
        if self._client:
            logfire.info("Closing HubSpotManager HTTPX client...")
            await self._client.aclose()
            self._client = None # Indicate client is closed
            logfire.info("HubSpotManager HTTPX client closed.")

    async def _make_request(
            self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None
    ) -> HubSpotApiResult:
        """Helper method to make requests to the HubSpot API."""
        url = f"{self.base_url.strip('/')}/{endpoint.lstrip('/')}"
        logfire.debug(
            f"Making HubSpot API request: {method} {url}", params=params, data=json_data)
        try:
            response = await self._client.request(method, endpoint, params=params, json=json_data)
            response.raise_for_status()  # Raise exception for 4xx/5xx errors
            response_data = response.json()
            logfire.debug("HubSpot API request successful.", response=response_data)
            # HubSpot API responses often don't have a simple 'status' field like Bland
            # Success is usually indicated by 2xx status code, handled by raise_for_status
            return HubSpotApiResult(status="success", message="Request successful", details=response_data)
        except httpx.HTTPStatusError as e:
            logfire.error(f"HubSpot API HTTP error: {e.response.status_code}", url=str(
                e.request.url), response=e.response.text)
            message = f"HTTP error {e.response.status_code}"
            try:
                error_details = e.response.json()
                if "message" in error_details:
                    message += f": {error_details['message']}"
            except Exception:
                error_details = {"raw_response": e.response.text}
                message += f": {e.response.text}"
            return HubSpotApiResult(status="error", message=message, details=error_details)
        except httpx.RequestError as e:
            logfire.error(f"HubSpot API request error: {e}", url=str(e.request.url))
            return HubSpotApiResult(status="error", message=f"Request failed: {e}", details={"error_type": type(e).__name__})
        except Exception as e:
            logfire.error(
                f"Unexpected error during HubSpot API request: {e}", exc_info=True)
            return HubSpotApiResult(status="error", message=f"An unexpected error occurred: {e}", details={"error_type": type(e).__name__})

    async def search_contact_by_email(self, email: str) -> Optional[str]:
        """Searches for a contact by email and returns their HubSpot ID if found."""
        endpoint = "/crm/v3/objects/contacts/search"
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email
                        }
                    ]
                }
            ],
            # Only need ID, but request at least one property
            "properties": ["email"],
            "limit": 1
        }
        result = await self._make_request("POST", endpoint, json_data=payload)
        if result.status == "success" and result.details.get("total", 0) > 0:
            contact_id = result.details["results"][0]["id"]
            logfire.info(f"Found existing HubSpot contact by email.",
                         email=email, contact_id=contact_id)
            return contact_id
        logfire.info("No existing HubSpot contact found by email.", email=email)
        return None

    async def create_or_update_contact(self, contact_data: HubSpotContactProperties) -> HubSpotApiResult:
        """
        Creates a new contact or updates an existing one based on email.
        Returns HubSpotApiResult consistently.
        """
        if not contact_data.email:
            logfire.error("Cannot create/update HubSpot contact without email.")
            return HubSpotApiResult(
                status="error",
                entity_type="contact",
                message="Email is required to create or update contact.",
                hubspot_id=None
            )

        existing_contact_id = await self.search_contact_by_email(contact_data.email)
        # Use mode='json' to ensure HttpUrl etc. are serialized to strings
        properties_payload = contact_data.model_dump(
            mode='json', by_alias=True, exclude_none=True)

        if existing_contact_id:
            # Update existing contact
            logfire.info("Updating existing HubSpot contact.",
                         contact_id=existing_contact_id, email=contact_data.email)
            endpoint = f"/crm/v3/objects/contacts/{existing_contact_id}"
            payload = {"properties": properties_payload}
            result = await self._make_request("PATCH", endpoint, json_data=payload)
            if result.status == "success":
                return HubSpotApiResult(
                    status="success",
                    entity_type="contact",
                    message="Contact updated successfully.",
                    hubspot_id=existing_contact_id,
                    details=result.details
                )
            else:
                return HubSpotApiResult(
                    status="error",
                    entity_type="contact",
                    message=f"Failed to update contact: {result.message}",
                    details=result.details,
                    hubspot_id=existing_contact_id
                )
        else:
            # Create new contact
            logfire.info("Creating new HubSpot contact.", email=contact_data.email)
            endpoint = "/crm/v3/objects/contacts"
            payload = {"properties": properties_payload}
            result = await self._make_request("POST", endpoint, json_data=payload)
            if result.status == "success":
                new_contact_id = result.details.get("id")
                return HubSpotApiResult(
                    status="success",
                    entity_type="contact",
                    message="Contact created successfully.",
                    hubspot_id=new_contact_id,
                    details=result.details
                )
            else:
                return HubSpotApiResult(
                    status="error",
                    entity_type="contact",
                    message=f"Failed to create contact: {result.message}",
                    details=result.details,
                    hubspot_id=None
                )

    # --- New Company Methods ---
    async def search_company_by_domain(self, domain: str) -> Optional[str]:
        """Searches for a company by domain and returns its HubSpot ID if found."""
        endpoint = "/crm/v3/objects/companies/search"
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "domain",
                            "operator": "EQ",
                            "value": domain
                        }
                    ]
                }
            ],
            "properties": ["domain", "name"], # Request basic properties
            "limit": 1
        }
        logfire.info(f"Searching for HubSpot company by domain: {domain}")
        result = await self._make_request("POST", endpoint, json_data=payload)
        if result.status == "success" and result.details and result.details.get("total", 0) > 0:
            company_id = result.details["results"][0]["id"]
            company_name = result.details["results"][0].get("properties", {}).get("name", "N/A")
            logfire.info(f"Found existing HubSpot company by domain.",
                         domain=domain, company_id=company_id, company_name=company_name)
            return company_id
        logfire.info("No existing HubSpot company found by domain.", domain=domain)
        return None

    async def create_or_update_company(self, company_data: HubSpotCompanyProperties) -> HubSpotApiResult:
        """
        Creates a new company or updates an existing one based on domain.
        Returns HubSpotApiResult consistently.
        """
        if not company_data.domain:
            logfire.warn("Cannot create/update HubSpot company without domain.")
            return HubSpotApiResult(
                status="error",
                entity_type="company",
                message="Domain is required to create or update company.",
                hubspot_id=None
            )

        existing_company_id = await self.search_company_by_domain(company_data.domain)
        # Use mode='json' for potential future complex types
        properties_payload = company_data.model_dump(
            mode='json', by_alias=True, exclude_none=True)
        
        # Ensure name is set if missing, default to domain
        if not properties_payload.get('name'):
            properties_payload['name'] = company_data.domain
            logfire.debug("Company name missing, defaulting to domain.", domain=company_data.domain)

        if existing_company_id:
            # Update existing company (optional - might just return ID)
            logfire.info("Found existing HubSpot company, returning ID.",
                         company_id=existing_company_id, domain=company_data.domain)
            # Optionally update properties if needed, for now just return success with ID
            # endpoint = f"/crm/v3/objects/companies/{existing_company_id}"
            # payload = {"properties": properties_payload}
            # update_result = await self._make_request("PATCH", endpoint, json_data=payload)
            # For now, just confirm existence is sufficient
            return HubSpotApiResult(
                status="success", # Indicate found/no update needed
                entity_type="company",
                message="Company already exists.",
                hubspot_id=existing_company_id,
                details={"properties": properties_payload} # Return intended props
            )
        else:
            # Create new company
            logfire.info("Creating new HubSpot company.", domain=company_data.domain, name=properties_payload['name'])
            endpoint = "/crm/v3/objects/companies"
            payload = {"properties": properties_payload}
            result = await self._make_request("POST", endpoint, json_data=payload)
            if result.status == "success":
                new_company_id = result.details.get("id")
                return HubSpotApiResult(
                    status="success",
                    entity_type="company",
                    message="Company created successfully.",
                    hubspot_id=new_company_id,
                    details=result.details
                )
            else:
                return HubSpotApiResult(
                    status="error",
                    entity_type="company",
                    message=f"Failed to create company: {result.message}",
                    details=result.details,
                    hubspot_id=None
                )

    async def associate_contact_to_company(self, contact_id: str, company_id: str) -> HubSpotApiResult:
        """Associates an existing contact with an existing company."""
        # Association: Contact -> Company (Primary)
        # Verify associationTypeId (e.g., 1 for Contact to Company Primary)
        association_type_id = 1 
        endpoint = f"/crm/v3/objects/contacts/{contact_id}/associations/company/{company_id}/{association_type_id}"
        logfire.info("Associating contact to company.", contact_id=contact_id, company_id=company_id, type_id=association_type_id)
        result = await self._make_request("PUT", endpoint) # PUT request with no body

        if result.status == "success":
            logfire.info("Successfully associated contact to company.", contact_id=contact_id, company_id=company_id)
            return HubSpotApiResult(
                status="success",
                entity_type="association",
                message="Contact associated to company successfully.",
                details=result.details
            )
        else:
            # Handle potential 404 if contact/company doesn't exist, or other errors
            logfire.error("Failed to associate contact to company.", 
                          contact_id=contact_id, company_id=company_id, 
                          error=result.message, details=result.details)
            return HubSpotApiResult(
                status="error",
                entity_type="association",
                message=f"Failed to associate contact {contact_id} to company {company_id}: {result.message}",
                details=result.details
            )
    # --- End New Company Methods ---

    async def create_lead(self, lead_data: HubSpotLeadProperties, 
                        associated_contact_id: Optional[str] = None, 
                        associated_company_id: Optional[str] = None) -> HubSpotApiResult:
        """
        Creates a new lead in HubSpot and optionally associates it with a contact and/or company.
        Requires at least one association (contact or company) based on HubSpot API rules.
        Returns HubSpotApiResult.
        """
        logfire.info("Creating new HubSpot lead.", 
                     lead_properties=lead_data.model_dump(exclude_none=True),
                     contact_id=associated_contact_id,
                     company_id=associated_company_id)
        
        # Check if at least one association ID is provided
        if not associated_contact_id and not associated_company_id:
            logfire.error("Lead creation requires at least one association (Contact ID or Company ID).", 
                          lead_properties=lead_data.model_dump(exclude_none=True))
            return HubSpotApiResult(
                status="error",
                entity_type="lead",
                message="Lead creation requires associating with a primary contact or company.",
                hubspot_id=None
            )

        endpoint = "/crm/v3/objects/leads"
        properties_dict = lead_data.model_dump(mode='json', by_alias=True, exclude_none=True)
        payload: Dict[str, Any] = {
            "properties": properties_dict,
            "associations": [] # Initialize empty list
        }

        # Add Contact Association if provided
        if associated_contact_id:
            contact_association = {
                "to": {"id": associated_contact_id},
                "types": [
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 578 # ID 578 = Lead to primary contact
                    }
                ]
            }
            payload["associations"].append(contact_association)
            logfire.info("Adding association to contact for new lead.", contact_id=associated_contact_id, type_id=578)

        # Add Company Association if provided
        if associated_company_id:
            company_association = {
                "to": {"id": associated_company_id},
                "types": [
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 610 # ID 610 = Lead to Company
                    }
                ]
            }
            payload["associations"].append(company_association)
            logfire.info("Adding association to company for new lead.", company_id=associated_company_id, type_id=610)

        result = await self._make_request("POST", endpoint, json_data=payload)

        if result.status == "success":
            lead_id = result.details.get("id")
            logfire.info("HubSpot lead created successfully.", lead_id=lead_id)
            # Return HubSpotApiResult for consistency
            return HubSpotApiResult(
                status="success",
                entity_type="lead",
                message="Lead created successfully.",
                hubspot_id=lead_id,
                details=result.details # Include full response details
            )
        else:
            logfire.error("Failed to create HubSpot lead.",
                          error=result.message,
                          details=result.details,
                          payload=payload
                          )
            return HubSpotApiResult(
                status="error",
                entity_type="lead",
                message=f"Failed to create lead: {result.message}",
                details=result.details,
                hubspot_id=None
            )

    async def get_contact_by_id(self, contact_id: str) -> HubSpotApiResult:
        """Fetches a contact by its HubSpot ID. Returns HubSpotApiResult."""
        logfire.info(f"Fetching HubSpot contact by ID: {contact_id}")
        endpoint = f"/crm/v3/objects/contacts/{contact_id}"
        # Specify properties you want to retrieve
        prop_list = list(HubSpotContactProperties.model_fields.keys())
        params = {"properties": ",".join(prop_list)}
        result = await self._make_request("GET", endpoint, params=params)

        if result.status == "success":
            return HubSpotApiResult(
                status="success",
                entity_type="contact",
                message="Contact fetched successfully.",
                hubspot_id=result.details.get("id"),
                details=result.details
            )
        else:
            return HubSpotApiResult(
                status="error",
                entity_type="contact",
                message=f"Failed to fetch contact {contact_id}: {result.message}",
                details=result.details,
                hubspot_id=contact_id
            )

    async def get_lead_by_id(self, lead_id: str) -> HubSpotApiResult:
        """Fetches a lead by its HubSpot ID. Returns HubSpotApiResult."""
        logfire.info(f"Fetching HubSpot lead by ID: {lead_id}")
        # Assuming 'leads' is the correct API name.
        endpoint = f"/crm/v3/objects/leads/{lead_id}"
        # Specify properties you want to retrieve
        prop_list = list(HubSpotLeadProperties.model_fields.keys())
        params = {"properties": ",".join(prop_list)}
        result = await self._make_request("GET", endpoint, params=params)

        if result.status == "success":
            return HubSpotApiResult(
                status="success",
                entity_type="lead",
                message="Lead fetched successfully.",
                hubspot_id=result.details.get("id"),
                details=result.details
            )
        else:
            return HubSpotApiResult(
                status="error",
                entity_type="lead",
                message=f"Failed to fetch lead {lead_id}: {result.message}",
                details=result.details,
                hubspot_id=lead_id
            )

    async def update_lead_properties(self, lead_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
        """Updates specific properties of an existing lead."""
        logfire.info(
            f"Updating properties for lead {lead_id}.", properties=properties)
        # Assuming 'leads' is the correct API name.
        endpoint = f"/crm/v3/objects/leads/{lead_id}"
        # Ensure properties are JSON serializable (though input is dict, good practice)
        # Pydantic model not used directly here, but ensure values are basic types
        payload = {"properties": properties} 
        result = await self._make_request("PATCH", endpoint, json_data=payload)

        if result.status == "success":
            logfire.info(f"Lead {lead_id} properties updated successfully.")
            # Return the generic result
            return HubSpotApiResult(
                status="success",
                entity_type="lead",
                message="Lead properties updated successfully.",
                hubspot_id=lead_id,
                details=result.details
            )
        else:
            logfire.error(
                f"Failed to update properties for lead {lead_id}.", error=result.message, details=result.details)
            return HubSpotApiResult(
                status="error",
                entity_type="lead",
                message=f"Failed to update lead properties: {result.message}",
                details=result.details,
                hubspot_id=lead_id
            )

    # Added function to update contact properties
    async def update_contact_properties(self, contact_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
        """Updates specific properties of an existing contact."""
        logfire.info(
            f"Updating properties for contact {contact_id}.", properties=properties)
        endpoint = f"/crm/v3/objects/contacts/{contact_id}"
        # Ensure properties are JSON serializable
        payload = {"properties": properties}
        result = await self._make_request("PATCH", endpoint, json_data=payload)

        if result.status == "success":
            logfire.info(f"Contact {contact_id} properties updated successfully.")
            return HubSpotApiResult(
                status="success",
                entity_type="contact",
                message="Contact properties updated successfully.",
                hubspot_id=contact_id,
                details=result.details
            )
        else:
            logfire.error(
                f"Failed to update properties for contact {contact_id}.", error=result.message, details=result.details)
            return HubSpotApiResult(
                status="error",
                entity_type="contact",
                message=f"Failed to update contact properties: {result.message}",
                details=result.details,
                hubspot_id=contact_id
            )

    # --- ID Lookup Methods ---
    async def get_pipeline_id(self, pipeline_name: str, object_type: str = "deals") -> Optional[str]:
        """Fetches the ID of a pipeline by its name. (Usually for Deals/Tickets)"""
        endpoint = f"/crm/v3/pipelines/{object_type}"
        logfire.info(
            f"Fetching {object_type} pipelines to find ID for '{pipeline_name}'.")
        result = await self._make_request("GET", endpoint)

        if result.status == "success" and "results" in result.details:
            for pipeline in result.details["results"]:
                if pipeline.get("label", "").lower() == pipeline_name.lower():
                    pipeline_id = pipeline.get("id")
                    logfire.info(f"Found pipeline ID.",
                                 name=pipeline_name, id=pipeline_id)
                    return pipeline_id
            logfire.warn(f"Pipeline not found by name.", name=pipeline_name, object_type=object_type)
            return None
        else:
            logfire.error(f"Failed to fetch {object_type} pipelines from HubSpot.",
                          error=result.message)
            return None

    async def get_stage_id(self, pipeline_id: str, stage_name: str, object_type: str = "deals") -> Optional[str]:
        """Fetches the ID of a stage within a specific pipeline by its name. (Usually for Deals/Tickets)"""
        endpoint = f"/crm/v3/pipelines/{object_type}/{pipeline_id}/stages"
        logfire.info(
            f"Fetching stages for pipeline {pipeline_id} ({object_type}) to find ID for stage '{stage_name}'.")
        result = await self._make_request("GET", endpoint)

        if result.status == "success" and "results" in result.details:
            for stage in result.details["results"]:
                if stage.get("label", "").lower() == stage_name.lower():
                    stage_id = stage.get("id")
                    logfire.info(f"Found stage ID.", pipeline_id=pipeline_id,
                                 name=stage_name, id=stage_id)
                    return stage_id
            logfire.warn(f"Stage not found by name in pipeline.",
                         name=stage_name, pipeline_id=pipeline_id, object_type=object_type)
            return None
        else:
            logfire.error(
                f"Failed to fetch stages for pipeline {pipeline_id} ({object_type}) from HubSpot.", error=result.message)
            return None

    async def get_owners(self, email: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetches owners (users) from HubSpot, optionally filtering by email."""
        endpoint = "/crm/v3/owners/"
        params = {"limit": limit}
        if email:
            params["email"] = email
        logfire.info("Fetching owners from HubSpot.", params=params)
        result = await self._make_request("GET", endpoint, params=params)

        if result.status == "success" and "results" in result.details:
            owners = result.details["results"]
            logfire.info(f"Fetched {len(owners)} owners from HubSpot.")
            return owners
        else:
            logfire.error("Failed to fetch owners from HubSpot.",
                          error=result.message)
            return []

    async def _update_owner_list_if_needed(self):
        """Fetches owners from HubSpot and updates the internal list and iterator if cache expired."""
        now = asyncio.get_event_loop().time()
        if not self._owner_list or not self._owners_last_fetched or (now - self._owners_last_fetched > self._owner_cache_ttl):
            logfire.info("Fetching or refreshing HubSpot owners for round-robin.")
            fetched_owners = await self.get_owners()
            # Filter out owners without an ID or potentially inactive ones if possible
            self._owner_list = [owner for owner in fetched_owners if owner.get("id")]
            if self._owner_list:
                self._owner_iterator = itertools.cycle(self._owner_list)
                self._owners_last_fetched = now
                logfire.info(
                    f"Initialized round-robin with {len(self._owner_list)} owners.")
            else:
                logfire.warn("No valid owners found to initialize round-robin.")
                self._owner_iterator = None
        else:
            logfire.debug("Using cached owner list for round-robin.")

    async def get_next_owner_id(self, team_name: Optional[str] = None) -> Optional[str]:
        """
        Gets the next owner ID using a simple in-memory round-robin.
        NOTE: In-memory state is not suitable for production. Filtering by team_name is not implemented.
        """
        async with self._owner_lock:  # Ensure atomic update of iterator
            await self._update_owner_list_if_needed()

            if not self._owner_iterator:
                logfire.error(
                    "Owner iterator not initialized, cannot assign next owner.")
                return None

            # TODO: Implement filtering by team_name if required.
            # This would involve fetching teams, finding the team ID, fetching team members,
            # and filtering the self._owner_list before creating the cycle.
            if team_name:
                logfire.warn(
                    "Filtering owners by team_name is not implemented in get_next_owner_id.")

            try:
                next_owner = next(self._owner_iterator)
                owner_id = next_owner.get("id")
                logfire.info(f"Assigned next owner via round-robin.",
                             owner_id=owner_id, owner_email=next_owner.get("email"))
                return owner_id
            except StopIteration:
                logfire.error("Owner iterator unexpectedly empty.")
                return None
            except Exception as e:
                logfire.error("Error getting next owner from iterator.", exc_info=True)
                return None


# Create a singleton instance of the manager
# Ensure settings are loaded before this is instantiated
hubspot_manager = HubSpotManager(api_key=settings.HUBSPOT_API_KEY)
