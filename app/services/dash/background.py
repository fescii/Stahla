import logging
from typing import Any, Dict, Optional
from datetime import datetime
import json
import logfire  # Import logfire

from app.models.dash.dashboard import RequestLogEntry
from app.services import mongo
from app.services.redis.redis import RedisService
# Import the singleton instance and alias it
from app.services.mongo.mongo import get_mongo_service
from fastapi import Depends
from app.services.mongo.mongo import get_mongo_service, MongoService

# Import centralized cache keys
from app.core.cachekeys import (
    RECENT_REQUESTS_KEY,
    RECENT_ERRORS_KEY,
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY,
    GMAPS_API_CALLS_KEY,
    GMAPS_API_ERRORS_KEY,
)

logger = logging.getLogger(__name__)

# Constants from dashboard service (or define centrally)
MAX_LOG_ENTRIES = 20
# TODO: Add keys for latency tracking if implementing (e.g., using Redis Streams or Sorted Sets)


async def log_request_response_bg(redis: RedisService, endpoint: str, request_id: str, request_payload: Any, response_payload: Any, status_code: int, latency_ms: Optional[float]):
  """Background task to log request/response pairs to a capped Redis list."""
  try:
    log_entry = RequestLogEntry(
        timestamp=datetime.now(),
        request_id=request_id,
        endpoint=endpoint,
        request_payload=request_payload.model_dump(mode='json') if hasattr(
            request_payload, 'model_dump') else request_payload,
        response_payload=response_payload.model_dump(mode='json') if hasattr(
            response_payload, 'model_dump') else response_payload,
        status_code=status_code,
        latency_ms=latency_ms
    )
    # Use the injected RedisService instance
    client = await redis.get_client()
    client.lpush(RECENT_REQUESTS_KEY, log_entry.model_dump_json())
    client.ltrim(RECENT_REQUESTS_KEY, 0, MAX_LOG_ENTRIES - 1)
    await client.close()
    logger.debug(
        f"Logged request {request_id} to Redis list {RECENT_REQUESTS_KEY}")
  except Exception as e:
    logger.error(
        f"Background task failed to log request/response to Redis: {e}", exc_info=True)


async def increment_request_counter_bg(redis: RedisService, key: str):
  """Increments a simple counter in Redis."""
  try:
    await redis.increment(key)
    logger.debug(f"Incremented Redis counter: {key}")
  except Exception as e:
    logger.error(
        f"Failed to increment Redis counter '{key}': {e}", exc_info=True)


async def log_error_bg(
    redis: RedisService,
    error_key: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None
):
  """Logs error details to Redis (optional) and MongoDB."""
  log_context = {
      "error_key": error_key,
      "message": error_message,
      "context": context or {}
  }
  # Use logfire for better visibility
  logfire.error(
      f"Background Error Logged: Key='{error_key}', Msg='{error_message}', Context={context}")

  mongo_service = await get_mongo_service()
  # Log to MongoDB using the imported singleton instance
  if mongo_service:
    logfire.info(
        f"Attempting to log error '{error_key}' to MongoDB...")  # Add log
    try:
      insert_id = await mongo_service.log_report(report_type=error_key, data=log_context, success=False, error_message=error_message)
      if insert_id:
        logfire.info(
            # Add log
            f"Successfully logged error '{error_key}' to MongoDB with id: {insert_id}")
      else:
        logfire.error(
            # Add log
            f"Failed to log error '{error_key}' to MongoDB (insert returned None).")
    except Exception as e:
      # Log exception during the mongo write attempt
      logfire.error(
          f"Exception while logging error '{error_key}' to MongoDB: {e}", exc_info=True)
  else:
    logfire.warning(
        f"Skipping MongoDB error log for '{error_key}': Mongo service not initialized.")

  # Optional: Log simple error count to Redis
  # try:
  #     await redis.increment(f"dash:errors:{error_key}:count")
  # except Exception as e:
  #     logger.error(f"Failed to increment Redis error counter for '{error_key}': {e}", exc_info=True)


async def log_success_bg(
    redis: RedisService,
    success_key: str,
    details: Optional[Dict[str, Any]] = None
):
  """Logs success details to MongoDB and optionally increments a Redis counter."""
  log_context = {
      "success_key": success_key,
      "details": details or {}
  }
  # Use logfire for better visibility
  logfire.info(
      f"Background Success Logged: Key='{success_key}', Details={details}")

  mongo_service = await get_mongo_service()
  # Log to MongoDB using the imported singleton instance
  if mongo_service:
    logfire.info(
        f"Attempting to log success '{success_key}' to MongoDB...")  # Add log
    try:
      insert_id = await mongo_service.log_report(report_type=success_key, data=log_context, success=True)
      if insert_id:
        logfire.info(
            # Add log
            f"Successfully logged success '{success_key}' to MongoDB with id: {insert_id}")
      else:
        logfire.error(
            # Add log
            f"Failed to log success '{success_key}' to MongoDB (insert returned None).")
    except Exception as e:
      # Log exception during the mongo write attempt
      logfire.error(
          f"Exception while logging success '{success_key}' to MongoDB: {e}", exc_info=True)
  else:
    logfire.warning(
        f"Skipping MongoDB success log for '{success_key}': Mongo service not initialized.")
