"""Background tasks for request/response logging and counter operations."""

import logging
from typing import Any, Optional
from datetime import datetime
import json

from app.models.dash.dashboard import RequestLogEntry
from app.core.keys import (
    RECENT_REQUESTS_KEY,
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY,
    GMAPS_API_CALLS_KEY,
    GMAPS_API_ERRORS_KEY,
)

logger = logging.getLogger(__name__)

# Constants
MAX_LOG_ENTRIES = 20


async def log_request_response_bg(redis, endpoint: str, request_id: str, request_payload: Any, response_payload: Any, status_code: int, latency_ms: Optional[float]):
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

    # Convert to dict
    entry_dict = log_entry.model_dump(mode='json')
    entry_json = json.dumps(entry_dict)

    # Use a pipeline for atomic operations
    redis_client = await redis.get_client()
    try:
      async with redis_client.pipeline(transaction=False) as pipe:
        # Add to recent requests list (newest first)
        pipe.lpush(RECENT_REQUESTS_KEY, entry_json)
        # Keep list size capped
        pipe.ltrim(RECENT_REQUESTS_KEY, 0, MAX_LOG_ENTRIES - 1)
        await pipe.execute()
    finally:
      await redis_client.close()

    logger.debug(
        f"Logged request/response for {endpoint} (request_id={request_id})")

  except Exception as e:
    logger.error(
        f"Failed to log request/response: {str(e)}", exc_info=True)


async def increment_request_counter_bg(redis, key: str):
  """Background task to increment a Redis counter."""
  try:
    await redis.increment(key)
    logger.debug(f"Incremented Redis counter: {key}")
  except Exception as e:
    logger.error(
        f"Failed to increment Redis counter '{key}': {e}", exc_info=True)
