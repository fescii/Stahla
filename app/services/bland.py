# app/services/bland.py

import httpx
import logfire
from typing import Dict, Any, Optional
import os
import json 
from fastapi import BackgroundTasks 
from datetime import datetime 

# Import models
from app.models.bland import (
    BlandApiResult,
    BlandCallbackRequest,
    BlandWebhookPayload,
    BlandProcessingResult
)
from app.models.blandlog import BlandCallStatus 
from app.models.error import ErrorLog 
from app.services.mongo.mongo import MongoService 


from app.core.config import settings

# --- Bland AI Manager ---

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
PATHWAY_JSON_PATH = os.path.join(_PROJECT_ROOT, "app", "assets", "call.json")

class BlandAIManager:
    """
    Manages interactions with the Bland.ai API.
    Handles pathway synchronization (creation if needed), initiating callbacks, and processing transcripts.
    Integrates with MongoService for call logging.
    """

    def __init__(self, api_key: str, base_url: str, pathway_id_setting: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.pathway_definition = self._load_pathway_definition() 
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

    async def _sync_pathway(self, mongo_service: Optional[MongoService] = None, background_tasks: Optional[BackgroundTasks] = None) -> None:
        """
        Attempts to update the configured pathway using the definition from call.json.
        Logs errors to MongoDB if mongo_service is provided.
        """
        logfire.info("Starting pathway synchronization check...")
        
        if not self.pathway_id:
            logfire.error("Pathway sync skipped: BLAND_PATHWAY_ID is not configured in settings.")
            if mongo_service:
                error_details_config = {
                    "service_name": "BlandAIManager._sync_pathway",
                    "error_type": "ConfigurationError",
                    "message": "Pathway sync skipped: BLAND_PATHWAY_ID is not configured.",
                    "details": {"pathway_id_configured": self.pathway_id}
                }
                if background_tasks:
                    background_tasks.add_task(mongo_service.log_error_to_db, **error_details_config)
                else:
                    await mongo_service.log_error_to_db(**error_details_config)
            return
            
        if not self.pathway_definition:
            logfire.error(f"Pathway sync failed for {self.pathway_id}: Definition not loaded from call.json.")
            if mongo_service:
                error_details_def = {
                    "service_name": "BlandAIManager._sync_pathway",
                    "error_type": "PathwayDefinitionError",
                    "message": f"Pathway sync failed for {self.pathway_id}: Definition not loaded from call.json.",
                    "details": {"pathway_id": self.pathway_id, "pathway_json_path": PATHWAY_JSON_PATH}
                }
                if background_tasks:
                    background_tasks.add_task(mongo_service.log_error_to_db, **error_details_def)
                else:
                    await mongo_service.log_error_to_db(**error_details_def)
            return

        pathway_name = self.pathway_definition.get("name")
        if not pathway_name:
            logfire.error(f"Pathway sync failed for {self.pathway_id}: 'name' field missing in call.json.")
            if mongo_service:
                error_details_name = {
                    "service_name": "BlandAIManager._sync_pathway",
                    "error_type": "PathwayDefinitionError",
                    "message": f"Pathway sync failed for {self.pathway_id}: 'name' field missing in call.json.",
                    "details": {"pathway_id": self.pathway_id, "pathway_definition_keys": list(self.pathway_definition.keys())}
                }
                if background_tasks:
                    background_tasks.add_task(mongo_service.log_error_to_db, **error_details_name)
                else:
                    await mongo_service.log_error_to_db(**error_details_name)
            return

        logfire.info(f"Attempting to update pathway {self.pathway_id} using POST /v1/pathway/{{pathway_id}}")
        endpoint = f"/v1/pathway/{self.pathway_id}"
        
        update_payload = {
            "name": pathway_name,
            "description": self.pathway_definition.get("description"),
            "nodes": self.pathway_definition.get("nodes", []),
            "edges": [] 
        }

        logfire.info(f"Sending update payload for {self.pathway_id}", payload=update_payload)
        
        update_result = await self._make_request("POST", endpoint, json_data=update_payload, mongo_service=mongo_service, background_tasks=background_tasks)

        if update_result.status == "success":
            logfire.info(f"Pathway sync successful: Updated existing pathway {self.pathway_id}.")
        else:
            logfire.error(f"Pathway sync failed: Could not update pathway {self.pathway_id}. Bland API Message: {update_result.message}", details=update_result.details)
            # Error already logged by _make_request if mongo_service was provided.

    async def close(self):
        """Gracefully closes the HTTP client."""
        await self._client.aclose()
        logfire.info("BlandAI HTTP client closed.")

    async def _make_request(
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
        """
        url = f"{self.base_url.strip('/')}/{endpoint.lstrip('/')}"
        logfire.debug(f"Making Bland API request: {method} {url}", payload=json_data)
        try:
            response = await self._client.request(method, endpoint, json=json_data)
            response.raise_for_status()
            response_data = response.json()
            logfire.debug("Bland API request successful.", response=response_data)
            status = response_data.get("status", "success")
            message = response_data.get("message", "Request successful")
            details = response_data
            call_id_from_bland = details.get("call_id") if isinstance(details, dict) else None
            return BlandApiResult(status=status, message=message, details=details, call_id=call_id_from_bland)
        except httpx.HTTPStatusError as e:
            logfire.error(f"Bland API HTTP error: {e.response.status_code}", url=str(e.request.url), response=e.response.text)
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
                        "request_payload_keys": list(json_data.keys()) if json_data else None,
                        "status_code": e.response.status_code,
                        "response_text": e.response.text,
                        "error_details_parsed": error_details_parsed
                    }
                }
                if background_tasks:
                    background_tasks.add_task(mongo_service.log_error_to_db, **log_db_payload)
                else:
                    await mongo_service.log_error_to_db(**log_db_payload)
            return BlandApiResult(status="error", message=message_content, details=error_details_parsed)
        except httpx.RequestError as e:
            logfire.error(f"Bland API request error: {e}", url=str(e.request.url))
            message_content = f"Request failed: {e}"
            error_details_data = {"error_type": type(e).__name__, "request_url": str(e.request.url) if e.request else "N/A"}
            if mongo_service:
                log_db_payload_req = {
                    "service_name": "BlandAIManager._make_request",
                    "error_type": "RequestError",
                    "message": message_content,
                    "details": {
                        "method": method,
                        "endpoint": endpoint,
                        "request_payload_keys": list(json_data.keys()) if json_data else None,
                        "error_details": error_details_data 
                    }
                }
                if background_tasks:
                    background_tasks.add_task(mongo_service.log_error_to_db, **log_db_payload_req)
                else:
                    await mongo_service.log_error_to_db(**log_db_payload_req)
            return BlandApiResult(status="error", message=message_content, details=error_details_data)
        except Exception as e:
            logfire.error(f"Unexpected error during Bland API request: {e}", exc_info=True)
            message_content = f"An unexpected error occurred: {e}"
            error_details_unexp_data = {"error_type": type(e).__name__, "exception_args": e.args}
            if mongo_service:
                log_db_payload_unexp = {
                    "service_name": "BlandAIManager._make_request",
                    "error_type": "UnexpectedException",
                    "message": message_content,
                    "details": {
                        "method": method,
                        "endpoint": endpoint,
                        "request_payload_keys": list(json_data.keys()) if json_data else None,
                        "error_details": error_details_unexp_data 
                    }
                }
                if background_tasks:
                    background_tasks.add_task(mongo_service.log_error_to_db, **log_db_payload_unexp)
                else:
                    await mongo_service.log_error_to_db(**log_db_payload_unexp)
            return BlandApiResult(status="error", message=message_content, details=error_details_unexp_data)

    async def initiate_callback(
        self, 
        request_data: BlandCallbackRequest, 
        mongo_service: MongoService,
        background_tasks: BackgroundTasks,
        contact_id: str, 
        log_retry_of_call_id: Optional[str] = None, 
        log_retry_reason: Optional[str] = None      
    ) -> BlandApiResult:
        """
        Initiates a callback using the Bland.ai /call endpoint.
        Logs the attempt to MongoDB via background task.
        The contact_id (HubSpot ID) must be passed in request_data.metadata.
        Passes retry-specific information for detailed logging.
        """
        endpoint = "/v1/calls"
        payload = request_data.model_dump(exclude_none=True)

        if "metadata" not in payload or payload["metadata"] is None:
            payload["metadata"] = {}
        payload["metadata"]["contact_id"] = contact_id
        
        pathway_id_used_for_call: Optional[str] = None
        task_sent_to_bland: Optional[str] = None

        if self.pathway_id:
            payload["pathway_id"] = self.pathway_id
            pathway_id_used_for_call = self.pathway_id
            payload.pop("task", None) 
            task_sent_to_bland = None 
            logfire.info(f"Using pathway_id: {self.pathway_id} for call to {request_data.phone_number}.")
        elif "task" not in payload or not payload["task"]: 
            default_task = "Follow up with the lead regarding their recent inquiry and gather necessary details."
            payload["task"] = default_task
            task_sent_to_bland = default_task
            logfire.warn("No pathway_id configured and no task provided or task was empty. Using default task for call.")
        else:
            task_sent_to_bland = payload["task"]
            logfire.info("Using task provided in request data for call (no pathway ID).")

        if "webhook" in payload and payload["webhook"] is not None:
            payload["webhook"] = str(payload["webhook"])

        background_tasks.add_task(
            mongo_service.log_bland_call_attempt,
            contact_id=contact_id,
            phone_number=request_data.phone_number,
            task=task_sent_to_bland, 
            pathway_id_used=pathway_id_used_for_call, 
            initial_status=BlandCallStatus.PENDING, 
            call_id_bland=None, 
            retry_of_call_id=log_retry_of_call_id, 
            retry_reason=log_retry_reason, 
            voice_id=request_data.voice_id,
            transfer_phone_number=request_data.transfer_phone_number,
            webhook_url=str(request_data.webhook) if request_data.webhook else None, 
            request_data_variables=request_data.request_data, 
            max_duration=request_data.max_duration
        )
        
        logfire.info(f"Initiating Bland callback for contact_id: {contact_id}", phone=request_data.phone_number)
        api_result = await self._make_request(
            "POST", 
            endpoint, 
            json_data=payload, 
            mongo_service=mongo_service, 
            background_tasks=background_tasks
        )

        if api_result.status == "error":
            logfire.error(f"Bland API call initiation failed for contact_id: {contact_id}. Error: {api_result.message}", details=api_result.details)
            failure_update_data = {
                "$set": {
                    "status": BlandCallStatus.FAILED.value,
                    "error_message": api_result.message, 
                    "updated_at": datetime.utcnow(),
                    "bland_error_details": api_result.details 
                }
            }
            background_tasks.add_task(mongo_service.update_bland_call_log_internal, contact_id=contact_id, update_data=failure_update_data)
        elif api_result.call_id: 
            success_init_update_data = {
                "$set": {
                    "call_id_bland": api_result.call_id, 
                    "status": BlandCallStatus.PENDING.value, 
                    "updated_at": datetime.utcnow(),
                    "error_message": None 
                },
                "$unset": {"bland_error_details": ""} 
            }
            background_tasks.add_task(mongo_service.update_bland_call_log_internal, contact_id=contact_id, update_data=success_init_update_data)
            logfire.info(f"Bland call initiated successfully for contact_id: {contact_id}. Bland Call ID: {api_result.call_id}")

        return api_result

    async def retry_call(
        self,
        contact_id: str,
        mongo_service: MongoService,
        background_tasks: BackgroundTasks,
        retry_reason: Optional[str] = "User initiated retry"
    ) -> BlandApiResult:
        """
        Retries a previously failed or problematic call.
        Fetches original call details from MongoDB, constructs a new call request,
        and initiates it via self.initiate_callback.
        """
        logfire.info(f"Attempting to retry call for contact_id: {contact_id} with reason: '{retry_reason}'")
        original_log_doc = await mongo_service.get_bland_call_log(contact_id)

        if not original_log_doc:
            logfire.error(f"Retry failed: Original call log not found for contact_id: {contact_id}")
            # Log this specific error to general error logs
            background_tasks.add_task(
                mongo_service.log_error_to_db,
                service_name="BlandAIManager.retry_call",
                error_type="NotFoundError",
                message="Original call log not found to retry.",
                details={"contact_id": contact_id, "retry_reason": retry_reason}
            )
            return BlandApiResult(status="error", message="Original call log not found to retry.", details={"contact_id": contact_id})

        phone_number = original_log_doc.get("phone_number")
        if not phone_number:
            logfire.error(f"Retry failed: Original call log for contact_id: {contact_id} is missing phone number.")
            background_tasks.add_task(
                mongo_service.log_error_to_db,
                service_name="BlandAIManager.retry_call",
                error_type="DataValidationError",
                message="Original call log missing phone number.",
                details={"contact_id": contact_id, "original_log_doc_id": str(original_log_doc.get("_id"))}
            )
            return BlandApiResult(status="error", message="Original call log missing phone number.", details={"contact_id": contact_id})

        task_for_retry = None
        if not original_log_doc.get("pathway_id_used") and original_log_doc.get("task"):
            task_for_retry = original_log_doc.get("task")
        
        webhook_str = original_log_doc.get("webhook_url")
        webhook_for_retry: Optional[Any] = None 
        if webhook_str:
            from pydantic import HttpUrl, ValidationError 
            try:
                webhook_for_retry = HttpUrl(webhook_str)
            except ValidationError as e: 
                logfire.warn(f"Could not parse original webhook_url '{webhook_str}' for retry due to validation error: {e}. Proceeding without webhook for retry.")
                background_tasks.add_task(
                    mongo_service.log_error_to_db,
                    service_name="BlandAIManager.retry_call",
                    error_type="WebhookParsingError",
                    message=f"Could not parse original webhook_url \'{webhook_str}\' for retry.",
                    details={
                        "contact_id": contact_id, 
                        "webhook_url_string": webhook_str,
                        "validation_error": str(e)
                    }
                )
            except Exception as e: 
                logfire.warn(f"Could not parse original webhook_url '{webhook_str}' for retry due to unexpected error: {e}. Proceeding without webhook for retry.")
                background_tasks.add_task(
                    mongo_service.log_error_to_db,
                    service_name="BlandAIManager.retry_call",
                    error_type="WebhookParsingError", 
                    message=f"Unexpected error parsing original webhook_url \'{webhook_str}\' for retry.",
                    details={
                        "contact_id": contact_id,
                        "webhook_url_string": webhook_str,
                        "error_type_name": type(e).__name__, 
                        "error_args": e.args
                    }
                )

        new_call_request = BlandCallbackRequest(
            phone_number=phone_number,
            task=task_for_retry,
            voice_id=original_log_doc.get("voice_id"),
            transfer_phone_number=original_log_doc.get("transfer_phone_number"),
            webhook=webhook_for_retry,
            request_data=original_log_doc.get("request_data_variables"),
            max_duration=original_log_doc.get("max_duration")
        )
        
        original_bland_call_id = original_log_doc.get("call_id_bland")

        logfire.info(f"Reconstructed call request for retry of contact_id: {contact_id}. Original Bland Call ID: {original_bland_call_id}")

        return await self.initiate_callback(
            request_data=new_call_request,
            mongo_service=mongo_service,
            background_tasks=background_tasks,
            contact_id=contact_id,
            log_retry_of_call_id=original_bland_call_id,
            log_retry_reason=retry_reason
        )

    async def _extract_data_from_transcript(self, transcript: list, mongo_service: MongoService, background_tasks: BackgroundTasks, contact_id: str) -> BlandProcessingResult:
        # Placeholder for actual data extraction logic
        # This method should be expanded based on specific needs.
        # For now, it returns a simple result.
        # Example: Look for keywords, summarize, etc.
        
        # Simulate data extraction
        extracted_data = {"summary": "Call transcript processed.", "keywords": []}
        full_transcript_text = " ".join([item.get('text', '') for item in transcript])


        # Log extraction attempt or error
        try:
            # Simulate some processing that might fail
            if not transcript:
                 # Log an error if transcript is empty, for example
                error_message_content = "Transcript processing error: Received empty transcript."
                logfire.warn(f"{error_message_content} for contact_id: {contact_id}")
                background_tasks.add_task(
                    mongo_service.log_error_to_db,
                    service_name="BlandAIManager._extract_data_from_transcript",
                    error_type="TranscriptProcessingError",
                    message=error_message_content, 
                    details={"contact_id": contact_id, "transcript_length": 0}
                )
                return BlandProcessingResult(
                    success=False, 
                    message=error_message_content,
                    data=None,
                    full_transcript=full_transcript_text
                )

            # Example: if a specific keyword is expected but not found
            # if "confirmation" not in full_transcript_text.lower():
            #     # ... log specific issue ...
            #     pass

            logfire.info(f"Data extraction from transcript successful for contact_id: {contact_id}")
            return BlandProcessingResult(
                success=True, 
                message="Data extracted successfully.", 
                data=extracted_data,
                full_transcript=full_transcript_text
            )

        except Exception as e:
            error_message_content = f"Unexpected error during transcript data extraction: {str(e)}"
            logfire.error(f"{error_message_content} for contact_id: {contact_id}", exc_info=True)
            background_tasks.add_task(
                mongo_service.log_error_to_db,
                service_name="BlandAIManager._extract_data_from_transcript",
                error_type="UnexpectedException",
                message=error_message_content,
                details={
                    "contact_id": contact_id, 
                    "exception_type": type(e).__name__,
                    "exception_args": e.args
                }
            )
            return BlandProcessingResult(
                success=False,
                message=error_message_content,
                data=None,
                full_transcript=full_transcript_text # Still provide transcript if available
            )


    async def process_incoming_transcript(
        self, 
        payload: BlandWebhookPayload, 
        mongo_service: MongoService, 
        background_tasks: BackgroundTasks
    ) -> None:
        """
        Processes incoming transcript from Bland.ai webhook.
        Updates MongoDB log with completion status, transcript, and extracted data.
        """
        contact_id = payload.metadata.get("contact_id") if payload.metadata else None
        bland_call_id = payload.call_id

        if not contact_id:
            logfire.error("Webhook received without contact_id in metadata.", received_payload=payload.model_dump())
            # Log to general errors
            background_tasks.add_task(
                mongo_service.log_error_to_db,
                service_name="BlandAIManager.process_incoming_transcript",
                error_type="MissingContactID",
                message="Webhook received without contact_id in metadata.",
                details={"bland_call_id": bland_call_id, "metadata": payload.metadata}
            )
            return

        logfire.info(f"Processing incoming transcript for contact_id: {contact_id}, Bland Call ID: {bland_call_id}")

        # Extract data from transcript (can be complex, placeholder for now)
        # Pass mongo_service and background_tasks for error logging within _extract_data_from_transcript
        processing_result = await self._extract_data_from_transcript(
            payload.transcript, 
            mongo_service, 
            background_tasks, 
            contact_id
        )
        
        # Update MongoDB log
        background_tasks.add_task(
            mongo_service.update_bland_call_completion,
            contact_id=contact_id,
            bland_call_id_received=bland_call_id, # The call_id from the webhook
            status=BlandCallStatus.COMPLETED, # Assuming successful completion if webhook is called with transcript
            transcript_data=payload.transcript,
            summary=payload.summary,
            recording_url=str(payload.recording_url) if payload.recording_url else None,
            concatenated_transcript=processing_result.full_transcript, # Use the full transcript from processing
            extracted_data=processing_result.data, # Use extracted data from processing
            processing_success=processing_result.success,
            processing_message=processing_result.message,
            call_length=payload.call_length,
            corrected_duration=payload.corrected_duration,
            to_number=payload.to_number,
            from_number=payload.from_number,
            answered_by=payload.answered_by,
            error_message_from_webhook=payload.error # If Bland reports an error in the webhook itself
        )
        logfire.info(f"Background task scheduled to update Bland call log for contact_id: {contact_id} as COMPLETED.")

        # If Bland webhook itself indicates an error for this call
        if payload.error:
            logfire.warn(f"Bland webhook for contact_id: {contact_id}, call_id: {bland_call_id} reported an error: {payload.error}")
            # This error is already logged via `error_message_from_webhook` in `update_bland_call_completion`.
            # If a separate general error log entry is desired for webhook-reported errors:
            background_tasks.add_task(
                mongo_service.log_error_to_db,
                service_name="BlandAIManager.process_incoming_transcript",
                error_type="WebhookReportedError",
                error_message=f"Bland webhook reported an error for call: {payload.error}", # Changed 'message' to 'error_message'
                details={
                    "contact_id": contact_id,
                    "bland_call_id": bland_call_id,
                    "webhook_error": payload.error,
                    "webhook_payload_summary": payload.model_dump(exclude={'transcript', 'recording_url'}) # Log key fields
                }
            )


    async def check_connection(self) -> str:
        """Checks the connection to the Bland.ai API."""
        logfire.debug("Attempting BlandAI connection check...")
        if not self._client:
            logfire.error("BlandAI connection check: Client not initialized.")
            return "error: BlandAI client not initialized."
        try:
            # Attempt to list pathways as a general read operation.
            api_result = await self._make_request(method="GET", endpoint="/v1/pathways")

            if api_result.status == "success":
                logfire.info("BlandAI connection check successful.")
                return "ok"
            else:
                logfire.warn(f"BlandAI connection check failed. API Response: {api_result.message}", details=api_result.details)
                return f"error: {api_result.message}"
        except Exception as e:
            logfire.error(f"BlandAI connection check failed with an exception: {str(e)}", exc_info=True)
            return f"error: Exception during health check: {str(e)}"


# --- Singleton Instance and Startup Sync --- 

bland_manager = BlandAIManager(
    api_key=settings.BLAND_API_KEY,
    base_url=settings.BLAND_API_URL,
    pathway_id_setting=settings.BLAND_PATHWAY_ID
)

async def sync_bland_pathway_on_startup(mongo_service: MongoService, background_tasks: Optional[BackgroundTasks] = None): # Made background_tasks optional
    logfire.info("Attempting to sync Bland pathway on application startup...")
    await bland_manager._sync_pathway(mongo_service=mongo_service, background_tasks=background_tasks)

# Note: This sync function needs to be called during FastAPI startup.
# This will be done in app/main.py
