# app/services/bland.py

import httpx
import logfire
from typing import Dict, Any, Optional, List
import os
import json
from fastapi import BackgroundTasks
from datetime import datetime

# Import models
from app.models.bland import (
    BlandApiResult,
    BlandCallbackRequest,
    BlandWebhookPayload,
    BlandProcessingResult,
)
from app.models.blandlog import BlandCallStatus
from app.models.error import ErrorLog
from app.services.mongo.mongo import MongoService
from app.core.config import settings

# --- Bland AI Manager ---

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
PATHWAY_JSON_PATH = os.path.join(_PROJECT_ROOT, "app", "assets", "call.json")
LOCATION_TOOL_JSON_PATH = os.path.join(
    _PROJECT_ROOT, "app", "assets", "location.json")
QUOTE_TOOL_JSON_PATH = os.path.join(
    _PROJECT_ROOT, "app", "assets", "quote.json")


class BlandAIManager:
  """
  Manages interactions with the Bland.ai API.
  Handles pathway synchronization (creation if needed), initiating callbacks, and processing transcripts.
  Integrates with MongoService for call logging.
  """

  def __init__(
          self,
          api_key: str,
          base_url: str,
          pathway_id_setting: Optional[str] = None,
          mongo_service: Optional[MongoService] = None,
          background_tasks: Optional[BackgroundTasks] = None
  ):
    self.api_key = api_key
    self.base_url = base_url
    self.pathway_definition = self._load_pathway_definition()
    self.location_tool_definition = self._load_location_tool_definition()
    self.quote_tool_definition = self._load_quote_tool_definition()
    self.pathway_id = pathway_id_setting
    self.location_tool_id = settings.BLAND_LOCATION_TOOL_ID  # Use settings object
    self.quote_tool_id = settings.BLAND_QUOTE_TOOL_ID    # Use settings object
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks

    headers = {
        "Authorization": f"{self.api_key}",
        "Content-Type": "application/json",
    }
    self._client = httpx.AsyncClient(
        base_url=self.base_url, headers=headers, timeout=None  # Timeout removed
    )

  def _load_pathway_definition(self) -> Dict[str, Any]:
    """Loads the pathway definition from the JSON file."""
    try:
      with open(PATHWAY_JSON_PATH, "r") as f:
        pathway_data = json.load(f)
        logfire.info(
            f"Successfully loaded pathway definition from {PATHWAY_JSON_PATH}"
        )
        return pathway_data
    except FileNotFoundError:
      logfire.error(
          f"Pathway definition file not found at {PATHWAY_JSON_PATH}. Cannot sync pathway."
      )
      return {}
    except json.JSONDecodeError as e:
      logfire.error(
          f"Error decoding JSON from {PATHWAY_JSON_PATH}: {e}", exc_info=True
      )
      return {}
    except Exception as e:
      logfire.error(
          f"Error loading pathway definition from {PATHWAY_JSON_PATH}: {e}",
          exc_info=True,
      )
      return {}

  def _load_location_tool_definition(self) -> Dict[str, Any]:
    """Loads the location tool definition from the JSON file."""
    try:
      with open(LOCATION_TOOL_JSON_PATH, "r") as f:
        location_data = json.load(f)
        logfire.info(
            f"Successfully loaded location tool definition from {LOCATION_TOOL_JSON_PATH}"
        )
        return location_data
    except FileNotFoundError:
      logfire.error(
          f"Location tool definition file not found at {LOCATION_TOOL_JSON_PATH}. Cannot load location tool."
      )
      return {}
    except json.JSONDecodeError as e:
      logfire.error(
          f"Error decoding JSON from {LOCATION_TOOL_JSON_PATH}: {e}", exc_info=True
      )
      return {}
    except Exception as e:
      logfire.error(
          f"Error loading location tool definition from {LOCATION_TOOL_JSON_PATH}: {e}",
          exc_info=True,
      )
      return {}

  def _load_quote_tool_definition(self) -> Dict[str, Any]:
    """Loads the quote tool definition from the JSON file."""
    try:
      with open(QUOTE_TOOL_JSON_PATH, "r") as f:
        quote_data = json.load(f)
        logfire.info(
            f"Successfully loaded quote tool definition from {QUOTE_TOOL_JSON_PATH}"
        )
        return quote_data
    except FileNotFoundError:
      logfire.error(
          f"Quote tool definition file not found at {QUOTE_TOOL_JSON_PATH}. Cannot load quote tool."
      )
      return {}
    except json.JSONDecodeError as e:
      logfire.error(
          f"Error decoding JSON from {QUOTE_TOOL_JSON_PATH}: {e}", exc_info=True
      )
      return {}
    except Exception as e:
      logfire.error(
          f"Error loading quote tool definition from {QUOTE_TOOL_JSON_PATH}: {e}",
          exc_info=True,
      )
      return {}

  async def _sync_pathway(self) -> None:
    """
    Attempts to update the configured pathway using the definition from call.json.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    logfire.info("Starting pathway synchronization check...")

    if not self.pathway_id:
      logfire.error(
          "Pathway sync skipped: BLAND_PATHWAY_ID is not configured in settings."
      )
      if self.mongo_service:
        error_details_config = {
            "service_name": "BlandAIManager._sync_pathway",
            "error_type": "ConfigurationError",
            "message": "Pathway sync skipped: BLAND_PATHWAY_ID is not configured.",
            "details": {"pathway_id_configured": self.pathway_id},
        }
        if self.background_tasks:
          self.background_tasks.add_task(
              self.mongo_service.log_error_to_db, **error_details_config
          )
        else:
          await self.mongo_service.log_error_to_db(**error_details_config)
      return

    if not self.pathway_definition:
      logfire.error(
          f"Pathway sync failed for {self.pathway_id}: Definition not loaded from call.json."
      )
      if self.mongo_service:
        error_details_def = {
            "service_name": "BlandAIManager._sync_pathway",
            "error_type": "PathwayDefinitionError",
            "message": f"Pathway sync failed for {self.pathway_id}: Definition not loaded from call.json.",
            "details": {
                "pathway_id": self.pathway_id,
                "pathway_json_path": PATHWAY_JSON_PATH,
            },
        }
        if self.background_tasks:
          self.background_tasks.add_task(
              self.mongo_service.log_error_to_db, **error_details_def
          )
        else:
          await self.mongo_service.log_error_to_db(**error_details_def)
      return

    pathway_name = self.pathway_definition.get("name")
    if not pathway_name:
      logfire.error(
          f"Pathway sync failed for {self.pathway_id}: 'name' field missing in call.json."
      )
      if self.mongo_service:
        error_details_name = {
            "service_name": "BlandAIManager._sync_pathway",
            "error_type": "PathwayDefinitionError",
            "message": f"Pathway sync failed for {self.pathway_id}: 'name' field missing in call.json.",
            "details": {
                "pathway_id": self.pathway_id,
                "pathway_definition_keys": list(self.pathway_definition.keys()),
            },
        }
        if self.background_tasks:
          self.background_tasks.add_task(
              self.mongo_service.log_error_to_db, **error_details_name
          )
        else:
          await self.mongo_service.log_error_to_db(**error_details_name)
      return

    logfire.info(
        f"Attempting to update pathway {self.pathway_id} using POST /v1/pathway/{{pathway_id}}"
    )
    endpoint = f"/v1/pathway/{self.pathway_id}"

    update_payload = {
        "name": pathway_name,
        "description": self.pathway_definition.get("description"),
        "nodes": self.pathway_definition.get("nodes", []),
        "edges": self.pathway_definition.get("edges", []),
    }

    logfire.info(
        f"Sending update payload for {self.pathway_id}", payload=update_payload
    )

    update_result = await self._make_request(
        "POST",
        endpoint,
        json_data=update_payload,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
    )

    if update_result.status == "success":
      logfire.info(
          f"Pathway sync successful: Updated existing pathway {self.pathway_id}."
      )
    else:
      logfire.error(
          f"Pathway sync failed: Could not update pathway {self.pathway_id}. Bland API Message: {update_result.message}",
          details=update_result.details,
      )
      # Error already logged by _make_request if mongo_service was provided.

  async def _sync_location_tool(self) -> None:
    """
    Attempts to update the location tool using the definition from location.json.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    logfire.info("Starting location tool synchronization check...")

    if not self.location_tool_definition:
      logfire.error(
          "Location tool sync failed: Definition not loaded from location.json."
      )
      if self.mongo_service:
        error_details = {
            "service_name": "BlandAIManager._sync_location_tool",
            "error_type": "LocationToolDefinitionError",
            "message": "Location tool sync failed: Definition not loaded from location.json.",
            "details": {"location_json_path": LOCATION_TOOL_JSON_PATH},
        }
        if self.background_tasks:
          self.background_tasks.add_task(
              self.mongo_service.log_error_to_db, **error_details
          )
        else:
          await self.mongo_service.log_error_to_db(**error_details)
      return

    endpoint = f"/v1/tools/{self.location_tool_id}"
    logfire.info(
        f"Attempting to update location tool using POST {endpoint}",
        payload=self.location_tool_definition,
    )

    json_data = {
        "name": self.location_tool_definition.get("name"),
        "description": self.location_tool_definition.get("description"),
        "url": self.location_tool_definition.get("url"),
        "headers": self.location_tool_definition.get("headers", {}),
        "input_schema": self.location_tool_definition.get("input_schema", {}),
        "type": self.location_tool_definition.get("type", "object"),
        "properties": self.location_tool_definition.get("properties", {}),
        "required": self.location_tool_definition.get("required", []),
        "body": self.location_tool_definition.get("body", {}),
        "response": self.location_tool_definition.get("response", {}),
        "speech": self.location_tool_definition.get("speech", None),
        "timeout": self.location_tool_definition.get("timeout", 10000),
    }

    update_result = await self._make_request(
        "POST",
        endpoint,
        json_data=json_data,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
    )

    if update_result.status == "success":
      logfire.info("Location tool sync successful.")
    else:
      logfire.error(
          f"Location tool sync failed: {update_result.message}",
          details=update_result.details,
      )

  async def _sync_quote_tool(self) -> None:
    """
    Attempts to update the quote tool using the definition from quote.json.
    Logs errors to MongoDB if self.mongo_service is available.
    """
    logfire.info("Starting quote tool synchronization check...")

    if not self.quote_tool_definition:
      logfire.error(
          "Quote tool sync failed: Definition not loaded from quote.json."
      )
      if self.mongo_service:
        error_details = {
            "service_name": "BlandAIManager._sync_quote_tool",
            "error_type": "QuoteToolDefinitionError",
            "message": "Quote tool sync failed: Definition not loaded from quote.json.",
            "details": {"quote_json_path": QUOTE_TOOL_JSON_PATH},
        }
        if self.background_tasks:
          self.background_tasks.add_task(
              self.mongo_service.log_error_to_db, **error_details
          )
        else:
          await self.mongo_service.log_error_to_db(**error_details)
      return

    endpoint = f"/v1/tools/{self.quote_tool_id}"
    logfire.info(
        f"Attempting to update quote tool using POST {endpoint}",
        payload=self.quote_tool_definition,
    )

    json_data = {
        "name": self.quote_tool_definition.get("name"),
        "description": self.quote_tool_definition.get("description"),
        "url": self.quote_tool_definition.get("url"),
        "headers": self.quote_tool_definition.get("headers", {}),
        "input_schema": self.quote_tool_definition.get("input_schema", {}),
        "type": self.quote_tool_definition.get("type", "object"),
        "properties": self.quote_tool_definition.get("properties", {}),
        "required": self.quote_tool_definition.get("required", []),
        "body": self.quote_tool_definition.get("body", {}),
        "response": self.quote_tool_definition.get("response", {}),
        "speech": self.quote_tool_definition.get("speech", None),
        "timeout": self.quote_tool_definition.get("timeout", 10000),
    }

    update_result = await self._make_request(
        "POST",
        endpoint,
        json_data=json_data,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
    )

    if update_result.status == "success":
      logfire.info("Quote tool sync successful.")
    else:
      logfire.error(
          f"Quote tool sync failed: {update_result.message}",
          details=update_result.details,
      )

  async def _sync_bland(self) -> None:
    """Synchronizes all Bland.ai definitions: pathway, location tool, and quote tool."""
    logfire.info("Starting synchronization of all Bland.ai definitions...")
    await self._sync_pathway()
    await self._sync_location_tool()
    await self._sync_quote_tool()
    logfire.info("Completed synchronization of all Bland.ai definitions.")

  async def close(self):
    """Gracefully closes the HTTP client."""
    await self._client.aclose()
    logfire.info("BlandAI HTTP client closed.")

  async def check_connection(self) -> Dict[str, Any]:
    """
    Checks the connection to the Bland AI API by attempting to list pathways.
    Returns a dictionary with connection status and details.
    """
    logfire.info("Checking Bland AI API connection...")
    endpoint = "/v1/pathway"  # A simple endpoint to check connectivity
    result = {"status": "error",
              "message": "Connection check failed.", "details": None}

    try:
      api_response = await self._make_request(
          method="GET",
          endpoint=endpoint,
          mongo_service=None,  # No need to log to DB for a simple health check
          background_tasks=None
      )

      if api_response.status == "success":
        result["status"] = "success"
        result["message"] = "Bland AI API connection successful."
        # You could add more details from api_response.details if needed
        # For example, number of pathways or a snippet of the response.
        # For now, keeping it simple.
        logfire.info("Bland AI API connection successful.")
      else:
        result["message"] = f"Bland AI API connection failed: {api_response.message}"
        result["details"] = api_response.details
        logfire.error(
            f"Bland AI API connection failed: {api_response.message}", details=api_response.details)

    except Exception as e:
      logfire.error(
          f"Unexpected error during Bland AI connection check: {e}", exc_info=True)
      result["message"] = f"Unexpected error during connection check: {str(e)}"
      result["details"] = {"error_type": type(e).__name__, "args": e.args}

    return result

  async def _make_request(self, method: str, endpoint: str, json_data: Optional[Dict] = None, mongo_service: Optional[MongoService] = None,  background_tasks: Optional[BackgroundTasks] = None) -> BlandApiResult:
    """
    Helper method to make requests to the Bland API.
    Logs errors to MongoDB if mongo_service is provided.
    """
    url = f"{self.base_url.strip('/')}/{endpoint.lstrip('/')}"
    logfire.debug(
        f"Making Bland API request: {method} {url}", payload=json_data)
    try:
      response = await self._client.request(method, endpoint, json=json_data)
      response.raise_for_status()
      response_data = response.json()
      logfire.debug("Bland API request successful.", response=response_data)

      if isinstance(response_data, list):
        # Handle list response (e.g., for listing pathways)
        # The 'details' will be the list itself.
        # 'status' and 'message' can be generic success.
        status = "success"
        message = "Request successful, list of items returned."
        details = response_data
        call_id_from_bland = None  # No single call_id for a list
      elif isinstance(response_data, dict):
        # Handle dict response (e.g., for single call, pathway creation/update)
        status = response_data.get("status", "success")
        message = response_data.get("message", "Request successful")
        details = response_data
        call_id_from_bland = details.get("call_id")
      else:
        # Unexpected response type
        status = "error"
        message = "Unexpected response format from Bland API."
        details = {"raw_response": response_data}
        call_id_from_bland = None
        logfire.warn(
            f"Unexpected response format from Bland API: {type(response_data)}", response=response_data)

      return BlandApiResult(
          status=status,
          message=message,
          details=details,
          call_id=call_id_from_bland,
      )
    except httpx.HTTPStatusError as e:
      logfire.error(
          f"Bland API HTTP error: {e.response.status_code}",
          url=str(e.request.url),
          response=e.response.text,
      )
      message_content = f"HTTP error {e.response.status_code}: {e.response.text}"
      try:
        error_details_parsed = e.response.json()
      except Exception:
        error_details_parsed = {"raw_response": e.response.text}

      if mongo_service:
        log_db_payload = {
            "service_name": "BlandAIManager._make_request",
            "error_type": "HTTPStatusError",
            "message": message_content,
            "details": {
                "method": method,
                "endpoint": endpoint,
                "request_payload_keys": (
                            list(json_data.keys()) if json_data else None
                ),
                "status_code": e.response.status_code,
                "response_text": e.response.text,
                "error_details_parsed": error_details_parsed,
            },
        }
        if background_tasks:
          background_tasks.add_task(
              mongo_service.log_error_to_db, **log_db_payload
          )
        else:
          await mongo_service.log_error_to_db(**log_db_payload)
      return BlandApiResult(
          status="error", message=message_content, details=error_details_parsed
      )
    except httpx.RequestError as e:
      logfire.error(f"Bland API request error: {e}", url=str(e.request.url))
      message_content = f"Request failed: {e}"
      error_details_data = {
          "error_type": type(e).__name__,
          "request_url": str(e.request.url) if e.request else "N/A",
      }
      if mongo_service:
        log_db_payload_req = {
            "service_name": "BlandAIManager._make_request",
            "error_type": "RequestError",
            "message": message_content,
            "details": {
                "method": method,
                "endpoint": endpoint,
                "request_payload_keys": (
                            list(json_data.keys()) if json_data else None
                ),
                "error_details": error_details_data,
            },
        }
        if background_tasks:
          background_tasks.add_task(
              mongo_service.log_error_to_db, **log_db_payload_req
          )
        else:
          await mongo_service.log_error_to_db(**log_db_payload_req)
      return BlandApiResult(
          status="error", message=message_content, details=error_details_data
      )
    except Exception as e:
      logfire.error(
          f"Unexpected error during Bland API request: {e}", exc_info=True
      )
      message_content = f"An unexpected error occurred: {e}"
      error_details_unexp_data = {
          "error_type": type(e).__name__,
          "exception_args": e.args,
      }
      if mongo_service:
        log_db_payload_unexp = {
            "service_name": "BlandAIManager._make_request",
            "error_type": "UnexpectedException",
            "message": message_content,
            "details": {
                "method": method,
                "endpoint": endpoint,
                "request_payload_keys": (
                            list(json_data.keys()) if json_data else None
                ),
                "error_details": error_details_unexp_data,
            },
        }
        if background_tasks:
          background_tasks.add_task(
              mongo_service.log_error_to_db, **log_db_payload_unexp
          )
        else:
          await mongo_service.log_error_to_db(**log_db_payload_unexp)
      return BlandApiResult(
          status="error",
          message=message_content,
          details=error_details_unexp_data,
      )

  async def initiate_callback(
          self,
          request_data: BlandCallbackRequest,
          contact_id: str,
          log_retry_of_call_id: Optional[str] = None,
          log_retry_reason: Optional[str] = None,
  ) -> BlandApiResult:
    """
    Initiates a callback using the Bland.ai /v1/calls endpoint.
    Logs the attempt and result to MongoDB.
    The contact_id is added to the call's metadata.
    Prioritizes pathway_id over task if self.pathway_id is configured.
    """
    endpoint = "/v1/calls"

    # Start payload directly from the Pydantic model, using aliases and excluding None values.
    # Fields like 'request_data' or 'dynamic_data' will only be included if they are
    # non-None in the request_data object.
    payload = request_data.model_dump(by_alias=True, exclude_none=True)

    # Ensure 'request_data' is present in the payload, defaulting to an empty dict if not provided.
    payload.setdefault("request_data", {})

    # Ensure 'metadata' is present and includes the contact_id.
    # If 'metadata' was provided in request_data (and was a dict), its existing values are preserved.
    # If 'metadata' was not provided, it's initialized as an empty dict here before adding contact_id.
    metadata_in_payload = payload.setdefault("metadata", {})
    metadata_in_payload["contact_id"] = contact_id

    pathway_id_used_for_call: Optional[str] = None
    # Get initial task from payload, which came from request_data.task
    task_sent_to_bland: Optional[str] = payload.get("task")

    if self.pathway_id:
      payload["pathway_id"] = self.pathway_id
      pathway_id_used_for_call = self.pathway_id
      # If pathway_id is used, Bland API docs imply 'task' should not be specified or can interfere.
      payload.pop("task", None)
      task_sent_to_bland = None  # Task is not sent if pathway_id is used
      logfire.info(
          f"Using pathway_id: {self.pathway_id} for call to {request_data.phone_number} for contact_id: {contact_id}."
      )
    elif not task_sent_to_bland:  # No self.pathway_id and task is empty or not provided in request_data
      default_task = "Follow up with the lead regarding their recent inquiry and gather necessary details."
      payload["task"] = default_task
      task_sent_to_bland = default_task
      logfire.warn(
          f"No pathway_id configured and no task provided in request for contact_id: {contact_id}. Using default task: '{default_task}'"
      )
    else:  # No self.pathway_id, but task was provided in request_data
      # task_sent_to_bland is already set from payload.get("task")
      logfire.info(
          f"Using task from request_data for call to {request_data.phone_number} for contact_id: {contact_id} (no pathway_id configured)."
      )

    # Bland API expects webhook URL as a string
    if payload.get("webhook") is not None:
      payload["webhook"] = str(payload["webhook"])

    # Log call attempt (pre-API call)
    if self.background_tasks and self.mongo_service:
      self.background_tasks.add_task(
          self.mongo_service.log_bland_call_attempt,
          contact_id=contact_id,
          phone_number=request_data.phone_number,
          task=task_sent_to_bland,
          pathway_id_used=pathway_id_used_for_call,
          initial_status=BlandCallStatus.PENDING,
          call_id_bland=None,  # Not known yet
          retry_of_call_id=log_retry_of_call_id,
          retry_reason=log_retry_reason,
          # Use what's in payload, preferring 'voice'
          voice_id=payload.get("voice") or payload.get("voice_id"),
          webhook_url=str(
              request_data.webhook) if request_data.webhook else None
      )
    else:
      logfire.warn(
          "MongoService or BackgroundTasks not available for pre-call logging.",
          contact_id=contact_id,
          method="initiate_callback"
      )

    logfire.info(
        f"Initiating Bland callback for contact_id: {contact_id}",
        phone=request_data.phone_number,
        # Log sorted keys for consistency
        payload_keys=sorted(list(payload.keys()))
    )

    api_result = await self._make_request(
        "POST",
        endpoint,
        json_data=payload,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
    )

    # Log call result (post-API call)
    current_time = datetime.utcnow()
    if api_result.status == "error":
      logfire.error(
          f"Bland API call initiation failed for contact_id: {contact_id}. Error: {api_result.message}",
          details=api_result.details,
      )
      failure_update_data = {
          "$set": {
              "status": BlandCallStatus.FAILED.value,
              "error_message": api_result.message,
              "updated_at": current_time,
              "bland_error_details": api_result.details,
          }
      }
      if self.background_tasks and self.mongo_service:
        self.background_tasks.add_task(
            self.mongo_service.update_bland_call_log_internal,
            contact_id=contact_id,
            update_data=failure_update_data,
        )
      else:
        logfire.warn(
            "MongoService or BackgroundTasks not available for logging call failure.",
            contact_id=contact_id,
            method="initiate_callback"
        )
    elif api_result.call_id:  # Success and call_id is present
      logfire.info(
          f"Bland call initiated successfully for contact_id: {contact_id}. Bland Call ID: {api_result.call_id}"
      )
      success_init_update_data = {
          "$set": {
              "call_id_bland": api_result.call_id,
              # Call is initiated, pending completion/webhook
              "status": BlandCallStatus.PENDING.value,
              "updated_at": current_time,
              "error_message": None,  # Clear any previous error
          },
          # Clear previous error details
          "$unset": {"bland_error_details": ""},
      }
      if self.background_tasks and self.mongo_service:
        self.background_tasks.add_task(
            self.mongo_service.update_bland_call_log_internal,
            contact_id=contact_id,
            update_data=success_init_update_data,
        )
      else:
        logfire.warn(
            "MongoService or BackgroundTasks not available for logging call success.",
            contact_id=contact_id,
            method="initiate_callback"
        )
    # API call did not return 'error' status but also no call_id (unexpected)
    else:
      logfire.warn(
          f"Bland API call for contact_id: {contact_id} returned status '{api_result.status}' but no call_id. This may indicate an issue.",
          message=api_result.message,
          details=api_result.details,
          payload_sent_keys=sorted(list(payload.keys()))
      )
      # Consider if a specific DB status update is needed here, e.g., to an 'UNKNOWN' or 'FAILED_NO_CALL_ID' state.
      # For now, the log entry would remain in PENDING status from the initial log_bland_call_attempt.

    return api_result

  async def retry_call(
          self,
          contact_id: str,
          # mongo_service is passed but initiate_callback uses self.mongo_service
          mongo_service: MongoService,
          # background_tasks is passed but initiate_callback uses self.background_tasks
          background_tasks: BackgroundTasks,
          retry_reason: Optional[str] = "User initiated retry",
  ) -> BlandApiResult:
    """
    Retries a previously failed or problematic call.
    Fetches original call details from MongoDB, constructs a new call request,
    and initiates it via self.initiate_callback.
    """
    logfire.info(
        f"Attempting to retry call for contact_id: {contact_id} with reason: '{retry_reason}'"
    )
    # Ensure the BlandAIManager instance has mongo_service and background_tasks if they are to be used by initiate_callback
    # This is crucial if this retry_call method is invoked in a context where self.mongo_service
    # or self.background_tasks might not be the same as the ones passed here.
    # For now, assuming initiate_callback will use self.mongo_service and self.background_tasks which should be set.

    # Uses passed mongo_service for this fetch
    original_log_doc = await mongo_service.get_bland_call_log(contact_id)

    if not original_log_doc:
      logfire.error(
          f"Retry failed: Original call log not found for contact_id: {contact_id}"
      )
      # Log this specific error to general error logs using the passed background_tasks and mongo_service
      background_tasks.add_task(
          mongo_service.log_error_to_db,
          service_name="BlandAIManager.retry_call",
          error_type="NotFoundError",
          message="Original call log not found to retry.",
          details={"contact_id": contact_id, "retry_reason": retry_reason},
      )
      return BlandApiResult(
          status="error",
          message="Original call log not found to retry.",
          details={"contact_id": contact_id},
      )

    phone_number = original_log_doc.get("phone_number")
    if not phone_number:
      logfire.error(
          f"Retry failed: Original call log for contact_id: {contact_id} is missing phone number."
      )
      background_tasks.add_task(
          mongo_service.log_error_to_db,
          service_name="BlandAIManager.retry_call",
          error_type="DataValidationError",
          message="Original call log missing phone number.",
          details={
              "contact_id": contact_id,
              "original_log_doc_id": str(original_log_doc.get("_id")),
          },
      )
      return BlandApiResult(
          status="error",
          message="Original call log missing phone number.",
          details={"contact_id": contact_id},
      )

    task_for_retry = None
    if not original_log_doc.get("pathway_id_used") and original_log_doc.get("task"):
      task_for_retry = original_log_doc.get("task")

    webhook_for_retry: Optional[HttpUrl] = None
    webhook_str = original_log_doc.get("webhook_url")
    if webhook_str:
      from pydantic import HttpUrl, ValidationError
      try:
        webhook_for_retry = HttpUrl(webhook_str)
      except ValidationError as e:
        logfire.warn(
            f"Could not parse original webhook_url '{webhook_str}' for retry due to validation error: {e}. Proceeding without webhook for retry."
        )
        background_tasks.add_task(
            mongo_service.log_error_to_db,
            service_name="BlandAIManager.retry_call",
            error_type="WebhookParsingError",
            message=f"Could not parse original webhook_url '{webhook_str}' for retry.",
            details={
                "contact_id": contact_id,
                "webhook_url_string": webhook_str,
                "validation_error": str(e),
            },
        )
      except Exception as e:
        logfire.warn(
            f"Could not parse original webhook_url '{webhook_str}' for retry due to unexpected error: {e}. Proceeding without webhook for retry."
        )
        background_tasks.add_task(
            mongo_service.log_error_to_db,
            service_name="BlandAIManager.retry_call",
            # Or more specific UnexpectedWebhookParsingError
            error_type="WebhookParsingError",
            message=f"Unexpected error parsing original webhook_url '{webhook_str}' for retry.",
            details={
                "contact_id": contact_id,
                "webhook_url_string": webhook_str,
                "error_type_name": type(e).__name__,
                "error_args": e.args,
            },
        )

    # Extract relevant fields from the original log for the new call request.
    # Ensure these keys exist in your BlandCallLog documents or handle their absence.
    # Assuming your log stores these under 'request_data_variables' and 'metadata_variables' respectively.
    # If they are stored directly as 'request_data' and 'metadata' in the log, use those keys.
    original_request_data = original_log_doc.get("request_data_variables")
    original_metadata = original_log_doc.get("metadata_variables")

    # If metadata is not explicitly stored, you might want to reconstruct it,
    # at least with the contact_id for consistency, though initiate_callback will add it if missing.
    if original_metadata is None:
      # Basic metadata if none was logged
      original_metadata = {"contact_id": contact_id}
    else:
      # Ensure contact_id is present
      original_metadata.setdefault("contact_id", contact_id)

    new_call_request = BlandCallbackRequest(
        phone_number=phone_number,
        task=task_for_retry,
        voice=original_log_doc.get("voice_id") or original_log_doc.get(
            "voice"),  # Prefer 'voice' if logged, fallback to 'voice_id'
        transfer_phone_number=original_log_doc.get("transfer_phone_number"),
        webhook=webhook_for_retry,
        # Ensure request_data is at least an empty dict
        request_data=original_request_data if original_request_data is not None else {},
        metadata=original_metadata,  # Pass reconstructed or original metadata
        max_duration=original_log_doc.get("max_duration"),
        record=original_log_doc.get("record_call") or original_log_doc.get(
            "record"),  # Check for common log keys
        first_sentence=original_log_doc.get("first_sentence"),
        wait_for_greeting=original_log_doc.get("wait_for_greeting")
        # Add other fields from original_log_doc as needed, matching BlandCallbackRequest fields
    )

    original_bland_call_id = original_log_doc.get("call_id_bland")

    logfire.info(
        f"Reconstructed call request for retry of contact_id: {contact_id}. Original Bland Call ID: {original_bland_call_id}",
        retry_request_keys=sorted(
            list(new_call_request.model_dump(exclude_none=True).keys()))
    )

    # initiate_callback uses self.mongo_service and self.background_tasks.
    # Ensure the BlandAIManager instance (self) has these attributes correctly set if they were
    # intended to be the ones passed to this retry_call method.
    # If mongo_service and background_tasks passed to retry_call are different and should be used by
    # the subsequent initiate_callback, then initiate_callback would need to be refactored to accept them as parameters.
    return await self.initiate_callback(
        request_data=new_call_request,
        contact_id=contact_id,
        log_retry_of_call_id=original_bland_call_id,
        log_retry_reason=retry_reason,
    )

  def _extract_data_from_transcript(
          self, transcripts: List[Dict[str, Any]]
  ) -> BlandProcessingResult:
    """
    Extracts relevant data from the transcript.
    Placeholder for actual data extraction logic.
    """
    if not transcripts:
      logfire.warning("No transcript data provided for extraction.")
      # Return with details field properly structured, even if empty
      return BlandProcessingResult(
          status="error",
          message="No transcript data",
          details={"extracted_data": {}},
          summary=None,
          classification=None
      )

    # Example: Concatenate all text from transcripts
    full_text = " ".join(
        t.get("text", "") for t in transcripts if isinstance(t, dict)
    )
    logfire.info(f"Extracted full text from transcript: {full_text[:100]}...")

    # Placeholder for actual data extraction logic (e.g., using NLP)
    extracted_data_content = {
        "full_transcript": full_text, "keywords": ["example"]}

    # Structure the result according to BlandProcessingResult model
    return BlandProcessingResult(
        status="success",
        message="Data extracted successfully",
        # Nest extracted_data here
        details={"extracted_data": extracted_data_content},
        summary=full_text[:150],  # Example summary
        classification={"intent": "unknown"}  # Example classification
    )

  async def process_incoming_transcript(
          self,
          payload: BlandWebhookPayload,
          mongo_service: MongoService,  # Added mongo_service
          background_tasks: BackgroundTasks  # Added background_tasks
  ) -> BlandProcessingResult:
    """
    Processes the incoming transcript from the Bland.ai webhook.
    Extracts data, logs to MongoDB, and potentially triggers further actions.
    """
    logfire.info(
        f"Processing incoming transcript for call_id: {payload.call_id}"
    )

    # Extract data from the transcript
    # Use payload.transcripts instead of payload.transcript
    processing_result = self._extract_data_from_transcript(payload.transcripts)

    contact_id_from_meta = (
        payload.metadata.get("contact_id") if payload.metadata else None
    )
    if not contact_id_from_meta:
      logfire.error(
          f"Webhook for call_id {payload.call_id} missing 'contact_id' in metadata. Cannot update log.",
          metadata=payload.metadata,
      )
      # Log this as a critical error to a general error log if possible
      # For now, we can't associate it with a specific contact_id log entry.
      return BlandProcessingResult(
          status="error",
          message="Missing contact_id in webhook metadata.",
          extracted_data={},
      )

    # Log the processed data and update call status in MongoDB
    # Use the new method name: update_bland_call_log_completion
    # Ensure all required arguments are passed
    update_success = await mongo_service.update_bland_call_log_completion(
        contact_id=contact_id_from_meta,
        call_id_bland=payload.call_id,
        status=BlandCallStatus.COMPLETED,  # Changed to use existing enum member
        transcript_payload=payload.transcripts,  # Pass the original transcripts
        summary_text=processing_result.summary,
        classification_payload=processing_result.classification,
        full_webhook_payload=payload.model_dump(
            mode='json'),  # Ensure BSON-compatible types
        call_completed_timestamp=payload.completed_at or datetime.utcnow(),
        bland_processing_result_payload=processing_result.model_dump(
            mode='json'),  # Ensure BSON-compatible types
        processing_status_message=processing_result.message
    )

    if not update_success:
      logfire.warning(
          f"Failed to update MongoDB log for call_id: {payload.call_id}, contact_id: {contact_id_from_meta}."
      )
      # The update_bland_call_log_completion method should log its own errors.
      # We might want to return a specific status if DB update fails but processing was ok.

    if processing_result.status == "success":
      logfire.info(
          f"Successfully processed transcript for call_id: {payload.call_id}"
      )
    else:
      logfire.error(
          f"Error processing transcript for call_id: {payload.call_id}. Message: {processing_result.message}"
      )

    # Placeholder for further actions (e.g., notifying other services)
    # if processing_result.status == "success":
    #     background_tasks.add_task(notify_crm, processing_result.extracted_data)

    return processing_result


# --- Singleton Instance and Startup Sync ---


bland_manager = BlandAIManager(
    api_key=settings.BLAND_API_KEY,
    base_url=settings.BLAND_API_URL,
    pathway_id_setting=settings.BLAND_PATHWAY_ID,
    mongo_service=None,  # Will be set at startup
    background_tasks=None,  # Will be set at startup
)


async def sync_bland_pathway_on_startup(
        mongo_service: MongoService, background_tasks: Optional[BackgroundTasks] = None
):  # Made background_tasks optional
  logfire.info("Attempting to sync Bland pathway on application startup...")
  # Update the manager instance with the service instances
  bland_manager.mongo_service = mongo_service
  bland_manager.background_tasks = background_tasks
  await bland_manager.sync_all_definitions()


# Note: This sync function needs to be called during FastAPI startup.
# This will be done in app/main.py
