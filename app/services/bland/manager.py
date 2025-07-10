"""Main Bland AI manager that orchestrates all components."""

import logfire
from typing import Optional
from fastapi import Depends, BackgroundTasks
from app.core.config import settings
from app.services.mongo import MongoService, get_mongo_service
from app.models.bland import BlandCallbackRequest, BlandApiResult, BlandWebhookPayload, BlandProcessingResult

from .config import load_pathway_definition, load_location_tool_definition, load_quote_tool_definition
from .api import BlandApiClient
from .sync import BlandSyncManager
from .calls import BlandCallManager, BlandTranscriptProcessor


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
      mongo_service: MongoService,
      background_tasks: BackgroundTasks,
      pathway_id_setting: Optional[str] = None,
  ):
    self.pathway_id = pathway_id_setting
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks

    # Load configuration data
    self.pathway_definition = load_pathway_definition()
    self.location_tool_definition = load_location_tool_definition()
    self.quote_tool_definition = load_quote_tool_definition()

    # Initialize API client
    self.api_client = BlandApiClient(api_key, base_url)

    # Initialize specialized managers
    self.sync_manager = BlandSyncManager(
        api_client=self.api_client,
        pathway_definition=self.pathway_definition,
        location_tool_definition=self.location_tool_definition,
        quote_tool_definition=self.quote_tool_definition,
        pathway_id=self.pathway_id,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
    )

    self.call_manager = BlandCallManager(
        api_client=self.api_client,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
        pathway_id=self.pathway_id,
    )

    # Initialize transcript processor with mongo_service
    self.transcript_processor = BlandTranscriptProcessor(self.mongo_service)

  async def close(self):
    """Gracefully closes the HTTP client."""
    await self.api_client.close()

  async def check_connection(self):
    """Checks the connection to the Bland AI API."""
    return await self.api_client.check_connection()

  # Sync operations
  async def sync_bland(self) -> None:
    """Synchronizes all Bland.ai definitions: pathway, location tool, and quote tool."""
    await self.sync_manager.sync_all()

  # Call management operations
  async def initiate_callback(
      self,
      request_data: BlandCallbackRequest,
      contact_id: str,
      log_retry_of_call_id: Optional[str] = None,
      log_retry_reason: Optional[str] = None
  ) -> BlandApiResult:
    """
    Initiates a callback using the Bland.ai API.
    Ensures call logs are saved to MongoDB for tracking and analytics.
    """
    try:
      # Call the manager which already handles MongoDB logging
      result = await self.call_manager.initiate_callback(
          request_data=request_data,
          contact_id=contact_id,
          log_retry_of_call_id=log_retry_of_call_id,
          log_retry_reason=log_retry_reason
      )

      # Additional verification that the call was logged
      if result.status == "success" and result.call_id:
        logfire.info(
            f"Call successfully initiated and logged to MongoDB",
            contact_id=contact_id,
            call_id_bland=result.call_id,
            manager="BlandAIManager"
        )
      elif result.status == "error":
        logfire.warn(
            f"Call initiation failed but error logged to MongoDB",
            contact_id=contact_id,
            error_message=result.message,
            manager="BlandAIManager"
        )

      return result

    except Exception as e:
      logfire.error(
          f"Unexpected error in BlandAIManager.initiate_callback: {e}",
          contact_id=contact_id,
          exc_info=True
      )

      # Log the error to MongoDB as well
      self.background_tasks.add_task(
          self.mongo_service.log_error_to_db,
          service_name="BlandAIManager.initiate_callback",
          error_type="UnexpectedError",
          message=str(e),
          details={"contact_id": contact_id},
          request_context={"request_data": request_data.model_dump()}
      )

      return BlandApiResult(
          status="error",
          message=f"Unexpected error during call initiation: {str(e)}",
          details={"contact_id": contact_id}
      )

  async def retry_call(
      self,
      contact_id: str,
      retry_reason: Optional[str] = "User initiated retry",
  ) -> BlandApiResult:
    """
    Retries a previously failed or problematic call.
    Ensures retry attempts are properly logged to MongoDB.
    """
    try:
      # Call the manager which already handles MongoDB logging
      result = await self.call_manager.retry_call(
          contact_id=contact_id,
          retry_reason=retry_reason
      )

      # Additional verification that the retry was logged
      if result.status == "success" and result.call_id:
        logfire.info(
            f"Call retry successfully initiated and logged to MongoDB",
            contact_id=contact_id,
            call_id_bland=result.call_id,
            retry_reason=retry_reason,
            manager="BlandAIManager"
        )
      elif result.status == "error":
        logfire.warn(
            f"Call retry failed but error logged to MongoDB",
            contact_id=contact_id,
            error_message=result.message,
            retry_reason=retry_reason,
            manager="BlandAIManager"
        )

      return result

    except Exception as e:
      logfire.error(
          f"Unexpected error in BlandAIManager.retry_call: {e}",
          contact_id=contact_id,
          retry_reason=retry_reason,
          exc_info=True
      )

      # Log the error to MongoDB as well
      self.background_tasks.add_task(
          self.mongo_service.log_error_to_db,
          service_name="BlandAIManager.retry_call",
          error_type="UnexpectedError",
          message=str(e),
          details={"contact_id": contact_id, "retry_reason": retry_reason}
      )

      return BlandApiResult(
          status="error",
          message=f"Unexpected error during call retry: {str(e)}",
          details={"contact_id": contact_id}
      )

  # Transcript processing operations
  async def process_incoming_transcript(
      self,
      payload: BlandWebhookPayload
  ) -> BlandProcessingResult:
    """
    Processes the incoming transcript from the Bland.ai webhook.
    Updates call logs in MongoDB with completion data.
    """
    try:
      # Process the transcript which updates the call log in MongoDB
      result = await self.transcript_processor.process_incoming_transcript(payload)

      # Additional verification that transcript processing was logged
      if result.status == "success":
        logfire.info(
            f"Transcript successfully processed and call log updated in MongoDB",
            call_id_bland=payload.call_id,
            contact_id=getattr(payload, 'contact_id', 'unknown'),
            manager="BlandAIManager"
        )
      else:
        logfire.warn(
            f"Transcript processing failed but logged to MongoDB",
            call_id_bland=payload.call_id,
            error_message=result.message,
            manager="BlandAIManager"
        )

      return result

    except Exception as e:
      logfire.error(
          f"Unexpected error in BlandAIManager.process_incoming_transcript: {e}",
          call_id_bland=getattr(payload, 'call_id', 'unknown'),
          exc_info=True
      )

      # Log the error to MongoDB as well
      self.background_tasks.add_task(
          self.mongo_service.log_error_to_db,
          service_name="BlandAIManager.process_incoming_transcript",
          error_type="UnexpectedError",
          message=str(e),
          details={"call_id_bland": getattr(payload, 'call_id', 'unknown')},
          request_context={"payload_keys": list(
              payload.__dict__.keys()) if hasattr(payload, '__dict__') else []}
      )

      return BlandProcessingResult(
          status="error",
          message=f"Unexpected error during transcript processing: {str(e)}",
          call_id=getattr(payload, 'call_id', None)
      )

  # Call analytics and monitoring operations
  async def get_call_stats(self) -> dict:
    """
    Retrieves comprehensive call statistics from MongoDB.
    Useful for monitoring call success rates and system health.
    """
    try:
      return await self.mongo_service.get_call_stats()
    except Exception as e:
      logfire.error(f"Error retrieving call stats: {e}", exc_info=True)
      return {"total_calls": 0, "error": str(e)}

  async def get_recent_calls(self, limit: int = 10) -> list:
    """
    Retrieves recent call logs from MongoDB.
    Useful for monitoring recent call activity.
    """
    try:
      calls = await self.mongo_service.get_recent_calls(limit=limit, offset=0)
      return [call.model_dump() if hasattr(call, 'model_dump') else call for call in calls]
    except Exception as e:
      logfire.error(f"Error retrieving recent calls: {e}", exc_info=True)
      return []

  async def get_call_by_contact(self, contact_id: str) -> Optional[dict]:
    """
    Retrieves the most recent call log for a specific contact.
    Useful for checking call history and status.
    """
    try:
      return await self.mongo_service.get_call_by_contact(contact_id)
    except Exception as e:
      logfire.error(
          f"Error retrieving call for contact {contact_id}: {e}", exc_info=True)
      return None


# --- Singleton Instance and Startup Sync ---

# The manager will be initialized during startup with required dependencies
_bland_manager: Optional[BlandAIManager] = None


async def initialize_bland_manager(mongo_service: MongoService, background_tasks: BackgroundTasks) -> BlandAIManager:
  """Initialize and sync the Bland AI manager with required dependencies."""
  global _bland_manager

  if _bland_manager is not None:
    logfire.info(
        "BlandAIManager already initialized, returning existing instance.")
    return _bland_manager

  logfire.info("Initializing BlandAIManager and syncing Bland definitions...")

  _bland_manager = BlandAIManager(
      api_key=settings.BLAND_API_KEY,
      base_url=settings.BLAND_API_URL,
      mongo_service=mongo_service,
      background_tasks=background_tasks,
      pathway_id_setting=settings.BLAND_PATHWAY_ID,
  )

  await _bland_manager.sync_bland()
  logfire.info("BlandAIManager initialized and synced successfully.")
  return _bland_manager


def set_bland_manager(manager: BlandAIManager) -> None:
  """Set the bland manager instance (used by application context)."""
  global _bland_manager
  _bland_manager = manager


def get_bland_manager() -> BlandAIManager:
  """Get the initialized bland manager instance."""
  if _bland_manager is None:
    raise RuntimeError(
        "BlandAIManager not initialized. Call initialize_bland_manager first.")
  return _bland_manager


async def sync_bland_pathway_on_startup(mongo_service: MongoService):
  """Legacy function for backward compatibility."""
  await initialize_bland_manager(mongo_service, BackgroundTasks())
