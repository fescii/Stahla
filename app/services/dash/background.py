import logging
from typing import Any, Dict, Optional
from datetime import datetime
import json

from app.services.redis.redis import RedisService
from app.models.dash.dashboard import RequestLogEntry, ErrorLogEntry

logger = logging.getLogger(__name__)

# Constants from dashboard service (or define centrally)
RECENT_REQUESTS_KEY = "dash:recent_requests"
RECENT_ERRORS_KEY = "dash:recent_errors"
MAX_LOG_ENTRIES = 20
# Redis keys for counters (examples)
TOTAL_QUOTE_REQUESTS_KEY = "dash:stats:quote_requests_total"
SUCCESS_QUOTE_REQUESTS_KEY = "dash:stats:quote_requests_success"
ERROR_QUOTE_REQUESTS_KEY = "dash:stats:quote_requests_error"
TOTAL_LOCATION_LOOKUPS_KEY = "dash:stats:location_lookups_total"
# Redis keys for Google Maps stats (examples)
GMAPS_API_CALLS_KEY = "dash:stats:gmaps_calls_total"
GMAPS_API_ERRORS_KEY = "dash:stats:gmaps_errors_total"
# TODO: Add keys for latency tracking if implementing (e.g., using Redis Streams or Sorted Sets)

async def log_request_response_bg(redis: RedisService, endpoint: str, request_id: str, request_payload: Any, response_payload: Any, status_code: int, latency_ms: Optional[float]):
    """Background task to log request/response pairs to a capped Redis list."""
    try:
        log_entry = RequestLogEntry(
            timestamp=datetime.now(),
            request_id=request_id,
            endpoint=endpoint,
            request_payload=request_payload.model_dump(mode='json') if hasattr(request_payload, 'model_dump') else request_payload,
            response_payload=response_payload.model_dump(mode='json') if hasattr(response_payload, 'model_dump') else response_payload,
            status_code=status_code,
            latency_ms=latency_ms
        )
        # Use the injected RedisService instance
        client = await redis.get_client()
        await client.lpush(RECENT_REQUESTS_KEY, log_entry.model_dump_json())
        await client.ltrim(RECENT_REQUESTS_KEY, 0, MAX_LOG_ENTRIES - 1)
        await client.close()
        logger.debug(f"Logged request {request_id} to Redis list {RECENT_REQUESTS_KEY}")
    except Exception as e:
        logger.error(f"Background task failed to log request/response to Redis: {e}", exc_info=True)

async def increment_request_counter_bg(redis: RedisService, key: str):
    """Background task to increment a request counter."""
    try:
        client = await redis.get_client()
        await client.incr(key)
        await client.close()
        logger.debug(f"Incremented Redis counter: {key}")
    except Exception as e:
        logger.error(f"Background task failed to increment counter {key}: {e}", exc_info=True)

async def log_error_bg(redis: RedisService, error_type: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Background task to log error details to a capped Redis list."""
    try:
        log_entry = ErrorLogEntry(
            timestamp=datetime.now(),
            error_type=error_type,
            message=message,
            details=details
        )
        client = await redis.get_client()
        await client.lpush(RECENT_ERRORS_KEY, log_entry.model_dump_json())
        await client.ltrim(RECENT_ERRORS_KEY, 0, MAX_LOG_ENTRIES - 1)
        await client.close()
        logger.debug(f"Logged error to Redis list {RECENT_ERRORS_KEY}: {error_type}")
    except Exception as e:
        logger.error(f"Background task failed to log error to Redis: {e}", exc_info=True)

# Add more background task functions as needed (e.g., for latency tracking)
