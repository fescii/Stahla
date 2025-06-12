# app/api/v1/endpoints/webhooks/models/responses.py

"""
Shared response models for webhook endpoints.
Provides consistent response structures across webhook types.
"""

from pydantic import BaseModel
from typing import Optional, Any, Dict
from app.models.common import GenericResponse


class WebhookStatusResponse(BaseModel):
  """Standard webhook status response."""
  status: str
  message: str
  processing_time_ms: Optional[float] = None
  request_id: Optional[str] = None


class WebhookErrorResponse(BaseModel):
  """Standard webhook error response."""
  status: str = "error"
  error_message: str
  error_code: Optional[str] = None
  request_id: Optional[str] = None


class WebhookMetricsResponse(BaseModel):
  """Standard metrics included in webhook responses."""
  processing_time_ms: float
  service_latencies: Optional[Dict[str, float]] = None
  cache_hit: Optional[bool] = None
  background_tasks_scheduled: Optional[int] = None


def create_success_response(
    data: Any,
    message: str = "Request processed successfully",
    metrics: Optional[WebhookMetricsResponse] = None
) -> GenericResponse:
  """
  Create a standardized success response for webhooks.

  Args:
      data: Response data payload
      message: Success message
      metrics: Optional performance metrics

  Returns:
      GenericResponse with consistent structure
  """
  response_data = {
      "status": "success",
      "message": message,
      "data": data
  }

  if metrics:
    response_data["metrics"] = metrics.model_dump(exclude_none=True)

  return GenericResponse(
      success=True,
      data=response_data
  )


def create_error_response(
    error_message: str,
    error_code: Optional[str] = None,
    request_id: Optional[str] = None
) -> GenericResponse:
  """
  Create a standardized error response for webhooks.

  Args:
      error_message: Error description
      error_code: Optional error code
      request_id: Optional request identifier

  Returns:
      GenericResponse with error structure
  """
  error_data = WebhookErrorResponse(
      error_message=error_message,
      error_code=error_code,
      request_id=request_id
  )

  error_data_dict = error_data.model_dump(exclude_none=True)
  return GenericResponse.error(
      message=error_message,
      details=error_data_dict,
      status_code=400 if error_code else 500
  )
