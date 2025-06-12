# app/api/v1/endpoints/webhooks/util/errors.py

"""
Error handling utilities for webhook endpoints.
Provides consistent error processing and logging.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.models.common import GenericResponse

logger = logging.getLogger(__name__)


class WebhookErrorHandler:
  """Centralized error handling for webhook endpoints."""

  @staticmethod
  def handle_validation_error(
      errors: list,
      request_id: Optional[str] = None
  ) -> HTTPException:
    """
    Handle validation errors consistently.

    Args:
        errors: List of validation error messages
        request_id: Optional request identifier

    Returns:
        HTTPException with validation error details
    """
    if not request_id:
      request_id = str(uuid.uuid4())

    error_message = f"Validation failed: {'; '.join(str(e) for e in errors)}"

    logger.warning(
        f"Webhook validation error (request_id: {request_id}): {error_message}"
    )

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": "validation_failed",
            "message": error_message,
            "errors": errors,
            "request_id": request_id
        }
    )

  @staticmethod
  def handle_service_error(
      service_name: str,
      error: Exception,
      request_id: Optional[str] = None
  ) -> HTTPException:
    """
    Handle service-level errors consistently.

    Args:
        service_name: Name of the service that failed
        error: The exception that occurred
        request_id: Optional request identifier

    Returns:
        HTTPException with service error details
    """
    if not request_id:
      request_id = str(uuid.uuid4())

    error_message = f"{service_name} service error: {str(error)}"

    logger.error(
        f"Webhook service error (request_id: {request_id}): {error_message}",
        exc_info=True
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error": "service_error",
            "message": f"Internal {service_name} service error",
            "service": service_name,
            "request_id": request_id
        }
    )

  @staticmethod
  def handle_timeout_error(
      operation: str,
      timeout_seconds: float,
      request_id: Optional[str] = None
  ) -> HTTPException:
    """
    Handle timeout errors consistently.

    Args:
        operation: Description of the operation that timed out
        timeout_seconds: Timeout duration in seconds
        request_id: Optional request identifier

    Returns:
        HTTPException with timeout error details
    """
    if not request_id:
      request_id = str(uuid.uuid4())

    error_message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"

    logger.warning(
        f"Webhook timeout error (request_id: {request_id}): {error_message}"
    )

    return HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail={
            "error": "timeout",
            "message": error_message,
            "operation": operation,
            "timeout_seconds": timeout_seconds,
            "request_id": request_id
        }
    )

  @staticmethod
  def handle_rate_limit_error(
      limit: int,
      window_seconds: int,
      request_id: Optional[str] = None
  ) -> HTTPException:
    """
    Handle rate limiting errors consistently.

    Args:
        limit: Request limit that was exceeded
        window_seconds: Time window for the limit
        request_id: Optional request identifier

    Returns:
        HTTPException with rate limit error details
    """
    if not request_id:
      request_id = str(uuid.uuid4())

    error_message = f"Rate limit exceeded: {limit} requests per {window_seconds} seconds"

    logger.warning(
        f"Webhook rate limit error (request_id: {request_id}): {error_message}"
    )

    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": error_message,
            "limit": limit,
            "window_seconds": window_seconds,
            "request_id": request_id
        }
    )


def create_error_response_data(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
  """
  Create consistent error response data structure.

  Args:
      error_type: Type of error (validation, service, timeout, etc.)
      message: Human-readable error message
      details: Optional additional error details

  Returns:
      Dictionary with error response structure
  """
  response_data = {
      "status": "error",
      "error_type": error_type,
      "message": message
  }

  if details:
    response_data.update(details)

  return response_data
