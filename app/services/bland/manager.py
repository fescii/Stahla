"""Main Bland AI manager that orchestrates all components."""

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
      pathway_id_setting: Optional[str] = None,
      mongo_service: Optional[MongoService] = None,
      background_tasks: Optional[BackgroundTasks] = None,
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
        pathway_id=self.pathway_id,
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks,
    )

    # Initialize transcript processor if mongo_service is available
    self.transcript_processor = None
    if self.mongo_service:
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
    # Ensure mongo service is available
    if not self.mongo_service:
      raise RuntimeError(
          "MongoService is required for sync operations but not provided. Ensure startup_mongo_service() is called before using BlandAIManager.")

    # Set up components with mongo service
    self.sync_manager.mongo_service = self.mongo_service
    self.call_manager.mongo_service = self.mongo_service
    if not self.transcript_processor:
      self.transcript_processor = BlandTranscriptProcessor(self.mongo_service)

    if not self.background_tasks:
      self.background_tasks = BackgroundTasks()
      self.sync_manager.background_tasks = self.background_tasks
      self.call_manager.background_tasks = self.background_tasks

    # Update the call manager's logging service with the new dependencies
    self.call_manager.update_services(
        mongo_service=self.mongo_service,
        background_tasks=self.background_tasks
    )

    await self.sync_manager.sync_all()

  # Call management operations
  async def initiate_callback(
      self,
      request_data: BlandCallbackRequest,
      contact_id: str,
      log_retry_of_call_id: Optional[str] = None,
      log_retry_reason: Optional[str] = None
  ) -> BlandApiResult:
    """Initiates a callback using the Bland.ai API."""
    return await self.call_manager.initiate_callback(
        request_data=request_data,
        contact_id=contact_id,
        log_retry_of_call_id=log_retry_of_call_id,
        log_retry_reason=log_retry_reason
    )

  async def retry_call(
      self,
      contact_id: str,
      retry_reason: Optional[str] = "User initiated retry",
  ) -> BlandApiResult:
    """Retries a previously failed or problematic call."""
    return await self.call_manager.retry_call(
        contact_id=contact_id,
        retry_reason=retry_reason
    )

  # Transcript processing operations
  async def process_incoming_transcript(
      self,
      payload: BlandWebhookPayload
  ) -> BlandProcessingResult:
    """Processes the incoming transcript from the Bland.ai webhook."""
    if not self.transcript_processor:
      if not self.mongo_service:
        raise ValueError("MongoService is required for transcript processing")
      self.transcript_processor = BlandTranscriptProcessor(self.mongo_service)

    return await self.transcript_processor.process_incoming_transcript(payload)


# --- Singleton Instance and Startup Sync ---

bland_manager = BlandAIManager(
    api_key=settings.BLAND_API_KEY,
    base_url=settings.BLAND_API_URL,
    pathway_id_setting=settings.BLAND_PATHWAY_ID,
    mongo_service=None,  # Will be set at startup by sync_bland_pathway_on_startup
    background_tasks=BackgroundTasks()
)


async def sync_bland_pathway_on_startup(mongo_service: MongoService):
  """Syncs Bland definitions on application startup."""
  import logfire
  logfire.info(
      "Attempting to sync Bland definitions on application startup...")
  bland_manager.mongo_service = mongo_service
  await bland_manager.sync_bland()  # Call the sync method
