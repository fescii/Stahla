# app/models/bland_models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal

class BlandBaseModel(BaseModel):
		"""Base model for Bland AI related entities."""
		class Config:
				extra = 'allow' # Allow extra fields from Bland API responses/webhooks

# --- Incoming Transcript Webhook Model ---

class BlandTranscriptSegment(BlandBaseModel):
		"""Represents a segment of the conversation transcript."""
		user: Optional[str] = None # Speaker ('user' or 'agent')
		text: Optional[str] = None # The transcribed text
		start_time: Optional[float] = Field(None, alias="startTime")
		end_time: Optional[float] = Field(None, alias="endTime")

class BlandWebhookPayload(BlandBaseModel):
		"""
		Structure of the webhook payload received from Bland.ai when a call completes.
		Customize based on the actual payload structure provided by Bland.ai documentation.
		"""
		call_id: Optional[str] = Field(None, alias="call_id", description="Unique ID for the call.")
		phone_number: Optional[str] = Field(None, alias="phone_number", description="The phone number called or calling.")
		transcript: Optional[List[BlandTranscriptSegment]] = Field(None, description="List of transcript segments.")
		summary: Optional[str] = Field(None, description="AI-generated summary of the call (if enabled).")
		recording_url: Optional[HttpUrl] = Field(None, alias="recording_url", description="URL to the call recording.")
		completed_at: Optional[str] = Field(None, alias="completed_at", description="Timestamp when the call completed.")
		# Add other relevant fields from the Bland webhook payload
		# e.g., metadata: Optional[Dict[str, Any]] = None (if you pass metadata during call initiation)
		# e.g., call_status: Optional[str] = None
		# e.g., total_duration: Optional[float] = None

# --- Callback Initiation Model ---

class BlandCallbackRequest(BaseModel):
		"""Data needed to initiate an outbound callback via Bland.ai API."""
		phone_number: str = Field(..., description="The phone number to call.")
		task: str = Field(..., description="A description or prompt for the AI agent's task during the call.")
		# Define other parameters required by Bland's /call endpoint
		# See https://docs.bland.ai/api-reference/endpoint/call
		voice_id: Optional[int] = Field(None, alias="voice_id", description="ID of the desired voice.")
		first_sentence: Optional[str] = Field(None, alias="first_sentence", description="The first sentence the agent should say.")
		wait_for_greeting: Optional[bool] = Field(None, alias="wait_for_greeting", description="Whether to wait for a greeting.")
		record: Optional[bool] = Field(None, description="Whether to record the call.")
		amd: Optional[bool] = Field(None, description="Enable answering machine detection.")
		webhook: Optional[HttpUrl] = Field(None, description="Webhook URL to send call results to (overrides default).")
		metadata: Optional[Dict[str, Any]] = Field(None, description="Custom data to associate with the call.")
		# Add other relevant parameters like language, max_duration, etc.

class BlandCallbackResponse(BlandBaseModel):
		"""Response received after successfully initiating a callback."""
		status: str # e.g., "success"
		call_id: str = Field(..., alias="call_id")
		message: Optional[str] = None
		batch_id: Optional[str] = Field(None, alias="batch_id") # If part of a batch


# --- General Result Model ---
class BlandApiResult(BaseModel):
		"""Generic result structure for Bland operations."""
		status: str # e.g., "success", "error"
		message: Optional[str] = None
		details: Optional[Any] = None # For detailed results or errors
		call_id: Optional[str] = None # Include call ID where relevant

class BlandProcessingResult(BaseModel):
		"""Result structure for transcript processing operations."""
		status: str # e.g., "success", "error", "partial"
		message: Optional[str] = None
		details: Optional[Dict[str, Any]] = None # For extracted data and other details
		call_id: Optional[str] = None # Include call ID where relevant

# --- Example Usage ---
"""
**Instructions:** Create a file named `bland_models.py` inside the `app/models/` directory and paste this code into it. You **must** consult the Bland.ai API documentation to ensure the fields in `BlandWebhookPayload` and `BlandCallbackRequest` accurately reflect their API structu
"""