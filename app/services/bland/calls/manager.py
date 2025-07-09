"""Call management functionality for Bland AI."""

import logfire
from typing import Optional
from datetime import datetime, timezone
from pydantic import ValidationError
from fastapi import BackgroundTasks
from app.models.bland import BlandApiResult, BlandCallbackRequest
from app.models.mongo.calls import CallStatus
from app.services.mongo import MongoService
from ..api import BlandApiClient
from ..logging import BlandLogService


class BlandCallManager:
  """Manages call operations with Bland AI."""

  def __init__(
      self,
      api_client: BlandApiClient,
      mongo_service: MongoService,
      background_tasks: BackgroundTasks,
      pathway_id: Optional[str] = None,
  ):
    self.api_client = api_client
    self.pathway_id = pathway_id
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks

    # Initialize logging service with required dependencies
    self.log_service = BlandLogService(
        mongo_service=mongo_service,
        background_tasks=background_tasks
    )

  def update_services(
      self,
      mongo_service: MongoService,
      background_tasks: BackgroundTasks
  ):
    """Update service dependencies and refresh the log service."""
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks

    # Update the log service with new dependencies
    self.log_service.update_services(
        mongo_service=mongo_service,
        background_tasks=background_tasks
    )

  async def initiate_callback(
      self,
      request_data: BlandCallbackRequest,
      contact_id: str,
      log_retry_of_call_id: Optional[str] = None,
      log_retry_reason: Optional[str] = None
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
    self.log_service.log_call_attempt(
        contact_id=contact_id,
        phone_number=request_data.phone_number,
        task=task_sent_to_bland,
        pathway_id_used=pathway_id_used_for_call,
        initial_status=CallStatus.PENDING,
        call_id_bland=None,
        retry_of_call_id=log_retry_of_call_id,
        retry_reason=log_retry_reason,
        voice_id=payload.get("voice") or payload.get("voice_id"),
        webhook_url=str(request_data.webhook) if request_data.webhook else None
    )

    logfire.info(
        f"Initiating Bland callback for contact_id: {contact_id}",
        phone=request_data.phone_number,
        payload_keys=sorted(list(payload.keys()))
    )

    api_result = await self.api_client.make_request(
        "POST",
        endpoint,
        json_data=payload,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
    )

    # Log call result (post-API call)
    if api_result.status == "error":
      logfire.error(
          f"Bland API call initiation failed for contact_id: {contact_id}. Error: {api_result.message}",
          details=api_result.details,
      )
      self.log_service.log_call_failure(
          contact_id=contact_id,
          error_message=api_result.message or "Unknown error",
          error_details=api_result.details
      )

    elif api_result.call_id:
      logfire.info(
          f"Bland call initiated successfully for contact_id: {contact_id}. Bland Call ID: {api_result.call_id}"
      )
      self.log_service.log_call_success(
          contact_id=contact_id,
          call_id_bland=api_result.call_id
      )
    else:
      logfire.warn(
          f"Bland API call for contact_id: {contact_id} returned status '{api_result.status}' but no call_id. This may indicate an issue.",
          message=api_result.message,
          details=api_result.details,
          payload_sent_keys=sorted(list(payload.keys()))
      )
    return api_result

  async def retry_call(
      self,
      contact_id: str,
      retry_reason: Optional[str] = "User initiated retry",
  ) -> BlandApiResult:
    """
    Retries a previously failed or problematic call.
    Fetches original call details from MongoDB using self.mongo_service.
    Constructs a new call request and initiates it via self.initiate_callback.
    """
    logfire.info(
        f"Attempting to retry call for contact_id: {contact_id} with reason: '{retry_reason}'"
    )

    original_log_doc = await self.mongo_service.get_bland_call_log(contact_id)

    if not original_log_doc:
      logfire.error(
          f"Retry failed: Original call log not found for contact_id: {contact_id}"
      )
      # Log this specific error to general error logs using the background_tasks
      self.background_tasks.add_task(
          self.mongo_service.log_error_to_db,
          service_name="BlandCallManager.retry_call",
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
      self.background_tasks.add_task(
          self.mongo_service.log_error_to_db,
          service_name="BlandCallManager.retry_call",
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

    webhook_for_retry: Optional[str] = None
    webhook_str = original_log_doc.get("webhook_url")
    if webhook_str:
      try:
        webhook_for_retry = webhook_str.strip()
      except ValidationError as e:
        logfire.warn(
            f"Could not parse original webhook_url '{webhook_str}' for retry due to validation error: {e}. Proceeding without webhook for retry."
        )
        self.background_tasks.add_task(
            self.mongo_service.log_error_to_db,
            service_name="BlandCallManager.retry_call",
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
        self.background_tasks.add_task(
            self.mongo_service.log_error_to_db,
            service_name="BlandCallManager.retry_call",
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

    return await self.initiate_callback(
        request_data=new_call_request,
        contact_id=contact_id,
        log_retry_of_call_id=original_bland_call_id,
        log_retry_reason=retry_reason,
    )
