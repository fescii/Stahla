"""Background tasks for error and success logging."""

from app.services.mongo import get_mongo_service
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import json
import logfire

from app.core.cachekeys import (
    RECENT_ERRORS_KEY,
)

logger = logging.getLogger(__name__)

# Constants
MAX_ERROR_ENTRIES = 20


async def log_error_bg(
    redis,
    error_key: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None
):
  """Background task to log error details to Redis and MongoDB."""
  log_context = {
      "error_key": error_key,
      "message": error_message,
      "context": context or {}
  }

  try:
    # Log to Logfire for monitoring
    logfire.error(
        f"Application Error: {error_message}",
        **log_context
    )

    # Create error entry for dashboard
    error_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_key": error_key,
        "message": error_message,
        "context": context or {}
    }

    entry_json = json.dumps(error_entry)

    # Use Redis pipeline for atomic operations
    redis_client = await redis.get_client()
    try:
      async with redis_client.pipeline(transaction=False) as pipe:
        # Add to recent errors list (newest first)
        pipe.lpush(RECENT_ERRORS_KEY, entry_json)
        # Keep list capped to recent entries
        pipe.ltrim(RECENT_ERRORS_KEY, 0, MAX_ERROR_ENTRIES - 1)
        # Increment counter for this specific error type
        pipe.incr(f"error:{error_key}")
        await pipe.execute()
    finally:
      await redis_client.close()

    # Log the error to MongoDB for long-term storage
    # This allows loading historical errors beyond what Redis keeps
    try:
      mongo_service = await get_mongo_service()
      if mongo_service and mongo_service.error_ops:
        await mongo_service.error_ops.log_error_to_db(
            service_name="dashboard",
            error_type=error_key,
            message=error_message,
            details=context,
            request_context=context
        )
    except Exception as mongo_error:
      logger.error(
          f"Failed to log error to MongoDB: {str(mongo_error)}", exc_info=True)

    logger.debug(f"Logged error: {error_key} - {error_message}")

  except Exception as e:
    logger.error(f"Failed to log error: {str(e)}", exc_info=True)


async def log_success_bg(
    redis,
    success_key: str,
    details: Optional[Dict[str, Any]] = None
):
  """Logs success details to MongoDB and optionally increments a Redis counter."""
  log_context = {
      "success_key": success_key,
      "details": details or {}
  }

  try:
    # Log to Logfire for monitoring
    logfire.info(
        f"Operation successful: {success_key}",
        **log_context
    )

    # Increment counter in Redis
    await redis.incr(f"success:{success_key}")

    # Log to MongoDB for analytics
    try:
      mongo_service = await get_mongo_service()
      if mongo_service and mongo_service.reports_ops:
        await mongo_service.reports_ops.log_report(
            report_type="success",
            data={
                "success_key": success_key,
                "details": details or {}
            },
            success=True
        )
    except Exception as mongo_error:
      logger.warning(
          f"Failed to log success to MongoDB: {str(mongo_error)}")

  except Exception as e:
    logger.error(f"Failed to log success: {str(e)}", exc_info=True)


# Import at the bottom to avoid circular imports
