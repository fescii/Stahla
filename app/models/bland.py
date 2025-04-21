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
  task: str = Field(..., description="A description or prompt for the AI agent's task during the call.")
  # Define other parameters required by Bland's /call endpoint
  # See https://docs.bland.ai/api-reference/endpoint/call
  voice_id: Optional[int] = Field(
      None, alias="voice_id", description="ID of the desired voice.")
  first_sentence: Optional[str] = Field(
      None, alias="first_sentence", description="The first sentence the agent should say.")
  wait_for_greeting: Optional[bool] = Field(
      None, alias="wait_for_greeting", description="Whether to wait for a greeting.")
  record: Optional[bool] = Field(
      None, description="Whether to record the call.")
  amd: Optional[bool] = Field(
      None, description="Enable answering machine detection.")
  webhook: Optional[str] = Field(
      None, description="Webhook URL to send call results to (overrides default).")
  metadata: Optional[Dict[str, Any]] = Field(
      None, description="Custom data to associate with the call.")
  # Add other relevant parameters like language, max_duration, etc.


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
  call_id: Optional[str] = None  # Include call ID where relevant
