# app/services/bland.py

import httpx
import logfire
from typing import Dict, Any, Optional
import os
import json # Keep json import if needed elsewhere, otherwise remove

# Import models
from app.models.bland import (
    BlandApiResult,
    BlandCallbackRequest,
    BlandWebhookPayload,
    BlandProcessingResult
)

from app.core.config import settings

# --- Bland AI Manager ---

# Define path to the pathway JSON file (Re-added)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
PATHWAY_JSON_PATH = os.path.join(_PROJECT_ROOT, "app", "assets", "call.json")

class BlandAIManager:
    """
    Manages interactions with the Bland.ai API.
    Handles pathway synchronization (creation if needed), initiating callbacks, and processing transcripts.
    """

    def __init__(self, api_key: str, base_url: str, pathway_id_setting: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.pathway_definition = self._load_pathway_definition() # Load pathway JSON
        # Store the ID from settings, it will be used if present.
        # If not present, _sync_pathway will attempt to create and populate self.pathway_id.
        self.pathway_id = pathway_id_setting

        headers = {
            "Authorization": f"{self.api_key}",
            "Content-Type": "application/json"
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=10.0
        )

    def _load_pathway_definition(self) -> Dict[str, Any]:
        """Loads the pathway definition from the JSON file."""
        try:
            with open(PATHWAY_JSON_PATH, 'r') as f:
                pathway_data = json.load(f)
                logfire.info(f"Successfully loaded pathway definition from {PATHWAY_JSON_PATH}")
                return pathway_data
        except FileNotFoundError:
            logfire.error(f"Pathway definition file not found at {PATHWAY_JSON_PATH}. Cannot sync pathway.")
            return {}
        except json.JSONDecodeError as e:
            logfire.error(f"Error decoding JSON from {PATHWAY_JSON_PATH}: {e}", exc_info=True)
            return {}
        except Exception as e:
            logfire.error(f"Error loading pathway definition from {PATHWAY_JSON_PATH}: {e}", exc_info=True)
            return {}

    async def _sync_pathway(self) -> None:
        """Attempts to update the configured pathway using the definition from call.json."""
        logfire.info("Starting pathway synchronization check...")
        
        if not self.pathway_id:
            # If no ID is configured, log an error and skip.
            # Creation logic is removed as per the requirement to use the configured ID.
            logfire.error("Pathway sync skipped: BLAND_PATHWAY_ID is not configured in settings.")
            return
            
        if not self.pathway_definition:
            logfire.error(f"Pathway sync failed for {self.pathway_id}: Definition not loaded from call.json.")
            return

        pathway_name = self.pathway_definition.get("name")
        if not pathway_name:
             logfire.error(f"Pathway sync failed for {self.pathway_id}: 'name' field missing in call.json.")
             return

        # --- Configured ID exists: Attempt to UPDATE --- 
        logfire.info(f"Attempting to update pathway {self.pathway_id} using POST /v1/pathway/{{pathway_id}}")
        endpoint = f"/v1/pathway/{self.pathway_id}"
        
        # Construct the payload strictly based on the update endpoint documentation
        # Include name, description, nodes (as array), and an empty edges array
        update_payload = {
            "name": pathway_name, # Use the name from call.json
            "description": self.pathway_definition.get("description"),
            "nodes": self.pathway_definition.get("nodes", []), # Get nodes array from call.json
            "edges": [] # Add empty edges array as per documentation
        }

        # Log the payload being sent for update at INFO level
        logfire.info(f"Sending update payload for {self.pathway_id}", payload=update_payload)
        
        update_result = await self._make_request("POST", endpoint, json_data=update_payload)

        if update_result.status == "success":
            logfire.info(f"Pathway sync successful: Updated existing pathway {self.pathway_id}.")
        else:
            # Log specific failure for update
            logfire.error(f"Pathway sync failed: Could not update pathway {self.pathway_id}. Check payload structure against API requirements.", message=update_result.message, details=update_result.details)
            # Continue using the configured ID even if update fails, but log the error.

    async def close_client(self):
        """Gracefully closes the HTTP client."""
        await self._client.aclose()
        logfire.info("BlandAI HTTP client closed.")

    async def _make_request(self, method: str, endpoint: str, json_data: Optional[Dict] = None) -> BlandApiResult:
        """Helper method to make requests to the Bland API."""
        url = f"{self.base_url.strip('/')}/{endpoint.lstrip('/')}"
        logfire.debug(f"Making Bland API request: {method} {url}", payload=json_data)
        try:
            response = await self._client.request(method, endpoint, json=json_data)
            response.raise_for_status()  # Raise exception for 4xx/5xx errors
            response_data = response.json()
            logfire.debug("Bland API request successful.", response=response_data)
            status = response_data.get("status", "success")
            message = response_data.get("message", "Request successful")
            details = response_data
            return BlandApiResult(status=status, message=message, details=details)
        except httpx.HTTPStatusError as e:
            logfire.error(f"Bland API HTTP error: {e.response.status_code}", url=str(
                e.request.url), response=e.response.text)
            message = f"HTTP error {e.response.status_code}: {e.response.text}"
            try:
                error_details = e.response.json()
            except Exception:
                error_details = {"raw_response": e.response.text}
            return BlandApiResult(status="error", message=message, details=error_details)
        except httpx.RequestError as e:
            logfire.error(f"Bland API request error: {e}", url=str(e.request.url))
            return BlandApiResult(status="error", message=f"Request failed: {e}", details={"error_type": type(e).__name__})
        except Exception as e:
            logfire.error(
                f"Unexpected error during Bland API request: {e}", exc_info=True)
            return BlandApiResult(status="error", message=f"An unexpected error occurred: {e}", details={"error_type": type(e).__name__})

    async def initiate_callback(self, request_data: BlandCallbackRequest) -> BlandApiResult:
        """
        Initiates a callback using the Bland.ai /call endpoint.
        Uses the configured pathway_id from settings.
        Includes metadata from the request.
        """
        endpoint = "/v1/calls" # Use the correct endpoint for initiating calls
        payload = request_data.model_dump(exclude_none=True)

        if self.pathway_id:
            payload["pathway_id"] = self.pathway_id
            payload.pop("task", None) # Remove task if pathway_id is used
            logfire.info(f"Using pathway_id: {self.pathway_id} for call.")
        elif "task" not in payload:
            # Add a default task if no pathway_id and no task provided in request_data
            payload["task"] = "Follow up with the lead regarding their recent inquiry and gather necessary details."
            logfire.warn("No pathway_id configured and no task provided. Using default task for call.")
        else:
            # Task was provided in the request_data, use that
            logfire.info("Using task provided in request data for call (no pathway ID).")

        logfire.debug("Metadata being sent to Bland API for call", metadata=payload.get("metadata"))

        if "webhook" in payload and payload["webhook"] is not None:
            payload["webhook"] = str(payload["webhook"])

        logfire.info("Initiating Bland callback.", phone=request_data.phone_number)
        result = await self._make_request("POST", endpoint, json_data=payload)

        if result.status == "success" and "call_id" in result.details:
            result.call_id = result.details.get("call_id")
        return result

    def _extract_data_from_transcript(self, payload: BlandWebhookPayload) -> Dict[str, Any]:
        """
        Extracts structured data directly from the Bland webhook payload.
        """
        extracted = {
            "call_id": payload.call_id,
            "to_number": payload.to,
            "from_number": payload.from_,
            "call_length": payload.call_length,
            "status": payload.status,
            "call_ended_by": payload.call_ended_by,
            "call_recording_url": str(payload.recording_url) if payload.recording_url else None,
            "call_summary": payload.summary,
            "full_transcript": payload.concatenated_transcript,
            "variables": payload.variables,
            "metadata": payload.metadata,
        }
        return extracted

    async def process_incoming_transcript(self, payload: BlandWebhookPayload) -> BlandProcessingResult:
        """
        Processes the incoming transcript data from the Bland webhook.
        """
        logfire.info("Processing incoming Bland transcript", call_id=payload.call_id)
        try:
            extracted_data = self._extract_data_from_transcript(payload)
            return BlandProcessingResult(
                status="success",
                message="Transcript processed successfully.",
                details={"extracted_data": extracted_data},
                call_id=payload.call_id
            )
        except Exception as e:
            logfire.error(f"Error processing transcript: {str(e)}", call_id=payload.call_id, exc_info=True)
            return BlandProcessingResult(
                status="error",
                message=f"Failed to process transcript: {e}",
                details={"error_type": type(e).__name__},
                call_id=payload.call_id
            )

    async def close(self):
        """Closes the underlying HTTPX client."""
        if self._client:
            logfire.info("Closing BlandAIManager HTTPX client...")
            await self._client.aclose()
            self._client = None # Indicate client is closed
            logfire.info("BlandAIManager HTTPX client closed.")

# --- Singleton Instance and Startup Sync --- 

# Create a singleton instance of the manager
bland_manager = BlandAIManager(
    api_key=settings.BLAND_API_KEY,
    base_url=settings.BLAND_API_URL,
    pathway_id_setting=settings.BLAND_PATHWAY_ID # Pass pathway_id from settings
)

# Define an async function to perform the sync
async def sync_bland_pathway_on_startup():
    logfire.info("Attempting to sync Bland pathway on application startup...")
    await bland_manager._sync_pathway()

# Note: This sync function needs to be called during FastAPI startup.
# This will be done in app/main.py
