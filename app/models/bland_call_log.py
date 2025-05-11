\
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class BlandCallStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class BlandCallLog(BaseModel):
    id: str = Field(..., description="HubSpot Contact ID, used as the primary key (_id in MongoDB)")
    phone_number: str
    task: Optional[str] = Field(default=None, description="Descriptive task for the call, if pathway_id is not used")
    pathway_id_used: Optional[str] = Field(default=None, description="The Bland.ai pathway_id used for the call, if any") # New
    voice_id: Optional[int] = Field(default=None, description="Voice ID used for the call") # New
    transfer_phone_number: Optional[str] = Field(default=None, description="Transfer phone number configured for the call") # New
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL configured for Bland.ai to send updates") # New
    request_data_variables: Optional[Dict[str, Any]] = Field(default=None, description="Variables passed to Bland.ai in request_data") # New
    max_duration: Optional[int] = Field(default=12, description="Maximum duration of the call in minutes") # New
    
    status: BlandCallStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Bland.ai specific response details
    call_id_bland: Optional[str] = Field(default=None, description="Call ID received from Bland.ai")
    summary: Optional[str] = Field(default=None, description="Summary of the call from Bland.ai")
    transcript: Optional[str] = Field(default=None, description="Transcript of the call from Bland.ai")
    full_response_bland: Optional[Dict[str, Any]] = Field(default=None, description="Full response payload from Bland.ai webhook")
    
    error_message: Optional[str] = Field(default=None, description="Error message if the call failed or an error occurred")
    
    # Retry information
    retry_count: int = Field(default=0, description="Number of times this call has been retried")
    retry_of_call_id: Optional[str] = Field(default=None, description="The call_id_bland of the previous attempt, if this is a retry")
    retry_reason: Optional[str] = Field(default=None, description="Reason for the retry")
    last_retry_attempt_at: Optional[datetime] = Field(default=None, description="Timestamp of the last retry attempt")

    model_config = {
        "populate_by_name": True,
        "json_encoders": {datetime: lambda dt: dt.isoformat()},
        "examples": {
            "create": {
                "id": "123",
                "phone_number": "555-1234",
                "task": "Follow up on proposal",
                "pathway_id_used": "pathway_456",
                "voice_id": 1,
                "transfer_phone_number": "555-5678",
                "webhook_url": "https://example.com/webhook",
                "request_data_variables": {"key1": "value1", "key2": "value2"},
                "max_duration": 15
            },
            "update": {
                "status": "completed",
                "summary": "Call completed successfully",
                "transcript": "This is a sample transcript of the call.",
                "error_message": None
            }
        }
    }

class BlandCallStats(BaseModel):
    total_calls: int
    pending_calls: int
    completed_calls: int
    failed_calls: int
    retrying_calls: int

class PaginatedBlandCallResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[BlandCallLog]
