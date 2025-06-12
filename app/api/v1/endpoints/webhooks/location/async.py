# app/api/v1/endpoints/webhooks/location/async.py

"""
Asynchronous location lookup webhook endpoint.
Handles background prefetching of location distances.
"""

import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.location import LocationLookupRequest
from app.models.common import GenericResponse, MessageResponse
from app.services.location import LocationService
from app.services.redis.service import RedisService
from app.core.dependencies import get_location_service_dep
from app.services.redis.factory import get_redis_service
from app.core.security import get_api_key
from app.services.background.util import attach_background_tasks
from app.services.dash.background import increment_request_counter_bg
from app.core.cachekeys import TOTAL_LOCATION_LOOKUPS_KEY

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/async", response_model=GenericResponse[MessageResponse])
async def location_lookup_webhook(
    payload: LocationLookupRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationService = Depends(get_location_service_dep),
    redis_service: RedisService = Depends(get_redis_service),
    api_key: str = Depends(get_api_key),
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

  # Attach background tasks to services
  attach_background_tasks(location_service, background_tasks)
  attach_background_tasks(redis_service, background_tasks)

  # Add background tasks
  background_tasks.add_task(
      location_service.prefetch_distance, payload.delivery_location
  )
  background_tasks.add_task(
      increment_request_counter_bg, redis_service, TOTAL_LOCATION_LOOKUPS_KEY
  )

  logger.info(
      f"Background tasks added for prefetching distance and incrementing counter for: {payload.delivery_location}"
  )

  return GenericResponse(
      data=MessageResponse(
          message=f"Location lookup initiated for {payload.delivery_location}"),
      status_code=202
  )
