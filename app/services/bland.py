# app/services/bland.py

import httpx
import logfire
from typing import Dict, Any, Optional

# Import models
from app.models.bland import (
    BlandApiResult,
    BlandCallbackRequest,
    BlandWebhookPayload,
    BlandProcessingResult
)
from app.core.config import settings

class BlandAIManager:
    """
    Manages interactions with the Bland.ai API.
    Handles initiating callbacks and processing incoming transcripts.
    """
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        # Use httpx.AsyncClient for asynchronous requests
        # Set headers common to all requests
        headers = {
            "Authorization": f"{self.api_key}",
            "Content-Type": "application/json"
        }
        # Initialize the client with base URL and headers
        # Add a timeout (e.g., 10 seconds)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=10.0
        )

    async def close_client(self):
        """Gracefully closes the HTTP client."""
        await self._client.aclose()
        logfire.info("BlandAI HTTP client closed.")

    async def _make_request(self, method: str, endpoint: str, json_data: Optional[Dict] = None) -> BlandApiResult:
        """Helper method to make requests to the Bland API."""
        url = f"{self.base_url.strip('/')}/{endpoint.lstrip('/')}"
        logfire.debug(f"Making Bland API request: {method} {url}", data=json_data)
        try:
            response = await self._client.request(method, endpoint, json=json_data)
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            response_data = response.json()
            logfire.debug("Bland API request successful.", response=response_data)
            # Assuming Bland API returns a 'status' field indicating success/error
            status = response_data.get("status", "success") # Default to success if status missing
            message = response_data.get("message", "Request successful")
            details = response_data # Return the full response data in details
            return BlandApiResult(status=status, message=message, details=details)
        except httpx.HTTPStatusError as e:
            logfire.error(f"Bland API HTTP error: {e.response.status_code}", url=str(e.request.url), response=e.response.text)
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
            logfire.error(f"Unexpected error during Bland API request: {e}", exc_info=True)
            return BlandApiResult(status="error", message=f"An unexpected error occurred: {e}", details={"error_type": type(e).__name__})

    async def initiate_callback(self, request_data: BlandCallbackRequest) -> BlandApiResult:
        """
        Initiates a callback using the Bland.ai /call endpoint.
        """
        endpoint = "/call"
        payload = request_data.model_dump(exclude_none=True)
        logfire.info("Initiating Bland callback.", phone=request_data.phone_number)
        result = await self._make_request("POST", endpoint, json_data=payload)
        # Add call_id to the result details if available
        if result.status == "success" and "call_id" in result.details:
             result.call_id = result.details.get("call_id")
        return result

    def _extract_data_from_transcript(self, payload: BlandWebhookPayload) -> Dict[str, Any]:
        """
        Placeholder function to extract structured data from the transcript.
        This needs significant refinement based on the actual transcript format
        and the specific information required by the call script.
        Could involve regex, keyword spotting, or an LLM call.
        """
        extracted = {
            "full_transcript": "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('text', '')}" for msg in payload.messages or []]),
            "summary": payload.summary or "Summary not provided.",
            "recording_url": payload.recording_url,
            # Attempt basic extraction (highly dependent on script/transcript structure)
            "firstname": None,
            "lastname": None,
            "email": None,
            "phone": payload.to_number, # Caller ID might be available
            "product_interest": [],
            "event_location": None,
            "duration_days": None,
            "guest_count": None,
            "ada_required": None,
            # ... add other fields from ClassificationInput based on call script questions ...
        }

        # Example: Very basic keyword spotting (replace with robust parsing)
        transcript_text = extracted["full_transcript"].lower()
        if "restroom trailer" in transcript_text:
            extracted["product_interest"].append("Restroom Trailer")
        if "porta potty" in transcript_text or "portable toilet" in transcript_text:
            extracted["product_interest"].append("Porta Potty")
        if "wedding" in transcript_text:
            extracted["event_type"] = "Wedding"
        elif "construction" in transcript_text:
            extracted["event_type"] = "Construction"

        # TODO: Implement robust parsing logic here based on the call script.
        # Consider using regex for patterns (email, phone numbers if not already present),
        # or an LLM for more complex entity extraction.
        logfire.warn("Transcript data extraction is using placeholder logic.", call_id=payload.call_id)

        return extracted

    async def process_incoming_transcript(self, payload: BlandWebhookPayload) -> BlandProcessingResult:
        """
        Processes the incoming transcript webhook from Bland.ai.
        Extracts relevant information.
        """
        logfire.info("Processing incoming Bland transcript.", call_id=payload.call_id)

        try:
            extracted_data = self._extract_data_from_transcript(payload)

            # Combine with metadata if available (e.g., original form data)
            if payload.metadata:
                extracted_data["metadata"] = payload.metadata

            logfire.info("Transcript data extracted.", call_id=payload.call_id, extracted_keys=list(extracted_data.keys()))
            return BlandProcessingResult(
                status="success",
                message="Transcript processed successfully.",
                details={"extracted_data": extracted_data}
            )
        except Exception as e:
            logfire.error("Error processing Bland transcript.", call_id=payload.call_id, exc_info=True)
            return BlandProcessingResult(
                status="error",
                message=f"Failed to process transcript: {e}",
                details={"error_type": type(e).__name__}
            )

# Create a singleton instance of the manager
# Ensure settings are loaded before this is instantiated
bland_manager = BlandAIManager(api_key=settings.BLAND_API_KEY, base_url=settings.BLAND_API_URL)


"""
**Instructions:**
    Replace the content of `app/services/bland.py` with this code. Key changes:
    *   Uses `httpx.AsyncClient` for efficient asynchronous requests.
    *   Includes `close_client` method for graceful shutdown (used in `main.py`).
    *   Implements `initiate_callback` using the `/call` endpoint and `BlandCallbackRequest`.
    *   Adds `process_incoming_transcript` which takes `BlandWebhookPayload`.
    *   Includes a **placeholder** `_extract_data_from_transcript` function. **This function requires significant development** to parse transcripts according to your call script, potentially using regex or an LLM.
    *   Returns `BlandProcessingResult` with extracted data.
"""