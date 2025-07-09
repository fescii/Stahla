# filepath: app/models/mongo/calls.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class CallStatus(str, Enum):
  """Status of call processing."""
  PENDING = "pending"
  INITIATED = "initiated"
  CONNECTING = "connecting"
  IN_PROGRESS = "in_progress"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"
  NO_ANSWER = "no_answer"
  BUSY = "busy"
  RETRYING = "retrying"


class CallDocument(BaseModel):
  """MongoDB document model for calls collection."""

  id: str = Field(...,
                  description="Unique call identifier, used as _id in MongoDB")
  contact_id: Optional[str] = Field(None, description="HubSpot contact ID")
  lead_id: Optional[str] = Field(
      None, description="HubSpot lead ID if available")

  # Call details
  phone_number: str = Field(..., description="Phone number that was called")
  call_id_bland: Optional[str] = Field(None, description="Bland.ai call ID")
  call_id_external: Optional[str] = Field(
      None, description="External call system ID")

  # Call configuration
  task: Optional[str] = Field(
      None, description="Task description for the call")
  pathway_id_used: Optional[str] = Field(
      None, description="Bland.ai pathway ID used")
  voice_id: Optional[str] = Field(
      None, description="Voice ID used for the call")
  webhook_url: Optional[str] = Field(
      None, description="Webhook URL for call updates")
  max_duration: Optional[int] = Field(
      12, description="Maximum call duration in minutes")
  transfer_phone_number: Optional[str] = Field(
      None, description="Transfer phone number")

  # Request data
  request_data_variables: Optional[Dict[str, Any]] = Field(
      None, description="Variables passed to call system")

  # Call results
  status: CallStatus = Field(
      CallStatus.PENDING, description="Current call status")
  duration_seconds: Optional[int] = Field(
      None, description="Call duration in seconds")
  cost: Optional[float] = Field(None, description="Call cost")
  answered_by: Optional[str] = Field(None, description="Who answered the call")
  ended_reason: Optional[str] = Field(None, description="Reason call ended")

  # Call content
  summary: Optional[str] = Field(None, description="Summary of the call")
  transcript: Optional[str] = Field(None, description="Full call transcript")
  transcript_payload: Optional[List[Dict[str, Any]]] = Field(
      None, description="Structured transcript data")
  recording_url: Optional[str] = Field(
      None, description="URL to call recording")
  recordings: Optional[List[str]] = Field(
      default_factory=list, description="List of recording URLs")

  # Analysis results
  analysis: Optional[Dict[str, Any]] = Field(
      None, description="Call analysis results")
  classification_payload: Optional[Dict[str, Any]] = Field(
      None, description="Classification results from call")

  # Error handling
  error_message: Optional[str] = Field(
      None, description="Error message if call failed")

  # Retry logic
  retry_count: int = Field(0, description="Number of retry attempts")
  retry_of_call_id: Optional[str] = Field(
      None, description="Original call ID if this is a retry")
  retry_reason: Optional[str] = Field(None, description="Reason for retry")
  last_retry_attempt_at: Optional[datetime] = Field(
      None, description="Last retry timestamp")

  # Webhook and processing
  full_webhook_payload: Optional[Dict[str, Any]] = Field(
      None, description="Complete webhook payload")
  processing_result_payload: Optional[Dict[str, Any]] = Field(
      None, description="Processing results")
  processing_status_message: Optional[str] = Field(
      None, description="Processing status message")

  # Background task tracking
  background_task_id: Optional[str] = Field(
      None, description="ID of background task that processed this call")

  # Timestamps
  call_initiated_at: Optional[datetime] = Field(
      None, description="When call was initiated")
  call_completed_at: Optional[datetime] = Field(
      None, description="When call completed")
  created_at: datetime = Field(
      default_factory=datetime.utcnow, description="Creation timestamp")
  updated_at: datetime = Field(
      default_factory=datetime.utcnow, description="Last update timestamp")

  class Config:
    json_schema_extra = {
        "example": {
            "id": "call_uuid_123",
            "contact_id": "hubspot_contact_123",
            "phone_number": "555-1234",
            "call_id_bland": "bland_call_456",
            "task": "Follow up on quote request",
            "pathway_id_used": "pathway_789",
            "voice_id": "voice_001",
            "max_duration": 12,
            "status": "completed",
            "duration_seconds": 180,
            "cost": 0.75,
            "answered_by": "John Doe",
            "ended_reason": "completed_successfully",
            "summary": "Customer confirmed interest in restroom trailer rental",
            "transcript": "Full conversation transcript here...",
            "retry_count": 0,
            "call_initiated_at": "2025-07-09T10:00:00.000Z",
            "call_completed_at": "2025-07-09T10:03:00.000Z"
        }
    }
