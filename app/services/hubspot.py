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
    HubSpotDealInput,
    HubSpotDealResult,
    HubSpotApiResult,
    HubSpotContactProperties,  # Import the properties models
    HubSpotDealProperties
)
from app.models.classification import ClassificationOutput  # Needed for deal creation
from app.core.config import settings


class HubSpotManager:
  """
  Manages interactions with the HubSpot API.
  Handles creating/updating contacts and deals.
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

  async def create_or_update_contact(self, contact_data: HubSpotContactProperties) -> HubSpotContactResult:
    """
    Creates a new contact or updates an existing one based on email.
    Returns HubSpotContactResult consistently.
    """
    if not contact_data.email:
      logfire.error("Cannot create/update HubSpot contact without email.")
      return HubSpotContactResult(
          status="error",
          message="Email is required to create or update contact.",
          id="",
          properties={}
      )

    existing_contact_id = await self.search_contact_by_email(contact_data.email)
    properties_payload = contact_data.model_dump(
        by_alias=True, exclude_none=True)

    if existing_contact_id:
      # Update existing contact
      logfire.info("Updating existing HubSpot contact.",
                   contact_id=existing_contact_id, email=contact_data.email)
      endpoint = f"/crm/v3/objects/contacts/{existing_contact_id}"
      payload = {"properties": properties_payload}
      result = await self._make_request("PATCH", endpoint, json_data=payload)
      if result.status == "success":
        return HubSpotContactResult(
            status="success",
            message="Contact updated successfully.",
            id=existing_contact_id,  # Use the existing ID
            properties=result.details.get("properties", {})
        )
      else:
        # Return HubSpotContactResult on error
        return HubSpotContactResult(
            status="error",
            message=f"Failed to update contact: {result.message}",
            details=result.details,
            id=existing_contact_id  # Still include the ID we tried to update
        )
    else:
      # Create new contact
      logfire.info("Creating new HubSpot contact.", email=contact_data.email)
      endpoint = "/crm/v3/objects/contacts"
      payload = {"properties": properties_payload}
      result = await self._make_request("POST", endpoint, json_data=payload)
      if result.status == "success":
        new_contact_id = result.details.get("id")
        return HubSpotContactResult(
            status="success",
            message="Contact created successfully.",
            id=new_contact_id,
            properties=result.details.get("properties", {})
        )
      else:
        # Return HubSpotContactResult on error
        return HubSpotContactResult(
            status="error",
            message=f"Failed to create contact: {result.message}",
            details=result.details,
            id=None  # No ID was created
        )

  async def create_deal(self, deal_data: HubSpotDealProperties, associated_contact_id: Optional[str] = None) -> HubSpotDealResult:
    """
    Creates a new deal in HubSpot and optionally associates it with a contact.
    Returns HubSpotDealResult consistently.
    """
    logfire.info("Creating new HubSpot deal.", deal_name=deal_data.dealname)
    endpoint = "/crm/v3/objects/deals"
    payload: Dict[str, Any] = {
        "properties": deal_data.model_dump(by_alias=True, exclude_none=True)}

    if associated_contact_id:
      # Correct association structure for V3 API
      payload["associations"] = [
          {
              "to": {"id": associated_contact_id},
              "types": [
                  {
                      "associationCategory": "HUBSPOT_DEFINED",
                      # Verify this ID (3 = Deal to Contact) in your HubSpot instance
                      "associationTypeId": 3
                  }
              ]
          }
      ]

    result = await self._make_request("POST", endpoint, json_data=payload)

    if result.status == "success":
      deal_id = result.details.get("id")
      return HubSpotDealResult(
          status="success",
          message="Deal created successfully.",
          id=deal_id,
          properties=result.details.get("properties", {})
      )
    else:
      # Log both the error response and the payload that caused it
      logfire.error("Failed to create HubSpot deal.",
                    error=result.message,
                    details=result.details,
                    payload=payload  # Include the payload that caused the error
                    )
      # Return a different result type for error cases to avoid validation issues
      return HubSpotApiResult(
          status="error",
          entity_type="deal",
          message=f"Failed to create deal: {result.message}",
          details=result.details,
          hubspot_id=None  # No ID was created
      )

  async def get_contact_by_id(self, contact_id: str) -> HubSpotContactResult:
    """Fetches a contact by its HubSpot ID."""
    logfire.info(f"Fetching HubSpot contact by ID: {contact_id}")
    endpoint = f"/crm/v3/objects/contacts/{contact_id}"
    # Specify properties you want to retrieve, adjust as needed
    params = {"properties": ",".join(
        HubSpotContactProperties.model_fields.keys())}
    result = await self._make_request("GET", endpoint, params=params)

    if result.status == "success":
      return HubSpotContactResult(
          status="success",
          message="Contact fetched successfully.",
          id=result.details.get("id"),
          properties=result.details.get("properties", {})
      )
    else:
      return HubSpotContactResult(
          status="error",
          message=f"Failed to fetch contact {contact_id}: {result.message}",
          details=result.details,
          id=contact_id
      )

  async def get_deal_by_id(self, deal_id: str) -> HubSpotDealResult:
    """Fetches a deal by its HubSpot ID."""
    logfire.info(f"Fetching HubSpot deal by ID: {deal_id}")
    endpoint = f"/crm/v3/objects/deals/{deal_id}"
    # Specify properties you want to retrieve, adjust as needed
    params = {"properties": ",".join(
        HubSpotDealProperties.model_fields.keys())}
    result = await self._make_request("GET", endpoint, params=params)

    if result.status == "success":
      return HubSpotDealResult(
          status="success",
          message="Deal fetched successfully.",
          id=result.details.get("id"),
          properties=result.details.get("properties", {})
      )
    else:
      # Return HubSpotApiResult for error to avoid validation issues if ID is missing
      return HubSpotApiResult(
          status="error",
          entity_type="deal",
          message=f"Failed to fetch deal {deal_id}: {result.message}",
          details=result.details,
          hubspot_id=deal_id
      )

  async def update_deal_properties(self, deal_id: str, properties: Dict[str, Any]) -> HubSpotApiResult:
    """Updates specific properties of an existing deal."""
    logfire.info(
        f"Updating properties for deal {deal_id}.", properties=properties)
    endpoint = f"/crm/v3/objects/deals/{deal_id}"
    payload = {"properties": properties}
    result = await self._make_request("PATCH", endpoint, json_data=payload)

    if result.status == "success":
      logfire.info(f"Deal {deal_id} properties updated successfully.")
    else:
      logfire.error(
          f"Failed to update properties for deal {deal_id}.", error=result.message, details=result.details)

    return result

  async def update_deal_pipeline_and_owner(self, deal_id: str, pipeline_id: str, stage_id: str, owner_id: Optional[str] = None) -> HubSpotApiResult:
    """
    Updates the pipeline, stage, and optionally the owner of a deal.
    NOTE: Requires knowing the internal IDs for pipeline, stage, and owner.
    Owner assignment might need more complex logic (round-robin). This is basic.
    """
    logfire.info(f"Updating pipeline/stage/owner for deal {deal_id}.",
                 pipeline=pipeline_id, stage=stage_id, owner=owner_id)
    endpoint = f"/crm/v3/objects/deals/{deal_id}"
    properties_to_update: Dict[str, Any] = {
        "pipeline": pipeline_id,
        "dealstage": stage_id
    }
    if owner_id:
      properties_to_update["hubspot_owner_id"] = owner_id

    payload = {"properties": properties_to_update}
    result = await self._make_request("PATCH", endpoint, json_data=payload)

    if result.status == "success":
      logfire.info(
          f"Deal {deal_id} pipeline/stage/owner updated successfully.")
    else:
      logfire.error(
          f"Failed to update pipeline/stage/owner for deal {deal_id}.", error=result.message)

    return result

  # --- ID Lookup Methods ---
  async def get_pipeline_id(self, pipeline_name: str, object_type: str = "deals") -> Optional[str]:
    """Fetches the ID of a pipeline by its name."""
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
      logfire.warn(f"Pipeline not found by name.", name=pipeline_name)
      return None
    else:
      logfire.error("Failed to fetch pipelines from HubSpot.",
                    error=result.message)
      return None

  async def get_stage_id(self, pipeline_id: str, stage_name: str, object_type: str = "deals") -> Optional[str]:
    """Fetches the ID of a stage within a specific pipeline by its name."""
    endpoint = f"/crm/v3/pipelines/{object_type}/{pipeline_id}/stages"
    logfire.info(
        f"Fetching stages for pipeline {pipeline_id} to find ID for stage '{stage_name}'.")
    result = await self._make_request("GET", endpoint)

    if result.status == "success" and "results" in result.details:
      for stage in result.details["results"]:
        if stage.get("label", "").lower() == stage_name.lower():
          stage_id = stage.get("id")
          logfire.info(f"Found stage ID.", pipeline_id=pipeline_id,
                       name=stage_name, id=stage_id)
          return stage_id
      logfire.warn(f"Stage not found by name in pipeline.",
                   name=stage_name, pipeline_id=pipeline_id)
      return None
    else:
      logfire.error(
          f"Failed to fetch stages for pipeline {pipeline_id} from HubSpot.", error=result.message)
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
