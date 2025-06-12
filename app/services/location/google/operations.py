# filepath: app/services/location/google/operations.py
import asyncio
import functools
import logfire
import time
from typing import Dict, Any, Optional
import googlemaps
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
from fastapi import BackgroundTasks
from app.core.config import settings
from app.services.redis.service import RedisService
from app.services.mongo import MongoService
from app.services.location.parsing import parse_and_normalize_address
from app.core.cachekeys import GMAPS_API_CALLS_KEY, GMAPS_API_ERRORS_KEY
from app.services.background import increment_request_counter_bg, record_external_api_latency_bg
from app.services.background.util import add_task_safely
from app.utils.latency import LatencyTracker

MILES_PER_METER = 0.000621371


class GoogleMapsOperations:
  """Handles Google Maps API operations for location service."""

  def __init__(self, redis_service: RedisService, mongo_service: MongoService):
    self.redis_service = redis_service
    self.mongo_service = mongo_service
    self.gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

  async def get_distance_from_google(
      self, origin: str, destination: str
  ) -> Optional[Dict[str, Any]]:
    """Helper to get distance using Google Maps API with multiple address variations. Logs errors to MongoDB."""
    if not self.gmaps:
      msg = "Google Maps client not initialized."
      logfire.error(msg)
      await self.mongo_service.log_error_to_db(
          service_name="GoogleMapsOperations.get_distance_from_google",
          error_type="ConfigurationError",
          message=msg,
          details={"origin": origin, "destination": destination},
      )
      return None

    loop = asyncio.get_running_loop()
    final_result_data: Optional[Dict[str, Any]] = None
    attempted_variations = []

    # Get multiple variations of the destination address
    destination_variations = parse_and_normalize_address(destination)
    logfire.info(
        f"Generated {len(destination_variations)} address variations for '{destination}': {destination_variations}")

    # Try each variation until we get a successful result
    for i, dest_variation in enumerate(destination_variations):
      try:
        logfire.info(
            f"Attempting Google Maps API call for origin: '{origin}', destination: '{dest_variation}' (variation {i+1}/{len(destination_variations)})")
        await increment_request_counter_bg(
            self.redis_service, GMAPS_API_CALLS_KEY
        )

        # Track latency for this specific API call
        from app.services.background.util import get_background_tasks

        # Get background tasks if available
        bg_tasks = get_background_tasks(self)

        if bg_tasks:
          with LatencyTracker(
              service_type="gmaps",
              redis_service=self.redis_service,
              background_tasks=bg_tasks,
              operation_name="distance_matrix",
              request_id=f"{origin}:{dest_variation}"
          ):
            func_call = functools.partial(
                self.gmaps.distance_matrix,  # type: ignore
                origins=[origin],
                destinations=[dest_variation],
                mode="driving",
            )
            result = await loop.run_in_executor(None, func_call)
        else:
          func_call = functools.partial(
              self.gmaps.distance_matrix,  # type: ignore
              origins=[origin],
              destinations=[dest_variation],
              mode="driving",
          )
          result = await loop.run_in_executor(None, func_call)

        attempted_variations.append(dest_variation)

        gmaps_status = result.get("status")
        element_status = (
            result["rows"][0]["elements"][0].get("status")
            if gmaps_status == "OK" and result.get("rows") and result["rows"][0].get("elements")
            else "N/A" if gmaps_status == "OK" else gmaps_status
        )

        if gmaps_status == "OK" and element_status == "OK":
          element = result["rows"][0]["elements"][0]
          distance_meters = element["distance"]["value"]
          duration_seconds = element["duration"]["value"]
          distance_miles = distance_meters * MILES_PER_METER
          logfire.info(
              f"Google Maps distance (variation {i+1}): {distance_miles:.2f} miles, Duration: {duration_seconds}s for {origin} -> {dest_variation}"
          )
          final_result_data = {
              "distance_miles": round(distance_miles, 2),
              "distance_meters": distance_meters,
              "duration_seconds": duration_seconds,
              "origin": origin,
              "destination": destination,  # Return original destination for consistency
              "successful_variation": dest_variation,
          }
          break  # Success! Stop trying other variations

        elif element_status == "ZERO_RESULTS":
          logfire.warning(
              f"Google Maps API returned ZERO_RESULTS for variation {i+1}: '{dest_variation}'. Trying next variation.")
          continue  # Try next variation

        else:
          # Other error status - log but continue trying
          logfire.warning(
              f"Google Maps API error for variation {i+1} '{dest_variation}': GMaps Status: {gmaps_status}, Element Status: {element_status}")
          continue  # Try next variation

      except (ApiError, HTTPError, Timeout, TransportError) as e:
        msg = f"Google Maps API client error for variation {i+1} '{dest_variation}': {type(e).__name__} - {str(e)}"
        logfire.warning(msg)
        attempted_variations.append(dest_variation)
        continue  # Try next variation

      except Exception as e:
        msg = f"Unexpected error during Google Maps API call for variation {i+1} '{dest_variation}': {str(e)}"
        logfire.warning(msg)
        attempted_variations.append(dest_variation)
        continue  # Try next variation

    # If we reach here and final_result_data is None, all variations failed
    if final_result_data is None:
      msg = f"Google Maps API failed for all {len(attempted_variations)} address variations of '{destination}'"
      logfire.error(msg)
      await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
      await self.mongo_service.log_error_to_db(
          service_name="GoogleMapsOperations.get_distance_from_google",
          error_type="GoogleMapsAPIAllVariationsFailed",
          message=msg,
          details={
              "origin": origin,
              "original_destination": destination,
              "attempted_variations": attempted_variations,
              "total_variations_tried": len(attempted_variations),
          },
      )

    return final_result_data
