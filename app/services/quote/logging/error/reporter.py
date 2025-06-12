# app/services/quote/logging/error/reporter.py

"""
Efficient error reporting and logging to database.
"""

import logging
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timezone

import logfire

from app.services.mongo import MongoService
from app.services.redis.service import RedisService

logger = logging.getLogger(__name__)


class ErrorReporter:
  """Handles efficient error reporting and logging to database."""

  def __init__(self, mongo_service: MongoService, redis_service: RedisService):
    self.mongo_service = mongo_service
    self.redis_service = redis_service
    self._error_queue = asyncio.Queue()
    self._processing_task = None

  async def start_background_processing(self):
    """Start background error processing task."""
    if self._processing_task is None:
      self._processing_task = asyncio.create_task(self._process_error_queue())
      logfire.info("Error reporter background processing started")

  async def stop_background_processing(self):
    """Stop background error processing task."""
    if self._processing_task:
      self._processing_task.cancel()
      try:
        await self._processing_task
      except asyncio.CancelledError:
        pass
      self._processing_task = None
      logfire.info("Error reporter background processing stopped")

  async def report_error(
      self,
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None,
      immediate: bool = False
  ):
    """
    Report an error for logging.

    Args:
        service_name: Name of the service where error occurred
        error_type: Type of error (e.g., 'CacheMiss', 'APIError')
        message: Error message
        details: Additional error details
        immediate: If True, log immediately; otherwise queue for batch processing
    """
    error_data = {
        "service_name": service_name,
        "error_type": error_type,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": self._determine_severity(error_type)
    }

    if immediate:
      await self._log_error_to_db(error_data)
    else:
      await self._error_queue.put(error_data)

  async def report_quote_error(
      self,
      context: str,
      error: Exception,
      request_data: Optional[Dict[str, Any]] = None,
      immediate: bool = False
  ):
    """
    Report a quote-specific error.

    Args:
        context: Context where error occurred
        error: The exception that occurred
        request_data: Request data that caused the error
        immediate: If True, log immediately
    """
    await self.report_error(
        service_name="QuoteService",
        error_type=type(error).__name__,
        message=f"{context}: {str(error)}",
        details={
            "context": context,
            "error_class": type(error).__name__,
            "request_data": request_data
        },
        immediate=immediate
    )

  async def report_sync_error(
      self,
      context: str,
      error: Exception,
      sync_data: Optional[Dict[str, Any]] = None,
      immediate: bool = False
  ):
    """
    Report a sync-specific error.

    Args:
        context: Context where error occurred
        error: The exception that occurred
        sync_data: Sync data that caused the error
        immediate: If True, log immediately
    """
    await self.report_error(
        service_name="SyncService",
        error_type=type(error).__name__,
        message=f"{context}: {str(error)}",
        details={
            "context": context,
            "error_class": type(error).__name__,
            "sync_data": sync_data
        },
        immediate=immediate
    )

  async def _process_error_queue(self):
    """Process errors from the queue in batches."""
    batch_size = 10
    batch_timeout = 5.0  # seconds

    while True:
      try:
        errors_batch = []

        # Collect errors for batch processing
        deadline = asyncio.get_event_loop().time() + batch_timeout

        while len(errors_batch) < batch_size and asyncio.get_event_loop().time() < deadline:
          try:
            error_data = await asyncio.wait_for(
                self._error_queue.get(),
                timeout=max(0.1, deadline - asyncio.get_event_loop().time())
            )
            errors_batch.append(error_data)
          except asyncio.TimeoutError:
            break

        # Process the batch if we have any errors
        if errors_batch:
          await self._log_errors_batch(errors_batch)

      except asyncio.CancelledError:
        break
      except Exception as e:
        logfire.error(f"Error in error processing queue: {e}")
        await asyncio.sleep(1)  # Prevent tight loop on persistent errors

  async def _log_error_to_db(self, error_data: Dict[str, Any]):
    """Log a single error to the database."""
    try:
      # Try to log to MongoDB using the built-in method
      await self.mongo_service.log_error_to_db(
          service_name=error_data["service_name"],
          error_type=error_data["error_type"],
          message=error_data["message"],
          details=error_data.get("details"),
          stack_trace=error_data.get("stack_trace"),
          request_context=error_data.get("request_context")
      )

      # Also increment error counter in Redis
      error_key = f"errors:{error_data['service_name']}:{error_data['error_type']}"
      await self.redis_service.increment(error_key, 1)

    except Exception as e:
      # If database logging fails, at least log to application logs
      logfire.error(
          f"Failed to log error to database: {e}",
          original_error=error_data
      )

  async def _log_errors_batch(self, errors_batch: list):
    """Log a batch of errors to the database."""
    try:
      # Log each error individually since MongoService doesn't have batch method
      for error_data in errors_batch:
        await self.mongo_service.log_error_to_db(
            service_name=error_data["service_name"],
            error_type=error_data["error_type"],
            message=error_data["message"],
            details=error_data.get("details"),
            stack_trace=error_data.get("stack_trace"),
            request_context=error_data.get("request_context")
        )

      # Update Redis counters
      for error_data in errors_batch:
        error_key = f"errors:{error_data['service_name']}:{error_data['error_type']}"
        await self.redis_service.increment(error_key, 1)

      logfire.info(
          f"Successfully logged {len(errors_batch)} errors to database")

    except Exception as e:
      # If batch fails, try individual logging
      logfire.error(
          f"Batch error logging failed: {e}, trying individual logging")
      for error_data in errors_batch:
        await self._log_error_to_db(error_data)

  def _determine_severity(self, error_type: str) -> str:
    """Determine error severity based on error type."""
    critical_errors = ["DatabaseError",
                       "AuthenticationError", "ConfigurationError"]
    warning_errors = ["CacheMiss", "ValidationWarning", "LocationNotFound"]

    if error_type in critical_errors:
      return "critical"
    elif error_type in warning_errors:
      return "warning"
    else:
      return "error"
