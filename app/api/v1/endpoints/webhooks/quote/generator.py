# app/api/v1/endpoints/webhooks/quote/generator.py

"""
Quote generation webhook endpoint.
Handles pricing calculations and quote generation.
"""

import logging
import time
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.quote import QuoteRequest, QuoteResponse
from app.models.common import GenericResponse
from app.services.quote import QuoteService
from app.services.redis.service import RedisService
from app.core.dependencies import get_quote_service_dep
from app.services.redis.factory import get_redis_service
from app.core.security import get_api_key
from app.services.background.util import attach_background_tasks
from app.services.dash.background import (
    increment_request_counter_bg,
    log_error_bg,
    record_quote_latency_bg,
)
from app.core.keys import (
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
)
from app.services.background.mongo.tasks import log_quote_bg
from app.services.mongo import MongoService, get_mongo_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=GenericResponse[QuoteResponse])
async def quote_webhook(
    payload: QuoteRequest,
    background_tasks: BackgroundTasks,
    quote_service: QuoteService = Depends(get_quote_service_dep),
    redis_service: RedisService = Depends(get_redis_service),
    mongo_service: MongoService = Depends(get_mongo_service),
    api_key: str = Depends(get_api_key),
) -> GenericResponse[QuoteResponse]:
  """
  Webhook endpoint for quote generation.
  - Validates API Key.
  - Receives a QuoteRequest payload.
  - Calls the QuoteService to generate a quote.
  - Returns the QuoteResponse with processing metrics.
  """
  request_id = str(uuid.uuid4())
  logger.info(
      f"Received quote request {request_id} for usage: {payload.usage_type}")
  start_time = time.perf_counter()

  # Attach background tasks to services
  attach_background_tasks(quote_service, background_tasks)
  attach_background_tasks(redis_service, background_tasks)

  try:
    quote_response_data = await quote_service.build_quote(payload)
    end_time = time.perf_counter()
    processing_time_ms = int((end_time - start_time) * 1000)

    logger.info(
        f"Quote generated successfully for request {request_id} in {processing_time_ms}ms")

    # Set processing time in metadata if available
    if quote_response_data and quote_response_data.metadata:
      quote_response_data.metadata.calculation_time_ms = processing_time_ms
    else:
      logger.warning(
          f"Metadata object not found or is None in QuoteResponse for request_id: {request_id}. "
          f"Cannot set calculation_time_ms. This indicates an issue with QuoteResponse model integrity."
      )

    # Increment total and success counters
    background_tasks.add_task(
        increment_request_counter_bg, redis_service, TOTAL_QUOTE_REQUESTS_KEY)
    background_tasks.add_task(
        increment_request_counter_bg, redis_service, SUCCESS_QUOTE_REQUESTS_KEY)

    # Record quote latency for monitoring
    background_tasks.add_task(
        record_quote_latency_bg,
        redis_service,
        processing_time_ms,
        request_id,
        payload.usage_type if hasattr(payload, 'usage_type') else None,
        payload.delivery_location if hasattr(
            payload, 'delivery_location') else None
    )

    # Log quote to MongoDB in background
    quote_data = {
        "id": str(uuid.uuid4()),
        "request_id": request_id,
        "contact_id": getattr(payload, 'contact_id', None),
        "delivery_location": payload.delivery_location,
        "trailer_type": payload.trailer_type,
        "usage_type": payload.usage_type,
        "rental_days": payload.rental_days,
        "rental_start_date": str(payload.rental_start_date) if payload.rental_start_date else None,
        "total_amount": quote_response_data.quote.subtotal if quote_response_data else 0,
        "status": "COMPLETED",
        "processing_time_ms": processing_time_ms,
        "quote_details": quote_response_data.model_dump() if quote_response_data else {},
        "extras": [{"extra_id": extra.extra_id, "qty": extra.qty} for extra in payload.extras] if payload.extras else []
    }
    background_tasks.add_task(
        log_quote_bg, mongo_service, quote_data, request_id)

    return GenericResponse(data=quote_response_data)

  except ValueError as ve:
    logger.warning(
        f"Value error building quote for request {request_id}: {ve}")

    # Increment total and error counters
    background_tasks.add_task(
        increment_request_counter_bg, redis_service, TOTAL_QUOTE_REQUESTS_KEY)
    background_tasks.add_task(
        increment_request_counter_bg, redis_service, ERROR_QUOTE_REQUESTS_KEY)
    background_tasks.add_task(
        log_error_bg,
        redis_service,
        "ValueError",
        str(ve),
        {"request_id": request_id},
    )

    return GenericResponse.error(
        message=str(ve), details={"request_id": request_id}
    )

  except Exception as e:
    logger.exception(
        f"Unexpected error building quote for request {request_id}", exc_info=e)

    # Increment total and error counters
    background_tasks.add_task(
        increment_request_counter_bg, redis_service, TOTAL_QUOTE_REQUESTS_KEY)
    background_tasks.add_task(
        increment_request_counter_bg, redis_service, ERROR_QUOTE_REQUESTS_KEY)
    background_tasks.add_task(
        log_error_bg,
        redis_service,
        type(e).__name__,
        str(e),
        {"request_id": request_id},
    )

    return GenericResponse.error(
        message="An internal error occurred while generating the quote.",
        details={"error_type": type(e).__name__, "request_id": request_id},
    )
