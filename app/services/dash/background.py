import logging
from typing import Any, Dict, Optional
from datetime import datetime
import json

from app.services.redis.redis import RedisService
from app.services.mongo.mongo import MongoService, mongo_service # Import MongoService
from app.models.dash.dashboard import RequestLogEntry, ErrorLogEntry

logger = logging.getLogger(__name__)

# Constants from dashboard service (or define centrally)
RECENT_REQUESTS_KEY = "dash:recent_requests"
RECENT_ERRORS_KEY = "dash:recent_errors"
MAX_LOG_ENTRIES = 20
# Redis keys for counters (examples)
TOTAL_QUOTE_REQUESTS_KEY = "dash:requests:quote:total"
SUCCESS_QUOTE_REQUESTS_KEY = "dash:requests:quote:success"
ERROR_QUOTE_REQUESTS_KEY = "dash:requests:quote:error"
TOTAL_LOCATION_LOOKUPS_KEY = "dash:requests:location:total"
# Redis keys for Google Maps stats (examples)
GMAPS_API_CALLS_KEY = "dash:gmaps:calls"
GMAPS_API_ERRORS_KEY = "dash:gmaps:errors"
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
    """Increments a simple counter in Redis."""
    try:
        await redis.increment(key)
        logger.debug(f"Incremented Redis counter: {key}")
    except Exception as e:
        logger.error(f"Failed to increment Redis counter '{key}': {e}", exc_info=True)

async def log_error_bg(
    redis: RedisService, 
    error_key: str, 
    error_message: str, 
    context: Optional[Dict[str, Any]] = None,
    mongo: MongoService = mongo_service # Inject mongo service
):
    """Logs error details to Redis (optional) and MongoDB."""
    log_context = {
        "error_key": error_key,
        "message": error_message,
        "context": context or {}
    }
    logger.error(f"Background Error Logged: Key='{error_key}', Msg='{error_message}', Context={context}")
    
    # Log to MongoDB
    try:
        await mongo.log_report(report_type=error_key, data=log_context, success=False, error_message=error_message)
    except Exception as e:
        logger.error(f"Failed to log error '{error_key}' to MongoDB: {e}", exc_info=True)

    # Optional: Log simple error count to Redis
    # try:
    #     await redis.increment(f"dash:errors:{error_key}:count")
    # except Exception as e:
    #     logger.error(f"Failed to increment Redis error counter for '{error_key}': {e}", exc_info=True)

async def log_success_bg(
    redis: RedisService, 
    success_key: str, 
    details: Optional[Dict[str, Any]] = None,
    mongo: MongoService = mongo_service # Inject mongo service
):
    """Logs success details to MongoDB and optionally increments a Redis counter."""
    log_context = {
        "success_key": success_key,
        "details": details or {}
    }
    logger.info(f"Background Success Logged: Key='{success_key}', Details={details}")

    # Log to MongoDB
    try:
        await mongo.log_report(report_type=success_key, data=log_context, success=True)
    except Exception as e:
        logger.error(f"Failed to log success '{success_key}' to MongoDB: {e}", exc_info=True)

    # Optional: Log simple success count to Redis
    # try:
    #     await redis.increment(f"dash:success:{success_key}:count")
    # except Exception as e:
    #     logger.error(f"Failed to increment Redis success counter for '{success_key}': {e}", exc_info=True)

# Example of how you might adapt other logging functions if needed
# async def log_gmaps_call_bg(redis: RedisService, mongo: MongoService = mongo_service):
#     await increment_request_counter_bg(redis, GMAPS_API_CALLS_KEY)
#     await mongo.log_report(report_type="gmaps_call", data={}, success=True)

# async def log_gmaps_error_bg(redis: RedisService, error_msg: str, mongo: MongoService = mongo_service):
#     await increment_request_counter_bg(redis, GMAPS_API_ERRORS_KEY)
#     await mongo.log_report(report_type="gmaps_error", data={"error": error_msg}, success=False, error_message=error_msg)
