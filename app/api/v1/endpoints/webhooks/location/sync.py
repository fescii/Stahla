# app/api/v1/endpoints/webhooks/location/sync.py

"""
Synchronous location lookup webhook endpoint.
Handles real-time distance calculations.
"""

import logging
import time
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.location import LocationLookupRequest, LocationLookupResponse
from app.models.mongo.location import LocationStatus  # Added import
from app.models.common import GenericResponse
from app.services.location import LocationService
from app.services.redis.service import RedisService
from app.services.mongo import MongoService, get_mongo_service  # Added import
from app.core.dependencies import get_location_service_dep
from app.services.redis.factory import get_redis_service
from app.core.security import get_api_key
from app.services.background.util import attach_background_tasks
from app.services.dash.background import increment_request_counter_bg, record_location_latency_bg
from app.services.background.mongo.tasks import log_location_bg  # Added import
from app.core.keys import TOTAL_LOCATION_LOOKUPS_KEY

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sync", response_model=GenericResponse[LocationLookupResponse])
async def location_lookup_sync_webhook(
    payload: LocationLookupRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationService = Depends(get_location_service_dep),
    redis_service: RedisService = Depends(get_redis_service),
    mongo_service: MongoService = Depends(
        get_mongo_service),  # Added dependency
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

      # Log location lookup to MongoDB in background
      location_data = {
          "id": str(uuid.uuid4()),
          "delivery_location": payload.delivery_location,
          "original_query": payload.delivery_location,
          "source": "sync_webhook",
          "status": LocationStatus.SUCCESS,
          "lookup_successful": True,
          "fallback_used": False,
          "nearest_branch": distance_result.nearest_branch.name,
          "nearest_branch_address": distance_result.nearest_branch.address,
          "distance_miles": distance_result.distance_miles,
          "distance_meters": distance_result.distance_meters,
          "duration_seconds": distance_result.duration_seconds,
          "within_service_area": distance_result.within_service_area,
          "is_local": distance_result.within_service_area and distance_result.distance_miles < 50,
          "service_area_type": "primary" if distance_result.within_service_area else "outside",
          "geocoded_coordinates": distance_result.geocoded_coordinates,
          "geocoding_successful": distance_result.geocoded_coordinates is not None,
          "is_distance_estimated": distance_result.is_distance_estimated,
          "api_method_used": "google_maps",
          "geocoding_provider": "google_maps" if distance_result.geocoded_coordinates else None,
          "distance_provider": "google_maps",
          "processing_time_ms": processing_time_ms,
          "api_calls_made": 1,
          "cache_hit": False,
          "full_response_data": distance_result.model_dump(),
          "lookup_completed_at": None
      }
      background_tasks.add_task(
          log_location_bg,
          mongo_service=mongo_service,
          location_data=location_data
      )

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

      # Log failed location lookup to MongoDB in background
      location_data = {
          "id": str(uuid.uuid4()),
          "delivery_location": payload.delivery_location,
          "original_query": payload.delivery_location,
          "source": "sync_webhook",
          "status": LocationStatus.FAILED,
          "lookup_successful": False,
          "fallback_used": False,
          "geocoding_successful": False,
          "is_distance_estimated": False,
          "api_method_used": "google_maps",
          "processing_time_ms": processing_time_ms,
          "api_calls_made": 1,
          "cache_hit": False,
          "full_response_data": None
      }
      background_tasks.add_task(
          log_location_bg,
          mongo_service=mongo_service,
          location_data=location_data
      )

      return GenericResponse.error(
          message=f"Unable to calculate distance for location: {payload.delivery_location}",
          details={"delivery_location": payload.delivery_location}
      )

  except Exception as e:
    end_time = time.perf_counter()
    processing_time_ms = int((end_time - start_time) * 1000)
    logger.exception(
        f"Error calculating distance for {payload.delivery_location}", exc_info=e)

    # Log failed location lookup to MongoDB in background
    location_data = {
        "id": str(uuid.uuid4()),
        "delivery_location": payload.delivery_location,
        "original_query": payload.delivery_location,
        "source": "sync_webhook",
        "status": LocationStatus.FAILED,
        "lookup_successful": False,
        "fallback_used": False,
        "geocoding_successful": False,
        "is_distance_estimated": False,
        "api_method_used": "google_maps",
        "processing_time_ms": processing_time_ms,
        "api_calls_made": 0,
        "cache_hit": False,
        "full_response_data": None
    }
    background_tasks.add_task(
        log_location_bg,
        mongo_service=mongo_service,
        location_data=location_data
    )

    return GenericResponse.error(
        message="An error occurred while calculating the distance.",
        details={"error_type": type(
            e).__name__, "delivery_location": payload.delivery_location}
    )
