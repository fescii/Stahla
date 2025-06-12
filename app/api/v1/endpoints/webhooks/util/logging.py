# app/api/v1/endpoints/webhooks/util/logging.py

"""
Logging utilities for webhook endpoints.
Provides structured logging for webhook operations.
"""

import logging
import time
import uuid
from typing import Optional, Dict, Any
from functools import wraps
import logfire

logger = logging.getLogger(__name__)


class WebhookLogger:
  """Structured logging for webhook operations."""

  @staticmethod
  def log_request_start(
      endpoint: str,
      request_data: Dict[str, Any],
      request_id: Optional[str] = None
  ) -> str:
    """
    Log the start of a webhook request.

    Args:
        endpoint: Webhook endpoint name
        request_data: Request payload data
        request_id: Optional request identifier

    Returns:
        Request ID for tracking
    """
    if not request_id:
      request_id = str(uuid.uuid4())

    # Sanitize sensitive data for logging
    safe_data = WebhookLogger._sanitize_request_data(request_data)

    logfire.info(
        f"Webhook request started: {endpoint}",
        endpoint=endpoint,
        request_id=request_id,
        request_data=safe_data
    )

    logger.info(
        f"Webhook {endpoint} request started (ID: {request_id})"
    )

    return request_id

  @staticmethod
  def log_request_success(
      endpoint: str,
      request_id: str,
      processing_time_ms: float,
      response_data: Optional[Dict[str, Any]] = None
  ) -> None:
    """
    Log successful webhook request completion.

    Args:
        endpoint: Webhook endpoint name
        request_id: Request identifier
        processing_time_ms: Processing time in milliseconds
        response_data: Optional response data summary
    """
    logfire.info(
        f"Webhook request completed: {endpoint}",
        endpoint=endpoint,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        status="success"
    )

    logger.info(
        f"Webhook {endpoint} completed successfully "
        f"(ID: {request_id}, time: {processing_time_ms:.2f}ms)"
    )

  @staticmethod
  def log_request_error(
      endpoint: str,
      request_id: str,
      error: Exception,
      processing_time_ms: float
  ) -> None:
    """
    Log webhook request error.

    Args:
        endpoint: Webhook endpoint name
        request_id: Request identifier
        error: Exception that occurred
        processing_time_ms: Processing time before error
    """
    logfire.error(
        f"Webhook request failed: {endpoint}",
        endpoint=endpoint,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        error_type=type(error).__name__,
        error_message=str(error),
        status="error"
    )

    logger.error(
        f"Webhook {endpoint} failed "
        f"(ID: {request_id}, time: {processing_time_ms:.2f}ms): {error}",
        exc_info=True
    )

  @staticmethod
  def _sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove or mask sensitive data from request logging.

    Args:
        data: Raw request data

    Returns:
        Sanitized data safe for logging
    """
    # List of keys that should be masked or removed
    sensitive_keys = {
        'api_key', 'token', 'password', 'secret',
        'auth', 'authorization', 'credentials'
    }

    sanitized = {}
    for key, value in data.items():
      key_lower = key.lower()

      # Mask sensitive keys
      if any(sensitive in key_lower for sensitive in sensitive_keys):
        sanitized[key] = "***masked***"
      elif isinstance(value, dict):
        sanitized[key] = WebhookLogger._sanitize_request_data(value)
      else:
        sanitized[key] = value

    return sanitized


def webhook_logging(endpoint_name: str):
  """
  Decorator for automatic webhook request logging.

  Args:
      endpoint_name: Name of the webhook endpoint

  Usage:
      @webhook_logging("location_sync")
      async def location_webhook(...):
          ...
  """
  def decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
      request_id = str(uuid.uuid4())
      start_time = time.perf_counter()

      # Extract request data from kwargs for logging
      request_data = {}
      if 'payload' in kwargs:
        payload = kwargs['payload']
        if hasattr(payload, 'model_dump'):
          request_data = payload.model_dump(exclude_none=True)
        else:
          request_data = {"payload": str(payload)}

      # Log request start
      WebhookLogger.log_request_start(
          endpoint_name, request_data, request_id
      )

      try:
        # Execute the webhook function
        result = await func(*args, **kwargs)

        # Calculate processing time
        processing_time_ms = (time.perf_counter() - start_time) * 1000

        # Log success
        WebhookLogger.log_request_success(
            endpoint_name, request_id, processing_time_ms
        )

        return result

      except Exception as error:
        # Calculate processing time up to error
        processing_time_ms = (time.perf_counter() - start_time) * 1000

        # Log error
        WebhookLogger.log_request_error(
            endpoint_name, request_id, error, processing_time_ms
        )

        # Re-raise the exception
        raise

    return wrapper
  return decorator
