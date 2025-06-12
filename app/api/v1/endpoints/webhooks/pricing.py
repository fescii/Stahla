# filepath: /home/femar/AO3/Stahla/app/api/v1/endpoints/webhooks/pricing.py
import logging
import logfire  # Import logfire
from typing import Annotated
import time  # For latency calculation

from fastapi import APIRouter, Depends, HTTPException, Security, status, BackgroundTasks
from pydantic import BaseModel  # Import BaseModel for LocationLookupRequest

from app.core.config import settings

# Import models using the correct path
from app.models.location import LocationLookupRequest as ModelLocationLookupRequest
from app.models.location import LocationLookupResponse  # Added import
from app.models.quote import QuoteRequest, QuoteResponse
from app.models.common import GenericResponse, MessageResponse

# Import service classes and their injectors
from app.services.location import LocationService
from app.services.quote import QuoteService
from app.services.redis.factory import get_instrumented_redis_service
from app.services.redis.instrumented import InstrumentedRedisService

# Import dependency injectors from core
from app.core.dependencies import get_location_service_dep, get_quote_service_dep
from app.core.security import get_api_key  # Import API key security from core

# Import background task helpers
from app.services.dash.background import (
    log_request_response_bg,
    increment_request_counter_bg,
    log_error_bg,
    record_quote_latency_bg,
    record_location_latency_bg,
)

# Import cache keys
from app.core.cachekeys import (
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Security ---
# Note: Using get_api_key from app.core.security


# --- Using LocationLookupRequest from models/location.py ---
# No need to redefine it here since we imported it

@router.post(
    "/location/lookup",
    # Updated response_model
    response_model=GenericResponse[MessageResponse],
    summary="Trigger Background Location Distance Calculation",
    description="Accepts a delivery location and triggers an asynchronous task to calculate and cache the distance to the nearest branch. Returns immediately.",
    # Removed tags here, they should be applied when including the router in api.py
)
async def webhook_location_lookup(
        payload: ModelLocationLookupRequest,
        background_tasks: BackgroundTasks,
        location_service: LocationService = Depends(
            get_location_service_dep
        ),  # Use unified dependency
        redis_service: InstrumentedRedisService = Depends(
            get_instrumented_redis_service),  # Use instrumented injector
        api_key: str = Depends(get_api_key),  # Enforce API Key Auth
):
  """
  Webhook endpoint to initiate background caching of location distance.
  - Validates API Key.
  - Receives `delivery_location`.
  - Adds a background task to call `location_service.prefetch_distance`.
  - Returns `202 Accepted` immediately.
  """
  logger.info(
      f"Received location_lookup webhook for: {payload.delivery_location}")

  # Add background tasks
  background_tasks.add_task(
      # Pass background_tasks here
      location_service.prefetch_distance, payload.delivery_location, background_tasks
  )
  background_tasks.add_task(
      increment_request_counter_bg, redis_service, TOTAL_LOCATION_LOOKUPS_KEY
  )
  # Optionally log the request itself (without response yet)
  # background_tasks.add_task(log_request_response_bg, redis_service, ...)

  logger.info(
      f"Background tasks added for prefetching distance and incrementing counter for: {payload.delivery_location}"
  )
  # Return 202 immediately, indicating the request is accepted for processing
  return GenericResponse(
      data=MessageResponse(
          message="Location lookup accepted for background processing."
      )
  )


@router.post(
    "/location/lookup/sync",
    response_model=GenericResponse[LocationLookupResponse],
    summary="Synchronous Location Distance Calculation for Testing",
    description="Accepts a delivery location, calculates the distance to the nearest branch, and returns the result immediately. This endpoint is for testing and waits for the calculation to complete.",
)
async def webhook_location_lookup_sync(
        payload: ModelLocationLookupRequest,
        # Keep for consistency, though not strictly needed for sync logic other than counters
        background_tasks: BackgroundTasks,
        location_service: LocationService = Depends(
            get_location_service_dep),
        redis_service: InstrumentedRedisService = Depends(
            get_instrumented_redis_service),
        api_key: str = Depends(get_api_key),
) -> GenericResponse[LocationLookupResponse]:
  """
  Webhook endpoint to perform synchronous calculation of location distance.
  - Validates API Key.
  - Receives `delivery_location`.
  - Calls `location_service.get_distance_to_nearest_branch` directly.
  - Returns the `DistanceResult` and processing time.
  """
  logger.info(
      f"Received synchronous location_lookup request for: {payload.delivery_location}"
  )
  start_time = time.perf_counter()

  try:
    distance_result = await location_service.get_distance_to_nearest_branch(
        payload.delivery_location, background_tasks
    )
    end_time = time.perf_counter()
    processing_time_ms = int((end_time - start_time) * 1000)

    if distance_result:
      logger.info(
          f"Successfully calculated distance for {payload.delivery_location} in {processing_time_ms}ms."
      )
      # Increment counter for successful sync lookups (can use existing or new key)
      background_tasks.add_task(
          # You might want a new key for sync lookups
          increment_request_counter_bg, redis_service, TOTAL_LOCATION_LOOKUPS_KEY
      )
      return GenericResponse(
          data=LocationLookupResponse(
              distance_result=distance_result,
              processing_time_ms=processing_time_ms,
              message="Location lookup successful."
          )
      )
    else:
      end_time = time.perf_counter()
      processing_time_ms = int((end_time - start_time) * 1000)
      logger.warning(
          f"Could not determine distance for {payload.delivery_location} after {processing_time_ms}ms."
      )
      # Increment error counter or a specific counter for failed sync lookups
      background_tasks.add_task(
          log_error_bg,
          redis_service,
          "LocationSyncError",
          "Failed to determine distance",
          {"delivery_location": payload.delivery_location},
      )
      return GenericResponse.error(
          message="Failed to determine distance for the provided location.",
          details=LocationLookupResponse(processing_time_ms=processing_time_ms,
                                         message="Failed to determine distance.")  # Include time even on failure
      )

  except Exception as e:
    end_time = time.perf_counter()
    processing_time_ms = int((end_time - start_time) * 1000)
    logger.exception(
        f"Unexpected error during synchronous location lookup for {payload.delivery_location} after {processing_time_ms}ms: {e}",
        exc_info=e
    )
    background_tasks.add_task(
        log_error_bg,
        redis_service,
        type(e).__name__,
        str(e),
        {"delivery_location": payload.delivery_location},
    )
    return GenericResponse.error(
        message="An internal error occurred during location lookup.",
        details=LocationLookupResponse(
            processing_time_ms=processing_time_ms, message=f"Internal error: {type(e).__name__}")
    )


@router.post(
    "/quote",
    # Updated response_model
    response_model=GenericResponse[QuoteResponse],
    summary="Generate Real-time Price Quote with Comprehensive Details",
    description="Calculates a detailed price quote based on provided information, including comprehensive location data, rental information, product specifications, budget breakdowns, and calculation metadata. Requires prior location lookup for optimal performance.",
    # Removed tags here
)
async def webhook_quote(
        payload: QuoteRequest,
        background_tasks: BackgroundTasks,  # Keep for error logging
        quote_service: QuoteService = Depends(
            get_quote_service_dep
        ),  # Use injector from quote.py
        redis_service: InstrumentedRedisService = Depends(
            get_instrumented_redis_service
        ),  # Use instrumented injector for error logging
        api_key: str = Depends(get_api_key),
) -> GenericResponse[QuoteResponse]:  # Updated return type hint
  request_id = payload.request_id

  # ADDED: Start timer
  start_time = time.perf_counter()

  try:
    logger.info(f"Received quote webhook for request_id: {request_id}")
    # This is QuoteResponse
    quote_response_data = await quote_service.build_quote(payload)

    # ADDED: End timer, calculate duration, and update metadata
    end_time = time.perf_counter()
    processing_time_ms = int((end_time - start_time) * 1000)

    # quote_response_data is of type QuoteResponse.
    # QuoteResponse has a 'metadata' field of type QuoteMetadata.
    # QuoteMetadata has a 'calculation_time_ms' field.
    # The build_quote service initializes metadata (likely to None for this field), so it should exist.
    if quote_response_data.metadata:
      quote_response_data.metadata.calculation_time_ms = processing_time_ms
    else:
      # This case implies an issue with QuoteResponse model instantiation or initialization
      # as 'metadata: QuoteMetadata' is a required field in QuoteResponse.
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

    # Return GenericResponse on success
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
    )  # Return GenericResponse on error
  except Exception as e:
    logger.exception(
        f"Unexpected error building quote for request {request_id}", exc_info=e
    )
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
    )  # Return GenericResponse on error
