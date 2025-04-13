# app/services/bland_service.py

import httpx # Using httpx for async HTTP requests
import logfire
from typing import Optional, Dict, Any

# Import settings and models
from app.core.config import settings
from app.models.bland_models import BlandWebhookPayload, BlandCallbackRequest, BlandCallbackResponse, BlandApiResult
# Import other services if needed (e.g., ClassificationManager to send data after processing)
# from app.services.classification_service import classification_manager
# from app.models.classification_models import ClassificationInput

class BlandAIManager:
    """
    Manages interactions with the Bland.ai API.
    Handles processing incoming call transcripts and initiating outbound calls.
    """

    def __init__(self):
        """Initializes the HTTP client for Bland.ai API calls."""
        self.api_key = settings.BLAND_API_KEY
        self.base_url = settings.BLAND_API_URL
        # Initialize an async HTTP client
        # Consider configuring timeouts, headers, etc.
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"{self.api_key}", # Use API Key directly if that's the auth method
                "Content-Type": "application/json"
            },
            timeout=30.0 # Set a reasonable timeout
        )
        logfire.info("BlandAIManager initialized.")

    async def close_client(self):
        """Closes the HTTP client gracefully."""
        await self.http_client.aclose()
        logfire.info("BlandAIManager HTTP client closed.")

    def _extract_key_info_from_transcript(self, payload: BlandWebhookPayload) -> Dict[str, Any]:
        """
        Placeholder function to extract key information from the transcript.
        Replace with actual logic (e.g., using regex, keyword spotting, or another LLM call).
        """
        logfire.debug("Extracting key info from Bland transcript (placeholder).", call_id=payload.call_id)
        extracted_data = {}
        full_transcript = " ".join([seg.text for seg in payload.transcript if seg.text])

        # Example Placeholder Logic:
        if "restroom trailer" in full_transcript.lower():
            extracted_data["product_interest"] = "Restroom Trailer"
        if "porta potty" in full_transcript.lower():
             extracted_data["product_interest"] = "Porta Potty"
        # Add more sophisticated extraction logic here...

        # Include other potentially useful info
        extracted_data["summary"] = payload.summary
        extracted_data["recording_url"] = str(payload.recording_url) if payload.recording_url else None
        extracted_data["full_transcript"] = full_transcript # Include the full text

        logfire.info("Key info extracted (placeholder).", call_id=payload.call_id, extracted_keys=list(extracted_data.keys()))
        return extracted_data

    async def process_incoming_transcript(self, payload: BlandWebhookPayload) -> BlandApiResult:
        """
        Processes the transcript received from the Bland.ai webhook.
        1. Extracts key information.
        2. Prepares data for the classification engine.
        3. (TODO) Sends data to the classification engine.
        """
        logfire.info("Processing incoming Bland transcript.", call_id=payload.call_id)

        try:
            # 1. Extract key information
            extracted_data = self._extract_key_info_from_transcript(payload)

            # 2. Prepare data for classification
            classification_input = { # Build the ClassificationInput structure
                "source": "voice",
                "raw_data": payload.model_dump(mode='json'), # Store the raw payload
                "extracted_data": extracted_data,
                # Populate other specific fields if extracted
                # "required_stalls": extracted_data.get("stalls"),
            }
            logfire.debug("Prepared data for classification.", call_id=payload.call_id, data=classification_input)

            # 3. TODO: Send data to Classification Engine
            # Example:
            # from app.models.classification_models import ClassificationInput
            # classification_payload = ClassificationInput(**classification_input)
            # classification_result = await classification_manager.classify_lead_data(classification_payload)
            # logfire.info("Sent data to classification engine.", call_id=payload.call_id, classification_status=classification_result.status)
            # Handle classification result (e.g., trigger HubSpot update via another service/workflow)


            return BlandApiResult(
                status="success",
                operation="process_transcript",
                message="Transcript processed successfully (placeholder).",
                call_id=payload.call_id,
                details={"extracted_keys": list(extracted_data.keys())}
            )

        except Exception as e:
            logfire.error(f"Error processing Bland transcript: {e}", exc_info=True, call_id=payload.call_id)
            return BlandApiResult(
                status="error",
                operation="process_transcript",
                message=f"An error occurred: {e}",
                call_id=payload.call_id
            )

    async def initiate_callback(self, callback_data: BlandCallbackRequest) -> BlandApiResult:
        """
        Initiates an outbound call using the Bland.ai /call endpoint.
        """
        logfire.info("Initiating Bland.ai callback.", phone_number=callback_data.phone_number)

        try:
            # Prepare the payload, excluding None values
            payload = callback_data.model_dump(exclude_none=True, by_alias=True)
            logfire.debug("Sending payload to Bland /call endpoint.", data=payload)

            response = await self.http_client.post("/call", json=payload)
            response.raise_for_status() # Raise exception for 4xx/5xx responses

            response_data = response.json()
            logfire.info("Bland.ai callback initiated successfully.", response=response_data)

            # Validate response structure if possible (using BlandCallbackResponse)
            try:
                callback_response = BlandCallbackResponse(**response_data)
                return BlandApiResult(
                    status="success",
                    operation="initiate_callback",
                    message=callback_response.message or "Callback initiated.",
                    call_id=callback_response.call_id,
                    details=callback_response.model_dump()
                )
            except Exception as pydantic_error:
                 logfire.warning(f"Could not parse Bland callback response: {pydantic_error}", raw_response=response_data)
                 # Return success but indicate parsing issue
                 return BlandApiResult(
                    status="success", # API call succeeded
                    operation="initiate_callback",
                    message="Callback initiated, but response parsing failed.",
                    call_id=response_data.get("call_id"), # Try to get call_id anyway
                    details=response_data
                 )


        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logfire.error(f"HTTP error initiating Bland callback: {e.response.status_code} - {error_body}", exc_info=True, request_payload=payload)
            return BlandApiResult(
                status="error",
                operation="initiate_callback",
                message=f"HTTP Error {e.response.status_code}: {error_body}",
                details={"status_code": e.response.status_code, "response": error_body}
            )
        except httpx.RequestError as e:
            logfire.error(f"Request error initiating Bland callback: {e}", exc_info=True, request_payload=payload)
            return BlandApiResult(
                status="error",
                operation="initiate_callback",
                message=f"Request Error: {e}"
            )
        except Exception as e:
            logfire.error(f"Unexpected error initiating Bland callback: {e}", exc_info=True, request_payload=payload)
            return BlandApiResult(
                status="error",
                operation="initiate_callback",
                message=f"An unexpected error occurred: {e}"
            )

# Instantiate the manager (or use dependency injection)
bland_manager = BlandAIManager()

# --- Cleanup ---
# Ensure the client is closed when the application shuts down.
# FastAPI's lifespan events are a good place for this.
# Example (in main.py):
# from contextlib import asynccontextmanager
# from app.services.bland_service import bland_manager
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup: Initialize clients, etc. (if not done globally)
#     logfire.info("Application startup.")
#     yield
#     # Shutdown: Close clients gracefully
#     logfire.info("Application shutdown.")
#     await bland_manager.close_client()
#
# app = FastAPI(lifespan=lifespan, ...)

"""
**Instructions:**
1.  Create a file named `bland_service.py` inside the `app/services/` directory.
2.  Paste this code into it.
3.  **Important:** The `_extract_key_info_from_transcript` method has very basic placeholder logic. Replace it with your actual transcript analysis approach.
4.  The `initiate_callback` method assumes API key authentication in the header; adjust if Bland.ai uses a different method. Verify the `/call` endpoint path and required parameters against their documentation.
5.  Consider implementing the `lifespan` context manager in your `app/main.py` to ensure the `httpx` client is closed properly on application shutdo
"""