"""Pathway and tool synchronization logic."""

import logfire
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks
from app.models.bland import BlandApiResult
from app.services.mongo import MongoService
from app.core.config import settings
from ..config import prepare_tool_json_data
from ..api import BlandApiClient


class BlandSyncManager:
  """Manages synchronization of pathways and tools with Bland AI."""

  def __init__(
      self,
      api_client: BlandApiClient,
      pathway_definition: Dict[str, Any],
      location_tool_definition: Dict[str, Any],
      quote_tool_definition: Dict[str, Any],
      pathway_id: Optional[str] = None,
      mongo_service: Optional[MongoService] = None,
      background_tasks: Optional[BackgroundTasks] = None,
  ):
    self.api_client = api_client
    self.pathway_definition = pathway_definition
    self.location_tool_definition = location_tool_definition
    self.quote_tool_definition = quote_tool_definition
    self.pathway_id = pathway_id
    self.location_tool_id = settings.BLAND_LOCATION_TOOL_ID
    self.quote_tool_id = settings.BLAND_QUOTE_TOOL_ID
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks

  async def validate_pathway_config(self) -> bool:
    """
    Validates the pathway configuration.
    Returns True if the configuration is valid, False otherwise.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    if not self.pathway_id:
      logfire.error(
          "Pathway: sync skipped: BLAND_PATHWAY_ID is not configured in settings."
      )
      if self.mongo_service:  # mongo_service is from self
        error_details_config = {
            "service_name": "BlandSyncManager.validate_pathway_config",
            "error_type": "ConfigurationError",
            "message": "Pathway: sync skipped: BLAND_PATHWAY_ID is not configured.",
            "details": {"pathway_id_configured": self.pathway_id},
        }
        # BackgroundTasks not used here for logging config errors, direct await
        await self.mongo_service.log_error_to_db(**error_details_config)
      return False

    if not self.pathway_definition:
      logfire.error(
          f"Pathway: sync failed for {self.pathway_id}: Definition not loaded from call.json."
      )
      if self.mongo_service:  # mongo_service is from self
        error_details_def = {
            "service_name": "BlandSyncManager.validate_pathway_config",
            "error_type": "PathwayDefinitionError",
            "message": f"Pathway: sync failed for {self.pathway_id}: Definition not loaded from call.json.",
            "details": {
                "pathway_id": self.pathway_id,
            },
        }
        await self.mongo_service.log_error_to_db(**error_details_def)
      return False

    pathway_name = self.pathway_definition.get("name")
    if not pathway_name:
      logfire.error(
          f"Pathway: sync failed for {self.pathway_id}: 'name' field missing in call.json."
      )
      if self.mongo_service:  # mongo_service is from self
        error_details_name = {
            "service_name": "BlandSyncManager.validate_pathway_config",
            "error_type": "PathwayDefinitionError",
            "message": f"Pathway: sync failed for {self.pathway_id}: 'name' field missing in call.json.",
            "details": {
                "pathway_id": self.pathway_id,
                "pathway_definition_keys": list(self.pathway_definition.keys()),
            },
        }
        await self.mongo_service.log_error_to_db(**error_details_name)
      return False

    return True

  async def update_pathway_component(self, component_type: str, component_data: Dict[str, Any]) -> BlandApiResult:
    """
    Updates a pathway component (nodes or edges) using the Bland API.
    Returns the API result.
    """
    logfire.info(
        f"Pathway: Attempting to update pathway {component_type} {self.pathway_id} using POST /v1/pathway/{{pathway_id}}"
    )
    endpoint = f"/v1/pathway/{self.pathway_id}"

    logfire.info(
        f"Pathway: Sending update payload for {self.pathway_id}", payload=component_data
    )

    update_result = await self.api_client.make_request(
        "POST",
        endpoint,
        json_data=component_data,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks
    )

    if update_result.status == "success":
      logfire.info(
          f"Pathway: sync successful: Updated existing pathway {self.pathway_id}: {component_type}"
      )
    else:
      logfire.error(
          f"Pathway: sync failed: Could not update pathway {component_type} {self.pathway_id}. Bland API Message: {update_result.message}",
          details=update_result,
      )

    return update_result

  async def sync_pathway_nodes(self) -> None:
    """
    Attempts to update the configured pathway using the definition from call.json.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    logfire.info("Pathway: Starting pathway Nodes synchronization check...")

    if not await self.validate_pathway_config():
      return

    update_payload = {
        "name": self.pathway_definition.get("name"),
        "description": self.pathway_definition.get("description"),
        "nodes": self.pathway_definition.get("nodes", []),
    }

    await self.update_pathway_component("nodes", update_payload)

  async def sync_pathway_edges(self) -> None:
    """
    Attempts to update the configured pathway using the definition from call.json.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    logfire.info("Pathway: Starting pathway edges synchronization check...")

    if not await self.validate_pathway_config():
      return

    update_payload = {
        "name": self.pathway_definition.get("name"),
        "description": self.pathway_definition.get("description"),
        "edges": self.pathway_definition.get("edges", []),
    }

    await self.update_pathway_component("edges", update_payload)

  async def validate_tool_definition(self, tool_type: str, tool_definition: Dict[str, Any], tool_id: str, json_path: str) -> bool:
    """
    Validates a tool definition.
    Returns True if the definition is valid, False otherwise.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    if not tool_definition:
      logfire.error(
          f"Pathway: {tool_type} tool sync failed: Definition not loaded from {json_path}.")
      if self.mongo_service:
        error_details = {
            "service_name": f"BlandSyncManager.validate_tool_definition",
            "error_type": f"{tool_type}ToolDefinitionError",
            "message": f"{tool_type} tool sync failed: Definition not loaded from {json_path}.",
            "details": {f"{tool_type.lower()}_json_path": json_path},
        }
        await self.mongo_service.log_error_to_db(**error_details)
      return False

    if not tool_id:
      logfire.error(
          f"Pathway: {tool_type} tool sync failed: Tool ID not configured.")
      if self.mongo_service:
        error_details = {
            "service_name": f"BlandSyncManager.validate_tool_definition",
            "error_type": f"{tool_type}ToolConfigError",
            "message": f"{tool_type} tool sync failed: Tool ID not configured.",
            "details": {f"{tool_type.lower()}_tool_id": tool_id},
        }
        await self.mongo_service.log_error_to_db(**error_details)
      return False

    return True

  async def update_tool(self, tool_type: str, tool_id: str, json_data: Dict[str, Any]) -> BlandApiResult:
    """
    Updates a tool using the Bland API.
    Returns the API result.
    """
    endpoint = f"/v1/tools/{tool_id}"

    update_result = await self.api_client.make_request(
        "POST",
        endpoint,
        json_data=json_data,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks
    )

    if update_result.status == "success":
      logfire.info(f"Pathway: {tool_type} tool sync successful.")
    else:
      logfire.error(
          f"Pathway: {tool_type} tool sync failed: {update_result.message}",
          details=update_result.details
      )

    return update_result

  async def sync_location_tool(self) -> None:
    """
    Attempts to update the location tool using the definition from location.json.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    logfire.info("Pathway: Starting location tool synchronization check...")

    if not self.location_tool_id:
      logfire.error("Location tool ID not configured.")
      return

    if not await self.validate_tool_definition(
        "Location",
        self.location_tool_definition,
        self.location_tool_id,
        "location.json"
    ):
      return

    json_data = prepare_tool_json_data(self.location_tool_definition)
    await self.update_tool("Location", self.location_tool_id, json_data)

  async def sync_quote_tool(self) -> None:
    """
    Attempts to update the quote tool using the definition from quote.json.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    logfire.info("Pathway: Starting quote tool synchronization check...")

    if not self.quote_tool_id:
      logfire.error("Quote tool ID not configured.")
      return

    if not await self.validate_tool_definition(
        "Quote",
        self.quote_tool_definition,
        self.quote_tool_id,
        "quote.json"
    ):
      return

    json_data = prepare_tool_json_data(self.quote_tool_definition)
    await self.update_tool("Quote", self.quote_tool_id, json_data)

  async def sync_all(self) -> None:
    """Synchronizes all Bland.ai definitions: pathway, location tool, and quote tool."""
    logfire.info(
        "Pathway: Starting synchronization of all Bland.ai definitions...")

    await self.sync_pathway_nodes()
    await self.sync_pathway_edges()
    await self.sync_location_tool()
    await self.sync_quote_tool()

    logfire.info(
        "Pathway: Completed synchronization of all Bland.ai definitions.")
