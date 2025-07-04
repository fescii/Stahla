# app/api/v1/endpoints/webhooks/location/sync.py

"""
Synchronous location lookup webhook endpoint.
Handles real-time distance calculations.
"""

import logging
import time
from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.location import LocationLookupRequest, LocationLookupResponse
from app.models.common import GenericResponse
from app.services.location import LocationService
from app.services.redis.service import RedisService
from app.core.dependencies import get_location_service_dep
from app.services.redis.factory import get_redis_service
from app.core.security import get_api_key
from app.services.background.util import attach_background_tasks
from app.services.dash.background import increment_request_counter_bg, record_location_latency_bg
from app.core.keys import TOTAL_LOCATION_LOOKUPS_KEY

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sync", response_model=GenericResponse[LocationLookupResponse])
async def location_lookup_sync_webhook(
    payload: LocationLookupRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationService = Depends(get_location_service_dep),
    redis_service: RedisService = Depends(get_redis_service),
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
      f"Received synchronous location_lookup request for: {payload.delivery_location}")
  start_time = time.perf_counter()

  # Attach background tasks to services
  attach_background_tasks(location_service, background_tasks)
  attach_background_tasks(redis_service, background_tasks)

  try:
    distance_result = await location_service.get_distance_to_nearest_branch(
        payload.delivery_location
    )
    end_time = time.perf_counter()
    processing_time_ms = int((end_time - start_time) * 1000)

    if distance_result:
      logger.info(
          f"Successfully calculated distance for {payload.delivery_location} in {processing_time_ms}ms.")

      # Increment counter for successful sync lookups
      background_tasks.add_task(
          increment_request_counter_bg, redis_service, TOTAL_LOCATION_LOOKUPS_KEY
      )

      # Record latency
      background_tasks.add_task(
          record_location_latency_bg,
          redis_service,
          processing_time_ms,
          payload.delivery_location,
          "sync_lookup"
      )

      return GenericResponse(
          data=LocationLookupResponse(
              distance_result=distance_result,
              processing_time_ms=processing_time_ms,
          )
      )
    else:
      logger.warning(
          f"No distance result found for {payload.delivery_location}")
      return GenericResponse.error(
          message=f"Unable to calculate distance for location: {payload.delivery_location}",
          details={"delivery_location": payload.delivery_location}
      )

  except Exception as e:
    end_time = time.perf_counter()
    processing_time_ms = int((end_time - start_time) * 1000)
    logger.exception(
        f"Error calculating distance for {payload.delivery_location}", exc_info=e)

    return GenericResponse.error(
        message="An error occurred while calculating the distance.",
        details={"error_type": type(
            e).__name__, "delivery_location": payload.delivery_location}
    )
