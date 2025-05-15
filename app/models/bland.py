# app/models/bland_models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal

# --- Base Model for Bland AI ---


class BlandBaseModel(BaseModel):
  """Base model for Bland AI related entities."""
  class Config:
    extra = 'allow'  # Allow extra fields from Bland API responses/webhooks


# --- Incoming Transcript Webhook Model ---

class BlandTranscriptSegment(BlandBaseModel):
  """Represents a segment of the conversation transcript."""
  user: Optional[str] = None  # Speaker ('user' or 'agent')
  text: Optional[str] = None  # The transcribed text
  start_time: Optional[float] = Field(None, alias="startTime")
  end_time: Optional[float] = Field(None, alias="endTime")


class BlandTranscriptEntry(BlandBaseModel):
  """Individual transcript entry from Bland.ai call."""
  id: Optional[int] = None
  user: Optional[str] = None  # "user", "assistant", "agent-action"
  text: Optional[str] = None
  created_at: Optional[str] = None


# --- Webhook Payload Model ---
class BlandWebhookPayload(BlandBaseModel):
  """
  Structure of the webhook payload received from Bland.ai when a call completes.
  Based on actual Bland.ai webhook payload structure.
  """
  # Call identification
  call_id: Optional[str] = None
  c_id: Optional[str] = None
  batch_id: Optional[str] = None

  # Phone numbers and direction
  to: Optional[str] = None
  from_: Optional[str] = Field(None, alias="from")
  inbound: Optional[bool] = None
  local_dialing: Optional[bool] = None

  # Call timing
  call_length: Optional[float] = None
  created_at: Optional[str] = None
  started_at: Optional[str] = None
  completed_at: Optional[str] = None
  end_at: Optional[str] = None
  corrected_duration: Optional[str] = None
  max_duration: Optional[int] = None

  # Call status
  completed: Optional[bool] = None
  status: Optional[str] = None
  queue_status: Optional[str] = None
  call_ended_by: Optional[str] = None
  disposition_tag: Optional[str] = None
  error_message: Optional[str] = None

  # Call content
  transcripts: Optional[List[BlandTranscriptEntry]] = None
  concatenated_transcript: Optional[str] = None
  summary: Optional[str] = None

  # Recording
  record: Optional[bool] = None
  recording_url: Optional[HttpUrl] = None
  recording_expiration: Optional[str] = None

  # Metadata and additional info
  variables: Optional[Dict[str, Any]] = None
  metadata: Optional[Dict[str, Any]] = None
  price: Optional[float] = None
  answered_by: Optional[str] = None

  # Pathway info
  pathway_id: Optional[str] = None
  pathway_logs: Optional[Any] = None
  pathway_tags: Optional[List[str]] = None
  analysis: Optional[Any] = None
  analysis_schema: Optional[Any] = None
  transferred_to: Optional[str] = None


class BlandCallbackRequest(BaseModel):
  """Data needed to initiate an outbound callback via Bland.ai API."""
  phone_number: str = Field(..., description="The phone number to call.")
  task: Optional[str] = Field(
      None, description="A description or prompt for the AI agent's task during the call. Will be overridden by BlandAIManager if script is loaded.")
  # Define other parameters required by Bland's /call endpoint
  # See https://docs.bland.ai/api-reference/endpoint/call
  voice_id: Optional[str] = Field(  # Changed from int to str to match Bland docs (e.g., "maya")
      # Alias to 'voice' as per Bland docs
      None, alias="voice", description="Voice of the AI agent. Can be ID or name like 'maya'.")
  first_sentence: Optional[str] = Field(
      # Removed alias, field name matches API
      None, description="The first sentence the agent should say.")
  wait_for_greeting: Optional[bool] = Field(
      # Removed alias, field name matches API
      None, description="Whether to wait for a greeting.")
  record: Optional[bool] = Field(
      None, description="Whether to record the call.")
  webhook: Optional[HttpUrl] = Field(  # Changed to HttpUrl for validation
      None, description="Webhook URL to send call results to (overrides default).")

  # Fields for HubSpot/form data integration as per user request
  request_data: Optional[Dict[str, Any]] = Field(
      None, description="Data accessible to the AI agent during the call (e.g., from HubSpot).")
  metadata: Optional[Dict[str, Any]] = Field(
      None, description="Custom data to associate with the call, returned in webhooks (e.g., source, HubSpot IDs).")

  # Other common Bland API parameters (add more as needed based on usage)
  transfer_phone_number: Optional[str] = Field(
      None, description="Phone number to transfer to if conditions are met.")
  max_duration: Optional[int] = Field(
      None, description="Maximum duration of the call in minutes.")
  # Example of another parameter from Bland docs
  # model: Optional[Literal['base', 'turbo']] = Field(None, description="Select a model to use for your call.")
  # temperature: Optional[float] = Field(None, description="A value between 0 and 1 that controls the randomness of the LLM.")
  # dynamic_data: Optional[List[Dict[str, Any]]] = Field(None, description="Integrate data from external APIs into your agent’s knowledge.")
  # tools: Optional[List[Dict[str, Any]]] = Field(None, description="Tools for the agent to interact with APIs.")

  class Config:
    extra = 'allow'  # Allow other fields to be passed through to Bland API
    populate_by_name = True  # Allow using alias names for instantiation


class BlandCallbackResponse(BlandBaseModel):
  """Response received after successfully initiating a callback."""
  status: str  # e.g., "success"
  call_id: str = Field(..., alias="call_id")
  message: Optional[str] = None
  batch_id: Optional[str] = Field(None, alias="batch_id")  # If part of a batch


# --- General Result Model ---
class BlandApiResult(BaseModel):
  """Generic result structure for Bland operations."""
  status: str  # e.g., "success", "error"
  message: Optional[str] = None
  details: Optional[Any] = None  # For detailed results or errors
  call_id: Optional[str] = None  # Include call ID where relevant


class BlandProcessingResult(BaseModel):
  """Result structure for transcript processing operations."""
  status: str  # e.g., "success", "error", "partial"
  message: Optional[str] = None
  # For extracted data and other details
  details: Optional[Dict[str, Any]] = None
  summary: Optional[str] = None  # Added field
  classification: Optional[Dict[str, Any]] = None  # Added field
  call_id: Optional[str] = None  # Include call ID where relevant
