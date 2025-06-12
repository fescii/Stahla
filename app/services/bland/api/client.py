"""API client for Bland AI requests."""

import httpx
import logfire
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks
from app.models.bland import BlandApiResult
from app.services.mongo import MongoService


class BlandApiClient:
  """HTTP client for making requests to the Bland AI API."""

  def __init__(self, api_key: str, base_url: str):
    self.api_key = api_key
    self.base_url = base_url

    headers = {
        "Authorization": f"{self.api_key}",
        "Content-Type": "application/json",
    }
    self._client = httpx.AsyncClient(
        base_url=self.base_url, headers=headers, timeout=None
    )

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
      api_response = await self.make_request(
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

  async def make_request(
      self,
      method: str,
      endpoint: str,
      json_data: Optional[Dict] = None,
      mongo_service: Optional[MongoService] = None,
      background_tasks: Optional[BackgroundTasks] = None
  ) -> BlandApiResult:
    """
    Helper method to make requests to the Bland API.
    Logs errors to MongoDB if mongo_service is provided.
    Uses background_tasks for logging if provided.
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
            "service_name": "BlandApiClient.make_request",
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
        if background_tasks:  # Check if background_tasks is provided
          background_tasks.add_task(
              mongo_service.log_error_to_db, **log_db_payload
          )
        else:  # Log synchronously if no background_tasks
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
            "service_name": "BlandApiClient.make_request",
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
        if background_tasks:  # Check if background_tasks is provided
          background_tasks.add_task(
              mongo_service.log_error_to_db, **log_db_payload_req
          )
        else:  # Log synchronously
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
            "service_name": "BlandApiClient.make_request",
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
        if background_tasks:  # Check if background_tasks is provided
          background_tasks.add_task(
              mongo_service.log_error_to_db, **log_db_payload_unexp
          )
        else:  # Log synchronously
          await mongo_service.log_error_to_db(**log_db_payload_unexp)
      return BlandApiResult(
          status="error",
          message=message_content,
          details=error_details_unexp_data,
      )
