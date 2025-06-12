import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ErrorLog(BaseModel):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
  timestamp: datetime = Field(default_factory=datetime.utcnow)
  service_name: str = Field(...,
                            description="Name of the service where the error occurred")
  error_type: str = Field(...,
                          description="Type of the error (e.g., ValueError, HTTPException)")
  error_message: str = Field(..., description="The error message")
  stack_trace: Optional[str] = Field(
      default=None, description="Full stack trace, if available")
  request_context: Optional[Dict[str, Any]] = Field(
      default=None, description="Contextual information about the request that led to the error (e.g., request ID, user ID, input payload snippet)")
  additional_data: Optional[Dict[str, Any]] = Field(
      default=None, description="Any other relevant data for debugging")

  class Config:
    populate_by_name = True  # Allows using alias _id for id field
    json_encoders = {
        datetime: lambda dt: dt.isoformat(),
        uuid.UUID: lambda u: str(u)
    }


class PaginatedErrorLogResponse(BaseModel):
  page: int
  page_size: int
  total_items: int
  total_pages: int
  items: List[ErrorLog]
